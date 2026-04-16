"""Generate ai_methodology.json from theming prompts, query templates, and model info."""
import json
import os
import re
import glob

def main():
    theming_dir = os.path.join('..', 'llm_analysis', 'theming')
    prompts = {}
    for filepath in sorted(glob.glob(os.path.join(theming_dir, '*.txt'))):
        name = os.path.splitext(os.path.basename(filepath))[0]
        with open(filepath, 'r') as f:
            prompts[name] = f.read()

    scripts_dir = os.path.join('..', 'llm_analysis', 'scripts')
    queries = {}

    sir_script = os.path.join(scripts_dir, 'update_sir_summaries.py')
    if os.path.exists(sir_script):
        with open(sir_script, 'r') as f:
            content = f.read()
        match = re.search(r'QUERY_TEXT\s*=\s*"""(.*?)"""', content, re.DOTALL)
        if match:
            queries['sir_summary'] = {
                'description': 'SIR Summary Generation',
                'prompt': match.group(1).strip()
            }

    vl_script = os.path.join(scripts_dir, 'update_violation_levels.py')
    if os.path.exists(vl_script):
        with open(vl_script, 'r') as f:
            content = f.read()
        match = re.search(r'QUERY_TEMPLATE\s*=\s*"""(.*?)"""', content, re.DOTALL)
        if match:
            queries['violation_level'] = {
                'description': 'Violation Severity Classification',
                'prompt': match.group(1).strip()
            }

    utils_path = os.path.join(scripts_dir, 'llm_utils.py')
    model = 'unknown'
    if os.path.exists(utils_path):
        with open(utils_path, 'r') as f:
            for line in f:
                if line.strip().startswith('MODEL'):
                    match = re.search(r"MODEL\s*=\s*['\"](.+?)['\"]", line)
                    if match:
                        model = match.group(1)
                    break

    os.makedirs('public/data', exist_ok=True)
    with open('public/data/ai_methodology.json', 'w') as f:
        json.dump({'model': model, 'theming_prompts': prompts, 'query_templates': queries}, f, indent=2)
    print(f'Generated ai_methodology.json with {len(prompts)} theming prompts, {len(queries)} query templates, model={model}')

if __name__ == '__main__':
    main()
