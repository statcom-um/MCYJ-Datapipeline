#!/usr/bin/env python3
"""Check output files for correctness."""

import pandas as pd
from pathlib import Path

print("=" * 80)
print("PARQUET FILES ANALYSIS")
print("=" * 80)

parquet_dir = Path('pdf_parsing/parquet_files')
parquet_files = sorted(parquet_dir.glob('*.parquet'))

print(f"\nTotal parquet files: {len(parquet_files)}\n")

total_records = 0
for parquet_file in parquet_files:
    df = pd.read_parquet(parquet_file)
    total_records += len(df)
    print(f"{parquet_file.name}: {len(df)} rows")

    # Check structure of first file
    if parquet_file == parquet_files[0]:
        print(f"  Columns: {list(df.columns)}")
        if len(df) > 0:
            row = df.iloc[0]
            print(f"  Sample record:")
            print(f"    sha256: {row['sha256'][:32]}...")
            print(f"    ContentDocumentId: {row.get('ContentDocumentId', 'N/A')}")
            print(f"    dateprocessed: {row.get('dateprocessed', 'N/A')}")
            print(f"    text pages: {len(row.get('text', []))}")

print(f"\nTotal records across all parquet files: {total_records}")

print("\n" + "=" * 80)
print("DATABASE FILE ANALYSIS")
print("=" * 80)

csv_path = Path('metadata_output/downloaded_files_database.csv')
if csv_path.exists():
    db = pd.read_csv(csv_path)
    print(f"\nDownloaded files database: {len(db)} rows")
    print(f"Columns: {list(db.columns)}")

    # Check for required columns
    required = ['ContentDocumentId', 'sha256']
    for col in required:
        if col in db.columns:
            print(f"  ✓ {col}: {db[col].notna().sum()} non-null values")
        else:
            print(f"  ✗ {col}: MISSING")

    if len(db) > 0:
        row = db.iloc[0]
        print(f"\n  Sample record:")
        print(f"    ContentDocumentId: {row.get('ContentDocumentId', 'N/A')}")
        print(f"    sha256: {row.get('sha256', 'N/A')[:32]}...")
        print(f"    agency_name: {row.get('agency_name', 'N/A')}")

print("\n" + "=" * 80)
print("CONSISTENCY CHECK")
print("=" * 80)

# Check if parquet content matches database
parquet_sha256_set = set()
parquet_content_ids = set()

for parquet_file in parquet_files:
    df = pd.read_parquet(parquet_file)
    parquet_sha256_set.update(df['sha256'].unique())
    if 'ContentDocumentId' in df.columns:
        parquet_content_ids.update(df['ContentDocumentId'].dropna().unique())

db_sha256_set = set(db['sha256'].dropna().unique())
db_content_ids = set(db['ContentDocumentId'].dropna().unique())

print(f"\nParquet files:")
print(f"  Unique sha256 hashes: {len(parquet_sha256_set)}")
print(f"  Unique ContentDocumentIds: {len(parquet_content_ids)}")

print(f"\nDatabase:")
print(f"  Unique sha256 hashes: {len(db_sha256_set)}")
print(f"  Unique ContentDocumentIds: {len(db_content_ids)}")

# Check overlap
sha256_overlap = len(parquet_sha256_set & db_sha256_set)
id_overlap = len(parquet_content_ids & db_content_ids)

print(f"\nOverlap:")
print(f"  sha256 hashes in both: {sha256_overlap}/{len(db_sha256_set)}")
print(f"  ContentDocumentIds in both: {id_overlap}/{len(db_content_ids)}")

if sha256_overlap == len(db_sha256_set):
    print("  ✓ All database sha256 hashes are in parquet files")
else:
    print(f"  ⚠ {len(db_sha256_set) - sha256_overlap} database hashes NOT in parquet")

print("\n" + "=" * 80)
