"""Reference lookups PeX can run itself (acquisition mode 2). Acceptance tests written from the requirements.

  C1  Nine lookups exist. Five are COMPUTED from a published rule, four are SIMULATED_DIRECTORY (seeded sample data, labelled).
  C2  Every lookup is for a real evidence type from the semantic layer, in the "Reference data" category.
  C3  Computed lookups give the right answer for known-good and known-bad inputs.
  C4  Simulated lookups say so in every answer and carry an as-of date.
  C5  A lookup never raises on bad input: it returns a clear result. An unknown evidence type is an error.
"""
import pytest

from app.services import reference_connectors as rc
from app.services.v2 import semantic_data as sd

COMPUTED = {"ACCOUNT_STRUCTURE_RULES", "ROUTING_SYNTAX_MASTER", "TARGET_SCHEME_CHARSET_SPEC", "APPLICABLE_PURPOSE_CODE_SET", "RAIL_OPERATING_CALENDAR"}
SIMULATED = {"BIC_REFERENCE_DIRECTORY", "FEDLINE_ROUTING_DIRECTORY", "ROUTING_DIRECTORY", "ROUTING_DIRECTORY_AUTHORITY"}


def test_c1_nine_lookups_five_computed_four_simulated():
    assert set(rc.REGISTRY) == COMPUTED | SIMULATED and len(rc.REGISTRY) == 9
    assert {k for k, c in rc.REGISTRY.items() if c.kind == "COMPUTED"} == COMPUTED
    assert {k for k, c in rc.REGISTRY.items() if c.kind == "SIMULATED_DIRECTORY"} == SIMULATED


def test_c2_every_lookup_is_a_real_reference_evidence_type():
    for k, c in rc.REGISTRY.items():
        assert k in sd.EVIDENCE and sd.EVIDENCE[k][0] == sd.REF, k
        assert c.name and c.source and c.params and c.as_of


# C3 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("iban", ["GB29NWBK60161331926819", "DE89370400440532013000", "FR1420041010050500013M02606", "ES9121000418450200051332",
                                  "IT60X0542811101000000123456", "NL91ABNA0417164300", "BE68539007547034", "CH9300762011623852957",
                                  "AT611904300234573201", "IE29AIBK93115212345678", "LU280019400644750000", "PT50000201231234567890154",
                                  "SE4550000000058398257466", "NO9386011117947", "DK5000400440116243", "FI2112345600000785",
                                  "PL61109010140000071219812874", "CZ6508000000192000145399", "HU42117730161111101800000000", "GR1601101250000000012300695"])
def test_c3_valid_ibans(iban):
    r = rc.lookup("ACCOUNT_STRUCTURE_RULES", iban=iban)["result"]
    assert r["valid"] is True and r["length_ok"] and r["checksum_ok"] and r["country"] == iban[:2]


@pytest.mark.parametrize("iban,why", [("GB29NWBK60161331926818", "checksum"), ("GB29NWBK6016133192681", "length"), ("XX0012345", "country"), ("", "empty"), ("GB29 NWBK 6016 1331 9268 19", None)])
def test_c3_invalid_or_spaced_ibans(iban, why):
    r = rc.lookup("ACCOUNT_STRUCTURE_RULES", iban=iban)["result"]
    if why is None:
        assert r["valid"] is True  # spaces are print formatting and are ignored
    else:
        assert r["valid"] is False and r["reason"]


@pytest.mark.parametrize("n,ok", [("011000015", True), ("021000021", True), ("026009593", True), ("011000016", False), ("12345678", False), ("abcdefghi", False)])
def test_c3_aba_routing_numbers(n, ok):
    r = rc.lookup("ROUTING_SYNTAX_MASTER", routing_number=n)["result"]
    assert r["valid"] is ok and r["scheme"] == "ABA"


@pytest.mark.parametrize("sc,ok", [("40-05-15", True), ("400515", True), ("40051", False), ("40-05-1A", False)])
def test_c3_uk_sort_codes(sc, ok):
    r = rc.lookup("ROUTING_SYNTAX_MASTER", sort_code=sc)["result"]
    assert r["valid"] is ok and r["scheme"] == "UK_SORT_CODE"


def test_c3_charset():
    assert rc.lookup("TARGET_SCHEME_CHARSET_SPEC", text="ACME Ltd. - Invoice 12/34 (EUR)")["result"] == {"valid": True, "invalid_characters": []}
    r = rc.lookup("TARGET_SCHEME_CHARSET_SPEC", text="Müller & Söhne #7")["result"]
    assert r["valid"] is False and set(r["invalid_characters"]) == {"ü", "&", "ö", "#"}


