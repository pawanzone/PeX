import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

# Let us check that we can update cases.py and data_loader.py cleanly
print("Checking backend imports...")
from app.services.data_loader import repo
print("Total loaded cases:", len(repo.cases))
