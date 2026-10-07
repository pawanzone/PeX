"""Provider-Neutral Routing Directory Port and Synthetic Adapter for DQ-08.

Supports the provider-neutral abstraction:
RoutingCode = <Jurisdiction, ClearingSystem, Identifier, ApplicableRail, Authority, Status, Successor, Reachability>

Governed by:
- PeX_Phase2_Taxonomy_Remediation_Architecture_Decision_v0.2.md
- PeX_Phase2_DQ08_PR08_Remediation_Implementation_Contract_v0.1.md
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field


class RoutingIdentifierStatus(str, Enum):
    """Authoritative lifecycle status of a national clearing routing identifier."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    RETIRED = "RETIRED"
    MERGED = "MERGED"
    DEFUNCT = "DEFUNCT"
    UNKNOWN = "UNKNOWN"
    NOT_FOUND = "NOT_FOUND"


class CentralBankMergerEntry(BaseModel):
    """Authoritative Central Bank Merger / Legal Bank Succession Record.
    
    Proves legal entity succession in official clearing registries (e.g. Federal Reserve Reg J, BoE ISCD).
    """
    retired_routing_code: str
    clearing_system: str
    institution_legal_name: str
    successor_routing_codes: List[str] = Field(default_factory=list)
    merger_effective_date: str = "2020-01-01"
    authority_source: str = "FEDERAL_RESERVE_E_PAYMENTS_DIRECTORY / BOE_ISCD"
    is_unambiguous_1to1: bool = True
    supported_clearing_rails: List[str] = Field(default_factory=lambda: ["FEDWIRE", "ACH", "CHAPS", "BACS", "FPS"])
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=1))
    freshness_seconds: int = 86400

    @property
    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at or (now - self.retrieved_at).total_seconds() > self.freshness_seconds


class RoutingDirectoryEntry(BaseModel):
    """Authoritative clearing registry entry for a national routing identifier."""
    routing_identifier: str
    clearing_system: str                                      # e.g. "USABA", "GBDSC"
    jurisdiction: str                                         # e.g. "US", "GB"
    institution_name: str
    status: RoutingIdentifierStatus
    supported_rails: List[str] = Field(default_factory=lambda: ["FEDWIRE", "ACH", "CHAPS", "BACS", "FPS"])
    merger_record: Optional[CentralBankMergerEntry] = None
    provider: str = "NATIONAL_CLEARING_DIRECTORY_PROVIDER (DEMO_ONLY_DEFAULT)"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    effective_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=1))
    freshness_seconds: int = 86400                            # DEMO_ONLY_DEFAULT: Production requires BANK_CONFIG_REQUIRED

    @property
    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at or (now - self.retrieved_at).total_seconds() > self.freshness_seconds


class BankCounterpartySSI(BaseModel):
    """Authoritative Bank Counterparty Standard Settlement Instructions (SSI) for Routing Codes."""
    counterparty_id: str
    clearing_system: str = "USABA"
    mandated_routing_code: Optional[str] = None
    allowed_routing_codes: List[str] = Field(default_factory=list)
    is_authorized: bool = True
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TargetRailRoutingSpec(BaseModel):
    """Target clearing rail reachability specification."""
    clearing_system: str = "USABA"
    target_rail: str = "FEDWIRE"
    corridor: Optional[str] = "US"
    direct_participant_required: bool = False


class RoutingDirectoryAdapterPort(ABC):
    """Provider-neutral port for querying national clearing routing directories and merger tables."""

    @abstractmethod
    def lookup_routing_code(self, identifier: str, clearing_system: str) -> Optional[RoutingDirectoryEntry]:
        """Looks up authoritative status, rails, and metadata for a routing identifier."""
        pass

    @abstractmethod
    def get_successor(self, identifier: str, clearing_system: str) -> Optional[CentralBankMergerEntry]:
        """Retrieves legal successor routing code(s) from central bank merger tables."""
        pass

    @abstractmethod
    def is_rail_reachable(self, identifier: str, clearing_system: str, target_rail: str) -> bool:
        """Determines if the institution routing code is an active node on the requested clearing rail."""
        pass


