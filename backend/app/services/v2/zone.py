"""The evidence zone: the one place where real personal values are handled.

Inside the zone   real values go in (bank event, connector responses), deterministic checks run on them
                  (mod-97, name similarity, exact match, directory lookup, history count), and the vault keeps raw <-> token.
Outside the zone  only tokens and derived facts come out ("passes checksum", "similarity 0.62", "matches directory", "3 earlier
                  payments"). Screens, audit rows, notifications, the AI input and the confidence engine read only that.
Reveal            an authorised person can ask to see real values (reason, logged, expires); each class has its own role list
                  (see classification.py). Admin never. Compliance alone sees C3.

Connectors        every external source has one interface. `simulated` returns ISO 20022-shaped data, `real` needs an adapter
                  registered for that system key (nothing falls back silently: a real connector without an adapter fails closed).
                  Switch per connector with PEX_CONNECTOR_MODES="CUSTM=real,COPVOP=real".
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.config import settings
from app.core.tokenization import token_vault
from app.services.v2 import classification as cl
from app.services.v2 import ext as xt
from app.services.v2.evidence_model import SYSTEMS

_TOKEN = r"TOK-[A-Z]+-[0-9A-F]{12}"
TOKEN_RE = re.compile(_TOKEN)
_SPLIT = re.compile(f"({_TOKEN})")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{2,4}){3,8}\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_SKIP_KEYS = {"id", "case_id", "endpoint", "reveal_endpoint", "hide_endpoint", "page_url", "status", "status_label", "class", "token", "mode"}


class ZoneLeak(Exception):
    """Raised when real personal data was about to leave the zone."""


# ----------------------------------------------------------------------------------------------
# Vault access (raw <-> token), persisted so reveal still works after a restart
# ----------------------------------------------------------------------------------------------
_display: Dict[str, str] = {}


def _persist(token: str, raw: str, kind: str):
    try:
        from app.db.models import TokenVaultModel
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            if db.query(TokenVaultModel).filter(TokenVaultModel.token_value == token).first() is None:
                clean = raw.strip().replace(" ", "").upper()
                db.add(TokenVaultModel(raw_hash=hashlib.sha256(clean.encode()).hexdigest(), raw_value=raw[:256], token_value=token,
                                       token_type=kind))
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    except Exception:  # pragma: no cover - vault persistence must never break a request
        pass


def tok(raw: Any, kind: str) -> str:
    r = str(raw or "").strip()
    if not r:
        return ""
    t = token_vault.tokenize(r, kind)
    if t not in _display:
        _display[t] = r
        _persist(t, r, kind)
    return t


def reveal_value(token: str) -> Optional[str]:
    v = _display.get(token)
    if v is None:
        try:
            from app.db.models import TokenVaultModel
            from app.db.session import SessionLocal
            db = SessionLocal()
            try:
                row = db.query(TokenVaultModel).filter(TokenVaultModel.token_value == token).first()
                v = row.raw_value if row else None
            finally:
                db.close()
        except Exception:
            v = None
        if v is None:
            v = token_vault.detokenize(token)
        if v is not None:
            _display[token] = v
    if v is not None and token.split("-")[1] in ("IBAN", "ACC") and xt.looks_like_iban(v):
        return xt.iban_group(v)
    return v


def raw_of(value: Any) -> Any:
    """Inside the zone only: turn a token back into the real value (used when a chosen candidate becomes a repair)."""
    if isinstance(value, str) and TOKEN_RE.fullmatch(value.strip()):
        return reveal_value(value.strip()) or value
    return value


# ----------------------------------------------------------------------------------------------
# Known values of a case, sealing (raw -> token) and unsealing (token -> raw for a permitted viewer)
# ----------------------------------------------------------------------------------------------
def case_pairs(case: Dict[str, Any], ext: Optional[Dict[str, Any]] = None) -> List[Tuple[str, str]]:
    """(raw text as it may appear, token) for one case, longest first."""
    if ext is None:
        from app.services.v2 import logic as lg
        ext = lg.ext_of(case)
    out: Dict[str, str] = {}

    def add(raw: Any, kind: str):
        if not isinstance(raw, str):
            return
        r = raw.strip()
        if len(r) < 5:
            return
        t = tok(r, kind)
        out[r] = t
        if kind in ("IBAN", "ACC"):
            c = xt.iban_compact(r)
            out[c] = t
            out[xt.iban_group(c)] = t

    for k in ("debtor_party", "creditor_party"):
        add((case.get(k) or {}).get("party_name"), "PARTY")
    for k in ("debtor_account", "creditor_account"):
        a = case.get(k) or {}
        add(a.get("iban"), "IBAN")
        add(a.get("account_number"), "ACC")
    add(ext.get("counterparty"), "PARTY")
    add(ext.get("debtor"), "PARTY")
    ch = ext.get("change") or {}
    for side in ("original", "proposed"):
        v = (ch.get(side) or {}).get("value")
        if isinstance(v, str) and xt.looks_like_iban(v):
            add(v, "IBAN")
    return sorted(out.items(), key=lambda kv: -len(kv[0]))


def seal_text(text: Any, case: Optional[Dict[str, Any]] = None, pairs: Optional[List[Tuple[str, str]]] = None) -> Any:
    """Replace real values in a string by tokens. Known case values first, then anything shaped like an IBAN or an e-mail."""
    if not isinstance(text, str) or not text:
        return text
    if pairs is None:
        pairs = case_pairs(case) if case else []
    parts = _SPLIT.split(text)
    for i in range(0, len(parts), 2):          # even parts are plain text, odd parts are existing tokens (left alone)
        s = parts[i]
        for raw, t in pairs:
            if raw in s:
                s = s.replace(raw, t)
        # the replacement above may have introduced tokens; only scan the plain pieces between them
        sub = _SPLIT.split(s)
        for j in range(0, len(sub), 2):
            seg = sub[j]
            seg = IBAN_RE.sub(lambda m: tok(m.group(0), "IBAN") if xt.looks_like_iban(m.group(0)) else m.group(0), seg)
            seg = EMAIL_RE.sub(lambda m: tok(m.group(0), "EMAIL"), seg)
            sub[j] = seg
        parts[i] = "".join(sub)
    return "".join(parts)


def seal_obj(o: Any, case: Optional[Dict[str, Any]] = None, pairs: Optional[List[Tuple[str, str]]] = None, _key: str = "") -> Any:
    if pairs is None:
        pairs = case_pairs(case) if case else []
    if isinstance(o, str):
        return o if _key in _SKIP_KEYS else seal_text(o, None, pairs)
    if isinstance(o, list):
        return [seal_obj(x, None, pairs, _key) for x in o]
    if isinstance(o, dict):
        return {k: seal_obj(v, None, pairs, str(k)) for k, v in o.items()}
    return o


def _kind_for_key(key: str) -> Optional[str]:
    """ISO 20022 element name (as a connector returns it) -> token type, so a response is tokenised by what each field IS."""
    k = str(key or "").lower()
    if k in ("matchednm", "listednm") or "sanction" in k:
        return "SCRN"
    if "iban" in k:
        return "IBAN"
    if k in ("nm", "acctholdernm", "acctHldrNm".lower(), "name", "dbtrnm", "cdtrnm", "ultmtcdtr", "ultmtdbtr") or k.endswith("nm") and k not in ("strtnm", "twnnm", "ctrysubdvsn"):
        return "PARTY"
    if k in ("strtnm", "twnnm", "pstcd", "adrline", "bldgnb", "bldgnm", "pstladr", "address"):
        return "ADDR"
    if k in ("ustrd", "addtlinf", "instrfornxtagt", "remittance", "note"):
        return "TEXT"
    if "email" in k:
        return "EMAIL"
    if k in ("prvtid", "dtandplcofbirth", "birthdt", "dob"):
        return "DOB"
    if k in ("othr", "acctid", "acct_no", "account_number"):
        return "ACC"
    return None


def seal_response(o: Any, key: str = "") -> Any:
    """Tokenise a connector response at the boundary, field by field (by element name), then catch IBAN- and e-mail-shaped text."""
    if isinstance(o, dict):
        return {k: seal_response(v, str(k)) for k, v in o.items()}
    if isinstance(o, list):
        return [seal_response(x, key) for x in o]
    if isinstance(o, str) and o and not TOKEN_RE.fullmatch(o.strip()):
        kind = _kind_for_key(key)
        if kind:
            return tok(o, kind)
        return seal_text(o)
    return o


SEALED_EXT_KEYS = ("evidence", "conflict", "needed", "request_info", "recommended_action", "handover")


def seal_ext(case_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Called whenever the per-case extension is stored: evidence and everything derived from it holds tokens, not real values.
    The proposed repair (`change`) and the case record stay real: they are what is handed to the bank, inside the zone."""
    try:
        from app.services.data_loader import repo
        case = repo.get_case(case_id)
    except Exception:
        case = None
    pairs = case_pairs(case, data) if case else []
    for k in SEALED_EXT_KEYS:
        if k in data and data[k] is not None:
            data[k] = seal_obj(data[k], None, pairs)
    return data


