"""In-Memory Reference General Ledger Suspense Adapter.

TEST / REFERENCE ONLY.
Implements GeneralLedgerSuspensePort (SPI-GENERAL-LEDGER-SUSPENSE).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.general_ledger_suspense_port import GeneralLedgerSuspensePort
from app.schemas.contracts.wave2_schemas import SettlementSuspenseBreakRecord


class InMemoryGeneralLedgerSuspenseAdapter(GeneralLedgerSuspensePort):
    """Hermetic reference implementation of GeneralLedgerSuspensePort."""

    def __init__(self):
        self._breaks: Dict[str, SettlementSuspenseBreakRecord] = {}

    def create_suspense_break(
        self,
        uetr: str,
        amount: float,
        currency: str,
        suspense_gl_account: str,
        escrow_reference_case: str,
        source_nostro_account: Optional[str] = None
    ) -> SettlementSuspenseBreakRecord:
        break_id = f"BRK-GL-{uuid.uuid4().hex[:8].upper()}"
        nostro = source_nostro_account or "GL-1010-FEDWIRE-NOSTRO"

        record = SettlementSuspenseBreakRecord(
            break_id=break_id,
            uetr=uetr,
            amount=amount,
            currency=currency,
            suspense_gl_account=suspense_gl_account,
            clearing_nostro_account=nostro,
            journal_debit_entry={
                "gl_account": nostro,
                "amount": amount,
                "currency": currency,
                "entry_type": "DEBIT",
                "description": f"Inward funds received under escrow hold for {escrow_reference_case}"
            },
            journal_credit_entry={
                "gl_account": suspense_gl_account,
                "amount": amount,
                "currency": currency,
                "entry_type": "CREDIT",
                "description": f"Escrow suspense liability booked for {escrow_reference_case}"
            },
            is_balanced=True,
            escrow_reference_case=escrow_reference_case,
            booked_at=datetime.now(timezone.utc)
        )
        self._breaks[break_id] = record
        return record

    def validate_journal_balance(self, record: SettlementSuspenseBreakRecord) -> bool:
        dr_amt = record.journal_debit_entry.get("amount", 0.0)
        cr_amt = record.journal_credit_entry.get("amount", 0.0)
        return bool(abs(dr_amt - cr_amt) < 0.0001 and record.is_balanced)
