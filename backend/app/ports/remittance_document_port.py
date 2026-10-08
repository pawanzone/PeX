"""Remittance Document Port (SPI).

Defines abstract SPI for retrieving and parsing commercial invoice / ERP documents
and deriving structured remittance tags (<Strd>).
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave1_schemas import (
    InvoiceDocumentRecord,
    RemittanceParseResult,
    StructuredRemittanceRecord,
)


class RemittanceDocumentPort(ABC):
    """Abstract port for Remittance Document retrieval and parsing."""

    @abstractmethod
    def fetch_invoice_document(
        self,
        invoice_id: str
    ) -> Optional[InvoiceDocumentRecord]:
        """Retrieves authoritative invoice document from ERP / Billing directory."""
        pass

    @abstractmethod
    def parse_remittance_document(
        self,
        raw_doc_bytes_or_text: str
    ) -> RemittanceParseResult:
        """Parses invoice document text and extracts key business attributes."""
        pass

    @abstractmethod
    def extract_structured_remittance(
        self,
        invoice_data: Dict[str, Any]
    ) -> Optional[StructuredRemittanceRecord]:
        """Derives canonical ISO 20022 <Strd> remittance tags from invoice data."""
        pass
