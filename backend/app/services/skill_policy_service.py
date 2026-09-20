"""Dynamic Skill & Policy Service: Ingests SME-authored Skill Markdown files at runtime.

This service enables authorized SMEs to update validation playbooks, threshold rules,
and attribution formulas in Markdown without requiring backend code changes.
"""
import re
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

class SkillPolicyService:
    def __init__(self, skills_root_dir: Optional[Path] = None):
        if skills_root_dir is None:
            # Locate .agents/skills/payment-exception-resolution from workspace root
            curr = Path(__file__).resolve().parent
            skills_dir = None
            for p in [curr.parent.parent.parent, curr.parent.parent, curr.parent]:
                candidate = p / ".agents" / "skills" / "payment-exception-resolution"
                if candidate.exists():
                    skills_dir = candidate
                    break
            self.skills_dir = skills_dir or (curr.parent.parent.parent / ".agents" / "skills" / "payment-exception-resolution")
        else:
            self.skills_dir = Path(skills_root_dir)

    def load_active_skills(self) -> Dict[str, Any]:
        """Dynamically scans and parses all skill playbooks and extract policy parameters."""
        policies = {
            "loaded_at": datetime.utcnow().isoformat(),
            "skill_name": "payment-exception-resolution",
            "skills_path": str(self.skills_dir),
            "playbooks": {},
            "parameters": {
                "confidence_threshold": 0.85,
                "dual_auth_threshold": 250000.0,
                "duplicate_window_minutes": 30,
                "kyc_provisional_waiver_days": 30,
                "country_iban_lengths": {
                    "DE": 22, "GB": 22, "FR": 27, "IT": 27, "ES": 24, "NL": 18, "CH": 21
                },
                "attribution_weights": {
                    "pillar_1_mod97": 0.30,
                    "pillar_2_ssi": 0.25,
                    "pillar_3_velocity": 0.20,
                    "pillar_4_rail": 0.15,
                    "pillar_5_remittance": 0.06
                }
            }
        }

        if not self.skills_dir.exists():
            return policies

        # 1. Parse Main SKILL.md
        main_skill_file = self.skills_dir / "SKILL.md"
        if main_skill_file.exists():
            content = main_skill_file.read_text(encoding="utf-8")
            policies["main_skill"] = content
            # Extract confidence threshold if specified
            conf_match = re.search(r"Threshold for 1-Tier Approval:\s*\\ge\s*(\d+)%", content)
            if conf_match:
                policies["parameters"]["confidence_threshold"] = float(conf_match.group(1)) / 100.0

        # 2. Parse references/
        ref_dir = self.skills_dir / "references"
        if ref_dir.exists():
            for f in ref_dir.glob("*.md"):
                text = f.read_text(encoding="utf-8")
                policies["playbooks"][f.stem] = {
                    "filename": f.name,
                    "title": self._extract_title(text),
                    "content": text,
                    "last_modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                }

                # Dynamically extract country IBAN lengths if in iban_repair_playbook
                if "iban" in f.stem.lower():
                    lengths = re.findall(r"\*\*([A-Z]{2})\s*\([^)]*\)\*\*:\s*(\d+)\s*chars", text)
                    for code, length in lengths:
                        policies["parameters"]["country_iban_lengths"][code] = int(length)

                # Dynamically extract Dual Auth threshold if in kyc or dual auth playbook
                if "kyc" in f.stem.lower() or "dual" in f.stem.lower():
                    da_match = re.search(r"\\ge\s*\$([0-9,]+)", text)
                    if da_match:
                        try:
                            val = float(da_match.group(1).replace(",", ""))
                            policies["parameters"]["dual_auth_threshold"] = val
                        except ValueError:
                            pass

                # Dynamically extract duplicate burst window
                if "duplicate" in f.stem.lower():
                    dup_match = re.search(r"\\Delta t\s*\\le\s*(\d+)\\text{\s*minutes}", text)
                    if dup_match:
                        policies["parameters"]["duplicate_window_minutes"] = int(dup_match.group(1))

        return policies

    def get_playbook_for_exception(self, profile: str) -> Optional[Dict[str, Any]]:
        """Returns the specific SME playbook for a given exception type at runtime."""
        skills = self.load_active_skills()
        
        # Domain Mapping for all 41 Profiles
        dq_profiles = {"INVALID_IBAN", "INVALID_BIC", "MISSING_BENEFICIARY_DATA", "MISSING_REMITTANCE_INFO", "INVALID_ADDRESS_FORMAT", "MISSING_PURPOSE_CODE", "INVALID_ACCOUNT_NUMBER", "INVALID_ROUTING_CODE", "BENEFICIARY_NAME_MISMATCH"}
        proc_profiles = {"DUPLICATE_PAYMENT", "ROUTING_FAILURE", "ISO20022_VALIDATION_ERROR", "CUTOFF_MISSED", "CORRUPTED_MESSAGE_FORMAT", "INTERMEDIARY_BANK_REJECTION", "NETWORK_TIMEOUT", "QUEUE_PROCESSING_FAILURE", "PAYMENT_HELD_FOR_REPAIR"}
        comp_profiles = {"SANCTIONS_SUSPECTED", "AML_ALERT", "PEP_MATCH", "RESTRICTED_CORRIDOR", "ADVERSE_MEDIA_MATCH", "HIGH_RISK_JURISDICTION", "REGULATORY_REPORTING_REQUIRED", "CUSTOMER_WATCHLIST_MATCH"}
        trea_profiles = {"KYC_EXPIRED", "INSUFFICIENT_FUNDS", "NOSTRO_SHORTFALL", "FX_RATE_UNAVAILABLE", "AUTHORIZATION_MISSING", "LIMIT_BREACH", "LIQUIDITY_CONSTRAINT", "CREDIT_EXPOSURE_BREACH"}
        sett_profiles = {"RETURNED_PAYMENT", "ACCOUNT_CLOSED", "BENEFICIARY_ACCOUNT_FROZEN", "RECONCILIATION_BREAK", "SETTLEMENT_FAILURE", "FUNDS_TRAPPED_AT_CORRESPONDENT", "UNMATCHED_CREDIT"}

        if profile in dq_profiles:
            playbook_key = "data_quality_domain_playbook"
        elif profile in proc_profiles:
            playbook_key = "processing_domain_playbook"
        elif profile in comp_profiles:
            playbook_key = "compliance_domain_playbook"
        elif profile in trea_profiles:
            playbook_key = "client_treasury_domain_playbook"
        elif profile in sett_profiles:
            playbook_key = "settlement_returns_domain_playbook"
        else:
            playbook_key = "data_quality_domain_playbook"

        if playbook_key in skills["playbooks"]:
            return skills["playbooks"][playbook_key]
        return None

    def get_policy_parameters(self) -> Dict[str, Any]:
        """Returns active runtime policy parameters derived directly from SME markdown skills."""
        return self.load_active_skills()["parameters"]

    def _extract_title(self, markdown_text: str) -> str:
        first_line = markdown_text.strip().split("\n")[0]
        return first_line.replace("#", "").strip()

skill_policy_service = SkillPolicyService()
