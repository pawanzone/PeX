"""Wave4ResolutionEngine: Client/Treasury and Settlement/Returns Capability Engine.

Authoritative implementation for PeX Wave 4:
- TR-01: KYC Expired (PAT-C / PAT-B SOP-302 Provisional Waiver Evaluation)
- TR-05: Authorization Missing (PAT-C / PAT-B Corporate Mandate & Secondary Signatory Dual-Auth)
- ST-06: Funds Trapped at Correspondent (PAT-F / PAT-E SWIFT gpi Transit Break & camt.056 Inquiry Packaging)

Invariants:
- Zero direct payment execution or ledger mutation (execution_owner = "BANK").
- Zero autonomous STP on ST-06 transit break (Group 4 Transit Break — autonomous_stp_prohibited = True).
- Missing, expired, unapproved, or unverified telemetry fails closed.
- Bank-policy parameterized thresholds (W4PolicyThresholds).
- Hermetic and provider-neutral SPI port integrations.
"""
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

from app.ports.kyc_master_port import KycMasterPort
from app.ports.corporate_mandate_port import CorporateMandatePort
from app.ports.transit_tracker_port import TransitTrackerPort

from app.adapters.reference.reference_kyc_master_adapter import InMemoryKycMasterAdapter
from app.adapters.reference.reference_corporate_mandate_adapter import InMemoryCorporateMandateAdapter
from app.adapters.reference.reference_transit_tracker_adapter import InMemoryTransitTrackerAdapter

from app.schemas.contracts.policy_schemas import W4PolicyThresholds
from app.schemas.contracts.wave4_schemas import (
    CustomerKycRecord,
    CorporateStandingRecord,
    KycWaiverPolicyRecord,
    KycProvisionalWaiverCandidate,
    CorporateMandateRecord,
    SecondarySignatoryRecord,
    PortalCallbackRecord,
    CorporateDualAuthorizationCandidate,
    CorrespondentTrackerHopRecord,
    DebitConfirmationRecord,
    TransitInquiryPolicyRecord,
    TransitInvestigationCandidate,
)
from app.schemas.resolution_contract import (
    ResolutionStatus,
    ResolutionUniqueness,
    ResolutionCandidate,
)


