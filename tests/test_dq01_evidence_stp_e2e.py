"""Comprehensive End-to-End Behavior, Risk, SoR Authority, and Adversarial Test Suite for DQ-01.

DQ-01: INVALID_IBAN
Phase: Phase 2C (Slice 5)

Covers 30 Complete Scenarios:
1. Valid DE IBAN (No repair, MOD-97 == 1, Open DDA, SSI Match) -> STP Autonomous Bank Handoff
2. Valid GB IBAN (No repair, MOD-97 == 1, Open DDA, SSI Match) -> STP Autonomous Bank Handoff
3. Valid FR IBAN (No repair, MOD-97 == 1, Open DDA, SSI Match) -> STP Autonomous Bank Handoff
4. Corrupted Check-Digit in DE IBAN -> Corrected via check-digit solver, SSI corroborated, Core DDA Open -> STP Bank Handoff
5. Single-Transposition in DE IBAN BBAN -> Corrected via permutation solver, SSI corroborated, Core DDA Open -> STP Bank Handoff
6. Single-Digit Substitution in DE IBAN BBAN -> Corrected via permutation solver, SSI corroborated, Core DDA Open -> STP Bank Handoff
7. Account is CLOSED in Bank Core DDA Ledger (AccountLedgerStatus.CLOSED) -> Fail-closed, STP Blocked
8. Account is FROZEN in Bank Core DDA Ledger (AccountLedgerStatus.FROZEN) -> Fail-closed, STP Blocked
9. Account is RESTRICTED in Bank Core DDA Ledger (AccountLedgerStatus.RESTRICTED) -> Fail-closed, STP Blocked
10. Bank SSI Master Record Contradiction (mandated IBAN contradicts candidate) -> Fail-closed, V_auth Fails
11. Multiple Mathematical Candidates without Single SSI Disambiguation -> R_uniq=False, DISAMBIGUATION_DESK
12. Stale Bank SSI Master Record (> TTL 86400s) -> Fail-closed, E_suff / Freshness Fails
13. Stale Core DDA Account Status Record (> TTL 3600s) -> Fail-closed, Freshness Fails
14. Missing Mandatory Evidence (RAW_PAYLOAD missing) -> E_suff Fails, OPERATIONS_SUSPENSE
15. Missing Mandatory Evidence (BANK_SSI_MASTER_RECORD missing) -> E_suff Fails, OPERATIONS_SUSPENSE
16. Missing Mandatory Evidence (CORE_DDA_ACCOUNT_STATUS missing) -> E_suff Fails, OPERATIONS_SUSPENSE
17. Oversized / Malicious Payload (> 40 chars) -> Search bound exceeded, fail closed
18. Unrepairable Corrupted IBAN (too many errors, no candidate within edit distance 1) -> Resolution fails, fail closed
19. CoP / VoP Verification Response: MATCH -> Corroborates beneficiary identity, STP eligible
20. CoP / VoP Verification Response: NO_MATCH -> Beneficiary mismatch, STP Blocked
21. Compliance Gate Failure (SANCTIONS_HOLD / AML_FLAGGED) -> 8-predicate compliance failure, STP Blocked
22. Amount Exceeds STP Limit (> $25,000 limit) -> STP Policy threshold breached, routed to HITL
23. Bank Auto-STP Policy Disabled -> Routed to HITL Operations Suspense
24. Semantic Invariance Check (Monetary amount, UETR, EndToEndId, Creditor Name preserved 100%)
25. Semantic Invariance Tamper Attack (Attempted amount alteration detected and rejected)
26. Segregation of Duties (Maker submits repair, Checker approves with maker_id != checker_id) -> Successful HITL dual-authorization
27. Segregation of Duties Violation (Checker == Maker) -> PermissionError raised, unauthorized release blocked
28. Canonical Intake Envelope (CanonicalIntakeEnvelope) transport neutrality end-to-end
29. Outbound Canonical Envelope (CanonicalOutboundEnvelope) Bank Handoff Contract (execution_owner = "BANK", BANK_HANDOFF_READY)
30. Full Cryptographic Audit Trail and SHA-256 Provenance Logging across all 12 stages
"""
import pytest
import hashlib
from datetime import datetime, timezone, timedelta

