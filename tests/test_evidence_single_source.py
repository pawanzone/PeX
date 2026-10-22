"""Profile packs are the single source of mandatory evidence (types, tiers, order)."""
import pytest

from app.profile_packs import registry
from app.schemas.contracts.evidence_config_schemas import EvidenceAcquisitionMode  # noqa: F401
from app.services.dynamic_config_resolver import DynamicEvidenceConfigResolver
from app.services.e2e_runner import E2EExecutionHarness

CODES = sorted(registry.load_packs())


class _NoPublishedConfig:
    def get_evidence_config(self, tenant_id, profile_id):
        return None


@pytest.mark.parametrize("code", CODES)
def test_every_pack_declares_its_evidence(code):
    p = registry.get_pack(code)
    assert p.evidence.required, code
    assert p.evidence.mandatory_types, f"{code} has no mandatory evidence"


@pytest.mark.parametrize("code", CODES)
def test_published_reference_config_equals_pack(code):
    """What the engine asks for at runtime equals what the pack declares (types, tiers, order, optional)."""
    p = registry.get_pack(code)
    r = E2EExecutionHarness().dynamic_config_resolver.resolve_requirements("DEFAULT_BANK", code, {})
    assert r.active_mandatory_types == p.evidence.mandatory_types, code
    assert r.active_optional_types == p.evidence.optional_types, code
    for e in p.evidence.required:
        assert r.min_trust_tiers[e.type].value == e.tier, (code, e.type)


@pytest.mark.parametrize("code", CODES)
def test_with_nothing_published_the_pack_decides(code):
    p = registry.get_pack(code)
    r = DynamicEvidenceConfigResolver(_NoPublishedConfig()).resolve_requirements("DEFAULT_BANK", code, {})
    assert r.active_mandatory_types == p.evidence.mandatory_types, code
    assert r.active_optional_types == p.evidence.optional_types, code


def test_legacy_fallback_map_is_gone():
    import inspect
    from app.services import dynamic_config_resolver as m
    assert "fallback_mandatory_map" not in inspect.getsource(m)


@pytest.mark.parametrize("code", CODES)
def test_ui_profile_spec_shows_pack_evidence(code):
    from app.services.v2 import core
    assert core.profile_spec(code)["mandatory_evidence"] == registry.get_pack(code).evidence.mandatory_types, code


def test_exception_types_list_shows_pack_evidence():
    from app.services.v2 import admin
    items = {i["code"]: i for i in admin.exception_types()["items"]}
    for code in CODES:
        assert items[code]["mandatory_evidence"] == registry.get_pack(code).evidence.mandatory_types, code
