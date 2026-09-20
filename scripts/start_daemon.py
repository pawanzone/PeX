"""Stable Background Server Startup Script for PeX Platform (Non-reload for rock-solid stability)."""
import uvicorn
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings

if __name__ == "__main__":
    print(f"Starting Stable PeX Server on http://0.0.0.0:{settings.PORT}...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=False, workers=1)
