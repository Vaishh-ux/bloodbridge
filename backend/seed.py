"""OPTIONAL demo data for local development and classroom demos.

* Never drops or deletes anything.
* Refuses to run when ENVIRONMENT=production or when the database already has users.
* Every record is clearly labelled as sample data ("Sample ..." names, @example.com emails),
  and no blood inventory is invented: facilities enter their own stock from the dashboard.

    python seed.py --demo
"""
import argparse
import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.auth import get_password_hash  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import (BloodRequest, DonorProfile, EmergencyLevel, FacilityType, Hospital,  # noqa: E402
                        PatientProfile, RequestStatus, User, UserRole)
from app.services.matching_service import run_donor_matching  # noqa: E402

DEMO_PASSWORD = "Demo@1234"
GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
CITIES = {"Delhi": ("Delhi", 28.6139, 77.2090), "Mumbai": ("Maharashtra", 19.0760, 72.8777),
          "Bengaluru": ("Karnataka", 12.9716, 77.5946), "Chennai": ("Tamil Nadu", 13.0827, 80.2707)}


def seed():
    if settings.is_production:
        sys.exit("Refusing to seed demo data when ENVIRONMENT=production.")
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            sys.exit("Database already contains users; demo seed skipped (nothing was changed).")
        rnd = random.Random(42)
        pw = get_password_hash(DEMO_PASSWORD)

        def user(name, email, role):
            u = User(name=name, email=email, phone="+91 9000000000", password_hash=pw, role=role,
                     is_verified=False, is_active=True)
            db.add(u)
            db.flush()
            return u

        hospitals = []
        for i, (city, (state, lat, lng)) in enumerate(CITIES.items(), start=1):
            kind = FacilityType.BLOOD_BANK if i % 2 == 0 else FacilityType.HOSPITAL
            label = "Blood Bank" if kind == FacilityType.BLOOD_BANK else "Hospital"
            u = user(f"Sample {city} {label}", f"facility{i}@example.com", UserRole.HOSPITAL)
            h = Hospital(user_id=u.id, name=u.name, facility_type=kind, email=u.email, phone=u.phone,
                         address=f"Sample Road {i}, {city}", city=city, state=state, pincode=None,
                         latitude=lat + 0.01 * i, longitude=lng - 0.01 * i, verified=False)
            db.add(h)
            db.flush()
            hospitals.append(h)

        for i in range(1, 21):
            city = list(CITIES)[i % 4]
            state, lat, lng = CITIES[city]
            u = user(f"Sample Donor {i:02d}", f"donor{i}@example.com", UserRole.DONOR)
            db.add(DonorProfile(
                user_id=u.id, blood_group=GROUPS[i % 8], date_of_birth=date(1990, i % 12 + 1, i % 27 + 1),
                city=city, state=state, latitude=round(lat + rnd.uniform(-0.08, 0.08), 5),
                longitude=round(lng + rnd.uniform(-0.08, 0.08), 5), available=i % 5 != 0,
                last_donation_date=date.today() - timedelta(days=rnd.choice([30, 100, 150, 400])),
                screening_passed=True))

        patients = []
        for i in range(1, 6):
            city = list(CITIES)[i % 4]
            u = user(f"Sample Patient {i:02d}", f"patient{i}@example.com", UserRole.PATIENT)
            db.add(PatientProfile(user_id=u.id, blood_group=GROUPS[i], city=city, state=CITIES[city][0]))
            patients.append(u)
        db.commit()

        levels = [EmergencyLevel.CRITICAL, EmergencyLevel.HIGH, EmergencyLevel.MEDIUM, EmergencyLevel.NORMAL]
        for i, h in enumerate(hospitals):
            owner = patients[i]
            req = BloodRequest(created_by_user_id=owner.id, patient_id=owner.patient_profile.id, hospital_id=h.id,
                               hospital_name=h.name, hospital_address=h.address, city=h.city, state=h.state,
                               blood_group=GROUPS[(i * 3) % 8], units_required=1 + i % 3, emergency_level=levels[i],
                               latitude=h.latitude, longitude=h.longitude,
                               required_date=(date.today() + timedelta(days=1)).isoformat(), required_time="10:00",
                               status=RequestStatus.REQUESTED, notes="Sample request created by seed.py")
            db.add(req)
            db.commit()
            run_donor_matching(db, req)
        print(f"Demo data created. All sample accounts use password {DEMO_PASSWORD!r}:")
        print("  donor1..20@example.com, patient1..5@example.com, facility1..4@example.com")
        print("Create an admin with:  python create_admin.py --email you@example.com")
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="confirm you want sample data")
    if not ap.parse_args().demo:
        ap.print_help()
        sys.exit(1)
    seed()
