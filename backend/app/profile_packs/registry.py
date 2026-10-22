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


def resolve_if_enabled(code: str, ctx: ResolutionContext) -> Optional[ResolutionResult]:
    """None means 'use the legacy path'. Anything wrong inside a pack fails closed to human review."""
    if not is_enabled(code):
        return None
    pack = get_pack(code)
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
