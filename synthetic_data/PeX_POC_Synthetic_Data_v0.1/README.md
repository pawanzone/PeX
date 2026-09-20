# PeX Payment Exception Resolution Framework
## Synthetic POC Dataset v0.1

This package contains synthetic, non-production banking data for the PeX POC. No real customer, account, payment or bank data is used.

The dataset is relational and intentionally coherent:
payments -> parties/accounts/beneficiaries -> exceptions -> evidence/history/policies/reference data.

Six exception profiles:
1. Invalid IBAN
2. Invalid BIC/SWIFT
3. Duplicate Payment
4. Sanctions Screening Hit
5. KYC Expired
6. Returned Payment

Each profile includes two active scenarios and one deliberately ambiguous scenario. Ambiguous cases should produce escalation / insufficient evidence.

Synthetic bank variability:
BANK_A = REST/PostgreSQL style
BANK_B = Kafka/legacy style
BANK_C = MQ/nested JSON style

Tokenization:
token_map.csv is a test-only mapping artifact and must NEVER be supplied to an external model.
Use stable tokens in AI-facing contexts and keep the mapping behind a controlled boundary.

Suggested POC flow:
Bank source event
 -> PeX Event Contract
 -> Canonical mapping
 -> Tokenization/minimization
 -> Evidence Planner
 -> Historical retrieval
 -> Semantic/LLM investigation
 -> Decision Contract
 -> Human approval
 -> Action simulation
 -> Audit

Evaluation:
evaluation_ground_truth.csv contains expected exception/recommendation/escalation labels for active cases.
