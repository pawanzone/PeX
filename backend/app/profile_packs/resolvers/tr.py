"""Treasury and client resolvers: pure functions lifted verbatim from the e2e_runner branches (behaviour unchanged;
the golden tests prove it). Generated once by scratch/gen_packs.py, maintained by hand from now on."""
from app.profile_packs.registry import register_resolver
from app.profile_packs.schema import ResolutionContext, ResolutionResult


@register_resolver("tr01_kyc_expired")
def tr01_kyc_expired(ctx: ResolutionContext) -> ResolutionResult:
    """TR-01 KYC_EXPIRED (lifted verbatim from the e2e_runner branch)."""
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
    cli_id = evidence_ctx.get("client_id") or pmt.debtor_name or "CLI-CORP-001"
    status, uniq, cand, diff_log, err = wave4_resolution_engine.resolve_tr01_kyc_expired(
        client_id=cli_id,
        amount=pmt.amount,
        currency=pmt.currency,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = not bool(evidence_ctx.get("deterministic_validation_failed", False) or evidence_ctx.get("syntax_validation_failed", False))
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "customer_kyc.provisional_status", "repaired_value": struct_data.get("provisional_status")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated TR-01")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("tr02_insufficient_funds")
def tr02_insufficient_funds(ctx: ResolutionContext) -> ResolutionResult:
    """TR-02 INSUFFICIENT_FUNDS (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import treasury_exposure_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w3_policy_thresholds if active_policy else None
    status, uniq, cand, diff_log, err = treasury_exposure_engine.resolve_tr02_insufficient_funds(
        account_number=pmt.debtor_account or evidence_ctx.get("debtor_account") or "ACCT-CORP-USD-001",
        instructed_amount=pmt.amount,
        currency=pmt.currency,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = not bool(evidence_ctx.get("deterministic_validation_failed", False) or evidence_ctx.get("syntax_validation_failed", False))
    if cand:
        struct_data = cand.repaired_structured or {}
        if "reservation_id" in struct_data:
            repaired_fields = [{"field_path": "treasury.reservation_id", "repaired_value": struct_data.get("reservation_id")}]
        elif "pacing_schedule" in struct_data:
            repaired_fields = [{"field_path": "treasury.pacing_schedule", "repaired_value": struct_data.get("pacing_schedule")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated TR-02")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("tr03_nostro_shortfall")
def tr03_nostro_shortfall(ctx: ResolutionContext) -> ResolutionResult:
    """TR-03 NOSTRO_SHORTFALL (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import treasury_exposure_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w3_policy_thresholds if active_policy else None
    nostro_bic = evidence_ctx.get("nostro_bic") or pmt.creditor_agent_bic or "BNPAFRPPXXX"
    status, uniq, cand, diff_log, err = treasury_exposure_engine.resolve_tr03_nostro_shortfall(
        nostro_bic=nostro_bic,
        instructed_amount=pmt.amount,
        currency=pmt.currency,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = not bool(evidence_ctx.get("deterministic_validation_failed", False) or evidence_ctx.get("syntax_validation_failed", False))
    if cand:
        struct_data = cand.repaired_structured or {}
        if "rebalancing_candidate" in struct_data:
            repaired_fields = [{"field_path": "treasury.nostro_rebalancing", "repaired_value": struct_data.get("rebalancing_candidate")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated TR-03")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("tr04_fx_rate_unavailable")
def tr04_fx_rate_unavailable(ctx: ResolutionContext) -> ResolutionResult:
    """TR-04 FX_RATE_UNAVAILABLE (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import treasury_exposure_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w3_policy_thresholds if active_policy else None
    pair = evidence_ctx.get("currency_pair") or f"{pmt.currency}/USD"
    settle_ccy = evidence_ctx.get("settlement_currency") or "USD"
    status, uniq, cand, diff_log, err = treasury_exposure_engine.resolve_tr04_fx_rate_unavailable(
        currency_pair=pair,
        instructed_amount=pmt.amount,
        instructed_currency=pmt.currency,
        settlement_currency=settle_ccy,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = not bool(evidence_ctx.get("deterministic_validation_failed", False) or evidence_ctx.get("syntax_validation_failed", False))
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [
            {"field_path": "payment.fx_applied_rate", "repaired_value": struct_data.get("applied_rate")},
            {"field_path": "payment.settlement_amount", "repaired_value": struct_data.get("settlement_amount")}
        ]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated TR-04")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("tr05_authorization_missing")
def tr05_authorization_missing(ctx: ResolutionContext) -> ResolutionResult:
    """TR-05 AUTHORIZATION_MISSING (lifted verbatim from the e2e_runner branch)."""
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
    acct = pmt.debtor_account or "ACCT-CORP-USD-001"
    sec_sig = evidence_ctx.get("secondary_signatory_id")
    status, uniq, cand, diff_log, err = wave4_resolution_engine.resolve_tr05_authorization_missing(
        debtor_account=acct,
        amount=pmt.amount,
        currency=pmt.currency,
        primary_signatory_id=evidence_ctx.get("primary_signatory_id"),
        secondary_signatory_id=sec_sig,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = not bool(evidence_ctx.get("deterministic_validation_failed", False) or evidence_ctx.get("syntax_validation_failed", False))
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "mandate_authorization.status", "repaired_value": struct_data.get("authorization_status")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated TR-05")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("tr06_limit_breach")
def tr06_limit_breach(ctx: ResolutionContext) -> ResolutionResult:
    """TR-06 LIMIT_BREACH (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import treasury_exposure_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w3_policy_thresholds if active_policy else None
    lim_id = evidence_ctx.get("limit_id") or "LIM-DAILY-CORP-01"
    cli_id = evidence_ctx.get("client_id") or pmt.debtor_name or "CLI-CORP-001"
    acct = pmt.debtor_account or "ACCT-CORP-USD-001"
    status, uniq, cand, diff_log, err = treasury_exposure_engine.resolve_tr06_limit_breach(
        limit_id=lim_id,
        client_id=cli_id,
        account_number=acct,
        instructed_amount=pmt.amount,
        currency=pmt.currency,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = not bool(evidence_ctx.get("deterministic_validation_failed", False) or evidence_ctx.get("syntax_validation_failed", False))
    if cand:
        struct_data = cand.repaired_structured or {}
        if "pacing_schedule" in struct_data:
            repaired_fields = [{"field_path": "treasury.limit_pacing", "repaired_value": struct_data.get("pacing_schedule")}]
        elif "dossier_id" in struct_data:
            repaired_fields = [{"field_path": "compliance.waiver_dossier_id", "repaired_value": struct_data.get("dossier_id")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated TR-06")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("tr07_liquidity_constraint")
def tr07_liquidity_constraint(ctx: ResolutionContext) -> ResolutionResult:
    """TR-07 LIQUIDITY_CONSTRAINT (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import treasury_exposure_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w3_policy_thresholds if active_policy else None
    clr_ctx = evidence_ctx.get("clearing_context") or pmt.clearing_rail or "FEDWIRE"
    status, uniq, cand, diff_log, err = treasury_exposure_engine.resolve_tr07_liquidity_constraint(
        clearing_context=clr_ctx,
        instructed_amount=pmt.amount,
        currency=pmt.currency,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = not bool(evidence_ctx.get("deterministic_validation_failed", False) or evidence_ctx.get("syntax_validation_failed", False))
    if cand:
        struct_data = cand.repaired_structured or {}
        if "pacing_schedule" in struct_data:
            repaired_fields = [{"field_path": "treasury.liquidity_pacing", "repaired_value": struct_data.get("pacing_schedule")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated TR-07")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("tr08_credit_exposure_breach")
def tr08_credit_exposure_breach(ctx: ResolutionContext) -> ResolutionResult:
    """TR-08 CREDIT_EXPOSURE_BREACH (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import treasury_exposure_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w3_policy_thresholds if active_policy else None
    cpty_id = evidence_ctx.get("counterparty_id") or pmt.debtor_name or "CPTY-CORP-ALPHA"
    fac_id = evidence_ctx.get("facility_id") or "FAC-ALPHA-01"
    status, uniq, cand, diff_log, err = treasury_exposure_engine.resolve_tr08_credit_exposure_breach(
        counterparty_id=cpty_id,
        instructed_amount=pmt.amount,
        currency=pmt.currency,
        facility_id=fac_id,
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = not bool(evidence_ctx.get("deterministic_validation_failed", False) or evidence_ctx.get("syntax_validation_failed", False))
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "compliance.credit_dossier_id", "repaired_value": struct_data.get("dossier_id")}]
        resolution_rec = struct_data
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated TR-08")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)
