"""Reference lookups PeX can run itself (evidence acquisition mode 2).

Nine lookups, each for a real evidence type in the "Reference data" category.
  COMPUTED             the answer comes from a published rule (IBAN check digits, routing-number checksum, character set,
                       ISO purpose codes, rail holiday rules). No data feed is involved.
  SIMULATED_DIRECTORY  the real source is licensed or live (SwiftRef, the Fed routing directory, ...). PeX answers from a small
                       seeded sample table, and every answer says so.

Nothing in the live case flow calls these yet. They exist so the integration contract can state truthfully what PeX could fetch.
A lookup never raises on bad input: it returns a result that says what was wrong. An unknown evidence type is a LookupError.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, Optional, Tuple

SEEDED = "2026-11-05 (seeded sample)"


@dataclass(frozen=True)
class Connector:
    evidence_type: str
    name: str
    kind: str                      # COMPUTED | SIMULATED_DIRECTORY
    source: str
    as_of: str
    params: Tuple[str, ...]
    fn: Callable[..., Dict[str, Any]]


def _s(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ""


# ---- IBAN structure ---------------------------------------------------------------------------------------------
IBAN_LENGTH = {
    "AD": 24, "AE": 23, "AL": 28, "AT": 20, "AZ": 28, "BA": 20, "BE": 16, "BG": 22, "BH": 22, "BR": 29, "BY": 28, "CH": 21, "CR": 22, "CY": 28,
    "CZ": 24, "DE": 22, "DK": 18, "DO": 28, "EE": 20, "EG": 29, "ES": 24, "FI": 18, "FO": 18, "FR": 27, "GB": 22, "GE": 22, "GI": 23, "GL": 18,
    "GR": 27, "GT": 28, "HR": 21, "HU": 28, "IE": 22, "IL": 23, "IQ": 23, "IS": 26, "IT": 27, "JO": 30, "KW": 30, "KZ": 20, "LB": 28, "LC": 32,
    "LI": 21, "LT": 20, "LU": 20, "LV": 21, "MC": 27, "MD": 24, "ME": 22, "MK": 19, "MR": 27, "MT": 31, "MU": 30, "NL": 18, "NO": 15, "PK": 24,
    "PL": 28, "PS": 29, "PT": 25, "QA": 29, "RO": 24, "RS": 22, "SA": 24, "SC": 31, "SE": 24, "SI": 19, "SK": 24, "SM": 27, "ST": 25, "SV": 28,
    "TL": 23, "TN": 24, "TR": 26, "UA": 29, "VA": 22, "VG": 24, "XK": 20,
}


def _iban(iban: Any = None) -> Dict[str, Any]:
    raw = re.sub(r"\s+", "", _s(iban)).upper()
    if not raw:
        return {"valid": False, "country": None, "expected_length": None, "length_ok": False, "checksum_ok": False, "reason": "No IBAN given."}
    cc = raw[:2]
    exp = IBAN_LENGTH.get(cc)
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", raw):
        return {"valid": False, "country": cc, "expected_length": exp, "length_ok": False, "checksum_ok": False, "reason": "Not in IBAN format (2 letters, 2 digits, then letters or digits)."}
    if exp is None:
        return {"valid": False, "country": cc, "expected_length": None, "length_ok": False, "checksum_ok": False, "reason": f"Country {cc} is not in the IBAN length table used here."}
    length_ok = len(raw) == exp
    moved = raw[4:] + raw[:4]
    num = "".join(str(int(ch, 36)) for ch in moved)
    checksum_ok = int(num) % 97 == 1
    reason = None if length_ok and checksum_ok else (f"{cc} IBANs are {exp} characters; this one is {len(raw)}." if not length_ok else "The check digits do not match (mod 97).")
    return {"valid": length_ok and checksum_ok, "country": cc, "expected_length": exp, "length_ok": length_ok, "checksum_ok": checksum_ok, "reason": reason}


# ---- routing-code syntax ----------------------------------------------------------------------------------------
def _routing(routing_number: Any = None, sort_code: Any = None) -> Dict[str, Any]:
    if routing_number is not None and not isinstance(routing_number, str):
        routing_number = str(routing_number) if isinstance(routing_number, int) and not isinstance(routing_number, bool) else ""
    if _s(routing_number) or (routing_number is not None and not _s(sort_code)):
        n = _s(routing_number)
        if not re.fullmatch(r"\d{9}", n):
            return {"valid": False, "scheme": "ABA", "reason": "A US routing number has 9 digits."}
        d = [int(c) for c in n]
        ok = (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])) % 10 == 0
        return {"valid": ok, "scheme": "ABA", "reason": None if ok else "The routing number checksum (3-7-1) does not match."}
    sc = re.sub(r"[\s-]", "", _s(sort_code))
    if sort_code is not None:
        ok = bool(re.fullmatch(r"\d{6}", sc))
        return {"valid": ok, "scheme": "UK_SORT_CODE", "reason": None if ok else "A UK sort code has 6 digits."}
    return {"valid": False, "scheme": None, "reason": "No routing number or sort code given."}


# ---- character set ----------------------------------------------------------------------------------------------
_CHARSET = re.compile(r"[A-Za-z0-9/\-?:().,'+ ]")


def _charset(text: Any = None) -> Dict[str, Any]:
    bad = []
    for ch in _s(text) if isinstance(text, str) else "":
        if not _CHARSET.fullmatch(ch) and ch not in bad:
            bad.append(ch)
    return {"valid": not bad, "invalid_characters": bad}


# ---- ISO purpose codes (subset) ---------------------------------------------------------------------------------
PURPOSE = {
    "SALA": "Salary payment", "SUPP": "Supplier payment", "TRAD": "Trade services", "INTC": "Intra-company payment", "GDDS": "Purchase or sale of goods",
    "SCVE": "Purchase or sale of services", "TAXS": "Tax payment", "PENS": "Pension payment", "DIVI": "Dividend", "LOAN": "Loan", "RENT": "Rent",
    "CHAR": "Charity payment", "GOVT": "Government payment", "EDUC": "Education", "MDCS": "Medical services", "INSU": "Insurance premium",
    "COMM": "Commission", "CASH": "Cash management transfer", "TREA": "Treasury payment", "SECU": "Securities", "BONU": "Bonus payment",
    "ALMY": "Alimony payment", "ELEC": "Electricity bill", "GASB": "Gas bill", "WTER": "Water bill", "TCSC": "Town council service charges",
    "ADVA": "Advance payment", "AGRT": "Agricultural transfer", "BEXP": "Business expenses", "CBTV": "Cable TV bill", "CCRD": "Credit card payment",
    "DCRD": "Debit card payment", "FEES": "Payment of fees", "INTE": "Interest", "LICF": "License fee", "OTHR": "Other",
}


def _purpose(purpose_code: Any = None) -> Dict[str, Any]:
    c = _s(purpose_code).upper()
    return {"valid": c in PURPOSE, "code": c or None, "meaning": PURPOSE.get(c), "note": f"Subset of the ISO 20022 external purpose list ({len(PURPOSE)} codes)."}


# ---- rail calendars ---------------------------------------------------------------------------------------------
def _easter(y: int) -> date:
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mo = (h + l - 7 * m + 114) // 31
    da = ((h + l - 7 * m + 114) % 31) + 1
    return date(y, mo, da)


def _nth_weekday(y: int, month: int, weekday: int, n: int) -> date:
    d = date(y, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_weekday(y: int, month: int, weekday: int) -> date:
    d = date(y, month + 1, 1) - timedelta(days=1) if month < 12 else date(y, 12, 31)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _target_holidays(y: int) -> Dict[date, str]:
    e = _easter(y)
    return {date(y, 1, 1): "New Year's Day", e - timedelta(days=2): "Good Friday", e + timedelta(days=1): "Easter Monday", date(y, 5, 1): "Labour Day (1 May)",
            date(y, 12, 25): "Christmas Day", date(y, 12, 26): "Christmas holiday (26 December)"}


def _fed_holidays(y: int) -> Dict[date, str]:
    h: Dict[date, str] = {}
    for d, name in ((date(y, 1, 1), "New Year's Day"), (date(y, 6, 19), "Juneteenth"), (date(y, 7, 4), "Independence Day"), (date(y, 11, 11), "Veterans Day"), (date(y, 12, 25), "Christmas Day")):
        if d.weekday() == 6:                         # Sunday is observed on the Monday; a Saturday holiday is not moved
            h[d + timedelta(days=1)] = f"{name} (observed)"
        elif d.weekday() < 5:
            h[d] = name
    h[_nth_weekday(y, 1, 0, 3)] = "Martin Luther King Jr. Day"
    h[_nth_weekday(y, 2, 0, 3)] = "Washington's Birthday"
    h[_last_weekday(y, 5, 0)] = "Memorial Day"
    h[_nth_weekday(y, 9, 0, 1)] = "Labor Day"
    h[_nth_weekday(y, 10, 0, 2)] = "Columbus Day"
    h[_nth_weekday(y, 11, 3, 4)] = "Thanksgiving Day"
    return h


def _calendar(rail: Any = None, date: Any = None) -> Dict[str, Any]:  # noqa: A002 (parameter name is part of the lookup contract)
    r = _s(rail).upper()
    out: Dict[str, Any] = {"rail": r or None, "date": date if isinstance(date, str) else None, "open": None, "reason": ""}
    if r not in ("TARGET", "FEDWIRE"):
        out["reason"] = "Rail not covered. This lookup knows TARGET and FEDWIRE."
        return out
    try:
        d = datetime.strptime(_s(date), "%Y-%m-%d").date()
    except ValueError:
        out["reason"] = "Date must be YYYY-MM-DD."
        return out
    if d.weekday() >= 5:
        out.update(open=False, reason="Saturday: not a business day." if d.weekday() == 5 else "Sunday: not a business day.")
        return out
    hol = (_target_holidays(d.year) if r == "TARGET" else _fed_holidays(d.year)).get(d)
    out.update(open=hol is None, reason=f"Closed: {hol}." if hol else "Business day.")
    return out


# ---- simulated directories --------------------------------------------------------------------------------------
BIC_DIR = {
    "NWBKGB2L": ("NATIONAL WESTMINSTER BANK PLC", "GB", "ACTIVE"), "DEUTDEFF": ("DEUTSCHE BANK AG", "DE", "ACTIVE"),
    "CHASUS33": ("JPMORGAN CHASE BANK, N.A.", "US", "ACTIVE"), "BNPAFRPP": ("BNP PARIBAS", "FR", "ACTIVE"),
    "CITIGB2L": ("CITIBANK N.A. LONDON", "GB", "ACTIVE"), "HSBCGB2L": ("HSBC UK BANK PLC", "GB", "ACTIVE"),
    "BOFAUS3N": ("BANK OF AMERICA, N.A.", "US", "ACTIVE"), "MIDLGB22": ("HSBC BANK PLC", "GB", "ACTIVE"),
    "OLDBGB2L": ("SAMPLE CLOSED BANK PLC", "GB", "CLOSED"),
}
ABA_DIR = {"021000021": ("JPMORGAN CHASE BANK, N.A.", "ACTIVE"), "026009593": ("BANK OF AMERICA, N.A.", "ACTIVE"), "121000248": ("WELLS FARGO BANK, N.A.", "ACTIVE")}
SORT_DIR = {"400515": ("HSBC UK BANK PLC", "ACTIVE"), "200000": ("BARCLAYS BANK UK PLC", "ACTIVE")}


def _bic_syntax(b: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?", b))


def _bic(bic: Any = None) -> Dict[str, Any]:
    b = _s(bic).upper()
    ok = _bic_syntax(b)
    key = b[:8] if ok else ""
    hit = BIC_DIR.get(key)
    return {"found": bool(hit), "syntax_ok": ok, "bic": b or None, "institution": hit[0] if hit else None, "country": hit[1] if hit else None, "status": hit[2] if hit else None}


def _fedline(routing_number: Any = None) -> Dict[str, Any]:
    n = re.sub(r"\D", "", _s(routing_number))
    hit = ABA_DIR.get(n)
    return {"found": bool(hit), "routing_number": n or None, "institution": hit[0] if hit else None, "status": hit[1] if hit else None}


def _any_code(code: str) -> Dict[str, Any]:
    c = re.sub(r"[\s-]", "", code).upper()
    if c in ABA_DIR:
        return {"found": True, "code": c, "scheme": "ABA", "institution": ABA_DIR[c][0], "status": ABA_DIR[c][1], "authority": "Fed e-Payments Routing Directory (simulated)"}
    if c in SORT_DIR:
        return {"found": True, "code": c, "scheme": "UK_SORT_CODE", "institution": SORT_DIR[c][0], "status": SORT_DIR[c][1], "authority": "UK sort code directory (simulated)"}
    b = _bic(c)
    if b["found"]:
        return {"found": True, "code": c, "scheme": "BIC", "institution": b["institution"], "status": b["status"], "authority": "SwiftRef BIC directory (simulated)"}
    return {"found": False, "code": c or None, "scheme": None, "institution": None, "status": None, "authority": None}


def _routing_dir(routing_code: Any = None) -> Dict[str, Any]:
    r = _any_code(_s(routing_code))
    r.pop("authority", None)
    return r


def _routing_authority(routing_code: Any = None) -> Dict[str, Any]:
    return _any_code(_s(routing_code))


_C = Connector
REGISTRY: Dict[str, Connector] = {c.evidence_type: c for c in (
    _C("ACCOUNT_STRUCTURE_RULES", "IBAN structure check", "COMPUTED", "IBAN length table and ISO 13616 mod-97 check digits", f"Published rules (subset of {len(IBAN_LENGTH)} countries)", ("iban",), _iban),
    _C("ROUTING_SYNTAX_MASTER", "Routing-code format check", "COMPUTED", "US routing number 3-7-1 checksum; UK sort code format", "Published rules (no data feed)", ("routing_number", "sort_code"), _routing),
    _C("TARGET_SCHEME_CHARSET_SPEC", "TARGET character set check", "COMPUTED", "SEPA and TARGET basic Latin character set", "Published rules (no data feed)", ("text",), _charset),
    _C("APPLICABLE_PURPOSE_CODE_SET", "ISO purpose code check", "COMPUTED", "ISO 20022 external purpose code list", f"Subset of {len(PURPOSE)} codes", ("purpose_code",), _purpose),
    _C("RAIL_OPERATING_CALENDAR", "Rail business-day check", "COMPUTED", "TARGET and Fedwire published holiday rules", "Published rules, TARGET and FEDWIRE only", ("rail", "date"), _calendar),
    _C("BIC_REFERENCE_DIRECTORY", "BIC directory lookup", "SIMULATED_DIRECTORY", "SwiftRef BIC directory (simulated sample table)", SEEDED, ("bic",), _bic),
    _C("FEDLINE_ROUTING_DIRECTORY", "Fedwire routing directory lookup", "SIMULATED_DIRECTORY", "Fed e-Payments Routing Directory (simulated sample table)", SEEDED, ("routing_number",), _fedline),
    _C("ROUTING_DIRECTORY", "Routing and bank directory lookup", "SIMULATED_DIRECTORY", "Routing and bank directory (simulated sample table)", SEEDED, ("routing_code",), _routing_dir),
    _C("ROUTING_DIRECTORY_AUTHORITY", "Routing directory authority lookup", "SIMULATED_DIRECTORY", "Routing directory with its authority (simulated sample table)", SEEDED, ("routing_code",), _routing_authority),
)}


def lookup(evidence_type: str, **params: Any) -> Dict[str, Any]:
    c = REGISTRY.get(evidence_type)
    if c is None:
        raise LookupError(f"No lookup is built for evidence type {evidence_type!r}.")
    allowed = {k: v for k, v in params.items() if k in c.params}
    return {"evidence_type": c.evidence_type, "name": c.name, "kind": c.kind, "source": c.source, "as_of": c.as_of, "params": list(c.params), "result": c.fn(**allowed)}
