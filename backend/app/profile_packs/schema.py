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


class RequiredEvidence(BaseModel):
    """One piece of mandatory evidence the engine will ask for, and how much it is trusted (1 = core record ... 4 = advisory)."""
    model_config = ConfigDict(extra="forbid")
    type: str
    tier: int = Field(ge=1, le=4)
    mandatory: bool = True   # False = asked for when available, never blocks


class EvidenceSpec(BaseModel):
    """The single source of the evidence a profile asks for (types, trust tiers, order). A bank's published
    configuration may override it; with nothing published this is what runs."""
    model_config = ConfigDict(extra="forbid")
    required: List[RequiredEvidence] = Field(default_factory=list)
    min_confidence: Optional[float] = Field(default=None, ge=0, le=1)

    @property
    def mandatory_types(self) -> List[str]:
        return [e.type for e in self.required if e.mandatory]

    @property
    def optional_types(self) -> List[str]:
        return [e.type for e in self.required if not e.mandatory]


class ApprovalSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    when_not_stp: str = "MAKER_CHECKER"   # MAKER_CHECKER | COMPLIANCE_THEN_RISK | SINGLE


class DecisionSpec(BaseModel):
    """For decision-support profiles: what a person is asked to decide, and by whom. PeX never picks an option."""
    model_config = ConfigDict(extra="forbid")
    target_field: str
    options: List[str] = Field(min_length=2)
    reviewer_role: str


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
    decision: Optional[DecisionSpec] = None

    @model_validator(mode="after")
    def _rules(self):
        if not _CODE.match(self.code):
            raise ValueError(f"bad profile code {self.code!r}")
        if self.outcome == Outcome.REPAIR and not self.resolver:
            raise ValueError("a REPAIR pack needs a resolver")
        if self.outcome != Outcome.REPAIR and self.stp != StpMode.NEVER:
            raise ValueError("only REPAIR packs may allow straight-through; others must be stp NEVER")
        if self.outcome != Outcome.REPAIR and not self.resolver and not self.decision:
            raise ValueError("a non-repair pack needs a resolver or a decision spec")
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
    policy: Any = None   # the active bank policy envelope
    extras: Dict[str, Any] = field(default_factory=dict)