def unseal_text(text: str, role: str) -> str:
    def sub(m):
        t = m.group(0)
        if cl.can_reveal_class(role, cl.token_class(t)):
            v = reveal_value(t)
            if v is not None:
                return v
        return t
    return TOKEN_RE.sub(sub, text)


def unseal_obj(o: Any, role: str) -> Any:
    if isinstance(o, str):
        return unseal_text(o, role)
    if isinstance(o, list):
        return [unseal_obj(x, role) for x in o]
    if isinstance(o, dict):
        return {k: (v if k in _SKIP_KEYS else unseal_obj(v, role)) for k, v in o.items()}
    return o


def restricted_tokens_present(o: Any, role: str) -> bool:
    """True when the payload still holds tokens this role may not reveal (so the screen can say why)."""
    s = json.dumps(o, default=str)
    return any(not cl.can_reveal_class(role, cl.token_class(t)) for t in TOKEN_RE.findall(s))


# ----------------------------------------------------------------------------------------------
# Connectors: one interface, simulated now, real when a bank agrees to take part
# ----------------------------------------------------------------------------------------------
class ConnectorNotConfigured(Exception):
    pass


class Connector:
    key = ""

    def fetch(self, req: Dict[str, Any], world: Dict[str, Any]) -> Dict[str, Any]:       # pragma: no cover - interface
        raise NotImplementedError


