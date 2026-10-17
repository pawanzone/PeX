"""Deterministic synthetic payment-exception batch generator (demo / load testing).

All data is fabricated: company names are fictional, IBANs carry *valid ISO 13616 MOD-97 check digits*
(invalid variants are made by digit transposition so a deterministic repair exists), the US has no IBAN
(account number + valid ABA routing number checksum), UETRs are UUIDv4-shaped, no real people.

Record shape == ``CanonicalE2EInput`` so every line goes straight through the canonical pipeline.
Profile mix: ~70% profiles whose resolution logic is implemented inline in the E2E harness
(DQ-01, DQ-08, PR-01, PR-08, ST-01, CO-04), ~30% spread over the other profiles using fixture templates
(``backend/app/data/batch_templates``) with per-record identifiers/amounts re-seeded.
"""
from __future__ import annotations

import copy
import gzip
import json
import random
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "data" / "batch_templates"
BASE_DATE = date(2026, 10, 19)  # a Monday; value dates are deterministic offsets from it

# ----------------------------------------------------------------------------------------------
# IBAN / ABA helpers
# ----------------------------------------------------------------------------------------------

def iban_check_digits(country: str, bban: str) -> str:
    s = bban + country + "00"
    n = int("".join(str(int(c, 36)) for c in s))
    return f"{98 - (n % 97):02d}"


def make_iban(country: str, bban: str) -> str:
    return f"{country}{iban_check_digits(country, bban)}{bban}"


def iban_valid(iban: str) -> bool:
    iban = iban.replace(" ", "").upper()
    if len(iban) < 15 or not iban[:2].isalpha():
        return False
    s = iban[4:] + iban[:4]
    try:
        return int("".join(str(int(c, 36)) for c in s)) % 97 == 1
    except ValueError:
        return False


def transpose_invalid(iban: str, rng: random.Random) -> str:
    """Swap two adjacent *different* characters in the BBAN part until MOD-97 fails (a typical keying error)."""
    chars = list(iban)
    idxs = list(range(len(iban) - 2, 4, -1))
    rng.shuffle(idxs)
    for i in idxs:
        if chars[i] != chars[i + 1] and chars[i].isdigit() and chars[i + 1].isdigit():
            c2 = chars[:]
            c2[i], c2[i + 1] = c2[i + 1], c2[i]
            cand = "".join(c2)
            if not iban_valid(cand):
                return cand
    raise ValueError("could not build invalid IBAN")


def aba_valid(r: str) -> bool:
    if len(r) != 9 or not r.isdigit():
        return False
    d = [int(c) for c in r]
    return (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])) % 10 == 0


def aba_transposed(r: str) -> str:
    for i in range(8, 0, -1):
        if r[i] != r[i - 1]:
            c = list(r)
            c[i], c[i - 1] = c[i - 1], c[i]
            cand = "".join(c)
            if not aba_valid(cand):
                return cand
    raise ValueError("no invalid transposition")


def _digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


def _fr_rib_key(bank: str, branch: str, acct: str) -> str:
    def conv(s):
        out = ""
        for ch in s:
            if ch.isdigit():
                out += ch
            else:
                out += "123456789123456789234567890123456789"[ord(ch.upper()) - 65]
        return int(out)
    return f"{97 - ((89 * conv(bank) + 15 * conv(branch) + 3 * conv(acct)) % 97):02d}"


GEO_BANKS = {
    "GB": [("NWBK", "601613", "NWBKGB2LXXX"), ("BARC", "200000", "BARCGB22XXX"), ("HBUK", "400515", "HBUKGB4BXXX"), ("LOYD", "309634", "LOYDGB2LXXX")],
    "DE": [("37040044", "COBADEFFXXX"), ("50010517", "INGDDEFFXXX"), ("10070000", "DEUTDEBBXXX"), ("76026000", "HYVEDEMM473")],
    "FR": [("30004", "00828", "BNPAFRPPXXX"), ("30003", "03620", "SOGEFRPPXXX"), ("30006", "00011", "AGRIFRPPXXX")],
    "NL": [("INGB", "INGBNL2AXXX"), ("ABNA", "ABNANL2AXXX"), ("RABO", "RABONL2UXXX")],
    "ES": [("0049", "1500", "BSCHESMMXXX"), ("0182", "5566", "BBVAESMMXXX"), ("2100", "0418", "CAIXESBBXXX")],
    "IT": [("05428", "11101", "BPBAIT3BXXX"), ("03069", "09606", "BCITITMMXXX"), ("02008", "05364", "UNCRITMMXXX")],
}
US_BANKS = [("021000021", "CHASUS33XXX", "JPMorgan Chase Bank, N.A."), ("026009593", "BOFAUS3NXXX", "Bank of America, N.A."),
            ("021000089", "CITIUS33XXX", "Citibank, N.A."), ("121000248", "WFBIUS6SXXX", "Wells Fargo Bank, N.A.")]

