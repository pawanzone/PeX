"""In-Memory Reference KYC Master Adapter.

TEST / REFERENCE ONLY (NON-PRODUCTION).
Implements KycMasterPort (SPI-KYC-MASTER).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid

from app.ports.kyc_master_port import KycMasterPort
from app.schemas.contracts.wave4_schemas import (
    CustomerKycRecord,
    CorporateStandingRecord,
    KycWaiverPolicyRecord,
    KycProvisionalWaiverCandidate,
)


class InMemoryKycMasterAdapter(KycMasterPort):
    """Hermetic reference implementation of KycMasterPort."""

    def __init__(
        self,
        kyc_records: Optional[Dict[str, CustomerKycRecord]] = None,
        corporate_standings: Optional[Dict[str, CorporateStandingRecord]] = None,
    ):
        now = datetime.now(timezone.utc)
        self._kyc_records: Dict[str, CustomerKycRecord] = kyc_records or {
            "CLI-CORP-001": CustomerKycRecord(
                client_id="CLI-CORP-001",
                client_name="Apex Global Corp",
                kyc_status="EXPIRED",
                last_review_date=now - timedelta(days=400),
                expiry_date=now - timedelta(days=35),
                refresh_in_progress=True,
                dispute_free_months=36,
                is_authoritative=True,
                authority_source="CLIENT_ONBOARDING_KYC_MASTER",
            ),
            "CLI-DISTRESSED-02": CustomerKycRecord(
                client_id="CLI-DISTRESSED-02",
                client_name="Distressed Holdings LLC",
                kyc_status="EXPIRED",
                last_review_date=now - timedelta(days=600),
                expiry_date=now - timedelta(days=235),
                refresh_in_progress=False,  # No documentation submitted
                dispute_free_months=4,
                is_authoritative=True,
                authority_source="CLIENT_ONBOARDING_KYC_MASTER",
            ),
        }
        self._corporate_standings: Dict[str, CorporateStandingRecord] = corporate_standings or {
            "CLI-CORP-001": CorporateStandingRecord(
                client_id="CLI-CORP-001",
                tier_rating="TIER_1_MULTINATIONAL",
                credit_score=820,
                relationship_tenure_years=8,
                has_active_sar_or_regulatory_query=False,
                clearing_corridor_risk="LOW",
            ),
            "CLI-DISTRESSED-02": CorporateStandingRecord(
                client_id="CLI-DISTRESSED-02",
                tier_rating="RETAIL",
                credit_score=520,
                relationship_tenure_years=1,
                has_active_sar_or_regulatory_query=True,  # Active SAR flag
                clearing_corridor_risk="HIGH",
            ),
        }
        self._policy = KycWaiverPolicyRecord(
            allow_provisional_waiver=True,
            max_waiver_days=30,
            max_waiver_amount=50000.0,
            min_clean_months=24,
        )

    def get_kyc_record(self, client_id: str) -> Optional[CustomerKycRecord]:
        return self._kyc_records.get(client_id.strip())

    def get_corporate_standing(self, client_id: str) -> Optional[CorporateStandingRecord]:
        return self._corporate_standings.get(client_id.strip())

    def get_waiver_policy(self, tenant_id: str = "DEFAULT_BANK") -> KycWaiverPolicyRecord:
        return self._policy

    def generate_provisional_waiver(
        self, client_id: str, waiver_days: int = 30
    ) -> KycProvisionalWaiverCandidate:
        now = datetime.now(timezone.utc)
        return KycProvisionalWaiverCandidate(
            waiver_id=f"WVR-KYC-{uuid.uuid4().hex[:8].upper()}",
            client_id=client_id,
            waiver_duration_days=waiver_days,
            expiry_timestamp=now + timedelta(days=waiver_days),
            provisional_status="WAIVER_ACTIVE_30_DAYS",
            execution_owner="BANK",
            rationale=f"Provisional 30-day KYC processing waiver granted under SOP-302 for {client_id}.",
        )
