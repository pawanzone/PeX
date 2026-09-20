"""Cryptographic SHA-256 Hash Chain Utility for Immutable Provenance."""
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def calculate_event_hash(
    event_index: int,
    timestamp_iso: str,
    case_id: str,
    stage_name: str,
    actor_id: str,
    action_name: str,
    details: str,
    prev_hash: str
) -> str:
    payload = {
        "event_index": event_index,
        "timestamp": timestamp_iso,
        "case_id": case_id,
        "stage_name": stage_name,
        "actor_id": actor_id,
        "action_name": action_name,
        "details": details,
        "prev_hash": prev_hash
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def verify_audit_chain(events: List[Dict[str, Any]]) -> bool:
    if not events:
        return True
    
    for i, event in enumerate(events):
        expected_prev = GENESIS_HASH if i == 0 else events[i-1]["current_hash"]
        if event.get("prev_hash") != expected_prev:
            return False
        
        computed_hash = calculate_event_hash(
            event_index=event["event_index"],
            timestamp_iso=event["timestamp"] if isinstance(event["timestamp"], str) else event["timestamp"].isoformat(),
            case_id=event["case_id"],
            stage_name=event["stage_name"],
            actor_id=event["actor_id"],
            action_name=event["action_name"],
            details=event["details"],
            prev_hash=expected_prev
        )
        if event.get("current_hash") != computed_hash:
            return False
            
    return True
