# LLM Analysis

AI-powered analysis of child welfare licensing documents using OpenRouter API. Generates summaries, classifies violation severity, and analyzes staffing reports.

## Directory Structure

```
llm_analysis/
├── data/
│   ├── sir_summaries.csv                          # AI-generated SIR summaries
│   ├── sir_violation_levels.csv                   # Severity classifications for SIRs
│   ├── staffing_summaries.csv                     # AI-generated staffing report summaries
│   └── violation_curation_keyword_reduction.csv   # Keyword consolidation mappings
├── scripts/
│   ├── update_sir_summaries.py        # Generate SIR summaries
│   ├── update_violation_levels.py     # Classify violation severity
│   ├── update_staffing_summaries.py   # Generate staffing summaries
│   └── llm_utils.py                  # Shared LLM utilities (API calls, caching)
├── theming/
│   ├── sir_theming.txt               # Criteria for SIR severity levels
│   └── staffing_theming.txt          # Criteria for staffing analysis
└── run.py                            # Orchestrator — runs all 3 steps
```

## Running

Requires `OPENROUTER_KEY` environment variable.

```bash
# Run all 3 LLM steps (default: up to 100 documents each)
export OPENROUTER_KEY="your-key"
python llm_analysis/run.py

# Limit documents processed per step
python llm_analysis/run.py --max-count 10
```

### Individual steps

```bash
python llm_analysis/scripts/update_sir_summaries.py --count 50
python llm_analysis/scripts/update_violation_levels.py --max-count 50
python llm_analysis/scripts/update_staffing_summaries.py --max-count 50
```

## Scripts

| Script | Purpose |
|--------|---------|
| `run.py` | Orchestrator — runs all 3 analysis steps in sequence |
| `update_sir_summaries.py` | Generates AI summaries for Special Investigation Reports using OpenRouter API |
| `update_violation_levels.py` | Classifies SIR violations into severity levels (low/moderate/severe) based on criteria in `theming/sir_theming.txt` |
| `update_staffing_summaries.py` | Generates AI summaries for staffing-related reports |
| `llm_utils.py` | Shared utilities for LLM API calls, prompt caching, and response parsing |

## Data Files

### `sir_summaries.csv`

AI-generated summaries for Special Investigation Reports:

| Column | Description |
|--------|-------------|
| `sha256` | Link to source document (join with `ingestion/data/document_info.csv`) |
| `response` | AI-generated summary |
| `violation` | Whether violations were substantiated (`y` or `n`) |
| API usage metrics | Tokens, duration, cost |

### `sir_violation_levels.csv`

Severity classifications for SIRs where violations were substantiated:

| Column | Description |
|--------|-------------|
| `sha256` | Link to source document |
| `level` | Severity: `low`, `moderate`, or `severe` |
| `justification` | Explanation of the classification |
| `keywords` | JSON list of relevant keywords |
| API usage metrics | Tokens, duration, cost |

### `staffing_summaries.csv`

AI-generated summaries for staffing-related reports:

| Column | Description |
|--------|-------------|
| `sha256` | Link to source document |
| `response` | AI-generated staffing summary |
| API usage metrics | Tokens, duration, cost |

### `violation_curation_keyword_reduction.csv`

Maps raw violation keywords to consolidated terms for consistency in analysis and display:

| Column | Description |
|--------|-------------|
| `original_keyword` | Raw keyword from AI classification |
| `reduced_keyword` | Normalized keyword (empty if keyword should be removed) |
| `frequency` | How often this keyword appears |

### `theming/sir_theming.txt`

Defines criteria for categorizing SIR severity:
- **Severe**: Safety/violence, restraint/seclusion, medical/mental health concerns
- **Moderate**: Administrative/rights issues, supervision failures, non-violent staff misconduct
- **Low**: Paperwork issues, non-safety policy compliance, non-hazardous facility conditions

### `theming/staffing_theming.txt`

Defines criteria for analyzing and categorizing staffing-related reports.
