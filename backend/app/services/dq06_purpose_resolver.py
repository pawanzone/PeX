"""Governed Purpose Code Resolver, Semantic Interpretation & Bank Policy Engine for DQ-06.

DQ-06: INVALID / MISSING PURPOSE CODE
Phase: Phase 2C (Slice 6)

Governing Standards & Taxonomy:
- ISO 20022: External Purpose Codes (ExternalPurpose1Code) - 4-character uppercase alphanumeric code.
- ISO 20022: pacs.008 Customer Credit Transfer (<CdtTrfTxInf><Purp><Cd>XXXX</Cd></Purp>).
- ISO 20022: Remittance Information (<RmtInf><Ustrd> narrative / <Strd> invoice).
- BIAN Domain: Data Quality Exceptions (Group 2: Conditionally STP-capable).

Core Architectural Invariants:
1. Separation of Concerns:
   SEMANTIC INTERPRETATION != AUTHORITATIVE ECONOMIC PURPOSE != CODE-SET VALIDITY != BANK AUTHORIZATION != STP ELIGIBILITY.
   - Semantic interpretation produces hypothesis candidates only (Tier 3).
   - Code-set membership proves structural validity only (V_det / Tier 2).
   - Bank Purpose Policy and Corridor Rules govern business authorization (V_auth / Tier 1).
   - AI confidence is informational and CANNOT satisfy authority gates.
2. Keyword Match is Never Authority:
   - Matching "supplier invoice" generates hypothesis candidate GDSV, but does NOT authorize autonomous STP.
   - Bank purpose policy or corridor mandates must explicitly corroborate the candidate.
3. Bounded Deterministic Derivation:
   - Candidate generation scans structured remittance and unstructured payment narrative against governed rules.
   - Ambiguous signals with multiple plausible candidates fail uniqueness (R_uniq = False -> DISAMBIGUATION_DESK).
   - Unrecognized / vague narrative without distinct semantic category fails derivation (R_det = False -> SUSPENSE).
4. Fail-Closed Handling:
   - Prohibited codes, missing bank policy, corridor restrictions, stale evidence (> TTL), or contradictory data
     immediately fail closed to HITL / Operations Suspense / Investigation Cockpit.
"""
import re
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field

from app.schemas.resolution_contract import (
    ResolutionCandidate,
    ResolutionResult,
    ResolutionStatus,
    ResolutionUniqueness,
)

# Register default ISO 20022 namespace to serialize with clean default xmlns
ET.register_namespace("", "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08")


# ============================================================================
# ISO 20022 Official External Purpose Code Catalog (Tier 2 External Authority)
# ============================================================================

