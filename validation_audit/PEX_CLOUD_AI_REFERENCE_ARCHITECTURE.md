# 🧠 PeX — Cloud AI & Cognitive Reference Architecture

**Document ID:** `PEX-CLOUD-AI-REF-ARCH-v0.1`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / Enterprise Architecture `v0.2`  
**Scope:** AI Architecture, RAG Pipeline, Governance Boundaries, and Model Neutrality  
**Date:** September 28, 2026  
**Status:** Approved Reference AI Architecture  

---

## 1. Cognitive Architecture Decision Chain

```mermaid
flowchart TD
    subgraph EvidenceStage["1. Evidence Aggregation & Validation Tier"]
        Inbound["Inbound Exception Event"] --> Tokenize["Perimeter Tokenization (Surrogate Tokens)"]
        Tokenize --> BMD["Beneficiary Master Directory (BMD) Lookup"]
        Tokenize --> SSI["Standard Settlement Instructions (SSI)"]
        Tokenize --> History["90-Day Settlement History Query"]
        Tokenize --> BIAN["BIAN SOP Playbook Embeddings"]
    end

    subgraph PromptStage["2. Zero-PII Context Assembly & Model Gateway"]
        BMD & SSI & History & BIAN --> ContextBuilder["Zero-PII Context Builder"]
        ContextBuilder --> ModelGW["Model Gateway (Abstract Port)"]
        ModelGW --> PrivateLLM["Private Foundation Model (Bedrock / Vertex / Azure OpenAI)"]
    end

    subgraph ReasoningStage["3. Advisory Schema Validation"]
        PrivateLLM --> OutputContract["Strict JSON ReasoningResult Validation"]
        OutputContract --> CheckAmbiguity{"Ambiguity Detected?"}
        CheckAmbiguity -->|Yes (Score Diff < 0.15)| Escalate["Route to Operator Disambiguation Desk"]
        CheckAmbiguity -->|No| AdvisoryOutput["Advisory Field Patch Recommendation"]
    end

    subgraph DeterministicStage["4. Deterministic Validation & Policy Gating"]
        AdvisoryOutput --> DeterministicCheck{"Deterministic Validation Pass?
(MOD-97-10 / ABA Checksum / Directory Match)"}
        DeterministicCheck -->|Fail| Block["Mark as INVALID_REPAIR / Escalate"]
        DeterministicCheck -->|Pass| PolicyAST["Policy-as-Code AST Engine Evaluation"]
    end

    subgraph GovernanceStage["5. Human Authorization & Execution"]
        PolicyAST --> DualAuthCheck{"Amount >= $250k or Sanctions Match?"}
        DualAuthCheck -->|Yes| Level2Auth["Level-2 Dual Authorization Gate"]
        DualAuthCheck -->|No| Level1Auth["Level-1 Operations Approver Sign-off"]
        Level1Auth & Level2Auth --> Detokenize["Controlled Outbound Detokenizer"]
        Detokenize --> WireRelease["Idempotent Bank Dispatch"]
    end
```

---

## 2. Cloud Model Provider Implementation Mapping

| Cognitive Capability | Provider-Neutral Specification | AWS Implementation | Google Cloud Platform (GCP) | Microsoft Azure |
|---|---|---|---|---|
| **Foundation Model (LLM)** | Private VPC-hosted model; zero data logging; zero training on customer payments. | **Amazon Bedrock (Anthropic Claude 3.5 Sonnet)** | **Google Vertex AI (Gemini 1.5 Pro / Flash)** | **Azure OpenAI Service (GPT-4o / GPT-4o-mini)** |
| **Private Model Connectivity**| Private subnet connection without public internet traversal. | **AWS PrivateLink (VPC Endpoints)** | **Private Service Connect (PSC)** | **Azure Private Endpoints (Private Link)** |
| **Semantic & RAG Index** | Vector search over BIAN standard operating procedures and historical precedents. | **Amazon OpenSearch Service (Serverless k-NN)** | **Google Vertex AI Vector Search** | **Azure AI Search (Vector Search)** |
| **Context Assembly Contract** | `ZeroPIIReasoningContext` containing format-preserving surrogate tokens. | Handled in `app.services.context_builder` (100% cloud-neutral Pydantic model). | Handled in `app.services.context_builder` (100% cloud-neutral Pydantic model). | Handled in `app.services.context_builder` (100% cloud-neutral Pydantic model). |
| **Output Contract** | `ReasoningResult` JSON schema enforcing proposed field diffs, confidence, and justification. | Handled in `app.services.model_gateway` (100% cloud-neutral Pydantic model). | Handled in `app.services.model_gateway` (100% cloud-neutral Pydantic model). | Handled in `app.services.model_gateway` (100% cloud-neutral Pydantic model). |

---

## 3. Cognitive Safety & Governance Guardrails

1. **Strict Advisory Status:** The AI Reasoner possesses **\$0.00 approval authority**. It cannot release funds, bypass approvals, or alter payment records without human or policy authorization.
2. **Deterministic Precedence Invariant:** A 0.99 AI confidence score CANNOT override a failed ISO 7064 MOD-97-10 check digit calculation. Deterministic checks unconditionally supersede AI outputs.
3. **Circuit Breaker & Fallback Protocol:**
   - **Timeout:** 3,000 ms.
   - **Circuit Breaker:** Opens after 5 consecutive 5xx/timeout errors.
   - **Fallback Action:** Reverts immediately to deterministic AST Policy Rules; if no rule matches, routes to `INVESTIGATING` with status `AI_UNAVAILABLE_MANUAL_TRIAGE`. Zero cases are dropped.
4. **Multi-Hypothesis Disambiguation:** When multiple candidate accounts match, the reasoner attributes confidence to each candidate and presents an interactive disambiguation interface to the Operator Maker.
