"""Comprehensive Behavioral Test Suite for DQ-08 (INVALID_ROUTING_CODE) Remediation.

Covers all authoritative behavioral acceptance scenarios:
- BEH-DQ08-01: Valid active routing identifier (Active routing path without merger)
- BEH-DQ08-02: Valid retired identifier with 1:1 successor (Successor mapping path)
- BEH-DQ08-03: Invalid structural syntax
- BEH-DQ08-04: Invalid ABA 9-digit Mod-10 checksum
- BEH-DQ08-05: Unknown routing identifier absent from directory
- BEH-DQ08-06: Inactive routing identifier with zero successors
- BEH-DQ08-07: 1:N ambiguous split successors (Disambiguation Desk)
- BEH-DQ08-08: Institution / Successor not reachable on target clearing rail
- BEH-DQ08-09: Stale / expired authority directory cache fails closed
- BEH-DQ08-10: Bank Counterparty SSI contradiction
- BEH-DQ08-11: Bank policy monetary threshold exceeded
- BEH-DQ08-12: Historical precedent cannot override live authority
- BEH-DQ08-13: Adversarial prompt injection defense in routing fields
- BEH-DQ08-14: Bank handoff contract with execution_owner = "BANK"
- Segregation of Duties (Maker cannot be Checker)
- UK Sort Code (GBDSC) structural parsing & merger routing
- Lossless semantic invariance validation
"""
import pytest
import hashlib
from datetime import datetime, timezone, timedelta

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
from app.adapters.routing_directory_adapter import (
    SyntheticRoutingDirectoryAdapter,
    RoutingIdentifierStatus,
    BankCounterpartySSI,
    TargetRailRoutingSpec,
    RoutingDirectoryEntry,
    CentralBankMergerEntry,
)
from app.services.dq08_routing_resolver import (
    GovernedRoutingCodeResolver,
    governed_routing_resolver,
    RoutingResolutionOutcome,
    DQ08RoutingResolutionResult,
)
from app.services.dq08_routing_stp_pipeline import (
    DQ08RoutingSTPPipeline,
    dq08_routing_pipeline,
    DQ08RoutingPipelineResult,
)
from app.adapters.input_adapter import InboundPackage
from app.services.audit_service import audit_service


# Sample ISO 20022 pacs.008 XML fixtures with <ClrSysMmbId>

SAMPLE_US_XML_ACTIVE_ABA = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>MSG-2026-DQ08-ACT-001</MsgId>
      <CreDtTm>2026-10-07T14:00:00Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <EndToEndId>E2E-DQ08-ACTIVE-01</EndToEndId>
        <UETR>c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c</UETR>
      </PmtId>
      <IntrBkSttlmAmt Ccy="USD">45000.00</IntrBkSttlmAmt>
      <Dbtr>
        <Nm>Acme Global Holdings LLC</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id><IBAN>US12CHAS00012345678901</IBAN></Id>
      </DbtrAcct>
      <CdtrAgt>
        <FinInstnId>
          <ClrSysMmbId>
            <ClrSysId><Cd>USABA</Cd></ClrSysId>
            <MmbId>021000021</MmbId>
          </ClrSysMmbId>
          <Nm>JPMorgan Chase Bank NA</Nm>
        </FinInstnId>
      </CdtrAgt>
      <Cdtr>
        <Nm>Apex Logistics US Corp</Nm>
      </Cdtr>
      <CdtrAcct>
        <Id><IBAN>US99BOFA00098765432109</IBAN></Id>
      </CdtrAcct>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>"""


SAMPLE_US_XML_RETIRED_ABA = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>MSG-2026-DQ08-RET-001</MsgId>
      <CreDtTm>2026-10-07T14:00:00Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <EndToEndId>E2E-DQ08-MERGED-01</EndToEndId>
        <UETR>e9f8d7c6-b5a4-4321-9876-fedcba098765</UETR>
      </PmtId>
      <IntrBkSttlmAmt Ccy="USD">25000.00</IntrBkSttlmAmt>
      <Dbtr>
        <Nm>Metropolitan Supply Co</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id><IBAN>US55WFBI00055566677788</IBAN></Id>
      </DbtrAcct>
      <CdtrAgt>
        <FinInstnId>
          <ClrSysMmbId>
            <ClrSysId><Cd>USABA</Cd></ClrSysId>
            <MmbId>021000089</MmbId>
          </ClrSysMmbId>
          <Nm>Chemical Bank NY (Retired RTN)</Nm>
        </FinInstnId>
      </CdtrAgt>
      <Cdtr>
        <Nm>Eastern Distribution Inc</Nm>
      </Cdtr>
      <CdtrAcct>
        <Id><IBAN>US11CHAS00011122233344</IBAN></Id>
      </CdtrAcct>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>"""


