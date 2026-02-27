"""Shared utilities for the ingestion pipeline."""

import hashlib
from datetime import datetime
from typing import Optional


def compute_sha256(file_path: str, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA256 hash of a file."""
    digest = hashlib.sha256()
    with open(file_path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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