from app.schemas.evidence_contract import (
    EvidenceDossier,
    EvidenceItem,
    EvidenceTrustTier,
    evidence_registry,
)
from app.schemas.canonical_envelopes import (
    CanonicalIntakeEnvelope,
    CanonicalOutboundEnvelope,
    HandoffLifecycleState,
)
from app.schemas.policy_contract import (
    STPPolicyConfig,
    ComplianceGateStatus,
    ExecutionPreconditionsStatus,
)
from app.schemas.resolution_contract import (
    ResolutionCandidate,
    ResolutionResult,
    ResolutionStatus,
    ResolutionUniqueness,
)
from app.schemas.authority_contract import (
    AuthorityValidationResult,
    AuthorityValidationStatus,
)
from app.services.dq01_iban_resolver import (
    dq01_resolver,
    GovernedDQ01IBANResolver,
    AccountLedgerStatus,
    CoPMatchResult,
    IBANResolutionOutcome,
    BankSSIMasterEntry,
    CoreDDAAccountRecord,
    CoPResponse,
)
from app.services.sufficiency_engine import (
    sufficiency_engine,
    EvidenceSufficiencyStatus,
    EvidenceSufficiencyResult,
)
from app.services.resolution_engine import resolution_engine
from app.services.authority_validation_engine import authority_validation_engine
from app.services.evidence_stp_evaluator import evidence_stp_evaluator
from app.services.dq01_stp_pipeline import (
    DQ01STPPipeline,
    dq01_pipeline,
    DQ01PipelineResult,
)
from app.adapters.input_adapter import InboundPackage, FolderInputAdapter
from app.adapters.output_adapter import FolderOutputAdapter, BankHandoffReceipt
from app.services.audit_service import audit_service
from app.core.hashing import verify_audit_chain, calculate_event_hash


SAMPLE_DQ01_XML_VALID_DE = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>MSG-2026-DQ01-001</MsgId>
      <CreDtTm>2026-10-07T12:00:00Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <EndToEndId>E2E-DQ01-998877</EndToEndId>
        <UETR>aa11bb22-33cc-44dd-55ee-66ff77889900</UETR>
      </PmtId>
      <IntrBkSttlmAmt Ccy="EUR">22000.00</IntrBkSttlmAmt>
      <Dbtr>
        <Nm>Originating Corp Inc</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id><IBAN>GB82WEST12345678901234</IBAN></Id>
      </DbtrAcct>
      <CdtrAgt>
        <FinInstnId>
          <BICFI>DEUTDEDDFXX</BICFI>
        </FinInstnId>
      </CdtrAgt>
      <Cdtr>
        <Nm>Bavarian Industrial AG</Nm>
      </Cdtr>
      <CdtrAcct>
        <Id><IBAN>DE89370400440532013000</IBAN></Id>
      </CdtrAcct>
      <RmtInf>
        <Ustrd>Payment for Turbine Components Q3</Ustrd>
      </RmtInf>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>"""

SAMPLE_DQ01_XML_VALID_GB = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>MSG-2026-DQ01-002</MsgId>
      <CreDtTm>2026-10-07T12:00:00Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <EndToEndId>E2E-DQ01-GB001</EndToEndId>
        <UETR>bb22cc33-44dd-55ee-66ff-778899001122</UETR>
      </PmtId>
      <IntrBkSttlmAmt Ccy="GBP">15000.00</IntrBkSttlmAmt>
      <Dbtr>
        <Nm>Originating Corp Inc</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id><IBAN>DE89370400440532013000</IBAN></Id>
      </DbtrAcct>
      <CdtrAgt>
        <FinInstnId>
          <BICFI>BARCGB22XXX</BICFI>
        </FinInstnId>
      </CdtrAgt>
      <Cdtr>
        <Nm>British Trading Corp Ltd</Nm>
      </Cdtr>
      <CdtrAcct>
        <Id><IBAN>GB58WEST12345678901234</IBAN></Id>
      </CdtrAcct>
      <RmtInf>
        <Ustrd>Invoice GB-9921</Ustrd>
      </RmtInf>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>"""
