"""Unit Tests for RemittanceDocumentEngine (DQ-04, CO-07).

Verifies structured remittance (<Strd>) derivation from invoice evidence
and deterministic statutory Balance of Payments (BoP) reporting code derivations.
"""
import pytest
from app.services.engines.remittance_document_engine import RemittanceDocumentEngine
from app.schemas.resolution_contract import ResolutionStatus, ResolutionUniqueness


@pytest.fixture
def engine():
    return RemittanceDocumentEngine()


class TestRemittanceDocumentEngineDQ04:
    """Tests for DQ-04: Missing Remittance Information."""

    def test_dq04_happy_path_invoice_id_lookup(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq04_missing_remittance(
            invoice_id_or_narrative="INV-2026-OCT-8891",
            amount=250000.0,
            currency="EUR"
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
        assert cand is not None
        strd = cand.repaired_structured["RmtInf"]["Strd"]
        assert strd["RfrdDocInf"]["Nb"] == "INV-2026-OCT-8891"
        assert strd["RfrdDocAmt"]["DuePyblAmt"] == 250000.0

    def test_dq04_happy_path_supplied_invoice_record(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq04_missing_remittance(
            invoice_id_or_narrative="",
            evidence_context={
                "invoice_document": {
                    "invoice_id": "INV-SUPPLIED-999",
                    "total_amount": 15000.0,
                    "currency": "USD",
                    "invoice_date": "2026-10-08"
                }
            }
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert cand.repaired_structured["RmtInf"]["Strd"]["RfrdDocInf"]["Nb"] == "INV-SUPPLIED-999"

    def test_dq04_unparseable_document_routes_to_hitl(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq04_missing_remittance(
            invoice_id_or_narrative="CORRUPTED_TEXT",
            evidence_context={"unparseable_remittance_document": True}
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "unparseable" in err.lower()


class TestRemittanceDocumentEngineCO07:
    """Tests for CO-07: Regulatory Reporting Required."""

    def test_co07_happy_path_brazil_bop_derivation(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_co07_regulatory_reporting(
            destination_country="BR",
            currency="BRL",
            amount=75000.0,
            clearing_rail="SWIFT_CBPR+",
            evidence_context={"trade_category": "GOODS"}
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
        assert cand is not None
        rgltry = cand.repaired_structured["RgltryRptg"]
        assert rgltry["Authrty"]["AuthrtyNm"] == "BANCO_CENTRAL_DO_BRASIL"
        assert rgltry["Dtls"]["Cd"] == "BOP-BR-101"

    def test_co07_happy_path_india_bop_derivation(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_co07_regulatory_reporting(
            destination_country="IN",
            currency="INR",
            amount=50000.0,
            clearing_rail="SWIFT_CBPR+",
            evidence_context={"trade_category": "SERVICES"}
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        rgltry = cand.repaired_structured["RgltryRptg"]
        assert rgltry["Authrty"]["AuthrtyNm"] == "RESERVE_BANK_OF_INDIA"
        assert rgltry["Dtls"]["Cd"] == "BOP-IN-P0802"

    def test_co07_missing_statutory_license_fails_closed(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_co07_regulatory_reporting(
            destination_country="BR",
            currency="BRL",
            amount=75000.0,
            clearing_rail="SWIFT_CBPR+",
            evidence_context={"missing_statutory_license": True}
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "statutory" in err.lower()
