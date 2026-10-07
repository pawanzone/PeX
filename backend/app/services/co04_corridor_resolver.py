"""Governed Corridor Resolver, Regulatory Systems of Record (SoR) Models & Instruction Engine for CO-04.

CO-04: RESTRICTED CORRIDOR
Phase: Phase 2D (Slice 8)
Domain: Domain 3 (Compliance & Regulatory Exceptions)

Governing Standards & Authority Hierarchy:
- Tier 2 (External Authoritative): Statutory / Multilateral Sanctions Authorities (OFAC Comprehensive Embargoes, EU/UN Sanctions, UK OFSI), ISO 3166-1 Country Code Standard.
- Tier 1 (Bank Authoritative): National Central Bank / Scheme Clearing Rules (Fedwire, TARGET2, CHAPS), Bank Operational Corridor Policy.
- Tier 3 (PeX Derived): Deterministic Geographic Corridor Normalizer, ISO 3166 Syntax Validator.
- Tier 4 (Historical Precedent): Past corridor transactions (Strictly NON-AUTHORITATIVE).

Core Architectural Invariants:
1. Separation of Concerns & Compliance Boundary:
   COUNTRY RECOGNITION != CORRIDOR PERMISSIBILITY != COMPLIANCE CLEARANCE != STATUTORY LEGAL AUTHORIZATION != FUNDS MOVEMENT.
   - PeX is NOT the legal authority, NOT the statutory regulator, and NOT the bank's MLRO.
   - PeX normalizes geography, identifies corridor, evaluates configured rules, identifies restrictions, and prepares handoff.
   - Bank Compliance / Regulatory functions own compliance liability. Bank owns final execution.
2. Canonical 8-Predicate STP Formula:
   STP_ELIGIBLE = E_suff & R_det & R_uniq & V_det & V_auth & P_bank & C_comp & X_pre
   - Permitted corridor + policy authorized -> STP Eligible (BANK_HANDOFF_READY, execution_owner = "BANK").
   - Embargoed corridor / prohibited -> C_comp = False, V_auth = False -> COMPLIANCE_SUSPENSE / AUTO_BLOCK_REJECT (STP Blocked).
   - Licensed / Exemption corridor -> Routes to Compliance Desk for Maker-Checker dual authorization (maker_id != checker_id).
3. Statutory Override Invariant:
   Higher-tier statutory embargoes strictly override lower-tier bank permissions.
4. Lossless & Invariant Geographic Resolution:
   - Corridor = <Origin Country, Transit Jurisdictions, Destination Country, Currency, Rail>.
   - Country codes must be valid ISO 3166-1 alpha-2.
   - BIC country component must match declared postal address country.
5. Safety & Fail-Closed Guardrails:
   - Stale statutory matrix or bank policy (> TTL) fails closed (E_suff = False / V_auth = False).
   - Missing bank policy defaults to BANK_CONFIG_REQUIRED (P_bank = False).
   - Inbound free-text (<AddtlInf>, <Ustrd>) is sanitized against prompt injection directives.
6. Execution Boundary:
   - PeX never releases or settles wires; outputs CanonicalOutboundEnvelope with execution_owner = "BANK".
"""
import re
import uuid
import hashlib
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

# Standard ISO 3166-1 Alpha-2 Valid Countries (Authoritative External Standard)
VALID_ISO_3166_COUNTRIES: Set[str] = {
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ",
    "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS",
    "BT", "BV", "BW", "BY", "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
    "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE",
    "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK", "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF",
    "GG", "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM",
    "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT", "JE", "JM",
    "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC",
    "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK",
    "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA",
    "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG",
    "PH", "PK", "PL", "PM", "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW",
    "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "SS",
    "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO",
    "TR", "TT", "TV", "TW", "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
    "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW"
}


# ============================================================================
# Synthetic Regulatory & Policy Data Models (Tier 1 & Tier 2 Systems of Record)
# Explicitly labeled: DEMO / SYNTHETIC TEST FIXTURES
# ============================================================================

class RestrictionType(str, Enum):
    """Classification of statutory restriction."""
    COMPREHENSIVE_EMBARGO = "COMPREHENSIVE_EMBARGO"
    TARGETED_SANCTIONS = "TARGETED_SANCTIONS"
    CURRENCY_RESTRICTION = "CURRENCY_RESTRICTION"
    RAIL_RESTRICTION = "RAIL_RESTRICTION"
    GOVERNMENT_SANCTION = "GOVERNMENT_SANCTION"


