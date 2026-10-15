"""In-Memory Reference Corporate Mandate Adapter.

TEST / REFERENCE ONLY (NON-PRODUCTION).
Implements CorporateMandatePort (SPI-CORPORATE-MANDATE).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.corporate_mandate_port import CorporateMandatePort
from app.schemas.contracts.wave4_schemas import (
    CorporateMandateRecord,
    SecondarySignatoryRecord,
    PortalCallbackRecord,
    CorporateDualAuthorizationCandidate,
)


class InMemoryCorporateMandateAdapter(CorporateMandatePort):
    """Hermetic reference implementation of CorporateMandatePort."""

    def __init__(
        self,
        mandates: Optional[Dict[str, CorporateMandateRecord]] = None,
        signatories: Optional[Dict[str, SecondarySignatoryRecord]] = None,
        callbacks: Optional[Dict[str, PortalCallbackRecord]] = None,
    ):
        self._mandates: Dict[str, CorporateMandateRecord] = mandates or {
            "ACCT-CORP-USD-001": CorporateMandateRecord(
                mandate_id="MAND-APEX-01",
                debtor_account="ACCT-CORP-USD-001",
                dual_auth_threshold=250000.0,
                required_signatory_count=2,
                allowed_signer_classes=["CLASS_A", "CLASS_B"],
                is_authoritative=True,
                authority_source="CORPORATE_MANDATE_SYSTEM",
            ),
            "ACCT-UNAPPROVED-USD-002": CorporateMandateRecord(
                mandate_id="MAND-SOLO-02",
                debtor_account="ACCT-UNAPPROVED-USD-002",
                dual_auth_threshold=100000.0,
                required_signatory_count=2,
                allowed_signer_classes=["CLASS_A"],
                is_authoritative=True,
                authority_source="CORPORATE_MANDATE_SYSTEM",
            ),
        }
        self._signatories: Dict[str, SecondarySignatoryRecord] = signatories or {
            "ACCT-CORP-USD-001": SecondarySignatoryRecord(
                signatory_id="SIG-CFO-001",
                signatory_name="Jane Doe (CFO)",
                signer_class="CLASS_A",
                signature_status="APPROVED",
                mfa_verified=True,
                digital_token_reference="TOK-MFA-883A92",
            ),
            "ACCT-UNAPPROVED-USD-002": SecondarySignatoryRecord(
                signatory_id="SIG-PENDING-002",
                signatory_name="John Smith (Treasurer)",
                signer_class="CLASS_A",
                signature_status="PENDING",  # Awaiting signature
                mfa_verified=False,
                digital_token_reference=None,
            ),
        }
        self._callbacks: Dict[str, PortalCallbackRecord] = callbacks or {
            "ACCT-CORP-USD-001": PortalCallbackRecord(
                callback_id="CB-PORTAL-01",
                debtor_account="ACCT-CORP-USD-001",
                callback_status="VERIFIED",
                verification_channel="CORPORATE_PORTAL_MFA",
            ),
            "ACCT-UNAPPROVED-USD-002": PortalCallbackRecord(
                callback_id="CB-PORTAL-02",
                debtor_account="ACCT-UNAPPROVED-USD-002",
                callback_status="UNREACHABLE",
                verification_channel="CORPORATE_PORTAL_MFA",
            ),
        }

    def get_mandate_record(self, debtor_account: str) -> Optional[CorporateMandateRecord]:
        return self._mandates.get(debtor_account.strip())

    def get_secondary_signatory(self, debtor_account: str) -> Optional[SecondarySignatoryRecord]:
        key = debtor_account.strip()
        if key in self._signatories:
            return self._signatories[key]
        for s in self._signatories.values():
            if s.signatory_id == key:
                return s
        return None

    def get_portal_callback(self, debtor_account: str) -> Optional[PortalCallbackRecord]:
        return self._callbacks.get(debtor_account.strip())

    def generate_dual_auth_clearance(
        self, mandate_id: str, primary_signer: str, secondary_signer: str
    ) -> CorporateDualAuthorizationCandidate:
        return CorporateDualAuthorizationCandidate(
            authorization_id=f"AUTH-MAND-{uuid.uuid4().hex[:8].upper()}",
            mandate_id=mandate_id,
            primary_signatory_id=primary_signer,
            secondary_signatory_id=secondary_signer,
            authorization_status="DUAL_AUTHORIZATION_VERIFIED",
            execution_owner="BANK",
            rationale=f"Dual authorization verified for mandate {mandate_id} via secondary digital signature ({secondary_signer}).",
        )
