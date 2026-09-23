with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\scripts\run_demo.py", "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("[✓]", "[OK]")

with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\scripts\run_demo.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Updated run_demo.py to use ASCII checkmarks [OK]")
