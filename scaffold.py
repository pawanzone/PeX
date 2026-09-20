import os
import sys

base_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app"
dirs = [
    r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\schemas",
    r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\core",
    r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\services",
    r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\api\endpoints",
    r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\tests",
    r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\scripts",
]
for d in dirs:
    os.makedirs(d, exist_ok=True)

print("Created backend directories successfully.")
