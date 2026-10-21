from datetime import date, timedelta

from app.models.blood_request import EmergencyLevel
from app.services.distance_service import calculate_haversine_distance
from app.services.eligibility_service import is_donor_eligible
from app.services.matching_service import calculate_match_score, can_donate_to, is_blood_compatible

GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


def test_o_negative_is_universal_red_cell_donor():
    assert all(is_blood_compatible(r, "O-") for r in GROUPS)


def test_ab_positive_is_universal_recipient():
    assert all(is_blood_compatible("AB+", d) for d in GROUPS)


def test_incompatible_pairs_rejected():
    assert not is_blood_compatible("O+", "A+")
    assert not is_blood_compatible("A-", "A+")  # Rh- recipient cannot receive Rh+
    assert not is_blood_compatible("B+", "AB+")
    assert not is_blood_compatible("O-", "O+")


def test_can_donate_to_matches_reference_table():
    assert sorted(can_donate_to("O+")) == sorted(["O+", "A+", "B+", "AB+"])
    assert sorted(can_donate_to("A-")) == sorted(["A-", "A+", "AB-", "AB+"])
    assert can_donate_to("AB+") == ["AB+"]


def test_haversine_delhi_mumbai():
    d = calculate_haversine_distance(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1140 < d < 1160


def test_closer_and_more_urgent_scores_higher():
    near = calculate_match_score(2, True, True, EmergencyLevel.HIGH)
    far = calculate_match_score(30, True, True, EmergencyLevel.HIGH)
    assert near > far
    assert calculate_match_score(5, True, True, EmergencyLevel.CRITICAL) > calculate_match_score(5, True, True, EmergencyLevel.NORMAL)
    assert calculate_match_score(5, True, False, EmergencyLevel.CRITICAL) == 0
    assert 0 <= near <= 100


def test_eligibility_rules():
    today = date(2026, 6, 1)
    assert is_donor_eligible(None, True, date(1990, 1, 1), today)[0]
    assert not is_donor_eligible(today - timedelta(days=30), True, None, today)[0]
    assert is_donor_eligible(today - timedelta(days=120), True, None, today)[0]
    assert not is_donor_eligible(None, False, None, today)[0]          # screening not confirmed
    assert not is_donor_eligible(None, True, date(2010, 1, 1), today)[0]  # under 18
    assert not is_donor_eligible(None, True, date(1950, 1, 1), today)[0]  # over 65