EU_COUNTRIES = ["DE", "FR", "NL", "ES", "IT"]


def gen_iban(country: str, rng: random.Random) -> Tuple[str, str, str]:
    """Return (iban, bic, bank_ref) with valid MOD-97."""
    if country == "GB":
        code, sort, bic = rng.choice(GEO_BANKS["GB"])
        bban = code + sort + _digits(rng, 8)
        return make_iban("GB", bban), bic, sort
    if country == "DE":
        blz, bic = rng.choice(GEO_BANKS["DE"])
        return make_iban("DE", blz + _digits(rng, 10)), bic, blz
    if country == "FR":
        bank, branch, bic = rng.choice(GEO_BANKS["FR"])
        acct = _digits(rng, 11)
        return make_iban("FR", bank + branch + acct + _fr_rib_key(bank, branch, acct)), bic, bank
    if country == "NL":
        code, bic = rng.choice(GEO_BANKS["NL"])
        return make_iban("NL", code + _digits(rng, 10)), bic, code
    if country == "ES":
        bank, branch, bic = rng.choice(GEO_BANKS["ES"])
        return make_iban("ES", bank + branch + "00" + _digits(rng, 10)), bic, bank
    if country == "IT":
        abi, cab, bic = rng.choice(GEO_BANKS["IT"])
        return make_iban("IT", "X" + abi + cab + _digits(rng, 12)), bic, abi
    raise ValueError(country)


# ----------------------------------------------------------------------------------------------
# Name pools (fictional)
# ----------------------------------------------------------------------------------------------
_NAMES = {
    "GB": ["Harlow & Finch Components Ltd", "Brightwater Logistics Ltd", "Calder Valley Foods PLC", "Northgate Precision Tooling Ltd", "Kestrel Marine Services Ltd", "Pennine Packaging Ltd", "Marlowe Biotech Ltd", "Thistledown Energy Ltd"],
    "US": ["Cobalt Ridge Manufacturing Inc", "Lakeshore Freight Systems LLC", "Redwood Analytics Corp", "Summit Peak Foods Inc", "Ironbridge Fabrication LLC", "Bluepine Medical Supply Inc", "Westmark Agricultural Co", "Granite Harbor Shipping Corp"],
    "DE": ["Rheinwerk Maschinenbau GmbH", "Bavaria Engine Works AG", "Nordlicht Verpackungen GmbH", "Elbe Chemie GmbH", "Schwarzwald Optik GmbH", "Hansa Logistik AG"],
    "FR": ["Atelier Lumière SAS", "Provence Agro SARL", "Loire Composants SA", "Marais Textiles SAS", "Côte d'Azur Marine SARL", "Bretagne Froid SAS"],
    "NL": ["Delta Kaas BV", "Rijnmond Havenservice BV", "Tulp Techniek BV", "Maasstad Bouw BV", "Zaanse Verf BV", "Amstel Datacenters BV"],
    "ES": ["Costa Dorada Cítricos SL", "Ibérica de Componentes SA", "Sierra Nevada Energía SL", "Levante Cerámica SL", "Navarra Conservas SA"],
    "IT": ["Brianza Tessuti SpA", "Adriatica Meccanica Srl", "Tirreno Olio Srl", "Piemonte Cioccolato SpA", "Lombarda Utensili Srl"],
}
_DEBTORS = ["Apex Global Treasury", "Meridian Holdings Treasury", "Orion Industrial Group", "Valence Retail Group", "Quantum Freight Holdings", "Aurelia Pharma Group"]
_REMIT = ["INV-{y}-{n:05d}", "PO {n:06d} SETTLEMENT", "SUPPLY CONTRACT {n:05d}", "INVOICE {n:07d}", "ORDER {n:06d} FINAL PAYMENT"]


