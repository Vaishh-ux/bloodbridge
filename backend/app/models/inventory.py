import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.timeutil import utcnow


class BloodComponent(str, enum.Enum):
    WHOLE_BLOOD = "WHOLE_BLOOD"
    PRBC = "PRBC"            # packed red blood cells
    PLATELETS = "PLATELETS"
    PLASMA = "PLASMA"        # fresh frozen plasma


COMPONENT_LABELS = {
    BloodComponent.WHOLE_BLOOD: "Whole Blood",
    BloodComponent.PRBC: "Packed Red Cells",
    BloodComponent.PLATELETS: "Platelets",
    BloodComponent.PLASMA: "Plasma",
}
RED_CELL_COMPONENTS = (BloodComponent.WHOLE_BLOOD.value, BloodComponent.PRBC.value)


class BloodInventory(Base):
    """Stock a facility reports, per blood group and component.

    Stored in table `blood_stock`. Databases created by the earlier version kept stock in
    `blood_inventory` (no component); init_db() copies those rows here as WHOLE_BLOOD once.
    """

    __tablename__ = "blood_stock"
    __table_args__ = (
        UniqueConstraint("hospital_id", "blood_group", "component", name="uq_stock_hospital_group_component"),
    )

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    blood_group = Column(String(5), nullable=False)
    component = Column(String(20), nullable=False, default=BloodComponent.WHOLE_BLOOD.value)
    available_units = Column(Integer, default=0, nullable=False)
    reserved_units = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    updated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    hospital = relationship("Hospital", back_populates="inventory")


class InventoryLog(Base):
    """History of every stock change made by a facility."""

    __tablename__ = "inventory_logs"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    blood_group = Column(String(5), nullable=False)
    component = Column(String(20), nullable=True)
    available_change = Column(Integer, default=0, nullable=False)
    reserved_change = Column(Integer, default=0, nullable=False)
    available_after = Column(Integer, nullable=False)
    reserved_after = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