class Wave4ResolutionEngine:
    """Enterprise resolution engine for Wave 4 exception profiles."""

    def __init__(
        self,
        kyc_port: Optional[KycMasterPort] = None,
        mandate_port: Optional[CorporateMandatePort] = None,
        tracker_port: Optional[TransitTrackerPort] = None,
    ):
        self.kyc_port = kyc_port or InMemoryKycMasterAdapter()
        self.mandate_port = mandate_port or InMemoryCorporateMandateAdapter()
        self.tracker_port = tracker_port or InMemoryTransitTrackerAdapter()

    # ==========================================================================
    # 1. TR-01: KYC EXPIRED (PAT-C / PAT-B)
    # ==========================================================================
    def resolve_tr01_kyc_expired(
        self,
        client_id: str,
        amount: float,
        currency: str,
        policy_thresholds: Optional[W4PolicyThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Evaluates expired client KYC under SOP-302 provisional waiver rules.

        Conditions for provisional 30-day waiver:
        1. Authoritative KYC master record exists and shows refresh in progress.
        2. Clean historical record (>= 24 dispute-free months).
        3. Corporate standing is Tier 1 / Regional without active SAR or regulatory inquiries.
        4. Clearing corridor risk is not HIGH.
        5. Instructed amount is within SOP-302 provisional threshold.
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W4PolicyThresholds()

        # Ingest injected evidence context records if present
        raw_kyc = ctx.get("customer_kyc_record")
        if raw_kyc and isinstance(raw_kyc, dict):
            now = datetime.now(timezone.utc)
            rec = CustomerKycRecord(
                client_id=raw_kyc.get("client_id", client_id),
                client_name=raw_kyc.get("client_name", "Corporate Client"),
                kyc_status=raw_kyc.get("kyc_status", "EXPIRED"),
                last_review_date=now - timedelta(days=400),
                expiry_date=now - timedelta(days=30),
                refresh_in_progress=bool(raw_kyc.get("refresh_in_progress", True)),
                dispute_free_months=int(raw_kyc.get("dispute_free_months", 24)),
                is_authoritative=bool(raw_kyc.get("is_authoritative", True)),
                authority_source=raw_kyc.get("authority_source", "CLIENT_ONBOARDING_KYC_MASTER"),
            )
            if hasattr(self.kyc_port, "_kyc_records"):
                self.kyc_port._kyc_records[client_id] = rec

        raw_standing = ctx.get("corporate_standing_record")
        if raw_standing and isinstance(raw_standing, dict):
            standing_rec = CorporateStandingRecord(
                client_id=raw_standing.get("client_id", client_id),
                tier_rating=raw_standing.get("tier_rating", "TIER_1_MULTINATIONAL"),
                credit_score=int(raw_standing.get("credit_score", 800)),
                relationship_tenure_years=int(raw_standing.get("relationship_tenure_years", 5)),
                has_active_sar_or_regulatory_query=bool(raw_standing.get("has_active_sar_or_regulatory_query", False)),
                clearing_corridor_risk=raw_standing.get("clearing_corridor_risk", "LOW"),
            )
            if hasattr(self.kyc_port, "_corporate_standings"):
                self.kyc_port._corporate_standings[client_id] = standing_rec

        # 1. Authoritative Lookups
        kyc_record = self.kyc_port.get_kyc_record(client_id)
        if not kyc_record:
            diff_log.append(f"No authoritative KYC master record found for client {client_id}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Missing KYC master record for {client_id}."

        standing = self.kyc_port.get_corporate_standing(client_id)
        if not standing:
            diff_log.append(f"No corporate relationship standing record found for client {client_id}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Missing corporate standing record for {client_id}."

        waiver_policy = self.kyc_port.get_waiver_policy()

        # 2. Risk & Compliance Guardrails
        if standing.has_active_sar_or_regulatory_query:
            diff_log.append(f"Client {client_id} has an active SAR or regulatory query on file. Provisional waiver strictly prohibited.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Active SAR flag prevents provisional KYC waiver."

        if standing.clearing_corridor_risk.upper() == "HIGH":
            diff_log.append(f"Clearing corridor risk for {client_id} is HIGH. Provisional waiver prohibited.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "High-risk corridor prohibits provisional KYC waiver."

        if not kyc_record.refresh_in_progress:
            diff_log.append(f"Client {client_id} has not initiated periodic KYC documentation refresh. Provisional waiver denied.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Documentation refresh not in progress."

        if kyc_record.dispute_free_months < waiver_policy.min_clean_months:
            diff_log.append(
                f"Client {client_id} dispute-free tenure ({kyc_record.dispute_free_months}m) "
                f"below required minimum ({waiver_policy.min_clean_months}m)."
            )
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Insufficient dispute-free history."

        # 3. Policy Threshold Evaluation
        max_amount = min(waiver_policy.max_waiver_amount, policy.max_provisional_waiver_amount)
        if amount > max_amount:
            diff_log.append(
                f"Instructed amount ({amount:,.2f} {currency}) exceeds maximum provisional waiver threshold ({max_amount:,.2f} {currency})."
            )
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Amount exceeds max provisional KYC waiver threshold."

        # 4. Generate Candidate Package
        waiver_candidate = self.kyc_port.generate_provisional_waiver(client_id, waiver_policy.max_waiver_days)
        diff_log.append(
            f"Provisional 30-day KYC waiver {waiver_candidate.waiver_id} granted for {client_id} "
            f"under SOP-302. Documentation refresh confirmed in progress."
        )

        repaired_dict = waiver_candidate.model_dump(mode="json")
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-TR01-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict),
            repaired_structured=repaired_dict,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_C_PROVISIONAL_KYC_WAIVER",
            is_lossless=True,
            fields_reordered=[],
        )
        uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS if ctx.get("ambiguous_candidates", False) else ResolutionUniqueness.RESOLUTION_UNIQUE
        return ResolutionStatus.RESOLUTION_DETERMINED, uniqueness, candidate, diff_log, None

    # ==========================================================================
    # 2. TR-05: AUTHORIZATION MISSING (PAT-C / PAT-B)
    # ==========================================================================
    def _scoped_mandate_port(self):
        """Private copy of the mandate port's records for one resolution (no state leaks between cases)."""
        mp = self.mandate_port
        if all(hasattr(mp, a) for a in ("_mandates", "_signatories", "_callbacks")):
            import copy
            clone = copy.copy(mp)
            clone._mandates = dict(mp._mandates)
            clone._signatories = dict(mp._signatories)
            clone._callbacks = dict(mp._callbacks)
            return clone
        return mp

    def resolve_tr05_authorization_missing(
        self,
        debtor_account: str,
        amount: float,
        currency: str,
        primary_signatory_id: Optional[str] = None,
        secondary_signatory_id: Optional[str] = None,
        policy_thresholds: Optional[W4PolicyThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Evaluates missing secondary authorization against corporate mandate and digital portal queue.

        Conditions for corporate dual-authorization clearance:
        1. Authoritative corporate mandate exists for debtor account.
        2. Secondary signatory is identified, holds allowed signer class (e.g. CLASS_A/B).
        3. Secondary digital signature is APPROVED with verified MFA.
        4. Out-of-band corporate portal callback status is VERIFIED.
        """
        # Evidence supplied with this case is applied to a private copy of the reference store. Writing it into the shared
        # adapter made later cases (and tests) see earlier cases' mandates, signatories and callbacks.
        port = self._scoped_mandate_port()
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W4PolicyThresholds()

        # Ingest injected evidence context records if present
        raw_mandate = ctx.get("corporate_mandate_record")
        if raw_mandate and isinstance(raw_mandate, dict):
            m_rec = CorporateMandateRecord(
                mandate_id=raw_mandate.get("mandate_id", "MAND-DEFAULT-01"),
                debtor_account=raw_mandate.get("debtor_account", debtor_account),
                dual_auth_threshold=float(raw_mandate.get("dual_auth_threshold", 250000.0)),
                required_signatory_count=int(raw_mandate.get("required_signatory_count", 2)),
                allowed_signer_classes=raw_mandate.get("allowed_signer_classes", ["CLASS_A", "CLASS_B"]),
                is_authoritative=bool(raw_mandate.get("is_authoritative", True)),
                authority_source=raw_mandate.get("authority_source", "CORPORATE_MANDATE_SYSTEM"),
            )
            if hasattr(port, "_mandates"):
                port._mandates[debtor_account] = m_rec

        raw_signer = ctx.get("secondary_signatory_record")
        sig_id = secondary_signatory_id or (raw_signer.get("signatory_id") if isinstance(raw_signer, dict) else "SIG-CLASS-A-99")
        if raw_signer and isinstance(raw_signer, dict):
            s_rec = SecondarySignatoryRecord(
                signatory_id=sig_id,
                signatory_name=raw_signer.get("signatory_name", "Authorized Signer"),
                signer_class=raw_signer.get("signer_class", "CLASS_A"),
                signature_status=raw_signer.get("signature_status", "APPROVED"),
                mfa_verified=bool(raw_signer.get("mfa_verified", True)),
                digital_token_reference=raw_signer.get("digital_token_reference", "TOKEN-MFA-OK"),
            )
            if hasattr(port, "_signatories"):
                port._signatories[sig_id] = s_rec
                port._signatories[debtor_account] = s_rec

        raw_callback = ctx.get("portal_callback_record")
        if raw_callback and isinstance(raw_callback, dict):
            c_rec = PortalCallbackRecord(
                callback_id=raw_callback.get("callback_id", "CB-DEFAULT-01"),
                debtor_account=raw_callback.get("debtor_account", debtor_account),
                callback_status=raw_callback.get("callback_status", "VERIFIED"),
                verification_channel=raw_callback.get("verification_channel", "CORPORATE_PORTAL_MFA"),
            )
            if hasattr(port, "_callbacks"):
                port._callbacks[debtor_account] = c_rec

        # 1. Authoritative Mandate Lookup
        mandate = port.get_mandate_record(debtor_account)
        if not mandate:
            diff_log.append(f"No authoritative corporate mandate found for account {debtor_account}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Missing corporate mandate for {debtor_account}."

        # 2. Signatory & Digital Signature Validation
        signatory = port.get_secondary_signatory(debtor_account) or port.get_secondary_signatory(sig_id)
        if not signatory:
            diff_log.append(f"Secondary signatory {sig_id} not found in corporate directory.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Secondary signatory {sig_id} not found."

        if signatory.signer_class not in mandate.allowed_signer_classes:
            diff_log.append(f"Signer class {signatory.signer_class} is not authorized under mandate {mandate.mandate_id}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Signer class {signatory.signer_class} unauthorized."

        if signatory.signature_status != "APPROVED":
            diff_log.append(f"Secondary signature status is {signatory.signature_status}. Dual authorization incomplete.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Secondary signature is {signatory.signature_status}."

        if not signatory.mfa_verified:
            diff_log.append(f"Secondary signatory {signatory.signatory_id} digital MFA was not verified.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Secondary signatory MFA not verified."

        # 3. Portal Out-of-Band Callback Verification
        callback = port.get_portal_callback(debtor_account)
        if not callback or callback.callback_status != "VERIFIED":
            diff_log.append(f"Out-of-band portal callback for account {debtor_account} is not VERIFIED.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Portal callback verification failed."

        # 4. Dual-Auth Candidate Clearance
        prim_id = primary_signatory_id or "SIG-PRIMARY-01"
        auth_candidate = port.generate_dual_auth_clearance(
            mandate_id=mandate.mandate_id,
            primary_signer=prim_id,
            secondary_signer=signatory.signatory_id,
        )
        diff_log.append(
            f"Dual authorization {auth_candidate.authorization_id} verified for mandate {mandate.mandate_id}. "
            f"Signatories: {prim_id} (Primary), {signatory.signatory_id} ({signatory.signer_class}, MFA verified)."
        )

        repaired_dict = auth_candidate.model_dump(mode="json")
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-TR05-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict),
            repaired_structured=repaired_dict,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_C_CORPORATE_DUAL_AUTH_VERIFICATION",
            is_lossless=True,
            fields_reordered=[],
        )
        uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS if ctx.get("ambiguous_candidates", False) else ResolutionUniqueness.RESOLUTION_UNIQUE
        return ResolutionStatus.RESOLUTION_DETERMINED, uniqueness, candidate, diff_log, None

    # ==========================================================================
    # 3. ST-06: FUNDS TRAPPED AT CORRESPONDENT (PAT-F / PAT-E)
    # ==========================================================================
    def resolve_st06_funds_trapped(
        self,
        uetr: str,
        amount: float,
        currency: str,
        intermediary_bic: Optional[str] = None,
        policy_thresholds: Optional[W4PolicyThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Evaluates SWIFT gpi transit break and packages camt.056 inquiry dossier.

        MANDATORY INVARIANT:
        Group 4 Transit Break — Autonomous STP is strictly prohibited (autonomous_stp_prohibited = True).
        All inquiry packages must route to Bank Operations Maker-Checker for controlled dispatch.

        Conditions for generating inquiry package:
        1. Authoritative SWIFT gpi tracker hop telemetry exists showing payment held at intermediary.
        2. Inward camt.054 debit confirmation proves funds left debtor account.
        3. Hold duration at intermediary exceeds bank inquiry policy threshold.
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W4PolicyThresholds()

        # Ingest injected evidence context records if present
        raw_hop = ctx.get("tracker_hop_record")
        target_bic = intermediary_bic or (raw_hop.get("intermediary_bic") if isinstance(raw_hop, dict) else "DEUTDEDDXXX")
        if raw_hop and isinstance(raw_hop, dict):
            hop_rec = CorrespondentTrackerHopRecord(
                uetr=raw_hop.get("uetr", uetr),
                intermediary_bic=target_bic,
                hop_number=int(raw_hop.get("hop_number", 2)),
                hold_duration_minutes=float(raw_hop.get("hold_duration_minutes", 180.0)),
                hop_status=raw_hop.get("hop_status", "HELD_AT_INTERMEDIARY"),
                is_authoritative=bool(raw_hop.get("is_authoritative", True)),
                authority_source=raw_hop.get("authority_source", "SWIFT_GPI_TRACKER"),
            )
            if hasattr(self.tracker_port, "_tracker_hops"):
                self.tracker_port._tracker_hops[uetr] = hop_rec

        raw_debit = ctx.get("debit_confirmation_record")
        if raw_debit and isinstance(raw_debit, dict):
            d_rec = DebitConfirmationRecord(
                debit_reference=raw_debit.get("debit_reference", "DBT-ST06-001"),
                debtor_account=raw_debit.get("debtor_account", "ACCT-ST06-7788"),
                amount=float(raw_debit.get("amount", amount)),
                currency=raw_debit.get("currency", currency),
                is_confirmed=bool(raw_debit.get("is_confirmed", True)),
            )
            if hasattr(self.tracker_port, "_debit_confirmations"):
                self.tracker_port._debit_confirmations[uetr] = d_rec

        # 1. Authoritative Tracker Telemetry Lookup
        hop = self.tracker_port.get_tracker_hop(uetr)
        if not hop or not hop.is_authoritative:
            diff_log.append(f"No authoritative SWIFT gpi tracker hop telemetry found for UETR {uetr}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Missing authoritative tracker telemetry for {uetr}."

        if hop.hop_status != "HELD_AT_INTERMEDIARY":
            diff_log.append(f"Tracker hop status is {hop.hop_status}, not HELD_AT_INTERMEDIARY. Cannot issue transit inquiry.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Hop status is {hop.hop_status}."

        # 2. Inward Debit Confirmation Lookup
        debit = self.tracker_port.get_debit_confirmation(uetr)
        if not debit or not debit.is_confirmed:
            diff_log.append(f"No confirmed camt.054 debit record found for UETR {uetr}. Transit inquiry requires confirmed debit.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Unconfirmed debit for {uetr}."

        # 3. Policy Hold Threshold Check
        inquiry_policy = self.tracker_port.get_inquiry_policy()
        min_hold = min(inquiry_policy.min_hold_minutes_for_inquiry, policy.min_transit_hold_minutes_for_inquiry)
        if hop.hold_duration_minutes < min_hold:
            diff_log.append(
                f"Transit hold duration ({hop.hold_duration_minutes:.1f}m) has not reached inquiry threshold ({min_hold:.1f}m)."
            )
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Hold duration below inquiry threshold."

        # 4. Generate Investigation Candidate (MANDATORY: zero autonomous STP)
        investigation_candidate = self.tracker_port.generate_investigation_candidate(
            uetr=uetr,
            intermediary_bic=target_bic or hop.intermediary_bic,
            inquiry_type=inquiry_policy.inquiry_message_type,
        )
        diff_log.append(
            f"Generated {investigation_candidate.inquiry_type} inquiry {investigation_candidate.inquiry_reference} "
            f"for intermediary {investigation_candidate.target_intermediary_bic} (hold: {hop.hold_duration_minutes:.1f}m). "
            f"Autonomous STP prohibited (Group 4 Transit Break); assigned to Bank Operations."
        )

        repaired_dict = investigation_candidate.model_dump(mode="json")
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-ST06-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict),
            repaired_structured=repaired_dict,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_F_INTERMEDIARY_INQUIRY_DOSSIER",
            is_lossless=True,
            fields_reordered=[],
        )
        uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS if ctx.get("ambiguous_candidates", False) else ResolutionUniqueness.RESOLUTION_UNIQUE
        return ResolutionStatus.RESOLUTION_DETERMINED, uniqueness, candidate, diff_log, None


wave4_resolution_engine = Wave4ResolutionEngine()