@pytest.mark.parametrize("code,ok", [("SALA", True), ("SUPP", True), ("TRAD", True), ("TAXS", True), ("sala", True), ("ZZZZ", False), ("", False)])
def test_c3_purpose_codes(code, ok):
    r = rc.lookup("APPLICABLE_PURPOSE_CODE_SET", purpose_code=code)["result"]
    assert r["valid"] is ok and (r["meaning"] if ok else True)


@pytest.mark.parametrize("rail,date,open_,why", [
    ("TARGET", "2026-04-03", False, "Good Friday"), ("TARGET", "2026-04-06", False, "Easter Monday"), ("TARGET", "2026-05-01", False, "Labour Day"),
    ("TARGET", "2026-12-25", False, "Christmas"), ("TARGET", "2025-12-26", False, "Christmas"), ("TARGET", "2026-01-01", False, "New Year"),
    ("TARGET", "2026-11-14", False, "Saturday"), ("TARGET", "2026-11-16", True, None), ("TARGET", "2026-11-26", True, None),
    ("FEDWIRE", "2026-11-26", False, "Thanksgiving"), ("FEDWIRE", "2026-12-25", False, "Christmas"), ("FEDWIRE", "2026-07-03", True, None),
    ("FEDWIRE", "2026-07-04", False, "Saturday"), ("FEDWIRE", "2026-01-19", False, "Martin Luther King"), ("FEDWIRE", "2026-11-16", True, None),
    ("FEDWIRE", "2027-07-05", False, "Independence"),
])
def test_c3_rail_calendars(rail, date, open_, why):
    r = rc.lookup("RAIL_OPERATING_CALENDAR", rail=rail, date=date)["result"]
    assert r["open"] is open_
    if why:
        assert why.lower() in r["reason"].lower()


# C4 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("etype,params", [("BIC_REFERENCE_DIRECTORY", {"bic": "NWBKGB2L"}), ("FEDLINE_ROUTING_DIRECTORY", {"routing_number": "021000021"}),
                                          ("ROUTING_DIRECTORY", {"routing_code": "NWBKGB2L"}), ("ROUTING_DIRECTORY_AUTHORITY", {"routing_code": "021000021"})])
def test_c4_simulated_directories_found(etype, params):
    a = rc.lookup(etype, **params)
    assert a["kind"] == "SIMULATED_DIRECTORY" and a["as_of"] and "simulated" in a["source"].lower()
    assert a["result"]["found"] is True and a["result"]["institution"] and a["result"]["status"] == "ACTIVE"


@pytest.mark.parametrize("etype,params", [("BIC_REFERENCE_DIRECTORY", {"bic": "ZZZZZZ2L"}), ("BIC_REFERENCE_DIRECTORY", {"bic": "BAD"}),
                                          ("FEDLINE_ROUTING_DIRECTORY", {"routing_number": "999999999"}), ("ROUTING_DIRECTORY", {"routing_code": "nope"})])
def test_c4_simulated_directories_not_found(etype, params):
    a = rc.lookup(etype, **params)
    assert a["result"]["found"] is False and a["kind"] == "SIMULATED_DIRECTORY"


def test_c4_bic_syntax_is_checked_separately():
    assert rc.lookup("BIC_REFERENCE_DIRECTORY", bic="NWBKGB2L")["result"]["syntax_ok"] is True
    assert rc.lookup("BIC_REFERENCE_DIRECTORY", bic="BAD")["result"]["syntax_ok"] is False


# C5 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("etype", sorted(COMPUTED | SIMULATED))
def test_c5_no_params_never_raises(etype):
    a = rc.lookup(etype)
    assert a["evidence_type"] == etype and "result" in a


@pytest.mark.parametrize("bad", [None, 123, [], {}])
def test_c5_odd_inputs_do_not_raise(bad):
    for etype, key in (("ACCOUNT_STRUCTURE_RULES", "iban"), ("ROUTING_SYNTAX_MASTER", "routing_number"), ("BIC_REFERENCE_DIRECTORY", "bic")):
        assert rc.lookup(etype, **{key: bad})["result"]


def test_c5_bad_dates_and_rails_are_results_not_crashes():
    assert rc.lookup("RAIL_OPERATING_CALENDAR", rail="TARGET", date="not-a-date")["result"]["open"] is None
    assert rc.lookup("RAIL_OPERATING_CALENDAR", rail="MOON", date="2026-01-02")["result"]["open"] is None


def test_c5_unknown_evidence_type_is_an_error():
    with pytest.raises(LookupError):
        rc.lookup("NOPE_NOT_REAL")
