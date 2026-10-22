"""Schema for profile packs and the resolver contract."""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Outcome(str, Enum):
    REPAIR = "REPAIR"                      # the engine can propose a repair; a resolver derives it
    DECISION_SUPPORT = "DECISION_SUPPORT"  # evidence is gathered and a person decides (no auto repair)
    INVESTIGATION = "INVESTIGATION"        # tracked investigation (for example funds trapped at a correspondent)


class StpMode(str, Enum):
    ALLOWED = "ALLOWED"            # straight-through when every predicate holds
    POLICY_GATED = "POLICY_GATED"  # straight-through only if the bank policy opts in
    NEVER = "NEVER"                # never straight-through; cannot be loosened by any tenant setting


_CODE = re.compile(r"^(DQ|PR|CO|TR|ST)-\d{2}$")


class EvidenceSpec(BaseModel):
    """Declared evidence. For now this mirrors the legacy profile spec (a test keeps them equal)."""
    model_config = ConfigDict(extra="forbid")
    mandatory: List[str] = Field(default_factory=list)
    min_confidence: Optional[float] = Field(default=None, ge=0, le=1)


class ApprovalSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    when_not_stp: str = "MAKER_CHECKER"   # MAKER_CHECKER | COMPLIANCE_THEN_RISK | SINGLE


class ProfilePack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    name: str
    family: str
    version: int = Field(ge=1)
    outcome: Outcome
    stp: StpMode
    evidence: EvidenceSpec = Field(default_factory=EvidenceSpec)
    checks: List[str] = Field(default_factory=list)
    resolver: Optional[str] = None
    authority_domain: str
    action: str = "REPAIR_AND_RELEASE"
    approval: ApprovalSpec = Field(default_factory=ApprovalSpec)

    @model_validator(mode="after")
    def _rules(self):
        if not _CODE.match(self.code):
            raise ValueError(f"bad profile code {self.code!r}")
        if self.outcome == Outcome.REPAIR and not self.resolver:
            raise ValueError("a REPAIR pack needs a resolver")
        if self.outcome != Outcome.REPAIR and self.stp != StpMode.NEVER:
            raise ValueError("only REPAIR packs may allow straight-through; others must be stp NEVER")
        if self.outcome == Outcome.REPAIR and self.stp == StpMode.NEVER:
            raise ValueError("a REPAIR pack cannot be stp NEVER (use DECISION_SUPPORT)")
        return self


class ResolutionResult(BaseModel):
    """What a resolver returns. The engine combines it with the shared predicates (evidence, authority, policy...)."""
    determined: bool = False   # R_det
    unique: bool = False       # R_uniq
    validated: bool = False    # V_det
    repaired_fields: List[Dict[str, Any]] = Field(default_factory=list)
    recommendation: Optional[Dict[str, Any]] = None
    basis: str = ""


@dataclass
class ResolutionContext:
    """Everything a resolver may read. Resolvers are pure: no I/O, no side effects."""
    profile: str
    pmt: Any
    evidence: Dict[str, Any]
    envelope: Any
    tenant_id: str = "DEFAULT_BANK"
    extras: Dict[str, Any] = field(default_factory=dict)
