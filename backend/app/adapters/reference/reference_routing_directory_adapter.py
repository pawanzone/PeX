"""In-Memory Reference Routing Directory & SSI Adapter.

TEST / REFERENCE ONLY.
Implements RoutingDirectoryPort with deterministic route resolution and SSI lookups.
Zero vendor SDK dependencies.
"""
from typing import Dict, List, Any, Optional
from app.ports.routing_directory_port import RoutingDirectoryPort
from app.schemas.contracts.wave1_schemas import (
    RouteResolutionRecord,
    SSIRecord,
)


class InMemoryRoutingDirectoryAdapter(RoutingDirectoryPort):
    """Hermetic reference implementation of RoutingDirectoryPort."""

    def __init__(
        self,
        routes: Optional[Dict[str, RouteResolutionRecord]] = None,
        ssis: Optional[Dict[str, SSIRecord]] = None
    ):
        self._routes: Dict[str, RouteResolutionRecord] = routes or {
            "BNPAFRPPXXX:CHASUS33XXX:USD": RouteResolutionRecord(
                debtor_agent_bic="BNPAFRPPXXX",
                creditor_agent_bic="CHASUS33XXX",
                clearing_rail="FEDWIRE",
                currency="USD",
                intermediary_agent_bic=None,
                clearing_system_member_id="021000021",
                is_reachable=True,
                reachability_status="DIRECT_SETTLEMENT_REACHABLE"
            ),
            "BNPAFRPPXXX:MIDLGB22XXX:GBP": RouteResolutionRecord(
                debtor_agent_bic="BNPAFRPPXXX",
                creditor_agent_bic="MIDLGB22XXX",
                clearing_rail="CHAPS",
                currency="GBP",
                intermediary_agent_bic=None,
                clearing_system_member_id="400515",
                is_reachable=True,
                reachability_status="DIRECT_SETTLEMENT_REACHABLE"
            ),
            "DEUTDEDDXXX:BOTKJPJTXXX:JPY": RouteResolutionRecord(
                debtor_agent_bic="DEUTDEDDXXX",
                creditor_agent_bic="BOTKJPJTXXX",
                clearing_rail="SWIFT_CBPR+",
                currency="JPY",
                intermediary_agent_bic="BOTKJPJTXXX",
                is_reachable=True,
                reachability_status="CORRESPONDENT_HOPS_VALIDATED"
            ),
            "ES91SANUESMM:CORRUPTED_BIC:EUR": RouteResolutionRecord(
                debtor_agent_bic="SANUESMMXXX",
                creditor_agent_bic="CORRUPTED_BIC",
                clearing_rail="TARGET2",
                currency="EUR",
                is_reachable=False,
                reachability_status="NO_ROUTE_FOUND"
            )
        }

        self._ssis: Dict[str, SSIRecord] = ssis or {
            "CHASUS33XXX:USD": SSIRecord(
                counterparty_bic="CHASUS33XXX",
                currency="USD",
                clearing_rail="FEDWIRE",
                settlement_account="FED-021000021-MAIN"
            ),
            "MIDLGB22XXX:GBP": SSIRecord(
                counterparty_bic="MIDLGB22XXX",
                currency="GBP",
                clearing_rail="CHAPS",
                settlement_account="CHAPS-400515-MAIN"
            )
        }

    def resolve_route(
        self,
        debtor_agent_bic: str,
        creditor_agent_bic: str,
        currency: str,
        clearing_rail: str
    ) -> Optional[RouteResolutionRecord]:
        key = f"{debtor_agent_bic.strip().upper()}:{creditor_agent_bic.strip().upper()}:{currency.strip().upper()}"
        if key in self._routes:
            return self._routes[key]

        # Standard fallback for well-formed BICs
        d_bic = debtor_agent_bic.strip().upper()
        c_bic = creditor_agent_bic.strip().upper()
        if len(c_bic) in (8, 11) and c_bic.isalnum():
            return RouteResolutionRecord(
                debtor_agent_bic=d_bic,
                creditor_agent_bic=c_bic,
                clearing_rail=clearing_rail or "SWIFT_CBPR+",
                currency=currency or "USD",
                is_reachable=True,
                reachability_status="STANDARD_DIRECTORY_ROUTE_RESOLVED"
            )
        return RouteResolutionRecord(
            debtor_agent_bic=d_bic,
            creditor_agent_bic=c_bic,
            clearing_rail=clearing_rail or "UNKNOWN",
            currency=currency or "USD",
            is_reachable=False,
            reachability_status="INVALID_BIC_OR_UNREACHABLE_CLEARING_PATH"
        )

    def get_ssi(
        self,
        bic_or_clearing_id: str,
        currency: str
    ) -> Optional[SSIRecord]:
        key = f"{bic_or_clearing_id.strip().upper()}:{currency.strip().upper()}"
        return self._ssis.get(key)

    def validate_clearing_identifier(
        self,
        routing_code: str,
        rail: str
    ) -> bool:
        r = routing_code.strip()
        if rail.upper() == "FEDWIRE":
            # 9-digit ABA routing check
            if len(r) != 9 or not r.isdigit():
                return False
            # Modulo-10 ABA checksum
            weights = [3, 7, 1, 3, 7, 1, 3, 7, 1]
            total = sum(int(r[i]) * weights[i] for i in range(9))
            return (total % 10) == 0
        elif rail.upper() == "CHAPS":
            # 6-digit UK sort code check
            return len(r) == 6 and r.isdigit()
        return len(r) >= 4
