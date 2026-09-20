"""Raw Bank Ingestion Event Schemas for Bank A, Bank B, and Bank C across all 5 Market Domains."""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class BankAEventPayload(BaseModel):
    payment_reference: str
    error_code: str
    error_message: str
    amount: float
    currency: str
    debtor_name: str
    debtor_account: str
    creditor_name: str
    creditor_iban: str
    creditor_bic: Optional[str] = None
    settlement_rail: str = "SWIFT_CBPR"
    timestamp: Optional[str] = None
    # Enriched domain metadata
    purpose_code: Optional[str] = None
    remittance_info: Optional[str] = None
    creditor_address: Optional[Dict[str, Any]] = None
    confirmation_of_payee_score: Optional[float] = None
    treasury_context: Optional[Dict[str, Any]] = None
    fx_details: Optional[Dict[str, Any]] = None
    compliance_flags: Optional[List[str]] = None

class BankBEventHeader(BaseModel):
    msg_type: str = "MT103_NACK"
    source_channel: str = "KAFKA_LEGACY"
    trn: str

class BankBEventBody(BaseModel):
    amount: float
    ccy: str
    ordering_customer: str
    ordering_account: str
    beneficiary_customer: str
    beneficiary_iban: str
    failure_reason: str
    exception_code: str
    # Enriched fields
    routing_code: Optional[str] = None
    intermediary_bic: Optional[str] = None
    cutoff_deadline: Optional[str] = None
    nostro_corridor_id: Optional[str] = None

class BankBEventPayload(BaseModel):
    header: BankBEventHeader
    body: BankBEventBody

class BankCEventPayload(BaseModel):
    message_id: str
    format: str = "ISO20022_WRAPPER"
    camt_code: str = "pacs.004.001.09"
    uetr: str
    debtor: Dict[str, Any]
    creditor: Dict[str, Any]
    amount: Dict[str, Any]
    return_reason: Dict[str, Any]
    charges_deducted: Optional[float] = 0.0
    original_settlement_date: Optional[str] = None

class RawBankEvent(BaseModel):
    event_id: str = Field(..., description="Unique Bank Source Event ID")
    source_bank_id: str = Field(..., description="e.g. BANK_A, BANK_B, BANK_C, GLOBAL_ROUTING")
    event_type: str = Field(..., description="e.g. PAYMENT_EXCEPTION, SETTLEMENT_FAILURE, SANCTIONS_ALERT, TREASURY_SHORTFALL")
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: Dict[str, Any]
