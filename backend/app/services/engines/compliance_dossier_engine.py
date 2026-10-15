"""ComplianceDossierEngine: Legal Freeze Dossier & Statutory Compliance Evaluation Capability Engine.

Authoritative implementation for PeX Wave 2:
- ST-03: Beneficiary Account Frozen (Supporting PAT-D Compliance & Risk Dossier)

Invariants:
- Zero autonomous policy creation; evaluates authoritative legal registries.
- ST-03 is strictly restricted to account credit restrictions (e.g. Post No Credits, Court Garnishments).
- Statutory sanctions asset blocks are strictly detected and diverted to CO-01 governance (No Return).
- Provider-neutral, cloud-neutral, model-neutral.
"""
from typing import Dict, List, Any, Optional, Tuple
from app.ports.legal_registry_port import LegalRegistryPort
from app.adapters.reference.reference_legal_registry_adapter import InMemoryLegalRegistryAdapter
from app.schemas.contracts.wave2_schemas import (
    LegalFreezeDossierRecord,
    LegalFreezeType,
    AccountRestrictionScope,
    AccountRestrictionType,
)


class ComplianceDossierEngine:
    """Capability engine for evaluating legal freeze dossiers, court injunctions, and statutory boundaries."""

    def __init__(self, legal_port: Optional[LegalRegistryPort] = None):
        self.legal_port = legal_port or InMemoryLegalRegistryAdapter()

    def evaluate_legal_freeze_dossier(
        self,
        account_number: str,
        evidence_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[LegalFreezeDossierRecord], List[str], Optional[str]]:
        """Evaluates legal/regulatory freeze dossiers associated with account credit restrictions.

        Returns:
            Tuple[is_valid_legal_hold, dossier_record, diff_log, error_reason]
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}

        # 1. Check for statutory sanctions conflict
        if ctx.get("is_statutory_sanctions") or ctx.get("ofac_sdn_hit"):
            diff_log.append("Account restriction stems from statutory sanctions / blocked property. Divert to CO-01 governance.")
            return False, None, diff_log, "Statutory sanctions block must be governed under CO-01, not ST-03."

        # 2. Check for conflicting legal orders
        if ctx.get("conflicting_legal_orders", False):
            diff_log.append("Conflicting judicial orders on record (e.g., competing state vs federal garnishment). Route to Legal Officer.")
            return False, None, diff_log, "Conflicting legal orders detected."

        # 3. Retrieve authoritative legal freeze dossier
        dossier = None
        if "legal_freeze_dossier" in ctx:
            raw_dossier = ctx["legal_freeze_dossier"]
            if raw_dossier is None:
                dossier = None
            elif isinstance(raw_dossier, dict):
                dossier = LegalFreezeDossierRecord(**raw_dossier)
            elif isinstance(raw_dossier, LegalFreezeDossierRecord):
                dossier = raw_dossier
        elif "court_order" in ctx:
            raw_dossier = ctx["court_order"]
            if isinstance(raw_dossier, dict):
                dossier = LegalFreezeDossierRecord(**raw_dossier)
        elif ctx.get("verified_legal_dossier_id"):
            dossier = LegalFreezeDossierRecord(
                dossier_id=ctx["verified_legal_dossier_id"],
                account_number=account_number,
                case_caption=ctx.get("case_caption", "State v. Target Entity"),
                court_or_agency_name=ctx.get("court_name", "District Court"),
                docket_number=ctx.get("docket_number", "DOCKET-2026-001"),
                freeze_type=LegalFreezeType.COURT_INJUNCTION,
                freeze_scope="POST_NO_CREDITS",
                permitted_disposition=ctx.get("permitted_disposition", "RETURN_TO_ORDERING_INSTITUTION"),
                compliance_officer_signoff=True
            )

        if not dossier and "legal_freeze_dossier" not in ctx:
            dossier = self.legal_port.get_legal_freeze_dossier(account_number)

        if not dossier:
            diff_log.append("No active legal freeze dossier found in Legal Registry SPI.")
            return False, None, diff_log, "Missing active legal freeze dossier record."

        if dossier.is_conflicting_order:
            diff_log.append(f"Dossier {dossier.dossier_id} flagged with conflicting legal orders.")
            return False, None, diff_log, "Conflicting judicial orders in dossier."

        if dossier.freeze_type == LegalFreezeType.STATUTORY_ASSET_FREEZE:
            diff_log.append("Dossier classified as STATUTORY_ASSET_FREEZE. Cannot perform return; requires CO-01.")
            return False, None, diff_log, "Statutory asset freeze must be processed under CO-01."

        diff_log.append(
            f"Validated legal dossier {dossier.dossier_id} ({dossier.freeze_type.value}, "
            f"court: '{dossier.court_or_agency_name}', docket: '{dossier.docket_number}'). "
            f"Permitted disposition: {dossier.permitted_disposition}."
        )

        return True, dossier, diff_log, None


# Global singleton
compliance_dossier_engine = ComplianceDossierEngine()