def _similar(a: str, b: str) -> float:
    n = lambda s: re.sub(r"[^a-z0-9 ]", "", str(s or "").lower()).strip()
    return round(difflib.SequenceMatcher(None, n(a), n(b)).ratio(), 2)


class _SimMaster(Connector):          # beneficiary / customer master (CUSTM)
    key = "CUSTM"

    def fetch(self, req, world):
        d = world.get("directory") or {}
        return {"Cdtr": {"Nm": d.get("name", req.get("name"))},
                "CdtrAcct": {"Id": {"IBAN": d.get("iban", req.get("iban"))}},
                "LastChanged": d.get("last_changed")}


class _SimVop(Connector):             # CoP / VoP scheme service (COPVOP)
    key = "COPVOP"

    def fetch(self, req, world):
        holder = world.get("account_holder", req.get("name"))
        ratio = _similar(req.get("name"), holder)
        return {"Rslt": "MTCH" if ratio >= 0.97 else ("CMTC" if ratio >= 0.75 else "NMTC"), "AcctHldrNm": holder}


class _SimHistory(Connector):         # message archive and payment history (ARCH)
    key = "ARCH"

    def fetch(self, req, world):
        h = world.get("history") or {}
        n, same = int(h.get("count", 3)), int(h.get("same_account", h.get("count", 3)))
        iban = h.get("iban") or (world.get("checksum") or {}).get("proposed") or req.get("iban")
        other = h.get("other_iban", "")
        return {"Pmts": [{"CdtrAcct": {"Id": {"IBAN": iban if i < same else other}}, "Dt": f"2026-0{(i % 9) + 1}-1{i % 9}"} for i in range(n)]}


