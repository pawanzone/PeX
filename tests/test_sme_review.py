"""SME review: the bank's experts validate the profiles and controls, and PeX records where that stands.

  R1  Every one of the 41 profiles and 17 controls starts as NOT_REVIEWED; the summary adds up.
  R2  Status moves through IN_REVIEW, CHANGES_REQUESTED and SIGNED_OFF, with who and when; unknown items and statuses are refused.
  R3  A sign-off is tied to the content it was given on: if the content changes, the item shows CHANGED_SINCE_SIGNOFF.
  R4  Comments attach to an item (and optionally one part of it); OPEN until addressed.
  R5  An item with an open comment cannot be signed off.
  R6  Access: Administrators and Policy Owners review; Supervisors and Audit read; operators and approvers are refused.
  R7  Every status change, comment and import is an audit event.
  R8  Excel export: Profiles, Evidence and Controls sheets, with Status, Reviewer comment and Reviewer columns to fill in.
  R9  Excel import (Administrator only) reads status and comments back; rows that cannot be used are reported and the rest apply.
  R10 A file exported from older content is refused row by row (changed since export), never applied silently.
  R11 A file that is not a review workbook is refused with a reason.
  R12 Review never changes profile content, policy or any case.
"""
import io

import pytest
from openpyxl import Workbook, load_workbook

from app.core.auth import create_token
from app.services.v2 import library, review
from app.services.v2 import seed as v2seed

ADMIN, OWNER, SUP, AUD, OP, APPR = "ADM-0002", "POL-8001", "SUP-2001", "AUD-5001", "OP-9012", "APR-3192"


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def fresh(client):
    v2seed.seed_v2()
    client.delete("/api/v2/review", headers=H(ADMIN))
    yield
    client.delete("/api/v2/review", headers=H(ADMIN))


