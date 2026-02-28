#!/usr/bin/env python3
"""Run the full ingestion workflow as 4 sequential steps plus a hash integrity check."""

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Run the full ingestion workflow")
    parser.add_argument(
        "--limit", type=int, default=None, help="Max number of new PDFs to process"
    )
    parser.add_argument(
        "--sleep", type=float, default=0.5, help="Seconds to sleep between API calls"
    )
    parser.add_argument(
        "--save-pdfs",
        default=None,
        metavar="DIR",
        help="Also save raw PDF files to this directory",
    )
    args = parser.parse_args()

    # Step 1: Pull agency data → facility_information.csv
    subprocess.run(
        [sys.executable, "ingestion/scripts/step1_pull_agency_data.py"],
        check=True,
    )

    # Step 2: Fetch per-agency document lists → downloaded_files_database.csv
    subprocess.run(
        [sys.executable, "ingestion/scripts/step2_pull_document_lists.py",
         "--sleep", str(args.sleep)],
        check=True,
    )

    # Step 3: Fetch unprocessed PDFs, extract text, write to parquet
    cmd = [
        sys.executable, "ingestion/scripts/step3_pull_unprocessed_docs.py",
        "--sleep", str(args.sleep),
    ]
    if args.limit is not None:
        cmd.extend(["--limit", str(args.limit)])
    if args.save_pdfs is not None:
        cmd.extend(["--save-pdfs", args.save_pdfs])
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
