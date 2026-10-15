"""In-Memory Reference Credit Risk & Exposure Adapter.

TEST / REFERENCE ONLY (NON-PRODUCTION).
Implements CreditRiskPort (SPI-CREDIT-RISK).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.credit_risk_port import CreditRiskPort
from app.schemas.contracts.wave3_schemas import (
    CounterpartyExposureRecord,
    CreditFacilityRecord,
    CreditRiskDossierRecord,
    CreditDecisionRecord,
)


class InMemoryCreditRiskAdapter(CreditRiskPort):
    """Hermetic reference implementation of CreditRiskPort."""

    def __init__(
        self,
        exposures: Optional[Dict[str, CounterpartyExposureRecord]] = None,
        facilities: Optional[Dict[str, CreditFacilityRecord]] = None,
    ):
        self._exposures: Dict[str, CounterpartyExposureRecord] = exposures or {
            "CPTY-CORP-ALPHA": CounterpartyExposureRecord(
                counterparty_id="CPTY-CORP-ALPHA",
                counterparty_bic="ALPHUS33XXX",
                credit_rating="AA",
                total_facility_limit=10000000.0,
                current_drawn_exposure=9500000.0,
                currency="USD",
                is_breached=False,
                is_authoritative=True,
                authority_source="ENTERPRISE_CREDIT_RISK_SYSTEM",
            ),
            "CPTY-DISTRESSED-01": CounterpartyExposureRecord(
                counterparty_id="CPTY-DISTRESSED-01",
                counterparty_bic="DISTUS33XXX",
                credit_rating="SUB_INVESTMENT",
                total_facility_limit=1000000.0,
                current_drawn_exposure=1200000.0,
                currency="USD",
                is_breached=True,
                is_authoritative=True,
                authority_source="ENTERPRISE_CREDIT_RISK_SYSTEM",
            ),
        }
        self._facilities: Dict[str, CreditFacilityRecord] = facilities or {
            "FAC-ALPHA-01": CreditFacilityRecord(
                facility_id="FAC-ALPHA-01",
                borrower_entity="CPTY-CORP-ALPHA",
                facility_type="REVOLVING_CREDIT",
                collateral_coverage_ratio=1.25,
                approval_tier_required="SENIOR_CREDIT_OFFICER",
            )
        }

    def get_counterparty_exposure(
        self, counterparty_id: str
    ) -> Optional[CounterpartyExposureRecord]:
        return self._exposures.get(counterparty_id.strip())

    def register_counterparty_exposure(self, record: CounterpartyExposureRecord) -> None:
        self._exposures[record.counterparty_id] = record

    def get_credit_facility(self, facility_id: str) -> Optional[CreditFacilityRecord]:
        return self._facilities.get(facility_id.strip())

    def assemble_credit_risk_dossier(
        self,
        counterparty_id: str,
        requested_amount: float,
        currency: str,
        facility_id: Optional[str] = None,
    ) -> Optional[CreditRiskDossierRecord]:
        exp = self.get_counterparty_exposure(counterparty_id)
        if not exp:
            return None

        fac = self.get_credit_facility(facility_id) if facility_id else None
        return CreditRiskDossierRecord(
            dossier_id=f"DOS-CREDIT-{uuid.uuid4().hex[:8].upper()}",
            counterparty_id=counterparty_id,
            requested_amount=requested_amount,
            currency=currency,
            exposure_record=exp,
            facility_record=fac,
            decision_record=None,
            autonomous_stp_prohibited=True,  # STRICT INVARIANT
            execution_owner="BANK",
        )
