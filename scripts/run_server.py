"""Unified Server Startup Script for PeX Platform."""
import uvicorn
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings

if __name__ == "__main__":
    print(f"Starting PeX Enterprise Platform on http://{settings.HOST}:{settings.PORT}...")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
