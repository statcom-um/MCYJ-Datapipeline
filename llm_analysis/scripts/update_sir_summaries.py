#!/usr/bin/env python3
"""
Update sir_summaries.csv with AI-generated summaries for SIRs.

This script:
1. Reads document_info.csv to identify all SIR document shas
2. Compares against existing summaries in llm_analysis/sir_summaries.csv
3. Queries up to N missing SIRs using OpenRouter API
4. Appends new results to llm_analysis/sir_summaries.csv
"""

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

from llm_utils import (
    get_api_key,
    get_existing_shas,
    load_document_from_parquet,
    parse_json_response,
    query_openrouter,
    setup_logger,
)

logger = setup_logger(__name__, 'update_sir_summaries.log')

# Query to ask about each SIR - now requests JSON format
QUERY_TEXT = """Please analyze this Special Investigation Report and respond with a JSON object containing exactly two fields:

1. "summary": A few sentences explaining what went down here, including one extra sentence weighing in on culpability.
2. "violation": Either "y" if allegations of policy/code violations were substantiated in this report, or "n" if they were not substantiated.

Return ONLY the JSON object, no other text. Format:
{"summary": "...", "violation": "y"}"""


def get_all_sir_shas(doc_info_csv: str):
    """Get SHA256 hashes for all documents that are SIRs from document_info.csv."""
    doc_info_path = Path(doc_info_csv)
    if not doc_info_path.exists():
        raise FileNotFoundError(f"Document info CSV not found: {doc_info_csv}")

    df = pd.read_csv(doc_info_csv)
    sirs = df[df['is_special_investigation'] == True]
    logger.info(f"Found {len(sirs)} SIRs in document info CSV")
    return [str(row['sha256']) for _, row in sirs.iterrows()]


def parse_sir_response(ai_response: str):
    """Parse the summary and violation from the AI response."""
    try:
        parsed = parse_json_response(ai_response)
        summary = parsed.get('summary', '')
        violation = parsed.get('violation', '').lower()
        if violation not in ['y', 'n']:
            violation = 'y' if 'yes' in violation or 'substantiated' in violation.lower() else 'n'
        return summary, violation
    except (ValueError, AttributeError, KeyError):
        # Fallback: try regex for JSON with summary+violation keys
        json_match = re.search(r'\{[^{}]*"summary"[^{}]*"violation"[^{}]*\}', ai_response, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                summary = parsed.get('summary', '')
                violation = parsed.get('violation', '').lower()
                if violation not in ['y', 'n']:
                    violation = 'y' if 'yes' in violation or 'substantiated' in violation.lower() else 'n'
                return summary, violation
            except json.JSONDecodeError:
                pass
        return '', ''


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update sir_summaries.csv with AI summaries for missing SIRs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--doc-info',
        default='../../ingestion/data/document_info.csv',
        help='Path to document_info.csv file (default: ../../ingestion/data/document_info.csv)'
    )
    parser.add_argument(
        '--parquet-dir',
        default='../../ingestion/data/parquet_files',
        help='Directory containing parquet files (default: ../../ingestion/data/parquet_files)'
    )
    parser.add_argument(
        '--output', '-o',
        default='../data/sir_summaries.csv',
        help='Output CSV file path (default: ../data/sir_summaries.csv)'
    )
    parser.add_argument(
        '--count', '-n',
        type=int,
        default=100,
        help='Maximum number of new SIRs to query (default: 100)'
    )
    parser.add_argument(
        '--query',
        default=QUERY_TEXT,
        help=f'Query text to use (default: "{QUERY_TEXT}")'
    )

    args = parser.parse_args()

    # Resolve paths relative to script directory
    script_dir = Path(__file__).parent
    doc_info_path = script_dir / args.doc_info
    parquet_dir = script_dir / args.parquet_dir
    output_path = script_dir / args.output

    # Get API key
    try:
        api_key = get_api_key()
        logger.info("API key loaded from environment")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Get all SIRs from document info CSV
    logger.info(f"Reading document info from {doc_info_path}...")
    all_sir_shas_list = get_all_sir_shas(str(doc_info_path))

    if not all_sir_shas_list:
        logger.warning("No SIRs found in document info CSV")
        sys.exit(0)

    all_sir_shas = set(all_sir_shas_list)

    # Get existing summary shas
    existing_shas = get_existing_shas(str(output_path), logger)

    # Find missing shas
    missing_shas = all_sir_shas - existing_shas
    logger.info(f"Found {len(missing_shas)} SIRs without summaries")

    if not missing_shas:
        logger.info("All SIRs already have summaries!")
        sys.exit(0)

    # Limit to requested count
    shas_to_query = sorted(list(missing_shas))[:args.count]
    logger.info(f"Will query {len(shas_to_query)} SIRs")

    results = []

    for idx, sha in enumerate(shas_to_query, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing SIR {idx}/{len(shas_to_query)}: {sha}")

        logger.info("Loading document from parquet...")
        doc = load_document_from_parquet(sha, str(parquet_dir))

        if not doc:
            logger.error(f"Could not find document in parquet files: {sha}")
            continue

        logger.info(f"Document: {len(doc['text_pages'])} pages, {len(doc['full_text'])} characters")

        # Build prompt: document first for prompt caching
        full_prompt = f"Consider the following document.\n\n{doc['full_text']}\n\n{args.query}"

        logger.info("Querying OpenRouter API...")
        try:
            result = query_openrouter(api_key, full_prompt, 'MCYJ Datapipeline SIR Summary Updates')

            logger.info(f"Response received:")
            logger.info(f"  Input tokens: {result['input_tokens']}")
            logger.info(f"  Output tokens: {result['output_tokens']}")
            logger.info(f"  Duration: {result['duration_ms']/1000:.2f}s")

            summary, violation = parse_sir_response(result['ai_response'])

            logger.info(f"  Summary preview: {summary[:150]}...")
            logger.info(f"  Violation: {violation}")

            if not summary or not violation:
                logger.error(f"JSON parsing failed for {sha} - skipping this document")
                logger.error(f"  Raw response: {result['ai_response']}")
                continue

            results.append({
                'sha256': sha,
                'response': summary,
                'violation': violation,
                'input_tokens': result['input_tokens'],
                'output_tokens': result['output_tokens'],
                'duration_ms': result['duration_ms']
            })

            if idx < len(shas_to_query):
                logger.info("Waiting 2 seconds before next query...")
                time.sleep(2)

        except Exception as e:
            logger.error(f"Error querying API: {e}")
            continue

    if not results:
        logger.warning("No results to save")
        sys.exit(0)

    # Append results to CSV
    logger.info(f"\n{'='*80}")
    logger.info(f"Appending {len(results)} results to {output_path}")

    file_exists = output_path.exists()

    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['sha256', 'response', 'violation',
                     'input_tokens', 'output_tokens', 'duration_ms']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerows(results)

    logger.info("Done!")

    total_input_tokens = sum(r['input_tokens'] for r in results)
    total_output_tokens = sum(r['output_tokens'] for r in results)

    logger.info(f"\nSummary:")
    logger.info(f"  New summaries added: {len(results)}")
    logger.info(f"  Total input tokens: {total_input_tokens:,}")
    logger.info(f"  Total output tokens: {total_output_tokens:,}")
    logger.info(f"  Output file: {output_path}")


if __name__ == "__main__":
    main()
