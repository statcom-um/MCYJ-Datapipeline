#!/usr/bin/env python3
"""Step 2: Fetch document metadata for every agency from the Michigan API.

This is the most network-intensive step — it makes one API call per agency
to retrieve each agency's document list.  No PDF file downloads happen here,
only metadata discovery.

Behaviour:
- New documents get download_status='pending', empty sha256.
- Existing documents get API fields refreshed.
- If a document's ContentBodyId has changed (content replaced upstream),
  the existing row is marked unavailable and a fresh 'pending' row is
  created so Step 3 will re-download and re-hash the file.
- Documents no longer in API get download_status='unavailable'
  (only when *every* agency call succeeded, so partial failures don't
  incorrectly mark documents as gone).
- Never deletes rows.
"""

import argparse
import os
import time
from datetime import datetime, timezone

import pandas as pd

from pull_agency_info_api import get_all_agency_info, get_agency_document_list

DEFAULT_DOWNLOAD_DB_CSV = "ingestion/data/downloaded_files_database.csv"

DB_COLUMNS = [
    "generated_filename", "agency_name", "agency_id", "FileExtension", "CreatedDate",
    "Title", "ContentBodyId", "Id", "ContentDocumentId", "downloaded_filename", "sha256",
    "downloaded_at_utc", "unavailable_marked_at_utc",
    "download_status", "id_match_checked",
]

API_METADATA_FIELDS = ["FileExtension", "CreatedDate", "Title", "Id"]


def _load_db(csv_path: str) -> pd.DataFrame:
    """Load the download database CSV, indexed by ContentBodyId."""
    if os.path.exists(csv_path):
        db = pd.read_csv(csv_path, dtype=str).fillna("")
    else:
        db = pd.DataFrame(columns=DB_COLUMNS)

    # Drop columns from older schema versions (e.g. last_seen_in_api_utc)
    db = db[[c for c in db.columns if c in DB_COLUMNS]]
    for c in DB_COLUMNS:
        if c not in db.columns:
            db[c] = ""

    # ContentBodyId is the natural key — enforce uniqueness and use as index
    db["ContentBodyId"] = db["ContentBodyId"].str.strip()
    dupes = db["ContentBodyId"].duplicated(keep="first")
    if dupes.any():
        n = dupes.sum()
        print(f"WARNING: dropped {n} duplicate ContentBodyId rows from DB")
        db = db[~dupes]

    db = db.set_index("ContentBodyId", drop=False)
    return db


def _build_cdid_to_body_lookup(db: pd.DataFrame) -> dict[str, str]:
    """Map ContentDocumentId -> ContentBodyId for active (non-unavailable) rows.

    When a document has multiple rows (old unavailable + current active),
    only the active one is returned.
    """
    lookup: dict[str, str] = {}
    for cbid, row in db.iterrows():
        if row["download_status"] != "unavailable" and row["ContentDocumentId"]:
            lookup[row["ContentDocumentId"]] = cbid
    return lookup


def _update_existing_row(db: pd.DataFrame, cbid: str, agency_name: str,
                         agency_id: str, record: dict, now_utc: str) -> None:
    """Refresh API metadata on a document we already know about."""
    if agency_name:
        db.at[cbid, "agency_name"] = agency_name
    if agency_id:
        db.at[cbid, "agency_id"] = agency_id
    for key in API_METADATA_FIELDS:
        new_val = (record.get(key) or "").strip()
        if new_val:
            db.at[cbid, key] = new_val
    db.at[cbid, "id_match_checked"] = "true"
    if db.at[cbid, "download_status"] == "unavailable":
        db.at[cbid, "download_status"] = "available_existing"
    db.at[cbid, "unavailable_marked_at_utc"] = ""


def _make_new_row(cdid: str, agency_name: str, agency_id: str,
                  record: dict, now_utc: str) -> dict:
    """Build a fresh row dict for a newly discovered document."""
    row = {col: "" for col in DB_COLUMNS}
    row["ContentDocumentId"] = cdid
    row["ContentBodyId"] = (record.get("ContentBodyId") or "").strip()
    row["agency_name"] = agency_name
    row["agency_id"] = agency_id
    for key in API_METADATA_FIELDS:
        row[key] = (record.get(key) or "").strip()
    row["download_status"] = "pending"
    row["id_match_checked"] = "true"
    return row


