"""Contextual Authority Port (SPI).

Defines the abstract interface for determining the authoritative system of record
based on the operational, legal, or transactional question being answered.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.contracts.authority_schemas import (
    QuestionDomain,
    AuthorityResolutionContext,
)


class ContextualAuthorityPort(ABC):
    """Abstract port for contextual authority resolution."""

    @abstractmethod
    def resolve_authority(
        self,
        question_domain: QuestionDomain,
        context_payload: Dict[str, Any]
    ) -> AuthorityResolutionContext:
        """Resolves the authoritative system of record and confirms whether V_auth is satisfied."""
        pass