class _SimInvoice(Connector):         # client ERP / AP ledger (ERP)
    key = "ERP"

    def fetch(self, req, world):
        inv = world.get("invoice") or {}
        return {"InvNb": inv.get("number", ""), "CdtrAcct": {"Id": {"IBAN": inv.get("iban", "")}}}


class _SimCore(Connector):            # core banking: account status (CORE)
    key = "CORE"

    def fetch(self, req, world):
        a = world.get("account") or {}
        return {"Acct": {"Sts": a.get("status", "OPEN"), "CanCredit": bool(a.get("can_credit", True))}}


class _SimScreening(Connector):       # sanctions lists and licences (LISTS)
    key = "LISTS"

    def fetch(self, req, world):
        s = world.get("screening") or {}
        return {"Hit": bool(s.get("hit")), "List": s.get("list", ""), "MatchedNm": s.get("name", ""), "Score": s.get("score", 0)}


SIMULATED: Dict[str, Connector] = {c.key: c for c in (_SimMaster(), _SimVop(), _SimHistory(), _SimInvoice(), _SimScreening(), _SimCore())}
REAL_ADAPTERS: Dict[str, Callable[[], Connector]] = {}


def register_real(key: str, factory: Callable[[], Connector]):
    """Plug in a real connector for a system key once a bank agrees to take part."""
    REAL_ADAPTERS[key] = factory


