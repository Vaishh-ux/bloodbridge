"""Importing this package registers every model with SQLAlchemy."""
from app.models.user import User, UserRole  # noqa: F401
from app.models.donor import DonorProfile  # noqa: F401
from app.models.patient import PatientProfile  # noqa: F401
from app.models.hospital import Hospital, FacilityType  # noqa: F401
from app.models.blood_request import BloodRequest, EmergencyLevel, RequestStatus  # noqa: F401
from app.models.match import DonorMatch, MatchStatus  # noqa: F401
from app.models.donation import Donation  # noqa: F401
from app.models.inventory import BloodComponent, BloodInventory, InventoryLog  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
