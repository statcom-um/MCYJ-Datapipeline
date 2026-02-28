#!/usr/bin/env python3
"""
Update sir_violation_levels.csv with AI-generated violation severity levels for SIRs.

This script:
1. Reads sir_summaries.csv to identify SIRs where violations were substantiated
2. Compares against existing levels in llm_analysis/sir_violation_levels.csv
3. Queries up to N missing SIRs using OpenRouter API
4. Appends new results to llm_analysis/sir_violation_levels.csv
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

logger = setup_logger(__name__, 'update_violation_levels.log')

# Query template for violation level classification
# Document comes first with a common prefix to enable prompt caching
QUERY_TEMPLATE = """Consider the following document.

{document_text}

Based on the categorization instructions below, please analyze this Special Investigation Report and determine the severity level of the actual violations that were substantiated (ignore any unsubstantiated allegations).

Categorization Instructions:
{theming_instructions}

Please respond with a JSON object containing exactly three fields:

1. "level": Either "low", "moderate", or "severe" based on the categorization instructions above
2. "justification": A brief explanation of why you chose this level, referencing the specific violations found and how they align with the categorization criteria
3. "keywords": A list of keywords pertinent to the reasons why this document is labelled with this violation level (e.g., ["physical assault", "inadequate supervision"], ["medication error"], ["paperwork delay", "documentation"])

Return ONLY the JSON object, no other text. Format:
{{"level": "...", "justification": "...", "keywords": [...]}}"""


def normalize_violation_level(level: str) -> str:
    """Normalize a violation level string to one of: 'low', 'moderate', 'severe', or empty."""
    level = level.lower()
    if level in ['low', 'moderate', 'severe']:
        return level
    if 'low' in level:
        return 'low'
    elif 'moderate' in level or 'medium' in level:
        return 'moderate'
    elif 'severe' in level or 'high' in level:
        return 'severe'
    return ''


def parse_violation_response(ai_response: str):
    """Parse level, justification, and keywords from the AI response.

    Returns:
        Tuple of (level, justification, keywords)

    Raises:
        ValueError: If parsing or validation fails
    """
    parsed = parse_json_response(ai_response)

    level = normalize_violation_level(parsed.get('level', ''))
    justification = parsed.get('justification', '')
    keywords = parsed.get('keywords', [])

    if keywords is None:
        keywords = []
    elif not isinstance(keywords, list):
        keywords = [str(keywords)] if keywords else []

    if not level:
        raise ValueError(f"Could not extract valid level from response: {ai_response[:200]}")

    return level, justification, keywords


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update sir_violation_levels.csv with AI-generated violation severity levels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--summaries',
        default='../data/sir_summaries.csv',
        help='Path to sir_summaries.csv file (default: ../data/sir_summaries.csv)'
    )
    parser.add_argument(
        '--theming',
        default='../theming/sir_theming.txt',
        help='Path to sir_theming.txt file (default: ../theming/sir_theming.txt)'
    )
    parser.add_argument(
        '--parquet-dir',
        default='../../ingestion/data/parquet_files',
        help='Directory containing parquet files (default: ../../ingestion/data/parquet_files)'
    )
    parser.add_argument(
        '--output', '-o',
        default='../data/sir_violation_levels.csv',
        help='Output CSV file path (default: ../data/sir_violation_levels.csv)'
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

    # Get existing level shas
    existing_shas = get_existing_shas(str(output_path), logger)

    # Find missing shas
    missing_shas = all_sir_shas - existing_shas
    logger.info(f"Found {len(missing_shas)} SIRs without violation levels")

    if not missing_shas:
        logger.info("All SIRs with violations already have levels!")
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

        # Build prompt
        full_prompt = QUERY_TEMPLATE.format(
            theming_instructions=theming_instructions,
            document_text=doc['full_text']
        )

        logger.info("Querying OpenRouter API...")
        try:
            result = query_openrouter(api_key, full_prompt, 'MCYJ Datapipeline SIR Violation Level Updates')

            logger.info(f"Response received:")
            logger.info(f"  Input tokens: {result['input_tokens']}")
            logger.info(f"  Output tokens: {result['output_tokens']}")
            logger.info(f"  Cached tokens: {result['cached_tokens']}")
            logger.info(f"  Duration: {result['duration_ms']/1000:.2f}s")

            level, justification, keywords = parse_violation_response(result['ai_response'])

            logger.info(f"  Level: {level}")
            logger.info(f"  Keywords: {keywords}")
            logger.info(f"  Justification preview: {justification[:150]}...")

            results.append({
                'sha256': sha,
                'level': level,
                'justification': justification,
                'keywords': json.dumps(keywords),
                'input_tokens': result['input_tokens'],
                'output_tokens': result['output_tokens'],
                'duration_ms': result['duration_ms']
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

    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['sha256', 'level', 'justification', 'keywords',
                     'input_tokens', 'output_tokens', 'duration_ms']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerows(results)

    logger.info("Done!")

    total_input_tokens = sum(r['input_tokens'] for r in results)
    total_output_tokens = sum(r['output_tokens'] for r in results)
    level_counts = {}
    for r in results:
        level_counts[r['level']] = level_counts.get(r['level'], 0) + 1

    logger.info(f"\nSummary:")
    logger.info(f"  New levels added: {len(results)}")
    logger.info(f"  Level distribution: {level_counts}")
    logger.info(f"  Total input tokens: {total_input_tokens:,}")
    logger.info(f"  Total output tokens: {total_output_tokens:,}")
    logger.info(f"  Output file: {output_path}")


if __name__ == "__main__":
    main()
