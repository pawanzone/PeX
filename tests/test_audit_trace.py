"""Tests for Cryptographic SHA-256 Continuous Audit Chaining."""
import pytest
from app.services.audit_service import audit_service
from app.core.hashing import verify_audit_chain

def test_audit_chain_tamper_detection():
    # Log 3 events
    audit_service.log_event("CASE-AUD-01", "UETR-1", "INTAKE", "SYSTEM", "SYS", "EVENT_1", "Details 1")
    audit_service.log_event("CASE-AUD-01", "UETR-1", "AI_INVESTIGATION", "AI", "MODEL", "EVENT_2", "Details 2")
    audit_service.log_event("CASE-AUD-01", "UETR-1", "SETTLEMENT", "BANK", "HUB", "EVENT_3", "Details 3")
    
    res = audit_service.verify_chain()
    assert res.is_intact is True
    assert res.total_events_checked >= 3
