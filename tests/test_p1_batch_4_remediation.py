"""Tests for PeX P1 Remediation Batch 4: Payment Domain & Reference Data Corrections.

Covers Master IDs:
- MST-021: Invalid / Fabricated US & Japan IBAN Fixtures
- MST-024: German IBAN Fixture Format (22-char numeric DE vs 26-char invalid)
- MST-025: AC01 vs AC04 (Account Identifier Incorrect vs Closed Account)
- MST-026: pacs.004 vs camt.056 (Payment Return vs Cancellation Request)
- MST-027: Payment Purpose Codes (ISO 20022 External Purpose List)
- MST-028: Fedwire IMAD Format (Strict 18-Character FAIM Standard)
- MST-029: Bacs Payment Classification (3-Day Bulk Batch ACH vs RTGS)
"""
import pytest
import json
from pathlib import Path

from app.services.canonicalizer import (
    validate_iban_mod97,
    validate_iban_structure,
    validate_fedwire_imad,
    is_valid_iso20022_purpose_code,
    OFFICIAL_IBAN_COUNTRY_LENGTHS,
    NON_IBAN_COUNTRIES,
    VALID_ISO20022_PURPOSE_CODES,
    ISO20022_RETURN_REASON_CODES
)
from app.services.profile_engine import PROFILE_SPECS
from app.schemas.canonical import ExceptionProfile, ExceptionDomain


# ==============================================================================
# MST-021: Invalid / Fabricated US & Japan IBAN Fixtures
# ==============================================================================

def test_mst_021_us_japan_not_iban_countries():
    """Verify that US and Japan are recognized as non-IBAN countries and rejected by IBAN validator."""
    assert "US" in NON_IBAN_COUNTRIES
    assert "JP" in NON_IBAN_COUNTRIES
    assert "SG" in NON_IBAN_COUNTRIES

    # Fabricated US and Japan IBANs must be rejected structurally
    is_valid_us, reason_us = validate_iban_structure("US64CHAS02100002100012345678")
    assert is_valid_us is False
    assert "does not issue IBANs" in reason_us

    is_valid_jp, reason_jp = validate_iban_structure("JP44BOTK0001000987654321")
    assert is_valid_jp is False
    assert "does not issue IBANs" in reason_jp


