"""
Michigan Child Welfare Agency Metadata Retrieval

This script pulls agency information and associated document metadata from the
Michigan Child Welfare Public Licensing Search API. It fetches data for all
agencies and their available documents, saving the results to a run directory.

The script performs these operations:
1. Fetches all agency information from the API
2. For each agency, retrieves associated document metadata
3. Saves all agency info and document details as JSON,
   and most of the key information is also stored as CSV
4. Merges all document metadata into a single combined CSV file

API Functions Overview:
    Two main functions interact with the Michigan API:

    1. get_all_agency_info()
       - Fetches list of ALL agencies with basic info (name, address, license)
       - Called ONCE at start of pipeline
       - API method: 'getAgenciesDetail' with recordId=None

    2. get_content_details_method(record_id)
       - Fetches DOCUMENT listings for ONE specific agency
       - Called FOR EACH agency to get their PDF metadata
       - API method: 'getContentDetails' with specific recordId
       - Returns list of PDFs with ContentDocumentId needed for download

    Key Distinction:
        - getAgenciesDetail: Returns AGENCY information (who they are)
        - getContentDetails: Returns DOCUMENT listings (what files they have)

Usage:
    python pull_agency_info_api.py --run-dir run_2025-11-03 [--verbose]

Output (in run directory):
    - YYYY-MM-DD_all_agency_info.json: Complete API response with all agencies
    - YYYY-MM-DD_agency_info.csv: Agency information in CSV format
    - YYYY-MM-DD_combined_pdf_content_details.csv: All documents from all agencies
    - Individual JSON/CSV files per agency (removed after merging by default)

Author: STATCOM MCYJ project
"""

import csv
import requests
import json
import urllib.parse
import urllib3
import argparse
import os
import logging
from datetime import datetime

# Set up logger
logger = logging.getLogger(__name__)

