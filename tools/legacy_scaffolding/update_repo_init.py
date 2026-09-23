with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\services\data_loader.py", "r", encoding="utf-8") as f:
    c = f.read()

# Make sure repo.load_all_data() runs on repo instance creation
if "repo = InMemoryRepository()\nrepo.load_all_data()" not in c:
    c = c.replace("repo = InMemoryRepository()", "repo = InMemoryRepository()\nrepo.load_all_data()")

with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\services\data_loader.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Updated data_loader.py to auto-load on import.")
