#!/usr/bin/env python3
"""Run the full ingestion workflow as 4 sequential steps plus a hash integrity check."""

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Run the full ingestion workflow")
    parser.add_argument(
        "--limit", type=int, default=None, help="Max number of new files to download"
    )
    parser.add_argument(
        "--sleep", type=float, default=0.0, help="Seconds to sleep between downloads"
    )
    parser.add_argument(
        "--skip-pdf-parsing",
        action="store_true",
        help="Skip PDF text extraction step after downloads",
    )
    args = parser.parse_args()

    # Step 1: Pull agency data → facility_information.csv
    subprocess.run(
        [sys.executable, "ingestion/scripts/step1_pull_agency_data.py"],
        check=True,
    )

    # Step 2: Pull document lists → downloaded_files_database.csv
    subprocess.run(
        [sys.executable, "ingestion/scripts/step2_pull_document_lists.py"],
        check=True,
    )

    # Step 3: Download unprocessed documents + PDF parsing
    cmd = [
        sys.executable, "ingestion/scripts/step3_pull_unprocessed_docs.py",
        "--sleep", str(args.sleep),
    ]
    if args.limit is not None:
        cmd.extend(["--limit", str(args.limit)])
    if args.skip_pdf_parsing:
        cmd.append("--skip-pdf-parsing")
    subprocess.run(cmd, check=True)

    # Step 4: Extract document info from parquet files
    subprocess.run(
        [
            sys.executable,
            "ingestion/scripts/extract_document_info.py",
            "--parquet-dir", "ingestion/data/parquet_files",
            "-o", "ingestion/data/document_info.csv",
        ],
        check=True,
    )

    # Hash integrity check
    subprocess.run(
        [sys.executable, "ingestion/scripts/check_unique_hashes.py"],
        check=True,
    )


if __name__ == "__main__":
    main()
