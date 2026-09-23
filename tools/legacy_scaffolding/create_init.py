import os

code_schemas_init = """\"\"\"Pydantic v2 Canonical Banking Schemas and Contracts for PeX.\"\"\"
from app.schemas.canonical import (
    LifecycleStage, ExceptionProfile, ExceptionSeverity,
    CanonicalParty, CanonicalAccount, CanonicalPayment,
    CanonicalException, PeXCase
)
from app.schemas.context import (
    EvidenceItem, PolicyRule, HistoricalPrecedent,
    TokenizedInvestigationContext
)
from app.schemas.recommendation import (
    ActionType, ProposedFieldChange, CorroboratingEvidenceRef,
    RiskEvaluation, DecisionRecommendation
)
from app.schemas.approval import (
    ApprovalAction, UserRole, ApprovalRecord
)
from app.schemas.action import (
    GovernedActionContract, DeliveryReceipt, ActionStatus
)
from app.schemas.audit import (
    AuditEvent, ProvenanceChain, HashVerificationResult
)
from app.schemas.auth import (
    UserPersona, LoginRequest, LoginResponse
)
"""

with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\schemas\__init__.py", "w", encoding="utf-8") as f:
    f.write(code_schemas_init)

print("Created schemas/__init__.py")