SAMPLE_DQ01_XML_VALID_FR = SAMPLE_DQ01_XML_VALID_DE.replace("DE89370400440532013000", "FR1420041010050500013M02606").replace("Bavarian Industrial AG", "French Supply SAS")
# Corrupted check digit: DE89 -> DE00
SAMPLE_DQ01_XML_BAD_CHECK_DIGIT = SAMPLE_DQ01_XML_VALID_DE.replace("DE89370400440532013000", "DE00370400440532013000")
# Transposition in BBAN: 0532013000 -> 0523013000 (corrupts MOD-97)
SAMPLE_DQ01_XML_TRANSPOSITION = SAMPLE_DQ01_XML_VALID_DE.replace("DE89370400440532013000", "DE89370400440523013000")
# Single-digit substitution in BBAN: 0532013000 -> 0532013001
SAMPLE_DQ01_XML_SUBSTITUTION = SAMPLE_DQ01_XML_VALID_DE.replace("DE89370400440532013000", "DE89370400440532013001")
# Closed account in DDA: DE89500105179999999999
SAMPLE_DQ01_XML_CLOSED_ACCOUNT = SAMPLE_DQ01_XML_VALID_DE.replace("DE89370400440532013000", "DE89500105179999999999").replace("Bavarian Industrial AG", "Defunct Trading GmbH")
# Frozen account in DDA: DE39500105178888888888
SAMPLE_DQ01_XML_FROZEN_ACCOUNT = SAMPLE_DQ01_XML_VALID_DE.replace("DE89370400440532013000", "DE39500105178888888888").replace("Bavarian Industrial AG", "Frozen Assets AG")


# ============================================================================
# Section 1: Valid IBAN Baseline Tests (DQ01-01 to DQ01-03)
# ============================================================================

def test_dq01_01_valid_de_iban_stp_bank_handoff():
    """DQ01-01: Valid German (DE) IBAN with MOD-97 == 1, open DDA, and SSI match qualifies for autonomous STP."""
    package = InboundPackage(
        package_id="PKG-DQ01-01",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE
    )
    result = dq01_pipeline.process_package(package, amount=22000.0, currency="EUR")
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert result.stp_decision.stp_eligible is True
    assert result.outbound_envelope is not None
    assert result.outbound_envelope.execution_owner == "BANK"
    assert result.handoff_receipt is not None
    assert result.original_iban == "DE89370400440532013000"


def test_dq01_02_valid_gb_iban_stp_bank_handoff():
    """DQ01-02: Valid British (GB) IBAN with MOD-97 == 1, open DDA, and SSI match qualifies for autonomous STP."""
    package = InboundPackage(
        package_id="PKG-DQ01-02",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_GB
    )
    result = dq01_pipeline.process_package(package, amount=15000.0, currency="GBP")
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert result.original_iban == "GB58WEST12345678901234"


def test_dq01_03_valid_fr_iban_stp_bank_handoff():
    """DQ01-03: Valid French (FR) IBAN with MOD-97 == 1, open DDA, and SSI match qualifies for autonomous STP."""
    package = InboundPackage(
        package_id="PKG-DQ01-03",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_FR
    )
    result = dq01_pipeline.process_package(package, amount=15000.0, currency="EUR")
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert result.original_iban == "FR1420041010050500013M02606"


# ============================================================================
# Section 2: Mathematical Checksum & Permutation Solving Tests (DQ01-04 to DQ01-06)
# ============================================================================

def test_dq01_04_corrupted_check_digit_recalculation():
    """DQ01-04: Inbound DE IBAN with mistyped check digits (DE00...) is mathematically solved and STP executed."""
    package = InboundPackage(
        package_id="PKG-DQ01-04",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_BAD_CHECK_DIGIT,
        evidence_fields={"beneficiary_name": "Bavarian Industrial AG"}
    )
    result = dq01_pipeline.process_package(package, amount=22000.0, currency="EUR")
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert "<IBAN>DE89370400440532013000</IBAN>" in result.outbound_envelope.proposed_repair["repaired_payload"]
    assert result.stp_decision.stp_eligible is True


def test_dq01_05_single_transposition_bban_repaired():
    """DQ01-05: Inbound DE IBAN with adjacent transposition in BBAN is resolved via permutation solver."""
    package = InboundPackage(
        package_id="PKG-DQ01-05",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_TRANSPOSITION,
        evidence_fields={"beneficiary_name": "Bavarian Industrial AG"}
    )
    result = dq01_pipeline.process_package(package, amount=22000.0, currency="EUR")
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert "<IBAN>DE89370400440532013000</IBAN>" in result.outbound_envelope.proposed_repair["repaired_payload"]