ISO_20022_EXTERNAL_PURPOSE_CODES: Dict[str, Dict[str, str]] = {
    # Commercial & Trade
    "GDSV": {"name": "PurchaseSaleOfGoods", "category": "COMMERCIAL", "description": "Payment for purchase and sale of goods"},
    "SCVE": {"name": "CommercialServices", "category": "COMMERCIAL", "description": "Payment for commercial services rendered"},
    "SUPP": {"name": "SupplierPayment", "category": "COMMERCIAL", "description": "Payment to a supplier"},
    "COMM": {"name": "CommercialPayment", "category": "COMMERCIAL", "description": "General commercial payment"},
    "IVPT": {"name": "InvoicePayment", "category": "COMMERCIAL", "description": "Payment of an invoice"},
    "TRAD": {"name": "TradeServices", "category": "COMMERCIAL", "description": "Payment for trade services"},
    "COST": {"name": "Costs", "category": "COMMERCIAL", "description": "Payment of costs"},
    "FEES": {"name": "PaymentOfFees", "category": "COMMERCIAL", "description": "Payment of fees"},
    "OFEE": {"name": "OpeningFee", "category": "COMMERCIAL", "description": "Payment of opening fee"},
    "ROYA": {"name": "Royalties", "category": "COMMERCIAL", "description": "Payment of royalties"},
    "SUBS": {"name": "Subscription", "category": "COMMERCIAL", "description": "Payment of subscription fees"},
    
    # Salary, Pension & Personnel
    "SALA": {"name": "SalaryPayment", "category": "PERSONNEL", "description": "Payment of salary to employees"},
    "PAYR": {"name": "Payroll", "category": "PERSONNEL", "description": "Payment of payroll"},
    "BONU": {"name": "BonusPayment", "category": "PERSONNEL", "description": "Payment of bonus to employees"},
    "PENS": {"name": "PensionPayment", "category": "PERSONNEL", "description": "Payment of pension or retirement funds"},
    "PENO": {"name": "PensionFundContribution", "category": "PERSONNEL", "description": "Contribution to a pension fund"},
    "SSBE": {"name": "SocialSecurityBenefit", "category": "GOVERNMENT", "description": "Social security benefit payment"},
    
    # Tax & Government
    "TAXS": {"name": "TaxPayment", "category": "TAX", "description": "Payment of taxes to authorities"},
    "ESTX": {"name": "EstateTax", "category": "TAX", "description": "Payment of estate tax"},
    "NITX": {"name": "NetIncomeTax", "category": "TAX", "description": "Payment of net income tax"},
    "WHLD": {"name": "WithholdingTax", "category": "TAX", "description": "Payment of withholding tax"},
    "GOVT": {"name": "GovernmentPayment", "category": "GOVERNMENT", "description": "Payment from or to a government entity"},
    "CORT": {"name": "CourtCosts", "category": "LEGAL", "description": "Payment of court costs or settlements"},
    
    # Financial, Investment & Treasury
    "DIVI": {"name": "Dividend", "category": "INVESTMENT", "description": "Payment of dividends to shareholders"},
    "INTE": {"name": "Interest", "category": "FINANCIAL", "description": "Payment of interest on debt or deposit"},
    "INTC": {"name": "IntraCompanyPayment", "category": "TREASURY", "description": "Payment between entities of the same corporate group"},
    "TREA": {"name": "TreasuryPayment", "category": "TREASURY", "description": "Payment related to treasury operations"},
    "CASH": {"name": "CashManagementTransfer", "category": "TREASURY", "description": "Payment for cash management operations"},
    "HEDG": {"name": "Hedging", "category": "TREASURY", "description": "Payment related to hedging operations"},
    "LOAN": {"name": "Loan", "category": "FINANCIAL", "description": "Payment related to loan disbursement or principal repayment"},
    "SAVG": {"name": "Savings", "category": "FINANCIAL", "description": "Payment to savings account"},
    "SECU": {"name": "Securities", "category": "INVESTMENT", "description": "Payment for securities trading"},
    "TRFD": {"name": "TrustFund", "category": "FINANCIAL", "description": "Payment related to trust funds"},
    
    # Real Estate & Utilities
    "RENT": {"name": "Rent", "category": "REAL_ESTATE", "description": "Payment for rent or lease of property"},
    "AREN": {"name": "AccountsReceivablesNeutral", "category": "REAL_ESTATE", "description": "Payment related to property management receivables"},
    "UBIL": {"name": "UtilityBill", "category": "UTILITIES", "description": "Payment of utility bills"},
    "WTER": {"name": "WaterBill", "category": "UTILITIES", "description": "Payment for water supply"},
    "TELI": {"name": "TelephoneBill", "category": "UTILITIES", "description": "Payment for telecommunications services"},
    
    # Insurance
    "INSU": {"name": "InsurancePremium", "category": "INSURANCE", "description": "Payment of insurance premium"},
    "INPC": {"name": "InsurancePremiumCar", "category": "INSURANCE", "description": "Payment of car insurance premium"},
    "LIFI": {"name": "LifeInsurance", "category": "INSURANCE", "description": "Payment of life insurance premium"},
    "HLRP": {"name": "HousingLoanRepayment", "category": "FINANCIAL", "description": "Payment of housing loan or mortgage"},
    
    # Social & Charity
    "CHAR": {"name": "Charity", "category": "CHARITY", "description": "Donation to a charitable organization"},
    "GIFT": {"name": "Gift", "category": "CHARITY", "description": "Gift payment"},
    "EDUC": {"name": "Education", "category": "EDUCATION", "description": "Payment of tuition or education fees"},
    "STDY": {"name": "Study", "category": "EDUCATION", "description": "Payment for studies and training"},
    
    # Healthcare
    "MDCP": {"name": "MedicalCarePayment", "category": "HEALTHCARE", "description": "Payment for medical services"},
    "HCRF": {"name": "HealthcareRefund", "category": "HEALTHCARE", "description": "Refund of healthcare payment"},
    
    # Other / Miscellaneous
    "OTHR": {"name": "Other", "category": "OTHER", "description": "Other payment purpose"},
    "REFU": {"name": "Refund", "category": "OTHER", "description": "Refund of payment"},
    "COLL": {"name": "CollectionPayment", "category": "COMMERCIAL", "description": "Collection payment"},
}


class PurposeResolutionOutcome(str, Enum):
    """Canonical resolution outcomes for DQ-06."""
    VALID_EXISTING_PURPOSE = "VALID_EXISTING_PURPOSE"
    SINGLE_CANDIDATE_REPAIRED = "SINGLE_CANDIDATE_REPAIRED"
    MULTIPLE_CANDIDATES_AMBIGUOUS = "MULTIPLE_CANDIDATES_AMBIGUOUS"
    NO_CANDIDATE_DERIVED = "NO_CANDIDATE_DERIVED"
    BANK_POLICY_UNAUTHORIZED = "BANK_POLICY_UNAUTHORIZED"
    CORRIDOR_PROHIBITED = "CORRIDOR_PROHIBITED"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    STALE_AUTHORITY = "STALE_AUTHORITY"
    CONTRADICTORY_AUTHORITY = "CONTRADICTORY_AUTHORITY"
    SEARCH_BOUND_EXCEEDED = "SEARCH_BOUND_EXCEEDED"
    HITL_REQUIRED = "HITL_REQUIRED"


