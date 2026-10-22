"""Settlement and returns resolvers: pure functions lifted verbatim from the e2e_runner branches (behaviour unchanged;
the golden tests prove it). Generated once by scratch/gen_packs.py, maintained by hand from now on."""
from app.profile_packs.registry import register_resolver
from app.profile_packs.schema import ResolutionContext, ResolutionResult


@register_resolver("st01_returned_payment")
def st01_returned_payment(ctx: ResolutionContext) -> ResolutionResult:
    """ST-01 RETURNED_PAYMENT (lifted verbatim from the e2e_runner branch)."""
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    orig_debit = evidence_ctx.get("original_debit_posted", True)
    if orig_debit:
        r_det = True
        r_uniq = True
        v_det = True
        repaired_fields = [{"field_path": "debtor_account.recredit_amount", "amount": pmt.amount, "currency": pmt.currency}]
        resolution_basis = "Inward pacs.004 return matched with posted debit. Preparing debtor ledger re-credit."
        resolution_rec = {"action": "RECREDIT_DEBTOR_LEDGER", "amount": pmt.amount, "currency": pmt.currency}
    else:
        resolution_basis = "Original payment debit not found or unposted in ledger."
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("st02_account_closed")
def st02_account_closed(ctx: ResolutionContext) -> ResolutionResult:
    """ST-02 ACCOUNT_CLOSED (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import account_master_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w2_policy_thresholds if active_policy else None
    status, uniq, cand, diff_log, err = account_master_engine.resolve_st02_account_closed(
        account_number=pmt.creditor_account or "",
        uetr=pmt.uetr,
        payment_id=pmt.payment_id,
        amount=pmt.amount,
        currency=pmt.currency,
        clearing_rail=pmt.clearing_rail,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        if "return_reason_code" in struct_data:
            repaired_fields = [{"field_path": "settlement_return.reason", "repaired_value": struct_data.get("return_reason_code")}]
        elif "successor_account_number" in struct_data:
            repaired_fields = [{"field_path": "creditor_account.account_number", "repaired_value": struct_data.get("successor_account_number")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated ST-02")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("st03_beneficiary_account_frozen")
def st03_beneficiary_account_frozen(ctx: ResolutionContext) -> ResolutionResult:
    """ST-03 BENEFICIARY_ACCOUNT_FROZEN (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import account_master_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w2_policy_thresholds if active_policy else None
    status, uniq, cand, diff_log, err = account_master_engine.resolve_st03_account_frozen(
        account_number=pmt.creditor_account or "",
        uetr=pmt.uetr,
        payment_id=pmt.payment_id,
        amount=pmt.amount,
        currency=pmt.currency,
        clearing_rail=pmt.clearing_rail,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        if "return_reason_code" in struct_data:
            repaired_fields = [{"field_path": "settlement_return.reason", "repaired_value": struct_data.get("return_reason_code")}]
        elif "suspense_gl_account" in struct_data:
            repaired_fields = [{"field_path": "general_ledger.suspense_account", "repaired_value": struct_data.get("suspense_gl_account")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated ST-03")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("st06_funds_trapped_at_correspondent")
def st06_funds_trapped_at_correspondent(ctx: ResolutionContext) -> ResolutionResult:
    """ST-06 FUNDS_TRAPPED_AT_CORRESPONDENT (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import wave4_resolution_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w4_policy_thresholds if active_policy else None
    inter_bic = evidence_ctx.get("intermediary_bic")
    status, uniq, cand, diff_log, err = wave4_resolution_engine.resolve_st06_funds_trapped(
        uetr=pmt.uetr,
        amount=pmt.amount,
        currency=pmt.currency,
        intermediary_bic=inter_bic,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = not bool(evidence_ctx.get("deterministic_validation_failed", False) or evidence_ctx.get("syntax_validation_failed", False))
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "transit_investigation.status", "repaired_value": struct_data.get("status")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated ST-06")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)
