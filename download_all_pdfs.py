#!/usr/bin/env python3
"""
Script to download all PDFs listed in a CSV by calling download_michigan_pdf
from `download_pdf.py` for each row.

Expected CSV headers:
generated_filename,agency_name,agency_id,FileExtension,CreatedDate,Title,ContentBodyId,Id,ContentDocumentId

Usage:
python download_all_pdfs.py --csv /path/to/file.csv --output-dir ./pdfs
"""
import csv
import os
import argparse
import time
import hashlib
from datetime import datetime, timezone
from typing import Optional

# Import functions from download_pdf.py
try:
    from download_pdf import download_michigan_pdf
except Exception as e:
    raise SystemExit(f"Failed to import download_michigan_pdf from download_pdf.py: {e}")


def compute_sha256(file_path: str, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA256 for a file."""
    digest = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_metadata_rows(metadata_csv: str):
    """Load existing metadata rows keyed by ContentDocumentId and generated_filename."""
    rows_by_id = {}
    rows_by_filename = {}
    fieldnames = []

    if not os.path.exists(metadata_csv):
        return rows_by_id, rows_by_filename, fieldnames

    with open(metadata_csv, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            content_document_id = (row.get('ContentDocumentId') or '').strip()
            generated_filename = (row.get('generated_filename') or '').strip()

            if content_document_id:
                rows_by_id[content_document_id] = row
            if generated_filename:
                rows_by_filename[generated_filename] = row

    return rows_by_id, rows_by_filename, fieldnames


def write_metadata_rows(metadata_csv: str, rows_by_id: dict, fieldnames: list):
    """Write metadata rows to disk in stable order."""
    os.makedirs(os.path.dirname(metadata_csv) or '.', exist_ok=True)
    ordered_rows = sorted(rows_by_id.values(), key=lambda row: (row.get('agency_id', ''), row.get('ContentDocumentId', '')))

    with open(metadata_csv, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for row in ordered_rows:
            writer.writerow({k: row.get(k, '') for k in fieldnames})


def process_csv(
    csv_path: str,
    output_dir: str,
    metadata_csv: Optional[str] = None,
    skip_existing: bool = True,
    limit: Optional[int] = None,
    sleep_seconds: float = 0.0,
):
    """Read CSV and call download_michigan_pdf for each row.

    Parameters:
        csv_path: path to input CSV
        output_dir: directory where PDFs will be saved
        metadata_csv: output metadata CSV tracking file IDs and SHA256 values
        skip_existing: if True and generated_filename present, skip if file exists
        limit: optional max number of rows to process
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    os.makedirs(output_dir, exist_ok=True)

    if not metadata_csv:
        metadata_csv = os.path.join(output_dir, 'facility_information_metadata.csv')

    existing_by_id, existing_by_filename, existing_fields = load_metadata_rows(metadata_csv)
    print(f"Loaded {len(existing_by_id)} existing metadata records from: {metadata_csv}")

    processed = 0
    failed = 0
    skipped_id_match = 0

    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        input_fields = list(reader.fieldnames or [])

        extra_fields = [
            'downloaded_filename',
            'downloaded_path',
            'sha256',
            'downloaded_at_utc',
            'download_status',
            'id_match_checked',
        ]
        metadata_fields = []
        for field in existing_fields + input_fields + extra_fields:
            if field and field not in metadata_fields:
                metadata_fields.append(field)

        for row in reader:
            if limit is not None and processed >= limit:
                break

            # Extract required fields from the CSV header
            gen_filename = (row.get('generated_filename') or '').strip()
            agency_name = (row.get('agency_name') or '').strip()
            agency_id = (row.get('agency_id') or '').strip()
            file_ext = (row.get('FileExtension') or '').strip()
            created_date = (row.get('CreatedDate') or '').strip()
            title = (row.get('Title') or '').strip()
            content_body_id = (row.get('ContentBodyId') or '').strip()
            id_field = (row.get('Id') or '').strip()
            content_document_id = (row.get('ContentDocumentId') or '').strip()

            # The download function needs ContentDocumentId (document_id);
            # fill other args from CSV.
            if not content_document_id:
                print(f"Skipping row with missing ContentDocumentId: {row}")
                failed += 1
                continue

            metadata_row = existing_by_id.get(content_document_id)
            if not metadata_row and gen_filename:
                metadata_row = existing_by_filename.get(gen_filename)

            target_path = os.path.join(output_dir, gen_filename) if gen_filename else None
            existing_path = (metadata_row or {}).get('downloaded_path', '').strip()
            if existing_path and not os.path.isabs(existing_path):
                existing_path = os.path.join(output_dir, existing_path)

            local_candidate_paths = [p for p in [target_path, existing_path] if p]
            local_file_path = next((p for p in local_candidate_paths if os.path.exists(p)), None)

            id_match = bool(metadata_row and (metadata_row.get('ContentDocumentId', '').strip() == content_document_id))

            if skip_existing and local_file_path and id_match:
                existing_sha = (metadata_row or {}).get('sha256', '').strip()
                if not existing_sha:
                    try:
                        existing_sha = compute_sha256(local_file_path)
                    except Exception as e:
                        print(f"Warning: could not compute SHA256 for {local_file_path}: {e}")
                        existing_sha = ''

                updated_row = dict(metadata_row or {})
                updated_row.update(row)
                updated_row.update({
                    'downloaded_filename': os.path.basename(local_file_path),
                    'downloaded_path': local_file_path,
                    'sha256': existing_sha,
                    'download_status': 'skipped_id_match',
                    'id_match_checked': 'true',
                })
                existing_by_id[content_document_id] = updated_row
                if gen_filename:
                    existing_by_filename[gen_filename] = updated_row

                print(f"Skipping existing file with matching ID: {local_file_path}")
                skipped_id_match += 1
                processed += 1
                continue

            if skip_existing and local_file_path and not id_match:
                print(
                    "Existing file found but metadata ID does not match API ID; "
                    f"re-downloading (api_id={content_document_id}, metadata_id={(metadata_row or {}).get('ContentDocumentId', '')})."
                )

            try:
                print(f"Downloading document {content_document_id} (agency: {agency_name}, title: {title})")
                out_path = download_michigan_pdf(
                    document_id=content_document_id,
                    document_agency=agency_name if agency_name else None,
                    document_name=title if title else None,
                    document_date=created_date if created_date else None,
                    output_dir=output_dir
                )

                if out_path:
                    sha256 = compute_sha256(out_path)
                    print(f"Saved to: {out_path}")
                    print(f"SHA256: {sha256}")

                    merged_row = dict(metadata_row or {})
                    merged_row.update(row)
                    merged_row.update({
                        'downloaded_filename': os.path.basename(out_path),
                        'downloaded_path': out_path,
                        'sha256': sha256,
                        'downloaded_at_utc': datetime.now(timezone.utc).isoformat(),
                        'download_status': 'downloaded',
                        'id_match_checked': 'true',
                    })
                    existing_by_id[content_document_id] = merged_row
                    if gen_filename:
                        existing_by_filename[gen_filename] = merged_row
                else:
                    print(f"Download returned None for {content_document_id}")
                    failed_row = dict(metadata_row or {})
                    failed_row.update(row)
                    failed_row.update({
                        'download_status': 'failed',
                        'id_match_checked': 'true',
                    })
                    existing_by_id[content_document_id] = failed_row
                    if gen_filename:
                        existing_by_filename[gen_filename] = failed_row
                    failed += 1

            except Exception as e:
                print(f"Error downloading {content_document_id}: {e}")
                failed_row = dict(metadata_row or {})
                failed_row.update(row)
                failed_row.update({
                    'download_status': 'failed',
                    'id_match_checked': 'true',
                })
                existing_by_id[content_document_id] = failed_row
                if gen_filename:
                    existing_by_filename[gen_filename] = failed_row
                failed += 1

            processed += 1
            # Sleep between downloads if requested
            if sleep_seconds and sleep_seconds > 0:
                try:
                    print(f"Sleeping for {sleep_seconds} seconds...")
                    time.sleep(sleep_seconds)
                except KeyboardInterrupt:
                    print("Sleep interrupted by user.")
                    break

    write_metadata_rows(metadata_csv, existing_by_id, metadata_fields)

    print(f"Metadata written to: {metadata_csv}")
    print(f"Done. Processed: {processed}. Failures: {failed}. Skipped with matching IDs: {skipped_id_match}.")
    return processed, failed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download PDFs listed in a CSV using download_michigan_pdf from download_pdf.py')
    parser.add_argument('--csv', required=True, help='Path to input CSV file')
    parser.add_argument('--output-dir', required=True, help='Directory to save downloaded PDFs')
    parser.add_argument('--metadata-csv', default=None, help='Path to metadata CSV (defaults to <output-dir>/facility_information_metadata.csv)')
    parser.add_argument('--no-skip', dest='skip_existing', action='store_false', help='Do not skip when generated_filename exists')
    parser.add_argument('--limit', type=int, default=None, help='Optional max number of rows to process')
    parser.add_argument('--sleep', dest='sleep_seconds', type=float, default=0.0, help='Seconds to sleep between downloads (float allowed)')

    args = parser.parse_args()

    process_csv(
        args.csv,
        args.output_dir,
        metadata_csv=args.metadata_csv,
        skip_existing=args.skip_existing,
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
    )
