# MCYJ Data Pipeline — Start Here

## What is this project?

This project builds a public-facing dashboard of Michigan child welfare licensing documents. It pulls inspection reports, special investigation reports (SIRs), and other licensing documents from the Michigan LARA (Licensing and Regulatory Affairs) public API, extracts text from the PDFs, and uses LLMs to generate summaries and classify violation severity.

The end product is a static website where journalists, advocates, and researchers can search facilities by name, browse their inspection histories, read AI-generated summaries of investigations, and filter by violation severity keywords. The data updates are automated via GitHub Actions — new documents are ingested weekly, analyzed by LLMs, and deployed to the live site.

## Data flow

```
Michigan LARA API
       │
       ▼
┌─────────────┐     facility_information.csv
│  ingestion/  │──▶  downloaded_files_database.csv
│  run.py      │     parquet_files/ (extracted PDF text)
│              │     document_info.csv
└──────┬───────┘
       │
       ▼
┌──────────────┐    sir_summaries.csv
│ llm_analysis/ │──▶ sir_violation_levels.csv
│ run.py        │    staffing_summaries.csv
└──────┬────────┘
       │
       ▼
┌──────────────┐    public/data/*.json
│   website/   │──▶ public/documents/*.json
│   build.sh   │    dist/ (static site)
└──────┬───────┘
       │
       ▼
  GitHub Pages / Netlify
```

## Setting up a local dev environment

### Python (ingestion + LLM analysis)

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies
uv sync

# Verify it works
uv run python ingestion/run.py --limit 1
```

### Environment variables

| Variable | Used by | Purpose |
|----------|---------|---------|
| `OPENROUTER_KEY` | `llm_analysis/` | API key for OpenRouter (LLM calls) |

### Node.js (website)

Requires Node.js 18+.

```bash
cd website
npm install
```

## Running each pipeline stage

### 1. Ingestion

Pulls documents from the Michigan API, extracts PDF text, and builds structured CSVs.

```bash
# Full pipeline (all documents)
python ingestion/run.py

# Limit to 5 new documents (good for testing)
python ingestion/run.py --limit 5
```

Output lands in `ingestion/data/`.

### 2. LLM analysis

Generates AI summaries and violation severity classifications. Requires `OPENROUTER_KEY`.

```bash
export OPENROUTER_KEY="your-key"
python llm_analysis/run.py --max-count 10
```

Output lands in `llm_analysis/data/`.

### 3. Website

Builds the static dashboard from the data CSVs.

```bash
cd website
./build.sh        # full build (data generation + Vite)
npm run dev        # dev server only (assumes data already generated)
```

Output lands in `website/dist/`.

## The SHA256 hash key

Every PDF is identified by the SHA256 hash of its raw bytes. This hash is the primary key that links a document across all CSVs:

- `downloaded_files_database.csv` → `sha256` (set when the PDF is downloaded)
- `parquet_files/*.parquet` → `sha256` (links extracted text to the original PDF)
- `document_info.csv` → `sha256` (links parsed metadata to the source)
- `sir_summaries.csv` → `sha256` (links AI summary to the source)
- `sir_violation_levels.csv` → `sha256` (links severity classification to the source)
- `staffing_summaries.csv` → `sha256` (links staffing analysis to the source)

To join any two tables, use `sha256` as the key.

## GitHub Actions

Five workflows live in `.github/workflows/`:

| Workflow | Trigger | What it does | Secrets needed |
|----------|---------|--------------|----------------|
| **Run Download Pipeline** | Manual dispatch | Runs `ingestion/run.py`, commits outputs to the triggering branch | None |
| **Run LLM** | Manual dispatch | Runs `llm_analysis/run.py`, commits outputs to the triggering branch | `OPENROUTER_KEY` |
| **Deploy to GitHub Pages** | Push to `main` or manual | Builds the website and deploys to GitHub Pages | None |
| **Check Unique SHA256 Hashes** | PRs touching parquet files | Verifies no duplicate SHA256 hashes across parquet files | None |
| **Sync Production with Main** | Manual dispatch | Force-pushes `main` to `production` branch (for Netlify) | None |

## Known gotchas

- **SSL verification**: The Michigan API calls use `verify=False` because the state API's certificate chain has historically been unreliable. This suppresses `InsecureRequestWarning`. Don't remove this without testing against the live API.

- **Append-only CSVs**: `facility_information.csv` and `downloaded_files_database.csv` never delete rows. Facilities that disappear from the API get `LicenseStatus='Unknown'`; documents that disappear get `download_status='unavailable'`. This is intentional — it preserves history.

- **Michigan API quirks**: Step 2 (document list fetching) makes one API call per agency. If any call fails, the step still completes but won't mark documents as `unavailable` (to avoid falsely flagging documents as gone due to transient errors).

- **Parquet file naming**: Each `step3` run creates a new timestamped parquet file (e.g., `20251103_133347_pdf_text.parquet`). Documents are never re-extracted — if a SHA256 already exists in any parquet file, it's skipped.

- **LLM costs**: The `llm_analysis/run.py` defaults to processing up to 100 documents per step. Use `--max-count` to control costs during testing.
