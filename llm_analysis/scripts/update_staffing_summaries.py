#!/usr/bin/env python3
"""
Update staffing_summaries.csv with AI-generated staffing problem classifications for SIRs.

This script:
1. Reads sir_summaries.csv to identify SIRs where violations were substantiated
2. Compares against existing rows in llm_analysis/staffing_summaries.csv
3. Queries up to N missing SIRs using OpenRouter API
4. Appends new results to llm_analysis/staffing_summaries.csv
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

from llm_utils import (
    get_api_key,
    get_existing_shas,
    get_sirs_with_violations,
    load_document_from_parquet,
    load_theming_instructions,
    parse_json_response,
    query_openrouter,
    setup_logger,
)

logger = setup_logger(__name__, 'update_staffing_summaries.log')


def build_prompt(theming_instructions: str, document_text: str) -> str:
    """Build the prompt by replacing the placeholder in the theming instructions."""
    return theming_instructions.replace('[[ report here ]]', document_text)


def parse_staffing_response(ai_response: str):
    """Parse staffing classification fields from the AI response.

    Returns:
        Dict with staffing_problem, confidence, primary_reason, and evidence fields

    Raises:
        ValueError: If JSON cannot be extracted
    """
    parsed = parse_json_response(ai_response)

    evidence = parsed.get('evidence', {})
    if not isinstance(evidence, dict):
        evidence = {}

    keywords_found = evidence.get('keywords_found', [])
    evidence_quotes = evidence.get('evidence_quotes', [])

    if not isinstance(keywords_found, list):
        keywords_found = [str(keywords_found)] if keywords_found else []
    if not isinstance(evidence_quotes, list):
        evidence_quotes = [str(evidence_quotes)] if evidence_quotes else []

    return {
        'staffing_problem': parsed.get('staffing_problem', False),
        'confidence': parsed.get('confidence', ''),
        'primary_reason': parsed.get('primary_reason', ''),
        'evidence_staffing_cited': evidence.get('staffing_cited', False),
        'evidence_keywords_found': keywords_found,
        'evidence_quotes': evidence_quotes,
        'evidence_explanation': evidence.get('explanation', ''),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update staffing_summaries.csv with AI-generated staffing problem classifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--summaries',
        default='../data/sir_summaries.csv',
        help='Path to sir_summaries.csv file (default: ../data/sir_summaries.csv)'
    )
    parser.add_argument(
        '--theming',
        default='../theming/staffing_theming.txt',
        help='Path to staffing_theming.txt file (default: ../theming/staffing_theming.txt)'
    )
    parser.add_argument(
        '--parquet-dir',
        default='../../ingestion/data/parquet_files',
        help='Directory containing parquet files (default: ../../ingestion/data/parquet_files)'
    )
    parser.add_argument(
        '--output', '-o',
        default='../data/staffing_summaries.csv',
        help='Output CSV file path (default: ../data/staffing_summaries.csv)'
    )
    parser.add_argument(
        '--max-count',
        type=int,
        default=100,
        help='Maximum number of new SIRs to query (default: 100)'
    )

    args = parser.parse_args()

    # Resolve paths relative to script directory
    script_dir = Path(__file__).parent
    summaries_path = script_dir / args.summaries
    theming_path = script_dir / args.theming
    parquet_dir = script_dir / args.parquet_dir
    output_path = script_dir / args.output

    # Get API key
    try:
        api_key = get_api_key()
        logger.info("API key loaded from environment")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Load theming instructions
    logger.info(f"Loading theming instructions from {theming_path}...")
    try:
        theming_instructions = load_theming_instructions(str(theming_path))
        logger.info(f"Loaded {len(theming_instructions)} characters of theming instructions")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Get all SIRs with violations from summaries CSV
    logger.info(f"Reading summaries from {summaries_path}...")
    try:
        all_sirs = get_sirs_with_violations(str(summaries_path))
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    if not all_sirs:
        logger.warning("No SIRs with violations found in summaries CSV")
        sys.exit(0)

    all_sir_shas = set(all_sirs)

    # Get existing staffing summary shas
    existing_shas = get_existing_shas(str(output_path), logger)

    # Find missing shas
    missing_shas = all_sir_shas - existing_shas
    logger.info(f"Found {len(missing_shas)} SIRs without staffing summaries")

    if not missing_shas:
        logger.info("All SIRs with violations already have staffing summaries!")
        sys.exit(0)

    # Limit to requested count
    shas_to_query = sorted(list(missing_shas))[:args.max_count]
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

        # Build prompt using the theming template
        prompt = build_prompt(theming_instructions, doc['full_text'])

        logger.info("Querying OpenRouter API...")
        try:
            result = query_openrouter(api_key, prompt, 'MCYJ Datapipeline Staffing Summaries')

            logger.info(f"Response received:")
            logger.info(f"  Input tokens: {result['input_tokens']}")
            logger.info(f"  Output tokens: {result['output_tokens']}")
            logger.info(f"  Cached tokens: {result['cached_tokens']}")
            logger.info(f"  Duration: {result['duration_ms']/1000:.2f}s")

            fields = parse_staffing_response(result['ai_response'])

            logger.info(f"  Staffing problem: {fields['staffing_problem']}")
            logger.info(f"  Confidence: {fields['confidence']}")
            logger.info(f"  Primary reason: {fields['primary_reason']}")
            logger.info(f"  Explanation preview: {fields['evidence_explanation'][:150]}...")

            results.append({
                'sha256': sha,
                'staffing_problem': fields['staffing_problem'],
                'confidence': fields['confidence'],
                'primary_reason': fields['primary_reason'],
                'evidence_staffing_cited': fields['evidence_staffing_cited'],
                'evidence_keywords_found': json.dumps(fields['evidence_keywords_found']),
                'evidence_quotes': json.dumps(fields['evidence_quotes']),
                'evidence_explanation': fields['evidence_explanation'],
            })

            if idx < len(shas_to_query):
                logger.info("Waiting 2 seconds before next query...")
                time.sleep(2)

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            continue

    if not results:
        logger.warning("No results to save")
        sys.exit(0)

    # Append results to CSV
    logger.info(f"\n{'='*80}")
    logger.info(f"Appending {len(results)} results to {output_path}")

    file_exists = output_path.exists()

    fieldnames = ['sha256', 'staffing_problem', 'confidence', 'primary_reason',
                  'evidence_staffing_cited', 'evidence_keywords_found',
                  'evidence_quotes', 'evidence_explanation']

    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerows(results)

    logger.info("Done!")

    staffing_counts = {}
    for r in results:
        sp = str(r['staffing_problem'])
        staffing_counts[sp] = staffing_counts.get(sp, 0) + 1

    logger.info(f"\nSummary:")
    logger.info(f"  New staffing summaries added: {len(results)}")
    logger.info(f"  Staffing problem distribution: {staffing_counts}")
    logger.info(f"  Output file: {output_path}")


if __name__ == "__main__":
    main()
