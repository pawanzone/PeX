"""Canonical E2E JSON Fixtures for Wave 0B (Scenarios 13–18).

Expands the test matrix to cover dynamic configuration, multi-mode acquisition (Modes 1, 2, 3, 4),
HITL closed loops, multi-tenant isolation, and fail-closed governance.
"""
from typing import Dict, Any

SCENARIOS_WAVE0B: Dict[str, Dict[str, Any]] = {
    # SCENARIO 13: High-Value Wire with Tier 1 Account Statement (Mode 1 + Dynamic Threshold)
    "SCENARIO_13_HIGH_VALUE_WIRE_TIER1_STMT": {
        "exception_id": "EX-W0B-SC13-001",
        "tenant_id": "BNP_PARIBAS",
        "profile_id": "DQ-01",
        "domain": "DATA_QUALITY",
        "error_code": "INVALID_IBAN_CHECKSUM",
        "error_message": "Inbound creditor IBAN check digit calculation failed MOD-97",
        "payment_info": {
            "payment_id": "PMT-W0B-13001",
            "uetr": "9f1e2d3c-4b5a-6789-0123-abcdef130001",
            "amount": 250000.00,
            "currency": "EUR",
            "clearing_rail": "TARGET2",
            "value_date": "2026-10-08",
            "debtor_name": "AIRBUS SAS",
            "debtor_account": "FR7630006000011234567890189",
            "debtor_agent_bic": "BNPAFRPPXXX",
            "creditor_name": "ROLLS ROYCE HOLDINGS PLC",
            "creditor_account": "GB82WEST12345612345670", # corrupted
            "creditor_agent_bic": "WESTGB2LXXX",
            "remittance_info": "INVOICE RR-2026-OCT-8891 AEROSPACE ENGINES",
            "charge_bearer": "SHA"
        },
        "bank_supplied_evidence": {
            "core_dda_account": {"account_number": "12345678", "sort_code": "123456", "status": "ACTIVE"},
            "routing_directory": {"bic": "WESTGB2LXXX", "clearing_code": "123456", "valid": True},
            "account_statement": {"statement_id": "STMT-2026-10", "verified_iban": "GB82WEST12345612345678", "currency": "EUR"}
        },
        "external_authoritative_evidence": {},
        "derived_evidence": {
            "verified_iban": "GB82WEST12345612345678"
        },
        "historical_evidence": {},
        "bank_policy_overrides": {
            "policy_id": "POL-BNP-HIGH-VAL",
            "policy_version": "v1.0.0",
            "environment": "TEST_ONLY",
            "risk_thresholds": {
                "max_autonomous_stp_amount": 500000.0,
                "max_batch_fast_lane_amount": 1000000.0,
                "dual_auth_mandatory_threshold": 5000000.0,
                "allowed_currencies": ["USD", "EUR", "GBP"]
            },
            "auto_stp_enabled_profiles": ["DQ-01", "INVALID_IBAN"]
        },
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    },

    # SCENARIO 14: Cross-Border Currency Corridor with Regulatory Certificate (Mode 3 Push)
    "SCENARIO_14_CORRIDOR_REGULATORY_CERT_PUSH": {
        "exception_id": "EX-W0B-SC14-001",
        "tenant_id": "BANCO_SANTANDER",
        "profile_id": "DQ-06",
        "domain": "DATA_QUALITY",
        "error_code": "MISSING_REGULATORY_REPORTING_CODE",
        "error_message": "Cross-border EUR to BRL corridor requires central bank foreign exchange certificate",
        "payment_info": {
            "payment_id": "PMT-W0B-14001",
            "uetr": "9f1e2d3c-4b5a-6789-0123-abcdef140001",
            "amount": 75000.00,
            "currency": "EUR",
            "clearing_rail": "SWIFT_CBPR+",
            "value_date": "2026-10-08",
            "debtor_name": "IBERDROLA SA",
            "debtor_account": "ES9121000418450200051332",
            "debtor_agent_bic": "SANUESMMXXX",
            "creditor_name": "VALE DO RIO DOCE SA",
            "creditor_account": "BR9300000000012345678901234",
            "creditor_agent_bic": "BRAZBRRJXXX",
            "remittance_info": "EQUIPMENT SUPPLY BRAZIL RENEWABLE PROJECT",
            "charge_bearer": "OUR"
        },
        "bank_supplied_evidence": {
            "core_dda_account": {"account_id": "ACC-VALE-01", "status": "ACTIVE"}
        },
        "external_authoritative_evidence": {},
        "derived_evidence": {},
        "historical_evidence": {},
        "bank_policy_overrides": {
            "policy_id": "POL-SANTANDER-CORRIDOR",
            "policy_version": "v1.0.0",
            "environment": "TEST_ONLY",
            "risk_thresholds": {
                "max_autonomous_stp_amount": 100000.0,
                "max_batch_fast_lane_amount": 250000.0,
                "dual_auth_mandatory_threshold": 1000000.0,
                "allowed_currencies": ["USD", "EUR", "GBP", "BRL"]
            },
            "auto_stp_enabled_profiles": ["DQ-06", "CROSS_BORDER_REMITTANCE"]
        },
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    },

    # SCENARIO 15: Operator IBAN Correction via HITL Closed-Loop (Mode 4 Interactive)
    "SCENARIO_15_OPERATOR_IBAN_CORRECTION_HITL": {
        "exception_id": "EX-W0B-SC15-001",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "DQ-08",
        "domain": "DATA_QUALITY",
        "error_code": "AMBIGUOUS_ROUTING_CODE",
        "error_message": "Multiple valid Fedwire transit ABA routing codes detected for receiver",
        "payment_info": {
            "payment_id": "PMT-W0B-15001",
            "uetr": "9f1e2d3c-4b5a-6789-0123-abcdef150001",
            "amount": 20000.00, # within default $25,000 batch fast lane limit
            "currency": "USD",
            "clearing_rail": "FEDWIRE",
            "value_date": "2026-10-08",
            "debtor_name": "TESLA INC",
            "debtor_account": "1122334455",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "PANASONIC ENERGY CORP",
            "creditor_account": "9988776655",
            "creditor_agent_bic": "BOTKUS33XXX",
            "remittance_info": "BATTERY CELLS SUPPLY Q4-2026",
            "charge_bearer": "SHA"
        },
        "bank_supplied_evidence": {
            "fedline_routing_directory": {"valid": True},
            "routing_syntax_master": {"format": "FEDWIRE_ABA"},
            "inbound_routing_code": "021000020",
            "ambiguous_routing_matches": True
        },
        "external_authoritative_evidence": {},
        "derived_evidence": {},
        "historical_evidence": {},
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    },

    # SCENARIO 16: Automated Core Banking Query (Mode 2 Progressive Fallback)
    "SCENARIO_16_AUTOMATED_CORE_BANKING_MODE2": {
        "exception_id": "EX-W0B-SC16-001",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "PR-01",
        "domain": "PROCESSING",
        "error_code": "DUPLICATE_PAYMENT_DETECTED",
        "error_message": "Identical amount and creditor detected within 24-hour settlement window",
        "payment_info": {
            "payment_id": "PMT-W0B-16001",
            "uetr": "9f1e2d3c-4b5a-6789-0123-abcdef160001",
            "amount": 18500.00,
            "currency": "USD",
            "clearing_rail": "FEDWIRE",
            "value_date": "2026-10-08",
            "debtor_name": "MICROSOFT CORP",
            "debtor_account": "7788990011",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "DATADOG INC",
            "creditor_account": "3344556677",
            "creditor_agent_bic": "WFBIUS6SXXX",
            "remittance_info": "CLOUD MONITORING SERVICE OCTOBER 2026",
            "charge_bearer": "SHA"
        },
        "bank_supplied_evidence": {
            "historical_payment_journal": {"prior_match_found": True},
            "settlement_ledger": {"settled": True},
            "original_payment_id": "PMT-ORIG-SETTLED-7711"
        },
        "external_authoritative_evidence": {},
        "derived_evidence": {},
        "historical_evidence": {},
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    },

    # SCENARIO 17: Multi-Tenant Config Isolation & Inheritance
    "SCENARIO_17_MULTI_TENANT_ISOLATION": {
        "exception_id": "EX-W0B-SC17-001",
        "tenant_id": "TENANT_ALPHA",
        "profile_id": "DQ-01",
        "domain": "DATA_QUALITY",
        "error_code": "INVALID_IBAN_SYNTAX",
        "error_message": "Creditor IBAN length check failed",
        "payment_info": {
            "payment_id": "PMT-W0B-17001",
            "uetr": "9f1e2d3c-4b5a-6789-0123-abcdef170001",
            "amount": 15000.00,
            "currency": "GBP",
            "clearing_rail": "CHAPS",
            "value_date": "2026-10-08",
            "debtor_name": "BARCLAYS PLC",
            "debtor_account": "GB29BARC20000012345678",
            "debtor_agent_bic": "BARCGB22XXX",
            "creditor_name": "VODAFONE GROUP",
            "creditor_account": "GB82WEST12345612345670", # Corrupted
            "creditor_agent_bic": "WESTGB2LXXX",
            "remittance_info": "TELECOM INFRASTRUCTURE BILLING",
            "charge_bearer": "SHA"
        },
        "bank_supplied_evidence": {
            "core_dda_account": {"account": "12345678", "status": "ACTIVE"},
            "routing_directory": {"bic": "WESTGB2LXXX", "valid": True}
        },
        "external_authoritative_evidence": {},
        "derived_evidence": {
            "verified_iban": "GB82WEST12345612345678"
        },
        "historical_evidence": {},
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    },

    # SCENARIO 18: Governance Compiler Fail-Closed Rejection
    "SCENARIO_18_GOVERNANCE_COMPILER_FAIL_CLOSED": {
        "exception_id": "EX-W0B-SC18-001",
        "tenant_id": "MALICIOUS_OR_ERRONEOUS_BANK",
        "profile_id": "CO-04",
        "domain": "COMPLIANCE",
        "error_code": "SANCTIONS_REGULATORY_HOLD",
        "error_message": "Attempting to bypass sanctions screening rule via custom configuration",
        "payment_info": {
            "payment_id": "PMT-W0B-18001",
            "uetr": "9f1e2d3c-4b5a-6789-0123-abcdef180001",
            "amount": 1000000.00,
            "currency": "USD",
            "clearing_rail": "FEDWIRE",
            "value_date": "2026-10-08",
            "debtor_name": "UNKNOWN FOREIGN ENTITY",
            "debtor_account": "999888777",
            "debtor_agent_bic": "UNKNUS33XXX",
            "creditor_name": "DESIGNATED SANCTIONED ENTITY",
            "creditor_account": "111222333",
            "creditor_agent_bic": "CHASUS33XXX",
            "remittance_info": "UNVERIFIED COMMERCIAL TRADE",
            "charge_bearer": "OUR"
        },
        "bank_supplied_evidence": {},
        "external_authoritative_evidence": {},
        "derived_evidence": {},
        "historical_evidence": {},
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    }
}
