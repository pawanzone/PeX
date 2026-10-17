"""SQL-aggregate summary counts (scale-safe)."""
from fastapi import APIRouter

from app.services.data_loader import repo

router = APIRouter()


@router.get("/counts")
def summary_counts():
    return repo.summary_counts()
