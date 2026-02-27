#!/usr/bin/env python3
"""Step 2: Fetch document metadata for every agency from the Michigan API.

This is the most network-intensive step — it makes one API call per agency
to retrieve each agency's document list.  No PDF file downloads happen here,
only metadata discovery.

Behaviour:
- New documents get download_status='pending', empty sha256.
- Existing documents get API fields refreshed and last_seen_in_api_utc updated.
- Documents no longer in API get download_status='unavailable'
  (only when *every* agency call succeeded, so partial failures don't
  incorrectly mark documents as gone).
- Never deletes rows.
"""

import argparse
import os
from datetime import datetime, timezone

import pandas as pd

from pull_agency_info_api import get_all_agency_info, get_agency_document_list

DEFAULT_DOWNLOAD_DB_CSV = "ingestion/data/downloaded_files_database.csv"

DB_COLUMNS = [
    "generated_filename", "agency_name", "agency_id", "FileExtension", "CreatedDate",
    "Title", "ContentBodyId", "Id", "ContentDocumentId", "downloaded_filename", "sha256",
    "downloaded_at_utc", "last_seen_in_api_utc", "unavailable_marked_at_utc",
    "download_status", "id_match_checked",
]

API_METADATA_FIELDS = ["FileExtension", "CreatedDate", "Title", "ContentBodyId", "Id"]


def _load_db(csv_path: str) -> pd.DataFrame:
    """Load the download database CSV, indexed by ContentDocumentId."""
    if os.path.exists(csv_path):
        db = pd.read_csv(csv_path, dtype=str).fillna("")
    else:
        db = pd.DataFrame(columns=DB_COLUMNS)

    # ContentDocumentId is the natural key — enforce uniqueness and use as index
    db["ContentDocumentId"] = db["ContentDocumentId"].str.strip()
    dupes = db["ContentDocumentId"].duplicated(keep="first")
    if dupes.any():
        n = dupes.sum()
        print(f"WARNING: dropped {n} duplicate ContentDocumentId rows from DB")
        db = db[~dupes]

    db = db.set_index("ContentDocumentId", drop=False)
    return db


def _update_existing_row(db: pd.DataFrame, cdid: str, agency_name: str,
                         agency_id: str, record: dict, now_utc: str) -> None:
    """Refresh API metadata on a document we already know about."""
    if agency_name:
        db.at[cdid, "agency_name"] = agency_name
    if agency_id:
        db.at[cdid, "agency_id"] = agency_id
    for key in API_METADATA_FIELDS:
        new_val = (record.get(key) or "").strip()
        if new_val:
            db.at[cdid, key] = new_val
    db.at[cdid, "last_seen_in_api_utc"] = now_utc
    db.at[cdid, "id_match_checked"] = "true"
    if db.at[cdid, "download_status"] == "unavailable":
        db.at[cdid, "download_status"] = "available_existing"
    db.at[cdid, "unavailable_marked_at_utc"] = ""


def _make_new_row(cdid: str, agency_name: str, agency_id: str,
                  record: dict, now_utc: str) -> dict:
    """Build a fresh row dict for a newly discovered document."""
    row = {col: "" for col in DB_COLUMNS}
    row["ContentDocumentId"] = cdid
    row["agency_name"] = agency_name
    row["agency_id"] = agency_id
    for key in API_METADATA_FIELDS:
        row[key] = (record.get(key) or "").strip()
    row["last_seen_in_api_utc"] = now_utc
    row["download_status"] = "pending"
    row["id_match_checked"] = "true"
    return row


def run(download_db_csv: str) -> None:
    """Fetch document lists for all agencies and update the download database."""
    db = _load_db(download_db_csv)

    # Fetch agency list (single API call)
    all_agency_info = get_all_agency_info()
    if not all_agency_info:
        raise RuntimeError("Failed to fetch agency information from API")

    agency_list = (
        all_agency_info.get("returnValue", {})
        .get("objectData", {})
        .get("responseResult", [])
    )
    print(f"Fetched {len(agency_list)} agencies. Fetching document lists...")

    api_seen: set[str] = set()
    failed_agency_count = 0
    now_utc = datetime.now(timezone.utc).isoformat()
    new_rows: list[dict] = []
    new_cdids_this_run: set[str] = set()  # dedup within this run

    for agency in agency_list:
        agency_id = (agency.get("agencyId") or "").strip()
        agency_name = (agency.get("AgencyName") or "").strip()
        if not agency_id:
            continue

        pdf_results = get_agency_document_list(agency_id)
        if not pdf_results:
            failed_agency_count += 1
            continue

        records = pdf_results.get("returnValue", {}).get("contentVersionRes", [])
        if not isinstance(records, list):
            failed_agency_count += 1
            continue

        for record in records:
            cdid = (record.get("ContentDocumentId") or "").strip()
            if not cdid:
                continue

            api_seen.add(cdid)

            if cdid in db.index:
                _update_existing_row(db, cdid, agency_name, agency_id, record, now_utc)
            elif cdid not in new_cdids_this_run:
                new_rows.append(_make_new_row(cdid, agency_name, agency_id, record, now_utc))
                new_cdids_this_run.add(cdid)

    # Append new rows
    if new_rows:
        new_df = pd.DataFrame(new_rows, columns=DB_COLUMNS)
        new_df = new_df.set_index("ContentDocumentId", drop=False)
        db = pd.concat([db, new_df])

    # Mark unavailable — only if every agency call succeeded
    unavailable_count = 0
    if failed_agency_count == 0:
        not_seen = ~db.index.isin(api_seen) & (db.index != "")
        newly_unavailable = not_seen & (db["download_status"] != "unavailable")
        unavailable_count = newly_unavailable.sum()
        db.loc[not_seen, "download_status"] = "unavailable"
        db.loc[not_seen, "unavailable_marked_at_utc"] = now_utc
        print(
            f"Availability sync: seen_in_api={len(api_seen)}, "
            f"marked_unavailable={unavailable_count}"
        )
    else:
        print(
            f"Skipped unavailable marking (failed_agencies={failed_agency_count})"
        )

    # Save (reset index so ContentDocumentId goes back to being a normal column)
    db = db.reset_index(drop=True)
    os.makedirs(os.path.dirname(download_db_csv) or ".", exist_ok=True)
    db.to_csv(download_db_csv, index=False, lineterminator="\r\n")

    print(
        f"Document list update complete: total={len(db)}, new={len(new_rows)}, "
        f"failed_agencies={failed_agency_count}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Step 2: Fetch per-agency document lists and update downloaded_files_database.csv"
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
