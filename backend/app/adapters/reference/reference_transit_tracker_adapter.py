"""In-Memory Reference Transit Tracker Adapter.

TEST / REFERENCE ONLY (NON-PRODUCTION).
Implements TransitTrackerPort (SPI-TRANSIT-TRACKER).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid

from app.ports.transit_tracker_port import TransitTrackerPort
from app.schemas.contracts.wave4_schemas import (
    CorrespondentTrackerHopRecord,
    DebitConfirmationRecord,
    TransitInquiryPolicyRecord,
    TransitInvestigationCandidate,
)


class InMemoryTransitTrackerAdapter(TransitTrackerPort):
    """Hermetic reference implementation of TransitTrackerPort."""

    def __init__(
        self,
        tracker_hops: Optional[Dict[str, CorrespondentTrackerHopRecord]] = None,
        debit_confirmations: Optional[Dict[str, DebitConfirmationRecord]] = None,
        policy: Optional[TransitInquiryPolicyRecord] = None,
    ):
        now = datetime.now(timezone.utc)
        self._tracker_hops: Dict[str, CorrespondentTrackerHopRecord] = tracker_hops or {
            "UETR-ST06-SUFF": CorrespondentTrackerHopRecord(
                uetr="UETR-ST06-SUFF",
                intermediary_bic="DEUTDEDDXXX",
                hop_number=2,
                hold_duration_minutes=180.0,
                hop_status="HELD_AT_INTERMEDIARY",
                is_authoritative=True,
                authority_source="SWIFT_GPI_TRACKER",
            ),
        }
        self._debit_confirmations: Dict[str, DebitConfirmationRecord] = debit_confirmations or {
            "UETR-ST06-SUFF": DebitConfirmationRecord(
                debit_reference="DBT-ST06-001",
                debtor_account="ACCT-ST06-7788",
                amount=125000.0,
                currency="EUR",
                debit_timestamp=now - timedelta(hours=4),
                is_confirmed=True,
            ),
        }
        self._policy = policy or TransitInquiryPolicyRecord(
            min_hold_minutes_for_inquiry=120.0,
            inquiry_message_type="CAMT_056",
            target_desk="CORRESPONDENT_INVESTIGATION_DESK",
        )

    def get_tracker_hop(self, uetr: str) -> Optional[CorrespondentTrackerHopRecord]:
        return self._tracker_hops.get(uetr.strip())

    def get_debit_confirmation(self, uetr: str) -> Optional[DebitConfirmationRecord]:
        return self._debit_confirmations.get(uetr.strip())

    def get_inquiry_policy(self, tenant_id: str = "DEFAULT_BANK") -> TransitInquiryPolicyRecord:
        return self._policy

    def generate_investigation_candidate(
        self, uetr: str, intermediary_bic: str, inquiry_type: str = "CAMT_056"
    ) -> TransitInvestigationCandidate:
        inquiry_ref = f"INQ-{uuid.uuid4().hex[:8].upper()}"
        return TransitInvestigationCandidate(
            investigation_id=f"INV-TRAP-{uuid.uuid4().hex[:8].upper()}",
            uetr=uetr,
            target_intermediary_bic=intermediary_bic,
            inquiry_type=inquiry_type,
            inquiry_reference=inquiry_ref,
            status=f"DISPATCH_{inquiry_type.upper().replace('.', '')}_INTERMEDIARY_INQUIRY",
            autonomous_stp_prohibited=True,
            execution_owner="BANK",
            rationale=(
                f"Funds confirmed debited and held at intermediary {intermediary_bic} beyond inquiry threshold; "
                f"structured {inquiry_type} inquiry generated under bank-owned operations review."
            ),
        )
