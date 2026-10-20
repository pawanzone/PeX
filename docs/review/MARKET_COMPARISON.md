# PeX market comparison: what banks can buy today, and what PeX should include

Prepared 20 Oct 2026 from vendor pages (linked at the end). Vendor claims are marketing claims, not tested results. Where a page gave no detail, this note says so.

## The products a bank is likely to compare us with

| Product | What it is | Strengths | What its public material does not show |
|---|---|---|---|
| **Swift Case Management** (Case Orchestrator, Stop and Recall) | Network-level service for investigations and cancellations, built on camt.110/111 and camt.056/029, tied to the UETR | Becomes the required route for the whole community: camt.110 receipt by November 2026, mandatory use by end of 2027. Free to send and receive camt.110 | It is a messaging and orchestration rail, not a bank's internal repair desk. Nothing on evidence, approvals or SLA control inside the bank |
| **Pega Payment Exceptions and Investigations** (launched Sept 2025) | Case platform with agents that read SWIFT messages and emails, open cases, suggest resolutions | Agentic workflow design from a plain-language description, parallel actions, MCP/agent interoperability, early camt.110/111 support | No stated approval gates, escalation thresholds, audit trail or override design. Says some email requests can run without human intervention |
| **Validata Payments Investigation and Case Manager** | Case manager with one master data model across SWIFT, clearing, ERP, core banking, CRM | De-duplicating case creation, smart routing, 360 view with AI reasoning, explainable decisions, SLA reports | No detail on who authorises a repair or how limits are controlled |
| **SmartStream Smart Payments** | Exception management with packaged rulebook workflows | Single case view, auto-classification, auto-acknowledgement, automated follow-ups and reminders, GPI/SEPA/TARGET workflows, configurable approvals, claims up to 70% saving in resolution cost | AI is for matching; not for evidence-backed repair recommendations |
| **Bottomline** | Case management for ISO 20022 payments | Customer-facing case handling | Page was only found in search; not reviewed in detail |

I did not find a ServiceNow payments-exceptions product in search, so it is not in the table.

## Where PeX is different

1. **Evidence before recommendation.** Each exception type has a procedure listing the evidence needed, weighted across five pillars, with gate items that block approval. The 42 framework procedures are visible to Admin and Policy Owner. None of the products above publish this.
2. **Controls validate, humans authorise, bank systems execute.** PeX never moves money. Four-eyes and dual authorisation are policy parameters, changed only with a second Policy Owner's approval.
3. **Evidence zone.** Personal data is tokenised, classified C1 to C5, revealed only with a reason, for a limited time, and logged. Compliance alone sees screening data.
4. **Explainable by default.** Dossier of five checks per evidence item, per-case timeline, audit trail with hash chain.

## What PeX should include next (ranked for a bank buyer)

| Priority | Capability | Why | Status in PeX |
|---|---|---|---|
| 1 | **camt.110 / camt.111 case handling and UETR-linked Case Orchestrator interop** | Swift deadline: receive by Nov 2026, mandatory by end 2027. A bank cannot skip it | Not built. Ontology covers camt.056/029 only as message types |
| 2 | **Stop and Recall (camt.056 / camt.029) workflow** | Same deadline. Cancellation requests are a core exception type | Not built as a workflow |
| 3 | **Inbound email and message ingestion into cases** | Pega, SmartStream and Validata all do it | Not built |
| 4 | **Automated counterparty follow-up and reminders** | SmartStream's main time saver | Internal chasers exist (approver, supervisor, head of operations); outward-facing follow-up does not |
| 5 | **Packaged rulebook workflows (GPI, SEPA, TARGET)** | Banks expect them out of the box | SOP framework defaults exist; not tied to rulebooks |
| 6 | **Operations analytics: SLA, resolution time, automation rate** | Needed for the business case | Bank-wide dashboard exists; no trend or cost view |
| 7 | **Natural-language rule authoring** | Pega's Blueprint sets the expectation | Studio edits parameters only; compiler planned |
| 8 | **Agent interoperability (MCP)** | Pega advertises it; banks run several agents | Not built |
| 9 | **Real bank connectors** | Pilot readiness | Simulated, with a real-connector interface ready |

Recommendation: build 1 and 2 first. They are dated, mandatory, and a differentiator when combined with PeX's evidence and approval controls.

## Sources

- Swift: [Transforming exceptions and investigations](https://www.swift.com/news-events/news/transforming-exceptions-and-investigations)
- Pega: [Launch announcement, 16 Sept 2025](https://www.businesswire.com/news/home/20250916937803/en/Pega-Launches-First-Payment-Exceptions-and-Investigations-Solution-with-Native-Agentic-Capabilities-to-Speed-Resolution-and-Lower-Costs)
- Validata: [Payments Investigation and Case Manager](https://www.validata-software.com/solutions/payments-investigation-and-case-manager/)
- SmartStream: [Smart Payments](https://smart.stream/solutions/smart-payments/)
- Bottomline: [ISO 20022-enabled customer case management](https://www.bottomline.com/resources/blog/iso-20022-enabled-customer-case-management-final-hurdle-overcome-achieving-payments-modernisation)
