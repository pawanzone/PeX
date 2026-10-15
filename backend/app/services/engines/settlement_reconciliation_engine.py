"""SettlementReconciliationEngine: Settlement Reconciliation, Intermediary Tracking, and Return Capability Engine.

Authoritative implementation for PeX Wave 2:
- PR-06: Intermediary Bank Rejection (PAT-F Intermediary & Claims Tracking / PAT-E Ledger Reversal / PAT-A Routing)
- ST-02: Account Closed (Supporting PAT-E Ledger Reversal & Return Packaging)
- ST-03: Beneficiary Account Frozen (Supporting PAT-E Ledger Reversal & Legal Suspense Booking)

Invariants:
- Zero direct payment execution or ledger mutation (execution_owner = "BANK").
- Zero reliance on network telemetry alone for PR-06 rejection state.
- W2-BPD-01 parameterized correspondent reroute thresholds.
- W2-BPD-02 parameterized closed account return vs rollover policy.
- W2-BPD-03 parameterized frozen account return vs legal suspense policy.
- Deterministic correlation matching using bank/rail keys (UETR, amount, currency, party IDs).
"""
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from app.ports.correspondent_gateway_port import CorrespondentGatewayPort
from app.ports.settlement_return_port import SettlementReturnPort
from app.ports.general_ledger_suspense_port import GeneralLedgerSuspensePort
from app.ports.routing_directory_port import RoutingDirectoryPort
from app.adapters.reference.reference_correspondent_gateway_adapter import InMemoryCorrespondentGatewayAdapter
from app.adapters.reference.reference_settlement_return_adapter import InMemorySettlementReturnAdapter
from app.adapters.reference.reference_general_ledger_suspense_adapter import InMemoryGeneralLedgerSuspenseAdapter
from app.adapters.reference.reference_routing_directory_adapter import InMemoryRoutingDirectoryAdapter

from app.schemas.contracts.policy_schemas import W2PolicyThresholds
from app.schemas.contracts.wave2_schemas import (
    IntermediaryRejectionAdvice,
    IntermediaryRejectionReasonCode,
    DeterministicCorrelationMatch,
    SettlementReturnPackage,
    SettlementSuspenseBreakRecord,
    AlternateRerouteResult,
)
from app.schemas.resolution_contract import (
    ResolutionStatus,
    ResolutionUniqueness,
    ResolutionCandidate,
)


