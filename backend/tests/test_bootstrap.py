from conftest import auth, make

from app.bootstrap import ensure_admin, ensure_admin_from_env
from app.config import settings


def _env(monkeypatch, **kw):
    for key in ("ADMIN_EMAIL", "ADMIN_PASSWORD", "ADMIN2_EMAIL", "ADMIN2_PASSWORD"):
        monkeypatch.setattr(settings, key, kw.get(key, ""))


def _login(client, email, pw):
    return client.post("/api/auth/login", json={"email": email, "password": pw, "role": "ADMIN"})


def test_admin_created_from_env_and_can_log_in(client, monkeypatch):
    _env(monkeypatch)
    assert ensure_admin_from_env() == {"ADMIN": "skipped", "ADMIN2": "skipped"}
    _env(monkeypatch, ADMIN_EMAIL="Boss@Example.com", ADMIN_PASSWORD="AdminPass123")
    assert ensure_admin_from_env()["ADMIN"] == "created"
    assert ensure_admin_from_env()["ADMIN"] == "unchanged"  # idempotent on every restart
    r = _login(client, "boss@example.com", "AdminPass123")
    assert r.status_code == 200
    assert client.get("/api/admin/dashboard", headers=auth(r.json()["access_token"])).status_code == 200
    _env(monkeypatch, ADMIN_EMAIL="boss@example.com", ADMIN_PASSWORD="NewPass4567")
    assert ensure_admin_from_env()["ADMIN"] == "updated"
    assert _login(client, "boss@example.com", "NewPass4567").status_code == 200


def test_two_team_admins(client, monkeypatch):
    _env(monkeypatch, ADMIN_EMAIL="first@example.com", ADMIN_PASSWORD="FirstPass123",
         ADMIN2_EMAIL="second@example.com", ADMIN2_PASSWORD="SecondPass456")
    assert ensure_admin_from_env() == {"ADMIN": "created", "ADMIN2": "created"}
    assert _login(client, "first@example.com", "FirstPass123").status_code == 200
    assert _login(client, "second@example.com", "SecondPass456").status_code == 200
    assert _login(client, "second@example.com", "FirstPass123").status_code == 401  # separate passwords


def test_admin_env_never_takes_over_other_accounts(client):
    make(client, "DONOR", "donor@example.com")
    assert ensure_admin("donor@example.com", "AdminPass123") == "conflict"
    me = client.post("/api/auth/login", json={"email": "donor@example.com", "password": "Secret123"}).json()
    assert me["role"] == "DONOR"


def test_admin_env_rejects_weak_password(client):
    assert ensure_admin("boss@example.com", "short") == "invalid"