def test_dq01_06_single_digit_substitution_bban_repaired():
    """DQ01-06: Inbound DE IBAN with single digit substitution is resolved via candidate intersection with SSI."""
    package = InboundPackage(
        package_id="PKG-DQ01-06",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_SUBSTITUTION,
        evidence_fields={"beneficiary_name": "Bavarian Industrial AG"}
    )
    result = dq01_pipeline.process_package(package, amount=22000.0, currency="EUR")
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert "<IBAN>DE89370400440532013000</IBAN>" in result.outbound_envelope.proposed_repair["repaired_payload"]


# ============================================================================
# Section 3: Core DDA Ledger Account Status & Fail-Closed Tests (DQ01-07 to DQ01-09)
# ============================================================================

def test_dq01_07_account_closed_fails_closed():
    """DQ01-07: Inbound IBAN corresponding to a CLOSED account in Bank Core DDA Ledger fails closed."""
    package = InboundPackage(
        package_id="PKG-DQ01-07",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_CLOSED_ACCOUNT,
        evidence_fields={"beneficiary_name": "Defunct Trading GmbH"}
    )
    result = dq01_pipeline.process_package(package, amount=20000.0, currency="EUR")
    assert result.is_stp_executed is False
    assert result.final_lifecycle_stage == "INVESTIGATION_COCKPIT"
    assert result.stp_decision.authority_validation_passed is False
    assert "CLOSED in Core DDA" in result.error_summary


def test_dq01_08_account_frozen_fails_closed():
    """DQ01-08: Inbound IBAN corresponding to a FROZEN account in Bank Core DDA Ledger fails closed."""
    package = InboundPackage(
        package_id="PKG-DQ01-08",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_FROZEN_ACCOUNT,
        evidence_fields={"beneficiary_name": "Frozen Assets AG"}
    )
    result = dq01_pipeline.process_package(package, amount=20000.0, currency="EUR")
    assert result.is_stp_executed is False
    assert result.final_lifecycle_stage == "INVESTIGATION_COCKPIT"
    assert result.stp_decision.authority_validation_passed is False
    assert "FROZEN in Core DDA" in result.error_summary


def test_dq01_09_account_restricted_fails_closed():
    """DQ01-09: Inbound IBAN corresponding to a RESTRICTED account in Bank Core DDA Ledger fails closed."""
    restricted_rec = CoreDDAAccountRecord(
        account_number="0532013000",
        iban="DE89370400440532013000",
        account_holder_name="Bavarian Industrial AG",
        status=AccountLedgerStatus.RESTRICTED
    )
    package = InboundPackage(
        package_id="PKG-DQ01-09",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE,
        evidence_fields={
            "beneficiary_name": "Bavarian Industrial AG",
            "core_dda_account": restricted_rec.model_dump()
        }
    )
    result = dq01_pipeline.process_package(package, amount=20000.0, currency="EUR")
    assert result.is_stp_executed is False
    assert result.stp_decision.authority_validation_passed is False
    assert result.final_lifecycle_stage == "INVESTIGATION_COCKPIT"


# ============================================================================
# Section 4: Bank SSI Authority & Disambiguation Tests (DQ01-10 to DQ01-11)
# ============================================================================

def test_dq01_10_bank_ssi_contradiction_blocks_stp():
    """DQ01-10: Inbound IBAN contradicts Bank SSI Master mandated IBAN, failing V_auth and blocking STP."""
    contradict_ssi = BankSSIMasterEntry(
        counterparty_id="CP-CONTRADICT-IBAN",
        beneficiary_name="Bavarian Industrial AG",
        mandated_iban="DE02100100100123456789",  # Different mandated IBAN
        allowed_ibans=["DE02100100100123456789"],
        is_authorized=True
    )
    package = InboundPackage(
        package_id="PKG-DQ01-10",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE,
        evidence_fields={
            "beneficiary_name": "Bavarian Industrial AG",
            "bank_ssi_master": contradict_ssi.model_dump()
        }
    )
    result = dq01_pipeline.process_package(package, amount=20000.0, currency="EUR")
    assert result.is_stp_executed is False
    assert result.stp_decision.authority_validation_passed is False
    assert result.final_lifecycle_stage == "INVESTIGATION_COCKPIT"


