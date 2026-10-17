# Local LLM setup (Windows, Ollama) - advisory layer

PeX uses a local model **only as an advisor**: it writes the rationale, ranks hypotheses (citing evidence
ids), suggests operator questions and a consequence summary. It never changes the proposed repair, the
confidence score, STP eligibility or any approval. If the model is off, slow, unreachable or returns
junk, PeX silently falls back to the deterministic recommendation and records why in the audit log.

The model only receives tokenized identifiers, masked account tails and scrubbed evidence - never names,
full IBANs, addresses or e-mails.

## 1. Install Ollama and pull a model
1. Download and install Ollama for Windows from https://ollama.com/download (runs as a background service).
2. Open PowerShell:
   ```powershell
   ollama pull qwen2.5:7b-instruct      # default, best quality that fits your machine
   ollama run qwen2.5:7b-instruct "say hello"   # warm-up: first load takes ~30-60 s
   ```
   Your GTX 1660 SUPER has 6 GB VRAM and Windows already uses ~2.6 GB, so the 7B model (~4.7 GB) will
   partly run on CPU/RAM (you have 31 GB). Close GPU-heavy apps (browsers with video, games) for speed.
   Expect it to be slower than a fully-on-GPU model; per-case advisory is a few seconds to ~half a
   minute (estimate, not measured on your machine).
3. Faster fallback (fits fully in VRAM, slightly weaker at structured JSON):
   ```powershell
   ollama pull qwen2.5:3b-instruct
   ```

## 2. Point PeX at it
Ollama exposes an OpenAI-compatible API at `http://localhost:11434/v1`. In the PowerShell window where
you start the backend:
```powershell
$env:PEX_LLM_ENABLED = "true"
$env:PEX_LLM_MODEL = "qwen2.5:7b-instruct"          # or qwen2.5:3b-instruct
$env:PEX_LLM_BASE_URL = "http://localhost:11434/v1"  # default, shown for clarity
$env:PEX_LLM_TIMEOUT_SECONDS = "120"                 # 7B partly on CPU: allow time
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

## 3. Check it works
- `curl http://localhost:8000/api/system/info` -> `llm` shows `enabled`, `model`, `reachable: true`,
  `model_available: true`. (`reachable:false` = Ollama not running / wrong URL.)
- `python scripts/llm_smoke.py` sends one synthetic sample to the real endpoint and prints the validated
  result, token counts and latency. Exit code 0 means status OK.
- In the UI/API, a recommendation now carries `llm_status`, `model_version`, `prompt_version`,
  `prompt_tokens`, `completion_tokens`, `latency_ms`, `llm_disagreement`, `llm_flags`.
  Each call also writes an `AI_ADVISORY` audit event (model/prompt version, tokens, latency, flags).

## 4. Switching models
Change `PEX_LLM_MODEL` and restart. Any OpenAI-compatible server works (llama.cpp `server`, LM Studio,
vLLM): set `PEX_LLM_BASE_URL` to its `/v1` URL.
- DeepSeek: `ollama pull deepseek-r1:7b`. It emits `<think>...</think>` blocks (PeX strips them) and is
  usually slower and less reliable at strict JSON than Qwen; try it, but keep Qwen as the default.
- Other options: `llama3.1:8b`, `qwen3:8b`. If a model's output fails validation PeX shows
  `llm_status: INVALID_OUTPUT` and falls back to deterministic - nothing breaks.

## 5. Behaviour you should expect
| Situation | `llm_status` | What the user sees |
|---|---|---|
| `PEX_LLM_ENABLED` not true | none | unchanged deterministic recommendation |
| Model answers correctly | `OK` | LLM rationale, hypotheses marked `LLM_ESTIMATE`, questions, consequence text |
| Ollama stopped / wrong URL | `UNREACHABLE` | deterministic output; further calls skipped for 15 s (circuit breaker) |
| Too slow | `TIMEOUT` | deterministic output |
| Not valid JSON / schema | `INVALID_OUTPUT` | deterministic output |
| Model proposes a value that is not the deterministic candidate | `OK` + `llm_disagreement: true` | advisory discarded, flagged in the audit event |

Hypothesis confidences from the model are rough estimates, not calibrated probabilities; the UI should
label them (`source: LLM_ESTIMATE`). Batch ingestion (`e2e_runner`) does not call the model; only the
investigation/recommendation endpoint does.
