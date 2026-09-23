import os

base_backend = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app"

services = {}

# 1. services/data_loader.py
services["services/data_loader.py"] = """\"\"\"Synthetic Data Loader & In-Memory Relational Repository for PeX.\"\"\"
import csv
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.config import settings
from app.core.tokenization import token_vault
from app.schemas.canonical import (
    CanonicalPayment, CanonicalException, CanonicalParty, CanonicalAccount,
    LifecycleStage, ExceptionProfile, ExceptionSeverity, ExceptionPriority, CaseSummary
)
from app.schemas.context import PolicyRule, EvidenceItem, HistoricalPrecedent
from app.schemas.recommendation import DecisionRecommendation
from app.schemas.approval import ApprovalRecord
from app.schemas.action import GovernedActionContract, DeliveryReceipt
from app.schemas.audit import AuditEvent

class InMemoryRepository:
    def __init__(self):
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.banks: Dict[str, Dict[str, Any]] = {}
        self.bank_source_events: Dict[str, Dict[str, Any]] = {}
        self.beneficiaries: Dict[str, Dict[str, Any]] = {}
        self.evidence: Dict[str, Dict[str, Any]] = {}
        self.exceptions_raw: Dict[str, Dict[str, Any]] = {}
        self.historical_cases: List[Dict[str, Any]] = []
        self.kyc_profiles: Dict[str, Dict[str, Any]] = {}
        self.parties: Dict[str, Dict[str, Any]] = {}
        self.payments_raw: Dict[str, Dict[str, Any]] = {}
        self.policies: List[PolicyRule] = []
        self.reference_data: Dict[str, Dict[str, Any]] = {}
        self.screening_results: Dict[str, List[Dict[str, Any]]] = {}
        self.ground_truth: Dict[str, Dict[str, Any]] = {}
        
        # Active runtime states
        self.cases: Dict[str, Dict[str, Any]] = {}
        self.recommendations: Dict[str, DecisionRecommendation] = {}
        self.approvals: Dict[str, List[ApprovalRecord]] = {}
        self.actions: Dict[str, GovernedActionContract] = {}
        self.receipts: Dict[str, DeliveryReceipt] = {}
        self.audit_log: List[AuditEvent] = []
        self.latest_chain_hash: str = "0000000000000000000000000000000000000000000000000000000000000000"

    def _read_csv(self, file_path: Path) -> List[Dict[str, str]]:
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return [dict(row) for row in reader]

    def load_all_data(self):
        data_dir = settings.DATA_DIR
        if not data_dir.exists():
            print(f"Warning: Synthetic data directory not found at {data_dir}")
            return

        # 1. Token Map
        token_rows = self._read_csv(data_dir / "token_map.csv")
        token_vault.preload_tokens(token_rows)

        # 2. Reference Data & Banks
        for row in self._read_csv(data_dir / "reference_data.csv"):
            key = row.get("ref_key") or row.get("id") or str(len(self.reference_data))
            self.reference_data[key] = row
            
        for row in self._read_csv(data_dir / "banks.csv"):
            self.banks[row.get("bank_id", "")] = row

        # 3. Parties & Accounts & Beneficiaries
        for row in self._read_csv(data_dir / "parties.csv"):
            self.parties[row.get("party_id", "")] = row
            
        for row in self._read_csv(data_dir / "accounts.csv"):
            self.accounts[row.get("account_id", "")] = row

        for row in self._read_csv(data_dir / "beneficiaries.csv"):
            b_id = row.get("beneficiary_id") or row.get("id", "")
            self.beneficiaries[b_id] = row

        # 4. KYC & Screening
        for row in self._read_csv(data_dir / "kyc_profiles.csv"):
            self.kyc_profiles[row.get("party_id", "")] = row

        for row in self._read_csv(data_dir / "screening_results.csv"):
            pid = row.get("party_id", "")
            if pid not in self.screening_results:
                self.screening_results[pid] = []
            self.screening_results[pid].append(row)

        # 5. Policies
        for row in self._read_csv(data_dir / "policies.csv"):
            prof_str = row.get("exception_profile") or row.get("profile", "INVALID_IBAN")
            try:
                prof = ExceptionProfile(prof_str)
            except Exception:
                prof = ExceptionProfile.INVALID_IBAN
            
            mand_str = row.get("mandatory_evidence") or row.get("evidence_required", "")
            mand_list = [e.strip() for e in mand_str.split(",") if e.strip()] if mand_str else ["BENEFICIARY_PROFILE", "ACCOUNT_DIRECTORY"]
            
            rule = PolicyRule(
                policy_id=row.get("policy_id", f"POL-{len(self.policies)+1}"),
                profile=prof,
                rule_code=row.get("rule_code", "POL-DEF-01"),
                rule_description=row.get("rule_description", row.get("description", "Governed Exception Policy")),
                mandatory_evidence=mand_list,
                auto_repair_eligible=row.get("auto_repair_eligible", "false").lower() == "true",
                max_amount_threshold=float(row.get("max_amount_threshold", "1000000.0")),
                required_confidence_threshold=float(row.get("required_confidence_threshold", "0.85"))
            )
            self.policies.append(rule)

        # 6. Historical Cases
        self.historical_cases = self._read_csv(data_dir / "historical_cases.csv")

        # 7. Ground Truth
        for row in self._read_csv(data_dir / "evaluation_ground_truth.csv"):
            self.ground_truth[row.get("case_id", "")] = row

        # 8. Bank Source Events & Payments & Exceptions
        for row in self._read_csv(data_dir / "bank_source_events.csv"):
            self.bank_source_events[row.get("event_id", "")] = row

        for row in self._read_csv(data_dir / "payments.csv"):
            self.payments_raw[row.get("payment_id", "")] = row

        for row in self._read_csv(data_dir / "exceptions.csv"):
            self.exceptions_raw[row.get("exception_id", "")] = row

        # Initialize Synthetic Cases into Live Case Store
        self._initialize_live_cases()
        print(f"Loaded {len(self.cases)} live cases from synthetic data fixtures.")

    def _initialize_live_cases(self):
        # Map raw payments and exceptions into live case representations
        for exc_id, exc_row in self.exceptions_raw.items():
            case_id = exc_row.get("case_id") or f"PEX-{exc_id}"
            payment_id = exc_row.get("payment_id", "")
            pmt_row = self.payments_raw.get(payment_id, {})
            
            amount = float(pmt_row.get("amount") or exc_row.get("amount") or 42000.0)
            currency = pmt_row.get("currency") or exc_row.get("currency") or "USD"
            
            prof_str = exc_row.get("exception_profile") or exc_row.get("profile") or "INVALID_IBAN"
            try:
                profile = ExceptionProfile(prof_str)
            except Exception:
                profile = ExceptionProfile.INVALID_IBAN

            # Determine initial queue & severity & priority
            queue = "Repair"
            if profile in [ExceptionProfile.SANCTIONS_SUSPECTED, ExceptionProfile.KYC_EXPIRED]:
                queue = "Compliance"
            elif profile in [ExceptionProfile.DUPLICATE_PAYMENT, ExceptionProfile.RETURNED_PAYMENT]:
                queue = "Investigation"
            elif "FX" in exc_row.get("reason", ""):
                queue = "Treasury"

            severity = ExceptionSeverity.MEDIUM
            if amount >= 250000.0 or profile == ExceptionProfile.SANCTIONS_SUSPECTED:
                severity = ExceptionSeverity.HIGH
            if amount >= 1000000.0:
                severity = ExceptionSeverity.CRITICAL

            priority = ExceptionPriority.NORMAL
            if severity in [ExceptionSeverity.HIGH, ExceptionSeverity.CRITICAL]:
                priority = ExceptionPriority.HIGH
            if amount >= 1000000.0:
                priority = ExceptionPriority.CRITICAL

            # Calculate mock SLA due
            sla_due = datetime.utcnow() + timedelta(hours=2, minutes=15)

            debtor_id = pmt_row.get("debtor_party_id") or "PARTY-DEBTOR-01"
            creditor_id = pmt_row.get("creditor_party_id") or "PARTY-CREDITOR-01"
            
            debtor_party_row = self.parties.get(debtor_id, {"party_name": "Acme Global Holdings", "country": "US"})
            creditor_party_row = self.parties.get(creditor_id, {"party_name": "HarborView Supplier Ltd", "country": "GB"})

            # Check if this synthetic case is resolved in ground truth or active
            status = LifecycleStage.PENDING_APPROVAL
            if "RESOLVED" in exc_row.get("status", "").upper():
                status = LifecycleStage.SETTLED
            elif "ESCALATED" in exc_row.get("status", "").upper():
                status = LifecycleStage.ESCALATED
            elif "IN_PROGRESS" in exc_row.get("status", "").upper():
                status = LifecycleStage.INVESTIGATING

            case_obj = {
                "case_id": case_id,
                "payment_id": payment_id,
                "uetr": pmt_row.get("uetr") or f"UETR-{case_id}",
                "payment_ref": pmt_row.get("client_reference") or pmt_row.get("instruction_id") or f"REF-{case_id}",
                "profile": profile,
                "error_code": exc_row.get("error_code") or "ERR_IBAN_MOD97",
                "reason": exc_row.get("reason") or "Beneficiary IBAN failed MOD-97 check validation against clearing directory.",
                "amount": amount,
                "currency": currency,
                "payment_rail": pmt_row.get("payment_rail") or "SWIFT / CBPR+",
                "debtor_party": {
                    "party_id": debtor_id,
                    "party_name": debtor_party_row.get("party_name", "Acme Global Holdings"),
                    "country": debtor_party_row.get("country", "US"),
                    "party_type": "DEBTOR"
                },
                "debtor_account": {
                    "account_id": pmt_row.get("debtor_account_id", "ACC-US-001"),
                    "account_number": "1234567890",
                    "iban": "US89CHAS12345678901234",
                    "currency": currency,
                    "bank_bic": "CHASUS33"
                },
                "creditor_party": {
                    "party_id": creditor_id,
                    "party_name": creditor_party_row.get("party_name", "HarborView Supplier Ltd"),
                    "country": creditor_party_row.get("country", "GB"),
                    "party_type": "CREDITOR"
                },
                "creditor_account": {
                    "account_id": pmt_row.get("creditor_account_id", "ACC-GB-002"),
                    "account_number": "98765432",
                    "iban": pmt_row.get("creditor_iban") or "GB82WEST12345698765432",
                    "currency": currency,
                    "bank_bic": "WESTGB2L"
                },
                "queue": queue,
                "status": status,
                "severity": severity,
                "priority": priority,
                "sla_due_at": sla_due,
                "dual_auth_required": amount >= settings.DUAL_AUTH_THRESHOLD,
                "ai_confidence": 0.96 if profile == ExceptionProfile.INVALID_IBAN else 0.88,
                "created_at": datetime.utcnow() - timedelta(minutes=45),
                "approval_history": []
            }
            self.cases[case_id] = case_obj

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        return self.cases.get(case_id)

    def save_case(self, case_obj: Dict[str, Any]):
        self.cases[case_obj["case_id"]] = case_obj

    def list_cases(
        self,
        queue: Optional[str] = None,
        status: Optional[str] = None,
        profile: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = list(self.cases.values())
        if queue and queue != "All" and queue != "All Queues":
            results = [c for c in results if c.get("queue") == queue]
        if status and status != "All" and status != "All Statuses":
            results = [c for c in results if c.get("status") == status or c.get("status", "").value == status]
        if profile and profile != "All" and profile != "All Types":
            results = [c for c in results if str(c.get("profile")) == profile or c.get("profile", "").value == profile]
        if search:
            s = search.lower()
            results = [
                c for c in results if
                s in c.get("case_id", "").lower() or
                s in c.get("uetr", "").lower() or
                s in c.get("payment_ref", "").lower() or
                s in c.get("creditor_party", {}).get("party_name", "").lower() or
                s in c.get("debtor_party", {}).get("party_name", "").lower()
            ]
        # Sort by creation / priority
        results.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        return results

repo = InMemoryRepository()
"""

# Write services/data_loader.py
for rel_path, content in services.items():
    full_path = os.path.join(base_backend, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {rel_path}")
