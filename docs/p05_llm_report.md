# P0.5 report - fork "llm" (advisory local-LLM gateway)

Status: DONE, 16/16 new tests pass (`tests/test_llm_gateway.py`, ~9 s). Nothing committed (per rules).

## Files
- NEW `backend/app/services/llm_provider.py` - httpx client for any OpenAI-compatible endpoint; strict pydantic
  output contract (`LLMAdvisory`); PII scrubber; versioned prompt (`PROMPT_VERSION = "pex-advisory-v1"`);
  circuit breaker (15 s after UNREACHABLE/TIMEOUT); cached `/models` ping (1 s timeout, 10 s cache).
  Never raises: returns `LLMStatus` OK | UNREACHABLE | TIMEOUT | INVALID_OUTPUT | DISABLED.
  Output-format step-down: `json_schema` -> `json_object` -> none if the server answers 400/422. Strips
  `<think>` blocks and code fences (DeepSeek-style), extracts first balanced JSON object.
- EDIT `backend/app/services/model_gateway.py` - old logic kept as `_evaluate_deterministic`; new
  `evaluate_investigation` wraps it. Canned `scenario_key` paths and LLM-disabled return the deterministic
  object untouched (verified equal). Enrichment works on a deep copy.
- EDIT `backend/app/schemas/recommendation.py` (not on my allow-list, needed; all additions optional/defaulted):
  `DecisionRecommendation.{model_version,prompt_version,latency_ms,llm_status,llm_disagreement,llm_flags,deterministic_rationale}`,
  `HypothesisRankingItem.{source,evidence_ids}`, `ConsequenceSimulation.narrative`.
- EDIT `backend/app/api/endpoints/system.py` - only the `llm` section (via `_llm_section()`).
- NEW `tests/test_llm_gateway.py`, `docs/LLM_LOCAL_SETUP.md`, `scripts/llm_smoke.py`, this report.

## Behaviour
- Model sees: tokenized ids, masked tails (`***5432`), scrubbed evidence, policies, history ids, deterministic
  finding (action, confidence, candidates as `CAND-n` + tails, check titles/badges). Never names/full IBANs
  (`scrub()` redacts PII keys, IBAN shapes, 9+ digit runs, e-mails). Test asserts none of the sample names/
  accounts appear in the wire request.
- Model may only: rationale, hypotheses (+evidence ids), guided questions, consequence narrative,
  confirm a candidate by id. If it names a candidate id/value that is not the deterministic one ->
  `llm_disagreement=true`, flag `llm_disagreement:candidate_mismatch`, WHOLE advisory discarded.
  Unknown evidence ids are dropped and flagged (`llm_unknown_evidence_ref:...`).
- Invariants asserted in tests: `action_type, confidence_score, proposed_changes, risk_evaluation,
  applied_policies, ambiguity_detected, step_by_step_assessment` are identical with and without the LLM.
- On OK, real `prompt_tokens/completion_tokens` come from the server's `usage` (no more 120/45).
- Hypothesis `source`: `LLM_ESTIMATE` (model), `SIMULATED` (demo fixture titles carrying "[SIMULATED]"),
  `DETERMINISTIC`. UI should show LLM scores as "model estimate", not a probability.
- Each advisory call logs an `AI_ADVISORY` audit event: model_version, prompt_version, tokens, latency,
  disagreement, flags (in the hashed `details` string; tags `Advisory only`, `LLM:<status>`, `LLM_DISAGREEMENT`).
- `GET /api/system/info` -> `llm: {enabled, model, base_url(host:port only), prompt_version, reachable,
  model_available, circuit_open}`; no ping when disabled.
- Config (already in config.py): `PEX_LLM_ENABLED` (default false), `PEX_LLM_BASE_URL`, `PEX_LLM_MODEL`
  (qwen2.5:7b-instruct), `PEX_LLM_TIMEOUT_SECONDS`. For 7B partly on CPU suggest 120.

## Findings for the main agent (outside my scope)
1. **P0-6 audit fields are not wired in the real audit path.** `repository.log_audit_event` has no
   `extra_payload/before/after/policy_version/model_version/reason_code/maker_id` parameters, does not pass
   them to `calculate_event_hash`, and `AuditEventModel`/`AuditEvent` have no such columns. Only the hashing
   util and AG's unit test know about them. I therefore put model/prompt version etc. into the hashed `details`
   string. Real fix = add an `extra_payload` JSON column + parameter in repository/model/schema/`audit_service`.
2. 4 legacy tests fail identically on clean HEAD (not caused by this work): `test_scenarios::test_scenario_iban_repair_001`,
   `test_functional_adversarial::{test_normal_full_lifecycle_e2e,test_redteam_idempotency_flood_attack}`,
   `test_replit_readiness::test_replit_end_to_end_exception_resolution_lifecycle` (they assert the removed
   synthetic `SETTLED_CONFIRMED` receipt). Also passing unchanged: test_hitl_approval, rest of those files (28).
3. The data_loader `build_rich_guided_recommendation` fixtures (proofs, 3 hypotheses, consequence figures like
   "$14.2M available") remain the deterministic fallback; they are labelled [SIMULATED] but the consequence
   numbers are not. UI should not show `ConsequenceSimulation` numeric fields as facts.

## Not done / limits
- Not run against a real Ollama/Qwen (VM cannot reach/download it); verified only against the fake
  OpenAI-style server (ok, format step-down, think/fence, unreachable+breaker, timeout, bad JSON, bad schema,
  hallucinated candidate, unknown evidence refs, PII, system info, canned scenarios, disabled). First real
  check: `python scripts/llm_smoke.py` after following `docs/LLM_LOCAL_SETUP.md`.
- Batch ingestion/`e2e_runner` do not call the model (by design; per-record 7B calls would not scale).
- `model_identifier` is left unchanged (still the deterministic engine label); LLM provenance is in `model_version`.