def connector_mode(key: str) -> str:
    modes = {}
    for part in str(getattr(settings, "CONNECTOR_MODES", "") or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            modes[k.strip().upper()] = v.strip().lower()
    return modes.get(key.upper(), "simulated")


def get_connector(key: str) -> Connector:
    if connector_mode(key) == "real":
        f = REAL_ADAPTERS.get(key)
        if f is None:
            raise ConnectorNotConfigured(f"Connector {key} is set to real but no adapter is registered")
        return f()
    return SIMULATED[key]


def connector_status() -> List[Dict[str, Any]]:
    return [{"key": k, "name": SYSTEMS[k][1], "mode": connector_mode(k), "adapter_registered": k in REAL_ADAPTERS}
            for k in sorted(SIMULATED)]


# ----------------------------------------------------------------------------------------------
# Checks. Real values in, tokens + derived facts out.
# ----------------------------------------------------------------------------------------------
def _party(case: Dict[str, Any], side: str) -> str:
    return str((case.get(f"{side}_party") or {}).get("party_name") or "")


def _iban(case: Dict[str, Any]) -> str:
    a = case.get("creditor_account") or {}
    return str(a.get("iban") or a.get("account_number") or "")


def _row(rid, check, result, sys_key, source, authority, status, label, ts, resp, fields, facts) -> Dict[str, Any]:
    r = xt.row(rid, check, result, source, authority, status, label, ts, raw=seal_response(resp or {}))
    r["fields"] = fields
    r["facts"] = facts
    r["mode"] = connector_mode(sys_key) if sys_key in SIMULATED else "zone"
    return r


def _field(label: str, raw: Any, kind: str) -> Dict[str, Any]:
    t = tok(raw, kind)
    return {"label": label, "token": t, "class": cl.TOKEN_CLASS.get(kind, "C1")}


def check_checksum(case, world, rid, ts, source="Deterministic check") -> Dict[str, Any]:
    vals: Dict[str, str] = world.get("checksum") or {"IBAN": _iban(case)}
    ok = {k: xt.iban_valid(v) for k, v in vals.items()}
    if set(vals) == {"original", "proposed"}:
        txt = f"Original {'passes' if ok['original'] else 'fails'} mod-97; proposed {'passes' if ok['proposed'] else 'fails'} mod-97"
        good = ok["proposed"]
    elif len(vals) > 1:
        good = all(ok.values())
        txt = "Both IBANs pass mod-97" if good else "At least one IBAN fails mod-97"
    else:
        good = all(ok.values())
        txt = "Passes mod-97" if good else "Fails mod-97"
    return _row(rid, "Creditor IBAN checksum", txt, "ISO", source, "Deterministic check", "pass" if good else "fail",
                "Passed" if good else "Failed", ts, None, [], {"valid": ok})


def check_directory(case, world, rid, ts, source="Beneficiary master directory") -> Dict[str, Any]:
    resp = get_connector("CUSTM").fetch({"name": _party(case, "creditor"), "iban": _iban(case)}, world)
    d_iban = resp["CdtrAcct"]["Id"]["IBAN"]
    agrees = xt.iban_compact(d_iban) == xt.iban_compact(_iban(case))
    return _row(rid, "Beneficiary master directory", f"Directory holds {tok(d_iban, 'IBAN')}", "CUSTM", source, "Authoritative",
                "agree" if agrees else "differs", "Agree" if agrees else "Differs", ts, resp,
                [_field("Directory IBAN", d_iban, "IBAN")], {"agrees_with_instruction": agrees})


def check_vop(case, world, rid, ts, source="Verification of Payee (simulated)") -> Dict[str, Any]:
    resp = get_connector("COPVOP").fetch({"name": _party(case, "creditor"), "iban": _iban(case)}, world)
    holder, sim = resp["AcctHldrNm"], _similar(_party(case, "creditor"), resp["AcctHldrNm"])
    match = resp["Rslt"] == "MTCH"
    return _row(rid, "Account holder name", f"Bank returns '{tok(holder, 'PARTY')}' (name similarity {sim:.2f})", "COPVOP", source, "Authoritative",
                "agree" if match else "differs", "Agree" if match else "Differs", ts, resp,
                [_field("Account holder", holder, "PARTY")], {"scheme_result": resp["Rslt"], "similarity": sim})


def check_history(case, world, rid, ts, source="Payment history") -> Dict[str, Any]:
    resp = get_connector("ARCH").fetch({"iban": _iban(case)}, world)
    target = xt.iban_compact((world.get("history") or {}).get("target_iban") or (world.get("checksum") or {}).get("proposed") or _iban(case))
    pm = resp["Pmts"]
    same = sum(1 for p in pm if xt.iban_compact(p["CdtrAcct"]["Id"]["IBAN"]) == target)
    return _row(rid, "Prior payments", f"{same} earlier payments to this beneficiary used the proposed IBAN", "ARCH", source, "Supporting",
                "agree" if same else "info", "Agree" if same else "No history", ts, resp, [], {"count": len(pm), "same_account": same})


def check_invoice(case, world, rid, ts, source=None) -> Dict[str, Any]:
    resp = get_connector("ERP").fetch({}, world)
    inv_iban, nb = resp["CdtrAcct"]["Id"]["IBAN"], resp["InvNb"]
    agrees = xt.iban_compact(inv_iban) == xt.iban_compact(_iban(case))
    return _row(rid, f"Invoice {nb}", f"Invoice shows {tok(inv_iban, 'IBAN')}", "ERP", source or f"Invoice {nb}", "Supporting",
                "agree" if agrees else "differs", "Agree" if agrees else "Differs", ts, resp,
                [_field("Invoice IBAN", inv_iban, "IBAN")], {"agrees_with_instruction": agrees})


def check_core(case, world, rid, ts, source="Core banking (simulated)") -> Dict[str, Any]:
    resp = get_connector("CORE").fetch({"iban": _iban(case)}, world)
    sts, can = resp["Acct"]["Sts"], resp["Acct"]["CanCredit"]
    ok = sts == "OPEN" and can
    return _row(rid, "Beneficiary account status", "Account is open and can receive credits" if ok else f"Account status is {str(sts).lower()}", "CORE", source,
                "Authoritative", "agree" if ok else "differs", "Agree" if ok else "Differs", ts, resp, [], {"status": sts, "can_credit": can})


def check_screening(case, world, rid, ts, source="Sanctions screening (simulated)") -> Dict[str, Any]:
    resp = get_connector("LISTS").fetch({"name": _party(case, "creditor")}, world)
    hit = bool(resp["Hit"])
    txt = (f"Possible match on {resp['List']} list: {tok(resp['MatchedNm'], 'SCRN')} (score {resp['Score']})" if hit else "No match on any list")
    return _row(rid, "Sanctions screening", txt, "LISTS", source, "Authoritative", "differs" if hit else "pass",
                "Possible match" if hit else "Clear", ts, resp, [_field("Listed name", resp["MatchedNm"], "SCRN")] if hit else [],
                {"hit": hit, "list": resp.get("List", ""), "score": resp.get("Score", 0)})


KINDS = {"checksum": check_checksum, "directory": check_directory, "vop": check_vop, "history": check_history,
         "invoice": check_invoice, "screening": check_screening, "core": check_core}


def run(kind: str, rid: str, case: Dict[str, Any], world: Dict[str, Any], ts: str, **kw) -> Dict[str, Any]:
    r = KINDS[kind](case, world, rid, ts, **kw)
    r.setdefault("kind", kind)
    return r


# ----------------------------------------------------------------------------------------------
# What the AI is allowed to see
# ----------------------------------------------------------------------------------------------
def ai_view(case: Dict[str, Any], ext: Dict[str, Any]) -> Dict[str, Any]:
    """The exact payload an LLM would receive for this case. Tokens, a band instead of the amount, and derived facts only."""
    from app.services.v2 import logic as lg
    pairs = case_pairs(case)
    cred_acc = case.get("creditor_account") or {}
    ev = []
    for r in ext.get("evidence") or []:
        ev.append({"id": r.get("id"), "check": seal_text(r.get("check"), None, pairs), "status": r.get("status"),
                   "finding": seal_text(r.get("result"), None, pairs), "authority": r.get("authority"),
                   "facts": r.get("facts") or {}, "values": [f"{f['token']}" for f in (r.get("fields") or []) if f.get("class") in ("C1",)]})
    out = {
        "case": {"profile": case.get("profile"), "error_code": case.get("error_code"), "rail": case.get("payment_rail"),
                 "currency": case.get("currency"), "amount_band": cl.amount_band(case.get("amount"), case.get("currency")),
                 "debtor_country": (case.get("debtor_party") or {}).get("country"),
                 "creditor_country": (case.get("creditor_party") or {}).get("country")},
        "reference": tok(case.get("uetr") or case.get("case_id"), "REF"),
        "parties": {"debtor": tok(_party(case, "debtor"), "PARTY"), "creditor": tok(_party(case, "creditor"), "PARTY")},
        "creditor_account": tok(cred_acc.get("iban") or cred_acc.get("account_number"), "IBAN"),
        "evidence": ev,
        "evidence_state": ext.get("evidence_state"),
        "reason": seal_text(case.get("reason"), None, pairs),
    }
    return out


def guard(payload: Any, case: Optional[Dict[str, Any]] = None, extra_raw: Optional[List[str]] = None) -> Any:
    """Fail closed: nothing real may leave the zone. Used before any prompt, export or notification is built from case data."""
    s = json.dumps(payload, default=str)
    plain = TOKEN_RE.sub("", s)
    found: List[str] = []
    for raw, _t in (case_pairs(case) if case else []):
        if raw and raw in plain:
            found.append("known value")
    for m in IBAN_RE.finditer(plain):
        if xt.looks_like_iban(m.group(0)):
            found.append("iban-shaped value")
    if EMAIL_RE.search(plain):
        found.append("e-mail address")
    for r in extra_raw or []:
        if r and str(r) in plain:
            found.append("listed value")
    if found:
        raise ZoneLeak(f"Real data would leave the zone ({', '.join(sorted(set(found)))})")
    return payload


def llm_input(case: Dict[str, Any], ext: Dict[str, Any]) -> Dict[str, Any]:
    """The only function that should build an LLM payload for a v2 case."""
    return guard(ai_view(case, ext), case)