class SemanticSignal(BaseModel):
    """A single semantic signal extracted from narrative or remittance text."""
    signal_term: str
    matched_keyword: str
    associated_purpose_code: str
    confidence_weight: float = 1.0
    category: str


class PurposeCandidateHypothesis(BaseModel):
    """A structured candidate purpose code hypothesis derived from semantic signals."""
    code: str
    code_name: str
    category: str
    derivation_rule: str
    matched_signals: List[str] = Field(default_factory=list)
    ranking_score: float = 1.0                  # Informational ranking score (NOT an STP predicate)
    is_code_set_valid: bool = True
    provenance: str = "PEX_SEMANTIC_INTERPRETER"


# ============================================================================
# Bank Purpose Policy & Corridor Models (Tier 1 Bank Authority)
# ============================================================================

class BankPurposePolicyEntry(BaseModel):
    """Authoritative Bank Purpose Code Policy for a counterparty, debtor, or product."""
    entity_id: str                              # Counterparty ID, Account Number, or Customer ID
    entity_name: str
    authorized_purpose_codes: List[str] = Field(default_factory=list)
    prohibited_purpose_codes: List[str] = Field(default_factory=list)
    default_purpose_code: Optional[str] = None
    is_authorized: bool = True
    provider: str = "BANK_PURPOSE_POLICY_STORE (DEMO/SYNTHETIC)"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    effective_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=1))
    freshness_seconds: int = 86400              # DEMO_ONLY_DEFAULT: 24h

    @property
    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at or (now - self.retrieved_at).total_seconds() > self.freshness_seconds


class BankCorridorPurposePolicy(BaseModel):
    """Authoritative Bank Corridor & Currency Purpose Code Policy."""
    corridor_id: str                            # e.g. "EUR-SEPA", "USD-FEDWIRE", "GBP-CHAPS"
    currency: str = "EUR"
    is_purpose_mandatory: bool = False
    allowed_purpose_codes: List[str] = Field(default_factory=list)
    prohibited_purpose_codes: List[str] = Field(default_factory=list)
    is_corridor_active: bool = True
    provider: str = "BANK_CORRIDOR_POLICY_STORE (DEMO/SYNTHETIC)"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=1))
    freshness_seconds: int = 86400              # DEMO_ONLY_DEFAULT: 24h

    @property
    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at or (now - self.retrieved_at).total_seconds() > self.freshness_seconds


# ============================================================================
# In-Memory Adapters (Explicitly DEMO / SYNTHETIC TEST FIXTURES)
# ============================================================================

class BankPurposePolicyAdapter:
    """Adapter abstracting Bank Purpose Policy queries. (DEMO / SYNTHETIC TEST FIXTURE)"""

    def __init__(self):
        self._policy_store: Dict[str, BankPurposePolicyEntry] = {}
        self._seed_demo_policies()

    def _seed_demo_policies(self):
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=1)
        
        # Seed 1: Bavarian Industrial AG (Supplier / Commercial Goods)
        self.register(BankPurposePolicyEntry(
            entity_id="CP-BAVARIAN-01",
            entity_name="Bavarian Industrial AG",
            authorized_purpose_codes=["GDSV", "SUPP", "IVPT", "COMM"],
            prohibited_purpose_codes=["SALA", "PENS", "CHAR"],
            default_purpose_code="GDSV",
            is_authorized=True,
            retrieved_at=now,
            expires_at=exp
        ))
        # Seed 2: Siemens Energy Global (Commercial Services & Goods)
        self.register(BankPurposePolicyEntry(
            entity_id="CP-SIEMENS-01",
            entity_name="Siemens Energy Global GmbH",
            authorized_purpose_codes=["GDSV", "SCVE", "IVPT", "SUPP"],
            prohibited_purpose_codes=["GAMB"],
            default_purpose_code="GDSV",
            is_authorized=True,
            retrieved_at=now,
            expires_at=exp
        ))
        # Seed 3: Global Payroll Services Ltd (Salary & Payroll)
        self.register(BankPurposePolicyEntry(
            entity_id="CP-PAYROLL-01",
            entity_name="Global Payroll Services Ltd",
            authorized_purpose_codes=["SALA", "PAYR", "BONU", "SSBE"],
            prohibited_purpose_codes=["GDSV", "COMM"],
            default_purpose_code="SALA",
            is_authorized=True,
            retrieved_at=now,
            expires_at=exp
        ))
        # Seed 4: Federal Tax Administration (Tax Payments)
        self.register(BankPurposePolicyEntry(
            entity_id="CP-TAX-01",
            entity_name="Federal Tax Administration",
            authorized_purpose_codes=["TAXS", "ESTX", "NITX", "WHLD", "GOVT"],
            prohibited_purpose_codes=["SALA", "GDSV"],
            default_purpose_code="TAXS",
            is_authorized=True,
            retrieved_at=now,
            expires_at=exp
        ))
        # Seed 5: Sovereign Investment Corp (Dividends & Investments)
        self.register(BankPurposePolicyEntry(
            entity_id="CP-INVEST-01",
            entity_name="Sovereign Investment Corp",
            authorized_purpose_codes=["DIVI", "INTE", "SECU", "TREA"],
            prohibited_purpose_codes=["SALA"],
            default_purpose_code="DIVI",
            is_authorized=True,
            retrieved_at=now,
            expires_at=exp
        ))

    def register(self, entry: BankPurposePolicyEntry):
        self._policy_store[entry.entity_id.upper()] = entry
        self._policy_store[entry.entity_name.upper()] = entry

    def lookup(self, identifier: str) -> Optional[BankPurposePolicyEntry]:
        if not identifier:
            return None
        return self._policy_store.get(identifier.strip().upper())


