"""Resolvers for profiles that run on the shared resolution engines (the same engines the dedicated pipelines use).

The runner hands over the bank's evidence and the raw payload; these resolvers build an evidence dossier from exactly
that (nothing is invented: a missing item stays missing), run the shared engine, and translate its result.
"""
import re
from typing import Any, Dict, List, Optional

from app.profile_packs.registry import get_pack, register_resolver
from app.profile_packs.schema import ResolutionContext, ResolutionResult
from app.schemas.evidence_contract import EvidenceDossier, EvidenceItem, EvidenceTrustTier
from app.schemas.resolution_contract import ResolutionStatus, ResolutionUniqueness

_TIER = {1: EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE, 2: EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
         3: EvidenceTrustTier.TIER_3_PEX_DERIVED, 4: EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT}


def build_dossier(ctx: ResolutionContext, metadata: Optional[Dict[str, Any]] = None, raw_item: str = "RAW_PAYLOAD") -> EvidenceDossier:
    """Evidence dossier made only from what the bank supplied. The raw payload comes from the input's raw_payload field."""
    pack = get_pack(ctx.profile)
    tiers = {e.type: e.tier for e in pack.evidence.required} if pack else {}
    case_id = str(getattr(ctx.pmt, "payment_id", None) or ctx.profile)
    d = EvidenceDossier(case_id=case_id, profile_id=ctx.profile, metadata=dict(metadata or {}))
    for key, val in ctx.evidence.items():
        name = str(key).upper()
        d.add_item(EvidenceItem(item_name=name, source_name="BANK_INPUT", trust_tier=_TIER[tiers.get(name, 1)],
                                payload=val if isinstance(val, dict) else {"value": val}))
    raw = ctx.extras.get("raw_payload") or {}
    text = raw.get("raw_text") or raw.get("raw_xml") if isinstance(raw, dict) else None
    if text and d.get_item(raw_item) is None:
        d.add_item(EvidenceItem(item_name=raw_item, source_name="BANK_INPUT", trust_tier=_TIER[1], payload={"raw_text": str(text)}))
    return d


def run_engine(dossier: EvidenceDossier):
    from app.schemas.authority_contract import AuthorityValidationStatus
    from app.services.authority_validation_engine import authority_validation_engine
    from app.services.resolution_engine import resolution_engine
    res = resolution_engine.derive_resolution(dossier)
    cand = res.primary_candidate
    determined = res.status == ResolutionStatus.RESOLUTION_DETERMINED and cand is not None
    unique = res.uniqueness == ResolutionUniqueness.RESOLUTION_UNIQUE
    validated = False
    if determined:
        auth = authority_validation_engine.validate_candidate(candidate=cand, profile_id=dossier.profile_id, dossier=dossier)
        validated = bool(auth.status == AuthorityValidationStatus.PASSED and auth.is_valid and cand.is_lossless and res.is_lossless)
    return res, determined, unique, validated


def _not_resolved(res, why: str) -> ResolutionResult:
    return ResolutionResult(determined=False, unique=ResolutionUniqueness.RESOLUTION_UNIQUE == res.uniqueness, validated=False,
                            repaired_fields=[], recommendation=None, basis=f"{why}: {res.error_message or 'not determined'}")


# ---------------------------------------------------------------------------------------------- DQ-02
_BIC_TAG = re.compile(r"<(?:BICFI|BIC)>([A-Z0-9]+)</(?:BICFI|BIC)>")


@register_resolver("dq02_bic_engine")
def dq02_bic_engine(ctx: ResolutionContext) -> ResolutionResult:
    """DQ-02 INVALID_BIC: structure, directory status, successor, rail reachability and SSI corroboration, by the shared engine."""
    meta = dict((ctx.extras.get("metadata") or {}))
    dossier = build_dossier(ctx, metadata={"allow_bic8_normalization": meta.get("allow_bic8_normalization", True)})
    res, determined, unique, validated = run_engine(dossier)
    if not determined:
        return _not_resolved(res, "BIC could not be resolved")
    orig_item = dossier.get_item("ORIGINAL_BIC_RECORD")
    orig = (orig_item.payload.get("bic_code") if orig_item else None) or ""

    def bic_of(c):
        m = _BIC_TAG.search(c.repaired_payload or "")
        return m.group(1) if m else None

    target = "creditor_agent.bic"
    if not unique:
        cands = [b for b in (bic_of(c) for c in res.candidates) if b]
        return ResolutionResult(determined=True, unique=False, validated=validated, repaired_fields=[],
                                recommendation={"action": "INVESTIGATION_HOLD", "target": target, "reason": "MULTIPLE_SUCCESSORS", "candidates": cands},
                                basis=f"{orig} has more than one authoritative successor ({', '.join(cands)}); a person must choose.")
    new = bic_of(res.primary_candidate) or orig
    basis = res.primary_candidate.diff_summary
    if new and new != orig:
        return ResolutionResult(determined=True, unique=True, validated=validated,
                                repaired_fields=[{"field_path": target, "original_value": orig, "repaired_value": new}],
                                recommendation={"action": "SUBSTITUTE_FIELD", "target": target, "value": new}, basis=basis)
    return ResolutionResult(determined=True, unique=True, validated=validated, repaired_fields=[],
                            recommendation={"action": "VALIDATE_NO_CHANGE", "target": target, "value": orig}, basis=basis)


