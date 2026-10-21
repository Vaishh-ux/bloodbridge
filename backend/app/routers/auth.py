from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import auth_rate_limit, create_access_token, get_current_user, get_password_hash, verify_password
from app.database import get_db
from app.models.donor import DonorProfile
from app.models.hospital import Hospital
from app.models.patient import PatientProfile
from app.models.user import User, UserRole
from app.schemas.user import Token, UserCreate, UserLogin
from app.services.audit import audit
from app.services.eligibility_service import donor_eligibility
from app.services.matching_service import match_donor_to_open_requests
from app.services.notification_service import create_notification

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _token_for(user: User) -> Token:
    return Token(access_token=create_access_token(user), user_id=user.id, name=user.name, email=user.email, role=user.role)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(auth_rate_limit)])
async def register(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    email = user_in.email.lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "An account with this email already exists. Please log in.")

    user = User(name=user_in.name, email=email, phone=user_in.phone,
                password_hash=get_password_hash(user_in.password), role=user_in.role,
                is_active=True, is_verified=False, is_blocked=False)
    db.add(user)
    db.flush()

    donor = None
    if user_in.role == UserRole.DONOR:
        donor = DonorProfile(
            user_id=user.id, blood_group=user_in.blood_group, date_of_birth=user_in.date_of_birth,
            gender=user_in.gender, address=user_in.address, city=user_in.city, state=user_in.state,
            pincode=user_in.pincode, latitude=user_in.latitude, longitude=user_in.longitude,
            available=user_in.available, last_donation_date=user_in.last_donation_date,
            screening_passed=user_in.meets_basic_criteria,
        )
        db.add(donor)
    elif user_in.role == UserRole.PATIENT:
        db.add(PatientProfile(
            user_id=user.id, blood_group=user_in.blood_group, date_of_birth=user_in.date_of_birth,
            gender=user_in.gender, address=user_in.address, city=user_in.city, state=user_in.state,
            pincode=user_in.pincode,
        ))
    elif user_in.role == UserRole.HOSPITAL:
        db.add(Hospital(
            user_id=user.id, name=user_in.name, facility_type=user_in.facility_type, email=email,
            phone=user_in.phone, address=user_in.address.strip(), city=user_in.city, state=user_in.state,
            pincode=user_in.pincode, latitude=user_in.latitude, longitude=user_in.longitude, verified=False,
        ))

    audit(db, user.id, "REGISTER", "user", user.id, f"role={user.role.value}", request)
    db.commit()
    db.refresh(user)

    if donor is not None:
        db.refresh(donor)
        for m in match_donor_to_open_requests(db, donor):
            await create_notification(
                db, user.id, "🚨 Emergency Blood Request Available",
                f"A {m.request.emergency_level.value} request for {m.request.blood_group} at "
                f"{m.request.hospital_name}, {m.request.city} matches your blood group.",
                "MATCH_FOUND", m.request_id)

    return _token_for(user)


@router.post("/login", response_model=Token, dependencies=[Depends(auth_rate_limit)])
def login(login_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == login_in.email.lower()).first()
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    if user.is_blocked or not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account has been suspended by an administrator.")
    if login_in.role is not None and login_in.role != user.role:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"This account is registered as {user.role.value.title()}. Select that role to sign in.")
    audit(db, user.id, "LOGIN", "user", user.id, None, request)
    db.commit()
    return _token_for(user)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    # JWTs are stateless; the client discards its token.
    return {"message": "Logged out."}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    profile = None
    if current_user.role == UserRole.DONOR and current_user.donor_profile:
        dp = current_user.donor_profile
        eligible, reason = donor_eligibility(dp)
        profile = {
            "profile_id": dp.id, "blood_group": dp.blood_group, "city": dp.city, "state": dp.state,
            "pincode": dp.pincode, "address": dp.address, "gender": dp.gender,
            "date_of_birth": dp.date_of_birth.isoformat() if dp.date_of_birth else None,
            "available": dp.available, "total_donations": dp.total_donations,
            "successful_donations": dp.successful_donations,
            "last_donation_date": dp.last_donation_date.isoformat() if dp.last_donation_date else None,
            "screening_passed": dp.screening_passed, "latitude": dp.latitude, "longitude": dp.longitude,
            "eligible": eligible, "eligibility_reason": reason,
        }
    elif current_user.role == UserRole.PATIENT and current_user.patient_profile:
        pp = current_user.patient_profile
        profile = {"profile_id": pp.id, "blood_group": pp.blood_group, "city": pp.city, "state": pp.state,
                   "pincode": pp.pincode}
    elif current_user.role == UserRole.HOSPITAL and current_user.hospital_profile:
        hp = current_user.hospital_profile
        profile = {"profile_id": hp.id, "name": hp.name, "facility_type": hp.facility_type.value,
                   "address": hp.address, "city": hp.city, "state": hp.state, "pincode": hp.pincode,
                   "verified": hp.verified, "latitude": hp.latitude, "longitude": hp.longitude}

    return {
        "id": current_user.id, "name": current_user.name, "email": current_user.email,
        "phone": current_user.phone, "role": current_user.role.value,
        "is_verified": current_user.is_verified, "profile": profile,
    }
