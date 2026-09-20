"""Pytest configuration and shared fixtures for PeX test suite."""
import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.services.data_loader import repo

@pytest.fixture(autouse=True)
def reset_test_state():
    """Ensure data is loaded and clean for every test run."""
    repo.load_all_data()
    yield

@pytest.fixture
def client():
    return TestClient(app)
