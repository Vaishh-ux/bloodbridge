"""System screening checks for donors.

These are configurable *coordination* rules (see MIN_DONATION_INTERVAL_DAYS, MIN_DONOR_AGE,
MAX_DONOR_AGE in config). They are not a medical determination: final eligibility is
always confirmed by blood-bank staff at the time of donation.
"""
from datetime import date
from typing import Optional, Tuple

from app.config import settings


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def is_donor_eligible(
    last_donation_date: Optional[date],
    screening_passed: bool = True,
    date_of_birth: Optional[date] = None,
    today: Optional[date] = None,
) -> Tuple[bool, str]:
    today = today or date.today()

    if not screening_passed:
        return False, "Basic self-screening not confirmed. Update your donor profile."

    if date_of_birth is not None:
        age = age_on(date_of_birth, today)
        if age < settings.MIN_DONOR_AGE:
            return False, f"Below the minimum donor age ({settings.MIN_DONOR_AGE})."
        if age > settings.MAX_DONOR_AGE:
            return False, f"Above the maximum donor age configured ({settings.MAX_DONOR_AGE})."

    if last_donation_date is None:
        return True, "Eligible for screening (no recorded donation)."

    days_since = (today - last_donation_date).days
    if days_since < settings.MIN_DONATION_INTERVAL_DAYS:
        remaining = settings.MIN_DONATION_INTERVAL_DAYS - days_since
        return False, f"Next donation possible in {remaining} day(s) (last donated {days_since} day(s) ago)."

    return True, "Eligible for screening."


def donor_eligibility(donor) -> Tuple[bool, str]:
    return is_donor_eligible(donor.last_donation_date, donor.screening_passed, donor.date_of_birth)
