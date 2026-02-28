"""Shared utilities for LLM analysis scripts."""

import ast
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
import requests


# OpenRouter API configuration
OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
MODEL = 'deepseek/deepseek-v3.2'


def setup_logger(name: str, log_filename: str) -> logging.Logger:
    """Set up a logger with console and file handlers.

    Args:
        name: Logger name (typically __name__ from the calling module)
        log_filename: Filename for the log file, placed in the scripts directory

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only add handlers if the logger doesn't already have them
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        script_dir = Path(__file__).parent
        log_file = script_dir / log_filename
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)

    return logger


def get_api_key() -> str:
    """Get OpenRouter API key from environment variable."""
    api_key = os.environ.get('OPENROUTER_KEY')
    if not api_key:
        raise ValueError(
            "OPENROUTER_KEY environment variable not set. "
            "Please set it with your OpenRouter API key."
        )
    return api_key


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
        except Exception:
            continue

    return None


def parse_json_response(ai_response: str) -> Dict:
    """Parse a JSON object from an AI response string.

    Handles cases where the response contains extra text around the JSON.

    Args:
        ai_response: Raw response string from the API

    Returns:
        Parsed dict

    Raises:
        ValueError: If no valid JSON can be extracted
    """
    try:
        return json.loads(ai_response)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from mixed text by matching braces
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

    raise ValueError(f"No valid JSON object found in response: {ai_response[:200]}")


def get_sirs_with_violations(summaries_csv: str) -> List[str]:
    """Get SHA256 hashes for SIRs where violations were substantiated.

    Args:
        summaries_csv: Path to sir_summaries.csv file

    Returns:
        List of SHA256 hashes for documents with violations
    """
    summaries_path = Path(summaries_csv)
    if not summaries_path.exists():
        raise FileNotFoundError(f"Summaries CSV not found: {summaries_csv}")

    df = pd.read_csv(summaries_csv)
    violations = df[df['violation'] == 'y']
    return [str(row['sha256']) for _, row in violations.iterrows()]


def load_theming_instructions(theming_path: str) -> str:
    """Load a theming instructions file.

    Args:
        theming_path: Path to the theming .txt file

    Returns:
        Content of the theming instructions file
    """
    theming_file = Path(theming_path)
    if not theming_file.exists():
        raise FileNotFoundError(f"Theming instructions file not found: {theming_path}")

    with open(theming_file, 'r', encoding='utf-8') as f:
        return f.read()


def get_existing_shas(csv_path: str, logger: logging.Logger) -> Set[str]:
    """Get SHA256 hashes already present in an output CSV.

    Args:
        csv_path: Path to the CSV file
        logger: Logger instance

    Returns:
        Set of SHA256 hashes found in the file
    """
    if not Path(csv_path).exists():
        logger.info(f"No existing {csv_path}, will create new file")
        return set()

    try:
        df = pd.read_csv(csv_path)
        existing_shas = set(df['sha256'].unique())
        logger.info(f"Found {len(existing_shas)} existing records in {csv_path}")
        return existing_shas
    except Exception as e:
        logger.error(f"Error reading {csv_path}: {e}")
        return set()


def query_openrouter(api_key: str, prompt: str, title: str = 'MCYJ Datapipeline') -> Dict:
    """Send a prompt to OpenRouter and return the parsed response.

    Args:
        api_key: OpenRouter API key
        prompt: Full prompt to send
        title: X-Title header for the request

    Returns:
        Dict with completion_id, ai_response, input_tokens, output_tokens,
        cached_tokens, and duration_ms
    """
    import time
    start_time = time.time()

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://github.com/jacksonloper/MCYJ-Datapipeline',
        'X-Title': title
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
        timeout=180
    )

    end_time = time.time()
    duration_ms = int((end_time - start_time) * 1000)

    if not response.ok:
        raise Exception(f"API request failed: {response.status_code} {response.text}")

    data = response.json()

    completion_id = data.get('id', '')
    ai_response = data.get('choices', [{}])[0].get('message', {}).get('content', 'No response received')
    usage = data.get('usage', {})
    input_tokens = usage.get('prompt_tokens', 0)
    output_tokens = usage.get('completion_tokens', 0)

    prompt_tokens_details = usage.get('prompt_tokens_details', {})
    cached_tokens = prompt_tokens_details.get('cached_tokens', 0) if prompt_tokens_details else 0

    return {
        'completion_id': completion_id,
        'ai_response': ai_response,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'cached_tokens': cached_tokens,
        'duration_ms': duration_ms
    }
