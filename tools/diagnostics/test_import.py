import sys
import os
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from app.services.data_loader import repo
from app.services.canonicalizer import canonicalizer
from app.services.profile_engine import get_profile_spec
from app.services.evidence_planner import evidence_planner
from app.services.context_builder import context_builder
from app.services.model_gateway import model_gateway
from app.services.decision_engine import decision_engine
from app.services.approval_engine import approval_engine
from app.services.action_executor import action_executor
from app.services.audit_service import audit_service

print("Testing loading synthetic data...")
repo.load_all_data()

print(f"Total cases in store: {len(repo.cases)}")
print(f"Total beneficiaries: {len(repo.beneficiaries)}")
print(f"Total accounts: {len(repo.accounts)}")
print(f"Total policies: {len(repo.policies)}")
print(f"Total historical cases: {len(repo.historical_cases)}")
print("Services validation test passed!")
