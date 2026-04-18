"""Build the per-document keyword list used by the website.

Source of truth:
  * llm_analysis/data/keyword_labels.csv  — per-keyword labels from the keywords
    LLM pipeline. A keyword is included iff applies == "yes". The "Staffing"
    keyword from this source is IGNORED here.
  * llm_analysis/data/staffing_summaries.csv — staffing LLM pipeline. The
    "Staffing" keyword is added iff staffing_problem is True AND
    confidence == "high".
"""
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional


STAFFING_KEYWORD = "Staffing"


def _load_applied_keywords(keyword_labels_csv: Optional[str]) -> Dict[str, List[str]]:
    """Load sha -> [keyword, ...] where applies == 'yes', dropping STAFFING_KEYWORD."""
    result: Dict[str, List[str]] = {}
    if not keyword_labels_csv or not Path(keyword_labels_csv).exists():
        return result

    with open(keyword_labels_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sha = row.get('sha256', '').strip()
            if not sha:
                continue
            try:
                entries = json.loads(row.get('keywords', '') or '[]')
            except (json.JSONDecodeError, ValueError):
                continue
            kws = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                name = entry.get('keyword', '')
                if entry.get('applies') == 'yes' and name and name != STAFFING_KEYWORD:
                    kws.append(name)
            result[sha] = kws
    return result


def _load_staffing_high_confidence(staffing_summaries_csv: Optional[str]) -> set:
    """Return set of shas where staffing_problem is True AND confidence == 'high'."""
    flagged = set()
    if not staffing_summaries_csv or not Path(staffing_summaries_csv).exists():
        return flagged

    with open(staffing_summaries_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sha = row.get('sha256', '').strip()
            if not sha:
                continue
            problem = row.get('staffing_problem', '').strip().lower() == 'true'
            high = row.get('confidence', '').strip().lower() == 'high'
            if problem and high:
                flagged.add(sha)
    return flagged


def load_raw_keyword_entries(keyword_labels_csv: Optional[str]) -> Dict[str, list]:
    """Load sha -> full list of per-keyword entry dicts (all 13, with explanations
    and citations). Used for the per-document detail view.
    """
    result: Dict[str, list] = {}
    if not keyword_labels_csv or not Path(keyword_labels_csv).exists():
        return result

    with open(keyword_labels_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sha = row.get('sha256', '').strip()
            if not sha:
                continue
            try:
                entries = json.loads(row.get('keywords', '') or '[]')
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(entries, list):
                result[sha] = entries
    return result


def load_effective_keywords(
    keyword_labels_csv: Optional[str],
    staffing_summaries_csv: Optional[str],
) -> Dict[str, List[str]]:
    """Return sha -> list of keyword strings that apply to the document."""
    applied = _load_applied_keywords(keyword_labels_csv)
    staffing_flagged = _load_staffing_high_confidence(staffing_summaries_csv)

    result: Dict[str, List[str]] = {}
    for sha, kws in applied.items():
        result[sha] = list(kws)
    for sha in staffing_flagged:
        result.setdefault(sha, [])
        if STAFFING_KEYWORD not in result[sha]:
            result[sha].append(STAFFING_KEYWORD)
    return result