def _name(rng, country):
    return rng.choice(_NAMES.get(country, _NAMES["GB"]))


def _amount(rng, small=True):
    if small:
        return round(rng.uniform(250, 9500), 2)
    return round(rng.uniform(10500, 320000), 2)


# ----------------------------------------------------------------------------------------------
# Context + builders
# ----------------------------------------------------------------------------------------------
class Ctx:
    def __init__(self, tag: str, seed: int, i: int, rng: random.Random):
        self.tag, self.seed, self.i, self.rng = tag, seed, i, rng

    def ids(self, code: str, suffix: str = ""):
        eid = f"PEX-{self.tag}-{code}-{self.i:07d}{suffix}"
        u = uuid.UUID(int=self.rng.getrandbits(128), version=4)
        return eid, f"PMT-{self.seed:04d}-{self.i:07d}", str(u)

    def remit(self):
        return self.rng.choice(_REMIT).format(y=2026, n=self.rng.randint(1, 999999))

    def vdate(self):
        d = BASE_DATE + timedelta(days=self.i % 5)
        return d.isoformat()


def _base(c: Ctx, code, profile, domain, err, msg, rail, ccy, amount, debtor, creditor, ext_ev=None, bank_ev=None,
          derived=None, hist=None, suffix="", extra_pay=None):
    eid, pid, uetr = c.ids(code, suffix)
    pay = {"payment_id": pid, "uetr": uetr, "amount": amount, "currency": ccy, "clearing_rail": rail,
           "value_date": c.vdate(), "remittance_info": c.remit()}
    pay.update(debtor)
    pay.update(creditor)
    if extra_pay:
        pay.update(extra_pay)
    return {
        "exception_id": eid, "tenant_id": "DEFAULT_BANK", "profile_id": profile, "domain": domain,
        "error_code": err, "error_message": msg, "payment_info": pay,
        "bank_supplied_evidence": bank_ev or {}, "external_authoritative_evidence": ext_ev or {},
        "derived_evidence": derived or {}, "historical_evidence": hist or {},
        "evidence_provenance": "NON_PRODUCTION_DEMO", "test_status": "TEST_ONLY",
    }


def _party_debtor(c: Ctx, geo: str):
    rng = c.rng
    if geo == "US":
        rt, bic, _bn = rng.choice(US_BANKS)[0:3]
        return {"debtor_name": rng.choice(_DEBTORS) + " (US)", "debtor_account": _digits(rng, 10), "debtor_agent_bic": bic}
    cc = "GB" if geo == "GB" else rng.choice(EU_COUNTRIES)
    iban, bic, _ = gen_iban(cc, rng)
    return {"debtor_name": rng.choice(_DEBTORS) + (" (UK)" if geo == "GB" else " (Europe)"), "debtor_account": iban, "debtor_agent_bic": bic}


GEO_RAILS = {
    "GB": [("CHAPS", "GBP"), ("FPS", "GBP"), ("BACS", "GBP")],
    "US": [("FEDWIRE", "USD"), ("ACH", "USD")],
    "EU": [("SEPA_SCT", "EUR"), ("SEPA_INST", "EUR"), ("T2", "EUR")],
}


def _pick_rail(c: Ctx, geo: str, allow=None):
    rails = [r for r in GEO_RAILS[geo] if not allow or r[0] in allow]
    return c.rng.choice(rails)


