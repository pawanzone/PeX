"""Sign-in screen: acceptance tests written from the requirements.

  R1  The app opens on a sign-in screen; a person signs in with a user and the shared demo password.
  R2  A wrong password or unknown user is refused, with no hint which part was wrong.
  R3  Sign-in works only where demo login is on (production = bank SSO, not built).
  R4  The existing persona switch keeps working for a signed-in demo (Switch Role).
  R5  The demo password comes from configuration, not a hard-coded constant in the screen.
"""
import pytest

from app.config import settings


def signin(client, uid, pw):
    return client.post("/api/auth/signin", json={"user_id": uid, "password": pw})


def test_correct_password_returns_a_working_token(client):
    r = signin(client, "SUP-2001", settings.PEX_DEMO_PASSWORD)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["user_id"] == "SUP-2001" and body["access_token"]
    me = client.get("/api/v2/me", headers={"Authorization": "Bearer " + body["access_token"]})
    assert me.status_code == 200 and me.json()["user"]["user_id"] == "SUP-2001" if "user" in me.json() else me.status_code == 200


def test_wrong_password_and_unknown_user_look_the_same(client):
    a = signin(client, "SUP-2001", "not-the-password")
    b = signin(client, "NOPE-0000", settings.PEX_DEMO_PASSWORD)
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_empty_password_is_refused(client):
    assert signin(client, "SUP-2001", "").status_code == 401


def test_signin_is_off_when_demo_login_is_off(client, monkeypatch):
    monkeypatch.setattr(settings, "PEX_DEMO", False)
    assert signin(client, "SUP-2001", settings.PEX_DEMO_PASSWORD).status_code == 404


def test_switch_role_still_works(client):
    assert client.post("/api/auth/login", json={"user_id": "APR-3192"}).status_code == 200


def test_demo_password_is_configurable(client, monkeypatch):
    monkeypatch.setattr(settings, "PEX_DEMO_PASSWORD", "another-secret")
    assert signin(client, "SUP-2001", "another-secret").status_code == 200
    assert signin(client, "SUP-2001", "demo1234").status_code == 401
