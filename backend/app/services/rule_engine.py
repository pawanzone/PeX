"""Dynamic Governed Business Rule & Policy Engine for PeX Enterprise Platform.

Translates natural language governance statements into executable JSON ASTs,
simulates policy impact on live database cases, and executes rules dynamically
with zero code changes and zero downtime.
"""
import re
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from app.schemas.rules import (
    RuleCategory,
    RuleStatus,
    SynthesizeRuleResponse,
    SimulateRuleResponse,
    MatchedCaseSample,
)

# Standard country aliases for sanctions & routing
COUNTRY_ALIASES = {
    "CUBA": "CU", "CU": "CU",
    "IRAN": "IR", "IR": "IR",
    "SYRIA": "SY", "SY": "SY",
    "NORTH KOREA": "KP", "KP": "KP", "DPRK": "KP",
    "RUSSIA": "RU", "RU": "RU",
    "UNITED STATES": "US", "USA": "US", "US": "US",
    "UNITED KINGDOM": "GB", "UK": "GB", "GB": "GB",
    "GERMANY": "DE", "DE": "DE",
    "FRANCE": "FR", "FR": "FR",
    "JAPAN": "JP", "JP": "JP",
}

class DynamicRuleEngine:
    """Evaluates, synthesizes, and simulates business rules dynamically."""

    def parse_numeric_amount(self, text: str) -> Optional[float]:
        """Extracts numeric monetary amounts from text (e.g. '$250,000', '€1.5M', '100k', '50000')."""
        # Match pattern with currency and optional k/m multipliers
        match = re.search(r'[\$€£¥]?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*([kKmMbB]|million|thousand)?', text)
        if match:
            raw_num_str = match.group(1).replace(",", "")
            multiplier_str = (match.group(2) or "").lower()
            try:
                base_num = float(raw_num_str)
                if multiplier_str in ["k", "thousand"]:
                    return base_num * 1000.0
                elif multiplier_str in ["m", "million"]:
                    return base_num * 1000000.0
                elif multiplier_str in ["b", "billion"]:
                    return base_num * 1000000000.0
                return base_num
            except ValueError:
                return None
        return None

    def parse_confidence_percentage(self, text: str) -> Optional[float]:
        """Extracts confidence score from text (e.g. '>95%', '>= 90%', '0.95', '95 percent')."""
        match = re.search(r'([0-9]{1,3}(?:\.[0-9]+)?)\s*(?:%|percent)', text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                return round(val / 100.0, 4) if val > 1.0 else round(val, 4)
            except ValueError:
                pass
        match_dec = re.search(r'confidence\s*(?:>=|>|above|over|of)?\s*(0\.[0-9]+)', text, re.IGNORECASE)
        if match_dec:
            try:
                return float(match_dec.group(1))
            except ValueError:
                pass
        return None

    def synthesize_rule(
        self,
        prompt: str,
        category_hint: Optional[str] = None,
        domain_hint: Optional[str] = None
    ) -> SynthesizeRuleResponse:
        """Translates a natural language governance statement into an executable JSON AST."""
        p_lower = prompt.lower()
        
        # 1. Determine Category
        category = category_hint or RuleCategory.APPROVAL_GATING.value
        if any(w in p_lower for w in ["fast-lane", "fast lane", "stp", "auto qualify", "auto-qualify", "1-click", "one-click", "auto approve", "micro repair", "straight through"]):
            category = RuleCategory.STP_FAST_LANE.value
        elif any(w in p_lower for w in ["route", "routing", "send to", "assign to", "queue", "desk", "sanction"]):
            category = RuleCategory.ROUTING.value
        elif any(w in p_lower for w in ["sla", "urgency", "escalate", "priority", "critical", "hours"]):
            category = RuleCategory.SLA_URGENCY.value
        elif any(w in p_lower for w in ["approval", "dual", "2-level", "two-level", "tier", "authorize", "authorisation"]):
            category = RuleCategory.APPROVAL_GATING.value

        # 2. Determine Domain
        domain = domain_hint or "ALL"
        if "sanction" in p_lower or "ofac" in p_lower or "aml" in p_lower or "pep" in p_lower:
            domain = "SANCTIONS_AML"
        elif "iban" in p_lower or "syntax" in p_lower or "format" in p_lower or "bic" in p_lower or "character" in p_lower:
            domain = "FORMAT_SYNTAX"
        elif "treasury" in p_lower or "liquidity" in p_lower or "cutoff" in p_lower:
            domain = "CLIENT_TREASURY"
        elif "directory" in p_lower or "account" in p_lower or "dormant" in p_lower:
            domain = "ACCOUNT_DIRECTORY"
        elif "settlement" in p_lower or "return" in p_lower or "recall" in p_lower:
            domain = "SETTLEMENT_RETURNS"

        clauses: List[Dict[str, Any]] = []
        actions: Dict[str, Any] = {}
        explanation_parts: List[str] = []

        # 3. Extract Amount Clauses
        amt = self.parse_numeric_amount(prompt)
        if amt is not None:
            if any(w in p_lower for w in ["more than", "greater than", "over", "above", ">=", ">", "exceeding", "at least"]):
                clauses.append({"field": "amount", "operator": ">=", "value": amt})
                explanation_parts.append(f"Payment amount is at least ${amt:,.2f}")
            elif any(w in p_lower for w in ["less than", "under", "below", "<=", "<", "at most"]):
                clauses.append({"field": "amount", "operator": "<=", "value": amt})
                explanation_parts.append(f"Payment amount is under or equal to ${amt:,.2f}")
            else:
                clauses.append({"field": "amount", "operator": ">=", "value": amt})
                explanation_parts.append(f"Payment amount meets threshold of ${amt:,.2f}")

        # 4. Extract Confidence Clauses
        conf = self.parse_confidence_percentage(prompt)
        if conf is not None:
            clauses.append({"field": "confidence", "operator": ">=", "value": conf})
            explanation_parts.append(f"AI decision confidence is at least {int(conf*100)}%")

        # 5. Extract Currency Clauses
        for ccy in ["EUR", "USD", "GBP", "JPY", "CHF", "CAD", "AUD"]:
            if re.search(r'\b' + ccy + r'\b', prompt, re.IGNORECASE) or (ccy == "EUR" and "€" in prompt) or (ccy == "GBP" and "£" in prompt) or (ccy == "USD" and "$" in prompt and "eur" not in p_lower and "gbp" not in p_lower):
                if ccy in ["EUR", "GBP", "JPY", "CHF"] or (ccy == "USD" and "usd" in p_lower):
                    clauses.append({"field": "currency", "operator": "==", "value": ccy})
                    explanation_parts.append(f"Currency is {ccy}")
                    break

        # 6. Extract Country / Sanctions Clauses
        found_countries = []
        for alias, code in COUNTRY_ALIASES.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', prompt, re.IGNORECASE):
                if code not in found_countries:
                    found_countries.append(code)
        if found_countries:
            if len(found_countries) == 1:
                clauses.append({"field": "creditor_country", "operator": "==", "value": found_countries[0]})
                explanation_parts.append(f"Beneficiary country is {found_countries[0]}")
            else:
                clauses.append({"field": "creditor_country", "operator": "in", "value": found_countries})
                explanation_parts.append(f"Beneficiary country in [{', '.join(found_countries)}]")

        # 7. Extract Profile / Exception Type Clauses
        for prof in ["INVALID_IBAN", "SANCTION_HIT", "DUPLICATE_PAYMENT", "CUTOFF_EXCEEDED", "BENEFICIARY_NAME_MISMATCH", "INSUFFICIENT_FUNDS"]:
            if prof.lower() in p_lower or prof.replace("_", " ").lower() in p_lower:
                clauses.append({"field": "profile", "operator": "==", "value": prof})
                explanation_parts.append(f"Exception profile is {prof}")
                break

        # 8. Build Actions based on Category and Context
        if category == RuleCategory.APPROVAL_GATING.value:
            actions["set_dual_auth_required"] = True
            actions["required_tiers"] = 2
            actions["tier_1_role"] = "OPERATIONS_APPROVER"
            actions["tier_2_role"] = "RISK_APPROVER"
            explanation_parts.append("Mandate 2-Level Maker-Checker Dual Authorization (Operations Approver + Risk Approver sign-offs)")
        elif category == RuleCategory.STP_FAST_LANE.value:
            actions["auto_qualify_fast_lane"] = True
            actions["one_click_eligible"] = True
            actions["target_queue"] = "Repair"
            explanation_parts.append("Qualify case for 1-Click Fast-Lane STP processing")
        elif category == RuleCategory.ROUTING.value:
            target_q = "Treasury"
            if "compliance" in p_lower or "sanction" in p_lower:
                target_q = "Compliance"
            elif "investigation" in p_lower:
                target_q = "Investigation"
            elif "repair" in p_lower:
                target_q = "Repair"
            actions["target_queue"] = target_q
            actions["override_priority"] = "HIGH"
            explanation_parts.append(f"Route matching exceptions directly to the {target_q} Desk with High priority")
        elif category == RuleCategory.SLA_URGENCY.value:
            actions["override_priority"] = "CRITICAL"
            explanation_parts.append("Escalate case priority to CRITICAL with real-time operator alerts")

        # Fallback if no clauses matched
        if not clauses:
            clauses.append({"field": "amount", "operator": ">=", "value": 250000.0})
            explanation_parts.append("Default fallback threshold: amount >= $250,000.00")

        # Generate Rule Name and ID
        rule_slug = category.replace("_", "-").lower()
        unique_suffix = uuid.uuid4().hex[:4].upper()
        rule_id = f"RULE-{rule_slug.upper()}-{unique_suffix}"
        
        # Build Name
        if amt:
            name = f"{category.replace('_', ' ').title()} (${amt:,.0f}+)"
        elif found_countries:
            name = f"{category.replace('_', ' ').title()} ({', '.join(found_countries)})"
        else:
            name = f"{category.replace('_', ' ').title()} Policy {unique_suffix}"

        return SynthesizeRuleResponse(
            rule_id=rule_id,
            name=name,
            natural_language_prompt=prompt,
            category=category,
            domain=domain,
            conditions={"logic": "AND", "clauses": clauses},
            actions=actions,
            explanation="; ".join(explanation_parts) + "."
        )

    def evaluate_clause(self, clause: Dict[str, Any], case: Dict[str, Any]) -> bool:
        """Evaluates a single rule clause against a case dictionary."""
        field = clause.get("field", "")
        op = clause.get("operator", "==")
        expected = clause.get("value")

        # Resolve field value from case
        actual = None
        if field == "amount":
            actual = float(case.get("amount", 0.0))
        elif field in ["confidence", "ai_confidence"]:
            actual = float(case.get("ai_confidence") or case.get("confidence") or 0.0)
        elif field == "currency":
            actual = str(case.get("currency", "")).upper()
        elif field == "domain":
            actual = str(case.get("domain", "")).upper()
        elif field == "profile":
            actual = str(case.get("profile", "")).upper()
        elif field == "error_code":
            actual = str(case.get("error_code", "")).upper()
        elif field == "creditor_country":
            cp = case.get("creditor_party") or {}
            actual = str(cp.get("country") or case.get("creditor_country", "")).upper()
        elif field == "debtor_country":
            dp = case.get("debtor_party") or {}
            actual = str(dp.get("country") or case.get("debtor_country", "")).upper()
        elif field == "queue":
            actual = str(case.get("queue", "")).upper()
        elif field == "severity":
            actual = str(case.get("severity", "")).upper()
        elif field == "priority":
            actual = str(case.get("priority", "")).upper()
        elif field == "payment_rail":
            actual = str(case.get("payment_rail", "")).upper()
        else:
            actual = case.get(field)

        if actual is None:
            return False

        # Execute Comparison
        try:
            if op == ">=":
                return float(actual) >= float(expected)
            elif op == "<=":
                return float(actual) <= float(expected)
            elif op == ">":
                return float(actual) > float(expected)
            elif op == "<":
                return float(actual) < float(expected)
            elif op in ["==", "="]:
                if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                    return float(actual) == float(expected)
                return str(actual).strip().upper() == str(expected).strip().upper()
            elif op in ["!=", "<>"]:
                return str(actual).strip().upper() != str(expected).strip().upper()
            elif op == "in":
                if isinstance(expected, list):
                    exp_norm = [str(x).strip().upper() for x in expected]
                    return str(actual).strip().upper() in exp_norm
                return str(actual).strip().upper() in str(expected).strip().upper()
            elif op == "contains":
                return str(expected).strip().lower() in str(actual).strip().lower()
        except Exception:
            return False

        return False

    def evaluate_rule(self, rule_dict: Dict[str, Any], case: Dict[str, Any]) -> bool:
        """Evaluates whether a case matches the rule's conditions and domain scope."""
        rule_domain = rule_dict.get("domain", "ALL")
        case_domain = case.get("domain", "")
        if rule_domain != "ALL" and str(rule_domain).upper() != str(case_domain).upper():
            return False

        conditions = rule_dict.get("conditions", {})
        clauses = conditions.get("clauses", [])
        if not clauses:
            return True

        logic = conditions.get("logic", "AND").upper()
        if logic == "AND":
            for c in clauses:
                if not self.evaluate_clause(c, case):
                    return False
            return True
        elif logic == "OR":
            for c in clauses:
                if self.evaluate_clause(c, case):
                    return True
            return False
        return False

    def simulate_impact(
        self,
        rule_dict: Dict[str, Any],
        cases: List[Dict[str, Any]]
    ) -> SimulateRuleResponse:
        """Simulates rule impact across benchmark or live cases."""
        total_cases = len(cases)
        matched_cases: List[Dict[str, Any]] = []
        matched_by_domain: Dict[str, int] = {}
        matched_by_queue: Dict[str, int] = {}
        total_dollar_vol = 0.0

        for case in cases:
            if self.evaluate_rule(rule_dict, case):
                matched_cases.append(case)
                amt = float(case.get("amount", 0.0))
                total_dollar_vol += amt
                
                dom = str(case.get("domain", "OTHER"))
                matched_by_domain[dom] = matched_by_domain.get(dom, 0) + 1
                
                q = str(case.get("queue", "OTHER"))
                matched_by_queue[q] = matched_by_queue.get(q, 0) + 1

        match_count = len(matched_cases)
        match_pct = round((match_count / total_cases * 100.0), 1) if total_cases > 0 else 0.0

        sample_cases: List[MatchedCaseSample] = []
        for c in matched_cases[:5]:
            sample_cases.append(
                MatchedCaseSample(
                    case_id=c.get("case_id", ""),
                    payment_id=c.get("payment_id", ""),
                    amount=float(c.get("amount", 0.0)),
                    currency=c.get("currency", "USD"),
                    profile=c.get("profile", ""),
                    domain=c.get("domain", ""),
                    reason=c.get("reason", ""),
                    queue=c.get("queue", ""),
                    confidence=c.get("ai_confidence")
                )
            )

        return SimulateRuleResponse(
            total_cases_evaluated=total_cases,
            matched_cases_count=match_count,
            match_percentage=match_pct,
            total_dollar_volume_affected=round(total_dollar_vol, 2),
            matched_by_domain=matched_by_domain,
            matched_by_queue=matched_by_queue,
            sample_matched_cases=sample_cases,
            action_preview=rule_dict.get("actions", {})
        )

    def evaluate_case_policies(
        self,
        case: Dict[str, Any],
        active_rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluates all active DB rules for a live case and returns effective runtime policies."""
        dual_auth_required = False
        required_tiers = 1
        tier_roles = ["OPERATIONS_APPROVER"]
        fast_lane_eligible = False
        one_click_eligible = False
        target_queue = None
        override_priority = None
        applied_rules: List[Dict[str, Any]] = []

        amount = float(case.get("amount", 0.0))

        # Check all active rules
        for rule in active_rules:
            if rule.get("status") != "ACTIVE":
                continue
            if self.evaluate_rule(rule, case):
                applied_rules.append({
                    "rule_id": rule.get("rule_id"),
                    "name": rule.get("name"),
                    "category": rule.get("category"),
                    "version": rule.get("version", "1.0")
                })
                actions = rule.get("actions", {})
                if actions.get("set_dual_auth_required"):
                    dual_auth_required = True
                    required_tiers = max(required_tiers, actions.get("required_tiers", 2))
                    tier_roles = [actions.get("tier_1_role", "OPERATIONS_APPROVER"), actions.get("tier_2_role", "RISK_APPROVER")]
                if actions.get("auto_qualify_fast_lane"):
                    fast_lane_eligible = True
                if actions.get("one_click_eligible"):
                    one_click_eligible = True
                if actions.get("target_queue"):
                    target_queue = actions.get("target_queue")
                if actions.get("override_priority"):
                    override_priority = actions.get("override_priority")

        # Fallback to default $250k threshold if no rule specified dual auth but amount is high
        if amount >= 250000.0 and not dual_auth_required:
            dual_auth_required = True
            required_tiers = 2
            tier_roles = ["OPERATIONS_APPROVER", "RISK_APPROVER"]

        return {
            "dual_auth_required": dual_auth_required,
            "required_tiers": required_tiers,
            "tier_roles": tier_roles,
            "fast_lane_eligible": fast_lane_eligible,
            "one_click_eligible": one_click_eligible,
            "target_queue": target_queue,
            "override_priority": override_priority,
            "applied_rules": applied_rules
        }

# Global singleton
rule_engine = DynamicRuleEngine()
