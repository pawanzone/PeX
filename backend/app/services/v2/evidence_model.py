"""PeX evidence & confidence model (single source of truth).

Used by (a) the runtime confidence engine on the case page and
(b) the generated evidence matrix documents. No app imports on purpose.

Concepts
- Evidence item: what the decision needs. Has a ROLE, a decision WEIGHT (sum = 100 per
  error type), a PILLAR (P1..P5), a SOURCE CLASS and a SYSTEM (-> connection option).
- GATE item: authority evidence. If missing/stale, the case cannot be sufficient
  regardless of the percentage (authority before confidence).
- Evidence coverage % = sum(weight of items present & fresh) / 100.
- Decision confidence % = family pillar scoring (see FAMILY_PILLARS) - ambiguity penalty.
  Pillar score = share of that pillar's item weight that is present & fresh; pillars with
  no items for an error type are dropped and the rest are re-normalised.
- Gate: confidence < CONFIDENCE_THRESHOLD (85) or a gate item missing -> extra manual approval.

Weights and pillar weights are PROPOSED starting values to be calibrated with the bank.
"""

CONFIDENCE_THRESHOLD = 85


def confidence_threshold() -> float:
    """The value in force (Rules & Policy Studio); CONFIDENCE_THRESHOLD is the shipped default."""
    from app.services.v2 import policy
    return policy.get("confidence_threshold")
PENALTY_MAX = 40

# source class: B = supplied by bank in the event, A = bank system API seek, X = external system
SYSTEMS = {
    "EVENT":   ("B", "Exception event / payload", "Supplied by bank with the event (MQ, file drop or REST push)"),
    "HUB":     ("B", "Payment hub / PSP message log", "Supplied in event or read from hub log (MQ topic / API)"),
    "CORE":    ("A", "Core banking (DDA, holds, status)", "Bank API (REST / MQ), read-only service account"),
    "CUSTM":   ("A", "Customer & beneficiary master (CRM)", "Bank API (REST) or nightly extract"),
    "SSI":     ("A", "SSI / counterparty / correspondent master", "Bank API (REST) or daily file"),
    "KYC":     ("A", "KYC / CLM platform", "Bank API (REST), read-only"),
    "LIMITS":  ("A", "Credit, limits & collateral system", "Bank API (REST / SQL view)"),
    "TREAS":   ("A", "Treasury / liquidity / nostro system", "Bank API; camt.052/053 statements"),
    "AML":     ("A", "Screening & AML case system", "Bank API (REST); case + disposition read"),
    "LEDGER":  ("A", "GL / sub-ledger / reconciliation", "Bank API or SQL read replica"),
    "ARCH":    ("A", "Message archive & payment history", "Bank data store (SQL / API) + PeX history"),
    "POLICY":  ("A", "Bank policy & SOP rules repository", "Config load from bank SOP (versioned, signed off)"),
    "MANDATE": ("A", "Mandate & signature system", "Bank API (REST)"),
    "CLIENT":  ("B", "Client-supplied documents", "Portal / email attachment forwarded in the event"),
    "ERP":     ("A", "Client ERP / AP ledger (host-to-host)", "H2H file or API with client consent"),
    "SWIFTREF": ("X", "SWIFTRef / BIC directory", "SWIFTRef API or bulk file (licensed)"),
    "IBANREG": ("X", "IBAN registry (SWIFT IBAN Plus / national)", "Licensed API or periodic file load"),
    "ISO":     ("X", "ISO 20022 schemas & code sets (incl. CBPR+/Fedwire guidelines)", "Versioned static load, refreshed per release"),
    "NATCLR":  ("X", "National clearing tables (ABA/FedACH, sort-code modulus, T2/CHAPS directories)", "Scheme file or vendor API"),
    "COPVOP":  ("X", "CoP / VoP scheme service", "Via bank's PSP gateway (API); EU VoP / UK CoP"),
    "FEDW":    ("X", "Fedwire Funds Service (pacs.002, admi.002, camt.110/111)", "FedLine Direct / FedPayments Manager"),
    "RTGS":    ("X", "Other RTGS / clearing (T2, CHAPS, CHIPS) calendars & status", "Participant gateway / scheme calendar feed"),
    "GPI":     ("X", "SWIFT gpi Tracker / Case Management (camt.110/111)", "gpi Tracker API; Case Orchestrator"),
    "LISTS":   ("X", "Sanctions lists & licences (OFAC SDN, EU, UN, HMT)", "List feed or vendor screening API"),
    "PEPV":    ("X", "PEP / adverse-media vendor", "Vendor API"),
    "FATF":    ("X", "FATF / EU high-risk jurisdiction lists", "Periodic list load"),
    "REG":     ("X", "Company registries / LEI (GLEIF)", "GLEIF API; national registry API"),
    "GEO":     ("X", "Postal & geocoding reference", "National postal file / geocoding API"),
    "FX":      ("X", "Market data / FX rate feed", "Market data API (bank-licensed)"),
    "CB":      ("X", "Central-bank account & reserve position", "Central-bank statement (camt.052/053) via gateway"),
    "STMT":    ("X", "Agent / correspondent statements (camt.053, camt.054, MT940)", "SWIFT FIN/FINplus or H2H"),
}

