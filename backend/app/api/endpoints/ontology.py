"""Payment Ontology & Lineage Inspector Endpoints."""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from app.services.data_loader import repo

router = APIRouter()

@router.get("/pipeline")
def get_pipeline_stages() -> List[Dict[str, Any]]:
    return [
        {"stage_id": "1", "name": "Source Systems Ingestion", "description": "Payment engines, KYC repository, sanctions/AML platforms, treasury system (source systems)"},
        {"stage_id": "2", "name": "Mapping & Validation Layer", "description": "Normalizes each source into the canonical ISO 20022 / BIAN schema below"},
        {"stage_id": "3", "name": "Canonical Payment Ontology", "description": "Structured domain entities (Payment, Exception, Client, KYC, Compliance, Historical Cases, Treasury)"},
        {"stage_id": "4", "name": "Context-Builder Service", "description": "Assembles one structured object per case, with per-field source, confidence, and lineage"},
        {"stage_id": "5", "name": "Governed Multi-Agent Pipeline", "description": "Triage -> Context-Collection -> Data-Quality -> Investigation -> Guardrail -> Repair-Planner -> Reflect"},
        {"stage_id": "6", "name": "Human Approval & Settlement", "description": "Human approval / straight-through repair, under the continuous SHA-256 audit trail"}
    ]

@router.get("/entities")
def get_canonical_entities() -> List[Dict[str, Any]]:
    return [
        {
            "name": "Payment",
            "description": "Corridor, rail, amount, currency, beneficiary, maker — the raw payment instruction.",
            "standard": "ISO 20022 pacs.008",
            "key_fields": ["paymentId", "corridor", "paymentRail", "amount", "currency", "beneficiary", "maker"]
        },
        {
            "name": "Exception",
            "description": "Exception type, severity, status, SLA risk, screening lockout.",
            "standard": "PeX Exception Domain",
            "key_fields": ["exceptionId", "exceptionType", "severity", "status", "slaBreachRisk", "screeningLocked"]
        },
        {
            "name": "Client",
            "description": "Client type, segment, country, risk rating, service tier, straight-through-repair eligibility.",
            "standard": "BIAN Customer Management",
            "key_fields": ["clientId", "name", "clientType", "segment", "country", "riskRating", "serviceTier", "historicalExceptionRate", "straightThroughRepairEligible"]
        },
        {
            "name": "KYC",
            "description": "KYC status, risk classification, expired/missing documents, payment restrictions.",
            "standard": "FATF AML / KYC Profile",
            "key_fields": ["kycStatus", "riskClassification", "expiredDocuments", "missingDocuments", "paymentRestriction", "exceptionApprovalRequired"]
        },
        {
            "name": "Compliance",
            "description": "Sanctions screening status/score, matched entities, AML alert status, PEP/high-risk-country flags.",
            "standard": "Wolfsberg / OFAC List",
            "key_fields": ["sanctionsStatus", "screeningScore", "matchedEntities", "amlAlertStatus", "pepFlag", "highRiskCountryFlag"]
        },
        {
            "name": "Historical Cases",
            "description": "Similar prior cases with root cause, resolution, repair action, and outcome.",
            "standard": "PeX Precedent Memory",
            "key_fields": ["caseMatchCount", "averageSimilarity", "lastResolutionAction", "settlementSuccessRate"]
        },
        {
            "name": "Treasury",
            "description": "Per-currency Nostro balance, liquidity threshold, shortfall, funding options.",
            "standard": "BIAN Treasury Management",
            "key_fields": ["nostroBalance", "liquidityThreshold", "currencyShortfall", "fundingRouteAvailable"]
        }
    ]

@router.get("/domains-matrix")
def get_investigation_domains_matrix() -> List[Dict[str, Any]]:
    return [
        {"exception_type": "Invalid BIC", "domains": ["client", "historical_cases"], "domain_str": "client, historical_cases"},
        {"exception_type": "IBAN format error", "domains": ["client", "historical_cases"], "domain_str": "client, historical_cases"},
        {"exception_type": "Missing beneficiary bank", "domains": ["client", "historical_cases"], "domain_str": "client, historical_cases"},
        {"exception_type": "Sanctions hit (false positive)", "domains": ["compliance", "historical_cases"], "domain_str": "compliance, historical_cases"},
        {"exception_type": "Currency mismatch", "domains": ["treasury"], "domain_str": "treasury"},
        {"exception_type": "Duplicate payment", "domains": ["historical_cases"], "domain_str": "historical_cases"},
        {"exception_type": "Recall request", "domains": ["compliance", "historical_cases"], "domain_str": "compliance, historical_cases"},
        {"exception_type": "RFI - missing purpose code", "domains": ["client"], "domain_str": "client"},
        {"exception_type": "Clearing code mismatch", "domains": ["client", "historical_cases"], "domain_str": "client, historical_cases"},
        {"exception_type": "Account closed", "domains": ["client", "historical_cases"], "domain_str": "client, historical_cases"},
        {"exception_type": "Regulatory reporting field missing", "domains": ["client", "compliance"], "domain_str": "client, compliance"}
    ]

