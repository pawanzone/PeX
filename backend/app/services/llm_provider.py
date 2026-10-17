"""Local LLM provider (OpenAI-compatible endpoint, e.g. Ollama / llama.cpp server).

ADVISORY ONLY. The model never decides anything: it writes a rationale, ranks hypotheses
(with evidence references), suggests guided questions and a consequence summary. The
deterministic 8-predicate gate, resolvers and e2e_runner stay authoritative. This module
never raises into the pipeline: every failure is returned as an LLMStatus.

PII boundary: the model only sees the tokenized investigation context plus a scrubbed
evidence summary and masked candidate tails. See `scrub()` / `build_messages()`.
"""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import settings

PROMPT_VERSION = "pex-advisory-v1"


class LLMStatus(str, Enum):
    OK = "OK"
    UNREACHABLE = "UNREACHABLE"
    TIMEOUT = "TIMEOUT"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    DISABLED = "DISABLED"


# ----------------------------------------------------------------------------------------
# Strict output contract
# ----------------------------------------------------------------------------------------
class LLMHypothesis(BaseModel):
    title: str = Field(..., min_length=1, max_length=240)
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: Literal["SELECTED", "ELIMINATED", "ELIGIBLE_CANDIDATE"] = "ELIGIBLE_CANDIDATE"
    evidence_ids: List[str] = Field(default_factory=list, max_length=8)
    elimination_reason: Optional[str] = Field(default=None, max_length=400)


class LLMGuidedQuestion(BaseModel):
    category: str = Field(..., min_length=1, max_length=80)
    question: str = Field(..., min_length=1, max_length=400)
    investigation_tip: str = Field(default="", max_length=400)


class LLMAdvisory(BaseModel):
    rationale: str = Field(..., min_length=1, max_length=1500)
    hypotheses: List[LLMHypothesis] = Field(default_factory=list, max_length=5)
    guided_questions: List[LLMGuidedQuestion] = Field(default_factory=list, max_length=5)
    consequence_summary: str = Field(default="", max_length=600)
    # The model may only *confirm* a deterministic candidate by id; it can never invent a value.
    selected_candidate_id: Optional[str] = Field(default=None, max_length=40)
    proposed_value_hint: Optional[str] = Field(default=None, max_length=80)
    cited_evidence_ids: List[str] = Field(default_factory=list, max_length=12)


@dataclass
class LLMResult:
    status: LLMStatus
    advisory: Optional[LLMAdvisory] = None
    model: Optional[str] = None
    model_version: Optional[str] = None
    prompt_version: str = PROMPT_VERSION
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    error: Optional[str] = None
    attempts: int = 0


# ----------------------------------------------------------------------------------------
# PII scrubbing
# ----------------------------------------------------------------------------------------
_PII_KEYS = {
    "name", "party_name", "beneficiary_name", "creditor_name", "debtor_name", "account_holder",
    "holder_name", "legal_name", "ordering_customer", "address", "street", "street_name",
    "address_line", "address_lines", "email", "phone", "contact", "remittance_info", "narrative",
    "free_text", "beneficiary", "owner", "owner_name", "signatory", "signer", "signer_name",
}
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
_IBAN_SPACED_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ][A-Z0-9]{2,4}){3,8}\b")
_DIGITS_RE = re.compile(r"\b\d{9,}\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _tail(value: str, n: int = 4) -> str:
    v = re.sub(r"\s+", "", value)
    return "***" + v[-n:] if len(v) > n else "***"


def scrub_text(text: str) -> str:
    t = _EMAIL_RE.sub("<EMAIL>", text)
    t = _IBAN_SPACED_RE.sub(lambda m: "IBAN" + _tail(m.group(0)), t)
    t = _IBAN_RE.sub(lambda m: "IBAN" + _tail(m.group(0)), t)
    t = _DIGITS_RE.sub(lambda m: "NUM" + _tail(m.group(0)), t)
    return t


def scrub(obj: Any, _key: Optional[str] = None) -> Any:
    """Recursively redact PII from evidence payloads before they reach any model."""
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in _PII_KEYS:
                out[k] = "<REDACTED>"
            elif ("iban" in lk or "account" in lk or lk.endswith("_number")) and isinstance(v, str):
                out[k] = _tail(v)
            else:
                out[k] = scrub(v, lk)
        return out
    if isinstance(obj, (list, tuple)):
        return [scrub(v, _key) for v in obj][:25]
    if isinstance(obj, str):
        return scrub_text(obj)[:300]
    return obj


# ----------------------------------------------------------------------------------------
# Prompt (single place, versioned)
# ----------------------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are an advisory assistant inside a bank's payment-exception platform (PeX). "
    "You do NOT decide, repair, approve or release anything. A deterministic rules engine has "
    "already evaluated the case; a human will decide. All identifiers you receive are tokens or "
    "masked tails; never try to reconstruct personal data.\n"
    "Your job: (1) explain the deterministic finding in plain language, (2) rank 2-4 plausible "
    "root-cause hypotheses, each citing evidence_ids that exist in the input, (3) suggest up to 4 "
    "questions an operator should check, (4) summarise consequences of acting or waiting.\n"
    "Hard rules: use only evidence_ids present in the input; if you refer to a proposed repair, "
    "set selected_candidate_id to one of the candidate ids provided and never invent a value; "
    "if there are no candidates leave selected_candidate_id null; confidence values are your own "
    "rough estimate between 0 and 1; reply with a single JSON object matching the schema and "
    "nothing else."
)