class SyntheticRoutingDirectoryAdapter(RoutingDirectoryAdapterPort):
    """Provider-neutral in-memory synthetic routing directory adapter for Level-1 testing and validation.
    
    Contains deterministic fixtures for US ABA RTNs and UK Sort Codes.
    Production deployments substitute live Federal Reserve / Bank of England connectors (BANK_CONFIG_REQUIRED).
    """

    def __init__(self):
        self._entries: Dict[Tuple[str, str], RoutingDirectoryEntry] = {}
        self._merger_table: Dict[Tuple[str, str], CentralBankMergerEntry] = {}
        self._seed_directory()

    def _seed_directory(self):
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=1)

        # =========================================================================
        # 1. US Fedwire / ACH (USABA) Entries
        # =========================================================================
        # Active Primary US ABAs
        self._add_entry("021000021", "USABA", "US", "JPMorgan Chase Bank NA New York", RoutingIdentifierStatus.ACTIVE, ["FEDWIRE", "ACH", "CHIPS"], now, exp)
        self._add_entry("026009593", "USABA", "US", "Bank of America NA New York", RoutingIdentifierStatus.ACTIVE, ["FEDWIRE", "ACH"], now, exp)
        self._add_entry("121000249", "USABA", "US", "Wells Fargo Bank NA San Francisco", RoutingIdentifierStatus.ACTIVE, ["FEDWIRE", "ACH"], now, exp)
        self._add_entry("071000013", "USABA", "US", "Federal Reserve Bank of Chicago", RoutingIdentifierStatus.ACTIVE, ["FEDWIRE", "ACH"], now, exp)

        # Active US ABA Restricted to ACH Only (Unreachable on Fedwire)
        self._add_entry("091000019", "USABA", "US", "Minneapolis Regional ACH Node", RoutingIdentifierStatus.ACTIVE, ["ACH"], now, exp)

        # Retired US ABA with Single Unambiguous 1:1 Successor
        m_chem = CentralBankMergerEntry(
            retired_routing_code="021000089",
            clearing_system="USABA",
            institution_legal_name="Chemical Bank (Merged into JPMorgan Chase)",
            successor_routing_codes=["021000021"],
            merger_effective_date="1996-03-31",
            authority_source="FEDERAL_RESERVE_REG_J_MERGER_DIRECTORY",
            is_unambiguous_1to1=True,
            supported_clearing_rails=["FEDWIRE", "ACH", "CHIPS"],
            retrieved_at=now,
            expires_at=exp
        )
        self._add_merger(m_chem)
        self._add_entry("021000089", "USABA", "US", "Chemical Bank (Retired)", RoutingIdentifierStatus.MERGED, ["FEDWIRE", "ACH"], now, exp, m_chem)

        # Retired US ABA with Single 1:1 Successor (First Interstate -> Wells Fargo)
        m_fi = CentralBankMergerEntry(
            retired_routing_code="122000496",
            clearing_system="USABA",
            institution_legal_name="First Interstate Bank (Merged into Wells Fargo)",
            successor_routing_codes=["121000249"],
            merger_effective_date="1996-04-01",
            authority_source="FEDERAL_RESERVE_REG_J_MERGER_DIRECTORY",
            is_unambiguous_1to1=True,
            supported_clearing_rails=["FEDWIRE", "ACH"],
            retrieved_at=now,
            expires_at=exp
        )
        self._add_merger(m_fi)
        self._add_entry("122000496", "USABA", "US", "First Interstate Bank (Retired)", RoutingIdentifierStatus.MERGED, ["FEDWIRE", "ACH"], now, exp, m_fi)

        # Retired US ABA with 1:N Ambiguous Split Successors
        m_split = CentralBankMergerEntry(
            retired_routing_code="021000128",
            clearing_system="USABA",
            institution_legal_name="Marine Midland Bank (Split Acquisition)",
            successor_routing_codes=["021000021", "026009593"],
            merger_effective_date="1999-12-31",
            authority_source="FEDERAL_RESERVE_REG_J_MERGER_DIRECTORY",
            is_unambiguous_1to1=False,
            supported_clearing_rails=["FEDWIRE", "ACH"],
            retrieved_at=now,
            expires_at=exp
        )
        self._add_merger(m_split)
        self._add_entry("021000128", "USABA", "US", "Marine Midland Split Division", RoutingIdentifierStatus.MERGED, ["FEDWIRE", "ACH"], now, exp, m_split)

        # Inactive US ABA with ZERO Successors (Defunct Institution)
        self._add_entry("021001088", "USABA", "US", "Defunct Trust Corp New York", RoutingIdentifierStatus.DEFUNCT, [], now, exp)

        # =========================================================================
        # 2. UK CHAPS / Bacs / FPS (GBDSC) Entries
        # =========================================================================
        # Active Primary UK Sort Codes
        self._add_entry("200000", "GBDSC", "GB", "Barclays Bank UK PLC London Head Office", RoutingIdentifierStatus.ACTIVE, ["CHAPS", "BACS", "FPS"], now, exp)
        self._add_entry("400515", "GBDSC", "GB", "HSBC Bank UK PLC London", RoutingIdentifierStatus.ACTIVE, ["CHAPS", "BACS", "FPS"], now, exp)
        self._add_entry("600001", "GBDSC", "GB", "NatWest Bank PLC London", RoutingIdentifierStatus.ACTIVE, ["CHAPS", "BACS", "FPS"], now, exp)

        # Retired UK Sort Code with 1:1 Successor
        m_barc = CentralBankMergerEntry(
            retired_routing_code="200001",
            clearing_system="GBDSC",
            institution_legal_name="Barclays Sub-Branch (Consolidated to Central)",
            successor_routing_codes=["200000"],
            merger_effective_date="2018-05-01",
            authority_source="BANK_OF_ENGLAND_ISCD_MERGER_TABLE",
            is_unambiguous_1to1=True,
            supported_clearing_rails=["CHAPS", "BACS", "FPS"],
            retrieved_at=now,
            expires_at=exp
        )
        self._add_merger(m_barc)
        self._add_entry("200001", "GBDSC", "GB", "Barclays Old Branch (Consolidated)", RoutingIdentifierStatus.RETIRED, ["CHAPS", "BACS"], now, exp, m_barc)

        # Retired UK Sort Code with 1:N Ambiguous Successors
        m_midland = CentralBankMergerEntry(
            retired_routing_code="400500",
            clearing_system="GBDSC",
            institution_legal_name="Midland Bank Historical Division (Split)",
            successor_routing_codes=["400515", "600001"],
            merger_effective_date="1992-06-30",
            authority_source="BANK_OF_ENGLAND_ISCD_MERGER_TABLE",
            is_unambiguous_1to1=False,
            supported_clearing_rails=["CHAPS", "BACS"],
            retrieved_at=now,
            expires_at=exp
        )
        self._add_merger(m_midland)
        self._add_entry("400500", "GBDSC", "GB", "Midland Bank Historical Split", RoutingIdentifierStatus.RETIRED, ["CHAPS", "BACS"], now, exp, m_midland)

    def _add_entry(
        self,
        identifier: str,
        clearing_system: str,
        jurisdiction: str,
        institution_name: str,
        status: RoutingIdentifierStatus,
        supported_rails: List[str],
        retrieved_at: datetime,
        expires_at: datetime,
        merger_record: Optional[CentralBankMergerEntry] = None
    ):
        key = (identifier.strip(), clearing_system.strip().upper())
        self._entries[key] = RoutingDirectoryEntry(
            routing_identifier=identifier.strip(),
            clearing_system=clearing_system.strip().upper(),
            jurisdiction=jurisdiction.strip().upper(),
            institution_name=institution_name,
            status=status,
            supported_rails=supported_rails,
            merger_record=merger_record,
            retrieved_at=retrieved_at,
            effective_at=retrieved_at,
            expires_at=expires_at,
            freshness_seconds=86400
        )

    def _add_merger(self, entry: CentralBankMergerEntry):
        key = (entry.retired_routing_code.strip(), entry.clearing_system.strip().upper())
        self._merger_table[key] = entry

    def lookup_routing_code(self, identifier: str, clearing_system: str) -> Optional[RoutingDirectoryEntry]:
        clean_id = identifier.strip().replace("-", "")
        clean_sys = clearing_system.strip().upper()
        return self._entries.get((clean_id, clean_sys))

    def get_successor(self, identifier: str, clearing_system: str) -> Optional[CentralBankMergerEntry]:
        clean_id = identifier.strip().replace("-", "")
        clean_sys = clearing_system.strip().upper()
        return self._merger_table.get((clean_id, clean_sys))

    def is_rail_reachable(self, identifier: str, clearing_system: str, target_rail: str) -> bool:
        entry = self.lookup_routing_code(identifier, clearing_system)
        if not entry or entry.status != RoutingIdentifierStatus.ACTIVE:
            return False
        return target_rail.strip().upper() in [r.upper() for r in entry.supported_rails]
