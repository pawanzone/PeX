import os
import sys
from pathlib import Path

# Set up environment
proj_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(proj_dir / "backend"))

writable_db_path = proj_dir / "scratch" / "writable_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{writable_db_path.as_posix()}"
os.environ["PYTHONPATH"] = "backend"

from sqlalchemy import create_engine
from app.db import session, init_db, repository
from app.db.session import SessionLocal

new_engine = create_engine(f"sqlite:///{writable_db_path.as_posix()}", connect_args={"check_same_thread": False})
session.engine = new_engine
init_db.engine = new_engine
session.SessionLocal.configure(bind=new_engine)

from app.services.data_loader import repo
repo.load_all_data()

print(f"Engine URL: {session.engine.url}")
print(f"SessionLocal bind: {SessionLocal.kw.get('bind').url}")

import pytest
exit_code = pytest.main(["tests/test_p0_remediation.py", "-v"])
sys.exit(exit_code)