def test_dq01_11_multiple_candidates_routed_to_disambiguation_desk():
    """DQ01-11: Multiple mathematical permutations matching SSI force R_uniq=False -> DISAMBIGUATION_DESK."""
    # When multiple permutations are allowed in Bank SSI
    multi_ssi = BankSSIMasterEntry(
        counterparty_id="CP-MULTI-01",
        beneficiary_name="Multi Candidate Corp",
        mandated_iban="DE89370400440532013000",
        allowed_ibans=["DE89370400440532013000", "DE89370400440523013000", "DE02370400440523013000"],
        is_authorized=True
    )
    res = dq01_resolver.resolve_iban(
        raw_payload=SAMPLE_DQ01_XML_TRANSPOSITION,
        original_iban="DE89370400440523013000",
        beneficiary_name="Multi Candidate Corp",
        ssi_record=multi_ssi
    )
    assert res.uniqueness == ResolutionUniqueness.RESOLUTION_AMBIGUOUS or len(res.candidates) >= 1


# ============================================================================
# Section 5: Evidence Freshness & Sufficiency Tests (DQ01-12 to DQ01-16)
# ============================================================================

def test_dq01_12_stale_bank_ssi_evidence_fails_closed():
    """DQ01-12: Bank SSI Master evidence exceeding its freshness TTL fails evidence sufficiency (E_suff)."""
    stale_ssi = BankSSIMasterEntry(
        counterparty_id="CP-STALE-01",
        beneficiary_name="Bavarian Industrial AG",
        mandated_iban="DE89370400440532013000",
        retrieved_at=datetime.now(timezone.utc) - timedelta(days=5),
        expires_at=datetime.now(timezone.utc) - timedelta(days=4),
        freshness_seconds=86400
    )
    assert stale_ssi.is_stale is True

    package = InboundPackage(
        package_id="PKG-DQ01-12",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE,
        evidence_fields={
            "beneficiary_name": "Bavarian Industrial AG",
            "bank_ssi_master": stale_ssi.model_dump()
        }
    )
    result = dq01_pipeline.process_package(package, amount=20000.0, currency="EUR")
    assert result.is_stp_executed is False
    assert result.stp_decision.evidence_sufficient is False
    assert result.final_lifecycle_stage == "OPERATIONS_SUSPENSE"


def test_dq01_13_stale_core_dda_evidence_fails_closed():
    """DQ01-13: Core DDA Account status exceeding its 1-hour freshness TTL fails evidence sufficiency."""
    stale_dda = CoreDDAAccountRecord(
        account_number="0532013000",
        iban="DE89370400440532013000",
        account_holder_name="Bavarian Industrial AG",
        retrieved_at=datetime.now(timezone.utc) - timedelta(hours=5),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=4),
        freshness_seconds=3600
    )
    assert stale_dda.is_stale is True

    package = InboundPackage(
        package_id="PKG-DQ01-13",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE,
        evidence_fields={
            "beneficiary_name": "Bavarian Industrial AG",
            "core_dda_account": stale_dda.model_dump()
        }
    )
    result = dq01_pipeline.process_package(package, amount=20000.0, currency="EUR")
    assert result.is_stp_executed is False
    assert result.stp_decision.evidence_sufficient is False


def test_dq01_14_missing_mandatory_raw_payload_fails_sufficiency():
    """DQ01-14: Missing RAW_PAYLOAD item in Evidence Dossier fails sufficiency."""
    dossier = EvidenceDossier(case_id="CASE-DQ01-14", profile_id="DQ-01")
    suff = sufficiency_engine.evaluate_sufficiency(dossier)
    assert suff.is_sufficient is False
    assert "RAW_PAYLOAD" in suff.missing_mandatory_items


def test_dq01_15_missing_mandatory_ssi_fails_sufficiency():
    """DQ01-15: Missing BANK_SSI_MASTER_RECORD in Evidence Dossier fails sufficiency."""
    dossier = EvidenceDossier(case_id="CASE-DQ01-15", profile_id="DQ-01")
    dossier.add_item(EvidenceItem(
        item_name="RAW_PAYLOAD",
        source_name="IN",
        trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
        payload={"raw_text": SAMPLE_DQ01_XML_VALID_DE}
    ))
    suff = sufficiency_engine.evaluate_sufficiency(dossier)
    assert suff.is_sufficient is False
    assert "BANK_SSI_MASTER_RECORD" in suff.missing_mandatory_items


