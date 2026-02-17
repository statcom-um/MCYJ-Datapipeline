#!/usr/bin/env python3
"""
Update staffing_summaries.csv with AI-generated staffing problem classifications for SIRs.

This script:
1. Reads sir_summaries.csv to identify SIRs where violations were substantiated
2. Compares against existing rows in pdf_parsing/staffing_summaries.csv
3. Queries up to N missing SIRs using OpenRouter API
4. Appends new results to pdf_parsing/staffing_summaries.csv
"""

import argparse
import ast
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
import requests

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add file handler for detailed logging
script_dir = Path(__file__).parent
log_file = script_dir / 'update_staffing_summaries.log'
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# OpenRouter API configuration
OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
MODEL = 'deepseek/deepseek-v3.2'


def get_api_key() -> str:
    """Get OpenRouter API key from environment variable."""
    api_key = os.environ.get('OPENROUTER_KEY')
    if not api_key:
        raise ValueError(
            "OPENROUTER_KEY environment variable not set. "
            "Please set it with your OpenRouter API key."
        )
    return api_key


def load_theming_instructions(theming_path: str) -> str:
    """
    Load the staffing_theming.txt file with instructions for classifying staffing problems.

    Args:
        theming_path: Path to staffing_theming.txt file

    Returns:
        Content of the theming instructions file
    """
    theming_file = Path(theming_path)
    if not theming_file.exists():
        raise FileNotFoundError(f"Theming instructions file not found: {theming_path}")

    with open(theming_file, 'r', encoding='utf-8') as f:
        return f.read()


def get_sirs_with_violations(summaries_csv: str) -> List[str]:
    """
    Get SHA256 hashes for SIRs where violations were substantiated.

    Args:
        summaries_csv: Path to sir_summaries.csv file

    Returns:
        List of SHA256 hashes for documents with violations
    """
    summaries_path = Path(summaries_csv)
    if not summaries_path.exists():
        raise FileNotFoundError(f"Summaries CSV not found: {summaries_csv}")

    df = pd.read_csv(summaries_csv)

    # Filter for SIRs where violation was substantiated
    violations = df[df['violation'] == 'y']

    logger.info(f"Found {len(violations)} SIRs with substantiated violations")

    return [str(row['sha256']) for _, row in violations.iterrows()]


def get_existing_staffing_shas(staffing_path: str) -> Set[str]:
    """
    Get SHA256 hashes that already have staffing summaries.

    Args:
        staffing_path: Path to staffing_summaries.csv

    Returns:
        Set of SHA256 hashes that already have staffing summaries
    """
    if not Path(staffing_path).exists():
        logger.info(f"No existing {staffing_path}, will create new file")
        return set()

    try:
        df = pd.read_csv(staffing_path)
        existing_shas = set(df['sha256'].unique())
        logger.info(f"Found {len(existing_shas)} existing staffing summaries")
        return existing_shas
    except Exception as e:
        logger.error(f"Error reading {staffing_path}: {e}")
        return set()


def load_document_from_parquet(sha256: str, parquet_dir: str) -> Optional[Dict]:
    """Load a document from parquet files by SHA256 hash."""
    parquet_path = Path(parquet_dir)
    parquet_files = list(parquet_path.glob("*.parquet"))

    for parquet_file in parquet_files:
        try:
            df = pd.read_parquet(parquet_file)
            matches = df[df['sha256'] == sha256]

            if not matches.empty:
                row = matches.iloc[0]

                # Parse text
                text_data = row['text']
                if isinstance(text_data, str):
                    text_stripped = text_data.strip()
                    if text_stripped.startswith('[') and text_stripped.endswith(']'):
                        text_pages = ast.literal_eval(text_data)
                    else:
                        text_pages = []
                else:
                    text_pages = list(text_data) if text_data is not None else []

                full_text = '\n\n'.join(text_pages)

                return {
                    'sha256': row['sha256'],
                    'text_pages': text_pages,
                    'full_text': full_text
                }
        except Exception as e:
            logger.debug(f"Error reading {parquet_file.name}: {e}")
            continue

    return None


def build_prompt(theming_instructions: str, document_text: str) -> str:
    """
    Build the prompt by replacing the placeholder in the theming instructions.

    Args:
        theming_instructions: Content from staffing_theming.txt
        document_text: Full document text (all pages concatenated)

    Returns:
        Complete prompt string with document text inserted
    """
    return theming_instructions.replace('[[ report here ]]', document_text)


