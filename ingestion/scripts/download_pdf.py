import argparse
import base64
import os
import re

import requests
import urllib3


def fetch_pdf_bytes(document_id: str) -> bytes | None:
    """Fetch a PDF from the Michigan API and return raw bytes, or None on failure."""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_url = "https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/webruntime/api/apex/execute?language=en-US&asGuest=true&htmlEncode=false"

    payload = {
        "namespace": "",
        "classname": "@udd/01p8z0000009E4V",
        "method": "getContentBaseData",
        "isContinuation": False,
        "params": {
            "contentDocumentId": document_id,
            "actionName": "download"
        },
        "cacheable": False
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://michildwelfarepubliclicensingsearch.michigan.gov',
        'Referer': 'https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/'
    }

    try:
        response = requests.post(
            base_url,
            json=payload,
            headers=headers,
            verify=False,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return base64.b64decode(data['returnValue'])
    except Exception as e:
        print(f"Failed to fetch PDF for {document_id}: {e}")
        return None


def save_pdf(pdf_bytes: bytes, document_id: str, document_agency=None,
             document_name=None, document_date=None, output_dir="./") -> str:
    """Save PDF bytes to disk. Returns the file path."""
    filename = generate_filename(document_id, document_agency, document_name, document_date)
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(pdf_bytes)
    return file_path


def download_michigan_pdf(document_id, document_agency=None, document_name=None,
                          document_date=None, output_dir="./"):
    """Fetch a PDF and save it to disk (convenience wrapper).

    Returns:
        str: Path to the downloaded file if successful, None if failed
    """
    pdf_bytes = fetch_pdf_bytes(document_id)
    if pdf_bytes is None:
        return None

    try:
        file_path = save_pdf(pdf_bytes, document_id, document_agency,
                             document_name, document_date, output_dir)
        print(f"PDF downloaded successfully: {file_path} ({len(pdf_bytes)} bytes)")
        return file_path
    except Exception as e:
        print(f"Error saving PDF: {e}")
        return None

def generate_filename(document_id, document_agency, document_name, document_date):
    """
    Generate a filename based on the provided parameters

    Args:
        document_id (str): The document ID
        document_agency (str): Agency name
        document_name (str): Document name
        document_date (str): Document date (not used in this version)

    Returns:
        str: Generated filename
    """
    # Clean up strings to be filesystem-safe
    def clean_string(s):
        if not s:
            return ""
        # Remove/replace problematic characters
        s = re.sub(r'[<>:"/\\|?*]', '_', s)
        # Remove extra whitespace
        s = re.sub(r'\s+', '_', s)
        # Remove leading/trailing underscores
        s = s.strip('_')
        return s

    # Build filename components
    parts = []

    if document_agency:
        parts.append(clean_string(document_agency))

    if document_name:
        parts.append(clean_string(document_name))

    if document_date:
        # Ensure the date is in YYYY-MM-DD format
        match = re.match(r'(\d{4})[-/](\d{2})[-/](\d{2})', str(document_date))
        # Raise error if month > 12
        if match:
            if int(match.group(2)) > 12:
                raise ValueError("Month in document date cannot be greater than 12")
            formatted_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            parts.append(formatted_date)
        else:
            # If not in correct format, skip or handle as needed
            raise ValueError("Document date must be in YYYY-MM-DD format")

    # Always include the document ID
    parts.append(clean_string(document_id))

    # Join parts with underscores
    filename = '_'.join(parts)

    # Ensure it ends with .pdf
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'

    return filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Michigan Child Welfare PDF by document ID.")
    parser.add_argument("document_id", help="The document ID (e.g., 0698z0000061FxYAAU)")
    parser.add_argument("--agency", dest="document_agency", help="Agency name for filename", default=None)
    parser.add_argument("--name", dest="document_name", help="Document name for filename", default=None)
    parser.add_argument("--output-dir", dest="output_dir", help="Directory to save the PDF", default="./")
    parser.add_argument("--date", dest="document_date", help="Document date for filename (YYYY-MM-DD)", default=None)

    args = parser.parse_args()

    download_michigan_pdf(
        document_id=args.document_id,
        document_agency=args.document_agency,
        document_name=args.document_name,
        document_date=args.document_date,
        output_dir=args.output_dir
    )