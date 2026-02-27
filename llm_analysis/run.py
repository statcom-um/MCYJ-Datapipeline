#!/usr/bin/env python3
"""Run all three LLM analysis steps in sequence."""

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Run all LLM analysis steps")
    parser.add_argument(
        "--max-count",
        type=int,
        default=100,
        help="Maximum number of documents to process per step (default: 100)",
    )
    args = parser.parse_args()

    count = str(args.max_count)

    # Step 1: Update SIR summaries
    subprocess.run(
        [sys.executable, "llm_analysis/scripts/update_sir_summaries.py", "--count", count],
        check=True,
    )

    # Step 2: Update violation levels
    subprocess.run(
        [sys.executable, "llm_analysis/scripts/update_violation_levels.py", "--max-count", count],
        check=True,
    )

    # Step 3: Update staffing summaries
    subprocess.run(
        [sys.executable, "llm_analysis/scripts/update_staffing_summaries.py", "--max-count", count],
        check=True,
    )


if __name__ == "__main__":
    main()