def b_dq01(c: Ctx, geo: str):
    """Invalid IBAN (MOD-97 transposition) with repair evidence. Variants: sufficient / missing / contradictory."""
    rng = c.rng
    cc = "GB" if geo == "GB" else rng.choice(EU_COUNTRIES)
    good, bic, bank = gen_iban(cc, rng)
    bad = transpose_invalid(good, rng)
    rail, ccy = _pick_rail(c, geo, allow={"CHAPS", "FPS", "SEPA_SCT", "T2"})
    v = rng.random()
    name = _name(rng, cc)
    deb = _party_debtor(c, geo)
    cred = {"creditor_name": name, "creditor_account": bad, "creditor_agent_bic": bic}
    msg = "Creditor IBAN MOD-97 check digit failure on pacs.008 inbound clearing message."
    der = {"mod97_calculated_checksum": good[2:4], "inbound_transposition_detected": True}
    hist = {"historical_match_count": rng.randint(3, 25), "confidence_heuristic": round(rng.uniform(0.9, 0.99), 2)}
    amt = _amount(rng, small=rng.random() < 0.85)
    directory = {"sort_code": bank, "chaps_enabled": True} if geo == "GB" else {"bank_code": bank, "target2_active": True, "country": cc}
    if v < 0.72:
        return _base(c, "DQ01", "DQ-01", "DATA_QUALITY", "ERR_INVALID_IBAN_CHECKSUM", msg, rail, ccy, amt, deb, cred,
                     ext_ev={"routing_directory": directory}, bank_ev={"core_dda_account": good, "verified_iban": good}, derived=der, hist=hist)
    if v < 0.88:  # mandatory core DDA evidence missing
        return _base(c, "DQ01", "DQ-01", "DATA_QUALITY", "ERR_INVALID_IBAN_CHECKSUM",
                     "Creditor IBAN checksum failed; mandatory core DDA evidence missing.", rail, ccy, amt, deb, cred,
                     ext_ev={"routing_directory": directory}, suffix="-M")
    other, _, _ = gen_iban(cc, rng)  # contradictory: core DDA vs SSI directory disagree
    return _base(c, "DQ01", "DQ-01", "DATA_QUALITY", "ERR_INVALID_IBAN_CHECKSUM", msg, rail, ccy, amt, deb, cred,
                 ext_ev={"routing_directory": directory}, bank_ev={"core_dda_account": good, "verified_iban": good, "ssi_directory_account": other},
                 derived=der, hist=hist, suffix="-C")


def b_dq08(c: Ctx, geo: str):
    rng = c.rng
    rt, bic, inst = rng.choice(US_BANKS)
    bad = aba_transposed(rt)
    amt = _amount(rng, small=rng.random() < 0.85)
    deb = _party_debtor(c, "US")
    cred = {"creditor_name": _name(rng, "US"), "creditor_account": _digits(rng, 11), "creditor_agent_bic": bic}
    amb = rng.random() < 0.12
    ext = {"fedline_routing_directory": {"routing_number": rt, "institution_name": inst, "fedwire_funds_status": "ELIGIBLE", "check_digit_valid": True},
           "valid_routing_code": rt, "inbound_routing_code": bad}
    if amb:
        ext["ambiguous_routing_matches"] = True
    return _base(c, "DQ08", "DQ-08", "DATA_QUALITY", "ERR_INVALID_ROUTING_CODE",
                 "Federal Reserve ABA routing transit check digit mismatch on Fedwire wire.", "FEDWIRE", "USD", amt, deb, cred,
                 ext_ev=ext, bank_ev={"routing_syntax_master": {"syntax_valid": True, "format": "ABA_9_DIGIT"}},
                 derived={"aba_weight_algorithm_result": rt}, hist={"precedent_count": rng.randint(2, 15)}, suffix="-A" if amb else "")


def b_pr01(c: Ctx, geo: str):
    rng = c.rng
    rail, ccy = _pick_rail(c, geo)
    cc = "US" if geo == "US" else ("GB" if geo == "GB" else rng.choice(EU_COUNTRIES))
    amt = _amount(rng, small=rng.random() < 0.8)
    deb = _party_debtor(c, geo)
    if geo == "US":
        cred = {"creditor_name": _name(rng, "US"), "creditor_account": _digits(rng, 10), "creditor_agent_bic": rng.choice(US_BANKS)[1]}
    else:
        iban, bic, _ = gen_iban(cc, rng)
        cred = {"creditor_name": _name(rng, cc), "creditor_account": iban, "creditor_agent_bic": bic}
    has_orig = rng.random() < 0.85
    orig_pid = f"PMT-ORIG-{rng.randint(100000, 999999)}"
    ext = {}
    bank_ev = {"settlement_ledger": {"settled_status": "POSTED", "settled_amount": amt}}
    if has_orig:
        ext = {"historical_payment_journal": {"original_payment_id": orig_pid, "original_uetr": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                                              "transmitted_timestamp": "2026-10-16T08:15:00Z"}, "original_payment_id": orig_pid}
    return _base(c, "PR01", "PR-01", "PROCESSING", "ERR_DUPLICATE_TRANSACTION_DETECTED",
                 "Exact matching payload and amount received within 24-hour duplicate detection window.", rail, ccy, amt, deb, cred,
                 ext_ev=ext, bank_ev=bank_ev, derived={"exact_hash_match": True}, suffix="" if has_orig else "-M")


