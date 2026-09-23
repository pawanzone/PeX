import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from app.schemas.canonical import LifecycleStage
print("Current stages:", [s.value for s in LifecycleStage])
