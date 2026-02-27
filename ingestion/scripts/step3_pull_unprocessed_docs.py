#!/usr/bin/env python3
"""Step 3: Download unprocessed documents and optionally parse PDFs to parquet.

Scans downloaded_files_database.csv for rows missing sha256, downloads the PDFs,
updates the CSV, and runs pdfplumber on new downloads.

- Only processes rows where sha256 is empty and download_status != 'unavailable'.
- Computes sha256 after download and updates the row.
- Stages new downloads in a temp dir and runs extract_pdf_text.process_directory().
"""

import argparse
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.scripts.download_pdf import download_michigan_pdf
from ingestion.scripts.extract_pdf_text import process_directory as process_pdf_directory
from ingestion.scripts.pipeline_utils import compute_sha256, parse_created_date_to_iso

DEFAULT_DOWNLOAD_DB_CSV = "ingestion/data/downloaded_files_database.csv"
DEFAULT_DOWNLOAD_DIR = "Downloads"
DEFAULT_PARQUET_DIR = "ingestion/data/parquet_files"


def run(
    download_db_csv: str,
    download_dir: str,
    parquet_dir: str,
    limit: int | None,
    sleep_seconds: float,
    skip_pdf_parsing: bool,
) -> None:
    # Load DB
    if not os.path.exists(download_db_csv):
        print(f"No download database found at {download_db_csv}; nothing to do.")
        return

    db = pd.read_csv(download_db_csv, dtype=str).fillna("")

    # Find pending rows: sha256 empty AND not unavailable
    pending_mask = (db["sha256"] == "") & (db["download_status"] != "unavailable")
    pending_indices = db.index[pending_mask].tolist()

    if limit is not None:
        pending_indices = pending_indices[:limit]

    print(f"Found {pending_mask.sum()} pending documents, will process {len(pending_indices)}")

    if not pending_indices:
        print("No documents to download.")
        return

    os.makedirs(download_dir, exist_ok=True)
    os.makedirs(parquet_dir, exist_ok=True)

    new_downloads = []  # list of (idx, downloaded_filename, sha256) for PDF parsing

    for i, idx in enumerate(pending_indices, 1):
        row = db.loc[idx]
        content_document_id = row["ContentDocumentId"]
        agency_name = row.get("agency_name", "")
        created_date_iso = parse_created_date_to_iso(row.get("CreatedDate", ""))

        out_path = download_michigan_pdf(
            document_id=content_document_id,
            document_agency=agency_name or None,
            document_name=row.get("Title", "") or None,
            document_date=created_date_iso,
            output_dir=download_dir,
        )

        if not out_path:
            print(f"  [{i}/{len(pending_indices)}] Failed to download {content_document_id}")
            continue

        sha = compute_sha256(out_path)
        filename = os.path.basename(out_path)

        db.at[idx, "sha256"] = sha
        db.at[idx, "downloaded_filename"] = filename
        db.at[idx, "generated_filename"] = filename
        db.at[idx, "downloaded_at_utc"] = datetime.now(timezone.utc).isoformat()
        db.at[idx, "download_status"] = "downloaded"

        new_downloads.append({
            "filename": filename,
            "ContentDocumentId": content_document_id,
            "sha256": sha,
        })

        print(f"  [{i}/{len(pending_indices)}] Downloaded {content_document_id}")

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    # Save updated DB
    db.to_csv(download_db_csv, index=False, lineterminator="\r\n")
    print(f"Download database updated: {download_db_csv} ({len(new_downloads)} new downloads)")

    # Parse new downloads to parquet
    if not skip_pdf_parsing and new_downloads:
        _parse_new_downloads(new_downloads, parquet_dir, download_dir)
    elif not new_downloads:
        print("No new downloads; skipping PDF parsing.")


def _parse_new_downloads(
    new_downloads: list[dict],
    parquet_dir: str,
    download_dir: str,
) -> None:
    """Stage new files in a temp dir and run PDF text extraction."""
    with tempfile.TemporaryDirectory(prefix="mcyj_new_downloads_") as staging_dir:
        staged_count = 0
        filename_to_metadata = {}

        for entry in new_downloads:
            filename = entry["filename"]
            file_path = os.path.join(download_dir, filename)
            if not os.path.exists(file_path):
                continue

            target_path = os.path.join(staging_dir, filename)
            try:
                os.symlink(os.path.abspath(file_path), target_path)
            except OSError:
                shutil.copy2(file_path, target_path)

            filename_to_metadata[filename] = {
                "ContentDocumentId": entry["ContentDocumentId"],
                "sha256": entry["sha256"],
            }
            staged_count += 1

        if staged_count == 0:
            print("No valid downloaded files available for parsing.")
            return

        print(f"Running PDF parsing on {staged_count} newly downloaded files...")
        process_pdf_directory(staging_dir, parquet_dir, limit=None, filename_to_metadata=filename_to_metadata)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Step 3: Download unprocessed documents and parse PDFs to parquet"
    )
    parser.add_argument(
        "--download-db-csv",
        default=DEFAULT_DOWNLOAD_DB_CSV,
        help=f"Path to downloaded_files_database.csv (default: {DEFAULT_DOWNLOAD_DB_CSV})",
    )
    parser.add_argument(
        "--download-dir",
        default=DEFAULT_DOWNLOAD_DIR,
        help=f"Directory for downloaded PDFs (default: {DEFAULT_DOWNLOAD_DIR})",
    )
    parser.add_argument(
        "--parquet-dir",
        default=DEFAULT_PARQUET_DIR,
        help=f"Output directory for parquet files (default: {DEFAULT_PARQUET_DIR})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of documents to download",
    )
    parser.add_argument(
        "--sleep",
        dest="sleep_seconds",
        type=float,
        default=0.0,
        help="Seconds to sleep between downloads",
    )
    parser.add_argument(
        "--skip-pdf-parsing",
        action="store_true",
        help="Skip PDF text extraction after downloads",
    )
    args = parser.parse_args()

    run(
        download_db_csv=args.download_db_csv,
        download_dir=args.download_dir,
        parquet_dir=args.parquet_dir,
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
        skip_pdf_parsing=args.skip_pdf_parsing,
    )


if __name__ == "__main__":
    main()
