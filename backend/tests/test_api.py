from datetime import date, timedelta

from conftest import DELHI, auth, make, register, tomorrow


def request_payload(**over):
    p = {"patient_name": "Private Person", "blood_group": "A+", "units_required": 1, "emergency_level": "Critical",
         "hospital_name": "Test General Hospital", "hospital_address": "2 Clinic Lane", "city": "Delhi",
         "state": "Delhi", "latitude": DELHI[0] + 0.02, "longitude": DELHI[1] + 0.02,
         "required_date": tomorrow(), "required_time": "14:30", "notes": "Ward 5, bed 12"}
    p.update(over)
    return p


# ---------- Registration / login -------------------------------------------------
def test_register_all_roles_and_me(client):
    for role in ("DONOR", "PATIENT", "HOSPITAL"):
        r = register(client, role, f"{role.lower()}@example.com")
        assert r.status_code == 201, r.text
        token = r.json()["access_token"]
        me = client.get("/api/auth/me", headers=auth(token)).json()
        assert me["role"] == role and me["profile"] is not None
        assert "password" not in str(me).lower()


def test_duplicate_email_case_insensitive(client):
    make(client, "DONOR", "Dup@Example.com")
    r = register(client, "DONOR", "dup@example.com")
    assert r.status_code == 400 and "already exists" in r.json()["detail"]


def test_admin_cannot_self_register(client):
    r = register(client, "ADMIN", "evil@example.com")
    assert r.status_code == 422 and "Administrator" in r.json()["detail"]


def test_validation_messages(client):
    assert register(client, "DONOR", "a@example.com", password="short").status_code == 422
    assert register(client, "DONOR", "b@example.com", password="lettersonly").status_code == 422
    r = register(client, "DONOR", "c@example.com", blood_group="Z+")
    assert r.status_code == 422 and "Blood group" in r.json()["detail"]
    r = register(client, "HOSPITAL", "h@example.com", latitude=None, longitude=None)
    assert r.status_code == 422 and "location" in r.json()["detail"].lower()


