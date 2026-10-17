"""PeX Enterprise Platform Configuration."""
import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DATA_DIR = BASE_DIR / "synthetic_data" / "PeX_POC_Synthetic_Data_v0.1"
if not SYNTHETIC_DATA_DIR.exists():
    SYNTHETIC_DATA_DIR = BASE_DIR / "synthetic_data"

class Settings(BaseModel):
    PROJECT_NAME: str = "PeX Enterprise Payment Exception Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Model Gateway Configuration
    MODEL_GATEWAY_MODE: str = os.getenv("PEX_MODEL_GATEWAY_MODE", "mock") # "mock", "gemini", "openai"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Operation Mode (Shadow, Assisted, Live)
    PEX_OPERATION_MODE: str = os.getenv("PEX_OPERATION_MODE", "SHADOW")  # "SHADOW", "ASSISTED", "LIVE"
    
    # Governance & Dual Authorization Threshold
    DUAL_AUTH_THRESHOLD: float = 250000.0  # USD equivalent
    
    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "pex-enterprise-secret-key-2026-sha256")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Persistent Database Configuration (SQLite local default, AWS RDS/Aurora PostgreSQL plug-and-play)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./pex_enterprise.db")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

    # Inbound File Watcher Configuration
    INPUT_WATCH_DIR: Path = Path(os.getenv("PEX_INPUT_WATCH_DIR", str(BASE_DIR / "e2e_fixtures" / "input")))
    OUTPUT_WATCH_DIR: Path = Path(os.getenv("PEX_OUTPUT_WATCH_DIR", str(BASE_DIR / "e2e_fixtures" / "output")))
    ARCHIVE_WATCH_DIR: Path = Path(os.getenv("PEX_ARCHIVE_WATCH_DIR", str(BASE_DIR / "e2e_fixtures" / "archive")))
    WATCHER_AUTO_ARCHIVE: bool = os.getenv("PEX_WATCHER_AUTO_ARCHIVE", "true").lower() == "true"
    WATCHER_POLL_INTERVAL: float = float(os.getenv("PEX_WATCHER_POLL_INTERVAL", "1.0"))
    WATCHER_ENABLED: bool = os.getenv("PEX_WATCHER_ENABLED", "true").lower() == "true"

    # Data Path
    DATA_DIR: Path = SYNTHETIC_DATA_DIR

settings = Settings()