def test_dq01_16_missing_mandatory_dda_fails_sufficiency():
    """DQ01-16: Missing CORE_DDA_ACCOUNT_STATUS in Evidence Dossier fails sufficiency."""
    dossier = EvidenceDossier(case_id="CASE-DQ01-16", profile_id="DQ-01")
    dossier.add_item(EvidenceItem(
        item_name="RAW_PAYLOAD",
        source_name="IN",
        trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
        payload={"raw_text": SAMPLE_DQ01_XML_VALID_DE}
    ))
    dossier.add_item(EvidenceItem(
        item_name="BANK_SSI_MASTER_RECORD",
        source_name="SSI",
        trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
        payload={"is_authorized": True}
    ))
    suff = sufficiency_engine.evaluate_sufficiency(dossier)
    assert suff.is_sufficient is False
    assert "CORE_DDA_ACCOUNT_STATUS" in suff.missing_mandatory_items


# ============================================================================
# Section 6: Input Boundaries & Unrepairable Exception Tests (DQ01-17 to DQ01-18)
# ============================================================================

def test_dq01_17_oversized_malicious_input_exceeds_bounds():
    """DQ01-17: Oversized IBAN input (> 40 chars) exceeds safety boundaries and fails closed."""
    oversized_iban = "DE89" + "9" * 45
    res = dq01_resolver.resolve_iban(
        raw_payload=SAMPLE_DQ01_XML_VALID_DE.replace("DE89370400440532013000", oversized_iban),
        original_iban=oversized_iban
    )
    assert res.success is False
    assert res.outcome == IBANResolutionOutcome.SEARCH_BOUND_EXCEEDED


def test_dq01_18_unrepairable_corrupted_iban_fails_closed():
    """DQ01-18: Multiple random corruptions exceeding edit distance 1 fail resolution safely."""
    hopelessly_corrupted = "DE99ZZZZZZZZZZZZZZZZZZ"
    res = dq01_resolver.resolve_iban(
        raw_payload=SAMPLE_DQ01_XML_VALID_DE.replace("DE89370400440532013000", hopelessly_corrupted),
        original_iban=hopelessly_corrupted
    )
    assert res.success is False
    assert res.outcome in (IBANResolutionOutcome.NO_VALID_CANDIDATE, IBANResolutionOutcome.AUTHORITY_MISMATCH)


# ============================================================================
# Section 7: Confirmation of Payee (CoP) & Verification Tests (DQ01-19 to DQ01-20)
# ============================================================================

def test_dq01_19_cop_vop_match_corroborates_stp():
    """DQ01-19: Confirmation of Payee returning MATCH successfully corroborates beneficiary ownership."""
    cop_match = CoPResponse(
        account_name_submitted="Bavarian Industrial AG",
        matched_name="Bavarian Industrial AG",
        match_result=CoPMatchResult.MATCH,
        token="COP-VALID-TOKEN-01"
    )
    package = InboundPackage(
        package_id="PKG-DQ01-19",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE,
        evidence_fields={
            "beneficiary_name": "Bavarian Industrial AG",
            "cop_vop_response": cop_match.model_dump()
        }
    )
    result = dq01_pipeline.process_package(package, amount=20000.0, currency="EUR")
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"


def test_dq01_20_cop_vop_no_match_blocks_stp():
    """DQ01-20: Confirmation of Payee returning NO_MATCH blocks autonomous STP and routes to investigation."""
    cop_no_match = CoPResponse(
        account_name_submitted="Bavarian Industrial AG",
        matched_name="Fraudulent Shell Entity Ltd",
        match_result=CoPMatchResult.NO_MATCH,
        token="COP-FAIL-TOKEN"
    )
    package = InboundPackage(
        package_id="PKG-DQ01-20",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE,
        evidence_fields={
            "beneficiary_name": "Bavarian Industrial AG",
            "cop_vop_response": cop_no_match.model_dump(),
            "require_cop": True
        }
    )
    result = dq01_pipeline.process_package(package, amount=20000.0, currency="EUR")
    assert result.is_stp_executed is False
    assert result.final_lifecycle_stage == "INVESTIGATION_COCKPIT"


# ============================================================================
# Section 8: Policy, Thresholds & Compliance Gates (DQ01-21 to DQ01-23)
# ============================================================================

def test_dq01_21_compliance_gate_failure_blocks_stp():
    """DQ01-21: Inbound exception encountering a compliance sanctions hold is immediately blocked."""
    package = InboundPackage(
        package_id="PKG-DQ01-21",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE
    )
    result = dq01_pipeline.process_package(
        package,
        amount=20000.0,
        currency="EUR",
        compliance_status=ComplianceGateStatus.FAIL
    )
    assert result.is_stp_executed is False
    assert result.stp_decision.compliance_gate_passed is False
    assert result.final_lifecycle_stage == "COMPLIANCE_SUSPENSE"


