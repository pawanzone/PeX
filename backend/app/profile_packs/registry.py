"""Loads packs, holds the resolver registry, and applies the per-profile switch."""
import json
import logging
import os
from pathlib import Path
from typing import Callable, Dict, Optional

from app.profile_packs.schema import ProfilePack, ResolutionContext, ResolutionResult

logger = logging.getLogger("pex.profile_packs")

PACK_DIR = Path(__file__).parent / "packs"
_RESOLVERS: Dict[str, Callable[[ResolutionContext], ResolutionResult]] = {}
_cache: Optional[Dict[str, ProfilePack]] = None
_OFF = {"OFF", "NONE", "0", "FALSE"}


def register_resolver(name: str):
    def deco(fn):
        _RESOLVERS[name] = fn
        return fn
    return deco


def get_resolver(name: str):
    _ensure_resolvers()
    return _RESOLVERS.get(name)


def _ensure_resolvers():
    from app.profile_packs import resolvers  # noqa: F401  (importing registers them)


def load_packs(directory: Optional[Path] = None) -> Dict[str, ProfilePack]:
    """Load and validate every pack in a directory. The bundled set is cached."""
    global _cache
    if directory is None and _cache is not None:
        return _cache
    _ensure_resolvers()
    folder = Path(directory) if directory is not None else PACK_DIR
    packs: Dict[str, ProfilePack] = {}
    for f in sorted(folder.glob("*.json")):
        pack = ProfilePack(**json.loads(f.read_text(encoding="utf-8")))
        if pack.code in packs:
            raise ValueError(f"duplicate pack for {pack.code} ({f.name})")
        if pack.resolver and pack.resolver not in _RESOLVERS:
            raise ValueError(f"pack {pack.code} names unknown resolver {pack.resolver!r}")
        packs[pack.code] = pack
    if directory is None:
        _cache = packs
    return packs


def get_pack(code: str) -> Optional[ProfilePack]:
    return load_packs().get((code or "").upper())


def is_enabled(code: str) -> bool:
    """On by default for every profile that has a pack. PEX_PROFILE_PACKS narrows it to a list (DQ-03,PR-02)
    or switches it off (off / none / 0 / false) to fall back to the legacy branches."""
    raw = os.environ.get("PEX_PROFILE_PACKS", "*").strip()
    wanted = {p.strip().upper() for p in raw.split(",") if p.strip()}
    code = (code or "").upper()
    if not wanted or wanted & _OFF or get_pack(code) is None:
        return False
    return "*" in wanted or code in wanted


_APPROVAL = {"MAKER_CHECKER": "MAKER_CHECKER_DUAL_AUTH", "SINGLE": "SINGLE_APPROVER",
             "COMPLIANCE_THEN_RISK": "COMPLIANCE_THEN_RISK_SIGN_OFF"}
_STRICT_DEFAULT = "MAKER_CHECKER_DUAL_AUTH"


def approval_requirement_for(code: str, stp_eligible: bool) -> str:
    """Who must authorise a case. Straight-through needs nobody; otherwise the pack decides.
    Anything unknown, or packs switched off, gets the strictest existing rule. The amount rule (dual
    authorisation from the policy threshold) is applied on top by the workflow layer and only tightens."""
    if stp_eligible:
        return "NONE_AUTONOMOUS_STP"
    if not is_enabled(code):
        return _STRICT_DEFAULT
    pack = get_pack(code)
    if pack is None:
        return _STRICT_DEFAULT
    return _APPROVAL.get(str(getattr(pack.approval.when_not_stp, "value", pack.approval.when_not_stp)), _STRICT_DEFAULT)


def never_stp_reason(code: str) -> Optional[str]:
    """Text to show when a pack forbids straight-through; None when it does not apply."""
    if not is_enabled(code):
        return None
    pack = get_pack(code)
    if pack is not None and str(getattr(pack.stp, "value", pack.stp)) == "NEVER":
        return f"Profile {code} is never straight-through; a person must decide."
    return None


def _decision_support(pack: ProfilePack, ctx: ResolutionContext) -> ResolutionResult:
    """Generic resolver for decision-support packs: reports evidence completeness and asks a named reviewer to
    choose among the pack's options. It never picks an option and never repairs anything."""
    env, d = ctx.envelope, pack.decision
    missing = list(getattr(env, "missing_mandatory_types", None) or [])
    stale = list(getattr(env, "stale_types", None) or [])
    conflicting = list(getattr(env, "contradictions", None) or [])
    if bool(getattr(env, "evidence_sufficient", False)):
        return ResolutionResult(
            determined=False, unique=True, validated=True,
            recommendation={"action": "DECISION_REQUIRED", "target": d.target_field, "options": list(d.options),
                            "reviewer_role": d.reviewer_role, "evidence_complete": True},
            basis=(f"Evidence is complete for {pack.code}. {d.reviewer_role} must choose a disposition for "
                   f"{d.target_field}; PeX does not decide this and it is never straight-through."))
    return ResolutionResult(
        determined=False, unique=False, validated=False,
        recommendation={"action": "INVESTIGATION_HOLD", "reason": "EVIDENCE_INCOMPLETE", "target": d.target_field,
                        "missing": missing + stale, "conflicting": conflicting, "evidence_complete": False},
        basis=(f"Evidence is incomplete for {pack.code} (missing {missing or 'none'}, stale {stale or 'none'}, "
               f"conflicting {conflicting or 'none'}). Gather it before {d.reviewer_role} decides."))


def resolve_if_enabled(code: str, ctx: ResolutionContext) -> Optional[ResolutionResult]:
    """None means 'use the legacy path'. Anything wrong inside a pack fails closed to human review."""
    if not is_enabled(code):
        return None
    pack = get_pack(code)
    if not pack.resolver and pack.decision is not None:
        try:
            return _decision_support(pack, ctx)
        except Exception as exc:
            logger.exception("decision support for %s failed", code)
            return ResolutionResult(basis=f"Decision support for {code} failed ({type(exc).__name__}); failing closed to human review.")
    if not pack.resolver:
        return ResolutionResult(basis=f"{code} is a decision-support profile: evidence is gathered and a person decides (fail closed).")
    try:
        fn = get_resolver(pack.resolver)
        if fn is None:
            raise LookupError(f"resolver {pack.resolver!r} is not registered")
        return fn(ctx)
    except Exception as exc:
        logger.exception("resolver for %s failed", code)
        return ResolutionResult(basis=f"Resolver for {code} failed ({type(exc).__name__}); failing closed to human review.")
