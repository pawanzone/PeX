# PeX — Provider Dependency & Environment Inventory

**Authoritative Inventory of Provider-Specific Tokens, Variables, and Dependencies**  
**Version:** `1.0.0`  
**Date:** September 23, 2026  
**Scope:** `backend/`, `frontend/`, `tests/`, `tools/`, configuration and deployment descriptors.

---

## 1. Inventory Summary

This inventory classifies all environment variables, driver hooks, and provider-specific tokens in the PeX repository. It validates that all external provider references are strictly isolated behind secondary port abstractions, have fully functional deterministic local defaults, and introduce zero cloud or model vendor lock-in.

---

## 2. Configuration & Environment Variable Register

| Variable / Token | Declared Location | Purpose & Function | Cloud / Model Provider | Default / Local Fallback | Isolation Mechanism | Neutrality Status |
|---|---|---|---|---|---|---|
| `DATABASE_URL` | `backend/app/config.py` | Connection string for relational persistence | Cloud Relational (AWS Aurora, GCP Cloud SQL, Azure PostgreSQL) | `sqlite:///./pex_enterprise.db` | SQLAlchemy 2.0 Engine dialect detection (`session.py`) | **Fully Neutral** (PostgreSQL / SQLite dialect agnostic) |
| `DB_POOL_SIZE` | `backend/app/config.py` | Database connection pool capacity | Enterprise PostgreSQL connection pool | `20` | Dynamic pool allocation in `session.py` (NullPool for SQLite) | **Fully Neutral** |
| `DB_MAX_OVERFLOW` | `backend/app/config.py` | Database burst connection limit | Enterprise PostgreSQL connection pool | `10` | SQLAlchemy connection pooling configuration | **Fully Neutral** |
| `DB_POOL_RECYCLE` | `backend/app/config.py` | Connection recycling interval | TCP keepalive and connection pruning | `1800` (30 min) | SQLAlchemy connection pool recycle setting | **Fully Neutral** |
| `DB_ECHO` | `backend/app/config.py` | SQL statement logging | All SQL engines | `false` | Standard SQLAlchemy logger | **Fully Neutral** |
| `PEX_MODEL_GATEWAY_MODE` / `MODEL_GATEWAY_MODE` | `backend/app/config.py` | LLM Gateway provider selector | Mock, Google Gemini, OpenAI, AWS Bedrock, Azure OpenAI | `"mock"` | Model Gateway factory dispatch (`model_gateway.py`) | **Fully Neutral** (Pluggable provider interface) |
| `GEMINI_API_KEY` | `backend/app/config.py` | API authentication key for Gemini Pro / Vertex AI | Google Cloud / Google AI | `""` (Empty string) | Evaluated only when `MODEL_GATEWAY_MODE == "gemini"` | **Fully Isolated** (No runtime dependency if mock mode) |
| `OPENAI_API_KEY` | `backend/app/config.py` | API authentication key for GPT-4o / Azure OpenAI | OpenAI / Microsoft Azure | `""` (Empty string) | Evaluated only when `MODEL_GATEWAY_MODE == "openai"` | **Fully Isolated** (No runtime dependency if mock mode) |
| `JWT_SECRET` | `backend/app/config.py` | Cryptographic secret for session and auth tokens | All Authentication Providers | `"pex-enterprise-secret-key-2026-sha256"` | `app.core.security` HMAC-SHA256 signer | **Fully Neutral** |
| `JWT_ALGORITHM` | `backend/app/config.py` | JWT signing algorithm | Standard JWT / JOSE | `"HS256"` | Standard PyJWT / Python-jose library | **Fully Neutral** |
| `is_aws_postgres` | `backend/app/db/session.py` | Legacy telemetry flag alias for cloud relational database | AWS / Enterprise Cloud | Evaluated from `not is_sqlite` | Backward-compatibility alias alongside `is_relational_postgres` | **Neutralized** (Alias retained for non-breaking telemetry) |
| `is_relational_postgres` | `backend/app/db/session.py` | Primary telemetry flag for cloud PostgreSQL backend | AWS Aurora, GCP Cloud SQL, Azure PostgreSQL | `False` when SQLite, `True` when PostgreSQL | Evaluated dynamically from `DATABASE_URL` prefix | **Fully Neutral** |

---

## 3. Runtime Dependency Analysis (`requirements.txt` & `pyproject.toml`)

All dependencies in the PeX environment are analyzed for vendor neutrality:

| Dependency Package | Role in Architecture | Provider Binding | Local / Replit Compatibility |
|---|---|---|---|
| `fastapi` / `uvicorn` | Core ASGI Web & API Framework | None (Open Source) | 100% Native |
| `pydantic` | Data modeling & schema contracts | None (Open Source) | 100% Native |
| `sqlalchemy` | Relational ORM & connection management | Multi-dialect (SQLite, PostgreSQL, MySQL) | 100% Native |
| `pytest` / `pytest-asyncio` | Unit & integration test execution | None (Open Source) | 100% Native |
| `requests` / `httpx` | HTTP client for ICD staging adapters | None (Open Source) | 100% Native |
| `python-jose` / `passlib` | Cryptographic security & hashing | None (Open Source) | 100% Native |

> **Audit Finding:** The PeX core dependencies contain **zero** mandatory proprietary SDKs (such as `boto3`, `google-cloud-*`, or `azure-mgmt-*`). When deploying to a specific enterprise cloud, provider-specific adapters are loaded dynamically as secondary plugins without touching the core domain code.

---

## 4. Replit & Cloud Readiness Certification

1. **Zero External Network Prerequisite:** In `MODEL_GATEWAY_MODE=mock` (the default), PeX operates with zero external network dependencies, requiring no third-party cloud accounts or billing setup.
2. **Deterministic Seed Data:** All 233 initial cases, 19 policy rules, and 5 ICD clearing nodes are automatically hydrated into SQLite on startup.
3. **Clean Environment Separation:** All environment variables use standard prefixes and provide fallback defaults.
