"""Where each key field of the Payment ontology lives in the canonical model. Curated here; every path is checked against the code
(tests/test_ontology_mapping.py), so the ontology tab cannot name a field the model does not have.

Per field: ("canonical", "Model.field") when the value is held directly, or ("derived", ["Model.field", ...]) when PeX computes it from
canonical fields. LOGICAL maps each ontology entity to its entity in the logical canonical model. SOURCE says where the data comes from
and whether the demo simulates it."""
from __future__ import annotations

from typing import Any, Dict, List

from app.schemas import canonical as cn

C, D = "canonical", "derived"

LOGICAL = {"Payment": "Payment", "Exception": "Exception", "Client": "Customer", "KYC": "Customer KYC record", "Compliance": "Screening alert",
           "Historical Cases": "Precedent", "Treasury": "Correspondent position"}

SOURCE = {
    "Payment": "Read from the payment message (pacs.008) or the bank event.",
    "Exception": "Raised by PeX when a payment stops.",
    "Client": "Bank customer system. Values shown in the demo are simulated.",
    "KYC": "Bank KYC system. Values shown in the demo are simulated.",
    "Compliance": "Bank screening system. Values shown in the demo are simulated.",
    "Historical Cases": "PeX precedent memory. Values shown in the demo are simulated.",
    "Treasury": "Bank treasury system. Values shown in the demo are simulated.",
}

FIELDS: Dict[str, Dict[str, Any]] = {
    "Payment": {
        "paymentId": (C, "CanonicalPayment.payment_id"),
        "corridor": (D, ["CanonicalParty.country"]),  # debtor country to creditor country
        "paymentRail": (C, "CanonicalPayment.payment_rail"),
        "amount": (C, "CanonicalPayment.amount"),
        "currency": (C, "CanonicalPayment.currency"),
        "beneficiary": (C, "CanonicalPayment.creditor_party"),
        "maker": (D, ["CanonicalAuditEvent.actor_id", "CanonicalAuditEvent.actor_role"]),
    },
    "Exception": {
        "exceptionId": (C, "CanonicalException.exception_id"),
        "exceptionType": (C, "CanonicalException.profile"),
        "severity": (C, "CanonicalException.severity"),
        "status": (C, "PeXCase.status"),
        "slaBreachRisk": (D, ["CanonicalException.sla_due_at", "CanonicalException.at_risk_amount"]),
        "screeningLocked": (D, ["CanonicalScreeningAlert.disposition"]),
    },
    "Client": {
        "clientId": (C, "CanonicalCustomer.client_id"), "name": (C, "CanonicalCustomer.name"), "clientType": (C, "CanonicalCustomer.client_type"),
        "segment": (C, "CanonicalCustomer.segment"), "country": (C, "CanonicalCustomer.country"), "riskRating": (C, "CanonicalCustomer.risk_rating"),
        "serviceTier": (C, "CanonicalCustomer.service_tier"), "historicalExceptionRate": (C, "CanonicalCustomer.historical_exception_rate"),
        "straightThroughRepairEligible": (C, "CanonicalCustomer.stp_repair_eligible"),
    },
    "KYC": {
        "kycStatus": (C, "CanonicalKycRecord.status"), "riskClassification": (C, "CanonicalKycRecord.risk_classification"),
        "expiredDocuments": (C, "CanonicalKycRecord.expired_documents"), "missingDocuments": (C, "CanonicalKycRecord.missing_documents"),
        "paymentRestriction": (C, "CanonicalKycRecord.payment_restriction"),
        "exceptionApprovalRequired": (D, ["CanonicalKycRecord.status", "CanonicalKycRecord.payment_restriction", "CanonicalException.at_risk_amount", "CanonicalException.severity"]),
    },
    "Compliance": {
        "sanctionsStatus": (D, ["CanonicalScreeningAlert.list_name", "CanonicalScreeningAlert.disposition"]),
        "screeningScore": (D, ["CanonicalScreeningAlert.match_score"]),
        "matchedEntities": (D, ["CanonicalScreeningAlert.matched_name"]),
        "amlAlertStatus": (D, ["CanonicalScreeningAlert.list_name", "CanonicalScreeningAlert.disposition"]),
        "pepFlag": (D, ["CanonicalScreeningAlert.list_name"]),
        "highRiskCountryFlag": (D, ["CanonicalParty.country"]),
    },
    "Historical Cases": {
        "caseMatchCount": (C, "CanonicalPrecedentSummary.case_match_count"), "averageSimilarity": (C, "CanonicalPrecedentSummary.average_similarity"),
        "lastResolutionAction": (C, "CanonicalPrecedentSummary.last_resolution_action"), "settlementSuccessRate": (C, "CanonicalPrecedentSummary.settlement_success_rate"),
    },
    "Treasury": {
        "nostroBalance": (C, "CanonicalTreasuryPosition.nostro_balance"), "liquidityThreshold": (C, "CanonicalTreasuryPosition.liquidity_threshold"),
        "currencyShortfall": (C, "CanonicalTreasuryPosition.currency_shortfall"), "fundingRouteAvailable": (C, "CanonicalTreasuryPosition.funding_route_available"),
    },
}


def exists(path: str) -> bool:
    model, _, fld = path.partition(".")
    c = getattr(cn, model, None)
    return bool(c) and (not fld or fld in c.model_fields)


def describe(entity: str, key_fields: List[str]) -> Dict[str, Any]:
    spec = FIELDS.get(entity, {})
    fields = []
    for k in key_fields:
        kind, v = spec.get(k, (None, None))
        home = v if kind == C else None
        src = v if kind == D else []
        paths = [home] if home else src
        fields.append({"name": k, "kind": kind or "unmapped", "home": home, "derived_from": src, "in_code": bool(paths) and all(exists(p) for p in paths)})
    return {"logical_entity": LOGICAL.get(entity), "source_note": SOURCE.get(entity, ""), "fields": fields}