# role: ID identification, VAL validation, AUTH authorization, COR corroboration, CTX context
# pillars: P1 proof, P2 system-of-record grounding, P3 precedent, P4 rail/regime/policy coherence, P5 documentary corroboration
PILLAR_NAMES = {
    "P1": "Deterministic proof",
    "P2": "System-of-record grounding",
    "P3": "Precedent & settlement history",
    "P4": "Rail / regime / policy coherence",
    "P5": "Documentary corroboration",
}

# AG's original pillar weights (SKILL.md/slide) are the DQ family. Others are proposed.
FAMILY_PILLARS = {
    "DQ": {"P1": 30, "P2": 25, "P3": 20, "P4": 15, "P5": 10},
    "PR": {"P1": 30, "P2": 25, "P3": 10, "P4": 25, "P5": 10},
    "CO": {"P1": 25, "P2": 30, "P3": 10, "P4": 20, "P5": 15},
    "TR": {"P1": 30, "P2": 25, "P3": 10, "P4": 25, "P5": 10},
    "ST": {"P1": 25, "P2": 30, "P3": 15, "P4": 20, "P5": 10},
}
FAMILY_NAMES = {"DQ": "Data Quality", "PR": "Processing", "CO": "Compliance",
                "TR": "Treasury / Risk", "ST": "Settlement / Post-settlement"}
FAMILY_BIAN = {
    "DQ": "Payment Order; Public Reference Data Management; Party Reference Data Directory; Correspondent Bank Directory",
    "PR": "Payment Execution; Payment Rail Operations; Transaction Engine; Correspondent Bank Operations",
    "CO": "Regulatory Compliance; Guideline Compliance; Fraud Evaluation/Resolution; Party Lifecycle Management",
    "TR": "Position Keeping; Limit and Exposure Management; Credit and Margin Management; Party Lifecycle Management",
    "ST": "Open Item Management; Account Reconciliation; Correspondent Bank Operations; Customer Case Management",
}
FAMILY_QUEUE = {"DQ": "Repair", "PR": "Investigation / Repair", "CO": "Compliance", "TR": "Treasury", "ST": "Investigation"}


def I(name, role, w, pillar, sysk, gate=False):
    return {"name": name, "role": role, "weight": w, "pillar": pillar, "system": sysk, "gate": gate}


