with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\api\endpoints\copilot.py", "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace("from typing import List, Dict, Any", "from typing import List, Dict, Any, Optional")
with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\api\endpoints\copilot.py", "w", encoding="utf-8") as f:
    f.write(c)
print("Updated copilot.py imports")
