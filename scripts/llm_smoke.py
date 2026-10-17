"""Smoke test for the local-LLM advisory layer against the REAL configured endpoint.

Usage (from the repo root, with Ollama running):
    set PEX_LLM_ENABLED=true            (PowerShell: $env:PEX_LLM_ENABLED="true")
    set PEX_LLM_MODEL=qwen2.5:7b-instruct
    python scripts/llm_smoke.py

Sends ONE synthetic sample (tokenized; no real data) and prints the validated advisory, the
deterministic fields that must not change, token counts and latency. Exit code 0 = OK.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("PEX_LLM_ENABLED", "true")

from app.config import settings                                    # noqa: E402
from app.schemas.bank_events import RawBankEvent                   # noqa: E402
from app.services.canonicalizer import canonicalizer               # noqa: E402
from app.services.evidence_planner import evidence_planner         # noqa: E402
from app.services.context_builder import context_builder           # noqa: E402
from app.services.model_gateway import model_gateway               # noqa: E402
from app.services.llm_provider import llm_provider, PROMPT_VERSION  # noqa: E402


def main() -> int:
    print(f"Endpoint : {settings.LLM_BASE_URL}")
    print(f"Model    : {settings.LLM_MODEL}   prompt_version={PROMPT_VERSION}")
    print(f"Timeout  : {settings.LLM_TIMEOUT_SECONDS}s")
    ping = llm_provider.ping()
    print(f"Reachable: {ping.get('reachable')}  model_available={ping.get('model_available')}")
    if not ping.get("reachable"):
        print("  -> Is Ollama running? (ollama serve)  Is PEX_LLM_BASE_URL correct (default http://localhost:11434/v1)?")

    event = RawBankEvent(
        event_id="EVT-SMOKE-1", source_bank_id="BANK_A", event_type="PAYMENT_EXCEPTION",
        raw_payload={
            "payment_reference": "REF-SMOKE-1", "error_code": "ERR_IBAN_MOD97",
            "error_message": "Beneficiary IBAN failed MOD-97 check validation",
            "amount": 42000.0, "currency": "EUR",
            "debtor_name": "Example Debtor GmbH", "debtor_account": "DE89370400440532013000",
            "creditor_name": "Example Creditor BV", "creditor_iban": "GB82WEST12345698765423",
        },
    )
    pmt, exc = canonicalizer.canonicalize_bank_event(event)
    evidence, policies, hist = evidence_planner.plan_and_gather_evidence(
        case_id=exc.case_id, profile=exc.profile, party_name=pmt.creditor_party.party_name,
        account_val=pmt.creditor_account.iban, currency=pmt.currency)
    ctx = context_builder.build_investigation_context(
        payment=pmt, exception=exc, evidence_items=evidence, policies=policies, historical_cases=hist)

    rec = model_gateway.evaluate_investigation(ctx)
    print("\n--- deterministic (must never be changed by the model) ---")
    print(f"action_type={rec.action_type.value}  confidence={rec.confidence_score}  "
          f"proposed_changes={len(rec.proposed_changes)}")
    print("\n--- LLM advisory ---")
    print(f"status={rec.llm_status}  model_version={rec.model_version}  prompt_version={rec.prompt_version}")
    print(f"tokens prompt/completion={rec.prompt_tokens}/{rec.completion_tokens}  latency_ms={rec.latency_ms}")
    print(f"disagreement={rec.llm_disagreement}  flags={rec.llm_flags}")
    print(f"rationale: {rec.rationale}")
    for h in rec.hypothesis_ranking:
        print(f"  [{h.source}] {h.hypothesis_id} {h.status} {h.confidence:.2f} {h.title}  refs={h.evidence_ids}")
    for q in rec.guided_questions:
        print(f"  ? {q.category}: {q.question}")
    if rec.consequence_simulation and rec.consequence_simulation.narrative:
        print(f"consequence: {rec.consequence_simulation.narrative}")
    return 0 if rec.llm_status == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