class BankCorridorPolicyAdapter:
    """Adapter abstracting Corridor and Currency Purpose rules. (DEMO / SYNTHETIC TEST FIXTURE)"""

    def __init__(self):
        self._corridor_store: Dict[str, BankCorridorPurposePolicy] = {}
        self._seed_demo_corridors()

    def _seed_demo_corridors(self):
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=1)

        # SEPA EUR Domestic & Cross-Border
        self.register(BankCorridorPurposePolicy(
            corridor_id="EUR-SEPA",
            currency="EUR",
            is_purpose_mandatory=False,
            allowed_purpose_codes=["GDSV", "SCVE", "SUPP", "COMM", "IVPT", "SALA", "PAYR", "BONU", "PENS", "TAXS", "DIVI", "RENT", "INSU", "CHAR", "TREA", "UBIL", "LOAN", "EDUC", "MDCP"],
            prohibited_purpose_codes=["GAMB"],
            is_corridor_active=True,
            retrieved_at=now,
            expires_at=exp
        ))
        # US Fedwire USD
        self.register(BankCorridorPurposePolicy(
            corridor_id="USD-FEDWIRE",
            currency="USD",
            is_purpose_mandatory=False,
            allowed_purpose_codes=["GDSV", "SCVE", "SUPP", "COMM", "IVPT", "SALA", "PAYR", "TAXS", "DIVI", "TREA", "INTE", "LOAN"],
            prohibited_purpose_codes=[],
            is_corridor_active=True,
            retrieved_at=now,
            expires_at=exp
        ))
        # UAE FTS AED Corridor (Mandatory purpose code corridor)
        self.register(BankCorridorPurposePolicy(
            corridor_id="AED-UAEFTS",
            currency="AED",
            is_purpose_mandatory=True,
            allowed_purpose_codes=["SALA", "GDSV", "SCVE", "IVPT", "RENT", "TAXS", "DIVI", "TREA"],
            prohibited_purpose_codes=["CHAR"],  # Charity requires special permit
            is_corridor_active=True,
            retrieved_at=now,
            expires_at=exp
        ))
        # Restricted Corridor Example (Prohibits commercial goods)
        self.register(BankCorridorPurposePolicy(
            corridor_id="RESTRICTED-CORRIDOR-01",
            currency="EUR",
            is_purpose_mandatory=True,
            allowed_purpose_codes=["EDUC", "MDCP", "CHAR"],
            prohibited_purpose_codes=["GDSV", "SUPP", "COMM", "TREA", "SECU"],
            is_corridor_active=True,
            retrieved_at=now,
            expires_at=exp
        ))

    def register(self, entry: BankCorridorPurposePolicy):
        self._corridor_store[entry.corridor_id.upper()] = entry
        key_with_curr = f"{entry.corridor_id.upper()}:{entry.currency.upper()}"
        self._corridor_store[key_with_curr] = entry

    def lookup(self, corridor_id: str, currency: Optional[str] = None) -> Optional[BankCorridorPurposePolicy]:
        if not corridor_id:
            return None
        if currency:
            combined = f"{corridor_id.strip().upper()}:{currency.strip().upper()}"
            if combined in self._corridor_store:
                return self._corridor_store[combined]
        return self._corridor_store.get(corridor_id.strip().upper())


# ============================================================================
# Governed DQ-06 Purpose Code Resolver Engine
# ============================================================================

