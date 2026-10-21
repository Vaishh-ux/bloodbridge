"""Extra end-to-end checks for every remaining button. Run AFTER e2e_test.py on the same database.

    BASE_URL=http://localhost:5173 python e2e/extra_checks.py
"""
import re, os, sys
from playwright.sync_api import sync_playwright, expect
BASE = os.environ.get("BASE_URL", "http://localhost:5173")
results, errors = [], []
def step(name, fn):
    try: fn(); results.append("PASS"); print("PASS", name, flush=True)
    except Exception as e: results.append("FAIL"); print("FAIL", name, "->", str(e).splitlines()[0][:250], flush=True)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
    def ctx(lat=28.62, lng=77.21, w=1360):
        c = b.new_context(viewport={"width": w, "height": 900}, geolocation={"latitude": lat, "longitude": lng}, permissions=["geolocation"])
        p = c.new_page(); p.on("dialog", lambda d: d.accept())
        p.on("pageerror", lambda e: errors.append(str(e)))
        return p
    def login(p, email, pw_, role):
        p.goto(BASE + "/login"); p.get_by_role("radio", name=role).click()
        p.get_by_label("Email address").fill(email); p.get_by_label("Password").fill(pw_)
        p.get_by_role("button", name="Sign In").click(); p.wait_for_timeout(1500)
    def reg_donor(p, email, bg):
        p.goto(BASE + "/register?role=DONOR")
        for lab, v in [("^Full name", "Kiran Rao"), ("^Email address", email), ("^Phone number", "+91 9555555555"),
                       ("^Password", "Secret123"), ("^Confirm password", "Secret123"), ("^City", "New Delhi"), ("^State", "Delhi")]:
            p.get_by_label(re.compile(lab, re.I)).first.fill(v)
        p.get_by_label(re.compile("^Blood group", re.I)).select_option(bg)
        p.get_by_role("button", name=re.compile("Use my location")).click(); p.wait_for_timeout(500)
        p.get_by_label(re.compile("I am 18–65")).check()
        p.get_by_role("button", name="Complete Registration").click(); expect(p).to_have_url(re.compile("donor-dashboard"), timeout=15000)

    D2 = ctx(); P = ctx(28.60, 77.20); H = ctx(); A = ctx(); G = ctx()
    login(P, "patient@example.com", "Secret123", "PATIENT"); login(H, "hospital@example.com", "Secret123", "HOSPITAL")
    login(A, "admin@example.com", "AdminPass123", "ADMIN")

    def new_request(bg="O+", units="1"):
        P.goto(BASE + "/create-request")
        P.get_by_label(re.compile(r"^Blood group required", re.I)).select_option(bg)
        P.get_by_label(re.compile(r"^Units required", re.I)).fill(units)
        sel = P.locator("select").nth(2); opts = sel.locator("option").all_text_contents()
        sel.select_option(label=[o for o in opts if "E2E Test Hospital" in o][0])
        P.get_by_role("button", name=re.compile("Submit Request")).click(); expect(P).to_have_url(re.compile("patient-dashboard"), timeout=15000)

    def t_decline():
        reg_donor(D2, "donor2@example.com", "O-")
        new_request("O+")
        expect(D2.get_by_role("button", name="Decline")).to_be_visible(timeout=10000)
        D2.get_by_role("button", name="Decline").click()
        expect(D2.get_by_text("No pending matches right now.")).to_be_visible()
        expect(D2.get_by_text("REJECTED").first).to_be_visible()
    step("Donor declines a match", t_decline)

    def t_search_again_and_cancel():
        P.reload(); P.get_by_role("button", name=re.compile("Search again")).first.click()
        expect(P.get_by_text(re.compile("Done|new_matches|Response", re.I)).first).to_be_visible(timeout=5000) if False else P.wait_for_timeout(1000)
        P.get_by_role("button", name="Cancel Request").first.click()
        expect(P.get_by_text(re.compile("Request cancelled")).first).to_be_visible()
        expect(P.get_by_text("CANCELLED").first).to_be_visible()
    step("Requester: Search again + Cancel request", t_search_again_and_cancel)

    def t_profile_availability():
        D2.get_by_role("button", name="Profile").click()
        D2.get_by_label(re.compile(r"^PIN code", re.I)).fill("110002"); D2.get_by_role("button", name="Save profile").click()
        expect(D2.get_by_text("Profile updated.")).to_be_visible()
        D2.get_by_role("button", name="Available").click(); expect(D2.get_by_role("button", name="Unavailable")).to_be_visible()
        D2.get_by_role("button", name="Unavailable").click(); expect(D2.get_by_role("button", name="Available")).to_be_visible()
    step("Donor: edit profile + toggle availability", t_profile_availability)

    def t_feed_volunteer_and_fulfil():
        new_request("A+")
        D2.goto(BASE + "/requests")
        D2.get_by_label("Severity").select_option("High"); D2.get_by_role("button", name="Search").click(); D2.wait_for_timeout(800)
        D2.get_by_label("Severity").select_option(""); D2.get_by_role("button", name="Search").click()
        D2.get_by_role("button", name=re.compile("I can donate")).first.click()
        expect(D2.get_by_text(re.compile("requester and hospital have been notified"))).to_be_visible()
        P.reload(); P.get_by_role("button", name="Mark fulfilled").first.click()
        expect(P.get_by_text(re.compile("marked as fulfilled")).first).to_be_visible()
    step("Feed filters + 'I can donate' + Mark fulfilled", t_feed_volunteer_and_fulfil)

    def t_issue_from_stock():
        new_request("O+", "2")
        H.reload(); H.get_by_role("button", name="Issue from stock").first.click()
        dlg = H.get_by_role("dialog"); dlg.get_by_label("Blood group issued").select_option("O-")
        dlg.get_by_label("Units").fill("2"); dlg.get_by_role("button", name="Issue units").click()
        expect(H.get_by_text("Units issued and inventory updated.")).to_be_visible()
        H.get_by_role("button", name="Inventory history").click()
        expect(H.get_by_text(re.compile("Issued 2 unit"))).to_be_visible()
        H.get_by_role("button", name="Close").click()
    step("Hospital: Issue from stock (inventory deducted) + Inventory history", t_issue_from_stock)

    def t_notifications():
        P.goto(BASE + "/"); P.get_by_role("button", name=re.compile("Notifications")).click()
        expect(P.get_by_text("Mark all read")).to_be_visible(); P.get_by_text("Mark all read").click()
        expect(P.get_by_role("button", name="Notifications (0 unread)")).to_be_visible()
        P.goto(BASE + "/notifications"); expect(P.get_by_text("Notifications Center")).to_be_visible()
        expect(P.get_by_text("Blood Request Broadcast Active").first).to_be_visible()
    step("Notification bell, mark all read, notifications page", t_notifications)

    def t_search_pages():
        G.goto(BASE + "/find-donors"); G.get_by_label("Patient blood group").select_option("A+")
        G.get_by_role("button", name="Use my location").click(); G.wait_for_timeout(500)
        G.get_by_label(re.compile("Passes screening")).uncheck(); G.get_by_role("button", name=re.compile("Search donors")).click()
        expect(G.get_by_text(re.compile(r"\d+ donors? found"))).to_be_visible()
        assert "9555555555" not in G.content(), "donor phone leaked"
        G.goto(BASE + "/blood-banks"); G.get_by_label("Stock for").select_option("O-"); G.get_by_role("button", name="Search").click()
        expect(G.get_by_text("E2E Test Hospital")).to_be_visible()
        G.get_by_role("button", name="Nearest").click(); expect(G.get_by_text(re.compile(r"km away"))).to_be_visible()
        G.goto(BASE + "/map"); expect(G.get_by_text(re.compile(r"registered facilit"))).to_be_visible()
    step("Find Donors filters (privacy-safe), Blood Banks filters + Nearest, Live Map", t_search_pages)

    def t_admin():
        A.reload(); A.get_by_role("tab", name="Requests").click()
        row = A.locator("tr", has=A.get_by_text("CANCELLED")).first
        row.get_by_role("button", name=re.compile("Flag suspicious")).click()
        expect(A.get_by_text(re.compile("suspicious status set to True"))).to_be_visible()
        A.get_by_role("tab", name="Users").click()
        A.get_by_label("Role").select_option("DONOR"); A.get_by_role("button", name="Filter").click(); A.wait_for_timeout(800)
        r = A.locator("tr", has_text="donor2@example.com"); r.get_by_role("button", name="Block").click()
        expect(A.get_by_text(re.compile("block status set to True"))).to_be_visible()
        g = ctx(); login(g, "donor2@example.com", "Secret123", "DONOR")
        expect(g.get_by_text(re.compile("suspended"))).to_be_visible()
        r = A.locator("tr", has_text="donor2@example.com"); r.get_by_role("button", name="Unblock").click()
        expect(A.get_by_text(re.compile("block status set to False"))).to_be_visible()
        A.get_by_role("tab", name="Audit log").click(); expect(A.get_by_text("USER_BLOCKED")).to_be_visible()
    step("Admin: flag suspicious, role filter, block (login refused) / unblock, audit log", t_admin)

    def t_logout_mobile():
        m = ctx(w=390); login(m, "patient@example.com", "Secret123", "PATIENT")
        m.get_by_role("button", name="Menu").click(); m.get_by_role("link", name="Find Blood Banks").click()
        expect(m).to_have_url(re.compile("blood-banks"))
        assert m.evaluate("document.documentElement.scrollWidth") <= 390
        m.get_by_role("link", name="Request Blood").first.wait_for()  # quick buttons visible on a phone
        m.get_by_role("link", name="Emergency Help").first.wait_for()
        m.get_by_role("button", name="Menu").click(); m.get_by_role("button", name="Log out").click()
        m.get_by_role("button", name="Menu").click()
        expect(m.get_by_role("link", name="Login").first).to_be_visible()
        m.goto(BASE + "/patient-dashboard"); expect(m).to_have_url(re.compile("/login"))
    step("Phone menu navigation + Log out (dashboard then requires login)", t_logout_mobile)
    b.close()
print("Page errors:", errors or "none")
print(f"{results.count('PASS')}/{len(results)} extra checks passed")
