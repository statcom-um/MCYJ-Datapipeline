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
  --gazetteer-zip ../public/2025_Gaz_zcta_national.zip \
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
echo "==> Step 3: Generating AI methodology data from theming prompts..."
python3 -c "
import json, os, glob

theming_dir = os.path.join('..', 'llm_analysis', 'theming')
prompts = {}
for filepath in sorted(glob.glob(os.path.join(theming_dir, '*.txt'))):
    name = os.path.splitext(os.path.basename(filepath))[0]
    with open(filepath, 'r') as f:
        prompts[name] = f.read()

# Read the LLM query prompts from analysis scripts
scripts_dir = os.path.join('..', 'llm_analysis', 'scripts')
queries = {}

# SIR summary query
sir_script = os.path.join(scripts_dir, 'update_sir_summaries.py')
if os.path.exists(sir_script):
    with open(sir_script, 'r') as f:
        content = f.read()
    # Extract QUERY_TEXT
    import re
    match = re.search(r'QUERY_TEXT\s*=\s*\"\"\"(.*?)\"\"\"', content, re.DOTALL)
    if match:
        queries['sir_summary'] = {
            'description': 'SIR Summary Generation',
            'prompt': match.group(1).strip()
        }

# Violation level query
vl_script = os.path.join(scripts_dir, 'update_violation_levels.py')
if os.path.exists(vl_script):
    with open(vl_script, 'r') as f:
        content = f.read()
    match = re.search(r'QUERY_TEMPLATE\s*=\s*\"\"\"(.*?)\"\"\"', content, re.DOTALL)
    if match:
        queries['violation_level'] = {
            'description': 'Violation Severity Classification',
            'prompt': match.group(1).strip()
        }

# Read model info from llm_utils.py
utils_path = os.path.join(scripts_dir, 'llm_utils.py')
model = 'unknown'
if os.path.exists(utils_path):
    with open(utils_path, 'r') as f:
        for line in f:
            if line.strip().startswith('MODEL'):
                match = re.search(r\"MODEL\s*=\s*['\\\"](.+?)['\\\"]\", line)
                if match:
                    model = match.group(1)
                break

output = {
    'model': model,
    'theming_prompts': prompts,
    'query_templates': queries
}

os.makedirs('public/data', exist_ok=True)
with open('public/data/ai_methodology.json', 'w') as f:
    json.dump(output, f, indent=2)
print(f'Generated ai_methodology.json with {len(prompts)} theming prompts, {len(queries)} query templates, model={model}')
"

echo ""
echo "==> Step 4: Building website with Vite..."
npm run build

echo ""
echo "==> Build complete! Output is in dist/"
