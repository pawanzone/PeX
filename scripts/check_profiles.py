import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

e2e_path = backend_path / "app" / "services" / "e2e_runner.py"
e2e_content = e2e_path.read_text(encoding="utf-8")

profile_map = {
    # Data Quality
    'INVALID_IBAN': 'DQ-01', 'INVALID_BIC': 'DQ-02', 'MISSING_BENEFICIARY_DATA': 'DQ-03',
    'MISSING_REMITTANCE_INFO': 'DQ-04', 'INVALID_ADDRESS_FORMAT': 'DQ-05', 'MISSING_PURPOSE_CODE': 'DQ-06',
    'INVALID_ACCOUNT_NUMBER': 'DQ-07', 'INVALID_ROUTING_CODE': 'DQ-08', 'BENEFICIARY_NAME_MISMATCH': 'DQ-09',
    # Processing
    'DUPLICATE_PAYMENT': 'PR-01', 'ROUTING_FAILURE': 'PR-02', 'ISO20022_VALIDATION_ERROR': 'PR-03',
    'CUTOFF_MISSED': 'PR-04', 'CORRUPTED_MESSAGE_FORMAT': 'PR-05', 'INTERMEDIARY_BANK_REJECTION': 'PR-06',
    'NETWORK_TIMEOUT': 'PR-07', 'QUEUE_PROCESSING_FAILURE': 'PR-08', 'PAYMENT_HELD_FOR_REPAIR': 'PR-09',
    # Compliance
    'SANCTIONS_SUSPECTED': 'CO-01', 'AML_ALERT': 'CO-02', 'PEP_MATCH': 'CO-03',
    'RESTRICTED_CORRIDOR': 'CO-04', 'ADVERSE_MEDIA_MATCH': 'CO-05', 'HIGH_RISK_JURISDICTION': 'CO-06',
    'REGULATORY_REPORTING_REQUIRED': 'CO-07', 'CUSTOMER_WATCHLIST_MATCH': 'CO-08',
    # Treasury
    'KYC_EXPIRED': 'TR-01', 'INSUFFICIENT_FUNDS': 'TR-02', 'NOSTRO_SHORTFALL': 'TR-03',
    'FX_RATE_UNAVAILABLE': 'TR-04', 'AUTHORIZATION_MISSING': 'TR-05', 'LIMIT_BREACH': 'TR-06',
    'LIQUIDITY_CONSTRAINT': 'TR-07', 'CREDIT_EXPOSURE_BREACH': 'TR-08',
    # Settlement
    'RETURNED_PAYMENT': 'ST-01', 'ACCOUNT_CLOSED': 'ST-02', 'BENEFICIARY_ACCOUNT_FROZEN': 'ST-03',
    'RECONCILIATION_BREAK': 'ST-04', 'SETTLEMENT_FAILURE': 'ST-05', 'FUNDS_TRAPPED_AT_CORRESPONDENT': 'ST-06',
    'UNMATCHED_CREDIT': 'ST-07'
}

implemented_e2e = []
missing_e2e = []

for name, code in profile_map.items():
    if f'profile == "{code}"' in e2e_content:
        implemented_e2e.append((name, code))
    else:
        missing_e2e.append((name, code))

print(f"Total profiles checked: {len(profile_map)}")
print(f"Profiles explicitly branched in e2e_runner: {len(implemented_e2e)}")
for p in implemented_e2e:
    print(f"   [IMPLEMENTED IN E2E] {p[1]}: {p[0]}")

print(f"\nProfiles NOT explicitly branched in e2e_runner (fallback path): {len(missing_e2e)}")
for p in missing_e2e:
    print(f"   [FALLBACK / UNBRANCHED] {p[1]}: {p[0]}")