# id: (profile, standards basis, bank SOP placeholder, [items])
PROFILES = {
 "DQ-01": ("INVALID_IBAN", "ISO 13616 IBAN; ISO 7064 MOD-97-10; SWIFT IBAN Plus; FATF R16", [
   I("IBAN country structure + MOD-97 proof", "VAL", 25, "P1", "IBANREG"),
   I("Original payload (creditor IBAN, parties)", "ID", 15, "P1", "EVENT"),
   I("Beneficiary SSI master record", "AUTH", 25, "P2", "SSI", True),
   I("Beneficiary account status (open / active)", "VAL", 15, "P2", "CORE"),
   I("Historical repair / settlement precedent", "COR", 10, "P3", "ARCH"),
   I("CoP / VoP name check", "COR", 10, "P5", "COPVOP")]),
 "DQ-02": ("INVALID_BIC", "ISO 9362 BIC; SWIFTRef BIC directory; CBPR+ agent rules", [
   I("BIC format check (8/11 chars, ISO 9362)", "VAL", 20, "P1", "ISO"),
   I("BIC exists and is active in directory", "VAL", 30, "P2", "SWIFTREF", True),
   I("Payload agent BIC + clearing member ID", "ID", 15, "P1", "EVENT"),
   I("Counterparty bank in SSI / correspondent table", "AUTH", 20, "P2", "SSI"),
   I("Precedent for same BIC correction", "COR", 15, "P3", "ARCH")]),
 "DQ-03": ("MISSING_BENEFICIARY_DATA", "FATF R16 (originator/beneficiary info); EU Reg 2023/1113; ISO 20022 pacs.008 party fields", [
   I("Original payload (parties present)", "ID", 15, "P1", "EVENT"),
   I("Client beneficiary master record", "AUTH", 30, "P2", "CUSTM", True),
   I("Required-field set for corridor (R16 / scheme rules)", "VAL", 20, "P4", "POLICY"),
   I("Prior payments to same beneficiary", "COR", 20, "P3", "ARCH"),
   I("Client confirmation of beneficiary details", "COR", 15, "P5", "CLIENT")]),
 "DQ-04": ("MISSING_REMITTANCE_INFO", "ISO 20022 RmtInf (structured/unstructured); CBPR+ remittance rules", [
   I("Original payload", "ID", 15, "P1", "EVENT"),
   I("Commercial invoice / purchase order", "VAL", 30, "P5", "CLIENT", True),
   I("Client AP-ledger match for invoice", "COR", 25, "P2", "ERP"),
   I("Rail remittance length / structure limits", "VAL", 15, "P4", "ISO"),
   I("Precedent for same payer/payee", "COR", 15, "P3", "ARCH")]),
 "DQ-05": ("INVALID_ADDRESS_FORMAT", "ISO 20022 structured postal address (CBPR+ Nov-2026 rules); ISO 3166", [
   I("Original payload (address fields)", "ID", 15, "P1", "EVENT"),
   I("Structured-address schema / usage guideline", "VAL", 30, "P1", "ISO", True),
   I("Customer master address", "AUTH", 25, "P2", "CUSTM"),
   I("Postal / geocode reference match", "VAL", 20, "P4", "GEO"),
   I("Precedent for same party", "COR", 10, "P3", "ARCH")]),
 "DQ-06": ("MISSING_PURPOSE_CODE", "ISO 20022 External Purpose / Category Purpose code sets; corridor reporting rules", [
   I("Original payload", "ID", 15, "P1", "EVENT"),
   I("ISO purpose code set validity", "VAL", 25, "P1", "ISO"),
   I("Invoice / contract metadata", "COR", 25, "P5", "CLIENT"),
   I("Customer usual purpose (master / history)", "AUTH", 20, "P2", "CUSTM", True),
   I("Corridor purpose-code requirement", "VAL", 15, "P4", "POLICY")]),
 "DQ-07": ("INVALID_ACCOUNT_NUMBER", "National BBAN / modulus rules (UK sort-code modulus, ABA); ISO 13616 BBAN", [
   I("Original payload", "ID", 15, "P1", "EVENT"),
   I("National account-number format / modulus check", "VAL", 30, "P1", "NATCLR"),
   I("Account directory / SSI record", "AUTH", 25, "P2", "SSI", True),
   I("CoP / VoP corroboration", "COR", 15, "P5", "COPVOP"),
   I("Precedent for same beneficiary", "COR", 15, "P3", "ARCH")]),
 "DQ-08": ("INVALID_ROUTING_CODE", "ABA/FedACH directory; UK sort-code directory; T2/CHAPS participant directories", [
   I("Original payload", "ID", 15, "P1", "EVENT"),
   I("Routing code exists in scheme directory", "VAL", 30, "P2", "NATCLR", True),
   I("Participant active on target rail", "VAL", 20, "P4", "RTGS"),
   I("SSI / correspondent master", "AUTH", 20, "P2", "SSI"),
   I("Precedent for same routing correction", "COR", 15, "P3", "ARCH")]),
 "DQ-09": ("BENEFICIARY_NAME_MISMATCH", "UK Confirmation of Payee; EU Verification of Payee (Reg 2024/886); LEI (ISO 17442)", [
   I("Original payload (beneficiary name)", "ID", 5, "P1", "EVENT"),
   I("CoP / VoP response", "AUTH", 30, "P2", "COPVOP", True),
   I("Account-holder name on SSI / account record", "VAL", 25, "P2", "SSI"),
   I("Company registry / LEI legal name", "COR", 15, "P5", "REG"),
   I("Name-similarity score (deterministic)", "VAL", 10, "P1", "EVENT"),
   I("Precedent for same name variant", "COR", 10, "P3", "ARCH"),
   I("Client confirmation", "COR", 5, "P5", "CLIENT")]),
 "PR-01": ("DUPLICATE_PAYMENT", "ISO 20022 UETR / EndToEndId; Fedwire IMAD duplicate control; SWIFT gpi", [
   I("Payment identifiers (EndToEndId, UETR, MsgId, amount, date)", "ID", 20, "P1", "EVENT"),
   I("Payment ledger / history for same debtor-creditor-amount window", "AUTH", 30, "P2", "ARCH", True),
   I("Core settlement history (bank signal)", "VAL", 20, "P2", "CORE"),
   I("Rail duplicate status (gpi UETR / Fedwire IMAD)", "VAL", 20, "P4", "GPI"),
   I("Customer confirmation of intent", "COR", 10, "P5", "CLIENT")]),
 "PR-02": ("ROUTING_FAILURE", "Correspondent routing tables; SWIFT gpi routing; T2/CHAPS/Fedwire eligibility", [
   I("Original payload", "ID", 15, "P1", "EVENT"),
   I("Correspondent / nostro routing table", "AUTH", 30, "P2", "SSI", True),
   I("Rail and corridor availability", "VAL", 25, "P4", "RTGS"),
   I("gpi last-hop status", "VAL", 15, "P4", "GPI"),
   I("Precedent route for corridor", "COR", 15, "P3", "ARCH")]),
 "PR-03": ("ISO20022_VALIDATION_ERROR", "ISO 20022 XSD; CBPR+ usage guidelines; Fedwire ISO 20022 usage rules", [
   I("Raw XML payload", "ID", 20, "P1", "EVENT"),
   I("XSD + CBPR+/Fedwire usage-guideline validation", "VAL", 35, "P1", "ISO", True),
   I("Rail rejection (admi.002 / pacs.002 reason)", "VAL", 20, "P4", "FEDW"),
   I("Archived original message", "COR", 10, "P2", "ARCH"),
   I("Precedent for same schema error", "COR", 15, "P3", "ARCH")]),
 "PR-04": ("CUTOFF_MISSED", "Rail operating hours (Fedwire, T2, CHAPS); bank cut-off SLA", [
   I("Payload timestamps and value date", "ID", 15, "P1", "EVENT"),
   I("Rail cut-off schedule and holiday calendar", "VAL", 35, "P4", "RTGS", True),
   I("Timestamp audit trail", "VAL", 20, "P2", "HUB"),
   I("Client value-date instruction / SLA", "COR", 15, "P4", "POLICY"),
   I("Precedent next-day handling", "COR", 15, "P3", "ARCH")]),
 "PR-05": ("CORRUPTED_MESSAGE_FORMAT", "ISO 20022 / MT syntax; Fedwire admi.006 retrieval; message integrity", [
   I("Raw byte buffer", "ID", 25, "P1", "EVENT"),
   I("Archived original message copy", "AUTH", 30, "P2", "ARCH", True),
   I("Schema / encoding check", "VAL", 20, "P1", "ISO"),
   I("Sender re-transmission confirmation", "COR", 15, "P5", "HUB"),
   I("Precedent", "COR", 10, "P3", "ARCH")]),
 "PR-06": ("INTERMEDIARY_BANK_REJECTION", "ISO 20022 pacs.002 / pacs.004 / camt.029 reason codes; SWIFT gpi", [
   I("Rejection message (pacs.002 NACK / pacs.004) with reason", "ID", 25, "P1", "HUB", True),
   I("Correspondent agreement / SLA terms", "VAL", 20, "P4", "POLICY"),
   I("Compliance-reason exclusion check", "VAL", 20, "P2", "AML"),
   I("Alternate route in SSI", "COR", 15, "P2", "SSI"),
   I("Precedent for same reason / bank", "COR", 20, "P3", "ARCH")]),
 "PR-07": ("NETWORK_TIMEOUT", "SWIFT gpi Tracker (ACSP/ACCC/RJCT); UETR duplicate control", [
   I("gpi Tracker status", "AUTH", 30, "P4", "GPI", True),
   I("Network gateway logs", "ID", 25, "P1", "HUB"),
   I("Transaction state (was it sent?)", "VAL", 25, "P2", "ARCH"),
   I("UETR duplicate guard (never resend blind)", "VAL", 10, "P4", "GPI"),
   I("Precedent", "COR", 10, "P3", "ARCH")]),
 "PR-08": ("QUEUE_PROCESSING_FAILURE", "Exactly-once / idempotency; broker DLQ operations", [
   I("Broker DLQ metadata", "ID", 25, "P1", "HUB"),
   I("Transaction state (exactly-once check)", "AUTH", 30, "P2", "ARCH", True),
   I("Idempotency key / UETR", "VAL", 20, "P4", "EVENT"),
   I("Downstream acknowledgement", "VAL", 15, "P4", "HUB"),
   I("Precedent", "COR", 10, "P3", "ARCH")]),
 "PR-09": ("PAYMENT_HELD_FOR_REPAIR", "Bank operations hold taxonomy", [
   I("Core hold flag and reason", "AUTH", 30, "P2", "CORE", True),
   I("Operations note", "COR", 15, "P5", "ARCH"),
   I("Original payload", "ID", 15, "P1", "EVENT"),
   I("Repair rule for hold reason (SOP)", "VAL", 25, "P4", "POLICY"),
   I("Precedent", "COR", 15, "P3", "ARCH")]),
 "CO-01": ("SANCTIONS_SUSPECTED", "OFAC / EU / UN / HMT lists; FATF R6 & R16; FFIEC BSA/AML manual; Wolfsberg", [
   I("Screening alert (list, score, matched fields)", "ID", 25, "P1", "AML", True),
   I("Watchlist entry (identifiers, DoB, aliases)", "AUTH", 25, "P2", "LISTS", True),
   I("Customer KYC identifiers", "VAL", 15, "P2", "KYC"),
   I("Prior dispositions for same match key", "COR", 15, "P3", "AML"),
   I("Supporting ID / ownership documents", "COR", 10, "P5", "KYC"),
   I("Sanctions regime and licence applicability", "VAL", 10, "P4", "LISTS")]),
 "CO-02": ("AML_ALERT", "FATF R10/R20; FFIEC BSA/AML; Wolfsberg; bank typology rules", [
   I("Rule / typology hit and velocity index", "ID", 25, "P1", "AML", True),
   I("Source of wealth / funds documents", "COR", 25, "P5", "KYC"),
   I("Customer risk rating and expected activity", "VAL", 20, "P2", "KYC"),
   I("Prior alerts / SAR history", "COR", 15, "P3", "AML"),
   I("Counterparty and jurisdiction risk", "VAL", 15, "P4", "FATF")]),
 "CO-03": ("PEP_MATCH", "FATF R12 (PEPs); EDD policy; vendor PEP data", [
   I("PEP registry hit (category, position)", "ID", 25, "P1", "PEPV"),
   I("Current EDD certificate / senior approval", "AUTH", 25, "P2", "KYC", True),
   I("Source of wealth", "COR", 20, "P5", "KYC"),
   I("Relationship / associate link", "VAL", 15, "P4", "PEPV"),
   I("Prior decision", "COR", 15, "P3", "AML")]),
 "CO-04": ("RESTRICTED_CORRIDOR", "OFAC programmes / EU restrictive measures; bank corridor policy; licences", [
   I("Statutory restriction matrix for corridor", "AUTH", 30, "P4", "LISTS", True),
   I("Bank corridor policy", "AUTH", 25, "P4", "POLICY", True),
   I("Licence (general / specific) if relied on", "VAL", 20, "P2", "LISTS"),
   I("Underlying trade / purpose documents", "COR", 15, "P5", "CLIENT"),
   I("Precedent", "COR", 10, "P3", "AML")]),
 "CO-05": ("ADVERSE_MEDIA_MATCH", "Wolfsberg adverse-media guidance; FATF R10 (ongoing due diligence)", [
   I("Adverse-media report (source, date)", "ID", 25, "P1", "PEPV"),
   I("Entity disambiguation (identifiers)", "AUTH", 25, "P2", "REG", True),
   I("Legal-status check (court / regulator)", "VAL", 25, "P2", "REG"),
   I("Prior review", "COR", 10, "P3", "AML"),
   I("Customer explanation", "COR", 15, "P5", "CLIENT")]),
 "CO-06": ("HIGH_RISK_JURISDICTION", "FATF high-risk & monitored lists; EU high-risk third countries; FATF R19", [
   I("FATF / EU list status for country", "AUTH", 30, "P4", "FATF", True),
   I("Country exposure and nostro justification", "VAL", 20, "P2", "POLICY"),
   I("Customer EDD / stated purpose", "COR", 20, "P5", "KYC"),
   I("Payment details", "ID", 15, "P1", "EVENT"),
   I("Precedent", "COR", 15, "P3", "AML")]),
 "CO-07": ("REGULATORY_REPORTING_REQUIRED", "Balance-of-payments / customs reporting; CTR thresholds; local FX regulations", [
   I("Customs declaration", "COR", 25, "P5", "CLIENT"),
   I("Trade contract / invoice", "COR", 20, "P5", "CLIENT"),
   I("Reporting regime and threshold rule", "AUTH", 30, "P4", "POLICY", True),
   I("Payment details", "ID", 15, "P1", "EVENT"),
   I("Precedent", "COR", 10, "P3", "ARCH")]),
 "CO-08": ("CUSTOMER_WATCHLIST_MATCH", "Internal watchlist / exit policy; Wolfsberg", [
   I("Internal watchlist entry and reason", "AUTH", 30, "P2", "AML", True),
   I("Exit memo / relationship status", "VAL", 25, "P2", "KYC"),
   I("Payment parties", "ID", 15, "P1", "EVENT"),
   I("Prior dispositions", "COR", 15, "P3", "AML"),
   I("Compliance instruction on file", "VAL", 15, "P4", "POLICY")]),
 "TR-01": ("KYC_EXPIRED", "FATF R10 (CDD); bank periodic-review policy; provisional waiver SOP", [
   I("KYC record and expiry date", "AUTH", 30, "P2", "KYC", True),
   I("Beneficial ownership (current)", "VAL", 25, "P2", "KYC"),
   I("Periodic-review / waiver policy", "VAL", 20, "P4", "POLICY"),
   I("Customer risk rating", "COR", 15, "P2", "KYC"),
   I("Document refresh evidence", "COR", 10, "P5", "CLIENT")]),
 "TR-02": ("INSUFFICIENT_FUNDS", "Bank account & overdraft policy; BCBS 248 intraday liquidity (context)", [
   I("DDA ledger balance and holds", "AUTH", 35, "P1", "CORE", True),
   I("Daylight / overdraft facility", "VAL", 25, "P2", "LIMITS"),
   I("Scheduled incoming credits", "COR", 15, "P4", "TREAS"),
   I("Customer funding pattern", "COR", 15, "P3", "ARCH"),
   I("Payload amount and value date", "ID", 10, "P1", "EVENT")]),
 "TR-03": ("NOSTRO_SHORTFALL", "camt.052 / camt.053 / MT942; nostro funding SOP", [
   I("Nostro position and projection", "AUTH", 35, "P1", "TREAS", True),
   I("Intraday sweep pool", "VAL", 25, "P2", "TREAS"),
   I("Correspondent funding cut-off", "VAL", 15, "P4", "RTGS"),
   I("Precedent funding action", "COR", 10, "P3", "ARCH"),
   I("Payload", "ID", 15, "P1", "EVENT")]),
 "TR-04": ("FX_RATE_UNAVAILABLE", "Market data policy; ISO 4217; bank dealing tolerance", [
   I("Live FX rate", "AUTH", 35, "P1", "FX", True),
   I("Quote tolerance band", "VAL", 25, "P4", "POLICY"),
   I("Booked deal / client rate", "VAL", 20, "P2", "TREAS"),
   I("Currency and value date in payload", "ID", 10, "P1", "EVENT"),
   I("Precedent", "COR", 10, "P3", "ARCH")]),
 "TR-05": ("AUTHORIZATION_MISSING", "Mandate matrix; four-eyes / dual authorisation; signature verification", [
   I("Mandate matrix", "AUTH", 35, "P2", "MANDATE", True),
   I("Signature record", "VAL", 25, "P1", "MANDATE"),
   I("Approvals present in payload", "ID", 15, "P1", "EVENT"),
   I("Delegated authority and limits", "VAL", 15, "P4", "POLICY"),
   I("Customer confirmation", "COR", 10, "P5", "CLIENT")]),
 "TR-06": ("LIMIT_BREACH", "Bank limit framework; large-exposure policy", [
   I("Exposure index", "AUTH", 30, "P1", "LIMITS", True),
   I("Limit definition and headroom", "VAL", 25, "P2", "LIMITS"),
   I("RM exception memo", "COR", 20, "P5", "CUSTM"),
   I("Payload", "ID", 10, "P1", "EVENT"),
   I("Precedent", "COR", 15, "P3", "ARCH")]),
 "TR-07": ("LIQUIDITY_CONSTRAINT", "BCBS 248 intraday liquidity monitoring; central-bank reserve rules", [
   I("Central-bank reserve / buffer position", "AUTH", 30, "P1", "CB", True),
   I("Netting / incoming schedule", "VAL", 25, "P4", "TREAS"),
   I("Intraday liquidity forecast", "VAL", 20, "P2", "TREAS"),
   I("Payment prioritisation policy", "VAL", 15, "P4", "POLICY"),
   I("Precedent", "COR", 10, "P3", "ARCH")]),
 "TR-08": ("CREDIT_EXPOSURE_BREACH", "Bank credit policy; collateral & margin terms", [
   I("Credit line registry", "AUTH", 30, "P2", "LIMITS", True),
   I("Collateral and margin", "VAL", 25, "P2", "LIMITS"),
   I("Exposure calculation", "VAL", 20, "P1", "LIMITS"),
   I("Credit approval memo", "COR", 15, "P5", "CUSTM"),
   I("Precedent", "COR", 10, "P3", "ARCH")]),
 "ST-01": ("RETURNED_PAYMENT", "ISO 20022 pacs.004 + ExternalReturnReason1Code; camt.029", [
   I("Return message pacs.004 with reason", "ID", 25, "P1", "HUB", True),
   I("Original payment pacs.008", "VAL", 20, "P2", "ARCH"),
   I("Settlement ledger state", "VAL", 20, "P2", "LEDGER"),
   I("Core account status", "VAL", 15, "P2", "CORE"),
   I("ISO return-reason code set", "VAL", 10, "P1", "ISO"),
   I("Return disposition / fee / corridor policy", "VAL", 10, "P4", "POLICY")]),
 "ST-02": ("ACCOUNT_CLOSED", "ISO return reason AC04 (ClosedAccountNumber)", [
   I("AC04 return record", "ID", 30, "P1", "HUB", True),
   I("Escrow / suspense handling policy", "VAL", 20, "P4", "POLICY"),
   I("Customer master (new account details)", "AUTH", 25, "P2", "CUSTM"),
   I("Original payment", "VAL", 15, "P2", "ARCH"),
   I("CoP / VoP on new details", "COR", 10, "P5", "COPVOP")]),
 "ST-03": ("BENEFICIARY_ACCOUNT_FROZEN", "ISO return reason AC06 (BlockedAccount); legal-order handling", [
   I("AC06 legal-block notice", "ID", 30, "P1", "HUB", True),
   I("Reversal ledger", "VAL", 25, "P2", "LEDGER"),
   I("Legal authority reference", "VAL", 20, "P4", "POLICY"),
   I("Original payment", "VAL", 15, "P2", "ARCH"),
   I("Sanctions linkage check", "VAL", 10, "P4", "AML")]),
 "ST-04": ("RECONCILIATION_BREAK", "camt.053 / camt.054; account reconciliation SOP", [
   I("Statement entry (camt.053)", "ID", 30, "P1", "STMT"),
   I("Sub-ledger record", "AUTH", 30, "P2", "LEDGER", True),
   I("Payment reference / UETR", "VAL", 15, "P1", "HUB"),
   I("Ageing and tolerance policy", "VAL", 15, "P4", "POLICY"),
   I("Precedent", "COR", 10, "P3", "ARCH")]),
 "ST-05": ("SETTLEMENT_FAILURE", "Fedwire pacs.002 RJCT / admi.002; T2 NACK; message authentication", [
   I("RTGS NACK / rejection", "ID", 30, "P1", "FEDW", True),
   I("Message authentication / signature proof", "VAL", 20, "P1", "HUB"),
   I("Account / liquidity state", "VAL", 20, "P2", "TREAS"),
   I("Payment record", "VAL", 15, "P2", "ARCH"),
   I("Precedent", "COR", 15, "P3", "ARCH")]),
 "ST-06": ("FUNDS_TRAPPED_AT_CORRESPONDENT", "camt.027 claim; camt.110/111 investigation; gpi Tracker; Stop & Recall", [
   I("Claim / investigation status (camt.027 / camt.110-111)", "ID", 25, "P1", "GPI", True),
   I("Intermediary correspondence", "COR", 20, "P5", "GPI"),
   I("gpi last-hop status", "VAL", 25, "P4", "GPI"),
   I("Original payment record", "VAL", 15, "P2", "ARCH"),
   I("Compliance-hold exclusion check", "VAL", 15, "P4", "AML")]),
 "ST-07": ("UNMATCHED_CREDIT", "camt.054 credit notification; ISO 20022 remittance; open-item management", [
   I("Incoming credit entry (camt.054 / 053)", "ID", 25, "P1", "STMT", True),
   I("Customer name variations / aliases", "AUTH", 25, "P2", "CUSTM"),
   I("Suspense credit entry", "VAL", 20, "P2", "LEDGER"),
   I("Open-item candidates from payment history", "COR", 20, "P3", "ARCH"),
   I("Remittance info / UETR on credit", "COR", 10, "P5", "EVENT")]),
 "ST-08": ("GENERAL_EXCEPTION", "Fallback - unclassified; always manual", [
   I("Raw payload", "ID", 40, "P1", "EVENT", True),
   I("Rule-based classification hypothesis", "VAL", 20, "P2", "POLICY"),
   I("Archived message", "COR", 20, "P2", "ARCH"),
   I("Precedent", "COR", 20, "P3", "ARCH")]),
}

