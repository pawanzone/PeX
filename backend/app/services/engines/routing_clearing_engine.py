"""RoutingClearingEngine: Routing, Clearing, Temporal, Queue, Gateway, and Retry Capability Engine.

Authoritative implementation for PeX Wave 1:
- PR-02: Routing Failure (PAT-A Master & Directory Resolution)
- PR-04: Cutoff Missed (PAT-B Temporal & Queue Recalculation / W1-POL-02)
- PR-07: Network Timeout (PAT-B Temporal & Queue Retry / Idempotency Controls)
- PR-09: Payment Held for Repair (PAT-B Repair Queue Recalculation)

Invariants:
- 0% autonomous synthesis of BICs, routing codes, or intermediary paths.
- W1-POL-02 parameterized cutoff buffer and value-date roll policy.
- Zero blind network retries; strict idempotency verification.
- Zero direct payment execution or ledger mutation (execution_owner = "BANK").
"""
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta, timezone

from app.ports.routing_directory_port import RoutingDirectoryPort
from app.ports.clearing_rail_calendar_port import ClearingRailCalendarPort
from app.ports.payment_hub_repair_queue_port import PaymentHubRepairQueuePort
from app.ports.gateway_socket_probe_port import GatewaySocketProbePort
from app.adapters.reference.reference_routing_directory_adapter import InMemoryRoutingDirectoryAdapter
from app.adapters.reference.reference_clearing_calendar_adapter import InMemoryClearingRailCalendarAdapter
from app.adapters.reference.reference_payment_hub_adapter import InMemoryPaymentHubRepairQueueAdapter
from app.adapters.reference.reference_gateway_socket_adapter import InMemoryGatewaySocketAdapter

from app.schemas.contracts.policy_schemas import W1PolicyCutoffBuffer
from app.schemas.contracts.wave1_schemas import (
    RouteResolutionRecord,
    SSIRecord,
    RailCutoffInfo,
    GatewayProbeResult,
    TransmissionStateResult,
    RetryBudgetResult,
    PaymentHubRepairRecord,
)
from app.schemas.resolution_contract import (
    ResolutionStatus,
    ResolutionUniqueness,
    ResolutionCandidate,
)


