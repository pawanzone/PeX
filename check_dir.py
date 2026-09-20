import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")
from app.config import settings
print("DATA_DIR:", settings.DATA_DIR)
import os
for f in os.listdir(settings.DATA_DIR):
    if "exception" in f.lower():
        print("Found file:", f)
        with open(settings.DATA_DIR / f, 'r') as fp:
            print("First line:", fp.readline())