def get_all_agency_info():
    """
    Fetches basic information for ALL agencies from the Michigan API.

    This function calls the 'getAgenciesDetail' API method with recordId=None to
    retrieve a list of all child welfare agencies in Michigan, including basic
    information like agency name, address, license status, etc.

    Returns:
        dict: JSON response containing a list of all agencies with their basic info
        None: If the request fails

    Note: This returns agency metadata ONLY, not the documents/PDFs associated
    with each agency. Use get_content_details_method() to fetch documents for
    a specific agency.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_url = "https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/webruntime/api/apex/execute"

    params = {
        "cacheable": "true",
        "classname": "@udd/01p8z0000009E4V",
        "isContinuation": "false",
        "method": "getAgenciesDetail",
        "namespace": "",
        "params": json.dumps({"recordId": None}),
        "language": "en-US",
        "asGuest": "true",
        "htmlEncode": "false"
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/'
    }

    try:
        logger.info("GET request with recordId=null")
        response = requests.get(base_url, params=params, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"GET request with recordId=null failed: {e}")
        return None

def get_content_details_method(record_id):
    """
    Fetches document/PDF metadata for a SPECIFIC agency by its record ID.

    This is the function used to get the list of documents associated with a
    specific agency.

    This function calls the 'getContentDetails' API method with a specific
    recordId to get a list of all documents (PDFs) associated with that agency,
    including metadata like:
        - Title: Document name/title
        - CreatedDate: When the document was created
        - FileExtension: Usually 'pdf'
        - ContentDocumentId: Unique ID needed to download the actual PDF file
        - ContentBodyId: Internal reference ID

    Args:
        record_id (str): The agency's unique identifier (agencyId)

    Returns:
        dict: JSON response containing list of documents in 'contentVersionRes' key
        None: If the request fails

    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_url = "https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/webruntime/api/apex/execute"

    # JSON payload
    payload = {
        "namespace": "",
        "classname": "@udd/01p8z0000009E4V",
        "method": "getContentDetails",
        "isContinuation": False,
        "params": {
            "recordId": record_id
        },
        "cacheable": False
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://michildwelfarepubliclicensingsearch.michigan.gov',
        'Referer': 'https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/'
    }

    logger.info("POST with JSON payload directly to the API endpoint")
    logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(
        base_url,
        json=payload,
        headers=headers,
        verify=False,
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def merge_agency_info(agency_csv, run_dir = ".", remove_files=False):
    """
    Merges the agency details into the all agency info dictionary.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Build a mapping from agencyId to AgencyName
    agency_names = {}
    with open(agency_csv, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            agency_id = row.get('agencyId')
            agency_name = row.get('AgencyName')
            if agency_id and agency_name:
                agency_names[agency_id] = agency_name

    # Merge PDF content details for each agency

    combined_rows = []
    header = []
    for agency_id, agency_name in agency_names.items():
        pdf_csv = os.path.join(run_dir, f"{agency_id}_pdf_content_details.csv")
        if os.path.exists(pdf_csv):
            with open(pdf_csv, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                header = ['agency_name'] + header
                for row in reader:
                    combined_rows.append([agency_name] + row)
        else:
            logger.warning(f"PDF content details CSV not found for agency ID {agency_id}, skipping...")
            continue

    # Write out the combined CSV
    combined_csv = os.path.join(run_dir, f"{date_str}_combined_pdf_content_details.csv")
    with open(combined_csv, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        # Write header: agency_id + original header
        writer.writerow(header)
        writer.writerows(combined_rows)

    logger.info(f"Combined PDF content details written to {combined_csv}")
    # If remove files then remove each file
    if remove_files:
        for agency_id, agency_name in agency_names.items():
            pdf_csv = os.path.join(run_dir, f"{agency_id}_pdf_content_details.csv")
            json_path = os.path.join(run_dir, f"{agency_id}_pdf_content_details.json")
            if os.path.exists(pdf_csv):
                os.remove(pdf_csv)
                logger.debug(f"Removed file: {pdf_csv}")
            if os.path.exists(json_path):
                os.remove(json_path)
                logger.debug(f"Removed file: {json_path}")
    return combined_csv


def pull_all_agency_metadata(run_dir, overwrite=False, remove_files=True, verbose=False):
    """
    Main function to pull all agency metadata and document listings from Michigan API.

    This function orchestrates the complete metadata retrieval process:
    1. Fetches all agency information
    2. Saves agency info to JSON and CSV
    3. For each agency, fetches document metadata
    4. Merges all document metadata into a combined CSV

    Args:
        run_dir (str): Directory to save all metadata files
        overwrite (bool): If False, skip agencies with existing CSV files (default: False)
        remove_files (bool): Remove individual agency files after merging (default: True)
        verbose (bool): Enable verbose output (default: False)

    Returns:
        str: Path to the combined CSV file containing all document metadata

    Raises:
        RuntimeError: If unable to fetch agency information from API
    """
    os.makedirs(run_dir, exist_ok=True)

    # Step 1: Fetch all agency information
    all_agency_info = get_all_agency_info()
    if not all_agency_info:
        raise RuntimeError("Failed to fetch agency information from API")

    if verbose:
        logger.debug(json.dumps(all_agency_info, indent=2))

    date_str = datetime.now().strftime("%Y-%m-%d")

    # Save complete agency info JSON
    agency_file = os.path.join(run_dir, f"{date_str}_all_agency_info.json")
    with open(agency_file, "w", encoding="utf-8") as f:
        json.dump(all_agency_info, f, indent=2, ensure_ascii=False)
    logger.info(f"All agency information saved to {agency_file}")

    # Extract agency list
    agency_list = (
        all_agency_info.get('returnValue', {})
        .get('objectData', {})
        .get('responseResult', [])
    )

    # Step 2: Save agency info as CSV
    agency_keep_cols = [
        "Address", "agencyId", "AgencyName", "AgencyType", "City", "County",
        "LicenseEffectiveDate", "LicenseeGroupOrganizationName",
        "LicenseExpirationDate", "LicenseNumber", "LicenseStatus", "Phone", "ZipCode"
    ]

    agency_csv_file = os.path.join(run_dir, f"{date_str}_agency_info.csv")
    with open(agency_csv_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=agency_keep_cols, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for agency in agency_list:
            row = {col: agency.get(col, "") for col in agency_keep_cols}
            writer.writerow(row)
    logger.info(f"Agency info written to {agency_csv_file}")

    # Step 3: Fetch document metadata for each agency
    doc_keep_cols = ['FileExtension', 'CreatedDate', 'Title', 'ContentBodyId', 'Id', 'ContentDocumentId']

    for agency in agency_list:
        record_id = agency.get('agencyId')
        if not record_id:
            if verbose:
                logger.debug(f"Skipping agency with empty ID")
            continue

        csv_file = os.path.join(run_dir, f"{record_id}_pdf_content_details.csv")

        # Skip if file exists and not overwriting
        if not overwrite and os.path.exists(csv_file):
            if verbose:
                logger.debug(f"Skipping {record_id} (file exists, overwrite=False)")
            continue

        if verbose:
            logger.info(f"Processing agency ID: {record_id}")

        pdf_results = get_content_details_method(record_id)

        if pdf_results:
            # Save full JSON
            json_file = os.path.join(run_dir, f"{record_id}_pdf_content_details.json")
            with open(json_file, "w", encoding="utf-8") as jf:
                json.dump(pdf_results, jf, indent=2, ensure_ascii=False)

            # Save CSV with key fields
            with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                writer.writerow(['agency_id'] + doc_keep_cols)
                for p in pdf_results.get('returnValue', {}).get('contentVersionRes', []):
                    row_data = [record_id] + [p.get(k, "") for k in doc_keep_cols]
                    writer.writerow(row_data)

            if verbose:
                logger.debug(f"  Saved document metadata for {record_id}")
        else:
            logger.warning(f"Failed to retrieve document details for agency ID: {record_id}")

    # Step 4: Merge all document metadata into single CSV
    combined_csv = merge_agency_info(agency_csv_file, run_dir, remove_files=remove_files)
    return combined_csv


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pull agency metadata and document listings from Michigan Child Welfare API"
    )
    parser.add_argument(
        "--run-dir",
        dest="run_dir",
        help="Directory for this run's metadata and artifacts",
        default="./"
    )
    parser.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        help="Overwrite existing files (default: False)"
    )
    parser.add_argument(
        "--remove-files",
        dest="remove_files",
        action="store_true",
        default=True,
        help="Remove individual agency files after merging (default: True)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        combined_csv = pull_all_agency_metadata(
            run_dir=args.run_dir,
            overwrite=args.overwrite,
            remove_files=args.remove_files,
            verbose=args.verbose
        )
        logger.info(f"Success! Combined metadata saved to: {combined_csv}")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)