def b_pr08(c: Ctx, geo: str):
    rng = c.rng
    rail, ccy = ("FEDWIRE", "USD") if geo == "US" else _pick_rail(c, geo)
    deadlock = rng.random() < 0.15
    deb = {"debtor_name": rng.choice(_DEBTORS)}
    cred = {"creditor_name": _name(rng, "US" if geo == "US" else ("GB" if geo == "GB" else "DE"))}
    amt = _amount(rng, small=True)
    if deadlock:
        return _base(c, "PR08", "PR-08", "PROCESSING", "ERR_QUEUE_PROCESSING_FAILURE", "Message broker cluster unreachable; authority unavailable.",
                     rail, ccy, amt, deb, cred, bank_ev={"dlq_record": {"reason": "CONNECTION_TIMEOUT"}, "simulate_authority_unavailable": True},
                     derived={"broker_deadlocked": True}, suffix="-D")
    return _base(c, "PR08", "PR-08", "PROCESSING", "ERR_QUEUE_PROCESSING_FAILURE", "Message partition lock conflict in outbound clearing broker queue.",
                 rail, ccy, amt, deb, cred, bank_ev={"dlq_record": {"reason": "PARTITION_LEASE_EXPIRED", "attempt_count": rng.randint(1, 4)}},
                 ext_ev={"streaming_broker_journal": {"queue_name": f"{rail}_OUTBOUND_QUEUE", "partition_id": rng.randint(0, 7),
                                                    "head_offset": rng.randint(10000, 999999), "partition_health": "RECOVERABLE"}},
                 derived={"broker_deadlocked": False})


_RETURN_CODES = {"EU": ["AC04", "AC01", "AC06", "AM04", "MS03", "RR04"], "GB": ["AC04", "AC01", "AC06"], "US": ["R02", "R03", "R01"]}


def b_st01(c: Ctx, geo: str):
    rng = c.rng
    rail, ccy = _pick_rail(c, geo, allow={"SEPA_SCT", "T2", "CHAPS", "FPS", "FEDWIRE", "ACH"})
    cc = "US" if geo == "US" else ("GB" if geo == "GB" else rng.choice(EU_COUNTRIES))
    amt = _amount(rng, small=rng.random() < 0.85)
    deb = _party_debtor(c, geo)
    if geo == "US":
        cred = {"creditor_name": _name(rng, "US"), "creditor_account": _digits(rng, 10), "creditor_agent_bic": rng.choice(US_BANKS)[1]}
    else:
        iban, bic, _ = gen_iban(cc, rng)
        cred = {"creditor_name": _name(rng, cc), "creditor_account": iban, "creditor_agent_bic": bic}
    code = rng.choice(_RETURN_CODES[geo])
    posted = rng.random() < 0.88
    orig_uetr = str(uuid.UUID(int=rng.getrandbits(128), version=4))
    if posted:
        return _base(c, "ST01", "ST-01", "SETTLEMENT_RETURNS", "ERR_INWARD_RETURN_RECEIVED",
                     f"Inward return received (Return Reason {code}). Original debit posted.", rail, ccy, amt, deb, cred,
                     bank_ev={"original_debit_record": {"original_debit_posted": True, "original_uetr": orig_uetr, "ledger_account": deb["debtor_account"]},
                              "original_debit_posted": True},
                     ext_ev={"inward_pacs004_return": {"return_reason_code": code, "return_amount": amt, "originating_bic": cred["creditor_agent_bic"]}},
                     derived={"amount_currency_match": True})
    return _base(c, "ST01", "ST-01", "SETTLEMENT_RETURNS", "ERR_INWARD_RETURN_UNMATCHED",
                 "Inward return received, but original payment debit cannot be found in ledger.", rail, ccy, amt, deb, cred,
                 ext_ev={"inward_pacs004_return": {"return_reason_code": code}}, derived={"original_debit_posted": False}, suffix="-M")


