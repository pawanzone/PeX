"""In-Memory Reference Regulatory Directory & BoP Adapter.

TEST / REFERENCE ONLY.
Implements RegulatoryDirectoryPort with deterministic Balance of Payments (BoP) and purpose code derivations (CO-07).
Zero vendor SDK dependencies.
"""
from typing import Dict, List, Any, Optional
from app.ports.regulatory_directory_port import RegulatoryDirectoryPort
from app.schemas.contracts.wave1_schemas import (
    BoPReportingCodeRecord,
    RegulatoryPurposeRule,
    RegulatoryReportingDerivationResult,
)


class InMemoryRegulatoryDirectoryAdapter(RegulatoryDirectoryPort):
    """Hermetic reference implementation of RegulatoryDirectoryPort."""

    def __init__(
        self,
        bop_codes: Optional[Dict[str, BoPReportingCodeRecord]] = None,
        rules: Optional[Dict[str, List[RegulatoryPurposeRule]]] = None
    ):
        self._bop_codes: Dict[str, BoPReportingCodeRecord] = bop_codes or {
            "GOODS:BR": BoPReportingCodeRecord(bop_code="BOP-BR-101", description="Import of Capital Goods & Machinery", category="GOODS", corridor_applicability=["BR", "LATAM"]),
            "SERVICES:IN": BoPReportingCodeRecord(bop_code="BOP-IN-P0802", description="Software & Information Technology Services", category="SERVICES", corridor_applicability=["IN"]),
            "INVESTMENT:AE": BoPReportingCodeRecord(bop_code="BOP-AE-301", description="Foreign Direct Investment in Commercial Real Estate", category="INVESTMENT", corridor_applicability=["AE"]),
            "TRADE:CN": BoPReportingCodeRecord(bop_code="BOP-CN-121", description="General Merchandise Trade Settlement", category="TRADE", corridor_applicability=["CN"]),
        }

        self._rules: Dict[str, List[RegulatoryPurposeRule]] = rules or {
            "BR": [
                RegulatoryPurposeRule(
                    destination_country="BR",
                    currency="BRL",
                    mandatory_purpose_code="GDDS",
                    regulatory_statute="BACEN Circular 3691",
                    authority_name="BANCO_CENTRAL_DO_BRASIL",
                    details_description="Cross-border goods import declaration code"
                )
            ],
            "IN": [
                RegulatoryPurposeRule(
                    destination_country="IN",
                    currency="INR",
                    mandatory_purpose_code="P0802",
                    regulatory_statute="RBI Master Direction - Export/Import of Goods and Services",
                    authority_name="RESERVE_BANK_OF_INDIA",
                    details_description="Software consultancy and implementation services"
                )
            ],
            "CN": [
                RegulatoryPurposeRule(
                    destination_country="CN",
                    currency="CNY",
                    mandatory_purpose_code="GDSV",
                    regulatory_statute="SAFE Regulations on Foreign Exchange Settlement",
                    authority_name="STATE_ADMINISTRATION_OF_FOREIGN_EXCHANGE",
                    details_description="Cross-border merchandise trade declaration"
                )
            ]
        }

    def get_purpose_code_rules(
        self,
        destination_country: str,
        currency: str,
        amount: float
    ) -> List[RegulatoryPurposeRule]:
        country_norm = destination_country.strip().upper()
        return self._rules.get(country_norm, [])

    def resolve_bop_code(
        self,
        trade_category: str,
        corridor: str
    ) -> Optional[BoPReportingCodeRecord]:
        key = f"{trade_category.strip().upper()}:{corridor.strip().upper()}"
        if key in self._bop_codes:
            return self._bop_codes[key]
        for (k, _), rec in self._bop_codes.items():
            if rec.category.upper() == trade_category.strip().upper() and (corridor.upper() in rec.corridor_applicability or "ALL" in rec.corridor_applicability):
                return rec
        return None

    def derive_regulatory_reporting(
        self,
        transaction_context: Dict[str, Any]
    ) -> RegulatoryReportingDerivationResult:
        dest_country = str(transaction_context.get("destination_country") or transaction_context.get("creditor_country") or "BR").upper()
        trade_cat = str(transaction_context.get("trade_category") or "GOODS").upper()
        rules = self.get_purpose_code_rules(dest_country, transaction_context.get("currency", "USD"), float(transaction_context.get("amount", 0.0)))
        bop = self.resolve_bop_code(trade_cat, dest_country)

        if rules:
            r = rules[0]
            bop_code_str = bop.bop_code if bop else r.mandatory_purpose_code
            return RegulatoryReportingDerivationResult(
                success=True,
                authority_code=r.authority_name,
                reporting_code=bop_code_str,
                details_text=r.details_description,
                statute_reference=r.regulatory_statute,
                derivation_method="AUTHORITATIVE_CENTRAL_BANK_REGULATORY_DIRECTORY",
                is_mandatory=True
            )

        if bop:
            return RegulatoryReportingDerivationResult(
                success=True,
                authority_code=bop.reporting_authority,
                reporting_code=bop.bop_code,
                details_text=bop.description,
                statute_reference="Central Bank Balance of Payments Guideline",
                derivation_method="BOP_CATEGORY_DIRECTORY_LOOKUP",
                is_mandatory=True
            )

        return RegulatoryReportingDerivationResult(
            success=False,
            derivation_method="UNMAPPED_CORRIDOR_STATUTE",
            is_mandatory=True
        )
