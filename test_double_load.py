import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from app.services.data_loader import repo

print("Initial load cases count:", len(repo.cases))
# Call load_all_data a second time to simulate server startup
repo.load_all_data()
print("After second load_all_data count:", len(repo.cases))

ingested = [c['case_id'] for c in repo.cases.values() if str(c['status']) == 'LifecycleStage.INGESTED' or c['status'] == 'INGESTED']
pending = [c['case_id'] for c in repo.cases.values() if str(c['status']) == 'LifecycleStage.PENDING_APPROVAL' or c['status'] == 'PENDING_APPROVAL']
dual_auth = [c['case_id'] for c in repo.cases.values() if str(c['status']) == 'LifecycleStage.AWAITING_SECOND_APPROVAL' or c['status'] == 'AWAITING_SECOND_APPROVAL']
settled = [c['case_id'] for c in repo.cases.values() if str(c['status']) == 'LifecycleStage.SETTLED' or c['status'] == 'SETTLED']

print("INGESTED:", len(ingested), ingested)
print("PENDING_APPROVAL:", len(pending), pending)
print("AWAITING_SECOND_APPROVAL:", len(dual_auth), dual_auth)
print("SETTLED:", len(settled), settled)
