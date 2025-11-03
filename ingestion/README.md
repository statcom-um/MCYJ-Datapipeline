# MCYJ Primary Document Ingestion

This directory contains scripts for downloading the current set of documents available from the [Michigan Welfare Licensing Search](https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/). The pipeline uses two separate directories:

1. **Download directory**: Persistent storage for PDF documents (accumulates over time)
2. **Run directory**: Run-specific metadata, logs, and artifacts for each round of ingestion

The scripts are idempotent - running them multiple times will only download new documents.

## Quick Start

The ingestion process consists of two simple steps:

### Step 1: Get Agency Metadata

Pull all available documents from the Michigan API:

```bash
python pull_agency_info_api.py --run-dir run_2025-11-03 --overwrite=False --verbose
```

**Output** (in `run_2025-11-03/`):
- `YYYY-MM-DD_agency_info.csv`
- `YYYY-MM-DD_all_agency_info.json`
- `YYYY-MM-DD_combined_pdf_content_details.csv`

### Step 2: Download Documents

Download PDFs directly from the content details CSV:

```bash
python download_all_pdfs.py --csv "run_2025-11-03/$(date +"%Y-%m-%d")_combined_pdf_content_details.csv" --download-dir Downloads
```

The download script automatically:
- Detects existing files by ContentDocumentId pattern (`*_{ContentDocumentId}.pdf`)
- Skips files that already exist (unless `--no-skip` is used)
- Verifies content integrity using SHA256 hashes
- Handles files with different agency names (agency renames, etc.)

**Options:**
- `--no-skip`: Re-download existing files (default: skip existing files)
- `--limit N`: Download at most N files (useful for testing)
- `--sleep SECONDS`: Delay between downloads (default: 0.1)

### Directory Structure

After running, you'll have two separate directories:

**Download directory** (`Downloads/`):
- PDF files named: `AGENCY_NAME_DOCUMENT_TITLE_YYYY-MM-DD.pdf`
- This directory persists and accumulates PDFs across multiple runs

**Run directory** (`run_2025-11-03/`):
- `YYYY-MM-DD_agency_info.csv` - Agency information
- `YYYY-MM-DD_all_agency_info.json` - Complete API response
- `YYYY-MM-DD_combined_pdf_content_details.csv` - All available documents
- This directory is specific to each run and contains all metadata/logs

## Example: Test Run

To test with only 10 downloads:

```bash
# Step 1: Get metadata
python pull_agency_info_api.py --run-dir run_test --verbose

# Step 2: Download with limit
python download_all_pdfs.py --csv "run_test/$(date +"%Y-%m-%d")_combined_pdf_content_details.csv" --download-dir Downloads --limit 10
```

## Re-running the Pipeline

The ingestion pipeline is designed to be run repeatedly:

1. **Daily updates**: Run the two-step process daily with a new run directory to pick up new documents
2. **Incremental downloads**: Only new/missing documents are downloaded
3. **Metadata refresh**: Use `--overwrite=True` with pull_agency_info_api.py to force metadata refresh

```bash
# Daily cron job example - creates a new run directory each day
# Step 1: Get metadata
0 2 * * * cd /path/to/ingestion && python pull_agency_info_api.py --run-dir "run_$(date +\%Y-\%m-\%d)"
# Step 2: Download files  
5 2 * * * cd /path/to/ingestion && python download_all_pdfs.py --csv "run_$(date +\%Y-\%m-\%d)/$(date +\%Y-\%m-\%d)_combined_pdf_content_details.csv" --download-dir Downloads
```

### Directory Best Practices

- **Download directory**: Single persistent directory (e.g., `Downloads/`) that accumulates all PDFs
- **Run directories**: Create a new one for each execution (e.g., `run_2025-11-03`, `run_2025-11-04`)
- Keep run directories for audit trails and historical metadata

## Known Limitations

The Michigan API has an important limitation regarding document versioning:

- **The API only exposes the latest version of each document**
- Historical versions of documents are NOT accessible through the API
- Each document has a unique `ContentDocumentId` (069...) used for downloading
- Documents also have a `ContentVersionId` (068...) that changes when updated
- However, the API does NOT support downloading by `ContentVersionId`
- When a document is updated, the old version becomes inaccessible

However, we believe that, in fact, the way Michigan is using their platform, there are *never* multiple versions.  In fact, we sometimes see the opposite: several identical files with different ContentDocumentId.  So for now we are operating as if ContentDocumentId is sufficient.  If we ever come across a situation where the pdf associated with a ContentDocumentId changes, we will adjust accordingly then.

**File Naming**: Files are named `{agency_name}_{ContentDocumentId}.pdf` where ContentDocumentId uniquely identifies each document (but only its latest version is downloadable).