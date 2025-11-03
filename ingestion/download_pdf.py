"""
Single PDF Downloader - Core Download Function

This script provides the core functionality for downloading a single PDF document
from the Michigan Child Welfare Public Licensing Search system. It can be used
as a standalone script or imported by other scripts (like download_all_pdfs.py).

The script performs these operations:
1. Fetches document content from the Michigan API using ContentDocumentId
2. Decodes the base64-encoded PDF data
3. Generates a standardized filename from agency, document name, and date
4. Saves the PDF to the specified download directory

Usage as standalone:
    python download_pdf.py <document_id> --csv run_2025-11-03/combined_pdf_content_details.csv --download-dir Downloads

Usage as module:
    from download_pdf import download_michigan_pdf

    # Download with explicit file path
    download_michigan_pdf(document_id="0698z0000061FxYAAU", file_path="Downloads/my_document.pdf")

Arguments (standalone):
    document_id: The ContentDocumentId from the API (required)
    --csv: CSV file to lookup agency name (required)
    --download-dir: Directory to save the PDF (default: current directory)

Note: If a file already exists, the script will download the content and compare SHA256
hashes. If they match, it succeeds without overwriting. If they differ, it raises an error.

Author: STATCOM MCYJ project
"""

import requests
import base64
import urllib3
import os
import re
import argparse
import logging
import hashlib
from io import BytesIO

# Set up logger
logger = logging.getLogger(__name__)

