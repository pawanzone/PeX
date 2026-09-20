with open(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\schemas\canonical.py", "a", encoding="utf-8") as f:
    f.write("""

class PeXCase(BaseModel):
    case_id: str
    payment_id: str
    uetr: str
    payment_ref: str
    profile: ExceptionProfile
    error_code: str
    reason: str
    amount: float
    currency: str
    payment_rail: str
    debtor_party: Dict[str, Any]
    debtor_account: Dict[str, Any]
    creditor_party: Dict[str, Any]
    creditor_account: Dict[str, Any]
    queue: str
    status: LifecycleStage
    severity: ExceptionSeverity
    priority: ExceptionPriority
    sla_due_at: datetime
    dual_auth_required: bool = False
    ai_confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approval_history: List[Dict[str, Any]] = []
    settled_at: Optional[str] = None
""")

print("Added PeXCase to canonical.py")
