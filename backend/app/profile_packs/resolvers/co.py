"""Compliance resolvers: pure functions lifted verbatim from the e2e_runner branches (behaviour unchanged;
the golden tests prove it). Generated once by scratch/gen_packs.py, maintained by hand from now on."""
from app.profile_packs.registry import register_resolver
from app.profile_packs.schema import ResolutionContext, ResolutionResult


@register_resolver("co04_restricted_corridor")
def co04_restricted_corridor(ctx: ResolutionContext) -> ResolutionResult:
    """CO-04 RESTRICTED_CORRIDOR (lifted verbatim from the e2e_runner branch)."""
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    is_cleared = evidence_ctx.get("ofac_license_exemption_verified", False)
    if is_cleared:
        r_det = True
        r_uniq = True
        v_det = True
        resolution_basis = "Corridor restricted under general policy, but specific OFAC general license exemption verified."
        resolution_rec = {"action": "RELEASE_CORRIDOR_HOLD", "license_id": "OFAC-GL-58A"}
    else:
        resolution_basis = "Mandatory statutory corridor restriction without verified licensing exemption."
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)


@register_resolver("co07_regulatory_reporting_required")
def co07_regulatory_reporting_required(ctx: ResolutionContext) -> ResolutionResult:
    """CO-07 REGULATORY_REPORTING_REQUIRED (lifted verbatim from the e2e_runner branch)."""
    from app.services.engines import remittance_document_engine
    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile
    r_det = False
    r_uniq = False
    v_det = False
    resolution_rec = None
    repaired_fields = []
    resolution_basis = ""
    status, uniq, cand, diff_log, err = remittance_document_engine.resolve_co07_regulatory_reporting(
        destination_country=evidence_ctx.get("destination_country") or evidence_ctx.get("creditor_country") or "BR",
        currency=pmt.currency,
        amount=pmt.amount,
        clearing_rail=pmt.clearing_rail,
        evidence_context=evidence_ctx
    )
    r_det = (status.value == "RESOLUTION_DETERMINED")
    r_uniq = (uniq.value == "RESOLUTION_UNIQUE")
    v_det = bool(r_det and cand is not None)
    if cand:
        struct_data = cand.repaired_structured or {}
        repaired_fields = [{"field_path": "regulatory_reporting", "repaired_value": struct_data}]
        resolution_rec = {"action": "POPULATE_REGULATORY_REPORTING", **struct_data}
    resolution_basis = "; ".join(diff_log) if diff_log else (err or "Evaluated CO-07")
    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),
                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)
