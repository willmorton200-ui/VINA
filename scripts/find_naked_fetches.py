import re

for fn in ['static/scanner.js', 'static/scanner.html']:
    with open(fn, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f, 1):
            if 'fetch(' in line and not ('apiUrl' in line or 'getHubApiBase' in line):
                print(f"{fn}:{idx}: {line.strip()}")
