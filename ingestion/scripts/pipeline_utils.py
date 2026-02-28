"""Shared utilities for the ingestion pipeline."""

from datetime import datetime
from typing import Optional


def parse_created_date_to_iso(created_date: str) -> Optional[str]:
    """Parse a CreatedDate string to ISO date (YYYY-MM-DD), or None on failure."""
    if not created_date:
        return None
    created_date = created_date.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(created_date, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None