class SettlementReconciliationEngine:
    """Capability engine for interbank rejection tracking, settlement return packaging, and suspense ledger breaks."""

    def __init__(
        self,
        correspondent_port: Optional[CorrespondentGatewayPort] = None,
        return_port: Optional[SettlementReturnPort] = None,
        suspense_port: Optional[GeneralLedgerSuspensePort] = None,
        routing_port: Optional[RoutingDirectoryPort] = None,
    ):
        self.correspondent_port = correspondent_port or InMemoryCorrespondentGatewayAdapter()
        self.return_port = return_port or InMemorySettlementReturnAdapter()
        self.suspense_port = suspense_port or InMemoryGeneralLedgerSuspenseAdapter()
        self.routing_port = routing_port or InMemoryRoutingDirectoryAdapter()

    # ==========================================================================
    # 1. PR-06: INTERMEDIARY BANK REJECTION (PAT-F / PAT-A / PAT-E)
    # ==========================================================================
    def resolve_pr06_intermediary_rejection(
        self,
        uetr: str,
        payment_id: str,
        amount: float,
        currency: str,
        debtor_agent_bic: str,
        creditor_agent_bic: str,
        original_intermediary_bic: Optional[str] = None,
        clearing_rail: str = "SWIFT_CBPR+",
        policy_thresholds: Optional[W2PolicyThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Resolves intermediary rejection by checking structured rejection advice,

        evaluating viable alternate correspondent hops (Branch A) or generating an outward return/re-credit package (Branch B).
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W2PolicyThresholds()

        # 1. Inspect Inward Rejection Advice
        if ctx.get("duplicate_rejection_burst", False):
            diff_log.append("Duplicate burst of conflicting rejection advices detected. PeX fails closed to HITL.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Duplicate burst of rejection advices."

        rejection_ref = ctx.get("rejection_reference") or uetr
        advice = self.correspondent_port.get_rejection_advice(rejection_ref)

        if "rejection_advice" in ctx and ctx["rejection_advice"] is None:
            advice = None
        elif not advice:
            # Check if supplied in evidence context directly
            raw_adv = ctx.get("inward_rejection_advice") or ctx.get("rejection_advice")
            if raw_adv and isinstance(raw_adv, dict):
                advice = IntermediaryRejectionAdvice(**raw_adv)
            elif ctx.get("is_telemetry_only") or ctx.get("socket_error"):
                advice = IntermediaryRejectionAdvice(
                    rejection_reference=f"TEL-{uuid.uuid4().hex[:6]}",
                    original_uetr=uetr,
                    original_payment_id=payment_id,
                    rejecting_institution_bic=original_intermediary_bic or "CHASUS33XXX",
                    rejection_code="SOCKET_TIMEOUT",
                    rejection_category=IntermediaryRejectionReasonCode.SOCKET_ERROR_TELEMETRY,
                    narrative_text="Socket timeout / TCP connection drop",
                    is_telemetry_only=True
                )

        if not advice:
            diff_log.append("No authoritative intermediary rejection advice found in correspondent gateway.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Missing authoritative intermediary rejection advice."

        # 2. Strict Telemetry Boundary Verification: Telemetry != Sovereign Rejection
        if advice.is_telemetry_only or ctx.get("is_telemetry_only") or ctx.get("socket_error") or advice.rejection_category == IntermediaryRejectionReasonCode.SOCKET_ERROR_TELEMETRY:
            diff_log.append("Rejection state based solely on raw network telemetry (socket/TCP timeout). Telemetry is not authoritative rejection advice.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Network telemetry does not establish sovereign intermediary rejection."

        # 3. Check for Narrative / Unmapped / Compliance Ambiguity
        if advice.rejection_category == IntermediaryRejectionReasonCode.NARRATIVE_UNMAPPED or ctx.get("unmapped_narrative", False):
            diff_log.append(f"Inward rejection contains unmapped narrative: '{advice.narrative_text}'. Requires human investigation in PeX HITL.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Unmapped narrative in rejection advice."

        if advice.rejection_category == IntermediaryRejectionReasonCode.COMPLIANCE_REVIEW_REQUIRED or ctx.get("compliance_hold_required", False):
            diff_log.append("Intermediary rejection indicates correspondent AML / sanctions compliance hold. Escalating to Compliance Officer.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Intermediary compliance embargo."

        diff_log.append(f"Authoritative rejection from {advice.rejecting_institution_bic} confirmed (code: {advice.rejection_code}, category: {advice.rejection_category.value}).")

        # 4. Correlate Rejection to Original Payment Keys
        corr = self.correspondent_port.correlate_rejection(advice, {
            "uetr": uetr,
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "debtor_agent_bic": debtor_agent_bic,
            "creditor_agent_bic": creditor_agent_bic
        })
        if not corr.is_unambiguous_match:
            diff_log.append("Deterministic correlation matching failed to link rejection to outbound payment record.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Ambiguous payment correlation match."

        diff_log.append(f"Correlated rejection to original payment {corr.original_payment_id} (UETR: {corr.original_uetr}) with 100% confidence.")

        # 5. Check Multiple / Competing Alternate Routing Candidates Ambiguity
        if ctx.get("multiple_competing_alternate_routes", False) or ctx.get("ambiguous_routing_paths", False):
            diff_log.append("Multiple competing alternate correspondent hops available without deterministic preference. Route to HITL.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Multiple competing alternate correspondent routes."

        # 6. Branch A: Alternate Correspondent Routing Hop Derivation
        alternate_bic = ctx.get("verified_alternate_intermediary_bic")
        if not alternate_bic and policy.allow_auto_reroute:
            # Query directory for alternate reachable correspondent
            route_rec = self.routing_port.resolve_route(
                debtor_agent_bic=debtor_agent_bic,
                creditor_agent_bic=creditor_agent_bic,
                currency=currency,
                clearing_rail=clearing_rail
            )
            if route_rec and route_rec.is_reachable and route_rec.intermediary_agent_bic and route_rec.intermediary_agent_bic != advice.rejecting_institution_bic:
                alternate_bic = route_rec.intermediary_agent_bic

        if alternate_bic:
            # Check Bank Policy Reroute Threshold (W2-BPD-01)
            if amount > policy.max_auto_reroute_amount:
                diff_log.append(f"Transaction amount (${amount:,.2f}) exceeds max automated reroute limit (${policy.max_auto_reroute_amount:,.2f}). Requires Maker-Checker.")
                return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Amount exceeds W2-BPD-01 reroute limit: {amount} > {policy.max_auto_reroute_amount}"

            diff_log.append(f"Resolved viable alternate correspondent hop: {alternate_bic} (Clearing Rail: {clearing_rail}).")
            repaired_dict = {
                "intermediary_agent_bic": alternate_bic,
                "original_intermediary_bic": advice.rejecting_institution_bic,
                "rejection_reference": advice.rejection_reference,
                "resolution_action": "REROUTE_VIA_ALTERNATE_CORRESPONDENT",
                "clearing_rail": clearing_rail
            }
            candidate = ResolutionCandidate(
                candidate_id=f"CAND-PR06-REROUTE-{uuid.uuid4().hex[:8]}",
                repaired_payload=json.dumps(repaired_dict),
                repaired_structured=repaired_dict,
                diff_summary="; ".join(diff_log),
                derivation_method="PAT_F_INTERMEDIARY_TRACKING_AND_ALTERNATE_REROUTE",
                is_lossless=True,
                fields_reordered=[]
            )
            return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

        # 7. Branch B: Outward Cancellation / Return Package (if no alternate hop exists)
        if ctx.get("no_alternate_route_available", True):
            diff_log.append("No viable alternate correspondent routing hop available in clearing directory. Compiling outward cancellation / debtor return package.")
            ret_pkg = self.return_port.generate_return_package(
                uetr=uetr,
                original_payment_id=payment_id,
                amount=amount,
                currency=currency,
                return_reason_code="RC01",
                clearing_rail=clearing_rail,
                narrative=f"Intermediary rejection by {advice.rejecting_institution_bic}; no alternate route"
            )
            candidate = ResolutionCandidate(
                candidate_id=f"CAND-PR06-RETURN-{uuid.uuid4().hex[:8]}",
                repaired_payload=json.dumps(ret_pkg.model_dump(mode="json")),
                repaired_structured=ret_pkg.model_dump(mode="json"),
                diff_summary="; ".join(diff_log),
                derivation_method="PAT_F_INTERMEDIARY_TRACKING_AND_RETURN_DISPATCH",
                is_lossless=True,
                fields_reordered=[]
            )
            return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

        return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Unable to resolve intermediary rejection."

    # ==========================================================================
    # 2. REUSABLE SETTLEMENT RETURN PACKAGING (ST-02, ST-03, PR-06)
    # ==========================================================================
    def compile_return_package(
        self,
        uetr: str,
        original_payment_id: str,
        amount: float,
        currency: str,
        return_reason_code: str,
        clearing_rail: str,
        narrative: Optional[str] = None,
        debtor_account: Optional[str] = None
    ) -> SettlementReturnPackage:
        """Generates standard, balanced settlement return package."""
        return self.return_port.generate_return_package(
            uetr=uetr,
            original_payment_id=original_payment_id,
            amount=amount,
            currency=currency,
            return_reason_code=return_reason_code,
            clearing_rail=clearing_rail,
            narrative=narrative,
            debtor_account=debtor_account
        )

    # ==========================================================================
    # 3. REUSABLE LEGAL SUSPENSE BOOKING (ST-03)
    # ==========================================================================
    def compile_legal_suspense_booking(
        self,
        uetr: str,
        amount: float,
        currency: str,
        suspense_gl_account: str,
        escrow_reference_case: str
    ) -> SettlementSuspenseBreakRecord:
        """Constructs balanced double-entry journal break for internal bank suspense booking."""
        return self.suspense_port.create_suspense_break(
            uetr=uetr,
            amount=amount,
            currency=currency,
            suspense_gl_account=suspense_gl_account,
            escrow_reference_case=escrow_reference_case
        )


# Global singleton
settlement_reconciliation_engine = SettlementReconciliationEngine()