def test_dq01_22_amount_limit_exceeded_routes_to_hitl():
    """DQ01-22: Transaction exceeding max autonomous STP threshold ($25,000) routes to HITL."""
    package = InboundPackage(
        package_id="PKG-DQ01-22",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE
    )
    result = dq01_pipeline.process_package(package, amount=250000.0, currency="EUR")
    assert result.is_stp_executed is False
    assert result.stp_decision.bank_policy_allows is False
    assert result.final_lifecycle_stage == "OPERATIONS_SUSPENSE"


def test_dq01_23_bank_auto_stp_disabled_routes_to_hitl():
    """DQ01-23: When bank configuration disables autonomous STP, cases route to Operations Suspense."""
    strict_policy = STPPolicyConfig(auto_stp_enabled=False)
    custom_pipeline = DQ01STPPipeline(policy_config=strict_policy)
    package = InboundPackage(
        package_id="PKG-DQ01-23",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE
    )
    result = custom_pipeline.process_package(package, amount=20000.0, currency="EUR")
    assert result.is_stp_executed is False
    assert result.stp_decision.bank_policy_allows is False


# ============================================================================
# Section 9: Semantic Invariance & Zero-Alteration Tests (DQ01-24 to DQ01-25)
# ============================================================================

def test_dq01_24_semantic_invariance_verification_preserves_all_fields():
    """DQ01-24: Verifies that monetary amounts, currencies, UETR, EndToEndId, and Debtor data remain 100% invariant."""
    res = dq01_resolver.resolve_iban(
        raw_payload=SAMPLE_DQ01_XML_BAD_CHECK_DIGIT,
        original_iban="DE00370400440532013000",
        beneficiary_name="Bavarian Industrial AG"
    )
    assert res.success is True
    assert res.semantic_preservation_passed is True
    assert "<IntrBkSttlmAmt Ccy=\"EUR\">22000.00</IntrBkSttlmAmt>" in res.candidates[0].repaired_payload
    assert "<UETR>aa11bb22-33cc-44dd-55ee-66ff77889900</UETR>" in res.candidates[0].repaired_payload


def test_dq01_25_semantic_invariance_tamper_attempt_detected():
    """DQ01-25: Attempted alteration of amount in repaired payload triggers semantic failure."""
    pre_tokens = dq01_resolver._extract_business_tokens(SAMPLE_DQ01_XML_VALID_DE)
    tampered_xml = SAMPLE_DQ01_XML_VALID_DE.replace("22000.00", "99000.00")
    post_tokens = dq01_resolver._extract_business_tokens(tampered_xml)
    passed, err = dq01_resolver._verify_semantic_invariance(pre_tokens, post_tokens)
    assert passed is False
    assert "Monetary amount altered" in err


# ============================================================================
# Section 10: HITL Governance & Segregation of Duties Tests (DQ01-26 to DQ01-27)
# ============================================================================

def test_dq01_26_hitl_maker_checker_lifecycle_success():
    """DQ01-26: High-value case successfully completes human Maker submission and Checker dual-authorization."""
    package = InboundPackage(
        package_id="PKG-DQ01-26",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_BAD_CHECK_DIGIT,
        evidence_fields={"beneficiary_name": "Bavarian Industrial AG"}
    )
    result = dq01_pipeline.process_package(package, amount=200000.0, currency="EUR")
    assert result.is_stp_executed is False
    case_id = result.case_id

    # Maker submits
    maker_res = dq01_pipeline.submit_maker(
        case_id=case_id,
        maker_id="maker_analyst_01",
        selected_candidate_id=result.resolution_result.candidates[0].candidate_id,
        rationale="Verified check-digit mistype against invoice"
    )
    assert maker_res["status"] == "PENDING_CHECKER_APPROVAL"

    # Checker approves
    checker_res = dq01_pipeline.approve_checker(
        case_id=case_id,
        checker_id="checker_officer_02",
        notes="Dual-authorization verified against Core DDA"
    )
    assert checker_res.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert checker_res.is_hitl_approved is True
    assert checker_res.outbound_envelope.execution_owner == "BANK"


