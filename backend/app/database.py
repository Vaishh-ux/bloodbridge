from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create any tables that do not exist yet.

    This never drops or alters existing tables, so it is safe to run against a database
    that already holds data. (Schema changes to existing tables need a migration.)
    """
    import app.models  # noqa: F401  (registers every model on Base.metadata)

    Base.metadata.create_all(bind=engine)
    _upgrade_existing_schema()


def _upgrade_existing_schema() -> None:
    """Small, additive upgrades for databases created by earlier versions. Never drops data."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    with engine.begin() as conn:
        if "inventory_logs" in tables:
            cols = {c["name"] for c in insp.get_columns("inventory_logs")}
            if "component" not in cols:
                conn.execute(text("ALTER TABLE inventory_logs ADD COLUMN component VARCHAR(20)"))
        # v1.1 kept stock in `blood_inventory` without a component: copy it once as whole blood.
        if "blood_inventory" in tables:
            already = conn.execute(text("SELECT COUNT(*) FROM blood_stock")).scalar()
            if not already:
                conn.execute(text(
                    "INSERT INTO blood_stock (hospital_id, blood_group, component, available_units, "
                    "reserved_units, last_updated, updated_by_user_id) "
                    "SELECT hospital_id, blood_group, 'WHOLE_BLOOD', available_units, reserved_units, "
                    "last_updated, updated_by_user_id FROM blood_inventory"
                ))
