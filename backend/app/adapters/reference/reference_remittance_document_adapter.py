"""In-Memory Reference Remittance Document & ERP Adapter.

TEST / REFERENCE ONLY.
Implements RemittanceDocumentPort with deterministic parsing and ISO 20022 <Strd> extraction.
Zero vendor SDK dependencies.
"""
import re
from typing import Dict, List, Any, Optional
from app.ports.remittance_document_port import RemittanceDocumentPort
from app.schemas.contracts.wave1_schemas import (
    InvoiceDocumentRecord,
    RemittanceParseResult,
    StructuredRemittanceRecord,
)


class InMemoryRemittanceDocumentAdapter(RemittanceDocumentPort):
    """Hermetic reference implementation of RemittanceDocumentPort."""

    def __init__(
        self,
        invoices: Optional[Dict[str, InvoiceDocumentRecord]] = None
    ):
        self._invoices: Dict[str, InvoiceDocumentRecord] = invoices or {
            "INV-2026-OCT-8891": InvoiceDocumentRecord(
                invoice_id="INV-2026-OCT-8891",
                debtor_tax_id="FR-99-1234567",
                creditor_tax_id="GB-88-7654321",
                invoice_date="2026-10-01",
                total_amount=250000.0,
                currency="EUR",
                structured_remittance=StructuredRemittanceRecord(
                    referred_document_number="INV-2026-OCT-8891",
                    referred_document_date="2026-10-01",
                    referred_document_amount=250000.0,
                    referred_document_currency="EUR",
                    debtor_reference="PO-AIRBUS-8891",
                    creditor_reference="CINV-RR-8891",
                    remittance_narrative="AEROSPACE JET ENGINE OVERHAUL SERVICE"
                )
            ),
            "INV-2026-US-4401": InvoiceDocumentRecord(
                invoice_id="INV-2026-US-4401",
                debtor_tax_id="US-11-2233445",
                creditor_tax_id="US-55-6677889",
                invoice_date="2026-10-05",
                total_amount=45000.0,
                currency="USD",
                structured_remittance=StructuredRemittanceRecord(
                    referred_document_number="INV-2026-US-4401",
                    referred_document_date="2026-10-05",
                    referred_document_amount=45000.0,
                    referred_document_currency="USD",
                    debtor_reference="PO-CORP-4401",
                    creditor_reference="CINV-ACME-4401",
                    remittance_narrative="ANNUAL CLOUD INFRASTRUCTURE LICENSES"
                )
            )
        }

    def fetch_invoice_document(
        self,
        invoice_id: str
    ) -> Optional[InvoiceDocumentRecord]:
        return self._invoices.get(invoice_id.strip())

    def parse_remittance_document(
        self,
        raw_doc_bytes_or_text: str
    ) -> RemittanceParseResult:
        text = (raw_doc_bytes_or_text or "").strip()
        if not text:
            return RemittanceParseResult(success=False, parsing_notes=["Empty document content."])

        # Regex search for common invoice number patterns: INV-..., INVOICE #..., CINV-...
        inv_match = re.search(r'\b(INV-[\w-]+|INVOICE\s*(?:NO|NUMBER|#)?\s*[:\s]*([\w-]+)|CINV-[\w-]+)\b', text, re.IGNORECASE)
        inv_id = None
        if inv_match:
            inv_id = inv_match.group(1) or inv_match.group(2)

        # Regex search for amount: $12,345.67 or EUR 12345.67
        amt_match = re.search(r'(?:USD|EUR|GBP|\$|€|£)\s*([\d,]+(?:\.\d{2})?)', text, re.IGNORECASE)
        amt = None
        if amt_match:
            try:
                amt = float(amt_match.group(1).replace(",", ""))
            except ValueError:
                pass

        if inv_id and inv_id in self._invoices:
            inv_rec = self._invoices[inv_id]
            return RemittanceParseResult(
                success=True,
                extracted_invoice_id=inv_id,
                extracted_amount=amt or inv_rec.total_amount,
                structured_remittance=inv_rec.structured_remittance,
                parsing_notes=["Successfully matched against authoritative invoice repository."]
            )

        if inv_id:
            strd = StructuredRemittanceRecord(
                referred_document_number=inv_id,
                referred_document_amount=amt,
                remittance_narrative=text[:140]
            )
            return RemittanceParseResult(
                success=True,
                extracted_invoice_id=inv_id,
                extracted_amount=amt,
                structured_remittance=strd,
                parsing_notes=["Derived structured remittance from raw document text."]
            )

        return RemittanceParseResult(
            success=False,
            parsing_notes=["No structured invoice identifier could be extracted from text."]
        )

    def extract_structured_remittance(
        self,
        invoice_data: Dict[str, Any]
    ) -> Optional[StructuredRemittanceRecord]:
        inv_id = invoice_data.get("invoice_id") or invoice_data.get("referred_document_number")
        if not inv_id:
            return None
        return StructuredRemittanceRecord(
            referred_document_number=str(inv_id),
            referred_document_date=invoice_data.get("invoice_date"),
            referred_document_amount=float(invoice_data["total_amount"]) if "total_amount" in invoice_data else None,
            referred_document_currency=invoice_data.get("currency"),
            debtor_reference=invoice_data.get("debtor_reference"),
            creditor_reference=invoice_data.get("creditor_reference"),
            remittance_narrative=invoice_data.get("remittance_narrative")
        )
