#!/usr/bin/env python3
"""
Update keyword_labels.csv with AI-generated per-keyword labels for SIRs.

This script:
1. Reads sir_summaries.csv to identify SIRs where violations were substantiated
2. Compares against existing rows in llm_analysis/keyword_labels.csv
3. Queries up to N missing SIRs using OpenRouter API
4. Appends new results to llm_analysis/keyword_labels.csv
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

logger = setup_logger(__name__, 'update_keyword_labels.log')

EXPECTED_KEYWORDS = [
    "Staffing",
    "Youth-on-youth violence",
    "Staff-on-youth violence",
    "Restraint",
    "Staff-on-youth verbal abuse",
    "Paperwork",
    "Confidentiality violation",
    "Seclusion",
    "Medical neglect",
    "Educational neglect",
    "Runaway",
    "Youth-to-youth sexual misconduct",
    "Staff-to-youth sexual misconduct",
    "Hazardous physical environment",
]
VALID_APPLIES = {'yes', 'no', 'uncertain'}
VALID_CONFIDENCE = {'high', 'medium', 'low'}


def build_prompt(theming_instructions: str, document_text: str) -> str:
    """Build the prompt by replacing the placeholder in the theming instructions."""
    return theming_instructions.replace('[[ report here ]]', document_text)


def parse_keyword_response(ai_response: str):
    """Parse and validate the keywords array from the AI response.

    Returns:
        List of keyword dicts, each with keyword, applies, confidence,
        explanation, and citations fields.

    Raises:
        ValueError: If JSON cannot be extracted or the response does not strictly
            follow the schema defined in theming/keywords.txt.
    """
    parsed = parse_json_response(ai_response)

    keywords = parsed.get('keywords')
    if not isinstance(keywords, list):
        raise ValueError(f"'keywords' field missing or not a list in response: {ai_response[:200]}")

    normalized = []
    seen_names = []
    for i, entry in enumerate(keywords):
        if not isinstance(entry, dict):
            raise ValueError(f"keywords[{i}] is not a dict: {entry!r}")

        name = entry.get('keyword')
        applies = entry.get('applies')
        confidence = entry.get('confidence')
        explanation = entry.get('explanation')
        citations = entry.get('citations')

        if not isinstance(name, str) or not name:
            raise ValueError(f"keywords[{i}].keyword missing or not a string: {entry!r}")
        if applies not in VALID_APPLIES:
            raise ValueError(f"keywords[{i}].applies={applies!r} not in {VALID_APPLIES}")
        if confidence not in VALID_CONFIDENCE:
            raise ValueError(f"keywords[{i}].confidence={confidence!r} not in {VALID_CONFIDENCE}")
        if not isinstance(explanation, str):
            raise ValueError(f"keywords[{i}].explanation missing or not a string: {entry!r}")
        if not isinstance(citations, list):
            raise ValueError(f"keywords[{i}].citations missing or not a list: {entry!r}")

        for j, citation in enumerate(citations):
            if not isinstance(citation, dict):
                raise ValueError(f"keywords[{i}].citations[{j}] is not a dict: {citation!r}")
            if not isinstance(citation.get('text'), str):
                raise ValueError(f"keywords[{i}].citations[{j}].text missing or not a string")
            if not isinstance(citation.get('location'), str):
                raise ValueError(f"keywords[{i}].citations[{j}].location missing or not a string")

        seen_names.append(name)
        normalized.append({
            'keyword': name,
            'applies': applies,
            'confidence': confidence,
            'explanation': explanation,
            'citations': citations,
        })

    expected_set = set(EXPECTED_KEYWORDS)
    seen_set = set(seen_names)
    missing = expected_set - seen_set
    extra = seen_set - expected_set
    if missing or extra:
        raise ValueError(f"keyword set mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    if len(seen_names) != len(expected_set):
        raise ValueError(f"duplicate keyword names in response: {seen_names}")

    return normalized


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update keyword_labels.csv with AI-generated per-keyword labels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--summaries',
        default='../data/sir_summaries.csv',
        help='Path to sir_summaries.csv file (default: ../data/sir_summaries.csv)'
    )
    parser.add_argument(
        '--theming',
        default='../theming/keywords.txt',
        help='Path to keywords.txt file (default: ../theming/keywords.txt)'
    )
    parser.add_argument(
        '--parquet-dir',
        default='../../ingestion/data/parquet_files',
        help='Directory containing parquet files (default: ../../ingestion/data/parquet_files)'
    )
    parser.add_argument(
        '--output', '-o',
        default='../data/keyword_labels.csv',
        help='Output CSV file path (default: ../data/keyword_labels.csv)'
    )
    parser.add_argument(
        '--max-count',
        type=int,
        default=100,
        help='Maximum number of new SIRs to query (default: 100)'
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    summaries_path = script_dir / args.summaries
    theming_path = script_dir / args.theming
    parquet_dir = script_dir / args.parquet_dir
    output_path = script_dir / args.output

    try:
        api_key = get_api_key()
        logger.info("API key loaded from environment")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info(f"Loading theming instructions from {theming_path}...")
    try:
        theming_instructions = load_theming_instructions(str(theming_path))
        logger.info(f"Loaded {len(theming_instructions)} characters of theming instructions")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

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

    existing_shas = get_existing_shas(str(output_path), logger)

    missing_shas = all_sir_shas - existing_shas
    logger.info(f"Found {len(missing_shas)} SIRs without keyword labels")

    if not missing_shas:
        logger.info("All SIRs with violations already have keyword labels!")
        sys.exit(0)

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

        prompt = build_prompt(theming_instructions, doc['full_text'])

        logger.info("Querying OpenRouter API...")
        try:
            result = query_openrouter(api_key, prompt, 'MCYJ Datapipeline Keyword Labels')

            logger.info(f"Response received:")
            logger.info(f"  Input tokens: {result['input_tokens']}")
            logger.info(f"  Output tokens: {result['output_tokens']}")
            logger.info(f"  Cached tokens: {result['cached_tokens']}")
            logger.info(f"  Duration: {result['duration_ms']/1000:.2f}s")

            keywords = parse_keyword_response(result['ai_response'])

            applies_counts = {}
            for entry in keywords:
                a = entry['applies']
                applies_counts[a] = applies_counts.get(a, 0) + 1
            logger.info(f"  Keywords labeled: {len(keywords)}")
            logger.info(f"  Applies distribution: {applies_counts}")

            results.append({
                'sha256': sha,
                'keywords': json.dumps(keywords),
                'input_tokens': result['input_tokens'],
                'output_tokens': result['output_tokens'],
                'duration_ms': result['duration_ms'],
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

    logger.info(f"\n{'='*80}")
    logger.info(f"Appending {len(results)} results to {output_path}")

    file_exists = output_path.exists()

    fieldnames = ['sha256', 'keywords', 'input_tokens', 'output_tokens', 'duration_ms']

    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerows(results)

    logger.info("Done!")

    total_input_tokens = sum(r['input_tokens'] for r in results)
    total_output_tokens = sum(r['output_tokens'] for r in results)

    logger.info(f"\nSummary:")
    logger.info(f"  New keyword-label rows added: {len(results)}")
    logger.info(f"  Total input tokens: {total_input_tokens:,}")
    logger.info(f"  Total output tokens: {total_output_tokens:,}")
    logger.info(f"  Output file: {output_path}")


if __name__ == "__main__":
    main()