def advisory_json_schema() -> Dict[str, Any]:
    return LLMAdvisory.model_json_schema()


def build_candidates(rec: Any) -> List[Dict[str, Any]]:
    cands = []
    for i, ch in enumerate(getattr(rec, "proposed_changes", None) or [], start=1):
        cands.append({
            "candidate_id": f"CAND-{i}",
            "field_path": ch.field_path,
            "original_tail": _tail(ch.original_value_masked or ""),
            "proposed_tail": _tail(ch.proposed_value_masked or ""),
            "validation_status": ch.validation_status,
        })
    return cands


def build_user_payload(context: Any, rec: Any) -> Dict[str, Any]:
    tp = context.tokenized_payment
    evidence = [{
        "evidence_id": e.evidence_id,
        "type": e.evidence_type,
        "source": e.source_connector,
        "mandatory": e.is_mandatory,
        "relevance": e.relevance_score,
        "data": scrub(e.data),
    } for e in context.evidence_items][:15]
    return {
        "prompt_version": PROMPT_VERSION,
        "case_id": context.case_id,
        "profile": getattr(context.profile, "value", str(context.profile)),
        "payment": {
            "amount": tp.amount,
            "currency": tp.currency,
            "rail": tp.payment_rail,
            "debtor_party_token": tp.debtor_party.token_id,
            "debtor_country": tp.debtor_party.country,
            "creditor_party_token": tp.creditor_party.token_id,
            "creditor_country": tp.creditor_party.country,
            "creditor_account_token": tp.creditor_account.token_id,
            "creditor_account_tail": _tail(tp.creditor_account.masked_identifier or ""),
            "creditor_bank_bic": tp.creditor_account.bank_bic,
        },
        "evidence": evidence,
        "policies": [{
            "policy_id": p.policy_id, "rule": p.rule_code,
            "description": scrub_text(p.rule_description)[:240],
            "auto_repair_eligible": p.auto_repair_eligible,
            "max_amount": p.max_amount_threshold,
        } for p in context.policies][:8],
        "history": [{
            "case": h.precedent_case_id, "similarity": h.similarity_score,
            "action": h.applied_action, "outcome": h.outcome,
        } for h in context.historical_cases][:5],
        "deterministic_finding": {
            "action_type": getattr(rec.action_type, "value", str(rec.action_type)),
            "confidence": rec.confidence_score,
            "candidates": build_candidates(rec),
            "checks": [{
                "step": s.step_title, "passed": s.is_passed, "badge": s.badge_label,
            } for s in (rec.step_by_step_assessment or [])][:8],
            "risk_level": getattr(rec.risk_evaluation.risk_level, "value", str(rec.risk_evaluation.risk_level)),
            "risk_factors": [scrub_text(str(f))[:160] for f in rec.risk_evaluation.risk_factors][:6],
        },
        "output_schema_hint": "JSON object with rationale, hypotheses[], guided_questions[], consequence_summary, "
                              "selected_candidate_id, proposed_value_hint, cited_evidence_ids[]",
    }


