"""Tests for the advisory local-LLM gateway using a fake OpenAI-compatible server.

The LLM is ADVISORY ONLY: deterministic fields (action, confidence, proposed changes, risk,
policies) must never change; failures degrade to the deterministic recommendation.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.config import settings
from app.schemas.bank_events import RawBankEvent
from app.services.canonicalizer import canonicalizer
from app.services.evidence_planner import evidence_planner
from app.services.context_builder import context_builder
from app.services.model_gateway import model_gateway
from app.services.llm_provider import llm_provider, LLMStatus, PROMPT_VERSION, scrub, extract_json_object
from app.services.data_loader import repo

SECRET_NAMES = ["HarborView Supplier Ltd", "Acme Global Holdings"]
SECRET_ACCOUNTS = ["GB82WEST12345698765432", "US89CHAS12345678901234", "GB82WEST12345698765423"]


# ----------------------------------------------------------------------------------------
# Fake OpenAI-compatible server
# ----------------------------------------------------------------------------------------
class _State:
    behavior = "ok"
    requests = []       # captured POST bodies (dicts)
    gets = []


def _good_payload(user_payload):
    ev_ids = [e["evidence_id"] for e in user_payload.get("evidence", [])][:2]
    cands = user_payload["deterministic_finding"]["candidates"]
    return {
        "rationale": "The deterministic checks found a check-digit failure that matches the directory entry.",
        "hypotheses": [
            {"title": "Digit transposition in account number", "confidence": 0.9, "status": "SELECTED", "evidence_ids": ev_ids},
            {"title": "Wrong bank identifier", "confidence": 0.05, "status": "ELIMINATED",
             "evidence_ids": ev_ids[:1], "elimination_reason": "Bank identifier validates."},
        ],
        "guided_questions": [{"category": "Verification", "question": "Does the client confirm the corrected account?",
                              "investigation_tip": "Use the call-back number on file."}],
        "consequence_summary": "Acting now meets the cut-off; waiting risks a late-payment claim.",
        "selected_candidate_id": cands[0]["candidate_id"] if cands else None,
        "proposed_value_hint": cands[0]["proposed_tail"] if cands else None,
        "cited_evidence_ids": ev_ids,
    }


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def _send(self, code, obj):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        _State.gets.append(self.path)
        if self.path.endswith("/models"):
            self._send(200, {"data": [{"id": "qwen2.5:7b-instruct"}]})
        else:
            self._send(404, {})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n) or b"{}")
        _State.requests.append(body)
        b = _State.behavior
        user_payload = json.loads(body["messages"][1]["content"])
        fmt = (body.get("response_format") or {}).get("type")
        if b == "timeout":
            time.sleep(2.0)
        if b == "format_400" and fmt == "json_schema":
            return self._send(400, {"error": "response_format not supported"})
        if b == "http_500":
            return self._send(500, {"error": "boom"})
        content = None
        if b in ("ok", "format_400", "timeout"):
            content = json.dumps(_good_payload(user_payload))
        elif b == "think_fenced":
            content = "<think>let me reason about this { not json }</think>\n```json\n" + json.dumps(_good_payload(user_payload)) + "\n```"
        elif b == "bad_json":
            content = "Sure! The answer is: I think you should repair the IBAN."
        elif b == "bad_schema":
            content = json.dumps({"hypotheses": "nope"})
        elif b == "hallucinate":
            p = _good_payload(user_payload)
            p["selected_candidate_id"] = "CAND-9"
            p["proposed_value_hint"] = "***9999"
            content = json.dumps(p)
        elif b == "unknown_evidence":
            p = _good_payload(user_payload)
            p["hypotheses"][0]["evidence_ids"] = ["EVID-FAKE-1"] + p["hypotheses"][0]["evidence_ids"]
            p["cited_evidence_ids"] = ["EVID-FAKE-2"]
            content = json.dumps(p)
        self._send(200, {
            "model": "qwen2.5:7b-instruct",
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 812, "completion_tokens": 233},
        })


@pytest.fixture
def fake_llm(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    _State.behavior = "ok"
    _State.requests = []
    _State.gets = []
    monkeypatch.setattr(settings, "LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_BASE_URL", f"http://127.0.0.1:{port}/v1")
    monkeypatch.setattr(settings, "LLM_MODEL", "qwen2.5:7b-instruct")
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 0.7)
    llm_provider.reset()
    yield _State
    server.shutdown()
    llm_provider.reset()


@pytest.fixture
def audit_capture(monkeypatch):
    calls = []
    real = repo.log_audit_event

    def _cap(**kw):
        calls.append(kw)
        return real(**kw)
    monkeypatch.setattr(repo, "log_audit_event", _cap)
    return calls


def _make_context(case_suffix="1"):
    event = RawBankEvent(
        event_id=f"EVT-LLM-{case_suffix}",
        source_bank_id="BANK_A",
        event_type="PAYMENT_EXCEPTION",
        raw_payload={
            "payment_reference": f"REF-LLM-{case_suffix}",
            "error_code": "ERR_IBAN_MOD97",
            "error_message": "Beneficiary IBAN failed MOD-97 check validation",
            "amount": 42000.0,
            "currency": "USD",
            "debtor_name": "Acme Global Holdings",
            "debtor_account": "US89CHAS12345678901234",
            "creditor_name": "HarborView Supplier Ltd",
            "creditor_iban": "GB82WEST12345698765423",
        },
    )
    pmt, exc = canonicalizer.canonicalize_bank_event(event)
    evidence, policies, hist = evidence_planner.plan_and_gather_evidence(
        case_id=exc.case_id, profile=exc.profile, party_name=pmt.creditor_party.party_name,
        account_val=pmt.creditor_account.iban, currency=pmt.currency,
    )
    return context_builder.build_investigation_context(
        payment=pmt, exception=exc, evidence_items=evidence, policies=policies, historical_cases=hist
    )


def _det_fields(rec):
    d = rec.model_dump(mode="json")
    keep = ["action_type", "confidence_score", "proposed_changes", "risk_evaluation", "applied_policies",
            "ambiguity_detected", "step_by_step_assessment"]
    return {k: d[k] for k in keep}


def _baseline(ctx):
    """Deterministic recommendation with the LLM layer off."""
    old = settings.LLM_ENABLED
    settings.LLM_ENABLED = False
    try:
        repo.recommendations.pop(ctx.case_id, None)
        return model_gateway.evaluate_investigation(ctx)
    finally:
        settings.LLM_ENABLED = old
        repo.recommendations.pop(ctx.case_id, None)


# ----------------------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------------------
def test_disabled_returns_deterministic_output_unchanged(monkeypatch):
    monkeypatch.setattr(settings, "LLM_ENABLED", False)
    ctx = _make_context("dis")
    repo.recommendations.pop(ctx.case_id, None)
    a = model_gateway.evaluate_investigation(ctx)
    repo.recommendations.pop(ctx.case_id, None)
    b = model_gateway.evaluate_investigation(ctx)
    assert a.llm_status is None and a.model_version is None and a.llm_flags == []
    da, db_ = a.model_dump(mode="json"), b.model_dump(mode="json")
    for k in ("generated_at",):
        da.pop(k), db_.pop(k)
    assert da == db_
    assert llm_provider.advise(ctx, a).status == LLMStatus.DISABLED


def test_happy_path_enriches_but_never_changes_deterministic_fields(fake_llm, audit_capture):
    ctx = _make_context("ok")
    base = _baseline(ctx)
    rec = model_gateway.evaluate_investigation(ctx)

    assert rec.llm_status == "OK"
    assert rec.model_version == "ollama:qwen2.5:7b-instruct" or rec.model_version.endswith(":qwen2.5:7b-instruct")
    assert rec.prompt_version == PROMPT_VERSION
    assert rec.prompt_tokens == 812 and rec.completion_tokens == 233      # real usage, not 120/45
    assert rec.latency_ms is not None and rec.latency_ms >= 0
    assert rec.llm_disagreement is False
    # advisory content applied
    assert rec.rationale.startswith("The deterministic checks found")
    assert rec.deterministic_rationale == base.rationale
    assert [h.source for h in rec.hypothesis_ranking] == ["LLM_ESTIMATE"] * len(rec.hypothesis_ranking)
    assert rec.consequence_simulation is not None and rec.consequence_simulation.narrative
    # evidence refs resolve to real evidence ids
    valid = {e.evidence_id for e in ctx.evidence_items}
    for h in rec.hypothesis_ranking:
        assert set(h.evidence_ids) <= valid
    # deterministic fields untouched
    assert _det_fields(rec) == _det_fields(base)
    # audit-visible record
    ev = [c for c in audit_capture if c["stage_name"] == "AI_ADVISORY"]
    assert ev and "model_version=" in ev[-1]["details"] and f"prompt_version={PROMPT_VERSION}" in ev[-1]["details"]
    assert "Advisory only" in ev[-1]["control_tags"]
    # request used schema-constrained output
    assert fake_llm.requests[0]["response_format"]["type"] == "json_schema"


def test_format_fallback_when_server_rejects_json_schema(fake_llm):
    fake_llm.behavior = "format_400"
    rec = model_gateway.evaluate_investigation(_make_context("f400"))
    assert rec.llm_status == "OK"
    assert [r["response_format"]["type"] if "response_format" in r else None for r in fake_llm.requests][:2] == ["json_schema", "json_object"]


def test_think_tags_and_code_fences_are_tolerated(fake_llm):
    fake_llm.behavior = "think_fenced"
    rec = model_gateway.evaluate_investigation(_make_context("think"))
    assert rec.llm_status == "OK"


def test_unreachable_falls_back_to_deterministic(monkeypatch, audit_capture):
    monkeypatch.setattr(settings, "LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_BASE_URL", "http://127.0.0.1:1/v1")
    llm_provider.reset()
    ctx = _make_context("unr")
    base = _baseline(ctx)
    rec = model_gateway.evaluate_investigation(ctx)
    assert rec.llm_status == "UNREACHABLE"
    assert "llm_unreachable" in rec.llm_flags
    assert _det_fields(rec) == _det_fields(base)
    assert rec.rationale == base.rationale
    assert rec.model_version is None
    assert all(h.source in ("SIMULATED", "DETERMINISTIC") for h in rec.hypothesis_ranking)
    # circuit breaker: second call returns quickly without another network attempt
    t0 = time.perf_counter()
    rec2 = model_gateway.evaluate_investigation(_make_context("unr2"))
    assert rec2.llm_status == "UNREACHABLE" and time.perf_counter() - t0 < 1.0
    llm_provider.reset()


def test_timeout_falls_back(fake_llm):
    fake_llm.behavior = "timeout"
    ctx = _make_context("to")
    base = _baseline(ctx)
    rec = model_gateway.evaluate_investigation(ctx)
    assert rec.llm_status == "TIMEOUT"
    assert _det_fields(rec) == _det_fields(base)


@pytest.mark.parametrize("behavior", ["bad_json", "bad_schema"])
def test_invalid_output_falls_back(fake_llm, behavior):
    fake_llm.behavior = behavior
    ctx = _make_context(behavior)
    base = _baseline(ctx)
    rec = model_gateway.evaluate_investigation(ctx)
    assert rec.llm_status == "INVALID_OUTPUT"
    assert rec.rationale == base.rationale
    assert _det_fields(rec) == _det_fields(base)


def test_hallucinated_value_is_discarded_and_flagged(fake_llm, audit_capture):
    fake_llm.behavior = "hallucinate"
    ctx = _make_context("hal")
    base = _baseline(ctx)
    rec = model_gateway.evaluate_investigation(ctx)
    assert rec.llm_status == "OK"
    assert rec.llm_disagreement is True
    assert "llm_disagreement:candidate_mismatch" in rec.llm_flags
    # advisory discarded entirely; deterministic proposal intact
    assert rec.rationale == base.rationale
    assert _det_fields(rec) == _det_fields(base)
    assert not any(h.source == "LLM_ESTIMATE" for h in rec.hypothesis_ranking)
    ev = [c for c in audit_capture if c["stage_name"] == "AI_ADVISORY"]
    assert ev and "LLM_DISAGREEMENT" in ev[-1]["control_tags"] and "disagreement=True" in ev[-1]["details"]


def test_unknown_evidence_refs_dropped_and_flagged(fake_llm):
    fake_llm.behavior = "unknown_evidence"
    ctx = _make_context("unk")
    rec = model_gateway.evaluate_investigation(ctx)
    assert rec.llm_status == "OK" and rec.llm_disagreement is False
    valid = {e.evidence_id for e in ctx.evidence_items}
    for h in rec.hypothesis_ranking:
        assert set(h.evidence_ids) <= valid
    assert any(f.startswith("llm_unknown_evidence_ref:") for f in rec.llm_flags)


def test_no_pii_in_prompt(fake_llm):
    ctx = _make_context("pii")
    model_gateway.evaluate_investigation(ctx)
    assert fake_llm.requests, "model was not called"
    wire = json.dumps(fake_llm.requests)
    for s in SECRET_NAMES + SECRET_ACCOUNTS:
        assert s not in wire, f"cleartext PII leaked to the model: {s}"
    # also not in spaced / lowercase forms
    assert "harborview" not in wire.lower()
    assert "acme global" not in wire.lower()


def test_scrub_redacts_known_pii_shapes():
    out = scrub({
        "beneficiary_name": "Jane Doe", "standing_iban": "DE89370400440532013000",
        "note": "Pay to FR1420041010050500013M02606 or mail a@b.com ref 123456789012",
        "nested": {"party_name": "ACME", "list": ["GB29NWBK60161331926819"]},
    })
    wire = json.dumps(out)
    for bad in ["Jane Doe", "DE89370400440532013000", "FR1420041010050500013M02606", "a@b.com",
                "123456789012", "ACME", "GB29NWBK60161331926819"]:
        assert bad not in wire


def test_extract_json_handles_think_and_fence():
    assert json.loads(extract_json_object('<think>{x}</think>```json\n{"a": {"b": "}"}}\n```')) == {"a": {"b": "}"}}
    assert extract_json_object("no json here") is None


def test_system_info_reports_llm_status(fake_llm, client):
    r = client.get("/api/system/info")
    assert r.status_code == 200
    llm = r.json()["llm"]
    assert llm["enabled"] is True and llm["model"] == "qwen2.5:7b-instruct"
    assert llm["reachable"] is True and llm["model_available"] is True
    assert llm["base_url"].startswith("127.0.0.1:") and "http" not in llm["base_url"]


def test_system_info_disabled_does_not_ping(monkeypatch, client):
    monkeypatch.setattr(settings, "LLM_ENABLED", False)
    llm_provider.reset()
    r = client.get("/api/system/info")
    assert r.json()["llm"]["enabled"] is False and r.json()["llm"]["reachable"] is None


def test_canned_scenarios_never_call_the_model(fake_llm):
    ctx = _make_context("scn")
    rec = model_gateway.evaluate_investigation(ctx, scenario_key="IBAN-ESCALATE-001")
    assert rec.llm_status is None and not fake_llm.requests
