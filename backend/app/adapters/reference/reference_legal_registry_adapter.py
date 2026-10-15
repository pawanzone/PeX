"""In-Memory Reference Legal Registry & Freeze Dossier Adapter.

TEST / REFERENCE ONLY.
Implements LegalRegistryPort (SPI-LEGAL-REGISTRY-PORT).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timezone

from app.ports.legal_registry_port import LegalRegistryPort
from app.schemas.contracts.wave2_schemas import (
    AccountRestrictionScope,
    AccountRestrictionType,
    LegalFreezeDossierRecord,
    LegalFreezeType,
    RolloverMandateRecord,
)


class InMemoryLegalRegistryAdapter(LegalRegistryPort):
    """Hermetic reference implementation of LegalRegistryPort."""

    def __init__(
        self,
        restrictions: Optional[Dict[str, AccountRestrictionScope]] = None,
        dossiers: Optional[Dict[str, LegalFreezeDossierRecord]] = None,
        mandates: Optional[Dict[str, RolloverMandateRecord]] = None,
    ):
        self._restrictions: Dict[str, AccountRestrictionScope] = restrictions or {
            "33445566": AccountRestrictionScope(
                account_number="33445566",
                account_title="METRO PROPERTIES HOLDING LLC",
                restriction_type=AccountRestrictionType.POST_NO_CREDITS,
                is_credit_prohibited=True,
                restriction_reference_id="JUD-FRZ-2026-NY-9912",
                issuing_authority="NEW_YORK_SUPREME_COURT",
                statutory_sanctions_hit=False
            ),
            "55667788": AccountRestrictionScope(
                account_number="55667788",
                account_title="COLUMBIA TRADING GROUP",
                restriction_type=AccountRestrictionType.DEBIT_ONLY,
                is_credit_prohibited=False, # Credits ARE allowed
                restriction_reference_id="LIEN-2026-0041",
                issuing_authority="INTERNAL_COLLATERAL_DEPT",
                statutory_sanctions_hit=False
            ),
            "77889900": AccountRestrictionScope(
                account_number="77889900",
                account_title="SANCTIONED PETROLEUM ASSETS LTD",
                restriction_type=AccountRestrictionType.STATUTORY_SANCTIONS_BLOCK,
                is_credit_prohibited=True,
                restriction_reference_id="OFAC-SDN-50PCT-BLOCKED",
                issuing_authority="US_TREASURY_OFAC",
                statutory_sanctions_hit=True  # Statutory Sanctions!
            )
        }

        self._dossiers: Dict[str, LegalFreezeDossierRecord] = dossiers or {
            "33445566": LegalFreezeDossierRecord(
                dossier_id="DOS-2026-NY-9912",
                account_number="33445566",
                case_caption="Apex Creditors v. Metro Properties Holding LLC",
                court_or_agency_name="New York State Supreme Court",
                docket_number="Index No. 650123/2026",
                freeze_type=LegalFreezeType.COURT_INJUNCTION,
                freeze_scope="POST_NO_CREDITS",
                is_conflicting_order=False,
                permitted_disposition="RETURN_TO_ORDERING_INSTITUTION",
                compliance_officer_signoff=True,
                dossier_status="ACTIVE",
                issued_date=date(2026, 1, 15)
            )
        }

        self._mandates: Dict[str, RolloverMandateRecord] = mandates or {
            "99887700": RolloverMandateRecord(
                mandate_id="MAND-ROLL-2026-001",
                debtor_or_creditor_entity_id="PACIFIC_RIM_TRADING",
                closed_account_number="99887700",
                successor_account_number="99887766",
                authorized_signatory="Jane Doe, VP Treasury",
                mandate_status="ACTIVE",
                signed_date=date(2026, 1, 10),
                dual_authorization_verified=True
            )
        }

    def get_restriction_scope(self, account_number: str) -> Optional[AccountRestrictionScope]:
        return self._restrictions.get(account_number.strip())

    def register_restriction(self, scope: AccountRestrictionScope) -> None:
        self._restrictions[scope.account_number.strip()] = scope

    def get_legal_freeze_dossier(self, account_number: str) -> Optional[LegalFreezeDossierRecord]:
        return self._dossiers.get(account_number.strip())

    def register_dossier(self, dossier: LegalFreezeDossierRecord) -> None:
        self._dossiers[dossier.account_number.strip()] = dossier

    def get_rollover_mandate(
        self,
        closed_account_number: str,
        entity_id_hint: Optional[str] = None
    ) -> Optional[RolloverMandateRecord]:
        return self._mandates.get(closed_account_number.strip())

    def register_mandate(self, mandate: RolloverMandateRecord) -> None:
        self._mandates[mandate.closed_account_number.strip()] = mandate
