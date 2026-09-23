"""Adversarial Cryptographic Tampering and Audit-Hash Invariant Tests (MST-034)."""
import pytest
from datetime import datetime
from app.core.hashing import calculate_event_hash, verify_audit_chain, GENESIS_HASH
from app.services.audit_service import audit_service
from app.db.session import SessionLocal
from app.db.models import AuditEventModel

def test_canonical_hash_determinism():
    """Validates that identical inputs yield identical SHA-256 digests deterministically."""
    ts = datetime.utcnow().isoformat()
    h1 = calculate_event_hash(
        event_index=1,
        timestamp_iso=ts,
        case_id="PEX-DET-001",
        stage_name="INTAKE",
        actor_id="SYS-01",
        action_name="INGEST",
        details="Wire payment received",
        prev_hash=GENESIS_HASH,
        amount=50000.0,
        currency="USD",
        debtor_account="ACC-DB-101",
        creditor_account="ACC-CR-202"
    )
    h2 = calculate_event_hash(
        event_index=1,
        timestamp_iso=ts,
        case_id="PEX-DET-001",
        stage_name="INTAKE",
        actor_id="SYS-01",
        action_name="INGEST",
        details="Wire payment received",
        prev_hash=GENESIS_HASH,
        amount=50000.00,  # equivalent float
        currency="USD",
        debtor_account="ACC-DB-101",
        creditor_account="ACC-CR-202"
    )
    assert h1 == h2
    assert len(h1) == 64

def test_tamper_detection_amount_mutation():
    """Validates that tampering with the monetary amount causes audit chain verification to fail."""
    ts1 = datetime.utcnow().isoformat()
    ts2 = datetime.utcnow().isoformat()
    
    h1 = calculate_event_hash(1, ts1, "CASE-T1", "INTAKE", "SYS", "INGEST", "Case 1", GENESIS_HASH, amount=10000.0, currency="USD", debtor_account="D1", creditor_account="C1")
    h2 = calculate_event_hash(2, ts2, "CASE-T1", "APPROVAL", "APR-3191", "APPROVE", "Approved", h1, amount=10000.0, currency="USD", debtor_account="D1", creditor_account="C1")
    
    events = [
        {"event_index": 1, "timestamp": ts1, "case_id": "CASE-T1", "stage_name": "INTAKE", "actor_id": "SYS", "action_name": "INGEST", "details": "Case 1", "amount": 10000.0, "currency": "USD", "debtor_account": "D1", "creditor_account": "C1", "prev_hash": GENESIS_HASH, "current_hash": h1},
        {"event_index": 2, "timestamp": ts2, "case_id": "CASE-T1", "stage_name": "APPROVAL", "actor_id": "APR-3191", "action_name": "APPROVE", "details": "Approved", "amount": 10000.0, "currency": "USD", "debtor_account": "D1", "creditor_account": "C1", "prev_hash": h1, "current_hash": h2}
    ]
    assert verify_audit_chain(events) is True

    # Tamper with amount in event 1 from $10,000 to $10,000,000
    events[0]["amount"] = 10000000.0
    assert verify_audit_chain(events) is False

def test_tamper_detection_currency_mutation():
    """Validates that altering the payment currency breaks the cryptographic hash chain."""
    ts = datetime.utcnow().isoformat()
    h1 = calculate_event_hash(1, ts, "CASE-T2", "INTAKE", "SYS", "INGEST", "Case 2", GENESIS_HASH, amount=25000.0, currency="USD", debtor_account="D2", creditor_account="C2")
    
    events = [
        {"event_index": 1, "timestamp": ts, "case_id": "CASE-T2", "stage_name": "INTAKE", "actor_id": "SYS", "action_name": "INGEST", "details": "Case 2", "amount": 25000.0, "currency": "USD", "debtor_account": "D2", "creditor_account": "C2", "prev_hash": GENESIS_HASH, "current_hash": h1}
    ]
    assert verify_audit_chain(events) is True

    # Tamper with currency from USD to EUR
    events[0]["currency"] = "EUR"
    assert verify_audit_chain(events) is False