def test_login_and_role_mismatch(client):
    make(client, "DONOR", "d@example.com")
    ok = client.post("/api/auth/login", json={"email": "d@example.com", "password": "Secret123", "role": "DONOR"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/api/auth/login", json={"email": "d@example.com", "password": "nope12345"})
    assert bad.status_code == 401
    wrong_role = client.post("/api/auth/login", json={"email": "d@example.com", "password": "Secret123", "role": "PATIENT"})
    assert wrong_role.status_code == 400


def test_protected_routes_need_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth("garbage")).status_code == 401
    assert client.post("/api/requests", json=request_payload()).status_code == 401


# ---------- Full flow ------------------------------------------------------------
def test_full_request_match_accept_confirm_flow(client):
    hosp = make(client, "HOSPITAL", "hosp@example.com", name="Test General Hospital")
    hosp_id = client.get("/api/hospitals/me", headers=auth(hosp)).json()["id"]
    donor = make(client, "DONOR", "donor@example.com", name="Ravi Teja", blood_group="O+")
    far_donor = make(client, "DONOR", "far@example.com", blood_group="O-", latitude=19.07, longitude=72.87)
    incompatible = make(client, "DONOR", "incompat@example.com", blood_group="B+")
    recent = make(client, "DONOR", "recent@example.com", blood_group="A+",
                  last_donation_date=(date.today() - timedelta(days=10)).isoformat())
    patient = make(client, "PATIENT", "patient@example.com")

    r = client.post("/api/requests", json=request_payload(hospital_id=hosp_id, latitude=None, longitude=None,
                                                          hospital_name=None, hospital_address=None),
                    headers=auth(patient))
    assert r.status_code == 201, r.text
    req = r.json()
    assert req["matched_donors_count"] == 1          # only the nearby, compatible, eligible donor
    assert req["status"] == "DONOR_FOUND"
    assert req["hospital_name"] == "Test General Hospital"
    rid = req["id"]

    # Public view hides private details
    pub = client.get(f"/api/requests/{rid}").json()
    for k in ("patient_name", "notes", "latitude", "hospital_address"):
        assert k not in pub
    assert client.get("/api/requests").json()[0]["id"] == rid

    # Owner sees matches, but no phone before acceptance
    matches = client.get(f"/api/matching/{rid}", headers=auth(patient)).json()
    assert len(matches) == 1 and matches[0]["donor_phone"] is None and matches[0]["donor_name"] == "Ravi T."
    mid = matches[0]["match_id"]

    # Other users can't see matches or act on the match
    assert client.get(f"/api/matching/{rid}", headers=auth(far_donor)).status_code == 403
    assert client.post(f"/api/matching/{mid}/accept", headers=auth(far_donor)).status_code == 403
    assert client.post(f"/api/matching/{mid}/accept", headers=auth(patient)).status_code == 403

    # Donor sees the match and gets a notification
    my = client.get("/api/donors/matches", headers=auth(donor)).json()
    assert my[0]["match_id"] == mid and "hospital_address" not in my[0]
    notes = client.get("/api/notifications", headers=auth(donor)).json()
    assert notes["unread_count"] >= 1

    acc = client.post(f"/api/matching/{mid}/accept", headers=auth(donor))
    assert acc.status_code == 200, acc.text
    assert client.post(f"/api/matching/{mid}/accept", headers=auth(donor)).status_code == 400
    assert client.get(f"/api/requests/{rid}", headers=auth(patient)).json()["status"] == "DONOR_ACCEPTED"
    matches = client.get(f"/api/matching/{rid}", headers=auth(patient)).json()
    assert matches[0]["donor_phone"] == "+91 9000000000" and matches[0]["donor_name"] == "Ravi Teja"
    assert any(n["type"] == "DONOR_ACCEPTED" for n in
               client.get("/api/notifications", headers=auth(patient)).json()["notifications"])

    # Only the hospital (or admin) can confirm
    assert client.post(f"/api/matching/{mid}/confirm", json={"units": 1}, headers=auth(patient)).status_code == 403
    conf = client.post(f"/api/matching/{mid}/confirm", json={"units": 1}, headers=auth(hosp))
    assert conf.status_code == 200, conf.text
    assert conf.json()["request_status"] == "COMPLETED"

    me = client.get("/api/donors/me", headers=auth(donor)).json()
    assert me["available"] is False and me["total_donations"] == 1 and me["eligible"] is False
    assert len(client.get("/api/donors/donations", headers=auth(donor)).json()) == 1

    stats = client.get("/api/stats/public").json()
    assert stats["registered_donors"] == 4 and stats["fulfilled_requests"] == 1
    assert stats["confirmed_donations"] == 1 and stats["active_requests"] == 0 and stats["hospitals"] == 1
    _ = (incompatible, recent)


def test_new_donor_is_matched_to_open_request(client):
    patient = make(client, "PATIENT", "p@example.com")
    r = client.post("/api/requests", json=request_payload(), headers=auth(patient)).json()
    assert r["matched_donors_count"] == 0 and r["status"] == "SEARCHING"
    donor = make(client, "DONOR", "late@example.com", blood_group="A-")
    assert client.get(f"/api/requests/{r['id']}", headers=auth(patient)).json()["status"] == "DONOR_FOUND"
    assert len(client.get("/api/donors/matches", headers=auth(donor)).json()) == 1


def test_donor_volunteers_from_feed(client):
    patient = make(client, "PATIENT", "p@example.com")
    rid = client.post("/api/requests", json=request_payload(blood_group="O+"), headers=auth(patient)).json()["id"]
    wrong = make(client, "DONOR", "ab@example.com", blood_group="AB+", latitude=19.0, longitude=72.8)
    assert client.post(f"/api/requests/{rid}/respond", headers=auth(wrong)).status_code == 400
    ok = make(client, "DONOR", "ok@example.com", blood_group="O-", latitude=19.0, longitude=72.8)
    r = client.post(f"/api/requests/{rid}/respond", headers=auth(ok))
    assert r.status_code == 200, r.text


# ---------- Authorization --------------------------------------------------------
def test_cannot_cancel_someone_elses_request(client):
    p1 = make(client, "PATIENT", "p1@example.com")
    p2 = make(client, "PATIENT", "p2@example.com")
    rid = client.post("/api/requests", json=request_payload(), headers=auth(p1)).json()["id"]
    assert client.post(f"/api/requests/{rid}/cancel", headers=auth(p2)).status_code == 403
    donor = make(client, "DONOR", "d@example.com")
    assert client.post(f"/api/requests/{rid}/cancel", headers=auth(donor)).status_code == 403
    assert client.post(f"/api/requests/{rid}/cancel", headers=auth(p1)).status_code == 200
    assert client.post(f"/api/requests/{rid}/cancel", headers=auth(p1)).status_code == 400


def test_donor_cannot_create_request(client):
    donor = make(client, "DONOR", "d@example.com")
    assert client.post("/api/requests", json=request_payload(), headers=auth(donor)).status_code == 403


def test_request_validation(client):
    p = make(client, "PATIENT", "p@example.com")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    assert client.post("/api/requests", json=request_payload(required_date=yesterday), headers=auth(p)).status_code == 422
    assert client.post("/api/requests", json=request_payload(units_required=0), headers=auth(p)).status_code == 422
    assert client.post("/api/requests", json=request_payload(latitude=None, longitude=None), headers=auth(p)).status_code == 422


def _admin_token(client):
    from app.auth import create_access_token, get_password_hash
    from app.database import SessionLocal
    from app.models.user import User, UserRole
    db = SessionLocal()
    u = User(name="Admin", email="admin@example.com", phone="+91 9000000000", password_hash=get_password_hash("x1234567"),
             role=UserRole.ADMIN, is_verified=True)
    db.add(u); db.commit(); db.refresh(u)
    tok = create_access_token(u); db.close()
    return tok


def test_inventory_is_never_fabricated_and_is_protected(client):
    h1 = make(client, "HOSPITAL", "h1@example.com")
    h2 = make(client, "HOSPITAL", "h2@example.com")
    hid = client.get("/api/hospitals/me", headers=auth(h1)).json()["id"]
    assert client.get(f"/api/hospitals/{hid}/inventory", headers=auth(h1)).json() == []
    body = {"blood_group": "O-", "available_units": 7, "reserved_units": 1, "reason": "Count"}
    assert client.post(f"/api/hospitals/{hid}/inventory", json=body).status_code == 401
    assert client.post(f"/api/hospitals/{hid}/inventory", json=body, headers=auth(h2)).status_code == 403
    r = client.post(f"/api/hospitals/{hid}/inventory", json=body, headers=auth(h1))
    assert r.status_code == 200 and r.json()[0]["available_units"] == 7 and r.json()[0]["component"] == "WHOLE_BLOOD"
    assert len(client.get(f"/api/hospitals/{hid}/inventory/history", headers=auth(h1)).json()) == 1

    # Unverified facility: stock is hidden from the public, visible to the facility itself.
    pub = {h["id"]: h for h in client.get("/api/hospitals").json()}[hid]
    assert pub["inventory"] == [] and pub["stock_hidden_until_verified"] is True and pub["inventory_reported"] is False
    assert client.get(f"/api/hospitals/{hid}/inventory").json() == []
    assert client.get(f"/api/hospitals/{hid}/inventory", headers=auth(h1)).json()[0]["available_units"] == 7

    # After admin verification the stock is published.
    admin = _admin_token(client)
    uid = client.get("/api/auth/me", headers=auth(h1)).json()["id"]
    assert client.put(f"/api/admin/users/{uid}/verify", headers=auth(admin)).status_code == 200
    pub = {h["id"]: h for h in client.get("/api/hospitals").json()}[hid]
    assert pub["verified"] is True and pub["inventory_reported"] is True and pub["inventory"][0]["available_units"] == 7


def test_inventory_components(client):
    h = make(client, "HOSPITAL", "h@example.com")
    hid = client.get("/api/hospitals/me", headers=auth(h)).json()["id"]
    for comp, n in [("WHOLE_BLOOD", 4), ("PRBC", 6), ("PLATELETS", 2), ("PLASMA", 9)]:
        r = client.put(f"/api/hospitals/{hid}/inventory", json={"blood_group": "A+", "component": comp, "available_units": n},
                       headers=auth(h))
        assert r.status_code == 200, r.text
    rows = client.get(f"/api/hospitals/{hid}/inventory", headers=auth(h)).json()
    assert [(x["component"], x["available_units"]) for x in rows] == [("WHOLE_BLOOD", 4), ("PRBC", 6), ("PLATELETS", 2), ("PLASMA", 9)]
    assert rows[1]["component_label"] == "Packed Red Cells"
    bad = client.put(f"/api/hospitals/{hid}/inventory", json={"blood_group": "A+", "component": "SERUM", "available_units": 1},
                     headers=auth(h))
    assert bad.status_code == 422
    # Only red-cell products can be issued against a request
    rid = client.post("/api/requests", json=request_payload(blood_group="A+"), headers=auth(h)).json()["id"]
    r = client.post(f"/api/hospitals/{hid}/requests/{rid}/fulfill-from-stock",
                    json={"units": 1, "blood_group": "A+", "component": "PLASMA"}, headers=auth(h))
    assert r.status_code == 400
    r = client.post(f"/api/hospitals/{hid}/requests/{rid}/fulfill-from-stock",
                    json={"units": 1, "blood_group": "A+", "component": "PRBC"}, headers=auth(h))
    assert r.status_code == 200
    rows = client.get(f"/api/hospitals/{hid}/inventory", headers=auth(h)).json()
    assert {x["component"]: x["available_units"] for x in rows}["PRBC"] == 5


def test_fulfill_from_stock(client):
    h = make(client, "HOSPITAL", "h@example.com")
    hid = client.get("/api/hospitals/me", headers=auth(h)).json()["id"]
    client.post(f"/api/hospitals/{hid}/inventory", json={"blood_group": "O-", "available_units": 3}, headers=auth(h))
    rid = client.post("/api/requests", json=request_payload(blood_group="A+", units_required=2),
                      headers=auth(h)).json()["id"]
    bad = client.post(f"/api/hospitals/{hid}/requests/{rid}/fulfill-from-stock", json={"units": 5, "blood_group": "O-"},
                      headers=auth(h))
    assert bad.status_code == 400
    ok = client.post(f"/api/hospitals/{hid}/requests/{rid}/fulfill-from-stock", json={"units": 2, "blood_group": "O-"},
                     headers=auth(h))
    assert ok.status_code == 200
    assert client.get(f"/api/hospitals/{hid}/inventory", headers=auth(h)).json()[0]["available_units"] == 1


def test_admin_endpoints_require_admin(client):
    donor = make(client, "DONOR", "d@example.com")
    assert client.get("/api/admin/dashboard", headers=auth(donor)).status_code == 403


def test_donor_search_is_privacy_safe(client):
    make(client, "DONOR", "d@example.com", name="Secret Name", blood_group="O-")
    res = client.get("/api/donors", params={"compatible_with": "A+", "lat": DELHI[0], "lng": DELHI[1]}).json()
    assert res["count"] == 1
    d = res["donors"][0]
    assert d["display_name"] == "Secret N." and "phone" not in d and "latitude" not in d and "email" not in d


def test_websocket_requires_token(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws") as ws:
            ws.receive_text()
    token = make(client, "DONOR", "ws@example.com")
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.send_text("ping")
        assert ws.receive_json()["event"] == "PONG"
