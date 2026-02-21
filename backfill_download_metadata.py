#!/usr/bin/env python3
"""
Backfill metadata for already-downloaded PDFs.

Scans a PDF directory, computes SHA256 checksums, and writes/updates
facility_information_metadata.csv used by download_all_pdfs.py.

It can optionally enrich rows using a source CSV (for example
metadata_output/*_combined_pdf_content_details.csv or missing_files.csv)
by matching ContentDocumentId and generated_filename.
"""

import argparse
import csv
import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional


DEFAULT_METADATA_FILENAME = "facility_information_metadata.csv"


def compute_sha256(file_path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def infer_content_document_id_from_filename(filename: str) -> Optional[str]:
    """Infer Salesforce-like ContentDocumentId from filename suffix.

    Expected pattern examples:
    - AGENCY_TITLE_2025-07-18_069cs0000104BR0AAM.pdf
    - anything_0698z000005Hpu5AAC.pdf
    """
    stem, ext = os.path.splitext(os.path.basename(filename))
    if ext.lower() != ".pdf":
        return None

    match = re.search(r"_([A-Za-z0-9]{15,18})$", stem)
    if match:
        return match.group(1)
    return None


def load_csv_rows(csv_path: str) -> List[Dict[str, str]]:
    if not csv_path or not os.path.exists(csv_path):
        return []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [row for row in reader]


def build_source_indexes(source_rows: Iterable[Dict[str, str]]):
    by_id: Dict[str, Dict[str, str]] = {}
    by_filename: Dict[str, Dict[str, str]] = {}
    source_fields: List[str] = []

    for row in source_rows:
        if not source_fields:
            source_fields = list(row.keys())
        content_document_id = (row.get("ContentDocumentId") or "").strip()
        generated_filename = (row.get("generated_filename") or "").strip()

        if content_document_id and content_document_id not in by_id:
            by_id[content_document_id] = row
        if generated_filename and generated_filename not in by_filename:
            by_filename[generated_filename] = row

    return by_id, by_filename, source_fields


def build_existing_index(existing_rows: Iterable[Dict[str, str]]):
    by_id: Dict[str, Dict[str, str]] = {}
    by_filename: Dict[str, Dict[str, str]] = {}
    existing_fields: List[str] = []

    for row in existing_rows:
        if not existing_fields:
            existing_fields = list(row.keys())
        content_document_id = (row.get("ContentDocumentId") or "").strip()
        generated_filename = (row.get("generated_filename") or row.get("downloaded_filename") or "").strip()

        if content_document_id:
            by_id[content_document_id] = row
        if generated_filename:
            by_filename[generated_filename] = row

    return by_id, by_filename, existing_fields


def iter_pdf_files(pdf_dir: str):
    for name in sorted(os.listdir(pdf_dir)):
        path = os.path.join(pdf_dir, name)
        if os.path.isfile(path) and name.lower().endswith(".pdf"):
            yield name, path


def merge_row(base: Dict[str, str], overlay: Optional[Dict[str, str]]) -> Dict[str, str]:
    merged = dict(base)
    if overlay:
        for key, value in overlay.items():
            if value not in (None, ""):
                merged[key] = value
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill SHA256 and metadata for downloaded PDFs")
    parser.add_argument("--pdf-dir", required=True, help="Directory containing downloaded PDFs")
    parser.add_argument(
        "--metadata-csv",
        default=None,
        help="Metadata CSV path (default: <pdf-dir>/facility_information_metadata.csv)",
    )
    parser.add_argument(
        "--source-csv",
        default=None,
        help="Optional source CSV to enrich metadata rows (e.g., missing_files.csv or *_combined_pdf_content_details.csv)",
    )

    args = parser.parse_args()

    pdf_dir = args.pdf_dir
    if not os.path.isdir(pdf_dir):
        raise NotADirectoryError(f"PDF directory does not exist: {pdf_dir}")

    metadata_csv = args.metadata_csv or os.path.join(pdf_dir, DEFAULT_METADATA_FILENAME)

    existing_rows = load_csv_rows(metadata_csv)
    source_rows = load_csv_rows(args.source_csv) if args.source_csv else []

    existing_by_id, existing_by_filename, existing_fields = build_existing_index(existing_rows)
    source_by_id, source_by_filename, source_fields = build_source_indexes(source_rows)

    output_rows_by_id: Dict[str, Dict[str, str]] = {}
    unknown_id_rows: List[Dict[str, str]] = []

    processed = 0
    inferred_ids = 0
    unknown_ids = 0

    for filename, full_path in iter_pdf_files(pdf_dir):
        processed += 1

        content_document_id = infer_content_document_id_from_filename(filename)
        if content_document_id:
            inferred_ids += 1

        existing_row = None
        source_row = None
        if content_document_id:
            existing_row = existing_by_id.get(content_document_id)
            source_row = source_by_id.get(content_document_id)

        if not existing_row:
            existing_row = existing_by_filename.get(filename)
        if not source_row:
            source_row = source_by_filename.get(filename)

        row = {}
        row = merge_row(row, source_row)
        row = merge_row(row, existing_row)

        if content_document_id:
            row["ContentDocumentId"] = content_document_id

        row["generated_filename"] = row.get("generated_filename") or filename
        row["downloaded_filename"] = filename
        row["downloaded_path"] = full_path
        row["sha256"] = compute_sha256(full_path)
        row["downloaded_at_utc"] = row.get("downloaded_at_utc") or datetime.now(timezone.utc).isoformat()
        row["download_status"] = "backfilled"
        row["id_match_checked"] = "true" if content_document_id else "false"

        if content_document_id:
            output_rows_by_id[content_document_id] = row
        else:
            unknown_ids += 1
            unknown_id_rows.append(row)

    # Keep old existing rows for IDs not present in scanned directory
    for content_document_id, existing_row in existing_by_id.items():
        if content_document_id not in output_rows_by_id:
            output_rows_by_id[content_document_id] = existing_row

    output_rows = sorted(
        output_rows_by_id.values(),
        key=lambda row: (
            row.get("agency_id", ""),
            row.get("ContentDocumentId", ""),
            row.get("generated_filename", ""),
        ),
    ) + sorted(unknown_id_rows, key=lambda row: row.get("generated_filename", ""))

    extra_fields = [
        "generated_filename",
        "downloaded_filename",
        "downloaded_path",
        "sha256",
        "downloaded_at_utc",
        "download_status",
        "id_match_checked",
        "ContentDocumentId",
    ]

    fieldnames: List[str] = []
    for field in existing_fields + source_fields + extra_fields:
        if field and field not in fieldnames:
            fieldnames.append(field)

    os.makedirs(os.path.dirname(metadata_csv) or ".", exist_ok=True)
    with open(metadata_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in output_rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"Processed PDFs: {processed}")
    print(f"Inferred ContentDocumentId from filename: {inferred_ids}")
    print(f"PDFs without inferable ContentDocumentId: {unknown_ids}")
    print(f"Metadata rows written: {len(output_rows)}")
    print(f"Metadata output: {metadata_csv}")


if __name__ == "__main__":
    main()