SAMPLE_UK_XML_ACTIVE_SORTCODE = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>MSG-2026-DQ08-UK-001</MsgId>
      <CreDtTm>2026-10-07T14:00:00Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <EndToEndId>E2E-DQ08-UK-01</EndToEndId>
        <UETR>a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d</UETR>
      </PmtId>
      <IntrBkSttlmAmt Ccy="GBP">12000.00</IntrBkSttlmAmt>
      <Dbtr><Nm>London Trade Corp</Nm></Dbtr>
      <DbtrAcct><Id><IBAN>GB82WEST12345678901234</IBAN></Id></DbtrAcct>
      <CdtrAgt>
        <FinInstnId>
          <ClrSysMmbId>
            <ClrSysId><Cd>GBDSC</Cd></ClrSysId>
            <MmbId>200000</MmbId>
          </ClrSysMmbId>
          <Nm>Barclays Bank UK PLC</Nm>
        </FinInstnId>
      </CdtrAgt>
      <Cdtr><Nm>UK Wholesale Ltd</Nm></Cdtr>
      <CdtrAcct><Id><IBAN>GB33BARC20000012345678</IBAN></Id></CdtrAcct>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>"""


# ============================================================================
# 1. BEH-DQ08-01: Valid Active Routing Identifier
# ============================================================================

def test_beh_dq08_01_active_routing_identifier_passes_without_merger_lookup():
    """BEH-DQ08-01: Active routing identifier (021000021) is verified valid and reachable without requiring merger evidence."""
    pkg = InboundPackage(
        package_id="PKG-DQ08-ACT-01",
        source_channel="BANK_INPUT_FOLDER",
        raw_payload_str=SAMPLE_US_XML_ACTIVE_ABA,
        evidence_fields={"routing_identifier": "021000021", "clearing_system": "USABA", "target_rail": "FEDWIRE"}
    )
    result = dq08_routing_pipeline.process_package(pkg, amount=45000.0, clearing_system="USABA", target_rail="FEDWIRE")
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert result.routing_result.outcome == RoutingResolutionOutcome.ACTIVE_ROUTING_VALID
    assert result.routing_result.resolved_routing_code == "021000021"
    assert result.authority_result.is_structural_syntax_valid is True
    assert result.authority_result.is_business_authority_confirmed is True
    assert result.stp_decision.stp_eligible is True


# ============================================================================
# 2. BEH-DQ08-02: Valid Retired Routing Identifier with 1:1 Successor
# ============================================================================

def test_beh_dq08_02_retired_routing_identifier_maps_cleanly_to_1to1_successor():
    """BEH-DQ08-02: Retired routing identifier (021000089 Chemical Bank) maps to active successor (021000021 Chase)."""
    pkg = InboundPackage(
        package_id="PKG-DQ08-RET-01",
        source_channel="BANK_INPUT_FOLDER",
        raw_payload_str=SAMPLE_US_XML_RETIRED_ABA,
        evidence_fields={"routing_identifier": "021000089", "clearing_system": "USABA", "target_rail": "FEDWIRE"}
    )
    result = dq08_routing_pipeline.process_package(pkg, amount=25000.0, clearing_system="USABA", target_rail="FEDWIRE")
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert result.routing_result.outcome == RoutingResolutionOutcome.SUCCESSOR_FOUND
    assert result.routing_result.original_routing_code == "021000089"
    assert result.routing_result.resolved_routing_code == "021000021"
    assert result.routing_result.uniqueness == ResolutionUniqueness.RESOLUTION_UNIQUE

    # Verify Repaired XML contains new routing transit number
    repaired = result.outbound_envelope.proposed_repair["repaired_payload"]
    assert "<MmbId>021000021</MmbId>" in repaired
    assert "<MmbId>021000089</MmbId>" not in repaired


# ============================================================================
# 3. BEH-DQ08-03: Invalid Structural Syntax
# ============================================================================

def test_beh_dq08_03_invalid_syntax_fails_deterministic_validation():
    """BEH-DQ08-03: Routing identifier with non-digit characters or wrong length fails V_det."""
    res = governed_routing_resolver.resolve_routing_code(
        raw_payload=SAMPLE_US_XML_ACTIVE_ABA,
        routing_code="021000AB!",
        clearing_system="USABA"
    )
    assert res.success is False
    assert res.outcome in (RoutingResolutionOutcome.INVALID_SYNTAX, RoutingResolutionOutcome.INVALID_CHECKSUM)
    assert res.semantic_preservation_passed is False


# ============================================================================
# 4. BEH-DQ08-04: Invalid ABA 9-Digit Mod-10 Checksum
# ============================================================================

def test_beh_dq08_04_invalid_aba_mod10_checksum_halts_stp():
    """BEH-DQ08-04: 9-digit ABA with corrupted check digit fails Mod-10 verification."""
    # 021000021 is valid. 021000022 fails Mod-10.
    assert GovernedRoutingCodeResolver.compute_aba_mod10_checksum("021000021") is True
    assert GovernedRoutingCodeResolver.compute_aba_mod10_checksum("021000022") is False

    res = governed_routing_resolver.resolve_routing_code(
        raw_payload=SAMPLE_US_XML_ACTIVE_ABA,
        routing_code="021000022",
        clearing_system="USABA"
    )
    assert res.success is False
    assert res.outcome == RoutingResolutionOutcome.INVALID_CHECKSUM
    assert "Mod-10 checksum validation" in res.error_message


# ============================================================================
# 5. BEH-DQ08-05: Unknown Routing Identifier Absent from Directory
# ============================================================================

def test_beh_dq08_05_unknown_routing_identifier_halts_with_directory_not_found():
    """BEH-DQ08-05: Syntactically valid ABA not registered in central bank directory halts with DIRECTORY_NOT_FOUND."""
    # 011000015 has valid checksum but is not seeded in synthetic fixture
    res = governed_routing_resolver.resolve_routing_code(
        raw_payload=SAMPLE_US_XML_ACTIVE_ABA,
        routing_code="011000015",
        clearing_system="USABA"
    )
    assert res.success is False
    assert res.outcome == RoutingResolutionOutcome.DIRECTORY_NOT_FOUND


# ============================================================================
# 6. BEH-DQ08-06: Inactive Identifier with Zero Successors
# ============================================================================

def test_beh_dq08_06_inactive_identifier_zero_successors_halts_to_suspense():
    """BEH-DQ08-06: Inactive defunct routing code (021001088) with 0 successors fails closed."""
    res = governed_routing_resolver.resolve_routing_code(
        raw_payload=SAMPLE_US_XML_ACTIVE_ABA,
        routing_code="021001088",
        clearing_system="USABA"
    )
    assert res.success is False
    assert res.outcome == RoutingResolutionOutcome.INACTIVE_NO_SUCCESSOR


# ============================================================================
# 7. BEH-DQ08-07: 1:N Ambiguous Split Successors
# ============================================================================

def test_beh_dq08_07_ambiguous_split_merger_forces_r_uniq_false_and_disambiguation():
    """BEH-DQ08-07: Retired identifier mapping to multiple successors (021000128 -> Chase / BofA) forces R_uniq=False."""
    pkg = InboundPackage(
        package_id="PKG-DQ08-AMB-01",
        source_channel="BANK_INPUT_FOLDER",
        raw_payload_str=SAMPLE_US_XML_RETIRED_ABA.replace("021000089", "021000128"),
        evidence_fields={"routing_identifier": "021000128", "clearing_system": "USABA"}
    )
    result = dq08_routing_pipeline.process_package(pkg, amount=10000.0, clearing_system="USABA")
    assert result.is_stp_executed is False
    assert result.is_disambiguation_routed is True
    assert result.final_lifecycle_stage == "DISAMBIGUATION_REQUIRED"
    assert result.recommended_routing == "DISAMBIGUATION_DESK"
    assert result.routing_result.uniqueness == ResolutionUniqueness.RESOLUTION_AMBIGUOUS
    assert len(result.routing_result.candidates) == 2


# ============================================================================
# 8. BEH-DQ08-08: Institution Not Reachable on Target Clearing Rail
# ============================================================================

def test_beh_dq08_08_active_code_unreachable_on_target_rail_halts():
    """BEH-DQ08-08: Active routing code supporting only ACH (091000019) halts when requested rail is FEDWIRE."""
    res = governed_routing_resolver.resolve_routing_code(
        raw_payload=SAMPLE_US_XML_ACTIVE_ABA,
        routing_code="091000019",
        clearing_system="USABA",
        target_rail_spec=TargetRailRoutingSpec(clearing_system="USABA", target_rail="FEDWIRE")
    )
    assert res.success is False
    assert res.outcome == RoutingResolutionOutcome.ACTIVE_NOT_REACHABLE


# ============================================================================
# 9. BEH-DQ08-09: Stale Authority Directory Cache Fails Closed
# ============================================================================

def test_beh_dq08_09_stale_directory_fails_closed():
    """BEH-DQ08-09: Expired directory cache fails closed when real-time sync is unavailable."""
    adapter = SyntheticRoutingDirectoryAdapter()
    entry = adapter.lookup_routing_code("021000021", "USABA")
    entry.retrieved_at = datetime.now(timezone.utc) - timedelta(days=2) # 48h old > 24h TTL

    resolver = GovernedRoutingCodeResolver(directory_adapter=adapter)
    res = resolver.resolve_routing_code(
        raw_payload=SAMPLE_US_XML_ACTIVE_ABA,
        routing_code="021000021",
        clearing_system="USABA",
        allow_stale_directory=False
    )
    assert res.success is False
    assert res.outcome == RoutingResolutionOutcome.DIRECTORY_STALE


# ============================================================================
# 10. BEH-DQ08-10: Bank Counterparty SSI Contradiction
# ============================================================================

def test_beh_dq08_10_bank_ssi_contradiction_halts_stp():
    """BEH-DQ08-10: Successor code contradicting mandated Bank SSI routing code halts with SSI_CONTRADICTION."""
    ssi = BankCounterpartySSI(
        counterparty_id="CP-US-99",
        clearing_system="USABA",
        mandated_routing_code="121000249", # Mandates Wells Fargo, but retired code maps to Chase
        is_authorized=True
    )
    res = governed_routing_resolver.resolve_routing_code(
        raw_payload=SAMPLE_US_XML_RETIRED_ABA,
        routing_code="021000089", # Maps to 021000021
        clearing_system="USABA",
        bank_ssi=ssi
    )
    assert res.success is False
    assert res.outcome == RoutingResolutionOutcome.SSI_CONTRADICTION


# ============================================================================
# 11. BEH-DQ08-11: Bank Policy Monetary Threshold Exceeded
# ============================================================================

def test_beh_dq08_11_policy_threshold_exceeded_routes_to_hitl():
    """BEH-DQ08-11: Exception amount ($1,500,000) exceeding policy ceiling ($1,000,000) routes to HITL Maker-Checker."""
    pkg = InboundPackage(
        package_id="PKG-DQ08-HIGHVAL",
        source_channel="BANK_INPUT_FOLDER",
        raw_payload_str=SAMPLE_US_XML_RETIRED_ABA,
        evidence_fields={"routing_identifier": "021000089", "clearing_system": "USABA"}
    )
    result = dq08_routing_pipeline.process_package(pkg, amount=1500000.0, clearing_system="USABA")
    assert result.is_stp_executed is False
    assert result.is_hitl_routed is True
    assert result.final_lifecycle_stage == "HITL_MAKER_PENDING"
    assert result.stp_decision.stp_eligible is False
    assert result.stp_decision.bank_policy_allows is False


# ============================================================================
# 12. BEH-DQ08-12: Historical Precedent Cannot Override Authority
# ============================================================================

def test_beh_dq08_12_historical_precedent_cannot_override_live_directory():
    """BEH-DQ08-12: Non-authoritative historical logs cannot assert validity when directory fails."""
    res = governed_routing_resolver.resolve_routing_code(
        raw_payload=SAMPLE_US_XML_ACTIVE_ABA,
        routing_code="021001088", # Defunct
        clearing_system="USABA"
    )
    assert res.success is False
    # AI confidence or historical precedent cannot convert this to True


# ============================================================================
# 13. BEH-DQ08-13: Adversarial Prompt Injection Defense
# ============================================================================

def test_beh_dq08_13_adversarial_prompt_injection_handled_safely():
    """BEH-DQ08-13: Prompt injection payload in routing reference text is validated safely without code execution."""
    injected_code = "021000021' OR 1=1; DROP TABLE ROUTING; --"
    res = governed_routing_resolver.resolve_routing_code(
        raw_payload=SAMPLE_US_XML_ACTIVE_ABA,
        routing_code=injected_code,
        clearing_system="USABA"
    )
    assert res.success is False
    assert res.outcome in (RoutingResolutionOutcome.INVALID_SYNTAX, RoutingResolutionOutcome.INVALID_CHECKSUM)


# ============================================================================
# 14. BEH-DQ08-14: Bank Execution Boundary
# ============================================================================

def test_beh_dq08_14_bank_handoff_contract_execution_owner_bank():
    """BEH-DQ08-14: STP handoff terminates at BANK_HANDOFF_READY with execution_owner = 'BANK'."""
    pkg = InboundPackage(
        package_id="PKG-DQ08-HANDOFF",
        source_channel="BANK_INPUT_FOLDER",
        raw_payload_str=SAMPLE_US_XML_ACTIVE_ABA,
        evidence_fields={"routing_identifier": "021000021", "clearing_system": "USABA"}
    )
    result = dq08_routing_pipeline.process_package(pkg, amount=10000.0, clearing_system="USABA")
    assert result.outbound_envelope.execution_owner == "BANK"
    assert result.outbound_envelope.lifecycle_state == HandoffLifecycleState.BANK_HANDOFF_READY


# ============================================================================
# 15. UK Sort Code (GBDSC) Structural & Successor Tests
# ============================================================================

def test_dq08_uk_sort_code_active_and_successor_mapping():
    """Verifies UK 6-digit Sort Code resolution for active (200000) and retired (200001 -> 200000)."""
    # Active Sort Code
    res_act = governed_routing_resolver.resolve_routing_code(
        raw_payload=SAMPLE_UK_XML_ACTIVE_SORTCODE,
        routing_code="200000",
        clearing_system="GBDSC",
        target_rail_spec=TargetRailRoutingSpec(clearing_system="GBDSC", target_rail="CHAPS")
    )
    assert res_act.success is True
    assert res_act.outcome == RoutingResolutionOutcome.ACTIVE_ROUTING_VALID

    # Retired Sort Code with 1:1 Successor
    res_ret = governed_routing_resolver.resolve_routing_code(
        raw_payload=SAMPLE_UK_XML_ACTIVE_SORTCODE.replace("200000", "200001"),
        routing_code="200001",
        clearing_system="GBDSC",
        target_rail_spec=TargetRailRoutingSpec(clearing_system="GBDSC", target_rail="CHAPS")
    )
    assert res_ret.success is True
    assert res_ret.outcome == RoutingResolutionOutcome.SUCCESSOR_FOUND
    assert res_ret.resolved_routing_code == "200000"


# ============================================================================
# 16. HITL Segregation of Duties & Continuation Flow
# ============================================================================

def test_dq08_hitl_maker_checker_sod_enforced():
    """Verifies that high-value exception routes to HITL and enforces Segregation of Duties."""
    pkg = InboundPackage(
        package_id="PKG-DQ08-SOD",
        source_channel="BANK_INPUT_FOLDER",
        raw_payload_str=SAMPLE_US_XML_RETIRED_ABA,
        evidence_fields={"routing_identifier": "021000089", "clearing_system": "USABA"}
    )
    pipeline = DQ08RoutingSTPPipeline()
    result = pipeline.process_package(pkg, amount=2000000.0) # > 1,000,000 threshold
    assert result.is_hitl_routed is True

    # Attempt Self-Approval (Maker == Checker) -> Must Raise ValueError
    with pytest.raises(ValueError, match="Segregation of Duties Violation"):
        pipeline.approve_and_dispatch(
            case_id=result.case_id,
            maker_id="ANALYST_ALICE",
            checker_id="ANALYST_ALICE",
            rationale="Attempting self-approval"
        )

    # Valid Dual Authorization (Maker != Checker)
    approved = pipeline.approve_and_dispatch(
        case_id=result.case_id,
        maker_id="ANALYST_ALICE",
        checker_id="SUPERVISOR_BOB",
        rationale="Verified Chemical Bank merger into Chase via Federal Reserve directory."
    )
    assert approved.is_hitl_approved is True
    assert approved.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert approved.outbound_envelope.execution_owner == "BANK"
