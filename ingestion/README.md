# Ingestion Pipeline

Pulls child welfare licensing documents from the Michigan LARA API, extracts text from PDFs, and produces structured CSVs.

## What it does

The pipeline runs 4 steps plus a hash integrity check:

1. **Pull agency data** — Fetches facility metadata from the API, upserts into `facility_information.csv`. Agencies that disappear from the API get `LicenseStatus='Unknown'` (rows are never deleted).

2. **Pull document lists** — Fetches the document list for every agency (one API call per agency). New documents get `download_status='pending'`. Documents no longer in the API get `download_status='unavailable'` (only when all agency calls succeed, to avoid false positives from transient errors).

3. **Download and extract** — For each pending document: fetches the PDF bytes, computes SHA256, extracts page text via pdfplumber, and writes the result to a new timestamped parquet file. Optionally saves raw PDFs with `--save-pdfs DIR`.

4. **Extract document info** — Parses parquet files to extract structured metadata (agency ID, name, dates, document type) into `document_info.csv`.

5. **Hash integrity check** — Verifies all SHA256 hashes across parquet files are unique.

## Running

```bash
# Full pipeline
python ingestion/run.py

# Limit new downloads (good for testing)
python ingestion/run.py --limit 5

# Add sleep between API calls
python ingestion/run.py --sleep 1.0

# Save raw PDFs to disk
python ingestion/run.py --save-pdfs Downloads/
```

### Individual steps

```bash
python ingestion/scripts/step1_pull_agency_data.py
python ingestion/scripts/step2_pull_document_lists.py
python ingestion/scripts/step3_pull_unprocessed_docs.py --limit 5
python ingestion/scripts/extract_document_info.py \
  --parquet-dir ingestion/data/parquet_files \
  -o ingestion/data/document_info.csv
```

## Data files

All output is in `ingestion/data/`.

### `facility_information.csv`

One row per licensed facility. Append-only (rows are never deleted).

| Column | Description |
|--------|-------------|
| `LicenseNumber` | Primary key (e.g., `CB250296641`) |
| `Address` | Full street address |
| `agencyId` | Salesforce agency ID from the API |
| `AgencyName` | Facility name |
| `AgencyType` | License type (e.g., "Child Placing Agency") |
| `City` | City |
| `County` | County |
| `LicenseEffectiveDate` | License start date |
| `LicenseeGroupOrganizationName` | Parent organization |
| `LicenseExpirationDate` | License expiration date |
| `LicenseStatus` | `Regular`, `Provisional`, `Unknown`, etc. |
| `Phone` | Phone number |
| `ZipCode` | ZIP code |

### `downloaded_files_database.csv`

One row per document known to the API. Append-only.

| Column | Description |
|--------|-------------|
| `generated_filename` | Filename derived from API metadata |
| `agency_name` | Facility name |
| `agency_id` | Salesforce agency ID |
| `FileExtension` | File type (usually `pdf`) |
| `CreatedDate` | Document creation date in the API |
| `Title` | Document title from the API |
| `ContentBodyId` | Salesforce content body ID |
| `Id` | Salesforce content version ID |
| `ContentDocumentId` | Salesforce content document ID |
| `downloaded_filename` | Local filename after download |
| `sha256` | SHA256 hash of the downloaded PDF bytes |
| `downloaded_at_utc` | Timestamp of download |
| `download_status` | `pending`, `downloaded`, `unavailable`, `error` |
| `id_match_checked` | Whether ID matching was verified |
| `last_seen_in_api_utc` | Last time this document appeared in the API |
| `unavailable_marked_at_utc` | When the document was marked unavailable |

### `document_info.csv`

Structured metadata parsed from extracted PDF text. Rebuilt from parquet files on each run.

| Column | Description |
|--------|-------------|
| `agency_id` | License number (e.g., `CA110200973`) |
| `date` | Inspection or report date |
| `agency_name` | Facility name (extracted from PDF text) |
| `document_title` | Document type (e.g., "Special Investigation Report") |
| `is_special_investigation` | `True` if document is a SIR |
| `sha256` | SHA256 hash linking to parquet source |
| `date_processed` | When the PDF was processed |

### `parquet_files/`

Timestamped parquet files (e.g., `20251103_133347_pdf_text.parquet`). Each record:

| Column | Description |
|--------|-------------|
| `sha256` | SHA256 hash of the original PDF |
| `text` | List of strings, one per page |
| `dateprocessed` | ISO 8601 timestamp |

## Scripts

| Script | Purpose |
|--------|---------|
| `step1_pull_agency_data.py` | Fetches agency metadata from the Michigan API |
| `step2_pull_document_lists.py` | Fetches per-agency document lists from the API |
| `step3_pull_unprocessed_docs.py` | Downloads pending PDFs and extracts text to parquet |
| `extract_document_info.py` | Parses parquet files into `document_info.csv` |
| `extract_pdf_text.py` | Standalone PDF text extraction utility |
| `check_unique_hashes.py` | Verifies SHA256 uniqueness across parquet files |
| `pull_agency_info_api.py` | Low-level API client for the Michigan LARA API |
| `download_pdf.py` | Low-level PDF download utility |
| `pipeline_utils.py` | Shared utilities (API URLs, request helpers) |
