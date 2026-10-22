"""Processing resolvers: pure functions lifted verbatim from the e2e_runner branches (behaviour unchanged;
the golden tests prove it). Generated once by scratch/gen_packs.py, maintained by hand from now on."""
from app.profile_packs.registry import register_resolver
from app.profile_packs.schema import ResolutionContext, ResolutionResult


@register_resolver("pr01_duplicate_payment")
def pr01_duplicate_payment(ctx: ResolutionContext) -> ResolutionResult:
    """PR-01 DUPLICATE_PAYMENT (lifted verbatim from the e2e_runner branch)."""
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    orig_pmt_id = evidence_ctx.get("original_payment_id")
    if orig_pmt_id:
        r_det = True
        r_uniq = True
        v_det = True
        repaired_fields = []
        resolution_basis = f"Confirmed duplicate transmission of settled payment {orig_pmt_id}. Suppressing duplicate wire."
        resolution_rec = {"action": "SUPPRESS_DUPLICATE_AND_NOTIFY", "original_payment_id": orig_pmt_id}
    else:
        resolution_basis = "No matching original transaction record found in settlement journal."
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("pr02_routing_failure")
def pr02_routing_failure(ctx: ResolutionContext) -> ResolutionResult:
    """PR-02 ROUTING_FAILURE (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import routing_clearing_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    status, uniq, cand, diff_log, err = routing_clearing_engine.resolve_pr02_routing_failure(
        debtor_agent_bic=pmt.debtor_agent_bic or "BNPAFRPPXXX",
        creditor_agent_bic=pmt.creditor_agent_bic or "CHASUS33XXX",
        currency=pmt.currency,
        clearing_rail=pmt.clearing_rail,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "creditor_agent.bic", "repaired_value": struct_data.get("intermediary_agent_bic") or pmt.creditor_agent_bic}]
        resolution_rec = {"action": "UPDATE_CLEARING_ROUTE", **struct_data}
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated PR-02")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("pr04_cutoff_missed")
def pr04_cutoff_missed(ctx: ResolutionContext) -> ResolutionResult:
    """PR-04 CUTOFF_MISSED (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import routing_clearing_engine
    from datetime import datetime, timezone
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_buffer = active_policy.w1_cutoff_buffer if active_policy else None
    try:
        curr_date = datetime.strptime(pmt.value_date, "%Y-%m-%d").date() if pmt.value_date else datetime.now(timezone.utc).date()
    except Exception:
        curr_date = datetime.now(timezone.utc).date()
    status, uniq, cand, diff_log, err = routing_clearing_engine.resolve_pr04_cutoff_missed(
        clearing_rail=pmt.clearing_rail,
        currency=pmt.currency,
        current_value_date=curr_date,
        policy_buffer=pol_buffer,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "payment.value_date", "original_value": pmt.value_date, "repaired_value": struct_data.get("value_date")}]
        resolution_rec = {"action": "ADJUST_VALUE_DATE", **struct_data}
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated PR-04")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("pr06_intermediary_bank_rejection")
def pr06_intermediary_bank_rejection(ctx: ResolutionContext) -> ResolutionResult:
    """PR-06 INTERMEDIARY_BANK_REJECTION (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import settlement_reconciliation_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w2_policy_thresholds if active_policy else None
    status, uniq, cand, diff_log, err = settlement_reconciliation_engine.resolve_pr06_intermediary_rejection(
        uetr=pmt.uetr,
        payment_id=pmt.payment_id,
        amount=pmt.amount,
        currency=pmt.currency,
        debtor_agent_bic=pmt.debtor_agent_bic or "BNPAFRPPXXX",
        creditor_agent_bic=pmt.creditor_agent_bic or "DEUTDEDDXXX",
        original_intermediary_bic=evidence_ctx.get("original_intermediary_bic") or "BNPAFRPPXXX",
        clearing_rail=pmt.clearing_rail,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        if "intermediary_agent_bic" in struct_data:
            repaired_fields = [{"field_path": "intermediary_agent.bic", "repaired_value": struct_data.get("intermediary_agent_bic")}]
        elif "return_reason_code" in struct_data:
            repaired_fields = [{"field_path": "settlement_return.reason", "repaired_value": struct_data.get("return_reason_code")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated PR-06")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("pr07_network_timeout")
def pr07_network_timeout(ctx: ResolutionContext) -> ResolutionResult:
    """PR-07 NETWORK_TIMEOUT (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import routing_clearing_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    status, uniq, cand, diff_log, err = routing_clearing_engine.resolve_pr07_network_timeout(
        payment_id=pmt.payment_id,
        payment_uetr=pmt.uetr,
        rail_code=pmt.clearing_rail,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = []
        resolution_rec = {"action": "IDEMPOTENT_SAFE_RETRY", **struct_data}
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated PR-07")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("pr08_queue_processing_failure")
def pr08_queue_processing_failure(ctx: ResolutionContext) -> ResolutionResult:
    """PR-08 QUEUE_PROCESSING_FAILURE (lifted verbatim from the e2e_runner branch)."""
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    broker_healthy = not evidence_ctx.get("broker_deadlocked", False)
    if broker_healthy:
        r_det = True
        r_uniq = True
        v_det = True
        repaired_fields = []
        resolution_basis = "Queue partition lock cleared and poison state re-enqueued for clean transit."
        resolution_rec = {"action": "RESET_BROKER_PARTITION_AND_RETRY", "target_queue": "FEDWIRE_OUTBOUND"}
    else:
        resolution_basis = "Message broker offline or partition corrupt."
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("pr09_payment_held_for_repair")
def pr09_payment_held_for_repair(ctx: ResolutionContext) -> ResolutionResult:
    """PR-09 PAYMENT_HELD_FOR_REPAIR (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import routing_clearing_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    status, uniq, cand, diff_log, err = routing_clearing_engine.resolve_pr09_held_for_repair(
        payment_id=pmt.payment_id,
        payment_uetr=pmt.uetr,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "payment_hub.queue_action", "repaired_value": "RELEASE_AFTER_SYNTAX_VALIDATION"}]
        resolution_rec = {"action": "RELEASE_FROM_REPAIR_QUEUE", **struct_data}
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated PR-09")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)
