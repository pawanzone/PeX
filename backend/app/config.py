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

    # Batch I/O (drop-folder JSON / JSONL in, results JSON out). NOT the e2e_fixtures folder:
    # the watcher consumes files placed in the inbox, so test fixtures must never live there.
    BATCH_IO_DIR: Path = Path(os.getenv("PEX_BATCH_IO_DIR", str(BASE_DIR / "batch_io")))
    INPUT_WATCH_DIR: Path = Path(os.getenv("PEX_INPUT_WATCH_DIR", str(BASE_DIR / "batch_io" / "inbox")))
    OUTPUT_WATCH_DIR: Path = Path(os.getenv("PEX_OUTPUT_WATCH_DIR", str(BASE_DIR / "batch_io" / "outbox")))
    ARCHIVE_WATCH_DIR: Path = Path(os.getenv("PEX_ARCHIVE_WATCH_DIR", str(BASE_DIR / "batch_io" / "archive")))
    FAILED_WATCH_DIR: Path = Path(os.getenv("PEX_FAILED_WATCH_DIR", str(BASE_DIR / "batch_io" / "failed")))
    BATCH_CHUNK_SIZE: int = int(os.getenv("PEX_BATCH_CHUNK_SIZE", "500"))
    WATCHER_AUTO_ARCHIVE: bool = os.getenv("PEX_WATCHER_AUTO_ARCHIVE", "true").lower() == "true"
    WATCHER_POLL_INTERVAL: float = float(os.getenv("PEX_WATCHER_POLL_INTERVAL", "1.0"))
    WATCHER_ENABLED: bool = os.getenv("PEX_WATCHER_ENABLED", "true").lower() == "true"

    # Data Path
    DATA_DIR: Path = SYNTHETIC_DATA_DIR

    # Demo / security
    PEX_DEMO: bool = os.getenv("PEX_DEMO", "false").lower() == "true"   # enables persona login + demo bank simulator
    BANK_CALLBACK_SECRET: str = os.getenv("PEX_BANK_CALLBACK_SECRET", "")  # HMAC-SHA256 secret for /api/bank/outcome
    BANK_COMM_MODE: str = os.getenv("PEX_BANK_COMM_MODE", "SIMULATED")      # SIMULATED only for now
    SIM_BANK_ACK_SECONDS: float = float(os.getenv("PEX_SIM_BANK_ACK_SECONDS", "6"))
    STP_MAX_AMOUNT: float = float(os.getenv("PEX_STP_MAX_AMOUNT", "10000"))  # conservative default; bank-configurable

    # Local LLM (OpenAI-compatible endpoint, e.g. Ollama http://localhost:11434/v1). Advisory only.
    LLM_ENABLED: bool = os.getenv("PEX_LLM_ENABLED", "false").lower() == "true"
    LLM_BASE_URL: str = os.getenv("PEX_LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_MODEL: str = os.getenv("PEX_LLM_MODEL", "qwen2.5:7b-instruct")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("PEX_LLM_TIMEOUT_SECONDS", "60"))

settings = Settings()