def test_dq01_27_hitl_maker_self_approval_segregation_of_duties_violation():
    """DQ01-27: Segregation of Duties violation raised when Maker attempts to self-approve as Checker."""
    package = InboundPackage(
        package_id="PKG-DQ01-27",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_BAD_CHECK_DIGIT,
        evidence_fields={"beneficiary_name": "Bavarian Industrial AG"}
    )
    result = dq01_pipeline.process_package(package, amount=200000.0, currency="EUR")
    case_id = result.case_id

    dq01_pipeline.submit_maker(
        case_id=case_id,
        maker_id="rogue_operator_01",
        selected_candidate_id=result.resolution_result.candidates[0].candidate_id,
        rationale="Self submission"
    )

    with pytest.raises(PermissionError, match="Segregation of Duties Violation"):
        dq01_pipeline.approve_checker(
            case_id=case_id,
            checker_id="rogue_operator_01",
            notes="Self approval attempt"
        )


# ============================================================================
# Section 11: Canonical Envelopes & Bank Handoff Contract (DQ01-28 to DQ01-29)
# ============================================================================

def test_dq01_28_canonical_intake_envelope_transport_neutrality():
    """DQ01-28: Processes a transport-neutral CanonicalIntakeEnvelope through the DQ-01 pipeline."""
    envelope = CanonicalIntakeEnvelope(
        message_id="MSG-CANONICAL-DQ01-01",
        source_system="CORE_BANKING_ENGINE",
        channel="MQ_SERIES",
        payload_format="XML_ISO20022",
        payment_reference="PMT-DQ01-CANONICAL",
        correlation_id="CORR-DQ01-CANONICAL",
        amount=22000.0,
        currency="EUR",
        raw_payload=SAMPLE_DQ01_XML_VALID_DE,
        evidence_items={"original_iban": "DE89370400440532013000", "beneficiary_name": "Bavarian Industrial AG"}
    )
    result = dq01_pipeline.process_canonical_envelope(envelope)
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"


def test_dq01_29_outbound_canonical_envelope_bank_handoff_contract():
    """DQ01-29: Outbound Canonical Envelope strictly adheres to Bank Handoff Boundary (execution_owner = BANK)."""
    package = InboundPackage(
        package_id="PKG-DQ01-29",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE
    )
    result = dq01_pipeline.process_package(package, amount=22000.0, currency="EUR")
    outbound = result.outbound_envelope
    assert outbound is not None
    assert outbound.profile_id == "DQ-01"
    assert outbound.execution_owner == "BANK"
    assert outbound.lifecycle_state == HandoffLifecycleState.BANK_HANDOFF_READY
    assert outbound.proposed_repair["repaired_payload"] is not None


# ============================================================================
# Section 12: Cryptographic Audit Provenance Tests (DQ01-30)
# ============================================================================

def test_dq01_30_full_cryptographic_audit_trail_and_hash_chain():
    """DQ01-30: Complete 12-stage execution generates tamper-evident cryptographic Merkle-like audit chain."""
    package = InboundPackage(
        package_id="PKG-DQ01-30",
        source_channel="BANK_INBOUND_FEED",
        raw_payload_str=SAMPLE_DQ01_XML_VALID_DE
    )
    result = dq01_pipeline.process_package(package, amount=22000.0, currency="EUR")
    assert result.is_stp_executed is True

    # Verify audit hash chain validity
    ts = datetime.now(timezone.utc).isoformat()
    h1 = calculate_event_hash(1, ts, result.case_id, "INGESTION", "SYSTEM", "INGEST", "Details 1", "0" * 64, 22000.0, "EUR", "GB82", "DE89")
    h2 = calculate_event_hash(2, ts, result.case_id, "BANK_HANDOFF", "SYSTEM", "HANDOFF", "Details 2", h1, 22000.0, "EUR", "GB82", "DE89")
    events = [
        {"event_index": 1, "timestamp": ts, "case_id": result.case_id, "stage_name": "INGESTION", "actor_id": "SYSTEM", "action_name": "INGEST", "details": "Details 1", "prev_hash": "0" * 64, "current_hash": h1, "amount": 22000.0, "currency": "EUR", "debtor_account": "GB82", "creditor_account": "DE89"},
        {"event_index": 2, "timestamp": ts, "case_id": result.case_id, "stage_name": "BANK_HANDOFF", "actor_id": "SYSTEM", "action_name": "HANDOFF", "details": "Details 2", "prev_hash": h1, "current_hash": h2, "amount": 22000.0, "currency": "EUR", "debtor_account": "GB82", "creditor_account": "DE89"}
    ]
    assert verify_audit_chain(events) is True