def query_openrouter(api_key: str, prompt: str) -> Dict:
    """
    Query OpenRouter API with the constructed prompt.

    Args:
        api_key: OpenRouter API key
        prompt: Full prompt with document text inserted

    Returns:
        Dict with parsed staffing fields, token usage, and duration

    Raises:
        Exception: If API request fails or JSON response cannot be parsed
    """
    start_time = time.time()

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://github.com/jacksonloper/MCYJ-Datapipeline',
        'X-Title': 'MCYJ Datapipeline Staffing Summaries'
    }

    payload = {
        'model': MODEL,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'usage': {
            'include': True
        }
    }

    response = requests.post(
        OPENROUTER_API_URL,
        headers=headers,
        json=payload,
        timeout=180  # 3 minute timeout
    )

    end_time = time.time()
    duration_ms = int((end_time - start_time) * 1000)

    if not response.ok:
        error_msg = f"API request failed: {response.status_code} {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)

    data = response.json()

    # Extract completion ID
    completion_id = data.get('id', '')
    logger.info(f"Completion ID: {completion_id}")

    # Extract response and token usage
    ai_response = data.get('choices', [{}])[0].get('message', {}).get('content', 'No response received')
    usage = data.get('usage', {})
    input_tokens = usage.get('prompt_tokens', 0)
    output_tokens = usage.get('completion_tokens', 0)

    # Extract cached tokens information
    prompt_tokens_details = usage.get('prompt_tokens_details', {})
    cached_tokens = prompt_tokens_details.get('cached_tokens', 0) if prompt_tokens_details else 0

    # Parse JSON response
    parsed = _parse_json_response(ai_response)

    # Extract and validate fields
    staffing_problem = parsed.get('staffing_problem', False)
    confidence = parsed.get('confidence', '')
    primary_reason = parsed.get('primary_reason', '')
    evidence = parsed.get('evidence', {})

    if not isinstance(evidence, dict):
        evidence = {}

    staffing_cited = evidence.get('staffing_cited', False)
    keywords_found = evidence.get('keywords_found', [])
    evidence_quotes = evidence.get('evidence_quotes', [])
    explanation = evidence.get('explanation', '')

    # Ensure lists
    if not isinstance(keywords_found, list):
        keywords_found = [str(keywords_found)] if keywords_found else []
    if not isinstance(evidence_quotes, list):
        evidence_quotes = [str(evidence_quotes)] if evidence_quotes else []

    # Validate confidence
    if confidence not in ('high', 'medium', 'low'):
        logger.warning(f"Unexpected confidence value: {confidence}")

    return {
        'completion_id': completion_id,
        'staffing_problem': staffing_problem,
        'confidence': confidence,
        'primary_reason': primary_reason,
        'evidence_staffing_cited': staffing_cited,
        'evidence_keywords_found': keywords_found,
        'evidence_quotes': evidence_quotes,
        'evidence_explanation': explanation,
        'response': ai_response,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'cached_tokens': cached_tokens,
        'duration_ms': duration_ms
    }


def _parse_json_response(ai_response: str) -> Dict:
    """
    Parse a JSON object from the AI response string.

    Args:
        ai_response: Raw response string from the API

    Returns:
        Parsed dict

    Raises:
        Exception: If no valid JSON can be extracted
    """
    try:
        return json.loads(ai_response)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from mixed text
    start_idx = ai_response.find('{')
    if start_idx != -1:
        brace_count = 0
        for i in range(start_idx, len(ai_response)):
            if ai_response[i] == '{':
                brace_count += 1
            elif ai_response[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_str = ai_response[start_idx:i+1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
        logger.error("No valid JSON object found in response")
        raise Exception("No valid JSON object found in response")
    else:
        logger.error("No JSON object found in response")
        raise Exception("No JSON object found in response")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update staffing_summaries.csv with AI-generated staffing problem classifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--summaries',
        default='sir_summaries.csv',
        help='Path to sir_summaries.csv file (default: sir_summaries.csv)'
    )
    parser.add_argument(
        '--theming',
        default='staffing_theming.txt',
        help='Path to staffing_theming.txt file (default: staffing_theming.txt)'
    )
    parser.add_argument(
        '--parquet-dir',
        default='parquet_files',
        help='Directory containing parquet files (default: parquet_files)'
    )
    parser.add_argument(
        '--output',
        '-o',
        default='staffing_summaries.csv',
        help='Output CSV file path (default: staffing_summaries.csv)'
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
    existing_shas = get_existing_staffing_shas(str(output_path))

    # Find missing shas
    missing_shas = all_sir_shas - existing_shas
    logger.info(f"Found {len(missing_shas)} SIRs without staffing summaries")

    if not missing_shas:
        logger.info("All SIRs with violations already have staffing summaries!")
        sys.exit(0)

    # Limit to requested count
    shas_to_query = sorted(list(missing_shas))[:args.max_count]
    logger.info(f"Will query {len(shas_to_query)} SIRs")

    # Prepare results list
    results = []

    # Query each SIR
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

        # Query the API
        logger.info("Querying OpenRouter API...")
        try:
            result = query_openrouter(api_key, prompt)

            logger.info(f"Response received:")
            logger.info(f"  Input tokens: {result['input_tokens']}")
            logger.info(f"  Output tokens: {result['output_tokens']}")
            logger.info(f"  Cached tokens: {result['cached_tokens']}")
            logger.info(f"  Duration: {result['duration_ms']/1000:.2f}s")
            logger.info(f"  Staffing problem: {result['staffing_problem']}")
            logger.info(f"  Confidence: {result['confidence']}")
            logger.info(f"  Primary reason: {result['primary_reason']}")
            logger.info(f"  Explanation preview: {result['evidence_explanation'][:150]}...")

            # Store result
            results.append({
                'sha256': sha,
                'staffing_problem': result['staffing_problem'],
                'confidence': result['confidence'],
                'primary_reason': result['primary_reason'],
                'evidence_staffing_cited': result['evidence_staffing_cited'],
                'evidence_keywords_found': json.dumps(result['evidence_keywords_found']),
                'evidence_quotes': json.dumps(result['evidence_quotes']),
                'evidence_explanation': result['evidence_explanation'],
            })

            # Add a small delay to avoid rate limiting
            if idx < len(shas_to_query):
                logger.info("Waiting 2 seconds before next query...")
                time.sleep(2)

        except requests.RequestException as e:
            logger.error(f"API request error: {e}")
            continue
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

    # Print summary
    successful = len(results)
    staffing_counts = {}
    for r in results:
        sp = str(r['staffing_problem'])
        staffing_counts[sp] = staffing_counts.get(sp, 0) + 1

    logger.info(f"\nSummary:")
    logger.info(f"  New staffing summaries added: {successful}")
    logger.info(f"  Staffing problem distribution: {staffing_counts}")
    logger.info(f"  Output file: {output_path}")


if __name__ == "__main__":
    main()