def run(download_db_csv: str, sleep_seconds: float = 0.0) -> None:
    """Fetch document lists for all agencies and update the download database."""
    db = _load_db(download_db_csv)

    # Build a reverse lookup: ContentDocumentId -> active ContentBodyId
    cdid_to_cbid = _build_cdid_to_body_lookup(db)

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

    api_seen_cbids: set[str] = set()
    failed_agency_count = 0
    now_utc = datetime.now(timezone.utc).isoformat()
    new_rows: list[dict] = []
    new_cbids_this_run: set[str] = set()  # dedup within this run
    body_id_changes = 0

    n_agencies = len(agency_list)
    agencies_processed = 0
    for agency in agency_list:
        agency_id = (agency.get("agencyId") or "").strip()
        agency_name = (agency.get("AgencyName") or "").strip()
        if not agency_id:
            continue

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

        agencies_processed += 1
        if agencies_processed % 10 == 0 or agencies_processed == n_agencies:
            print(f"  Fetching document lists... {agencies_processed}/{n_agencies}")

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
            new_cbid = (record.get("ContentBodyId") or "").strip()
            if not cdid or not new_cbid:
                continue

            api_seen_cbids.add(new_cbid)

            if new_cbid in db.index:
                # Same ContentBodyId — just refresh metadata
                _update_existing_row(db, new_cbid, agency_name, agency_id, record, now_utc)
            elif cdid in cdid_to_cbid:
                # Same ContentDocumentId but different ContentBodyId —
                # content was replaced upstream.  Mark old row unavailable
                # and create a fresh pending row for re-download.
                old_cbid = cdid_to_cbid[cdid]
                db.at[old_cbid, "download_status"] = "unavailable"
                db.at[old_cbid, "unavailable_marked_at_utc"] = now_utc
                del cdid_to_cbid[cdid]
                body_id_changes += 1
                print(
                    f"  ContentBodyId changed for {cdid}: "
                    f"{old_cbid} -> {new_cbid}, scheduling re-download"
                )
                if new_cbid not in new_cbids_this_run:
                    new_rows.append(_make_new_row(cdid, agency_name, agency_id, record, now_utc))
                    new_cbids_this_run.add(new_cbid)
                    cdid_to_cbid[cdid] = new_cbid
            elif new_cbid not in new_cbids_this_run:
                # Entirely new document
                new_rows.append(_make_new_row(cdid, agency_name, agency_id, record, now_utc))
                new_cbids_this_run.add(new_cbid)
                cdid_to_cbid[cdid] = new_cbid

    # Append new rows
    if new_rows:
        new_df = pd.DataFrame(new_rows, columns=DB_COLUMNS)
        new_df = new_df.set_index("ContentBodyId", drop=False)
        db = pd.concat([db, new_df])

    # Mark unavailable — only if every agency call succeeded
    unavailable_count = 0
    if failed_agency_count == 0:
        not_seen = ~db.index.isin(api_seen_cbids) & (db.index != "")
        newly_unavailable = not_seen & (db["download_status"] != "unavailable")
        unavailable_count = newly_unavailable.sum()
        db.loc[not_seen, "download_status"] = "unavailable"
        db.loc[not_seen, "unavailable_marked_at_utc"] = now_utc
        print(
            f"Availability sync: seen_in_api={len(api_seen_cbids)}, "
            f"marked_unavailable={unavailable_count}"
        )
    else:
        print(
            f"Skipped unavailable marking (failed_agencies={failed_agency_count})"
        )

    # Save (reset index so ContentBodyId goes back to being a normal column)
    db = db.reset_index(drop=True)
    os.makedirs(os.path.dirname(download_db_csv) or ".", exist_ok=True)
    db.to_csv(download_db_csv, index=False, lineterminator="\r\n")

    print(
        f"Document list update complete: total={len(db)}, new={len(new_rows)}, "
        f"body_id_changes={body_id_changes}, "
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
    parser.add_argument(
        "--sleep",
        dest="sleep_seconds",
        type=float,
        default=0.5,
        help="Seconds to sleep between agency API calls (default: 0.5)",
    )
    args = parser.parse_args()
    run(args.download_db_csv, sleep_seconds=args.sleep_seconds)


if __name__ == "__main__":
    main()
