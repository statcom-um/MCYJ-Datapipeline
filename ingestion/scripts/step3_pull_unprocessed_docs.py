#!/usr/bin/env python3
"""Step 3: Fetch unprocessed PDFs from the Michigan API, extract text, and write to parquet.

For each pending document in downloaded_files_database.csv:
1. Fetch the PDF bytes from the API (kept in memory by default)
2. Compute SHA256 on the bytes
3. Extract page text via pdfplumber
4. Append the result to a new timestamped parquet file

Use --save-pdfs DIR to also persist the raw PDF files to disk.
"""

import argparse
import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from download_pdf import fetch_pdf_bytes, save_pdf
from extract_pdf_text import extract_text_from_pdf_bytes
from pipeline_utils import parse_created_date_to_iso

DEFAULT_DOWNLOAD_DB_CSV = "ingestion/data/downloaded_files_database.csv"
DEFAULT_PARQUET_DIR = "ingestion/data/parquet_files"


def run(
    download_db_csv: str,
    parquet_dir: str,
    limit: int | None,
    sleep_seconds: float,
    save_pdfs_dir: str | None,
) -> None:
    """Fetch, parse, and record unprocessed PDFs."""
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
        print("No documents to process.")
        return

    os.makedirs(parquet_dir, exist_ok=True)
    if save_pdfs_dir:
        os.makedirs(save_pdfs_dir, exist_ok=True)

    # Load existing SHA256 hashes from all parquet files so we can skip duplicates
    existing_hashes: set[str] = set()
    for pq_file in Path(parquet_dir).glob("*.parquet"):
        try:
            existing_hashes.update(pd.read_parquet(pq_file, columns=["sha256"])["sha256"].tolist())
        except Exception:
            pass
    print(f"Loaded {len(existing_hashes)} existing hashes from parquet files")

    # Collect parquet records for this batch
    records: list[dict] = []
    skipped_duplicate = 0

    for i, idx in enumerate(pending_indices, 1):
        row = db.loc[idx]
        content_document_id = row["ContentDocumentId"]
        agency_name = row.get("agency_name", "")

        # Fetch PDF bytes from the API
        pdf_bytes = fetch_pdf_bytes(content_document_id)
        if pdf_bytes is None:
            print(f"  [{i}/{len(pending_indices)}] Failed to fetch {content_document_id}")
            continue

        # SHA256 directly on the bytes — no disk needed
        sha = hashlib.sha256(pdf_bytes).hexdigest()

        # Extract text in memory
        try:
            pages_text = extract_text_from_pdf_bytes(pdf_bytes)
        except Exception as e:
            print(f"  [{i}/{len(pending_indices)}] pdfplumber failed for {content_document_id}: {e}")
            continue

        # Optionally save PDF to disk
        if save_pdfs_dir:
            created_date_iso = parse_created_date_to_iso(row.get("CreatedDate", ""))
            save_pdf(
                pdf_bytes, content_document_id,
                document_agency=agency_name or None,
                document_name=row.get("Title", "") or None,
                document_date=created_date_iso,
                output_dir=save_pdfs_dir,
            )

        # Update the database row
        now_utc = datetime.now(timezone.utc).isoformat()
        db.at[idx, "sha256"] = sha
        db.at[idx, "downloaded_at_utc"] = now_utc
        db.at[idx, "download_status"] = "downloaded"

        # Only add to parquet if this sha256 isn't already in existing files
        if sha in existing_hashes:
            skipped_duplicate += 1
            print(f"  [{i}/{len(pending_indices)}] Processed {content_document_id} ({len(pages_text)} pages) — sha256 already in parquet, skipped")
        else:
            records.append({
                "sha256": sha,
                "ContentDocumentId": content_document_id,
                "text": pages_text,
                "dateprocessed": datetime.now().isoformat(),
            })
            existing_hashes.add(sha)
            print(f"  [{i}/{len(pending_indices)}] Processed {content_document_id} ({len(pages_text)} pages)")

        if sleep_seconds > 0 and i < len(pending_indices):
            time.sleep(sleep_seconds)

    # Save updated DB
    db.to_csv(download_db_csv, index=False, lineterminator="\r\n")
    print(f"Download database updated: {download_db_csv} ({len(records)} new, {skipped_duplicate} duplicate sha256 skipped)")

    # Write parquet batch
    if records:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_parquet = Path(parquet_dir) / f"{timestamp}_pdf_text.parquet"
        pd.DataFrame(records).to_parquet(output_parquet, compression="zstd", index=False)
        print(f"Saved {len(records)} records to {output_parquet}")
    else:
        print("No new records to write to parquet.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Step 3: Fetch unprocessed PDFs, extract text, write to parquet"
    )
    parser.add_argument(
        "--download-db-csv",
        default=DEFAULT_DOWNLOAD_DB_CSV,
        help=f"Path to downloaded_files_database.csv (default: {DEFAULT_DOWNLOAD_DB_CSV})",
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
        help="Max number of documents to process",
    )
    parser.add_argument(
        "--sleep",
        dest="sleep_seconds",
        type=float,
        default=0.0,
        help="Seconds to sleep between API calls",
    )
    parser.add_argument(
        "--save-pdfs",
        dest="save_pdfs_dir",
        default=None,
        metavar="DIR",
        help="Also save raw PDF files to this directory",
    )
    args = parser.parse_args()

    run(
        download_db_csv=args.download_db_csv,
        parquet_dir=args.parquet_dir,
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
        save_pdfs_dir=args.save_pdfs_dir,
    )


if __name__ == "__main__":
    main()
