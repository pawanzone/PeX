import os

dist_path = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\dist\index.html"

# Let us verify if the intake section has "Submit Another" button
with open(dist_path, "r", encoding="utf-8") as f:
    content = f.read()

print("File size:", len(content))
