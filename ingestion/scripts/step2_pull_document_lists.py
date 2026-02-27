#!/usr/bin/env python3
"""Step 2: Iterate all agencies, fetch document lists, update downloaded_files_database.csv.

No downloading happens here — only metadata discovery and tracking.

- New documents get download_status='pending', empty sha256.
- Existing documents get API fields refreshed and last_seen_in_api_utc updated.
- Documents no longer in API get download_status='unavailable' (only if no API calls failed).
- Never deletes rows.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.scripts.pull_agency_info_api import get_all_agency_info, get_content_details_method

DEFAULT_DOWNLOAD_DB_CSV = "ingestion/data/downloaded_files_database.csv"

DB_COLUMNS = [
    "generated_filename", "agency_name", "agency_id", "FileExtension", "CreatedDate",
    "Title", "ContentBodyId", "Id", "ContentDocumentId", "downloaded_filename", "sha256",
    "downloaded_at_utc", "last_seen_in_api_utc", "unavailable_marked_at_utc",
    "download_status", "id_match_checked",
]


def run(download_db_csv: str) -> None:
    # Load existing DB
    if os.path.exists(download_db_csv):
        db = pd.read_csv(download_db_csv, dtype=str).fillna("")
    else:
        db = pd.DataFrame(columns=DB_COLUMNS)

    # Index by ContentDocumentId for fast lookup
    db_index = {}
    for idx, row in db.iterrows():
        cdid = row.get("ContentDocumentId", "").strip()
        if cdid:
            db_index[cdid] = idx

    # Fetch agency list
    all_agency_info = get_all_agency_info()
    if not all_agency_info:
        raise RuntimeError("Failed to fetch agency information from API")

    agency_list = (
        all_agency_info.get("returnValue", {})
        .get("objectData", {})
        .get("responseResult", [])
    )
    print(f"Fetched {len(agency_list)} agencies. Starting document list discovery.")

    api_seen = set()
    failed_agency_count = 0
    new_count = 0
    now_utc = datetime.now(timezone.utc).isoformat()
    new_rows = []

    for agency in agency_list:
        agency_id = (agency.get("agencyId") or "").strip()
        agency_name = (agency.get("AgencyName") or "").strip()
        if not agency_id:
            continue

        pdf_results = get_content_details_method(agency_id)
        if not pdf_results:
            failed_agency_count += 1
            continue

        records = pdf_results.get("returnValue", {}).get("contentVersionRes", [])
        if not isinstance(records, list):
            failed_agency_count += 1
            continue

        for record in records:
            content_document_id = (record.get("ContentDocumentId") or "").strip()
            if not content_document_id:
                continue

            api_seen.add(content_document_id)

            if content_document_id in db_index:
                # Update existing row with API metadata
                idx = db_index[content_document_id]
                db.at[idx, "agency_name"] = agency_name or db.at[idx, "agency_name"]
                db.at[idx, "agency_id"] = agency_id or db.at[idx, "agency_id"]
                for key in ["FileExtension", "CreatedDate", "Title", "ContentBodyId", "Id"]:
                    new_val = (record.get(key) or "").strip()
                    if new_val:
                        db.at[idx, key] = new_val
                db.at[idx, "last_seen_in_api_utc"] = now_utc
                db.at[idx, "id_match_checked"] = "true"
                # If was unavailable, mark available again
                if db.at[idx, "download_status"] == "unavailable":
                    db.at[idx, "download_status"] = "available_existing"
                db.at[idx, "unavailable_marked_at_utc"] = ""
            else:
                # New document
                new_row = {col: "" for col in DB_COLUMNS}
                new_row["ContentDocumentId"] = content_document_id
                new_row["agency_name"] = agency_name
                new_row["agency_id"] = agency_id
                for key in ["FileExtension", "CreatedDate", "Title", "ContentBodyId", "Id"]:
                    new_row[key] = (record.get(key) or "").strip()
                new_row["last_seen_in_api_utc"] = now_utc
                new_row["download_status"] = "pending"
                new_row["id_match_checked"] = "true"
                new_rows.append(new_row)
                # Register in index so we don't add duplicates within this run
                db_index[content_document_id] = len(db) + len(new_rows) - 1
                new_count += 1

    # Append new rows
    if new_rows:
        db = pd.concat([db, pd.DataFrame(new_rows, columns=DB_COLUMNS)], ignore_index=True)

    # Mark unavailable if we had a complete API sweep
    unavailable_count = 0
    if failed_agency_count == 0:
        for idx, row in db.iterrows():
            cdid = row.get("ContentDocumentId", "").strip()
            if cdid and cdid not in api_seen:
                if db.at[idx, "download_status"] != "unavailable":
                    unavailable_count += 1
                db.at[idx, "download_status"] = "unavailable"
                db.at[idx, "unavailable_marked_at_utc"] = now_utc
        print(
            f"Availability sync: seen_in_api={len(api_seen)}, "
            f"marked_unavailable={unavailable_count}"
        )
    else:
        print(
            f"Skipped unavailable marking (failed_agencies={failed_agency_count})"
        )

    # Save
    os.makedirs(os.path.dirname(download_db_csv) or ".", exist_ok=True)
    db.to_csv(download_db_csv, index=False)

    print(
        f"Document list update complete: total={len(db)}, new={new_count}, "
        f"failed_agencies={failed_agency_count}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Step 2: Fetch document lists from API and update downloaded_files_database.csv"
    )
    parser.add_argument(
        "--download-db-csv",
        default=DEFAULT_DOWNLOAD_DB_CSV,
        help=f"Path to downloaded_files_database.csv (default: {DEFAULT_DOWNLOAD_DB_CSV})",
    )
    args = parser.parse_args()
    run(args.download_db_csv)


if __name__ == "__main__":
    main()
