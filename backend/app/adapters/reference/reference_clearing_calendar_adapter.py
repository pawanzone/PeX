"""In-Memory Reference Clearing Rail Calendar & Cutoff Adapter.

TEST / REFERENCE ONLY.
Implements ClearingRailCalendarPort with deterministic calendar and cutoff arithmetic.
Zero vendor SDK dependencies.
"""
from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta, timezone
from app.ports.clearing_rail_calendar_port import ClearingRailCalendarPort
from app.schemas.contracts.wave1_schemas import RailCutoffInfo


class InMemoryClearingRailCalendarAdapter(ClearingRailCalendarPort):
    """Hermetic reference implementation of ClearingRailCalendarPort."""

    def __init__(
        self,
        cutoffs: Optional[Dict[str, RailCutoffInfo]] = None
    ):
        today = datetime.now(timezone.utc).date()
        self._cutoffs: Dict[str, RailCutoffInfo] = cutoffs or {
            "FEDWIRE:USD": RailCutoffInfo(rail_code="FEDWIRE", currency="USD", operating_start_utc="00:00", cutoff_utc="22:00", is_open_today=True, next_operating_date=today + timedelta(days=1)),
            "CHAPS:GBP": RailCutoffInfo(rail_code="CHAPS", currency="GBP", operating_start_utc="06:00", cutoff_utc="17:00", is_open_today=True, next_operating_date=today + timedelta(days=1)),
            "TARGET2:EUR": RailCutoffInfo(rail_code="TARGET2", currency="EUR", operating_start_utc="07:00", cutoff_utc="18:00", is_open_today=True, next_operating_date=today + timedelta(days=1)),
            "SWIFT_CBPR+:USD": RailCutoffInfo(rail_code="SWIFT_CBPR+", currency="USD", operating_start_utc="00:00", cutoff_utc="23:59", is_open_today=True, next_operating_date=today + timedelta(days=1)),
        }

    def get_rail_cutoff(
        self,
        rail_code: str,
        currency: str
    ) -> Optional[RailCutoffInfo]:
        key = f"{rail_code.strip().upper()}:{currency.strip().upper()}"
        if key in self._cutoffs:
            return self._cutoffs[key]
        # Default fallback
        today = datetime.now(timezone.utc).date()
        return RailCutoffInfo(
            rail_code=rail_code.upper(),
            currency=currency.upper(),
            operating_start_utc="06:00",
            cutoff_utc="20:00",
            is_open_today=True,
            next_operating_date=today + timedelta(days=1)
        )

    def is_operating_day(
        self,
        rail_code: str,
        target_date: date
    ) -> bool:
        # 0 = Mon, 4 = Fri, 5 = Sat, 6 = Sun
        return target_date.weekday() < 5

    def calculate_next_value_date(
        self,
        rail_code: str,
        current_date: date,
        roll_days: int = 1
    ) -> date:
        next_d = current_date
        added = 0
        while added < roll_days:
            next_d += timedelta(days=1)
            if self.is_operating_day(rail_code, next_d):
                added += 1
        return next_d
