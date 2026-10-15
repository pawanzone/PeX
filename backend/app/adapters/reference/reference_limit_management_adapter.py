"""In-Memory Reference Limit Management Adapter.

TEST / REFERENCE ONLY (NON-PRODUCTION).
Implements LimitManagementPort (SPI-LIMIT-MANAGEMENT).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid

from app.ports.limit_management_port import LimitManagementPort
from app.schemas.contracts.wave3_schemas import (
    LimitType,
    LimitUtilizationRecord,
    ClientLimitProfileRecord,
    OperationalLimitWaiverDossier,
    TreasuryPacingSchedule,
)


class InMemoryLimitManagementAdapter(LimitManagementPort):
    """Hermetic reference implementation of LimitManagementPort."""

    def __init__(
        self,
        limits: Optional[Dict[str, LimitUtilizationRecord]] = None,
        profiles: Optional[Dict[str, ClientLimitProfileRecord]] = None,
    ):
        now = datetime.now(timezone.utc)
        self._limits: Dict[str, LimitUtilizationRecord] = limits or {
            "LIM-DAILY-CORP-01": LimitUtilizationRecord(
                limit_id="LIM-DAILY-CORP-01",
                limit_type=LimitType.DAILY_ACCOUNT_LIMIT,
                limit_cap=1000000.0,
                current_utilization=850000.0,
                currency="USD",
                reset_schedule_utc=now + timedelta(hours=2),
                is_breached=False,
                is_authoritative=True,
                authority_source="BANK_LIMIT_ENGINE",
            ),
            "LIM-BREACHED-01": LimitUtilizationRecord(
                limit_id="LIM-BREACHED-01",
                limit_type=LimitType.DAILY_ACCOUNT_LIMIT,
                limit_cap=500000.0,
                current_utilization=490000.0,
                currency="USD",
                reset_schedule_utc=now + timedelta(hours=1),
                is_breached=False,
                is_authoritative=True,
                authority_source="BANK_LIMIT_ENGINE",
            ),
        }
        self._profiles: Dict[str, ClientLimitProfileRecord] = profiles or {
            "CLI-CORP-001:ACCT-CORP-USD-001": ClientLimitProfileRecord(
                client_id="CLI-CORP-001",
                account_number="ACCT-CORP-USD-001",
                approved_overdraft_facility=200000.0,
                preauthorized_waiver_cap=100000.0,
                waiver_requires_dual_auth=True,
            )
        }

    def get_limit_utilization(self, limit_id: str) -> Optional[LimitUtilizationRecord]:
        return self._limits.get(limit_id.strip())

    def register_limit_utilization(self, record: LimitUtilizationRecord) -> None:
        self._limits[record.limit_id] = record

    def get_client_limit_profile(
        self, client_id: str, account_number: str
    ) -> Optional[ClientLimitProfileRecord]:
        key = f"{client_id.strip()}:{account_number.strip()}"
        return self._profiles.get(key)

    def assemble_limit_waiver_dossier(
        self,
        limit_id: str,
        breached_amount: float,
        currency: str,
        client_profile: Optional[ClientLimitProfileRecord] = None,
    ) -> Optional[OperationalLimitWaiverDossier]:
        lim = self.get_limit_utilization(limit_id)
        if not lim:
            return None

        new_total = lim.current_utilization + breached_amount
        util_pct = round((new_total / lim.limit_cap) * 100.0, 2) if lim.limit_cap > 0 else 100.0

        pacing_sched = None
        if lim.reset_schedule_utc:
            pacing_sched = TreasuryPacingSchedule(
                schedule_id=f"PACE-LIM-{uuid.uuid4().hex[:6].upper()}",
                target_profile="TR-06",
                pacing_interval_seconds=1800.0,
                max_retry_attempts=2,
                current_attempt=1,
                next_evaluation_time=lim.reset_schedule_utc,
                pacing_reason=f"Pacing queued until intraday limit reset cycle at {lim.reset_schedule_utc.isoformat()}",
                execution_owner="BANK",
            )

        return OperationalLimitWaiverDossier(
            dossier_id=f"DOS-LIM-{uuid.uuid4().hex[:8].upper()}",
            limit_id=limit_id,
            breached_amount=breached_amount,
            currency=currency,
            utilization_percentage=util_pct,
            requires_credit_approver=True,
            pacing_schedule=pacing_sched,
            execution_owner="BANK",
        )
