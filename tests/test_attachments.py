"""Real attachments on Submit for approval. Acceptance tests from the requirements.

  A1  A maker can upload a file to a case they work. PeX keeps it with a SHA-256 fingerprint.
  A2  Limits: 5 MB, a short list of file types, and the content must match the type.
  A3  The file name is cleaned (no folders, no control characters).
  A4  Submitting with the attachment ties it to the handover note, with its fingerprint, for the approver to see.
  A5  Only the person who uploaded a file can attach it, and only to the case it was uploaded to.
  A6  An approver can open it; the download is a plain attachment, and every open is in the audit trail.
  A7  Roles that may not reveal personal data (Administrator, Policy Owner) cannot open it; Audit and Risk can, and it is logged.
"""
import base64
import hashlib

import pytest

from app.core.auth import create_token
from app.services.v2 import seed as v2seed

MAKER, MAKER2, APPR, AUD = "OP-9012", "OP-9020", "APR-3192", "AUD-5001"
CASE = "PEX-INV-0002"
PDF = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n"


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


def upload(client, uid, name, data, case=CASE, expect=201):
    r = client.post(f"/api/v2/cases/{case}/attachments", json={"name": name, "content_base64": base64.b64encode(data).decode()}, headers=H(uid))
    assert r.status_code == expect, f"{r.status_code} {r.text}"
    return r.json()


def test_upload_returns_fingerprint(client):
    a = upload(client, MAKER, "INV-2291.pdf", PDF)
    assert a["name"] == "INV-2291.pdf" and a["size"] == len(PDF)
    assert a["sha256"] == hashlib.sha256(PDF).hexdigest() and a["id"]


def test_too_big_is_refused(client):
    r = upload(client, MAKER, "big.pdf", b"%PDF" + b"0" * (5 * 1024 * 1024 + 1), expect=413)
    assert "5 MB" in r["error"]["message"]


@pytest.mark.parametrize("name,data", [("run.exe", b"MZ\x90\x00"), ("notes.pdf", b"MZ not a pdf"), ("pic.png", b"%PDF-1.4"), ("data.csv", b"a,b\n\x00\x01")])
def test_wrong_type_or_content_is_refused(client, name, data):
    r = upload(client, MAKER, name, data, expect=422)
    assert r["error"]["code"] in ("INVALID_INPUT", "VALIDATION", "INVALID")


def test_file_name_is_cleaned(client):
    a = upload(client, MAKER, "../../etc/pass\x07wd.pdf", PDF)
    assert a["name"] == "passwd.pdf"


def test_only_a_maker_can_upload(client):
    upload(client, AUD, "x.pdf", PDF, expect=403)


def test_submit_ties_attachment_to_handover(client):
    a = upload(client, MAKER, "INV-2291.pdf", PDF)
    r = client.post(f"/api/v2/cases/{CASE}/submit", json={"handover_note": "Checked with the client by phone.", "attachment_id": a["id"]}, headers=H(MAKER))
    assert r.status_code == 200, r.text
    h = client.get(f"/api/v2/cases/{CASE}/page", headers=H(APPR)).json()["handover"]
    assert h["attachment"]["id"] == a["id"] and h["attachment"]["sha256"] == a["sha256"] and h["attachment"]["name"] == "INV-2291.pdf"


def test_someone_elses_or_unknown_attachment_cannot_be_used(client):
    a = upload(client, MAKER2, "theirs.pdf", PDF)
    r = client.post(f"/api/v2/cases/{CASE}/submit", json={"handover_note": "x y z", "attachment_id": a["id"]}, headers=H(MAKER))
    assert r.status_code in (403, 404), r.text
    r = client.post(f"/api/v2/cases/{CASE}/submit", json={"handover_note": "x y z", "attachment_id": "nope"}, headers=H(MAKER))
    assert r.status_code == 404, r.text


def test_attachment_from_another_case_cannot_be_used(client):
    a = upload(client, MAKER, "other.pdf", PDF, case="PEX-INV-0001")
    r = client.post(f"/api/v2/cases/{CASE}/submit", json={"handover_note": "x y z", "attachment_id": a["id"]}, headers=H(MAKER))
    assert r.status_code in (403, 404, 422), r.text


def test_approver_can_open_and_it_is_audited(client):
    a = upload(client, MAKER, "INV-2291.pdf", PDF)
    client.post(f"/api/v2/cases/{CASE}/submit", json={"handover_note": "Checked with the client.", "attachment_id": a["id"]}, headers=H(MAKER))
    r = client.get(f"/api/v2/cases/{CASE}/attachments/{a['id']}/download", headers=H(APPR))
    assert r.status_code == 200 and r.content == PDF
    assert "attachment" in r.headers["content-disposition"] and "INV-2291.pdf" in r.headers["content-disposition"]
    assert r.headers.get("x-content-type-options") == "nosniff"
    ev = client.get(f"/api/v2/cases/{CASE}/timeline", headers=H(APPR)).text
    assert "Attachment opened" in ev


def test_roles_without_reveal_cannot_open(client):
    a = upload(client, MAKER, "INV-2291.pdf", PDF)
    for uid in ("ADM-0002", "POL-8001"):
        r = client.get(f"/api/v2/cases/{CASE}/attachments/{a['id']}/download", headers=H(uid))
        assert r.status_code == 403, uid
    assert client.get(f"/api/v2/cases/{CASE}/attachments/{a['id']}/download", headers=H(AUD)).status_code == 200
