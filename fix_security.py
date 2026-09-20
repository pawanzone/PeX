with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\core\security.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("from typing import List, Dict, Optional", "from typing import Tuple, List, Dict, Optional")

with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\core\security.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated core/security.py imports")
