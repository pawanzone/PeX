import os

comp_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\src\components"
os.makedirs(os.path.join(comp_dir, "Dashboard"), exist_ok=True)
os.makedirs(os.path.join(comp_dir, "Intake"), exist_ok=True)
os.makedirs(os.path.join(comp_dir, "Worklist"), exist_ok=True)
os.makedirs(os.path.join(comp_dir, "Approvals"), exist_ok=True)
os.makedirs(os.path.join(comp_dir, "Investigations"), exist_ok=True)
os.makedirs(os.path.join(comp_dir, "Analytics"), exist_ok=True)
os.makedirs(os.path.join(comp_dir, "SwiftIso"), exist_ok=True)
os.makedirs(os.path.join(comp_dir, "Governance"), exist_ok=True)
os.makedirs(os.path.join(comp_dir, "Ontology"), exist_ok=True)
os.makedirs(os.path.join(comp_dir, "Copilot"), exist_ok=True)

print("Folders verified.")