# ---------------------------------------------------------------------------------------------- PR-03 / PR-05
def _payload_repair(ctx: ResolutionContext, dossier, field_path: str, unchanged: bool, why: str) -> ResolutionResult:
    res, determined, unique, validated = run_engine(dossier)
    if not determined:
        return _not_resolved(res, why)
    cand = res.primary_candidate
    if unchanged:
        return ResolutionResult(determined=True, unique=unique, validated=validated, repaired_fields=[],
                                recommendation={"action": "VALIDATE_NO_CHANGE", "target": field_path}, basis=cand.diff_summary)
    return ResolutionResult(determined=True, unique=unique, validated=validated,
                            repaired_fields=[{"field_path": field_path, "original_value": "as received", "repaired_value": cand.diff_summary}],
                            recommendation={"action": "REPLACE_PAYLOAD", "target": field_path, "value": cand.repaired_payload}, basis=cand.diff_summary)


@register_resolver("pr03_iso20022_structure")
def pr03_iso20022_structure(ctx: ResolutionContext) -> ResolutionResult:
    """PR-03 ISO 20022 error: lossless re-sequencing / envelope / namespace repair, checked against the schema spec."""
    d = build_dossier(ctx)
    res = None
    r = _payload_repair(ctx, d, "message.structure", False, "Message structure could not be repaired")
    if r.determined and r.recommendation is not None:
        c = run_engine(d)[0].primary_candidate
        if c.diff_summary.startswith("XML structure already valid"):
            r = _payload_repair(ctx, d, "message.structure", True, "")
    return r


@register_resolver("pr05_character_encoding")
def pr05_character_encoding(ctx: ResolutionContext) -> ResolutionResult:
    """PR-05 corrupted message: governed, lossless character / encoding transformation within the bank's transliteration policy."""
    d = build_dossier(ctx, raw_item="RAW_PAYLOAD_BYTES")
    c = run_engine(d)[0].primary_candidate
    return _payload_repair(ctx, d, "message.characters", bool(c and c.diff_summary.startswith("Zero character modifications")),
                           "Message could not be cleaned")


# ---------------------------------------------------------------------------------------------- DQ-06
_PURP = re.compile(r"<Purp>\s*<Cd>([A-Z0-9]+)</Cd>")


@register_resolver("dq06_purpose_code")
def dq06_purpose_code(ctx: ResolutionContext) -> ResolutionResult:
    """DQ-06 missing / invalid purpose code: inferred from remittance text, confirmed by the bank's purpose and corridor policy."""
    def item(name):
        v = ctx.evidence.get(name) or ctx.evidence.get(name.lower())
        return v if isinstance(v, dict) else {}
    meta = dict(ctx.extras.get("metadata") or {})
    pay = item("PAYMENT_CONTEXT")
    md = {"existing_purpose_code": item("PURPOSE_CODE_FIELD").get("purpose_code"),
          "remittance_text": item("REMITTANCE_INFORMATION").get("remittance_text"),
          "debtor_name": pay.get("debtor_name"), "creditor_name": pay.get("creditor_name"),
          "corridor_id": pay.get("corridor_id"), "currency": pay.get("currency"),
          "allow_stale_evidence": bool(meta.get("allow_stale_evidence", False))}
    d = build_dossier(ctx, metadata=md)
    res, determined, unique, validated = run_engine(d)
    if not determined:
        return _not_resolved(res, "Purpose code could not be determined")
    target, orig = "purpose.code", md["existing_purpose_code"]

    def code_of(c):
        m = _PURP.search(c.repaired_payload or "")
        return m.group(1) if m else None
    if not unique:
        cands = [x for x in (code_of(c) for c in res.candidates) if x]
        return ResolutionResult(determined=True, unique=False, validated=validated, repaired_fields=[],
                                recommendation={"action": "INVESTIGATION_HOLD", "target": target, "reason": "MULTIPLE_PURPOSE_CODES", "candidates": cands},
                                basis=f"The remittance supports more than one purpose code ({', '.join(cands)}); a person must choose.")
    new = code_of(res.primary_candidate)
    basis = res.primary_candidate.diff_summary
    if new and new != orig:
        return ResolutionResult(determined=True, unique=True, validated=validated,
                                repaired_fields=[{"field_path": target, "original_value": orig, "repaired_value": new}],
                                recommendation={"action": "SUBSTITUTE_FIELD" if orig else "INSERT_FIELD", "target": target, "value": new}, basis=basis)
    return ResolutionResult(determined=True, unique=True, validated=validated, repaired_fields=[],
                            recommendation={"action": "VALIDATE_NO_CHANGE", "target": target, "value": orig}, basis=basis)
