"""Data quality resolvers: pure functions lifted verbatim from the e2e_runner branches (behaviour unchanged;
the golden tests prove it). Generated once by scratch/gen_packs.py, maintained by hand from now on."""
from app.profile_packs.registry import register_resolver
from app.profile_packs.schema import ResolutionContext, ResolutionResult


@register_resolver("dq01_invalid_iban")
def dq01_invalid_iban(ctx: ResolutionContext) -> ResolutionResult:
    """DQ-01 INVALID_IBAN (lifted verbatim from the e2e_runner branch)."""
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    orig_iban = pmt.creditor_account or ""
    target_iban = evidence_ctx.get("verified_iban") or evidence_ctx.get("core_dda_account")
    has_contradiction = bool(
        envelope.contradictions
        or evidence_ctx.get("contradictory_evidence_flag", False)
        or evidence_ctx.get("contradiction_detected", False)
        or evidence_ctx.get("has_contradictory_evidence", False)
        or (
            evidence_ctx.get("core_dda_account")
            and evidence_ctx.get("ssi_directory_account")
            and str(evidence_ctx.get("core_dda_account")).strip() != str(evidence_ctx.get("ssi_directory_account")).strip()
        )
    )
    if target_iban and len(target_iban) >= 15:
        r_det = True
        r_uniq = not (has_contradiction or evidence_ctx.get("multiple_matching_ibans", False))
        v_det = not bool(evidence_ctx.get("deterministic_validation_failed", False) or evidence_ctx.get("syntax_validation_failed", False))
        repaired_fields = [{"field_path": "creditor_account.iban", "original_value": orig_iban, "repaired_value": target_iban}]
        if has_contradiction:
            resolution_basis = f"Contradictory evidence detected ({', '.join(envelope.contradictions) if envelope.contradictions else 'Core DDA vs SSI directory conflict'}); resolution is ambiguous. Routing to Human-in-the-Loop."
            resolution_rec = {"action": "INVESTIGATION_HOLD", "target": "creditor_account.iban", "candidate_value": target_iban, "reason": "CONTRADICTORY_EVIDENCE"}
        else:
            resolution_basis = f"IBAN MOD-97 check digit validated against the {pmt.clearing_rail or 'scheme'} routing directory."
            resolution_rec = {"action": "SUBSTITUTE_FIELD", "target": "creditor_account.iban", "value": target_iban}
    else:
        resolution_basis = "Unable to derive valid MOD-97 IBAN checksum."
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("dq03_missing_beneficiary")
def dq03_missing_beneficiary(ctx: ResolutionContext) -> ResolutionResult:
    """DQ-03 MISSING_BENEFICIARY_DATA (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import account_master_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    debtor_id = evidence_ctx.get("debtor_id") or pmt.debtor_name or "DEBTOR-001"
    cred_hint = evidence_ctx.get("creditor_hint") or pmt.creditor_name or pmt.creditor_account
    status, uniq, cand, diff_log, err = account_master_engine.resolve_dq03_missing_beneficiary(
        debtor_id=debtor_id,
        account_number=pmt.creditor_account or "",
        creditor_hint=cred_hint,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "creditor.name", "repaired_value": struct_data.get("creditor_name")}]
        resolution_rec = {"action": "POPULATE_BENEFICIARY_DATA", **struct_data}
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated DQ-03")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("dq04_missing_remittance_info")
def dq04_missing_remittance_info(ctx: ResolutionContext) -> ResolutionResult:
    """DQ-04 MISSING_REMITTANCE_INFO (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import remittance_document_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    inv_ref = evidence_ctx.get("invoice_reference_number") or pmt.remittance_info or ""
    status, uniq, cand, diff_log, err = remittance_document_engine.resolve_dq04_missing_remittance(
        invoice_id_or_narrative=inv_ref,
        amount=pmt.amount,
        currency=pmt.currency,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "remittance_info.structured", "repaired_value": struct_data}]
        resolution_rec = {"action": "POPULATE_STRUCTURED_REMITTANCE", **struct_data}
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated DQ-04")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("dq05_invalid_address_format")
def dq05_invalid_address_format(ctx: ResolutionContext) -> ResolutionResult:
    """DQ-05 INVALID_ADDRESS_FORMAT (lifted verbatim from the e2e_runner branch)."""
    from app.services.eur_rail_overlay import resolve_dq05
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    from app.services.eur_rail_overlay import resolve_dq05
    _d5 = resolve_dq05(evidence_ctx)
    r_det, r_uniq, v_det = _d5["r_det"], _d5["r_uniq"], _d5["v_det"]
    repaired_fields = _d5["repaired_fields"]
    resolution_rec = _d5["rec"]
    resolution_basis = _d5["basis"]
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("dq07_invalid_account_number")
def dq07_invalid_account_number(ctx: ResolutionContext) -> ResolutionResult:
    """DQ-07 INVALID_ACCOUNT_NUMBER (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import account_master_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    status, uniq, cand, diff_log, err = account_master_engine.resolve_dq07_invalid_account_number(
        inbound_account_number=pmt.creditor_account or "",
        clearing_rail=pmt.clearing_rail,
        currency=pmt.currency,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "creditor_account.account_number", "original_value": pmt.creditor_account, "repaired_value": struct_data.get("account_number")}]
        resolution_rec = {"action": "SUBSTITUTE_ACCOUNT_NUMBER", **struct_data}
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated DQ-07")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("dq08_invalid_routing_code")
def dq08_invalid_routing_code(ctx: ResolutionContext) -> ResolutionResult:
    """DQ-08 INVALID_ROUTING_CODE (lifted verbatim from the e2e_runner branch)."""
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    orig_routing = evidence_ctx.get("inbound_routing_code", "021000020")
    valid_routing = evidence_ctx.get("valid_routing_code", "021000021")
    is_ambiguous = evidence_ctx.get("ambiguous_routing_matches", False)
    if valid_routing and len(valid_routing) == 9:
        r_det = True
        r_uniq = not is_ambiguous
        v_det = True # 9-digit ABA checksum valid
        repaired_fields = [{"field_path": "creditor_agent.aba_routing", "original_value": orig_routing, "repaired_value": valid_routing}]
        resolution_basis = "ABA routing transit check digit validated via FedLine directory."
        resolution_rec = {"action": "SUBSTITUTE_FIELD", "target": "creditor_agent.aba_routing", "value": valid_routing}
    else:
        resolution_basis = "Invalid routing number syntax."
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("dq09_beneficiary_name_mismatch")
def dq09_beneficiary_name_mismatch(ctx: ResolutionContext) -> ResolutionResult:
    """DQ-09 BENEFICIARY_NAME_MISMATCH (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import account_master_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    active_policy = ctx.policy
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    pol_thresholds = active_policy.w1_matching_thresholds if active_policy else None
    status, uniq, cand, diff_log, err = account_master_engine.resolve_dq09_beneficiary_name_mismatch(
        account_number=pmt.creditor_account or "",
        inbound_payee_name=pmt.creditor_name or "",
        policy_thresholds=pol_thresholds,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "creditor.name", "original_value": pmt.creditor_name, "repaired_value": struct_data.get("creditor_name")}]
        resolution_rec = {"action": "ALIGN_BENEFICIARY_TITLE", **struct_data}
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated DQ-09")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)