# Fallback profile (not one of the 41) always capped below threshold
ALWAYS_MANUAL = {"GENERAL_EXCEPTION"}
# Compliance family never auto-clears: confidence is computed but the case always keeps compliance routing
FAMILY_ALWAYS_ROUTED = {"CO"}

_FAMILY_OF = lambda pid: pid.split("-")[0]
BY_PROFILE = {v[0]: (k, v) for k, v in PROFILES.items()}


def _check():
    for pid, (name, std, items) in PROFILES.items():
        s = sum(i["weight"] for i in items)
        assert s == 100, (pid, name, s)
        assert any(i["gate"] for i in items), (pid, "no gate item")
    for f, p in FAMILY_PILLARS.items():
        assert sum(p.values()) == 100, f
_check()


def sop_ref(pid):
    return f"SOP-{pid} (placeholder - replace with bank SOP clause)"


def score(profile_name, states, ambiguity=0):
    """states: {item_name: 'PRESENT'|'MISSING'|'STALE'|'CONFLICT'}; missing keys = MISSING.
    Returns dict with coverage %, confidence %, pillar breakdown, gate result."""
    pid, (_, std, items) = BY_PROFILE[profile_name]
    fam = _FAMILY_OF(pid)
    pw = FAMILY_PILLARS[fam]
    ok = lambda it: states.get(it["name"], "MISSING") == "PRESENT"
    coverage = sum(i["weight"] for i in items if ok(i))
    pillars = {}
    for p in pw:
        its = [i for i in items if i["pillar"] == p]
        if not its:
            continue
        tot = sum(i["weight"] for i in its)
        got = sum(i["weight"] for i in its if ok(i))
        pillars[p] = (got / tot, pw[p])
    wsum = sum(w for _, w in pillars.values())
    raw = sum(frac * w for frac, w in pillars.values()) / wsum * 100 if wsum else 0
    penalty = min(max(ambiguity, 0), PENALTY_MAX)
    conf = max(0.0, raw - penalty)
    gates_missing = [i["name"] for i in items if i["gate"] and not ok(i)]
    thr = confidence_threshold()
    manual = conf < thr or bool(gates_missing) or profile_name in ALWAYS_MANUAL
    reasons = []
    if conf < thr:
        reasons.append(f"Confidence {conf:.0f}% is below the {thr:g}% threshold")
    if gates_missing:
        reasons.append("Authority evidence missing or stale: " + ", ".join(gates_missing))
    if profile_name in ALWAYS_MANUAL:
        reasons.append("Unclassified exception always needs manual review")
    return {"profile": profile_name, "profile_id": pid, "family": fam, "coverage_pct": round(coverage, 1),
            "confidence_pct": round(conf, 1), "raw_pct": round(raw, 1), "penalty_pct": penalty,
            "pillars": {p: {"name": PILLAR_NAMES[p], "weight": w, "score_pct": round(f * 100)} for p, (f, w) in pillars.items()},
            "gates_missing": gates_missing, "extra_approval": manual, "reasons": reasons,
            "threshold": thr}


if __name__ == "__main__":
    for pid, (n, _, items) in PROFILES.items():
        full = {i["name"]: "PRESENT" for i in items}
        assert score(n, full)["confidence_pct"] == 100
    print(len(PROFILES), "profiles ok")