class GovernedDQ06PurposeResolver:
    """Governed semantic interpreter, candidate solver, and code-set validator for DQ-06."""

    SEMANTIC_KEYWORD_RULES: List[Dict[str, Any]] = [
        {
            "code": "SALA",
            "category": "PERSONNEL",
            "rule": "SALARY_PAYROLL_RULE",
            "keywords": ["salary", "salaries", "monthly salary", "wages", "remuneration", "gehalt", "salaire", "stipend", "monatsgehalt", "lohn", "paycheck"]
        },
        {
            "code": "PAYR",
            "category": "PERSONNEL",
            "rule": "PAYROLL_RULE",
            "keywords": ["payroll", "payroll wages", "bi-weekly payroll", "payroll payment", "paie"]
        },
        {
            "code": "BONU",
            "category": "PERSONNEL",
            "rule": "BONUS_INCENTIVE_RULE",
            "keywords": ["annual bonus", "performance bonus", "incentive payment", "gratifikation", "tantieme", "bonus payment", "bonus"]
        },
        {
            "code": "PENS",
            "category": "PERSONNEL",
            "rule": "PENSION_RETIREMENT_RULE",
            "keywords": ["pension", "superannuation", "retirement annuity", "altersrente", "ruhegehalt", "retraite", "pension payment"]
        },
        {
            "code": "TAXS",
            "category": "TAX",
            "rule": "TAX_GOVERNMENT_RULE",
            "keywords": ["tax payment", "tax", "taxes", "vat payment", "vat", "customs duty", "sales tax", "corporate tax", "income tax", "corporate income tax", "steuern", "finanzamt", "impot", "gst payment", "gst", "tva"]
        },
        {
            "code": "WHLD",
            "category": "TAX",
            "rule": "WITHHOLDING_TAX_RULE",
            "keywords": ["withholding tax", "quellensteuer", "retencao na fonte", "prelevement a la source"]
        },
        {
            "code": "DIVI",
            "category": "INVESTMENT",
            "rule": "DIVIDEND_DISTRIBUTION_RULE",
            "keywords": ["dividend", "dividends", "dividende", "interim dividend", "shareholder distribution", "gewinnausschuettung", "stock dividend"]
        },
        {
            "code": "GDSV",
            "category": "COMMERCIAL",
            "rule": "GOODS_PURCHASE_RULE",
            "keywords": ["purchase of goods", "goods", "goods delivery", "delivery of goods", "delivery of office equipment", "office equipment", "delivery", "equipment", "equipment components", "machinery", "components", "material purchase", "materials", "hardware", "hardware delivery", "warenlieferung", "warenkauf", "merchandise", "lieferung"]
        },
        {
            "code": "SCVE",
            "category": "COMMERCIAL",
            "rule": "COMMERCIAL_SERVICES_RULE",
            "keywords": ["consulting services", "consulting", "professional services", "advisory services", "advisory", "legal services", "marketing services", "marketing", "it services", "dienstleistungen", "dienstleistung", "beratung", "prestations de service"]
        },
        {
            "code": "SUPP",
            "category": "COMMERCIAL",
            "rule": "SUPPLIER_PAYMENT_RULE",
            "keywords": ["supplier payment", "supplier", "vendor payment", "vendor", "lieferant", "lieferantenrechnung", "fournisseur", "supply payment", "supply"]
        },
        {
            "code": "IVPT",
            "category": "COMMERCIAL",
            "rule": "INVOICE_PAYMENT_RULE",
            "keywords": ["invoice payment", "invoice", "inv", "rechnungszahlung", "rechnung", "paiement facture", "facture", "inv #", "inv-", "rechnung nr"]
        },
        {
            "code": "RENT",
            "category": "REAL_ESTATE",
            "rule": "PROPERTY_RENT_RULE",
            "keywords": ["office rent", "rent", "rental", "property lease", "lease", "leasing", "rental payment", "miete", "loyer", "bueromiete", "commercial lease"]
        },
        {
            "code": "INSU",
            "category": "INSURANCE",
            "rule": "INSURANCE_PREMIUM_RULE",
            "keywords": ["insurance premium", "insurance", "policy payment", "policy", "assurance", "versicherung", "versicherungsbeitrag", "health insurance"]
        },
        {
            "code": "LOAN",
            "category": "FINANCIAL",
            "rule": "LOAN_REPAYMENT_RULE",
            "keywords": ["loan repayment", "loan", "principal repayment", "darlehen", "kredit", "kreditrate", "pret bancaire", "pret", "loan installment", "mortgage", "hypothek"]
        },
        {
            "code": "CHAR",
            "category": "CHARITY",
            "rule": "CHARITABLE_DONATION_RULE",
            "keywords": ["charitable donation", "charity", "donation", "donations", "non-profit grant", "grant", "spende", "spenden", "don caritatif", "humanitarian relief"]
        },
        {
            "code": "INTE",
            "category": "FINANCIAL",
            "rule": "INTEREST_PAYMENT_RULE",
            "keywords": ["interest payment", "interest", "coupon payment", "coupon", "zinszahlung", "zinsen", "interets"]
        },
        {
            "code": "TREA",
            "category": "TREASURY",
            "rule": "TREASURY_TRANSFER_RULE",
            "keywords": ["treasury transfer", "treasury", "liquidity sweep", "sweep", "cash pool", "hedging settlement", "intercompany sweep", "intercompany", "konzernverrechnung"]
        },
        {
            "code": "UBIL",
            "category": "UTILITIES",
            "rule": "UTILITY_BILL_RULE",
            "keywords": ["utility bill", "utility", "electricity bill", "water bill", "stromrechnung", "telecom charge", "gas bill"]
        },
        {
            "code": "EDUC",
            "category": "EDUCATION",
            "rule": "EDUCATION_TUITION_RULE",
            "keywords": ["tuition fee", "tuition", "university fee", "school tuition", "education", "studiengebuehr", "studium", "frais de scolarite"]
        },
        {
            "code": "MDCP",
            "category": "HEALTHCARE",
            "rule": "MEDICAL_CARE_RULE",
            "keywords": ["medical bill", "medical", "hospital invoice", "hospital", "healthcare charge", "healthcare", "arztrechnung", "doctor", "clinic", "soins medicaux"]
        },
    ]

    def validate_code_set_membership(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validates if a purpose code conforms to ISO 20022 4-character syntax and official catalog."""
        if not code:
            return False, "Purpose code is empty."
        norm_code = code.strip().upper()
        if not re.match(r'^[A-Z0-9]{4}$', norm_code):
            return False, f"Purpose code '{norm_code}' does not conform to 4-character uppercase format (^[A-Z0-9]{{4}}$)."
        if norm_code not in ISO_20022_EXTERNAL_PURPOSE_CODES:
            return False, f"Purpose code '{norm_code}' is not a registered ISO 20022 External Purpose Code."
        return True, None

    def sanitize_untrusted_narrative(self, raw_narrative: str) -> str:
        """Sanitizes remittance text against prompt injection or control characters.
        
        Treats payment narrative strictly as untrusted literal text, stripping control bytes.
        """
        if not raw_narrative:
            return ""
        sanitized = "".join(ch for ch in raw_narrative if ord(ch) in (0x09, 0x0A, 0x0D) or (ord(ch) >= 0x20 and ord(ch) != 0x7F))
        return sanitized.strip()

    def extract_semantic_signals(self, narrative: str) -> List[SemanticSignal]:
        """Scans sanitized narrative text deterministically against governed keyword rules using non-overlapping longest match."""
        sanitized = self.sanitize_untrusted_narrative(narrative).lower()
        if not sanitized:
            return []

        # Ignore vague stop words when they appear alone without context
        stop_words = {"payment", "per", "agreement", "ref", "reference", "transfer", "settlement", "to", "for", "from"}
        tokens = set(re.findall(r'\b[a-z0-9]+\b', sanitized))
        if tokens.issubset(stop_words):
            return []

        # Flatten and sort all keywords by length descending for longest-match precedence
        all_kws = []
        for rule in self.SEMANTIC_KEYWORD_RULES:
            code = rule["code"]
            category = rule["category"]
            for kw in rule["keywords"]:
                all_kws.append((len(kw), kw, code, category))
        all_kws.sort(key=lambda x: x[0], reverse=True)

        matched_spans: List[Tuple[int, int]] = []
        signals: List[SemanticSignal] = []

        for _, kw, code, category in all_kws:
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            for m in re.finditer(pattern, sanitized):
                span = m.span()
                # Check for overlap with existing matched spans
                if any(s[0] <= span[0] < s[1] or s[0] < span[1] <= s[1] or (span[0] <= s[0] and span[1] >= s[1]) for s in matched_spans):
                    continue
                matched_spans.append(span)
                signals.append(SemanticSignal(
                    signal_term=kw,
                    matched_keyword=kw,
                    associated_purpose_code=code,
                    category=category,
                    confidence_weight=1.0
                ))

        return signals

    def derive_candidate_hypotheses(
        self,
        narrative: str,
        debtor_name: Optional[str] = None,
        creditor_name: Optional[str] = None,
        raw_payload: Optional[str] = None
    ) -> Tuple[List[PurposeCandidateHypothesis], bool]:
        """Derives structured candidate purpose hypotheses from narrative and payment metadata."""
        if len(narrative) > 10000:
            raise ValueError("SEARCH_BOUND_EXCEEDED: Payment narrative length exceeds 10,000 characters.")

        signals = self.extract_semantic_signals(narrative)

        if not signals:
            return [], False

        code_counts: Dict[str, List[SemanticSignal]] = {}
        for sig in signals:
            code_counts.setdefault(sig.associated_purpose_code, []).append(sig)

        candidates: List[PurposeCandidateHypothesis] = []
        for code, sig_list in code_counts.items():
            spec = ISO_20022_EXTERNAL_PURPOSE_CODES.get(code, {"name": code, "category": "UNKNOWN"})
            r_name = "GOVERNED_SEMANTIC_KEYWORD_RULE"
            for rule in self.SEMANTIC_KEYWORD_RULES:
                if rule["code"] == code:
                    r_name = rule["rule"]
                    break

            cand = PurposeCandidateHypothesis(
                code=code,
                code_name=spec["name"],
                category=spec["category"],
                derivation_rule=r_name,
                matched_signals=[s.matched_keyword for s in sig_list],
                ranking_score=float(len(sig_list)),
                is_code_set_valid=(code in ISO_20022_EXTERNAL_PURPOSE_CODES)
            )
            candidates.append(cand)

        # Sort candidates descending by ranking score
        candidates.sort(key=lambda c: c.ranking_score, reverse=True)

        is_ambiguous = False
        if len(candidates) > 1:
            top_score = candidates[0].ranking_score
            second_score = candidates[1].ranking_score
            if candidates[0].category != candidates[1].category and top_score == second_score:
                is_ambiguous = True
            elif len(candidates) >= 2 and top_score == second_score and candidates[0].code != candidates[1].code:
                is_ambiguous = True

        return candidates[:10], is_ambiguous

    def repair_xml_payload(self, raw_xml: str, target_purpose_code: str) -> Tuple[str, List[str], bool]:
        """Losslessly updates or inserts <Purp><Cd>XXXX</Cd></Purp> in pacs.008 XML in canonical tag sequence."""
        diff_log: List[str] = []
        is_lossless = True

        try:
            root = ET.fromstring(raw_xml)
        except ET.ParseError as pe:
            diff_log.append(f"XML parse error during payload repair: {str(pe)}")
            return raw_xml, diff_log, False

        cdt_tx = root.find(".//{urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08}CdtTrfTxInf")
        if cdt_tx is None:
            cdt_tx = root.find(".//CdtTrfTxInf")

        if cdt_tx is None:
            diff_log.append("Could not find <CdtTrfTxInf> in XML payload.")
            return raw_xml, diff_log, False

        purp_elem = cdt_tx.find("{urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08}Purp")
        if purp_elem is None:
            purp_elem = cdt_tx.find("Purp")

        if purp_elem is not None:
            cd_elem = purp_elem.find("{urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08}Cd")
            if cd_elem is None:
                cd_elem = purp_elem.find("Cd")
            if cd_elem is not None:
                old_val = cd_elem.text
                cd_elem.text = target_purpose_code
                diff_log.append(f"Replaced purpose code <Purp><Cd>{old_val}</Cd></Purp> -> <Purp><Cd>{target_purpose_code}</Cd></Purp>")
            else:
                for child in list(purp_elem):
                    purp_elem.remove(child)
                ns = "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08" if "}" in cdt_tx.tag else ""
                tag_name = f"{{{ns}}}Cd" if ns else "Cd"
                new_cd = ET.SubElement(purp_elem, tag_name)
                new_cd.text = target_purpose_code
                diff_log.append(f"Inserted <Purp><Cd>{target_purpose_code}</Cd></Purp> into existing <Purp> element.")
        else:
            ns = "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08" if "}" in cdt_tx.tag else ""
            purp_tag = f"{{{ns}}}Purp" if ns else "Purp"
            cd_tag = f"{{{ns}}}Cd" if ns else "Cd"

            new_purp = ET.Element(purp_tag)
            new_cd = ET.SubElement(new_purp, cd_tag)
            new_cd.text = target_purpose_code

            children = list(cdt_tx)
            insert_idx = len(children)
            for idx, child in enumerate(children):
                ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if ctag == "RmtInf":
                    insert_idx = idx
                    break
            cdt_tx.insert(insert_idx, new_purp)
            diff_log.append(f"Inserted new <Purp><Cd>{target_purpose_code}</Cd></Purp> at canonical position {insert_idx} in <CdtTrfTxInf>.")

        repaired_xml = ET.tostring(root, encoding="utf-8").decode("utf-8")
        return repaired_xml, diff_log, is_lossless

    def resolve(
        self,
        raw_payload: str,
        existing_purpose_code: Optional[str] = None,
        remittance_text: Optional[str] = None,
        debtor_name: Optional[str] = None,
        creditor_name: Optional[str] = None,
        corridor_id: Optional[str] = None,
        currency: Optional[str] = None,
        bank_purpose_policy: Optional[BankPurposePolicyEntry] = None,
        corridor_policy: Optional[BankCorridorPurposePolicy] = None,
        allow_stale_evidence: bool = False
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, List[ResolutionCandidate], Optional[ResolutionCandidate], List[str], Optional[str], bool]:
        """Executes governed resolution determination (R_det, R_uniq) for DQ-06."""
        diff_log: List[str] = []
        is_lossless = True

        diff_log.append(f"Initiating governed DQ-06 Purpose Code resolution. Existing code: '{existing_purpose_code}'")

        # 1. Check if existing code is already valid
        if existing_purpose_code:
            is_valid_iso, err = self.validate_code_set_membership(existing_purpose_code)
            if is_valid_iso:
                diff_log.append(f"Existing purpose code '{existing_purpose_code}' is registered in ISO 20022 External Purpose Code set.")
                cand = ResolutionCandidate(
                    candidate_id=f"DQ06-NOOP-{existing_purpose_code}",
                    repaired_payload=raw_payload,
                    diff_summary=f"Existing purpose code '{existing_purpose_code}' is structurally valid in ISO 20022 code set.",
                    derivation_method="EXISTING_VALID_PURPOSE_CODE_PASSTHROUGH",
                    is_lossless=True
                )
                return (
                    ResolutionStatus.RESOLUTION_DETERMINED,
                    ResolutionUniqueness.RESOLUTION_UNIQUE,
                    [cand],
                    cand,
                    diff_log,
                    None,
                    True
                )
            else:
                diff_log.append(f"Existing purpose code '{existing_purpose_code}' is INVALID: {err}")

        # 2. Extract Remittance narrative if not explicitly passed
        narrative = remittance_text or ""
        if not narrative and raw_payload:
            try:
                root = ET.fromstring(raw_payload)
                ustrd = root.find(".//{urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08}Ustrd")
                if ustrd is None:
                    ustrd = root.find(".//Ustrd")
                if ustrd is not None and ustrd.text:
                    narrative = ustrd.text
                    diff_log.append(f"Extracted remittance narrative from XML: '{narrative}'")
            except Exception:
                pass

        if not narrative:
            diff_log.append("No remittance narrative or unstructured payment text available for semantic interpretation.")
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_UNIQUE,
                [],
                None,
                diff_log,
                "Missing remittance narrative for purpose code derivation.",
                False
            )

        # 3. Derive Candidate Hypotheses from Semantic Interpretation
        try:
            hypotheses, is_ambiguous = self.derive_candidate_hypotheses(
                narrative=narrative,
                debtor_name=debtor_name,
                creditor_name=creditor_name,
                raw_payload=raw_payload
            )
        except ValueError as ve:
            diff_log.append(f"Resolution error: {str(ve)}")
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_UNIQUE,
                [],
                None,
                diff_log,
                str(ve),
                False
            )

        if not hypotheses:
            diff_log.append("Semantic interpreter found no matching purpose code signals in remittance narrative.")
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_UNIQUE,
                [],
                None,
                diff_log,
                "No candidate purpose code could be derived from remittance narrative.",
                False
            )

        diff_log.append(f"Semantic interpreter derived {len(hypotheses)} candidate purpose hypothesis(es): {[h.code for h in hypotheses]}")

        # 4. Generate ResolutionCandidate objects for each hypothesis
        candidates: List[ResolutionCandidate] = []
        for idx, hyp in enumerate(hypotheses):
            repaired_payload, rep_log, rep_lossless = self.repair_xml_payload(raw_payload, hyp.code)
            cand_id = f"DQ06-CAND-{hyp.code}-{idx+1}"
            cand = ResolutionCandidate(
                candidate_id=cand_id,
                repaired_payload=repaired_payload,
                diff_summary=f"Repaired purpose code to '{hyp.code}' ({hyp.code_name}) derived via {hyp.derivation_rule} from signals: {hyp.matched_signals}",
                derivation_method=f"GOVERNED_SEMANTIC_INTERPRETER:{hyp.derivation_rule}",
                is_lossless=rep_lossless,
                fields_reordered=["Purp/Cd"]
            )
            candidates.append(cand)

        # 5. Handle Ambiguity vs Uniqueness
        if is_ambiguous:
            disambiguated_cand = None
            if bank_purpose_policy and bank_purpose_policy.is_authorized and not (bank_purpose_policy.is_stale and not allow_stale_evidence):
                auth_codes = set(bank_purpose_policy.authorized_purpose_codes)
                matching_auth = [c for c in candidates if c.candidate_id.split("-")[2] in auth_codes]
                if len(matching_auth) == 1:
                    disambiguated_cand = matching_auth[0]
                    diff_log.append(f"Bank Purpose Policy successfully disambiguated multiple hypotheses to single authorized code: {disambiguated_cand.candidate_id.split('-')[2]}")
                elif len(matching_auth) > 1:
                    # If default purpose code matches one of the top candidates
                    if bank_purpose_policy.default_purpose_code and any(c.candidate_id.split("-")[2] == bank_purpose_policy.default_purpose_code for c in matching_auth):
                        for c in matching_auth:
                            if c.candidate_id.split("-")[2] == bank_purpose_policy.default_purpose_code:
                                disambiguated_cand = c
                                diff_log.append(f"Bank Purpose Policy default code '{bank_purpose_policy.default_purpose_code}' selected among authorized candidates.")
                                break

            if disambiguated_cand:
                return (
                    ResolutionStatus.RESOLUTION_DETERMINED,
                    ResolutionUniqueness.RESOLUTION_UNIQUE,
                    [disambiguated_cand],
                    disambiguated_cand,
                    diff_log,
                    None,
                    True
                )
            else:
                diff_log.append(f"Ambiguous purpose code candidates detected ({len(candidates)} candidates). Routing to DISAMBIGUATION_DESK.")
                return (
                    ResolutionStatus.RESOLUTION_DETERMINED,
                    ResolutionUniqueness.RESOLUTION_AMBIGUOUS,
                    candidates,
                    candidates[0],
                    diff_log,
                    "Multiple plausible purpose codes derived; human disambiguation required.",
                    True
                )

        primary = candidates[0]
        diff_log.append(f"Unique resolution candidate derived: {primary.candidate_id}")
        return (
            ResolutionStatus.RESOLUTION_DETERMINED,
            ResolutionUniqueness.RESOLUTION_UNIQUE,
            [primary],
            primary,
            diff_log,
            None,
            True
        )


# Global singleton resolver instance
dq06_resolver = GovernedDQ06PurposeResolver()