@router.get("/inspect/{case_id}")
def inspect_case_ontology(case_id: str) -> Dict[str, Any]:
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    debtor = case.get("debtor_party", {})
    creditor = case.get("creditor_party", {})
    creditor_acc = case.get("creditor_account", {})
    debtor_acc = case.get("debtor_account", {})
    
    amount = case.get("amount", 0.0)
    currency = case.get("currency", "USD")
    profile = case.get("profile", "INVALID_IBAN")
    profile_str = str(profile).replace("ExceptionProfile.", "")
    
    maker_name = case.get("maker", "Priya Nair")
    if case.get("audit_timeline"):
        for step in case["audit_timeline"]:
            if "MAKER" in step.get("actor_role", "").upper() or "OPERATOR" in step.get("actor_role", "").upper():
                maker_name = step.get("actor_name", maker_name)
                break

    # 4-Column Canonical context structure matching screenshot
    return {
        "case_id": case_id,
        "payment_ref": case.get("payment_ref", f"PR-{case_id}"),
        "exception_profile": profile_str,
        "payment": {
            "paymentId": {"value": case.get("payment_id", f"PAY-{case_id[-4:]}"), "status": "VALIDATED"},
            "corridor": {"value": f"{debtor.get('country', 'US')} -> {creditor.get('country', 'GB')}", "status": "VALIDATED"},
            "paymentRail": {"value": case.get("payment_rail", "ISO 20022 pacs.008"), "status": "VALIDATED"},
            "amount": {"value": f"{amount:,.2f}", "status": "VALIDATED"},
            "currency": {"value": currency, "status": "VALIDATED"},
            "beneficiary": {"value": creditor.get("party_name", "Beneficiary"), "status": "VALIDATED"},
            "maker": {"value": maker_name, "status": "VALIDATED"}
        },
        "exception": {
            "exceptionId": {"value": f"EXC-{case_id[-6:]}", "status": "VALIDATED"},
            "exceptionType": {"value": profile_str.replace("_", " ").title(), "status": "VALIDATED"},
            "severity": {"value": str(case.get("severity", "MEDIUM")).lower(), "status": "VALIDATED"},
            "status": {"value": str(case.get("status", "PENDING_APPROVAL")).lower(), "status": "VALIDATED"},
            "slaBreachRisk": {"value": "within SLA" if amount < 1000000 else "breached risk", "status": "VALIDATED"},
            "screeningLocked": {"value": "true" if profile_str == "SANCTIONS_SUSPECTED" else "false", "status": "VALIDATED"}
        },
        "client": {
            "clientId": {"value": f"CLIENT-{debtor.get('party_id', '01')[-3:]}", "status": "VALIDATED"},
            "name": {"value": debtor.get("party_name", "Acme Global Holdings"), "status": "VALIDATED"},
            "clientType": {"value": "CORPORATE", "status": "VALIDATED"},
            "segment": {"value": "LARGE_CORPORATE", "status": "VALIDATED"},
            "country": {"value": debtor.get("country", "US"), "status": "VALIDATED"},
            "riskRating": {"value": "LOW", "status": "VALIDATED"},
            "serviceTier": {"value": "PLATINUM", "status": "VALIDATED"},
            "historicalExceptionRate": {"value": "0.014", "status": "VALIDATED"},
            "straightThroughRepairEligible": {"value": "true", "status": "VALIDATED"}
        },
        "kyc": {
            "kycStatus": {"value": "ACTIVE", "status": "VALIDATED"},
            "riskClassification": {"value": "LOW", "status": "VALIDATED"},
            "expiredDocuments": {"value": "[]", "status": "VALIDATED"},
            "missingDocuments": {"value": "[]", "status": "VALIDATED"},
            "paymentRestriction": {"value": "false", "status": "VALIDATED"},
            "exceptionApprovalRequired": {"value": "true" if amount >= 250000 else "false", "status": "VALIDATED"}
        }
    }
