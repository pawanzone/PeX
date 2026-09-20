"""Exception Profile Engine: Profile specifications & mandatory evidence gates across all 41 profiles."""
from typing import Dict, List, Any
from app.schemas.canonical import ExceptionProfile, ExceptionDomain, get_domain_for_profile

PROFILE_SPECS: Dict[ExceptionProfile, Dict[str, Any]] = {
    # === DOMAIN 1: DATA QUALITY (9 Profiles) ===
    ExceptionProfile.INVALID_IBAN: {
        "domain": ExceptionDomain.DATA_QUALITY,
        "title": "Invalid Beneficiary IBAN",
        "description": "Validates format, country code length, and ISO 7064 MOD-97 checksum against beneficiary standing directory.",
        "default_queue": "Repair",
        "mandatory_evidence": ["BENEFICIARY_PROFILE", "ACCOUNT_DIRECTORY"],
        "min_confidence": 0.85
    },
    ExceptionProfile.INVALID_BIC: {
        "domain": ExceptionDomain.DATA_QUALITY,
        "title": "Invalid Routing BIC",
        "description": "Cross-references SWIFT BIC directory and national clearing codes (Fedwire, CHAPS, SEPA).",
        "default_queue": "Repair",
        "mandatory_evidence": ["BIC_DIRECTORY", "REFERENCE_DATA"],
        "min_confidence": 0.90
    },
    ExceptionProfile.MISSING_BENEFICIARY_DATA: {
        "domain": ExceptionDomain.DATA_QUALITY,
        "title": "Missing Beneficiary Data",
        "description": "Validates presence of creditor legal name, registration identifiers, and structured address elements.",
        "default_queue": "Repair",
        "mandatory_evidence": ["BENEFICIARY_PROFILE", "CLIENT_VAULT"],
        "min_confidence": 0.88
    },
    ExceptionProfile.MISSING_REMITTANCE_INFO: {
        "domain": ExceptionDomain.DATA_QUALITY,
        "title": "Missing Remittance Information",
        "description": "Checks structured remittance tags (<Strd>) against debtor AP commercial invoice repository.",
        "default_queue": "Repair",
        "mandatory_evidence": ["COMMERCIAL_INVOICE", "PURCHASE_ORDER"],
        "min_confidence": 0.85
    },
    ExceptionProfile.INVALID_ADDRESS_FORMAT: {
        "domain": ExceptionDomain.DATA_QUALITY,
        "title": "Invalid Postal Address Format",
        "description": "Enforces ISO 20022 / CBPR+ discrete structured address elements (Street, Building, Post Code, Town).",
        "default_queue": "Repair",
        "mandatory_evidence": ["ADDRESS_SCHEMA", "GEODATA_VAULT"],
        "min_confidence": 0.90
    },
    ExceptionProfile.MISSING_PURPOSE_CODE: {
        "domain": ExceptionDomain.DATA_QUALITY,
        "title": "Missing Regulatory Purpose Code",
        "description": "Identifies mandatory 4-character ISO 20022 external purpose code required by destination central bank.",
        "default_queue": "Repair",
        "mandatory_evidence": ["PURPOSE_DIRECTORY", "INVOICE_METADATA"],
        "min_confidence": 0.92
    },
    ExceptionProfile.INVALID_ACCOUNT_NUMBER: {
        "domain": ExceptionDomain.DATA_QUALITY,
        "title": "Invalid Domestic Account Number",
        "description": "Validates non-IBAN domestic bank account against national modulus rules (ABA DDA, Sort Code Modulus).",
        "default_queue": "Repair",
        "mandatory_evidence": ["NATIONAL_CLEARING_MODULUS", "ACCOUNT_DIRECTORY"],
        "min_confidence": 0.88
    },
    ExceptionProfile.INVALID_ROUTING_CODE: {
        "domain": ExceptionDomain.DATA_QUALITY,
        "title": "Invalid National Routing Transit Code",
        "description": "Cross-references national clearing transit directories (US Fedwire ABA, UK Sort Code, AU BSB).",
        "default_queue": "Repair",
        "mandatory_evidence": ["TRANSIT_DIRECTORY", "CENTRAL_BANK_ROUTING"],
        "min_confidence": 0.90
    },
    ExceptionProfile.BENEFICIARY_NAME_MISMATCH: {
        "domain": ExceptionDomain.DATA_QUALITY,
        "title": "Beneficiary Name Mismatch (Confirmation of Payee)",
        "description": "Scores legal name on instruction against creditor bank ledger using Verification of Payee (VoP) algorithms.",
        "default_queue": "Repair",
        "mandatory_evidence": ["COP_RECORD", "COMPANY_REGISTRY"],
        "min_confidence": 0.85
    },

    # === DOMAIN 2: PROCESSING (9 Profiles) ===
    ExceptionProfile.DUPLICATE_PAYMENT: {
        "domain": ExceptionDomain.PROCESSING,
        "title": "Duplicate Payment Suspected",
        "description": "Identifies identical amount, counterparty, and instruction timestamps within rolling 30m/24h window.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["PAYMENT_LEDGER", "SETTLEMENT_HISTORY"],
        "min_confidence": 0.95
    },
    ExceptionProfile.ROUTING_FAILURE: {
        "domain": ExceptionDomain.PROCESSING,
        "title": "Corridor Routing Failure",
        "description": "Isolates broken intermediary correspondent hops and evaluates alternate clearing paths.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["CORRESPONDENT_TABLE", "NOSTRO_DIRECTORY"],
        "min_confidence": 0.90
    },
    ExceptionProfile.ISO20022_VALIDATION_ERROR: {
        "domain": ExceptionDomain.PROCESSING,
        "title": "ISO 20022 XSD Schema Syntax Error",
        "description": "Validates CBPR+ XML document against central ISO 20022 schemas and tag constraints.",
        "default_queue": "Repair",
        "mandatory_evidence": ["XSD_SCHEMA", "RAW_XML_PAYLOAD"],
        "min_confidence": 0.94
    },
    ExceptionProfile.CUTOFF_MISSED: {
        "domain": ExceptionDomain.PROCESSING,
        "title": "Clearing Cutoff Window Missed",
        "description": "Detects instruction arrival past central bank RTGS gross settlement deadline; flags for value-date roll.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["RAIL_CUTOFF_SCHEDULE", "TIME_STAMP_AUDIT"],
        "min_confidence": 0.95
    },
    ExceptionProfile.CORRUPTED_MESSAGE_FORMAT: {
        "domain": ExceptionDomain.PROCESSING,
        "title": "Corrupted Message Encoding Format",
        "description": "Detects UTF-8 character encoding corruption, illegal control characters, or truncated byte buffers.",
        "default_queue": "Repair",
        "mandatory_evidence": ["RAW_BYTE_BUFFER", "MESSAGE_ARCHIVE"],
        "min_confidence": 0.92
    },
    ExceptionProfile.INTERMEDIARY_BANK_REJECTION: {
        "domain": ExceptionDomain.PROCESSING,
        "title": "Intermediary Correspondent Bank NACK",
        "description": "Processes pacs.002 negative acknowledgment from intermediary clearing hop.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["PACS002_NACK_RECORD", "INTERMEDIARY_CONTRACT"],
        "min_confidence": 0.90
    },
    ExceptionProfile.NETWORK_TIMEOUT: {
        "domain": ExceptionDomain.PROCESSING,
        "title": "Network Transport ACK Timeout",
        "description": "Correlates SWIFT gpi tracker status when outbound instruction exceeds delivery timeout SLA.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["GPI_TRACKER_LOG", "NETWORK_GATEWAY"],
        "min_confidence": 0.92
    },
    ExceptionProfile.QUEUE_PROCESSING_FAILURE: {
        "domain": ExceptionDomain.PROCESSING,
        "title": "Queue Deadlock / Processing Exception",
        "description": "Releases transactions stalled in message broker dead-letter queues after transient lock.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["BROKER_DLQ_METADATA", "TRANSACTION_STATE"],
        "min_confidence": 0.95
    },
    ExceptionProfile.PAYMENT_HELD_FOR_REPAIR: {
        "domain": ExceptionDomain.PROCESSING,
        "title": "Payment Held for Operational Repair",
        "description": "Internal core banking staging hold requiring operational enrichment before dispatch.",
        "default_queue": "Repair",
        "mandatory_evidence": ["CORE_BANKING_FLAG", "OPERATIONS_NOTE"],
        "min_confidence": 0.88
    },

    # === DOMAIN 3: COMPLIANCE (8 Profiles) ===
    ExceptionProfile.SANCTIONS_SUSPECTED: {
        "domain": ExceptionDomain.COMPLIANCE,
        "title": "Sanctions Screening Watchlist Hit",
        "description": "Evaluates fuzzy matching against OFAC, EU, UN, and UK OFSI consolidated watchlists.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["SCREENING_RECORD", "WATCHLIST_MATCH"],
        "min_confidence": 0.98
    },
    ExceptionProfile.AML_ALERT: {
        "domain": ExceptionDomain.COMPLIANCE,
        "title": "AML Structuring / Velocity Alert",
        "description": "Identifies irregular transaction volume bursts, circular routing, or transaction structuring patterns.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["VELOCITY_INDEX", "SOURCE_OF_WEALTH"],
        "min_confidence": 0.90
    },
    ExceptionProfile.PEP_MATCH: {
        "domain": ExceptionDomain.COMPLIANCE,
        "title": "Politically Exposed Person (PEP) Hit",
        "description": "Identifies ultimate beneficial owners holding senior public offices requiring Enhanced Due Diligence.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["PEP_REGISTRY", "EDD_CERTIFICATE"],
        "min_confidence": 0.92
    },
    ExceptionProfile.RESTRICTED_CORRIDOR: {
        "domain": ExceptionDomain.COMPLIANCE,
        "title": "Restricted / Embargoed Corridor Hit",
        "description": "Evaluates geographic routing intersections with comprehensive sanctioned territories or embargoes.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["GEOPOLITICAL_REGISTRY", "OFAC_LICENSE_DB"],
        "min_confidence": 0.98
    },
    ExceptionProfile.ADVERSE_MEDIA_MATCH: {
        "domain": ExceptionDomain.COMPLIANCE,
        "title": "Adverse Media Screening Match",
        "description": "Evaluates negative news screening relating to corporate fraud, bribery, or financial misconduct.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["ADVERSE_MEDIA_REPORT", "LEGAL_STATUS_CHECK"],
        "min_confidence": 0.88
    },
    ExceptionProfile.HIGH_RISK_JURISDICTION: {
        "domain": ExceptionDomain.COMPLIANCE,
        "title": "FATF High-Risk Jurisdiction Alert",
        "description": "Applies Wolfsberg / FATF grey & black list increased monitoring controls to correspondent hops.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["FATF_INDEX", "NOSTRO_JUSTIFICATION"],
        "min_confidence": 0.90
    },
    ExceptionProfile.REGULATORY_REPORTING_REQUIRED: {
        "domain": ExceptionDomain.COMPLIANCE,
        "title": "Mandatory Regulatory BoP Declaration Required",
        "description": "Enforces Balance of Payments / foreign exchange declarations required by national central banks.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["CUSTOMS_DECLARATION", "TRADE_CONTRACT"],
        "min_confidence": 0.92
    },
    ExceptionProfile.CUSTOMER_WATCHLIST_MATCH: {
        "domain": ExceptionDomain.COMPLIANCE,
        "title": "Internal Customer Risk Blacklist Hit",
        "description": "Identifies entities flagged in internal bank operational risk and off-boarded accounts registries.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["INTERNAL_BLACKLIST", "EXIT_MEMO"],
        "min_confidence": 0.95
    },

    # === DOMAIN 4: CLIENT / TREASURY (8 Profiles) ===
    ExceptionProfile.KYC_EXPIRED: {
        "domain": ExceptionDomain.CLIENT_TREASURY,
        "title": "KYC Profile Expired / Missing",
        "description": "Checks customer periodic review dates and governs SOP-302 30-day provisional waiver authorization.",
        "default_queue": "Compliance",
        "mandatory_evidence": ["KYC_RECORD", "BENEFICIAL_OWNERSHIP"],
        "min_confidence": 0.90
    },
    ExceptionProfile.INSUFFICIENT_FUNDS: {
        "domain": ExceptionDomain.CLIENT_TREASURY,
        "title": "Debtor Insufficient Account Balance",
        "description": "Evaluates ordering customer balance against wire amount plus fees and intraday credit line.",
        "default_queue": "Treasury",
        "mandatory_evidence": ["DDA_LEDGER_BALANCE", "DAYLIGHT_FACILITY"],
        "min_confidence": 0.95
    },
    ExceptionProfile.NOSTRO_SHORTFALL: {
        "domain": ExceptionDomain.CLIENT_TREASURY,
        "title": "Nostro Corridor Liquidity Shortfall",
        "description": "Monitors bank's own Nostro account balances across international clearing corridors.",
        "default_queue": "Treasury",
        "mandatory_evidence": ["NOSTRO_POSITION", "INTRADAY_SWEEP_POOL"],
        "min_confidence": 0.95
    },
    ExceptionProfile.FX_RATE_UNAVAILABLE: {
        "domain": ExceptionDomain.CLIENT_TREASURY,
        "title": "FX Rate Lock Unavailable / Timed Out",
        "description": "Resolves rate quote expiration on cross-currency wires via secondary FX market aggregator.",
        "default_queue": "Treasury",
        "mandatory_evidence": ["FX_RATE_FEED", "QUOTE_TOLERANCE_BAND"],
        "min_confidence": 0.92
    },
    ExceptionProfile.AUTHORIZATION_MISSING: {
        "domain": ExceptionDomain.CLIENT_TREASURY,
        "title": "Corporate Client Mandate Signature Missing",
        "description": "Verifies dual corporate signatory mandate rules under customer banking agreement.",
        "default_queue": "Treasury",
        "mandatory_evidence": ["MANDATE_MATRIX", "SIGNATURE_VAULT"],
        "min_confidence": 0.90
    },
    ExceptionProfile.LIMIT_BREACH: {
        "domain": ExceptionDomain.CLIENT_TREASURY,
        "title": "Corporate Daily Limit Cap Breached",
        "description": "Evaluates transaction against customer single-wire and daily cumulative exposure caps.",
        "default_queue": "Treasury",
        "mandatory_evidence": ["EXPOSURE_INDEX", "RM_EXCEPTION_MEMO"],
        "min_confidence": 0.92
    },
    ExceptionProfile.LIQUIDITY_CONSTRAINT: {
        "domain": ExceptionDomain.CLIENT_TREASURY,
        "title": "Intraday Liquidity Buffer Constraint",
        "description": "Queues high-value outflows to preserve central bank reserve minimums under BCBS 248.",
        "default_queue": "Treasury",
        "mandatory_evidence": ["CENTRAL_BANK_BUFFER", "NETTING_SCHEDULE"],
        "min_confidence": 0.94
    },
    ExceptionProfile.CREDIT_EXPOSURE_BREACH: {
        "domain": ExceptionDomain.CLIENT_TREASURY,
        "title": "Counterparty Bank Credit Ceiling Breach",
        "description": "Enforces risk ceiling on total unsettled gross positions with beneficiary financial institution.",
        "default_queue": "Treasury",
        "mandatory_evidence": ["CREDIT_LINE_REGISTRY", "COLLATERAL_MARGIN"],
        "min_confidence": 0.92
    },

    # === DOMAIN 5: SETTLEMENT / RETURNS (7 Profiles) ===
    ExceptionProfile.RETURNED_PAYMENT: {
        "domain": ExceptionDomain.SETTLEMENT_RETURNS,
        "title": "Returned Payment (pacs.004 / camt.056)",
        "description": "Processes incoming payment return messages and maps ISO external return reason codes.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["RETURN_REASON_CODE", "ORIGINAL_PAYMENT"],
        "min_confidence": 0.90
    },
    ExceptionProfile.ACCOUNT_CLOSED: {
        "domain": ExceptionDomain.SETTLEMENT_RETURNS,
        "title": "Creditor Account Closed (pacs.004 AC04)",
        "description": "Manages return reconciliation when receiving bank returns payment for closed account.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["AC04_RETURN_RECORD", "DEBTOR_ESCROW"],
        "min_confidence": 0.95
    },
    ExceptionProfile.BENEFICIARY_ACCOUNT_FROZEN: {
        "domain": ExceptionDomain.SETTLEMENT_RETURNS,
        "title": "Beneficiary Account Frozen (pacs.004 AC06)",
        "description": "Handles return workflows when creditor account is legally blocked or under court garnishment.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["AC06_LEGAL_BLOCK", "REVERSAL_LEDGER"],
        "min_confidence": 0.95
    },
    ExceptionProfile.RECONCILIATION_BREAK: {
        "domain": ExceptionDomain.SETTLEMENT_RETURNS,
        "title": "End-of-Day Ledger Reconciliation Break",
        "description": "Identifies discrepancies between camt.053 bank statements and internal settlement ledger.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["CAMT053_STATEMENT", "SUBLEDGER_RECORD"],
        "min_confidence": 0.92
    },
    ExceptionProfile.SETTLEMENT_FAILURE: {
        "domain": ExceptionDomain.SETTLEMENT_RETURNS,
        "title": "Clearing Hub Settlement Delivery Failure",
        "description": "Resolves delivery failure on RTGS clearing network due to hash verification or network outage.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["RTGS_NACK_LOG", "DIGITAL_SIGNATURE_PROOF"],
        "min_confidence": 0.92
    },
    ExceptionProfile.FUNDS_TRAPPED_AT_CORRESPONDENT: {
        "domain": ExceptionDomain.SETTLEMENT_RETURNS,
        "title": "Funds Trapped at Intermediary Correspondent",
        "description": "Initiates SWIFT camt.027 non-receipt claims for stalled forward dispatch at intermediary.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["CAMT027_CLAIM", "INTERMEDIARY_CORRESPONDENCE"],
        "min_confidence": 0.90
    },
    ExceptionProfile.UNMATCHED_CREDIT: {
        "domain": ExceptionDomain.SETTLEMENT_RETURNS,
        "title": "Unmatched Inbound Credit Instruction",
        "description": "Investigates inbound pacs.008 credit transfer without matching internal customer account.",
        "default_queue": "Investigation",
        "mandatory_evidence": ["CUSTOMER_NAME_VARIATION", "SUSPENSE_CREDIT_ENTRY"],
        "min_confidence": 0.88
    },
    ExceptionProfile.GENERAL_EXCEPTION: {
        "domain": ExceptionDomain.PROCESSING,
        "title": "General Payment Exception",
        "description": "Generic unclassified exception profile for manual triage.",
        "default_queue": "Repair",
        "mandatory_evidence": ["RAW_PAYLOAD"],
        "min_confidence": 0.85
    }
}

def get_profile_spec(profile: ExceptionProfile) -> Dict[str, Any]:
    return PROFILE_SPECS.get(profile, PROFILE_SPECS[ExceptionProfile.INVALID_IBAN])
