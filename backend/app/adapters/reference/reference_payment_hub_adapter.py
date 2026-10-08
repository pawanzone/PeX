"""In-Memory Reference Payment Hub Repair Queue Adapter.

TEST / REFERENCE ONLY.
Implements PaymentHubRepairQueuePort with deterministic repair item retrieval and validation.
Zero vendor SDK dependencies.
"""
from typing import Dict, List, Any, Optional
from app.ports.payment_hub_repair_queue_port import PaymentHubRepairQueuePort
from app.schemas.contracts.wave1_schemas import (
    PaymentHubRepairRecord,
    RepairValidationResult,
)


class InMemoryPaymentHubRepairQueueAdapter(PaymentHubRepairQueuePort):
    """Hermetic reference implementation of PaymentHubRepairQueuePort."""

    def __init__(
        self,
        items: Optional[Dict[str, PaymentHubRepairRecord]] = None
    ):
        self._items: Dict[str, PaymentHubRepairRecord] = items or {
            "PMT-PR09-001": PaymentHubRepairRecord(
                payment_id="PMT-PR09-001",
                uetr="9f1e2d3c-4b5a-6789-0123-abcdef090001",
                current_queue_status="HELD_IN_REPAIR",
                syntax_error_code="ERR_SYNTAX_TAG_UNCLOSED",
                syntax_error_tag="<RmtInf>",
                repair_instruction="CLOSE_UNCLOSED_REMITTANCE_TAG_AND_REVALIDATE"
            )
        }

    def get_repair_item(self, payment_id: str) -> Optional[PaymentHubRepairRecord]:
        return self._items.get(payment_id.strip())

    def validate_repair_syntax(
        self,
        payment_id: str,
        proposed_fix: Dict[str, Any]
    ) -> RepairValidationResult:
        errors = []
        if not proposed_fix:
            errors.append("Proposed fix dictionary is empty.")
            return RepairValidationResult(payment_id=payment_id, is_valid_repair=False, validation_errors=errors)

        if "repaired_payload" not in proposed_fix and "repaired_fields" not in proposed_fix:
            errors.append("Proposed fix must specify either 'repaired_payload' or 'repaired_fields'.")

        is_valid = len(errors) == 0
        return RepairValidationResult(
            payment_id=payment_id,
            is_valid_repair=is_valid,
            repaired_xml_or_json=proposed_fix.get("repaired_payload"),
            validation_errors=errors
        )