class RestrictionStatus(str, Enum):
    """Lifecycle status of regulatory restriction."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"


class CorridorPolicyStatus(str, Enum):
    """Bank Operational Corridor Policy Status."""
    PERMITTED = "PERMITTED"
    RESTRICTED = "RESTRICTED"
    PROHIBITED = "PROHIBITED"
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"


class StatutoryRestrictionMatrixRecord(BaseModel):
    """Authoritative Statutory Embargo / Sanctions Record (Tier 2 External Authority Fixture).
    
    Classification: DEMO / SYNTHETIC TEST FIXTURE (Non-production)
    """
    jurisdiction: str # ISO 3166-1 alpha-2 country code (e.g. 'CU', 'KP', 'IR', 'SY')
    restriction_type: RestrictionType = RestrictionType.COMPREHENSIVE_EMBARGO
    issuing_authority: str = "OFAC_COMPREHENSIVE_EMBARGO" # e.g. OFAC, EU_SANCTIONS, UN_SECURITY_COUNCIL
    rule_id: str = Field(default_factory=lambda: f"REG-RULE-{uuid.uuid4().hex[:8].upper()}")
    effective_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) - timedelta(days=365))
    effective_to: Optional[datetime] = None
    status: RestrictionStatus = RestrictionStatus.ACTIVE
    affected_rails: List[str] = Field(default_factory=lambda: ["*"]) # '*' means all rails
    affected_currencies: List[str] = Field(default_factory=lambda: ["*"]) # '*' means all currencies
    exemption_permitted: bool = False
    source_version: str = "STATUTORY_EMBARGO_V2026.1"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BankCorridorPolicyRecord(BaseModel):
    """Authoritative Bank Operational Corridor Policy (Tier 1 Bank Authority Fixture).
    
    Classification: DEMO / SYNTHETIC TEST FIXTURE (Non-production)
    """
    corridor_id: str = "SEPA_EUR_DOMESTIC"
    origin_country: str = "DE"
    destination_country: str = "FR"
    permitted_rails: List[str] = Field(default_factory=lambda: ["SEPA", "SWIFT", "TARGET2"])
    permitted_currencies: List[str] = Field(default_factory=lambda: ["EUR", "USD", "GBP"])
    corridor_status: CorridorPolicyStatus = CorridorPolicyStatus.PERMITTED
    auto_stp_permitted: bool = True
    max_auto_amount: float = 100000.0
    requires_compliance_review: bool = False
    policy_version: str = "POL-2026-CORR-01"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CorridorRegulatoryExemptionRecord(BaseModel):
    """Authoritative Regulatory License / Exemption Documentation (Tier 1 Bank Authority Fixture).
    
    Classification: DEMO / SYNTHETIC TEST FIXTURE (Non-production)
    """
    license_id: str
    issuing_authority: str = "OFAC_GENERAL_LICENSE"
    effective_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) - timedelta(days=30))
    effective_to: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=335))
    covered_jurisdictions: List[str] = Field(default_factory=list)
    covered_transaction_types: List[str] = Field(default_factory=lambda: ["HUMANITARIAN_AID", "MEDICAL_SUPPLIES", "DIPLOMATIC"])
    is_valid: bool = True
    requires_human_verification: bool = True
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CorridorDispositionInstruction(BaseModel):
    """Prepared, immutable Corridor Compliance Disposition for Bank Execution.
    
    Classification: Governed Output Payload (execution_owner = 'BANK')
    """
    instruction_id: str = Field(default_factory=lambda: f"CDI-{uuid.uuid4().hex[:12].upper()}")
    uetr: str
    end_to_end_id: str
    origin_country: str
    destination_country: str
    transit_countries: List[str] = Field(default_factory=list)
    currency: str
    rail: str
    amount: float = 0.0
    corridor_status: str # PERMITTED, RESTRICTED, PROHIBITED
    compliance_disposition: str # COMPLIANCE_CLEAR, COMPLIANCE_REVIEW, COMPLIANCE_BLOCK
    matched_restrictions: List[str] = Field(default_factory=list)
    exemption_license_id: Optional[str] = None
    execution_owner: str = "BANK"
    preparation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    disposition_status: str = "PREPARED_FOR_BANK_DISPOSITION"


# ============================================================================
# Governed CO-04 Corridor Resolver Engine
# ============================================================================

class GovernedCO04CorridorResolver:
    """Deterministic Geographic Corridor Normalizer, Restriction Matcher & Disposition Engine for CO-04."""

    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous\s+instructions|embargo|sanctions|compliance)", re.IGNORECASE),
        re.compile(r"destination\s+is\s+[a-z]{2,}", re.IGNORECASE),
        re.compile(r"skip\s+(compliance|sanctions|screening|ofac)", re.IGNORECASE),
        re.compile(r"approve\s+(this\s+)?payment", re.IGNORECASE),
        re.compile(r"bypass\s+(maker[-_\s]*checker|approval|compliance)", re.IGNORECASE),
        re.compile(r"<script>|javascript:|eval\(", re.IGNORECASE),
        re.compile(r"auto[-_\s]*stp\s*=\s*true", re.IGNORECASE),
    ]

    def sanitize_narrative(self, narrative: Optional[str]) -> Tuple[str, bool]:
        """Sanitizes remittance narrative text and detects adversarial prompt injection attempts."""
        if not narrative:
            return "", False
        is_adversarial = False
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if pattern.search(narrative):
                is_adversarial = True
                break
        sanitized = re.sub(r"[<>]", "", narrative).strip()
        return sanitized, is_adversarial

    def extract_country_from_bic(self, bic: Optional[str]) -> Optional[str]:
        """Extracts 2-letter ISO 3166-1 country code from characters 5-6 of an 8 or 11-char BIC."""
        if not bic or len(bic.strip()) < 6:
            return None
        clean_bic = bic.strip().upper()
        country_candidate = clean_bic[4:6]
        if country_candidate in VALID_ISO_3166_COUNTRIES:
            return country_candidate
        return None

    def resolve_corridor(
        self,
        raw_payload: str,
        uetr: str,
        end_to_end_id: str,
        origin_country: Optional[str] = None,
        destination_country: Optional[str] = None,
        debtor_agent_bic: Optional[str] = None,
        creditor_agent_bic: Optional[str] = None,
        intermediary_countries: Optional[List[str]] = None,
        currency: str = "EUR",
        rail: str = "SEPA",
        amount: float = 1000.0,
        remittance_narrative: Optional[str] = None,
        statutory_matrix: Optional[List[StatutoryRestrictionMatrixRecord]] = None,
        bank_corridor_policy: Optional[BankCorridorPolicyRecord] = None,
        exemption_record: Optional[CorridorRegulatoryExemptionRecord] = None,
        allow_stale_evidence: bool = False,
        policy_freshness_seconds: int = 86400,
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, List[ResolutionCandidate], Optional[ResolutionCandidate], List[str], Optional[str], bool]:
        """Deterministically normalizes corridor geography, matches restrictions, and derives compliance disposition candidate.
        
        Returns:
            (status, uniqueness, candidates, primary_candidate, audit_trail, error_message, is_lossless)
        """
        trail: List[str] = [f"Initiating Governed CO-04 Corridor Resolution for UETR: {uetr}"]
        is_lossless = True

        # 0. Prompt Injection & Narrative Sanitization
        sanitized_narrative, is_injection_detected = self.sanitize_narrative(remittance_narrative)
        if is_injection_detected:
            trail.append("SECURITY ALERT: Adversarial prompt injection pattern detected in remittance text. Sanitized and quarantined.")

        # 1. Geographic Origin & Destination Normalization
        norm_origin = origin_country.strip().upper() if origin_country else None
        norm_destination = destination_country.strip().upper() if destination_country else None
        transit_jurisdictions = [c.strip().upper() for c in (intermediary_countries or []) if c]

        # Corroborate with BIC country components
        origin_bic_country = self.extract_country_from_bic(debtor_agent_bic)
        dest_bic_country = self.extract_country_from_bic(creditor_agent_bic)

        if not norm_origin and origin_bic_country:
            norm_origin = origin_bic_country
            trail.append(f"Derived origin country '{norm_origin}' from Debtor Agent BIC ({debtor_agent_bic}).")
        if not norm_destination and dest_bic_country:
            norm_destination = dest_bic_country
            trail.append(f"Derived destination country '{norm_destination}' from Creditor Agent BIC ({creditor_agent_bic}).")

        # Validation of ISO 3166-1 country code structure (V_det)
        if not norm_origin or not norm_destination:
            trail.append(f"FAILED: Missing origin ({norm_origin}) or destination ({norm_destination}) country.")
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_UNIQUE,
                [],
                None,
                trail,
                "Missing origin or destination country in payment payload.",
                False
            )

        if norm_origin not in VALID_ISO_3166_COUNTRIES:
            trail.append(f"FAILED (V_det): Origin country code '{norm_origin}' is not a valid ISO 3166-1 Alpha-2 code.")
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_UNIQUE,
                [],
                None,
                trail,
                f"Invalid ISO 3166-1 origin country code: {norm_origin}",
                False
            )

        if norm_destination not in VALID_ISO_3166_COUNTRIES:
            trail.append(f"FAILED (V_det): Destination country code '{norm_destination}' is not a valid ISO 3166-1 Alpha-2 code.")
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_UNIQUE,
                [],
                None,
                trail,
                f"Invalid ISO 3166-1 destination country code: {norm_destination}",
                False
            )

        # Check for BIC country / postal country conflict
        if origin_bic_country and norm_origin and origin_bic_country != norm_origin:
            trail.append(f"FAILED (R_uniq): Country conflict detected between Debtor BIC ({origin_bic_country}) and address ({norm_origin}).")
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_AMBIGUOUS,
                [],
                None,
                trail,
                f"Geographic conflict: Debtor BIC country {origin_bic_country} != address country {norm_origin}",
                False
            )

        if dest_bic_country and norm_destination and dest_bic_country != norm_destination:
            trail.append(f"FAILED (R_uniq): Country conflict detected between Creditor BIC ({dest_bic_country}) and address ({norm_destination}).")
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_AMBIGUOUS,
                [],
                None,
                trail,
                f"Geographic conflict: Creditor BIC country {dest_bic_country} != address country {norm_destination}",
                False
            )

        corridor_tag = f"{norm_origin}->{norm_destination} [{currency}/{rail}]"
        trail.append(f"Corridor Identified: {corridor_tag} with {len(transit_jurisdictions)} transit jurisdictions.")

        # 2. Freshness & Effective Dates Check on Statutory Matrix & Bank Policy
        now_utc = datetime.now(timezone.utc)
        all_restrictions = statutory_matrix or []
        active_statutory_restrictions: List[StatutoryRestrictionMatrixRecord] = []

        for rec in all_restrictions:
            # Check retrieval freshness
            if not allow_stale_evidence and rec.retrieved_at:
                age_sec = (now_utc - rec.retrieved_at).total_seconds()
                if age_sec > policy_freshness_seconds:
                    trail.append(f"FAILED (Freshness): Statutory restriction record '{rec.rule_id}' is stale ({int(age_sec)}s > {policy_freshness_seconds}s TTL).")
                    return (
                        ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                        ResolutionUniqueness.RESOLUTION_UNIQUE,
                        [],
                        None,
                        trail,
                        f"Statutory restriction evidence expired for rule: {rec.rule_id}",
                        False
                    )
            # Check effective window
            is_effective = rec.effective_from <= now_utc and (rec.effective_to is None or rec.effective_to >= now_utc)
            if rec.status == RestrictionStatus.ACTIVE and is_effective:
                active_statutory_restrictions.append(rec)

        # 3. Restriction Matching against All Corridor Jurisdictions
        matched_statutory_rules: List[str] = []
        is_statutory_blocked = False

        all_corridor_countries = [norm_origin, norm_destination] + transit_jurisdictions
        for country in all_corridor_countries:
            for rule in active_statutory_restrictions:
                if rule.jurisdiction == country:
                    # Check affected rail and currency
                    rail_match = "*" in rule.affected_rails or rail in rule.affected_rails
                    curr_match = "*" in rule.affected_currencies or currency in rule.affected_currencies
                    if rail_match and curr_match:
                        matched_statutory_rules.append(f"{rule.issuing_authority}:{rule.jurisdiction}:{rule.restriction_type.value}")
                        is_statutory_blocked = True

        if matched_statutory_rules:
            trail.append(f"Statutory Embargo Matches Detected: {', '.join(matched_statutory_rules)}")

        # 4. Bank Corridor Policy Authority Verification (V_auth / P_bank)
        if not bank_corridor_policy:
            trail.append("FAILED (V_auth): Missing Bank Corridor Policy record in evidence dossier.")
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_UNIQUE,
                [],
                None,
                trail,
                "Bank corridor policy missing or unconfigured (BANK_CONFIG_REQUIRED).",
                False
            )

        if not allow_stale_evidence and bank_corridor_policy.retrieved_at:
            age_sec = (now_utc - bank_corridor_policy.retrieved_at).total_seconds()
            if age_sec > policy_freshness_seconds:
                trail.append(f"FAILED (Freshness): Bank Corridor Policy is stale ({int(age_sec)}s > {policy_freshness_seconds}s TTL).")
                return (
                    ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                    ResolutionUniqueness.RESOLUTION_UNIQUE,
                    [],
                    None,
                    trail,
                    "Bank corridor policy evidence expired.",
                    False
                )

        # Check Bank Policy permissions
        is_bank_policy_permitted = (
            bank_corridor_policy.corridor_status == CorridorPolicyStatus.PERMITTED and
            (rail in bank_corridor_policy.permitted_rails or "*" in bank_corridor_policy.permitted_rails) and
            (currency in bank_corridor_policy.permitted_currencies or "*" in bank_corridor_policy.permitted_currencies)
        )

        if not is_bank_policy_permitted and not is_statutory_blocked:
            trail.append(f"Bank Policy Restriction: Corridor status is '{bank_corridor_policy.corridor_status}'. Rails: {bank_corridor_policy.permitted_rails}, Currencies: {bank_corridor_policy.permitted_currencies}.")

        # 5. Regulatory Exemption / License Corroboration
        has_valid_exemption = False
        exemption_id = None
        if exemption_record and exemption_record.is_valid:
            ex_effective = exemption_record.effective_from <= now_utc <= exemption_record.effective_to
            if ex_effective and (norm_destination in exemption_record.covered_jurisdictions or "*" in exemption_record.covered_jurisdictions):
                has_valid_exemption = True
                exemption_id = exemption_record.license_id
                trail.append(f"Valid Regulatory Exemption License '{exemption_id}' corroborated for corridor.")
            else:
                trail.append(f"Exemption license '{exemption_record.license_id}' present but expired or does not cover jurisdiction '{norm_destination}'.")

        # 6. Synthesize Compliance Disposition & Candidate Derivation
        # Statutory Embargo strictly overrides Bank Policy (Authority Hierarchy Invariant)
        if is_statutory_blocked:
            if has_valid_exemption:
                disposition = "COMPLIANCE_REVIEW"
                corr_status = "RESTRICTED"
                diff_summary = f"Restricted corridor {corridor_tag} with active exemption license {exemption_id} (Requires Maker-Checker Dual Authorization)"
            else:
                disposition = "COMPLIANCE_BLOCK"
                corr_status = "PROHIBITED"
                diff_summary = f"Statutory embargo violation on corridor {corridor_tag}: {', '.join(matched_statutory_rules)} (Auto-Block / Reject)"
        elif not is_bank_policy_permitted:
            disposition = "COMPLIANCE_REVIEW"
            corr_status = "RESTRICTED"
            diff_summary = f"Bank policy restriction on corridor {corridor_tag} (Status: {bank_corridor_policy.corridor_status.value})"
        else:
            disposition = "COMPLIANCE_CLEAR"
            corr_status = "PERMITTED"
            diff_summary = f"Permitted corridor {corridor_tag} cleared against statutory matrix and bank policy"

        # 7. Formulate Immutable Instruction
        instruction = CorridorDispositionInstruction(
            uetr=uetr,
            end_to_end_id=end_to_end_id,
            origin_country=norm_origin,
            destination_country=norm_destination,
            transit_countries=transit_jurisdictions,
            currency=currency,
            rail=rail,
            amount=amount,
            corridor_status=corr_status,
            compliance_disposition=disposition,
            matched_restrictions=matched_statutory_rules,
            exemption_license_id=exemption_id,
            execution_owner="BANK",
            preparation_timestamp=datetime.now(timezone.utc),
            disposition_status="PREPARED_FOR_BANK_DISPOSITION"
        )

        instruction_diff = instruction.model_dump()
        instruction_diff["sanitized_narrative"] = sanitized_narrative

        candidate = ResolutionCandidate(
            candidate_id=f"CAND-CO04-{instruction.instruction_id}",
            repaired_payload=raw_payload,
            diff_summary=diff_summary,
            derivation_method="GOVERNED_CO04_CORRIDOR_RESOLUTION_RULE",
            is_lossless=True,
            repaired_structured=instruction_diff,
            fields_reordered=["CORRIDOR_DISPOSITION_INSTRUCTION", "ORIGIN_COUNTRY", "DESTINATION_COUNTRY", "COMPLIANCE_DISPOSITION"]
        )

        trail.append(f"Disposition Prepared: {disposition} (Status: {corr_status}) for {corridor_tag}.")

        return (
            ResolutionStatus.RESOLUTION_DETERMINED,
            ResolutionUniqueness.RESOLUTION_UNIQUE,
            [candidate],
            candidate,
            trail,
            None,
            is_lossless
        )


# Global singleton CO-04 resolver
co04_resolver = GovernedCO04CorridorResolver()
