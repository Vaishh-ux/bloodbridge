"""Browser end-to-end test (3 simultaneous users).

Prereqs: backend on :8000 with an EMPTY database, an admin created with
  ADMIN_PASSWORD=AdminPass123 python create_admin.py --email admin@example.com
frontend dev server on :5173, and  pip install playwright && playwright install chromium
Run:  python e2e/e2e_test.py ./e2e-screenshots
"""
import os, re, sys, time
from playwright.sync_api import sync_playwright, expect

BASE = __import__("os").environ.get("BASE_URL", "http://localhost:5173")
SHOTS = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(SHOTS, exist_ok=True)
errors = []
results = []

def step(name, fn):
    try:
        fn(); results.append(("PASS", name)); print("PASS", name, flush=True)
    except Exception as e:
        results.append(("FAIL", name)); print("FAIL", name, "->", str(e).splitlines()[0][:300], flush=True)
        raise

def ctx(browser, lat, lng):
    c = browser.new_context(viewport={"width": 1360, "height": 900}, geolocation={"latitude": lat, "longitude": lng},
                            permissions=["geolocation"])
    p = c.new_page()
    p.on("console", lambda m: m.type == "error" and "tile.openstreetmap" not in m.text and "ERR_" not in m.text and errors.append(m.text))
    p.on("pageerror", lambda e: errors.append(str(e)))
    return p