def b_co04(c: Ctx, geo: str):
    rng = c.rng
    rail, ccy = ("FEDWIRE", "USD") if geo == "US" else _pick_rail(c, geo)
    deb = {"debtor_name": rng.choice(_DEBTORS)}
    blocked = rng.random() < 0.3
    amt = round(rng.uniform(5000, 60000), 2)
    if blocked:
        return _base(c, "CO04", "CO-04", "COMPLIANCE", "ERR_RESTRICTED_CORRIDOR",
                     "Payment corridor prohibited under statutory sanctions regime; no valid license exemption.", rail, ccy, amt, deb,
                     {"creditor_name": "Prohibited Jurisdiction Trading Co"},
                     bank_ev={"corridor_policy_matrix": {"policy_id": "POL-CORRIDOR-PROHIBITED", "general_license_permitted": False}, "ofac_license_exemption_verified": False},
                     ext_ev={"sanctions_watchlist": {"sdn_match": True, "program": "OFAC_TERRITORIAL_SANCTIONS"}}, derived={"creditor_country": "NK"}, suffix="-B")
    return _base(c, "CO04", "CO-04", "COMPLIANCE", "ERR_RESTRICTED_CORRIDOR",
                 "Payment corridor requires verified statutory exemption; general license verified.", rail, ccy, amt, deb,
                 {"creditor_name": "Humanitarian Supplies Beneficiary " + str(rng.randint(100, 999))},
                 bank_ev={"corridor_policy_matrix": {"policy_id": "POL-CORRIDOR-EXEMPT-01", "general_license_permitted": True}, "ofac_license_exemption_verified": True},
                 ext_ev={"sanctions_watchlist": {"sdn_match": False, "license_type": "OFAC_GL_58A_HUMANITARIAN"}},
                 derived={"corridor_clearance_code": "EXEMPT_MEDICINE"}, extra_pay={"remittance_info": "MEDICINE_SUPPLIES_HUMANITARIAN_AID"})


# (builder, weight, geos supported)
REAL_BUILDERS: List[Tuple[Callable, float, Tuple[str, ...]]] = [
    (b_dq01, 0.20, ("GB", "EU")),
    (b_dq08, 0.10, ("US",)),
    (b_pr01, 0.12, ("GB", "US", "EU")),
    (b_pr08, 0.05, ("GB", "US", "EU")),
    (b_st01, 0.13, ("GB", "US", "EU")),
    (b_co04, 0.10, ("GB", "US", "EU")),
]

_template_cache: Optional[List[Dict[str, Any]]] = None


def _templates() -> List[Dict[str, Any]]:
    global _template_cache
    if _template_cache is None:
        _template_cache = []
        if TEMPLATE_DIR.exists():
            real = {"DQ-01", "DQ-08", "PR-01", "PR-08", "ST-01", "CO-04"}
            for p in sorted(TEMPLATE_DIR.glob("*.json")):
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if str(d.get("profile_id", "")).upper() in real:
                    continue
                _template_cache.append(d)
    return _template_cache


def b_template(c: Ctx, geo: str):
    """'Other profile' record: fixture template with fresh identifiers and slightly varied amount/date.
    Accounts/parties/evidence are kept so the engines' reference lookups still match."""
    t = copy.deepcopy(c.rng.choice(_templates()))
    prof = t["profile_id"].replace("-", "")
    eid, pid, uetr = c.ids(prof, "-" + t["exception_id"].rsplit("-", 1)[-1][:4])
    t["exception_id"] = eid
    p = t["payment_info"]
    p["payment_id"], p["uetr"] = pid, uetr
    p["value_date"] = c.vdate()
    if p.get("amount", 0) and p["amount"] < 100000:
        p["amount"] = round(p["amount"] * c.rng.uniform(0.6, 1.4), 2)
    t["evidence_provenance"] = "NON_PRODUCTION_DEMO"
    return _replace_fake_us_ibans(t, c.rng)


_FAKE_US_IBAN = re.compile(r"^US\d{2}[A-Z0-9]{6,}$")


