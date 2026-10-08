"""Clearing Rail Calendar & Cutoff Port (SPI).

Defines abstract SPI for querying rail operating schedules, cutoff times,
and calculating deterministic value-date adjustments.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from app.schemas.contracts.wave1_schemas import RailCutoffInfo


class ClearingRailCalendarPort(ABC):
    """Abstract port for Rail Operating Calendar and Cutoff lookups."""

    @abstractmethod
    def get_rail_cutoff(
        self,
        rail_code: str,
        currency: str
    ) -> Optional[RailCutoffInfo]:
        """Retrieves operating hours and cutoff time for a specific clearing rail."""
        pass

    @abstractmethod
    def is_operating_day(
        self,
        rail_code: str,
        target_date: date
    ) -> bool:
        """Determines if target date is an active operating business day for the rail."""
        pass

    @abstractmethod
    def calculate_next_value_date(
        self,
        rail_code: str,
        current_date: date,
        roll_days: int = 1
    ) -> date:
        """Calculates next valid operating value date skipping weekends and clearing holidays."""
        pass
