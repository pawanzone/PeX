import csv
from pathlib import Path
p = Path(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\synthetic_data\PeX_POC_Synthetic_Data_v0.1\exceptions.csv")
with open(p, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row.get('exception_id'), '| Type:', row.get('exception_type'), '| Cat:', row.get('category'), '| Sev:', row.get('severity'), '| Stage:', row.get('lifecycle_stage'))
