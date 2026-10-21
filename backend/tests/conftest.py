import os
from datetime import date, timedelta

import pytest

# Use a dedicated test database. Default: throwaway SQLite file.
# To test against PostgreSQL:  TEST_DATABASE_URL=postgresql://user:pass@localhost/bloodbridge_test pytest
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test_bloodbridge.db")
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret-not-for-production-use-0123456789"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

_db_name = engine.url.database or ""
assert engine.dialect.name == "sqlite" or _db_name.endswith("_test"), \
    "Refusing to run tests: TEST_DATABASE_URL must point to a database whose name ends in _test."


@pytest.fixture(autouse=True)
def fresh_db():
    # Safe: only ever runs against the dedicated *_test / SQLite test database (asserted above).
    if engine.dialect.name == "postgresql":
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    else:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def tomorrow():
    return (date.today() + timedelta(days=1)).isoformat()


DELHI = (28.6139, 77.2090)


def register(client, role="DONOR", email=None, **over):
    payload = {
        "name": over.pop("name", f"Test {role.title()}"),
        "email": email or f"{role.lower()}{abs(hash(str(over))) % 100000}@example.com",
        "phone": "+91 9000000000",
        "password": "Secret123",
        "role": role,
        "city": "Delhi",
        "state": "Delhi",
        "pincode": "110001",
    }
    if role == "DONOR":
        payload.update(blood_group="O+", latitude=DELHI[0], longitude=DELHI[1], meets_basic_criteria=True,
                       available=True, date_of_birth="1995-01-01")
    if role == "PATIENT":
        payload.update(blood_group="A+")
    if role == "HOSPITAL":
        payload.update(address="1 Test Road, New Delhi", latitude=DELHI[0] + 0.01, longitude=DELHI[1] + 0.01,
                       facility_type="HOSPITAL")
    payload.update(over)
    r = client.post("/api/auth/register", json=payload)
    return r


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def make(client, role, email, **over):
    r = register(client, role, email, **over)
    assert r.status_code == 201, r.text
    return r.json()["access_token"]