def summary(client, uid=ADMIN):
    r = client.get("/api/v2/review/summary", headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


def items(client, kind, uid=ADMIN):
    r = client.get("/api/v2/review/items", params={"kind": kind}, headers=H(uid))
    assert r.status_code == 200, r.text
    return {x["id"]: x for x in r.json()["items"]}


def setst(client, kind, id_, status, note="", uid=ADMIN):
    return client.post(f"/api/v2/review/items/{kind}/{id_}/status", json={"status": status, "note": note}, headers=H(uid))


def comment(client, kind, id_, text="Please check this", part=None, uid=ADMIN):
    return client.post(f"/api/v2/review/items/{kind}/{id_}/comments", json={"text": text, "part": part}, headers=H(uid))


# R1 --------------------------------------------------------------------------------------------------------------
def test_everything_starts_not_reviewed_and_the_summary_adds_up(client):
    s = summary(client)
    assert s["profiles"]["total"] == 41 and s["controls"]["total"] == 17
    for k in ("profiles", "controls"):
        assert s[k]["NOT_REVIEWED"] == s[k]["total"]
        assert sum(s[k][x] for x in ("NOT_REVIEWED", "IN_REVIEW", "CHANGES_REQUESTED", "SIGNED_OFF", "CHANGED_SINCE_SIGNOFF")) == s[k]["total"]
    assert s["open_comments"] == 0
    assert len(items(client, "profile")) == 41 and len(items(client, "control")) == 17


# R2 --------------------------------------------------------------------------------------------------------------
def test_status_moves_and_records_who_and_when(client):
    for st in ("IN_REVIEW", "CHANGES_REQUESTED", "IN_REVIEW", "SIGNED_OFF"):
        r = setst(client, "profile", "DQ-01", st, "ok", uid=OWNER)
        assert r.status_code == 200, r.text
    it = items(client, "profile")["DQ-01"]
    assert it["status"] == "SIGNED_OFF" and it["reviewer"] == OWNER and it["reviewed_at"]
    assert summary(client)["profiles"]["SIGNED_OFF"] == 1


@pytest.mark.parametrize("kind,id_,status", [("profile", "ZZ-99", "IN_REVIEW"), ("control", "CTL-99", "IN_REVIEW"), ("widget", "DQ-01", "IN_REVIEW"),
                                             ("profile", "DQ-01", "DONE"), ("profile", "DQ-01", "CHANGED_SINCE_SIGNOFF"), ("profile", "DQ-01", "")])
def test_unknown_item_or_status_is_refused(client, kind, id_, status):
    assert setst(client, kind, id_, status).status_code in (400, 404, 422)


# R3 --------------------------------------------------------------------------------------------------------------
def test_content_change_after_signoff_is_flagged(client, monkeypatch):
    assert setst(client, "profile", "DQ-01", "SIGNED_OFF").status_code == 200
    assert items(client, "profile")["DQ-01"]["status"] == "SIGNED_OFF"
    real = review.content_hash
    monkeypatch.setattr(review, "content_hash", lambda kind, id_: ("x" if (kind, id_) == ("profile", "DQ-01") else "") + real(kind, id_))
    it = items(client, "profile")["DQ-01"]
    assert it["status"] == "CHANGED_SINCE_SIGNOFF" and it["signed_off_on_version"] != it["version"]
    s = summary(client)["profiles"]
    assert s["CHANGED_SINCE_SIGNOFF"] == 1 and s["SIGNED_OFF"] == 0


def test_content_hash_is_stable(client):
    assert review.content_hash("profile", "DQ-01") == review.content_hash("profile", "DQ-01")
    assert review.content_hash("profile", "DQ-01") != review.content_hash("profile", "DQ-02")
    assert review.content_hash("control", "CTL-01") != review.content_hash("control", "CTL-02")


# R4, R5 ----------------------------------------------------------------------------------------------------------
def test_comments_open_then_addressed_and_block_signoff_while_open(client):
    r = comment(client, "profile", "DQ-01", "Evidence ACCOUNT_STATUS is not tier 1 for us", part="evidence: CORE_DDA_ACCOUNT")
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    assert r.json()["status"] == "OPEN" and r.json()["part"] == "evidence: CORE_DDA_ACCOUNT"
    assert summary(client)["open_comments"] == 1 and items(client, "profile")["DQ-01"]["open_comments"] == 1
    blocked = setst(client, "profile", "DQ-01", "SIGNED_OFF")
    assert blocked.status_code == 409 and "comment" in blocked.text.lower()
    a = client.post(f"/api/v2/review/comments/{cid}/address", json={"note": "Tier changed in v2"}, headers=H(OWNER))
    assert a.status_code == 200 and a.json()["status"] == "ADDRESSED" and a.json()["addressed_by"] == OWNER
    assert summary(client)["open_comments"] == 0
    assert setst(client, "profile", "DQ-01", "SIGNED_OFF").status_code == 200
    d = client.get("/api/v2/review/items/profile/DQ-01", headers=H(ADMIN)).json()
    assert [c["status"] for c in d["comments"]] == ["ADDRESSED"]


@pytest.mark.parametrize("text", ["", "   ", "x" * 2001])
def test_bad_comment_text_is_refused(client, text):
    assert comment(client, "profile", "DQ-01", text).status_code in (400, 422)


def test_unknown_comment_cannot_be_addressed(client):
    assert client.post("/api/v2/review/comments/NOPE/address", json={"note": ""}, headers=H(ADMIN)).status_code == 404


# R6 --------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("uid", [ADMIN, OWNER])
def test_reviewers_can_set_status_and_comment(client, uid):
    assert setst(client, "control", "CTL-02", "IN_REVIEW", uid=uid).status_code == 200
    assert comment(client, "control", "CTL-02", uid=uid).status_code == 200


@pytest.mark.parametrize("uid", [SUP, AUD, OP, APPR])
def test_others_cannot_change_anything(client, uid):
    assert setst(client, "control", "CTL-02", "IN_REVIEW", uid=uid).status_code == 403
    assert comment(client, "control", "CTL-02", uid=uid).status_code == 403


@pytest.mark.parametrize("uid", [ADMIN, OWNER, SUP, AUD])
def test_these_roles_can_read(client, uid):
    assert client.get("/api/v2/review/summary", headers=H(uid)).status_code == 200
    assert client.get("/api/v2/review/export.xlsx", headers=H(uid)).status_code in (200, 403)  # export is read access for all four


@pytest.mark.parametrize("uid", [OP, APPR])
def test_operators_and_approvers_cannot_read(client, uid):
    assert client.get("/api/v2/review/summary", headers=H(uid)).status_code == 403
    assert client.get("/api/v2/review/items", params={"kind": "profile"}, headers=H(uid)).status_code == 403


def test_export_is_open_to_the_four_reading_roles(client):
    for uid in (ADMIN, OWNER, SUP, AUD):
        assert client.get("/api/v2/review/export.xlsx", headers=H(uid)).status_code == 200
    assert client.get("/api/v2/review/export.xlsx", headers=H(OP)).status_code == 403


# R7 --------------------------------------------------------------------------------------------------------------
def test_changes_are_audited(client):
    def n():
        ev = client.get("/api/v2/audit/events", params={"case_id": "SME-REVIEW", "page_size": 500}, headers=H(AUD)).json()["items"]
        return len(ev)
    base = n()
    setst(client, "profile", "DQ-01", "IN_REVIEW")
    cid = comment(client, "profile", "DQ-01").json()["id"]
    client.post(f"/api/v2/review/comments/{cid}/address", json={"note": "done"}, headers=H(ADMIN))
    assert n() == base + 3


# R8 --------------------------------------------------------------------------------------------------------------
def export(client, uid=ADMIN):
    r = client.get("/api/v2/review/export.xlsx", headers=H(uid))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    return r.content, load_workbook(io.BytesIO(r.content))


def test_export_has_the_sheets_and_columns(client):
    _, wb = export(client)
    assert {"Read me", "Profiles", "Evidence", "Controls"} <= set(wb.sheetnames)
    for sheet in ("Profiles", "Controls", "Evidence"):
        heads = [c.value for c in wb[sheet][1]]
        assert "Reviewer comment" in heads and "Version" in heads
        assert ("Status" in heads) == (sheet != "Evidence")  # evidence rows take a comment; status is per profile or control
    assert wb["Profiles"].max_row == 42 and wb["Controls"].max_row == 18
    ev = library.profile("DQ-01")["evidence"]
    assert sum(1 for r in wb["Evidence"].iter_rows(min_row=2, values_only=True) if r[0] == "DQ-01") == len(ev)


# R9 --------------------------------------------------------------------------------------------------------------
def fill(content, edits):
    """edits: sheet -> {key_value(s) -> {column: value}}; keys are the first column (Evidence: first two)."""
    wb = load_workbook(io.BytesIO(content))
    for sheet, rows in edits.items():
        ws = wb[sheet]
        heads = [c.value for c in ws[1]]
        for row in ws.iter_rows(min_row=2):
            key = row[0].value if sheet != "Evidence" else (row[0].value, row[1].value)
            if key in rows:
                for col, v in rows[key].items():
                    row[heads.index(col)].value = v
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def upload(client, data, uid=ADMIN, name="review.xlsx"):
    return client.post("/api/v2/review/import", files={"file": (name, io.BytesIO(data), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, headers=H(uid))


def test_round_trip_applies_status_and_comments(client):
    content, _ = export(client)
    edited = fill(content, {"Profiles": {"DQ-01": {"Status": "Signed off", "Reviewer": "J. Smith"}, "DQ-02": {"Status": "Changes requested", "Reviewer comment": "Option 2 not how we do it", "Reviewer": "J. Smith"}},
                            "Controls": {"CTL-01": {"Status": "In review"}},
                            "Evidence": {("DQ-01", "CORE_DDA_ACCOUNT"): {"Reviewer comment": "Our core calls this CIF_ACCOUNT"}}})
    r = upload(client, edited)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["rejected"] == [] and b["applied"] >= 4
    p = items(client, "profile")
    assert p["DQ-01"]["status"] == "SIGNED_OFF" and p["DQ-02"]["status"] == "CHANGES_REQUESTED"
    assert items(client, "control")["CTL-01"]["status"] == "IN_REVIEW"
    d2 = client.get("/api/v2/review/items/profile/DQ-02", headers=H(ADMIN)).json()
    assert d2["comments"][0]["text"] == "Option 2 not how we do it" and d2["comments"][0]["status"] == "OPEN"
    d1 = client.get("/api/v2/review/items/profile/DQ-01", headers=H(ADMIN)).json()
    assert any(c["part"] == "evidence: CORE_DDA_ACCOUNT" and "CIF_ACCOUNT" in c["text"] for c in d1["comments"])


def test_importing_the_same_file_twice_does_not_duplicate_comments(client):
    content, _ = export(client)
    edited = fill(content, {"Profiles": {"DQ-02": {"Status": "Changes requested", "Reviewer comment": "Same note"}}})
    upload(client, edited)
    upload(client, edited)
    assert len(client.get("/api/v2/review/items/profile/DQ-02", headers=H(ADMIN)).json()["comments"]) == 1


def test_bad_rows_are_reported_and_the_rest_apply(client):
    content, _ = export(client)
    edited = fill(content, {"Profiles": {"DQ-01": {"Status": "Signed off"}, "DQ-02": {"Status": "Finished!"}, "DQ-03": {"Status": "Signed off", "Reviewer comment": "but also a comment"}}})
    b = upload(client, edited).json()
    assert b["applied"] == 1 and len(b["rejected"]) == 2
    assert {x["id"] for x in b["rejected"]} == {"DQ-02", "DQ-03"} and all(x["reason"] for x in b["rejected"])
    assert items(client, "profile")["DQ-01"]["status"] == "SIGNED_OFF" and items(client, "profile")["DQ-02"]["status"] == "NOT_REVIEWED"


def test_unknown_code_in_the_file_is_reported(client):
    content, _ = export(client)
    wb = load_workbook(io.BytesIO(content))
    ws = wb["Profiles"]
    ws.append(["ZZ-99"] + [None] * (ws.max_column - 1))
    heads = [c.value for c in ws[1]]
    ws.cell(row=ws.max_row, column=heads.index("Status") + 1, value="Signed off")
    out = io.BytesIO()
    wb.save(out)
    b = upload(client, out.getvalue()).json()
    assert any(x["id"] == "ZZ-99" for x in b["rejected"])


def test_only_administrators_import(client):
    content, _ = export(client)
    for uid in (OWNER, SUP, AUD, OP, APPR):
        assert upload(client, content, uid=uid).status_code == 403


# R10 -------------------------------------------------------------------------------------------------------------
def test_file_from_older_content_is_refused_per_row(client, monkeypatch):
    content, _ = export(client)
    edited = fill(content, {"Profiles": {"DQ-01": {"Status": "Signed off"}, "DQ-02": {"Status": "Signed off"}}})
    real = review.content_hash
    monkeypatch.setattr(review, "content_hash", lambda kind, id_: ("x" if (kind, id_) == ("profile", "DQ-01") else "") + real(kind, id_))
    b = upload(client, edited).json()
    assert b["applied"] == 1 and [x["id"] for x in b["rejected"]] == ["DQ-01"] and "changed" in b["rejected"][0]["reason"].lower()
    assert items(client, "profile")["DQ-01"]["status"] == "NOT_REVIEWED"


# R11 -------------------------------------------------------------------------------------------------------------
def test_not_a_workbook_is_refused(client):
    assert upload(client, b"not a spreadsheet at all").status_code == 400
    wb = Workbook()
    wb.active.title = "Sheet1"
    out = io.BytesIO()
    wb.save(out)
    r = upload(client, out.getvalue())
    assert r.status_code == 400 and "profiles" in r.text.lower()


# R12 -------------------------------------------------------------------------------------------------------------
def test_review_changes_no_content(client):
    before = (review.content_hash("profile", "DQ-01"), review.content_hash("control", "CTL-01"))
    setst(client, "profile", "DQ-01", "SIGNED_OFF")
    comment(client, "control", "CTL-01")
    assert (review.content_hash("profile", "DQ-01"), review.content_hash("control", "CTL-01")) == before


def test_clear_is_admin_only(client):
    setst(client, "profile", "DQ-01", "IN_REVIEW")
    assert client.delete("/api/v2/review", headers=H(OWNER)).status_code == 403
    assert client.delete("/api/v2/review", headers=H(ADMIN)).status_code == 200
    assert summary(client)["profiles"]["NOT_REVIEWED"] == 41