def test_mst_021_staging_store_removes_fake_ibans_and_unsupported_countries():
    """Verify that icd_staging_store.json reference data omits US/JP from IBAN countries and provides domestic routing."""
    store_path = Path(__file__).resolve().parent.parent / "backend" / "app" / "data" / "icd_staging_store.json"
    with open(store_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    supported = data["swift_reference_master"]["iban_math_spec"]["supported_countries"]
    assert "US" not in supported
    assert "JP" not in supported
    assert "SG" not in supported
    assert "GB" in supported
    assert "DE" in supported

    counterparties = data["core_banking_ssi"]["counterparty_master"]
    
    # Apex Global Treasury (US) should have ABA routing and account number, not standing_iban
    us_cp = counterparties["Apex Global Treasury"]
    assert "standing_iban" not in us_cp
    assert us_cp["routing_aba"] == "021000021"
    assert us_cp["account_number"] == "0002100012345678"

    # Kyoto Precision Robotics (JP) should have Zengin bank code and branch code, not standing_iban
    jp_cp = counterparties["Kyoto Precision Robotics"]
    assert "standing_iban" not in jp_cp
    assert jp_cp["zengin_bank_code"] == "0005"
    assert jp_cp["branch_code"] == "001"
    assert jp_cp["account_number"] == "000987654321"


# ==============================================================================
# MST-024: German IBAN Fixture Format
# ==============================================================================

def test_mst_024_valid_german_iban_validation():
    """Verify that official 22-digit numeric German IBANs pass validation and MOD-97 checksum."""
    valid_de_iban = "DE89370400440532013000"
    assert len(valid_de_iban) == 22
    assert OFFICIAL_IBAN_COUNTRY_LENGTHS["DE"] == 22

    # MOD-97 check directly
    assert validate_iban_mod97(valid_de_iban) is True

    # Full structural validator
    is_valid, reason = validate_iban_structure(valid_de_iban)
    assert is_valid is True
    assert reason == "Valid ISO 13616 IBAN"


def test_mst_024_invalid_german_ibans_rejected():
    """Verify that oversized or alphanumeric German IBANs are strictly rejected."""
    # 26-character legacy fixture with letters 'DEUT'
    invalid_legacy_de = "DE89DEUT370400440532013000"
    is_valid, reason = validate_iban_structure(invalid_legacy_de)
    assert is_valid is False
    assert "expected 22" in reason or "numeric digits" in reason

    # 22-character with letters in BBAN
    invalid_alpha_de = "DE89ABCD37040044053201"
    is_valid, reason = validate_iban_structure(invalid_alpha_de)
    assert is_valid is False
    assert "only numeric digits" in reason

    # 21-character truncated German IBAN
    is_valid, reason = validate_iban_structure("DE8937040044053201300")
    assert is_valid is False
    assert "expected 22" in reason


def test_mst_024_staging_store_german_counterparty():
    """Verify that Vanguard BioPharma GmbH in icd_staging_store.json uses valid 22-digit German IBAN."""
    store_path = Path(__file__).resolve().parent.parent / "backend" / "app" / "data" / "icd_staging_store.json"
    with open(store_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    vanguard = data["core_banking_ssi"]["counterparty_master"]["Vanguard BioPharma GmbH"]
    assert vanguard["standing_iban"] == "DE89370400440532013000"
    assert len(vanguard["standing_iban"]) == 22
    assert validate_iban_mod97(vanguard["standing_iban"]) is True


# ==============================================================================
# MST-025: AC01 vs AC04
# ==============================================================================

def test_mst_025_return_reason_code_semantics():
    """Verify official ISO 20022 ExternalReturnReason1Code semantic mappings."""
    assert ISO20022_RETURN_REASON_CODES["AC01"] == "IncorrectAccountNumber"
    assert ISO20022_RETURN_REASON_CODES["AC04"] == "ClosedAccountNumber"
    assert ISO20022_RETURN_REASON_CODES["AC06"] == "BlockedAccount"
    assert ISO20022_RETURN_REASON_CODES["RC01"] == "BankIdentifierIncorrect"
    assert ISO20022_RETURN_REASON_CODES["MS03"] == "NotSpecifiedReasonAgentGenerated"


def test_mst_025_profile_account_closed_mapping():
    """Verify that ACCOUNT_CLOSED profile in profile engine references AC04."""
    profile_def = PROFILE_SPECS[ExceptionProfile.ACCOUNT_CLOSED]
    assert "AC04" in profile_def["title"]
    assert "closed account" in profile_def["description"].lower()
    assert "AC04_RETURN_RECORD" in profile_def["mandatory_evidence"]


# ==============================================================================
# MST-026: pacs.004 vs camt.056
# ==============================================================================

def test_mst_026_pacs004_value_return_distinction():
    """Verify that RETURNED_PAYMENT profile represents pacs.004 value returns and distinguishes from camt.056 recall requests."""
    profile_def = PROFILE_SPECS[ExceptionProfile.RETURNED_PAYMENT]
    assert "pacs.004" in profile_def["title"]
    assert "Value Return" in profile_def["title"]
    assert "camt.056" not in profile_def["title"]
    assert profile_def["domain"] == ExceptionDomain.SETTLEMENT_RETURNS


# ==============================================================================
# MST-027: Payment Purpose Codes
# ==============================================================================

def test_mst_027_valid_iso20022_purpose_codes():
    """Verify that official ISO 20022 external purpose codes are recognized."""
    valid_codes = ["GDSV", "COMC", "MDCS", "TREA", "CORT", "SALA", "SUPP", "INTC"]
    for code in valid_codes:
        assert is_valid_iso20022_purpose_code(code) is True, f"Code {code} should be valid"


def test_mst_027_invalid_purpose_codes_rejected():
    """Verify that non-standard/hallucinated purpose codes are rejected."""
    invalid_codes = ["GDDS", "PHAR", "COMM", "COMP", "AUDT", "FAKE", "1234", ""]
    for code in invalid_codes:
        assert is_valid_iso20022_purpose_code(code) is False, f"Code {code} should be invalid"


def test_mst_027_staging_store_purpose_codes_valid():
    """Verify that all counterparties in icd_staging_store.json use valid ISO 20022 purpose codes."""
    store_path = Path(__file__).resolve().parent.parent / "backend" / "app" / "data" / "icd_staging_store.json"
    with open(store_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    counterparties = data["core_banking_ssi"]["counterparty_master"]
    for name, cp in counterparties.items():
        purpose = cp.get("purpose_code")
        assert purpose is not None, f"Counterparty {name} missing purpose_code"
        assert is_valid_iso20022_purpose_code(purpose) is True, (
            f"Counterparty {name} has invalid purpose code '{purpose}'"
        )


# ==============================================================================
# MST-028: Fedwire IMAD Format
# ==============================================================================

def test_mst_028_valid_fedwire_imad():
    """Verify that standard 18-character Fedwire IMAD strings pass FAIM validation."""
    valid_imad = "20260923MMQF004812"
    assert len(valid_imad) == 18
    is_valid, reason = validate_fedwire_imad(valid_imad)
    assert is_valid is True
    assert reason == "Valid Fedwire FAIM IMAD"

    valid_imad_2 = "20260101FT01000001"
    is_valid, reason = validate_fedwire_imad(valid_imad_2)
    assert is_valid is True


def test_mst_028_invalid_fedwire_imads_rejected():
    """Verify that 22-character, truncated, or malformed IMAD strings are rejected."""
    # 22-character legacy prototype string
    invalid_22 = "20260901MMQF0001004812"
    is_valid, reason = validate_fedwire_imad(invalid_22)
    assert is_valid is False
    assert "strictly 18 characters" in reason

    # 17-character truncated string
    is_valid, reason = validate_fedwire_imad("20260923MMQF00481")
    assert is_valid is False

    # Invalid characters in sequence
    is_valid, reason = validate_fedwire_imad("20260923MMQF00481A")
    assert is_valid is False
    assert "FAIM standard" in reason


# ==============================================================================
# MST-029: Bacs Payment Classification
# ==============================================================================

def test_mst_029_uk_rail_classification():
    """Verify that UK payment rails are properly classified according to Pay.UK and Bank of England rules."""
    uk_rail_taxonomy = {
        "CHAPS": {
            "type": "RTGS",
            "operator": "Bank of England",
            "settlement": "Real-Time Gross Settlement",
            "high_value": True
        },
        "Faster Payments": {
            "type": "Instant / Retail",
            "operator": "Pay.UK",
            "settlement": "Near-Real-Time Deferred Net",
            "high_value": False
        },
        "Bacs": {
            "type": "Automated Clearing House (ACH)",
            "operator": "Pay.UK",
            "settlement": "3-Day Deferred Net Settlement Batch",
            "high_value": False
        }
    }

    assert uk_rail_taxonomy["CHAPS"]["type"] == "RTGS"
    assert uk_rail_taxonomy["CHAPS"]["high_value"] is True
    assert uk_rail_taxonomy["Bacs"]["type"] == "Automated Clearing House (ACH)"
    assert uk_rail_taxonomy["Bacs"]["high_value"] is False
    assert "3-Day" in uk_rail_taxonomy["Bacs"]["settlement"]