def fill(page, label, value):
    page.get_by_label(re.compile(label, re.I)).first.fill(value)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
    H = ctx(b, 28.6139, 77.2090); D = ctx(b, 28.6250, 77.2200); P = ctx(b, 28.60, 77.20)

    def reg_hospital():
        H.goto(BASE + "/register")
        H.get_by_role("radio", name="Hospital / Blood Bank").click()
        fill(H, r"^Hospital / blood bank name", "E2E Test Hospital")
        fill(H, r"^Email address", "hospital@example.com")
        fill(H, r"^Phone number", "+91 9111111111")
        H.get_by_label(re.compile(r"^Facility type", re.I)).select_option("BLOOD_BANK")
        fill(H, r"^Password", "Secret123"); fill(H, r"^Confirm password", "Secret123")
        fill(H, r"^Facility address", "1 Test Marg, Connaught Place")
        fill(H, r"^City", "New Delhi"); fill(H, r"^State", "Delhi"); fill(H, r"^PIN code", "110001")
        H.get_by_role("button", name=re.compile("Use my location")).click()
        expect(H.get_by_text(re.compile(r"Set: 28\.6139"))).to_be_visible()
        H.get_by_role("button", name="Complete Registration").click()
        expect(H).to_have_url(re.compile("/hospital-dashboard"), timeout=15000)
        expect(H.get_by_text("Awaiting admin verification")).to_be_visible()
    step("Hospital registers via UI (geolocation) -> hospital dashboard", reg_hospital)

    def inventory():
        H.get_by_label("Whole Blood O- available units").fill("5")
        H.get_by_label("Whole Blood O+ available units").fill("2")
        H.get_by_role("tab", name=re.compile("Packed Red Cells")).click()
        H.get_by_label("Packed Red Cells B+ available units").fill("3")
        H.get_by_role("tab", name=re.compile("Plasma")).click()
        H.get_by_label("Plasma AB+ available units").fill("4")
        H.get_by_placeholder(re.compile("Reason")).fill("Opening count")
        H.get_by_role("button", name=re.compile(r"Save Stock Changes \(4\)")).click()
        expect(H.get_by_text(re.compile("Saved 4 stock line"))).to_be_visible()
        H.screenshot(path=f"{SHOTS}/1_hospital_dashboard.png", full_page=True)
    step("Hospital saves stock per component (whole blood, packed red cells, plasma)", inventory)

    def reg_donor():
        D.goto(BASE + "/register?role=DONOR")
        fill(D, r"^Full name", "Ravi Teja"); fill(D, r"^Email address", "donor@example.com")
        fill(D, r"^Phone number", "+91 9222222222"); fill(D, r"^Password", "Secret123"); fill(D, r"^Confirm password", "Secret123")
        D.get_by_label(re.compile(r"^Blood group", re.I)).select_option("O+")
        D.get_by_label(re.compile(r"^Date of birth", re.I)).fill("1995-05-05")
        fill(D, r"^City", "New Delhi"); fill(D, r"^State", "Delhi")
        D.get_by_role("button", name=re.compile("Use my location")).click()
        expect(D.get_by_text(re.compile(r"Set: 28\.625"))).to_be_visible()
        D.get_by_label(re.compile("I am 18–65")).check()
        D.screenshot(path=f"{SHOTS}/2_register_donor.png", full_page=True)
        D.get_by_role("button", name="Complete Registration").click()
        expect(D).to_have_url(re.compile("/donor-dashboard"), timeout=15000)
        expect(D.get_by_text("No pending matches right now.")).to_be_visible()
    step("Donor registers via UI -> donor dashboard", reg_donor)

    def dup_email():
        P.goto(BASE + "/register?role=PATIENT")
        fill(P, r"^Full name", "Someone"); fill(P, r"^Email address", "donor@example.com")
        fill(P, r"^Phone number", "+91 9333333333"); fill(P, r"^Password", "Secret123"); fill(P, r"^Confirm password", "Secret123")
        fill(P, r"^City", "New Delhi"); fill(P, r"^State", "Delhi")
        P.get_by_role("button", name="Complete Registration").click()
        expect(P.get_by_text("An account with this email already exists. Please log in.")).to_be_visible()
    step("Duplicate email shows the real server error (not a generic failure)", dup_email)

    def guest_request():
        P.goto(BASE + "/")
        P.get_by_role("link", name=re.compile("Emergency Blood Request")).click()
        expect(P).to_have_url(re.compile("/create-request"))
        expect(P.get_by_text("Your contact details")).to_be_visible()
        fill(P, r"^Your name", "Meera Patient"); fill(P, r"^Phone number", "+91 9333333333")
        fill(P, r"^Email", "patient@example.com"); fill(P, r"^Create a password", "Secret123")
        P.get_by_label(re.compile(r"^Blood group required", re.I)).select_option("A+")
        P.get_by_label(re.compile(r"^Emergency level", re.I)).select_option("Critical")
        fill(P, r"^Patient name", "Meera's father")
        sel = P.locator("select").nth(2)
        opts = sel.locator("option").all_text_contents()
        sel.select_option(label=[o for o in opts if "E2E Test Hospital" in o][0])
        fill(P, r"^Additional notes", "Ward 3")
        P.screenshot(path=f"{SHOTS}/3_guest_request.png", full_page=True)
        P.get_by_role("button", name=re.compile("Submit Request")).click()
        expect(P).to_have_url(re.compile("/patient-dashboard"), timeout=15000)
        expect(P.get_by_text(re.compile("matched 1 compatible donor")).first).to_be_visible()
        expect(P.get_by_text("Donors notified").first).to_be_visible()
    step("Logged-out visitor submits an emergency request in ONE step (account auto-created) -> 1 donor matched", guest_request)

    def donor_realtime():
        # no reload: WebSocket push should surface the match
        expect(D.get_by_text("Emergency Blood Request Available").first).to_be_visible(timeout=10000)
        expect(D.get_by_role("button", name="Accept")).to_be_visible(timeout=10000)
        D.screenshot(path=f"{SHOTS}/4_donor_realtime_match.png", full_page=True)
    step("Donor receives the match in real time (no page refresh)", donor_realtime)

    def hospital_realtime():
        expect(H.get_by_text("Meera's father")).to_be_visible(timeout=10000)
    step("Hospital sees new request in real time", hospital_realtime)

    def public_privacy():
        g = b.new_page()
        g.goto(BASE + "/requests")
        expect(g.get_by_text(re.compile(r"Live Emergency Blood Requests \(1\)"))).to_be_visible()
        body = g.content()
        assert "Meera's father" not in body and "Ward 3" not in body, "private data leaked on public feed"
        g.screenshot(path=f"{SHOTS}/5_public_feed.png", full_page=True)
        g.close()
    step("Public feed shows request without patient name/notes", public_privacy)

    def labels():
        for name in ["Emergency Help", "Request Blood", "My Dashboard", "Donate Blood", "Find Blood Banks"]:
            expect(D.get_by_role("link", name=name).first).to_be_visible()
        D.screenshot(path=f"{SHOTS}/13_header_1360.png")
        for w in (1024, 1280, 1920):
            D.set_viewport_size({"width": w, "height": 900})
            hh = D.evaluate("document.querySelector('header > div').getBoundingClientRect().height")
            assert hh <= 64.5, f"header row wraps at {w}px ({hh}px)"
        D.set_viewport_size({"width": 1360, "height": 900})
    step("Quick navigation always labelled (Emergency Help, Request Blood, My Dashboard, Donate, Blood Banks) at 1024-1920px", labels)

    def accept():
        D.get_by_role("button", name="Accept").click()
        expect(D.get_by_text("Requests you accepted")).to_be_visible()
        expect(D.get_by_text("1 Test Marg, Connaught Place")).to_be_visible()
    step("Donor accepts; hospital address revealed to donor", accept)

    def patient_realtime():
        expect(P.get_by_text("Donor accepted").first).to_be_visible(timeout=10000)
        P.get_by_role("button", name="View Matched Donors").click()
        expect(P.get_by_role("link", name=re.compile(r"\+91 9222222222"))).to_be_visible()
        expect(P.get_by_role("dialog").get_by_text("Ravi Teja")).to_be_visible()
        P.screenshot(path=f"{SHOTS}/6_patient_donor_accepted.png", full_page=True)
        P.get_by_role("button", name="Close").click()
    step("Patient sees 'Donor accepted' in real time and donor's phone after acceptance", patient_realtime)

    def confirm():
        H.reload()
        H.get_by_role("button", name="Confirm Donation").first.click()
        H.get_by_role("dialog").get_by_role("button", name="Confirm Donation").click()
        expect(H.get_by_text("Donation confirmed.")).to_be_visible()
        expect(H.get_by_text("Completed").first).to_be_visible()
    step("Hospital confirms donation -> request completed", confirm)

    def patient_completed():
        expect(P.get_by_text("Request History")).to_be_visible(timeout=10000)
        expect(P.get_by_text("No Active Blood Requests")).to_be_visible()
    step("Patient dashboard moves request to history (real time)", patient_completed)

    def donor_after():
        D.reload()
        expect(D.get_by_role("button", name="Unavailable")).to_be_visible()
        expect(D.get_by_text(re.compile("Next donation possible in"))).to_be_visible()
        D.screenshot(path=f"{SHOTS}/7_donor_after_donation.png", full_page=True)
    step("Donor now unavailable + interval shown; donation history recorded", donor_after)

    def home_stats():
        g = b.new_page(viewport={"width": 1360, "height": 900}); g.goto(BASE + "/")
        expect(g.get_by_text("Fulfilled Requests")).to_be_visible()
        expect(g.get_by_text("0 hospitals · 1 blood bank")).to_be_visible()
        g.screenshot(path=f"{SHOTS}/8_home_live_stats.png")
        g.goto(BASE + "/blood-banks")
        expect(g.get_by_text("E2E Test Hospital")).to_be_visible()
        expect(g.get_by_text(re.compile("will be shown once a Blood Bridge administrator verifies"))).to_be_visible()
        g.screenshot(path=f"{SHOTS}/9_blood_banks.png", full_page=True)
        g.goto(BASE + "/find-donors"); g.get_by_role("button", name=re.compile("Search donors")).click()
        expect(g.get_by_text(re.compile("No matching donors found|donor found"))).to_be_visible()
        g.goto(BASE + "/map"); expect(g.get_by_text("Live Emergency Map")).to_be_visible()
        g.goto(BASE + "/emergency"); expect(g.get_by_text("112").first).to_be_visible()
        g.goto(BASE + "/donate"); expect(g.get_by_text("Haemoglobin at least 12.5 g/dL", exact=False)).to_be_visible()
        g.set_viewport_size({"width": 390, "height": 844}); g.goto(BASE + "/")
        g.screenshot(path=f"{SHOTS}/10_mobile_home.png", full_page=False)
        sw = g.evaluate("document.documentElement.scrollWidth"); assert sw <= 390, f"horizontal scroll on mobile: {sw}"
    step("Home live stats, blood banks, donors, map, emergency, donate, mobile layout", home_stats)

    def login_flow():
        g = b.new_context().new_page(); g.goto(BASE + "/login")
        g.get_by_role("radio", name="PATIENT").click()
        g.get_by_label("Email address").fill("donor@example.com"); g.get_by_label("Password").fill("Secret123")
        g.get_by_role("button", name="Sign In").click()
        expect(g.get_by_text(re.compile("registered as Donor"))).to_be_visible()
        g.get_by_role("radio", name="DONOR").click(); g.get_by_role("button", name="Sign In").click()
        expect(g).to_have_url(re.compile("/donor-dashboard"))
        g.goto(BASE + "/hospital-dashboard"); expect(g.get_by_text("Not available for your account")).to_be_visible()
    step("Login with role check; role-protected routes", login_flow)

    def admin_flow():
        g = b.new_context(viewport={"width": 1360, "height": 900}).new_page(); g.goto(BASE + "/login")
        g.get_by_role("radio", name="ADMIN").click()
        g.get_by_label("Email address").fill("admin@example.com"); g.get_by_label("Password").fill("AdminPass123")
        g.get_by_role("button", name="Sign In").click()
        expect(g).to_have_url(re.compile("/admin-dashboard"))
        expect(g.get_by_text("System Administration")).to_be_visible()
        row = g.locator("tr", has_text="hospital@example.com")
        row.get_by_role("button", name="Verify Now").click()
        expect(row.get_by_text("Verified")).to_be_visible()
        g.get_by_role("tab", name="Audit log").click(); expect(g.get_by_text("USER_VERIFIED")).to_be_visible()
        g.get_by_role("tab", name="Users").click()
        g.screenshot(path=f"{SHOTS}/11_admin.png", full_page=True)
        g.goto(BASE + "/blood-banks"); expect(g.get_by_text("Verified").first).to_be_visible()
        expect(g.get_by_role("cell", name="Packed Red Cells")).to_be_visible()
        expect(g.get_by_role("cell", name="Plasma")).to_be_visible()
        g.screenshot(path=f"{SHOTS}/12_blood_banks_components.png", full_page=True)
    step("Admin verifies facility -> component stock becomes public on Find Blood Banks", admin_flow)

    b.close()

print("\nConsole errors:", errors[:10] if errors else "none")
print(f"{sum(r[0]=='PASS' for r in results)}/{len(results)} steps passed")
