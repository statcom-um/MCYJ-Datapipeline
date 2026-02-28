# Michigan Child Welfare Licensing Dashboard

A lightweight web dashboard built with Vite + React to display Michigan child welfare agency documents and reports. Main is live [here](https://statcom-um.github.io/MCYJ-Datapipeline/) and production is live [here](https://statcom-mcyj-datapipeline.netlify.app/).

## Features

- **Agency Directory**: Browse all child welfare agencies
- **Facility Pages**: View detailed info and documents per facility
- **Document Tracking**: View detailed document reports for each agency
- **Search & Filter**: Search agencies by name or ID
- **Keyword Analysis**: Filter SIRs by violation severity keywords
- **Summary Statistics**: Dashboard showing total agencies and reports

## Development

### Prerequisites

- Node.js (v18 or later recommended)
- Python 3.11+
- pandas and pyarrow Python packages (installed via `uv sync` from the repo root)

### Local Development

1. Install dependencies:
   ```bash
   npm install
   ```

2. Generate the data files:
   ```bash
   ./build.sh
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser to `http://localhost:5173` (or the port shown in the terminal)

### Building for Production

Run the build script which:
1. Generates JSON data files from CSVs (document info, SIR summaries, violation levels, staffing summaries)
2. Applies keyword reduction to consolidate violation keywords
3. Exports parquet documents to individual JSON files
4. Builds the static website with Vite

```bash
./build.sh
```

The built files will be in the `dist/` directory.

## Netlify Deployment

The site is configured for automatic deployment on Netlify. The build process:

1. Installs Python dependencies with pip
2. Runs `generate_website_data.py` to create JSON files from CSVs
3. Runs `export_parquet_to_json.py` to export parquet documents to individual JSON files
4. Applies keyword reduction using `violation_curation_keyword_reduction.csv`
5. Builds the static site with Vite

### Keyword Reduction

The build process applies keyword reduction to consolidate similar violation keywords for better consistency. For example:
- "inadequate supervision" and "lack of supervision" → "supervision failure"
- "unsafe de-escalation" → "de-escalation failure"
- "paperwork delay" → "paperwork error"

This is configured through `../llm_analysis/data/violation_curation_keyword_reduction.csv` and is automatically applied during the build. The original data in `sir_violation_levels.csv` remains unchanged.

### Netlify Configuration

The `netlify.toml` file configures:
- Build command: `bash build.sh`
- Publish directory: `dist`
- Python version: 3.11
- SPA routing with redirects

## Data Sources

The dashboard reads data from the upstream pipeline directories:

- `../ingestion/data/document_info.csv` — structured metadata about documents
- `../ingestion/data/facility_information.csv` — facility details (name, address, license status)
- `../ingestion/data/parquet_files/` — source PDF text, exported to individual document JSON files
- `../llm_analysis/data/sir_summaries.csv` — AI-generated summaries for Special Investigation Reports
- `../llm_analysis/data/sir_violation_levels.csv` — severity levels and keywords for SIRs
- `../llm_analysis/data/staffing_summaries.csv` — AI-generated staffing report summaries
- `../llm_analysis/data/violation_curation_keyword_reduction.csv` — maps keywords to consolidated versions

## Project Structure

```
website/
├── index.html               # Main HTML file (agency directory)
├── document.html            # Document detail page
├── facilities.html          # Facility detail page
├── keywords.html            # Keywords analysis page
├── src/
│   ├── index.jsx            # Main app entry point
│   ├── document-entry.jsx   # Document page entry point
│   ├── facilities-entry.jsx # Facilities page entry point
│   ├── keywords-entry.jsx   # Keywords page entry point
│   ├── components/          # Shared React components
│   ├── pages/               # Page-level React components
│   ├── styles/              # CSS styles
│   └── utils/               # Helper utilities
├── public/
│   ├── data/                # Generated JSON data files (git-ignored)
│   └── documents/           # Individual document JSON files (git-ignored)
├── generate_website_data.py # Script to generate JSON from CSVs
├── export_parquet_to_json.py # Script to export parquet to individual JSON files
├── keyword_reduction.py     # Keyword consolidation utilities
├── build.sh                 # Build script for the entire site
├── vite.config.js           # Vite configuration
├── netlify.toml             # Netlify deployment configuration
├── package.json             # Node.js dependencies and scripts
└── README.md                # This file
```

## Scripts

- `npm run dev` — Start development server
- `npm run build` — Build for production
- `npm run preview` — Preview production build locally
- `./build.sh` — Full build pipeline (data generation + site build)

## License

ISC
