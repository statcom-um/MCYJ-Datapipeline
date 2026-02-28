#!/bin/bash

# Build script for generating website data and building the site

set -e  # Exit on error

echo "==> Step 0: Installing Python dependencies..."
pip install pandas pyarrow

echo ""
echo "==> Step 1: Generating JSON data for website..."
python3 generate_website_data.py \
  --document-csv ../ingestion/data/document_info.csv \
  --sir-summaries-csv ../llm_analysis/data/sir_summaries.csv \
  --sir-violation-levels-csv ../llm_analysis/data/sir_violation_levels.csv \
  --keyword-reduction-csv ../llm_analysis/data/violation_curation_keyword_reduction.csv \
  --facility-info-csv ../ingestion/data/facility_information.csv \
  --staffing-summaries-csv ../llm_analysis/data/staffing_summaries.csv \
  --output-dir public/data

echo ""
echo "==> Step 2: Exporting parquet documents to individual JSON files..."
python3 export_parquet_to_json.py \
  --parquet-dir ../ingestion/data/parquet_files \
  --output-dir public/documents \
  --document-csv ../ingestion/data/document_info.csv \
  --sir-summaries-csv ../llm_analysis/data/sir_summaries.csv \
  --sir-violation-levels-csv ../llm_analysis/data/sir_violation_levels.csv \
  --keyword-reduction-csv ../llm_analysis/data/violation_curation_keyword_reduction.csv \
  --staffing-summaries-csv ../llm_analysis/data/staffing_summaries.csv

echo ""
echo "==> Step 3: Building website with Vite..."
npm run build

echo ""
echo "==> Build complete! Output is in dist/"
