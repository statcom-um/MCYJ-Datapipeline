#!/usr/bin/env python3
"""
Batch PDF Downloader - Downloads PDFs from Content Details CSV

This script downloads PDFs listed in a CSV file (such as combined_pdf_content_details.csv)
by calling download_michigan_pdf from download_pdf.py for each row. It handles batch
downloads with progress tracking, error handling, and rate limiting.

The script performs these operations:
1. Reads a CSV file containing document metadata
2. For each document, checks if it already exists (by ContentDocumentId pattern)
3. Downloads missing PDFs from the Michigan API
4. Skips files that already exist (configurable with --no-skip)
5. Applies rate limiting between downloads
6. Reports progress and failures

Expected CSV headers:
    ContentDocumentId,agency_name (required)
    Other columns are ignored but can be present

File Naming Convention:
    Files are named using ContentDocumentId as the unique identifier.
    Format: {agency_name}_{ContentDocumentId}.pdf
    Example: glens_house_0698z0000061FxYAAU.pdf

    Note: The API only exposes the latest version of each document. Historical versions
    are not accessible.

Usage:
    python download_all_pdfs.py --csv combined_pdf_content_details.csv --download-dir Downloads [--limit 100] [--sleep 0.5]

Options:
    --csv: Path to CSV file with document metadata (e.g., combined_pdf_content_details.csv)
    --download-dir: Directory to save downloaded PDFs
    --no-skip: Re-download files even if they exist
    --limit: Maximum number of files to download (for testing)
    --sleep: Seconds to sleep between downloads (default: 0.1)

Author: STATCOM MCYJ project
"""
import csv
import os
import argparse
import time
import logging
from typing import Optional

# Set up logger
logger = logging.getLogger(__name__)

# Import functions from download_pdf.py
from download_pdf import download_michigan_pdf, generate_filename
import glob

def process_csv(csv_path: str, output_dir: str, skip_existing: bool = True, limit: Optional[int] = None, sleep_seconds: Optional[float] = 0.1):
    """Read CSV and call download_michigan_pdf for each row.

    Parameters:
        csv_path: path to input CSV
        output_dir: directory where PDFs will be saved
        skip_existing: if True and file with matching ContentDocumentId
            is present, skip if file exists.  If False, download and verify
            that sha256 matches existing file (we will throw an exception and
            abort entire run if sha256 does not match, as this would indicates data
            inconsistency that requires investigation).
        limit: optional max number of rows to process
        sleep_seconds: seconds to sleep between downloads to respect
            rate limiting and avoid server overload.
    """

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    os.makedirs(output_dir, exist_ok=True)

    processed = 0
    failed = 0

    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if limit is not None and processed >= limit:
                break

            # Extract required fields from the CSV header
            content_document_id = (row.get('ContentDocumentId') or '').strip()
            agency_name = (row.get('agency_name') or '').strip()

            # Validate required fields
            if not content_document_id:
                logger.warning(f"Skipping row with missing ContentDocumentId: {row}")
                failed += 1
                continue

            # Use glob to find existing files with pattern *_ContentDocumentId.pdf
            pattern = os.path.join(output_dir, f"*_{content_document_id}.pdf")
            existing_files = glob.glob(pattern)

            # if there is exactly one existing file
            # we consider that the filename to use
            # (and possibly skip download)
            if len(existing_files)==1:
                filename = os.path.basename(existing_files[0])
                if skip_existing:
                    logger.info(f"Skipping existing file: {filename}")
                    processed += 1
                    continue
            elif len(existing_files) > 1:
                raise ValueError(f"Multiple existing files found for ContentDocumentId={content_document_id}: {existing_files}")
            else:
                filename = generate_filename(content_document_id, agency_name)

            try:
                logger.info(f"Downloading document {content_document_id} (agency: {agency_name})")
                file_path = os.path.join(output_dir, filename)
                out_path = download_michigan_pdf(
                    document_id=content_document_id,
                    file_path=file_path
                )
                logger.info(f"Saved to: {out_path}")

            except Exception as e:
                logger.error(f"Error downloading {content_document_id}: {e}")
                failed += 1

            processed += 1
            # Sleep between downloads if requested
            if sleep_seconds and sleep_seconds > 0:
                try:
                    logger.debug(f"Sleeping for {sleep_seconds} seconds...")
                    time.sleep(sleep_seconds)
                except KeyboardInterrupt:
                    logger.info("Sleep interrupted by user.")
                    break

    logger.info(f"Done. Processed: {processed}. Failures: {failed}.")
    return processed, failed


if __name__ == '__main__':
    # Set up logging for script use
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    parser = argparse.ArgumentParser(description='Download PDFs from content details CSV using download_michigan_pdf')
    parser.add_argument('--csv', required=True, help='Path to content details CSV file (e.g., combined_pdf_content_details.csv)')
    parser.add_argument('--download-dir', required=True, help='Directory to save downloaded PDFs')
    parser.add_argument('--no-skip', dest='skip_existing', action='store_false', help='Do not skip when generated_filename exists')
    parser.add_argument('--limit', type=int, default=None, help='Optional max number of rows to process')
    parser.add_argument('--sleep', dest='sleep_seconds', type=float, default=0.1, help='Seconds to sleep between downloads (float allowed)')

    args = parser.parse_args()

    process_csv(args.csv, args.download_dir, skip_existing=args.skip_existing, limit=args.limit, sleep_seconds=args.sleep_seconds)