def get_content_base_data(document_id):
    """
    POST request to fetch content base data for a given ContentDocumentId.

    Args:
        document_id (str): ContentDocumentId (069...)

    Returns:
        dict: JSON response with base64-encoded PDF data
        None: If request fails

    Note:
        The API only supports downloading by ContentDocumentId, which always returns
        the latest version. ContentVersionId cannot be used for downloading.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Use same base endpoint as other functions; include the query params
    base_url = "https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/webruntime/api/apex/execute?language=en-US&asGuest=true&htmlEncode=false"

    params_dict = {
        "contentDocumentId": document_id,
        "actionName": "download"
    }

    payload = {
        "namespace": "",
        "classname": "@udd/01p8z0000009E4V",
        "method": "getContentBaseData",
        "isContinuation": False,
        "params": params_dict,
        "cacheable": False
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://michildwelfarepubliclicensingsearch.michigan.gov',
        'Referer': 'https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/'
    }

    logger.info(f"POST getContentBaseData for ContentDocumentId={document_id}")
    response = requests.post(
        base_url,
        json=payload,
        headers=headers,
        verify=False,
        timeout=60
    )
    response.raise_for_status()
    return response.json()

def download_michigan_pdf(document_id, file_path):
    """
    Download a PDF from Michigan Child Welfare Public Licensing Search

    Args:
        document_id (str): The ContentDocumentId (e.g., "0698z0000061FxYAAU")
        file_path (str): Where to download the PDF file

    Returns:
        str: Path to the downloaded file if successful, None if failed

    Raises:
        ValueError: If API request fails or if existing file has different content (SHA256 mismatch)

    Note:
        Downloads using ContentDocumentId, which always returns the latest version.
        The API does not support downloading historical versions.
        If file exists, compares SHA256 hash - succeeds if identical, raises ValueError if different.
    """

    # Disable SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    logger.info(f"Downloading document: {document_id}")
    res = get_content_base_data(document_id=document_id)

    if not res or 'returnValue' not in res:
        raise ValueError(f"Failed to get PDF data from API for document ID: {document_id}")

    base64_data = res['returnValue']

    # Decode the PDF content
    pdf_content = base64.b64decode(base64_data)

    # Calculate SHA256 of the new content
    new_content_hash = hashlib.sha256(pdf_content).hexdigest()

    # Check if file exists and compare hashes
    if os.path.exists(file_path):
        logger.info(f"File already exists: {file_path}")
        logger.info("Comparing SHA256 hashes...")

        # Read existing file and calculate its hash
        with open(file_path, 'rb') as f:
            existing_content = f.read()
        existing_content_hash = hashlib.sha256(existing_content).hexdigest()

        if new_content_hash == existing_content_hash:
            logger.info(f"SHA256 hashes match - file is identical")
            logger.info(f"Downloaded {len(pdf_content)} bytes and verified existing file")
            return file_path
        else:
            raise ValueError(
                f"File exists but content differs (SHA256 mismatch):\n"
                f"  Existing: {existing_content_hash}\n"
                f"  New:      {new_content_hash}\n"
                f"  File:     {file_path}"
            )

    # Save the PDF (only if file doesn't exist or hashes match)
    with open(file_path, 'wb') as f:
        f.write(pdf_content)

    logger.info(f"Downloaded {len(pdf_content)} bytes")

    return file_path

def generate_filename(document_id, document_agency):
    """
    Generate a filename based on ContentDocumentId and agency name.

    Args:
        document_id (str): The ContentDocumentId (e.g., "0698z0000061FxYAAU")
        document_agency (str): Agency name

    Returns:
        str: Generated filename in format: {agency_name}_{document_id}.pdf

    Example:
        generate_filename("0698z0000061FxYAAU", "Glen's House")
        -> "glens_house_0698z0000061FxYAAU.pdf"
    """
    # Clean up agency name to be filesystem-safe
    def clean_string(s):
        if not s:
            return ""
        # Remove/replace problematic characters
        s = re.sub(r'[<>:"/\\|?*]', '_', s)
        # Replace spaces and special chars with underscores
        s = re.sub(r'\s+', '_', s)
        # Remove apostrophes and quotes
        s = s.replace("'", "").replace('"', '')
        # Remove leading/trailing underscores
        s = s.strip('_')
        return s.lower()

    # Build filename: {agency}_{document_id}.pdf
    agency_clean = clean_string(document_agency) if document_agency else "unknown"

    # If no document_id provided, use placeholder
    if not document_id:
        import time
        document_id = f"unknown_{int(time.time())}"

    # Format: {agency_name}_{document_id}.pdf
    filename = f"{agency_clean}_{document_id}.pdf"

    return filename

if __name__ == "__main__":
    # Set up logging for script use
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    parser = argparse.ArgumentParser(
        description="Download Michigan Child Welfare PDF by document ID."
    )
    parser.add_argument("document_id", help="The document ID (ContentDocumentId, e.g., 0698z0000061FxYAAU)")
    parser.add_argument("--csv", required=True, help="CSV file to lookup agency name (e.g., combined_pdf_content_details.csv)")
    parser.add_argument("--download-dir", dest="output_dir", help="Directory to save the PDF", default="./")

    args = parser.parse_args()

    # Look up agency name from CSV
    import csv as csv_module
    agency_name = None
    with open(args.csv, 'r', encoding='utf-8') as f:
        reader = csv_module.DictReader(f)
        for row in reader:
            if row.get('ContentDocumentId', '').strip() == args.document_id:
                agency_name = row.get('agency_name', '').strip()
                break

    if not agency_name:
        logger.error(f"Could not find ContentDocumentId={args.document_id} in {args.csv}")
        logger.error("Make sure the CSV has 'ContentDocumentId' and 'agency_name' columns")
        exit(1)

    logger.info(f"Found agency in CSV: {agency_name}")

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate filename and full file path
    filename = generate_filename(args.document_id, agency_name)
    file_path = os.path.join(args.output_dir, filename)

    try:
        result = download_michigan_pdf(
            document_id=args.document_id,
            file_path=file_path
        )
    except Exception as e:
        logger.error(f"Download failed: {e}")
        exit(1)

    if result:
        logger.info(f"Success! File saved to: {result}")
    else:
        logger.error("Download failed")
        exit(1)