def _replace_fake_us_ibans(rec: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """Fixture templates carry fake 'US..' IBANs; the US has no IBAN. Swap them for plain account numbers everywhere."""
    mapping: Dict[str, str] = {}
    for k in ("debtor_account", "creditor_account"):
        v = rec["payment_info"].get(k)
        if isinstance(v, str) and _FAKE_US_IBAN.match(v):
            mapping[v] = _digits(rng, 10)
    if not mapping:
        return rec

    def walk(x):
        if isinstance(x, str):
            return mapping.get(x, x)
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        return x
    return walk(rec)


def _pick_geo(rng: random.Random, geos: List[str], supported: Tuple[str, ...]):
    opts = [g for g in geos if g in supported]
    return rng.choice(opts) if opts else None


def generate_records(count: int, seed: int = 1, rails: Optional[List[str]] = None, tag: Optional[str] = None,
                     real_share: float = 0.70, swift_share: float = 0.10, duplicate_rate: float = 0.0,
                     malformed_rate: float = 0.0, salt: Optional[str] = None) -> Iterator[Dict[str, Any]]:
    """Yield ``count`` records (constant memory). Deterministic for a given (count, seed, rails)."""
    geos = [g.strip().upper() for g in (rails or ["GB", "US", "EU"]) if g.strip()]
    geos = [("EU" if g in ("EUR", "SEPA", "EU") else g) for g in geos]
    geos = [g for g in geos if g in GEO_RAILS] or ["GB", "US", "EU"]
    # salt (optional) makes ids/UETRs unique per call while staying deterministic for a given (seed, salt)
    rng = random.Random(f"{seed}:{salt}" if salt else seed)
    tag = tag or f"S{seed}"
    prev: List[Dict[str, Any]] = []
    for i in range(count):
        c = Ctx(tag, seed, i, rng)
        roll = rng.random()
        rec = None
        if roll < real_share:
            weights = [(b, w) for b, w, sup in REAL_BUILDERS if any(g in sup for g in geos)]
            tot = sum(w for _, w in weights)
            r = rng.random() * tot
            acc = 0.0
            chosen = weights[-1][0]
            for b, w in weights:
                acc += w
                if r <= acc:
                    chosen = b
                    break
            sup = next(s for bb, _, s in REAL_BUILDERS if bb is chosen)
            geo = _pick_geo(rng, geos, sup)
            rec = chosen(c, geo)
        elif _templates():
            rec = b_template(c, "")
        else:
            geo = _pick_geo(rng, geos, ("GB", "US", "EU"))
            rec = b_pr01(c, geo)
        # cross-border SWIFT variant: same record routed over SWIFT_CBPR+
        if rng.random() < swift_share and rec["payment_info"].get("clearing_rail") in ("CHAPS", "FPS", "SEPA_SCT", "T2", "FEDWIRE", "ACH") \
                and rec["profile_id"] in ("DQ-01", "PR-01", "ST-01", "CO-04"):
            rec["payment_info"]["clearing_rail"] = "SWIFT_CBPR+"
        if duplicate_rate and prev and rng.random() < duplicate_rate:
            yield copy.deepcopy(rng.choice(prev))
            continue
        if len(prev) < 50:
            prev.append(rec)
        if malformed_rate and rng.random() < malformed_rate:
            bad = copy.deepcopy(rec)
            bad.pop("payment_info", None)
            yield bad
            continue
        yield rec


def write_batch(path: Path, count: int, seed: int = 1, rails: Optional[List[str]] = None, fmt: Optional[str] = None,
                **kw) -> Path:
    """Write a batch file. fmt: jsonl (default), json (envelope), jsonl.gz, json.gz."""
    path = Path(path)
    name = path.name.lower()
    fmt = fmt or ("json.gz" if name.endswith(".json.gz") else "jsonl.gz" if name.endswith((".jsonl.gz", ".ndjson.gz"))
                  else "json" if name.endswith(".json") else "jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = (lambda p: gzip.open(p, "wt", encoding="utf-8")) if fmt.endswith(".gz") else (lambda p: open(p, "w", encoding="utf-8"))
    recs = generate_records(count, seed, rails, **kw)
    with opener(path) as f:
        if fmt.startswith("json") and not fmt.startswith("jsonl"):
            bid = f"GEN-{seed}-{count}"
            f.write('{"batch_id": %s, "source_system": "PEX_SYNTHETIC_GENERATOR", "generated_at": %s, "records": [\n'
                    % (json.dumps(bid), json.dumps(datetime.now(timezone.utc).isoformat())))
            first = True
            for r in recs:
                f.write(("" if first else ",\n") + json.dumps(r))
                first = False
            f.write("\n]}\n")
        else:
            for r in recs:
                f.write(json.dumps(r) + "\n")
    return path
