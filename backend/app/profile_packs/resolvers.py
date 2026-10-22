"""Resolvers: the only profile-specific code. Each is a pure function ResolutionContext -> ResolutionResult.

They are lifted from the inline branches of e2e_runner without changing behaviour (the goldens prove it).
"""
from app.profile_packs.registry import register_resolver
from app.profile_packs.schema import ResolutionContext, ResolutionResult


@register_resolver("dq03_missing_beneficiary")
def dq03_missing_beneficiary(ctx: ResolutionContext) -> ResolutionResult:
    from app.services.engines import account_master_engine
    pmt, ev = ctx.pmt, ctx.evidence
    debtor_id = ev.get("debtor_id") or pmt.debtor_name or "DEBTOR-001"
    cred_hint = ev.get("creditor_hint") or pmt.creditor_name or pmt.creditor_account
    status, uniq, cand, diff_log, err = account_master_engine.resolve_dq03_missing_beneficiary(
        debtor_id=debtor_id,
        account_number=pmt.creditor_account or "",
        creditor_hint=cred_hint,
        evidence_context=ev,
    )
    determined = (status.value == "RESOLUTION_DETERMINED")
    unique = (uniq.value == "RESOLUTION_UNIQUE")
    res = ResolutionResult(determined=determined, unique=unique, validated=bool(determined and cand is not None))
    if cand:
        struct_data = cand.repaired_structured or {}
        res.repaired_fields = [{"field_path": "creditor.name", "repaired_value": struct_data.get("creditor_name")}]
        res.recommendation = {"action": "POPULATE_BENEFICIARY_DATA", **struct_data}
    res.basis = "; ".join(diff_log) if diff_log else (err or "Evaluated DQ-03")
    return res
