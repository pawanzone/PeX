"""Evidence Acquisition Port (SPI).

Defines the abstract interface for acquiring evidence across all 4 acquisition modes:
Mode 1 (Inbound Payload), Mode 2 (API Connector), Mode 3 (Bank Push), Mode 4 (HITL Operator).
Reference: PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md Section 2 & 5.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.schemas.contracts.evidence_schemas import EvidenceItem
from app.schemas.contracts.evidence_config_schemas import HitlEvidenceSubmissionRequest


class EvidenceAcquisitionPort(ABC):
    """Abstract port for acquiring evidence across inbound, outbound API, push, and HITL channels."""

    @abstractmethod
    def acquire_inbound_mode1(
        self,
        case_id: str,
        profile_id: str,
        payload_data: Dict[str, Any]
    ) -> List[EvidenceItem]:
        """Parses and wraps pre-gathered evidence bundled directly in the inbound exception payload."""
        pass

    @abstractmethod
    def query_api_connector_mode2(
        self,
        case_id: str,
        source_id: str,
        query_params: Dict[str, Any]
    ) -> Optional[EvidenceItem]:
        """Executes an automated outbound inquiry against a bank system API via Port adapter (Progressive/Optional)."""
        pass

    @abstractmethod
    def receive_bank_push_mode3(
        self,
        case_id: str,
        profile_id: str,
        event_type: str,
        push_payload: Dict[str, Any]
    ) -> EvidenceItem:
        """Processes an asynchronous event pushed by a bank system (e.g. statement ready, AML cleared)."""
        pass

    @abstractmethod
    def receive_hitl_submission_mode4(
        self,
        submission: HitlEvidenceSubmissionRequest
    ) -> List[EvidenceItem]:
        """Converts human operator input submitted via the PeX resolution workspace into structured evidence items."""
        pass