def build_messages(context: Any, rec: Any) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(build_user_payload(context, rec), default=str)},
    ]


# ----------------------------------------------------------------------------------------
# Output parsing
# ----------------------------------------------------------------------------------------
_THINK_RE = re.compile(r"<think>.*?</think>", re.S | re.I)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)


def extract_json_object(text: str) -> Optional[str]:
    """Strip <think> blocks and code fences, then return the first balanced {...} block."""
    t = _THINK_RE.sub("", text or "").strip()
    t = _FENCE_RE.sub("", t).strip()
    start = t.find("{")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return t[start:i + 1]
    return None


# ----------------------------------------------------------------------------------------
# Provider
# ----------------------------------------------------------------------------------------
def _base_url() -> str:
    return str(settings.LLM_BASE_URL).rstrip("/")


def model_version_label(model: str, base_url: Optional[str] = None) -> str:
    url = base_url or _base_url()
    flavour = "ollama" if ":11434" in url else "openai-compat"
    return f"{flavour}:{model}"


class LocalLLMProvider:
    MAX_ATTEMPTS = 2

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._breaker_until = 0.0
        self._ping_cache: Tuple[float, Dict[str, Any]] = (0.0, {})

    # -- circuit breaker: avoid piling timeouts onto a batch when the model is down --
    def reset(self) -> None:
        with self._lock:
            self._breaker_until = 0.0
            self._ping_cache = (0.0, {})

    def _trip(self, seconds: float = 15.0) -> None:
        with self._lock:
            self._breaker_until = time.monotonic() + seconds

    def _tripped(self) -> bool:
        return time.monotonic() < self._breaker_until

    # -- reachability (cheap, cached 10s) --
    def ping(self) -> Dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            ts, cached = self._ping_cache
            if cached and now - ts < 10.0:
                return cached
        info: Dict[str, Any] = {"reachable": False, "model_available": None}
        try:
            r = httpx.get(f"{_base_url()}/models", timeout=1.0)
            if r.status_code == 200:
                info["reachable"] = True
                try:
                    ids = [m.get("id") for m in (r.json().get("data") or [])]
                    info["model_available"] = settings.LLM_MODEL in ids if ids else None
                except Exception:
                    pass
        except Exception:
            pass
        with self._lock:
            self._ping_cache = (time.monotonic(), info)
        return info

    def status_summary(self) -> Dict[str, Any]:
        host = urlparse(_base_url()).netloc
        out: Dict[str, Any] = {
            "enabled": bool(settings.LLM_ENABLED),
            "model": settings.LLM_MODEL,
            "base_url": host,
            "prompt_version": PROMPT_VERSION,
            "reachable": None,
            "model_available": None,
            "circuit_open": self._tripped(),
        }
        if settings.LLM_ENABLED:
            p = self.ping()
            out["reachable"] = p.get("reachable")
            out["model_available"] = p.get("model_available")
        return out

    # -- main call --
    def advise(self, context: Any, rec: Any) -> LLMResult:
        if not settings.LLM_ENABLED:
            return LLMResult(status=LLMStatus.DISABLED)
        model = settings.LLM_MODEL
        mv = model_version_label(model)
        if self._tripped():
            return LLMResult(status=LLMStatus.UNREACHABLE, model=model, model_version=mv,
                             error="circuit open after recent failure")
        try:
            messages = build_messages(context, rec)
        except Exception as e:  # never break the pipeline on prompt construction
            return LLMResult(status=LLMStatus.INVALID_OUTPUT, model=model, model_version=mv,
                             error=f"prompt build failed: {type(e).__name__}")

        t0 = time.perf_counter()
        formats: List[Optional[Dict[str, Any]]] = [
            {"type": "json_schema", "json_schema": {"name": "pex_advisory", "schema": advisory_json_schema(), "strict": True}},
            {"type": "json_object"},
            None,
        ]
        fmt_idx = 0
        attempts = 0
        last_error = "unknown"
        timeout = httpx.Timeout(float(settings.LLM_TIMEOUT_SECONDS), connect=3.0)
        url = f"{_base_url()}/chat/completions"
        while attempts < self.MAX_ATTEMPTS + 2 and fmt_idx < len(formats):
            attempts += 1
            body: Dict[str, Any] = {
                "model": model, "messages": messages, "temperature": 0.1,
                "stream": False, "max_tokens": 900,
            }
            if formats[fmt_idx] is not None:
                body["response_format"] = formats[fmt_idx]
            try:
                resp = httpx.post(url, json=body, timeout=timeout)
            except httpx.TimeoutException:
                self._trip()
                return LLMResult(LLMStatus.TIMEOUT, model=model, model_version=mv, attempts=attempts,
                                 latency_ms=int((time.perf_counter() - t0) * 1000), error="timeout")
            except httpx.HTTPError as e:
                last_error = type(e).__name__
                if attempts >= self.MAX_ATTEMPTS:
                    self._trip()
                    return LLMResult(LLMStatus.UNREACHABLE, model=model, model_version=mv, attempts=attempts,
                                     latency_ms=int((time.perf_counter() - t0) * 1000), error=last_error)
                time.sleep(0.3)
                continue
            if resp.status_code in (400, 422) and fmt_idx < len(formats) - 1:
                fmt_idx += 1  # server rejects this response_format: step down to a simpler one
                continue
            if resp.status_code >= 500 or resp.status_code in (404, 401, 403):
                self._trip()
                return LLMResult(LLMStatus.UNREACHABLE, model=model, model_version=mv, attempts=attempts,
                                 latency_ms=int((time.perf_counter() - t0) * 1000), error=f"HTTP {resp.status_code}")
            if resp.status_code != 200:
                return LLMResult(LLMStatus.INVALID_OUTPUT, model=model, model_version=mv, attempts=attempts,
                                 latency_ms=int((time.perf_counter() - t0) * 1000), error=f"HTTP {resp.status_code}")
            return self._parse(resp, model, mv, attempts, t0, messages)
        return LLMResult(LLMStatus.UNREACHABLE, model=model, model_version=mv, attempts=attempts,
                         latency_ms=int((time.perf_counter() - t0) * 1000), error=last_error)

    def _parse(self, resp: httpx.Response, model: str, mv: str, attempts: int, t0: float,
               messages: List[Dict[str, str]]) -> LLMResult:
        latency = int((time.perf_counter() - t0) * 1000)
        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except Exception:
            return LLMResult(LLMStatus.INVALID_OUTPUT, model=model, model_version=mv, attempts=attempts,
                             latency_ms=latency, error="malformed completion envelope")
        usage = data.get("usage") or {}
        pt = int(usage.get("prompt_tokens") or sum(len(m["content"]) for m in messages) // 4)
        ct = int(usage.get("completion_tokens") or len(content or "") // 4)
        served = data.get("model") or model
        mv_served = model_version_label(served)
        raw = extract_json_object(content or "")
        if raw is None:
            return LLMResult(LLMStatus.INVALID_OUTPUT, model=served, model_version=mv_served, attempts=attempts,
                             latency_ms=latency, prompt_tokens=pt, completion_tokens=ct, error="no JSON object in output")
        try:
            advisory = LLMAdvisory.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as e:
            return LLMResult(LLMStatus.INVALID_OUTPUT, model=served, model_version=mv_served, attempts=attempts,
                             latency_ms=latency, prompt_tokens=pt, completion_tokens=ct,
                             error=f"schema validation failed: {type(e).__name__}")
        return LLMResult(LLMStatus.OK, advisory=advisory, model=served, model_version=mv_served, attempts=attempts,
                         latency_ms=latency, prompt_tokens=pt, completion_tokens=ct)


llm_provider = LocalLLMProvider()
