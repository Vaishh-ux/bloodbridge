"""An existing database from the previous version (stock in `blood_inventory`, no component
column) must upgrade on startup without losing data."""
import os
import subprocess
import sys

from sqlalchemy import create_engine, text

from app.database import Base

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_old_database_is_upgraded_without_data_loss(tmp_path):
    url = f"sqlite:///{tmp_path / 'old.db'}"
    eng = create_engine(url)
    Base.metadata.create_all(eng)
    with eng.begin() as c:
        # Recreate the v1.1 layout.
        c.execute(text("DROP TABLE blood_stock"))
        c.execute(text("ALTER TABLE inventory_logs DROP COLUMN component"))
        c.execute(text("""CREATE TABLE blood_inventory (id INTEGER PRIMARY KEY, hospital_id INTEGER NOT NULL,
            blood_group VARCHAR(5) NOT NULL, available_units INTEGER NOT NULL, reserved_units INTEGER NOT NULL,
            last_updated DATETIME NOT NULL, updated_by_user_id INTEGER)"""))
        c.execute(text("INSERT INTO users (id,name,email,phone,password_hash,role,is_verified,is_active,is_blocked,created_at,updated_at)"
                       " VALUES (1,'H','h@example.com','+919000000000','x','HOSPITAL',1,1,0,'2026-01-01','2026-01-01')"))
        c.execute(text("INSERT INTO hospitals (id,user_id,name,facility_type,email,phone,address,city,state,verified,created_at)"
                       " VALUES (1,1,'Old','HOSPITAL','h@example.com','+919000000000','1 Road','Chittoor','AP',1,'2026-01-01')"))
        c.execute(text("INSERT INTO blood_inventory VALUES (1,1,'B+',5,1,'2026-01-01 10:00:00',NULL)"))
    eng.dispose()

    env = dict(os.environ, DATABASE_URL=url, ENVIRONMENT="test", JWT_SECRET="t" * 40)
    for _ in range(2):  # running twice must not duplicate rows
        subprocess.run([sys.executable, "-c", "from app.database import init_db; init_db()"],
                       cwd=BACKEND, env=env, check=True)

    eng = create_engine(url)
    with eng.connect() as c:
        rows = c.execute(text("SELECT blood_group, component, available_units, reserved_units FROM blood_stock")).all()
        cols = [r[1] for r in c.execute(text("PRAGMA table_info(inventory_logs)"))]
        legacy = c.execute(text("SELECT COUNT(*) FROM blood_inventory")).scalar()
    assert rows == [("B+", "WHOLE_BLOOD", 5, 1)]
    assert "component" in cols
    assert legacy == 1  # the old table is kept, never dropped