def test_tamper_detection_debtor_account_mutation():
    """Validates that modifying the source debtor account breaks audit chain integrity."""
    ts = datetime.utcnow().isoformat()
    h1 = calculate_event_hash(1, ts, "CASE-T3", "INTAKE", "SYS", "INGEST", "Case 3", GENESIS_HASH, amount=75000.0, currency="GBP", debtor_account="GB82WEST123456", creditor_account="GB82BARC987654")
    
    events = [
        {"event_index": 1, "timestamp": ts, "case_id": "CASE-T3", "stage_name": "INTAKE", "actor_id": "SYS", "action_name": "INGEST", "details": "Case 3", "amount": 75000.0, "currency": "GBP", "debtor_account": "GB82WEST123456", "creditor_account": "GB82BARC987654", "prev_hash": GENESIS_HASH, "current_hash": h1}
    ]
    assert verify_audit_chain(events) is True

    # Tamper with debtor account
    events[0]["debtor_account"] = "GB82ROGUE999999"
    assert verify_audit_chain(events) is False

def test_tamper_detection_creditor_account_mutation():
    """Validates that modifying the destination creditor account breaks audit chain integrity."""
    ts = datetime.utcnow().isoformat()
    h1 = calculate_event_hash(1, ts, "CASE-T4", "INTAKE", "SYS", "INGEST", "Case 4", GENESIS_HASH, amount=120000.0, currency="EUR", debtor_account="NL91ABNA01", creditor_account="DE8937040044")
    
    events = [
        {"event_index": 1, "timestamp": ts, "case_id": "CASE-T4", "stage_name": "INTAKE", "actor_id": "SYS", "action_name": "INGEST", "details": "Case 4", "amount": 120000.0, "currency": "EUR", "debtor_account": "NL91ABNA01", "creditor_account": "DE8937040044", "prev_hash": GENESIS_HASH, "current_hash": h1}
    ]
    assert verify_audit_chain(events) is True

    # Tamper with creditor account
    events[0]["creditor_account"] = "DE89ATTACKER7777"
    assert verify_audit_chain(events) is False

def test_tamper_detection_multi_field_mutation():
    """Validates that mutating both amount and routing fields is detected."""
    ts = datetime.utcnow().isoformat()
    h1 = calculate_event_hash(1, ts, "CASE-T5", "INTAKE", "SYS", "INGEST", "Case 5", GENESIS_HASH, amount=500.0, currency="USD", debtor_account="ACC-1", creditor_account="ACC-2")
    
    events = [
        {"event_index": 1, "timestamp": ts, "case_id": "CASE-T5", "stage_name": "INTAKE", "actor_id": "SYS", "action_name": "INGEST", "details": "Case 5", "amount": 500.0, "currency": "USD", "debtor_account": "ACC-1", "creditor_account": "ACC-2", "prev_hash": GENESIS_HASH, "current_hash": h1}
    ]
    assert verify_audit_chain(events) is True

    # Tamper with amount and creditor account
    events[0]["amount"] = 5000000.0
    events[0]["creditor_account"] = "ACC-OFFSHORE-99"
    assert verify_audit_chain(events) is False

def test_end_to_end_audit_service_database_tamper_detection():
    """End-to-end database test logging events and testing tamper detection via AuditService."""
    cid = "PEX-E2E-TAMPER-TEST"
    ev1 = audit_service.log_event(
        case_id=cid,
        correlation_id="UETR-E2E-1",
        stage_name="INTAKE",
        actor_id="SYS-INGEST",
        actor_role="SYSTEM",
        action_name="INGEST_EXCEPTION",
        details="Ingested wire exception",
        amount=88000.0,
        currency="USD",
        debtor_account="ACC-D-88",
        creditor_account="ACC-C-88"
    )
    
    res = audit_service.verify_chain()
    assert res.is_intact is True

    # Direct database manipulation simulating a malicious database administrator
    db = SessionLocal()
    try:
        db_ev = db.query(AuditEventModel).filter(AuditEventModel.event_index == ev1.event_index).first()
        assert db_ev is not None
        original_amt = db_ev.amount
        # Maliciously mutate amount in database
        db_ev.amount = 99999999.0
        db.commit()
    finally:
        db.close()

    # Audit service verification must now detect the tampering!
    tampered_res = audit_service.verify_chain()
    assert tampered_res.is_intact is False

    # Restore database state
    db = SessionLocal()
    try:
        db_ev = db.query(AuditEventModel).filter(AuditEventModel.event_index == ev1.event_index).first()
        db_ev.amount = original_amt
        db.commit()
    finally:
        db.close()

    clean_res = audit_service.verify_chain()
    assert clean_res.is_intact is True
