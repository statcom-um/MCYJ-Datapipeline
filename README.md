# MCYJ Data Pipeline

A data pipeline that ingests Michigan child welfare licensing documents from the state API, uses LLMs to generate summaries and classify violations, and publishes an interactive dashboard.

**New here?** Start with [ONBOARDING.md](ONBOARDING.md) for setup instructions, data flow, and context.

## Repository structure

```
ingestion/          Pull documents from Michigan API, extract PDF text
  data/             facility_information.csv, downloaded_files_database.csv,
                    document_info.csv, parquet_files/
  scripts/          Individual pipeline steps
  run.py            Orchestrator — runs all 4 steps + hash check

llm_analysis/       AI-powered document analysis
  data/             sir_summaries.csv, sir_violation_levels.csv,
                    staffing_summaries.csv, violation_curation_keyword_reduction.csv
  scripts/          Individual LLM steps
  theming/          Severity classification criteria
  run.py            Orchestrator — runs all 3 LLM steps

website/            Static dashboard (Vite + React)
  build.sh          Full build (data generation + Vite)
  src/              React components and pages

.github/workflows/  CI/CD automation
```

## Quick start

```bash
# Install Python dependencies
uv sync

# Run the ingestion pipeline (limit to 5 docs for testing)
python ingestion/run.py --limit 5

# Run LLM analysis (requires OPENROUTER_KEY)
export OPENROUTER_KEY="your-key"
python llm_analysis/run.py --max-count 10

# Build the website
cd website
npm install
./build.sh
```

## GitHub Actions

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| [Run Download Pipeline](.github/workflows/run-download-pipeline.yml) | Manual | Runs ingestion, commits outputs |
| [Run LLM](.github/workflows/run-llm.yml) | Manual | Runs LLM analysis, commits outputs |
| [Deploy to GitHub Pages](.github/workflows/deploy-pages.yml) | Push to `main` | Builds and deploys website |
| [Check Unique SHA256 Hashes](.github/workflows/check-unique-hashes.yml) | PRs with parquet changes | Validates no duplicate hashes |
| [Sync Production](.github/workflows/sync-production.yml) | Manual | Pushes `main` to `production` |

## Details

- [ingestion/README.md](ingestion/README.md) — Ingestion pipeline steps, data schemas, and CLI flags
- [llm_analysis/README.md](llm_analysis/README.md) — LLM analysis scripts, theming criteria, and output formats
- [website/README.md](website/README.md) — Dashboard development, build process, and deployment
