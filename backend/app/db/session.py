"""SQLAlchemy Engine & Thread-Safe Session Management for Local SQLite & AWS PostgreSQL."""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Dialect Detection & Connection Engine Factory
database_url = settings.DATABASE_URL

if database_url.startswith("sqlite"):
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        echo=settings.DB_ECHO,
    )
else:
    # PostgreSQL / AWS Aurora / RDS Configuration
    engine = create_engine(
        database_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=settings.DB_ECHO,
    )

# Thread-safe Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database session lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_info() -> dict:
    """Returns database connection telemetry & dialect details."""
    dialect_name = engine.dialect.name
    is_sqlite = dialect_name == "sqlite"
    
    # Mask password if present in URL
    raw_url = str(engine.url)
    if "@" in raw_url:
        masked_url = raw_url.split("@")[0].split(":")[0] + ":***@" + raw_url.split("@")[1]
    else:
        masked_url = raw_url

    return {
        "status": "ONLINE",
        "dialect": dialect_name,
        "is_sqlite": is_sqlite,
        "is_aws_postgres": not is_sqlite,
        "url_masked": masked_url,
        "pool_size": getattr(engine.pool, "size", lambda: None)() if hasattr(engine.pool, "size") else "N/A",
    }