class RoutingClearingEngine:
    """Capability engine for routing, clearing rail temporal schedules, retry budgets, and repair queues."""

    def __init__(
        self,
        routing_port: Optional[RoutingDirectoryPort] = None,
        calendar_port: Optional[ClearingRailCalendarPort] = None,
        payment_hub_port: Optional[PaymentHubRepairQueuePort] = None,
        gateway_port: Optional[GatewaySocketProbePort] = None,
    ):
        self.routing_port = routing_port or InMemoryRoutingDirectoryAdapter()
        self.calendar_port = calendar_port or InMemoryClearingRailCalendarAdapter()
        self.payment_hub_port = payment_hub_port or InMemoryPaymentHubRepairQueueAdapter()
        self.gateway_port = gateway_port or InMemoryGatewaySocketAdapter()

    # ==========================================================================
    # 1. PR-02: ROUTING FAILURE
    # ==========================================================================
    def resolve_pr02_routing_failure(
        self,
        debtor_agent_bic: str,
        creditor_agent_bic: str,
        currency: str,
        clearing_rail: str,
        evidence_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Resolves valid reachable correspondent routing path and SSI from authoritative directory."""
        diff_log: List[str] = []
        ctx = evidence_context or {}

        # 1. Check for ambiguity / multiple unresolved routes
        if ctx.get("ambiguous_routing_paths", False) or ctx.get("multiple_clearing_routes", False):
            diff_log.append("Multiple competing clearing routes available without deterministic preference. Route to HITL.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Multiple competing routing candidates."

        # 2. Query routing directory port
        route_rec = self.routing_port.resolve_route(
            debtor_agent_bic=debtor_agent_bic,
            creditor_agent_bic=creditor_agent_bic,
            currency=currency,
            clearing_rail=clearing_rail
        )

        if not route_rec or not route_rec.is_reachable:
            reason = route_rec.reachability_status if route_rec else "No route found in SWIFT / clearing directory."
            diff_log.append(f"Routing resolution failed: {reason}")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, reason

        # 3. Query SSI for settlement account
        ssi = self.routing_port.get_ssi(creditor_agent_bic, currency)
        settlement_acct = ssi.settlement_account if ssi else route_rec.clearing_system_member_id

        diff_log.append(
            f"Resolved route via {route_rec.clearing_rail} "
            f"(intermediary={route_rec.intermediary_agent_bic or 'DIRECT'}, settlement_id={settlement_acct or 'NONE'})."
        )

        repaired_dict_pr02 = {
            "clearing_rail": route_rec.clearing_rail,
            "intermediary_agent_bic": route_rec.intermediary_agent_bic,
            "clearing_system_member_id": route_rec.clearing_system_member_id,
            "settlement_account": settlement_acct
        }
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-PR02-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict_pr02),
            repaired_structured=repaired_dict_pr02,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_A_ROUTING_DIRECTORY_SSI_RESOLVER",
            is_lossless=True,
            fields_reordered=[]
        )

        return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

    # ==========================================================================
    # 2. PR-04: CUTOFF MISSED
    # ==========================================================================
    def resolve_pr04_cutoff_missed(
        self,
        clearing_rail: str,
        currency: str,
        current_value_date: date,
        policy_buffer: Optional[W1PolicyCutoffBuffer] = None,
        evidence_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Recalculates deterministic value-date adjustment under W1-POL-02 policy cutoff buffer."""
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_buffer or W1PolicyCutoffBuffer()

        # 1. Retrieve rail cutoff schedule
        cutoff_info = self.calendar_port.get_rail_cutoff(clearing_rail, currency)
        if not cutoff_info:
            diff_log.append(f"No cutoff calendar available for rail {clearing_rail} / {currency}. Route to HITL.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Missing rail cutoff schedule."

        diff_log.append(f"Rail {clearing_rail} cutoff time: {cutoff_info.cutoff_utc} UTC (Buffer: {policy.cutoff_buffer_minutes}m).")

        # 2. Check if policy allows automated value-date roll
        if not policy.allow_auto_value_date_roll:
            diff_log.append("Bank policy W1-POL-02 disallows autonomous value-date rolls without explicit client authorization.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Autonomous value-date roll prohibited by bank policy."

        # 3. Calculate next valid operating value date
        next_value_date = self.calendar_port.calculate_next_value_date(clearing_rail, current_value_date, roll_days=1)
        days_rolled = (next_value_date - current_value_date).days

        if days_rolled > policy.max_value_date_roll_days:
            diff_log.append(f"Value date roll ({days_rolled} days) exceeds maximum allowed roll window ({policy.max_value_date_roll_days} days).")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Value date roll window exceeded."

        diff_log.append(f"Recalculated value date from {current_value_date.isoformat()} to {next_value_date.isoformat()} (T+{days_rolled} business day).")

        repaired_dict_pr04 = {
            "value_date": next_value_date.isoformat(),
            "original_value_date": current_value_date.isoformat(),
            "days_rolled": days_rolled,
            "clearing_rail": clearing_rail
        }
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-PR04-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict_pr04),
            repaired_structured=repaired_dict_pr04,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_B_TEMPORAL_CUTOFF_RECALCULATOR",
            is_lossless=True,
            fields_reordered=[]
        )

        return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

    # ==========================================================================
    # 3. PR-07: NETWORK TIMEOUT
    # ==========================================================================
    def resolve_pr07_network_timeout(
        self,
        payment_id: str,
        payment_uetr: str,
        rail_code: str,
        gateway_id: str = "GW-PRIMARY",
        evidence_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Verifies gateway health, checks payment transmission state, and evaluates safe idempotent retry eligibility."""
        diff_log: List[str] = []
        ctx = evidence_context or {}

        # 1. Probe gateway socket health
        probe = self.gateway_port.probe_gateway_socket(gateway_id, rail_code)
        if not probe.is_socket_connected or probe.socket_status in ["UNREACHABLE", "DEADLOCKED"]:
            diff_log.append(f"Gateway socket '{gateway_id}' is unhealthy ({probe.socket_status}). Hold for investigation.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Gateway socket {probe.socket_status}"

        # 2. Check transmission state
        tx_state = self.gateway_port.check_transmission_state(payment_uetr)
        if tx_state.is_execution_settled:
            diff_log.append(f"Payment {payment_uetr} confirmed settled on remote clearing rail. Retry forbidden (duplicate prevention).")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Payment already settled on clearing network."

        if not tx_state.can_safely_retry:
            diff_log.append(f"Transmission state '{tx_state.transmission_status}' cannot be safely retried without human operator review.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Unsafe transmission retry state."

        # 3. Check retry budget
        budget = self.gateway_port.get_retry_budget(payment_id)
        if not budget.can_retry:
            diff_log.append(f"Retry budget exhausted ({budget.retries_exhausted}/{budget.max_retries}). Route to PeX HITL.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Retry attempt budget exhausted."

        diff_log.append(f"Gateway healthy ({probe.latency_ms:.1f}ms). Safe idempotent retry approved (Attempt {budget.retries_exhausted + 1}/{budget.max_retries}).")

        repaired_dict_pr07 = {
            "action": "IDEMPOTENT_GATEWAY_RETRY",
            "payment_uetr": payment_uetr,
            "target_gateway": gateway_id,
            "retry_attempt": budget.retries_exhausted + 1
        }
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-PR07-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict_pr07),
            repaired_structured=repaired_dict_pr07,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_B_GATEWAY_SAFE_RETRY_EVALUATOR",
            is_lossless=True,
            fields_reordered=[]
        )

        return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

    # ==========================================================================
    # 4. PR-09: PAYMENT HELD FOR REPAIR
    # ==========================================================================
    def resolve_pr09_held_for_repair(
        self,
        payment_id: str,
        payment_uetr: str,
        evidence_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Inspects payment hub repair queue item, verifies syntax correction, and prepares release envelope."""
        diff_log: List[str] = []
        ctx = evidence_context or {}

        # 1. Retrieve repair item metadata from payment hub
        repair_item = self.payment_hub_port.get_repair_item(payment_id)
        if not repair_item:
            diff_log.append(f"No pending repair record for payment {payment_id} in bank payment hub.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Payment not found in repair queue."

        diff_log.append(f"Payment hub queue status: '{repair_item.current_queue_status}' (Syntax Error: {repair_item.syntax_error_code or 'NONE'}).")

        # 2. Check for simulated unresolved repair conditions
        if ctx.get("unresolved_syntax_error", False):
            diff_log.append("Syntax error in repair item could not be resolved automatically. PeX HITL repair required.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Unresolved repair syntax error."

        # 3. Validate repair fix
        proposed_fix = {
            "repaired_fields": ctx.get("repaired_fields", [{"field_path": "GrpHdr.CreDtTm", "status": "SYNTAX_NORMALIZED"}]),
            "repaired_payload": ctx.get("repaired_payload", f"<Document xmlns=\"urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08\"><PmtId>{payment_uetr}</PmtId></Document>")
        }
        val_res = self.payment_hub_port.validate_repair_syntax(payment_id, proposed_fix)

        if not val_res.is_valid_repair:
            diff_log.append(f"Repair validation failed: {val_res.validation_errors}")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Validation errors: {val_res.validation_errors}"

        diff_log.append(f"Repair syntax validated against payment hub schema. Release envelope prepared for bank execution.")

        candidate = ResolutionCandidate(
            candidate_id=f"CAND-PR09-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(proposed_fix),
            repaired_structured=proposed_fix,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_B_PAYMENT_HUB_REPAIR_QUEUE_RESOLVER",
            is_lossless=True,
            fields_reordered=[]
        )

        return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

    # ==========================================================================
    # 5. PR-06 SUPPORTING: ALTERNATE CORRESPONDENT HOP RESOLUTION (PAT-A)
    # ==========================================================================
    def resolve_alternate_correspondent_hop(
        self,
        debtor_agent_bic: str,
        creditor_agent_bic: str,
        currency: str,
        clearing_rail: str,
        rejected_intermediary_bic: str,
        evidence_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], List[str], Optional[str]]:
        """Queries clearing directory and SSI records to find a viable, reachable alternate intermediary hop.

        Returns:
            Tuple[is_viable, alternate_bic, diff_log, error_reason]
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}

        # 1. Check for ambiguous competing routes
        if ctx.get("ambiguous_routing_paths", False) or ctx.get("multiple_competing_alternate_routes", False):
            diff_log.append("Multiple competing alternate correspondent hops available. Disambiguation required in HITL.")
            return False, None, diff_log, "Ambiguous alternate correspondent routes."

        # 2. Check if verified alternate BIC is supplied in context
        if ctx.get("verified_alternate_intermediary_bic"):
            alt_bic = ctx["verified_alternate_intermediary_bic"]
            diff_log.append(f"Using supplied verified alternate correspondent BIC: {alt_bic}.")
            return True, alt_bic, diff_log, None

        # 3. Query routing directory port
        route_rec = self.routing_port.resolve_route(
            debtor_agent_bic=debtor_agent_bic,
            creditor_agent_bic=creditor_agent_bic,
            currency=currency,
            clearing_rail=clearing_rail
        )

        if not route_rec or not route_rec.is_reachable:
            diff_log.append(f"No reachable clearing route found between {debtor_agent_bic} and {creditor_agent_bic}.")
            return False, None, diff_log, "No reachable routing path in clearing directory."

        # Verify candidate intermediary hop is different from rejected one
        cand_bic = route_rec.intermediary_agent_bic
        if not cand_bic or cand_bic == rejected_intermediary_bic:
            # Check secondary SSI
            ssi = self.routing_port.get_ssi(creditor_agent_bic, currency)
            if ssi and ssi.intermediary_bic and ssi.intermediary_bic != rejected_intermediary_bic:
                cand_bic = ssi.intermediary_bic

        if not cand_bic or cand_bic == rejected_intermediary_bic:
            diff_log.append(f"No distinct alternate intermediary hop available (only rejected {rejected_intermediary_bic} listed).")
            return False, None, diff_log, "No distinct alternate intermediary available."

        diff_log.append(f"Resolved viable alternate intermediary BIC '{cand_bic}' via {clearing_rail}.")
        return True, cand_bic, diff_log, None


# Global singleton
routing_clearing_engine = RoutingClearingEngine()
