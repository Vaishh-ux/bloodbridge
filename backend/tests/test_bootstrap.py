from conftest import auth, make

from app.bootstrap import ensure_admin_from_env
from app.config import settings


def _set(monkeypatch, email, password):
    monkeypatch.setattr(settings, "ADMIN_EMAIL", email)
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", password)


def test_admin_created_from_env_and_can_log_in(client, monkeypatch):
    _set(monkeypatch, "", "")
    assert ensure_admin_from_env() == "skipped"
    _set(monkeypatch, "Boss@Example.com", "AdminPass123")
    assert ensure_admin_from_env() == "created"
    assert ensure_admin_from_env() == "unchanged"  # idempotent on every restart
    r = client.post("/api/auth/login", json={"email": "boss@example.com", "password": "AdminPass123", "role": "ADMIN"})
    assert r.status_code == 200
    assert client.get("/api/admin/dashboard", headers=auth(r.json()["access_token"])).status_code == 200
    _set(monkeypatch, "boss@example.com", "NewPass4567")
    assert ensure_admin_from_env() == "updated"
    assert client.post("/api/auth/login", json={"email": "boss@example.com", "password": "NewPass4567"}).status_code == 200


def test_admin_env_never_takes_over_other_accounts(client, monkeypatch):
    make(client, "DONOR", "donor@example.com")
    _set(monkeypatch, "donor@example.com", "AdminPass123")
    assert ensure_admin_from_env() == "conflict"
    me = client.post("/api/auth/login", json={"email": "donor@example.com", "password": "Secret123"}).json()
    assert me["role"] == "DONOR"


def test_admin_env_rejects_weak_password(client, monkeypatch):
    _set(monkeypatch, "boss@example.com", "short")
    assert ensure_admin_from_env() == "invalid"
