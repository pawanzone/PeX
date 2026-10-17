"""Model Gateway: Pluggable AI Reasoning layer with Deterministic Mock & Live Provider capabilities."""
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import settings
from app.schemas.context import TokenizedInvestigationContext
from app.schemas.recommendation import (
    DecisionRecommendation, ActionType, ProposedFieldChange,
    CorroboratingEvidenceRef, RiskEvaluation, GuidedQuestionItem,
    StepAssessmentItem, HypothesisRankingItem, AnomalyGuardrailItem, ConsequenceSimulation
)
from app.schemas.canonical import ExceptionSeverity
from app.core.tokenization import token_vault
from app.schemas.recommendation import ConsequenceSimulation as _ConsequenceSimulation
from app.services.llm_provider import (
    llm_provider, LLMStatus, LLMResult, PROMPT_VERSION, build_candidates, _tail,
)

class ModelGateway:
    def _evaluate_deterministic(
        self,
        context: TokenizedInvestigationContext,
        scenario_key: Optional[str] = None
    ) -> DecisionRecommendation:
        case_id = context.case_id
        profile = context.profile
        amount = context.tokenized_payment.amount

        if scenario_key == "IBAN-ESCALATE-001":
            return DecisionRecommendation(
                recommendation_id=f"REC-{case_id}",
                case_id=case_id,
                action_type=ActionType.ESCALATE,
                confidence_score=0.45,
                rationale="Conflicting and ambiguous evidence detected. Auto-repair blocked; escalated to Senior Operations Lead.",
                proposed_changes=[],
                corroborating_evidence=[],
                risk_evaluation=RiskEvaluation(
                    risk_level=ExceptionSeverity.HIGH,
                    risk_score=0.75,
                    risk_factors=["Ambiguous directory records", "Conflicting IBAN records"],
                    dual_auth_required=False
                ),
                guided_questions=[],
                step_by_step_assessment=[],
                hypothesis_ranking=[],
                anomaly_guardrails=[],
                consequence_simulation=None,
                applied_policies=[],
                model_identifier="apex-reasoner-deterministic-v1",
                prompt_tokens=120,
                completion_tokens=45,
                generated_at=datetime.utcnow()
            )

        if scenario_key == "IBAN-MISSING-EVIDENCE-001":
            return DecisionRecommendation(
                recommendation_id=f"REC-{case_id}",
                case_id=case_id,
                action_type=ActionType.INSUFFICIENT_EVIDENCE,
                confidence_score=0.20,
                rationale="Missing mandatory beneficiary account directory evidence.",
                proposed_changes=[],
                corroborating_evidence=[],
                risk_evaluation=RiskEvaluation(
                    risk_level=ExceptionSeverity.HIGH,
                    risk_score=0.85,
                    risk_factors=["Missing mandatory evidence", "Beneficiary directory unresolvable"],
                    dual_auth_required=False
                ),
                guided_questions=[],
                step_by_step_assessment=[],
                hypothesis_ranking=[],
                anomaly_guardrails=[],
                consequence_simulation=None,
                applied_policies=[],
                model_identifier="apex-reasoner-deterministic-v1",
                prompt_tokens=120,
                completion_tokens=45,
                generated_at=datetime.utcnow()
            )

        # Import repository to reuse rich definitions if present
        from app.services.data_loader import repo, build_rich_guided_recommendation
        
        if case_id in repo.recommendations:
            return repo.recommendations[case_id]

        creditor_name = "Nordhavn Components A/S"
        creditor_country = "GB"
        case_obj = repo.get_case(case_id)
        if case_obj:
            creditor_name = case_obj.get("creditor_party", {}).get("party_name", "Nordhavn Components A/S")
            creditor_country = case_obj.get("creditor_party", {}).get("country", "GB")

        return build_rich_guided_recommendation(
            case_id=case_id,
            profile=profile,
            amount=amount,
            creditor_name=creditor_name,
            creditor_country=creditor_country,
            case_idx=1
        )

    # ------------------------------------------------------------------------------------
    # Advisory LLM layer. Deterministic output is authoritative; the model can only add
    # narrative (rationale, hypotheses with evidence refs, questions, consequence summary).
    # ------------------------------------------------------------------------------------
    def evaluate_investigation(
        self,
        context: TokenizedInvestigationContext,
        scenario_key: Optional[str] = None
    ) -> DecisionRecommendation:
        rec = self._evaluate_deterministic(context, scenario_key)
        if scenario_key or not settings.LLM_ENABLED:
            return rec                      # canned scenarios / disabled: deterministic output unchanged
        if rec.llm_status == LLMStatus.OK.value:
            return rec                      # already advised once
        enriched = self._enrich(context, rec)
        try:
            from app.services.data_loader import repo
            repo.recommendations[context.case_id] = enriched
        except Exception:
            pass
        return enriched

    @staticmethod
    def _annotate_hypothesis_sources(rec: DecisionRecommendation) -> None:
        for h in rec.hypothesis_ranking:
            if h.source is None:
                h.source = "SIMULATED" if "[SIMULATED]" in (h.title or "") else "DETERMINISTIC"

    def _enrich(self, context: TokenizedInvestigationContext, rec: DecisionRecommendation) -> DecisionRecommendation:
        out = rec.model_copy(deep=True)
        try:
            res = llm_provider.advise(context, rec)
        except Exception as e:  # defensive: the provider should never raise
            res = LLMResult(status=LLMStatus.INVALID_OUTPUT, error=f"provider error: {type(e).__name__}")

        out.llm_status = res.status.value
        out.prompt_version = res.prompt_version
        out.latency_ms = res.latency_ms
        flags: list = []
        disagreement = False

        if res.status == LLMStatus.OK and res.advisory is not None:
            out.model_version = res.model_version
            out.prompt_tokens = res.prompt_tokens
            out.completion_tokens = res.completion_tokens
            adv = res.advisory
            valid_ids = {e.evidence_id for e in context.evidence_items}

            # 1) Candidate check: the model may only confirm a deterministic candidate, never invent one.
            cands = build_candidates(rec)
            cand_ids = {c["candidate_id"] for c in cands}
            cand_tails = {c["proposed_tail"] for c in cands}
            if adv.selected_candidate_id is not None and adv.selected_candidate_id not in cand_ids:
                disagreement = True
            if adv.proposed_value_hint:
                if not cands or _tail(adv.proposed_value_hint) not in cand_tails:
                    disagreement = True

            if disagreement:
                out.llm_disagreement = True
                flags.append("llm_disagreement:candidate_mismatch")
                self._annotate_hypothesis_sources(out)  # advisory discarded entirely
            else:
                # 2) Evidence references must exist; unknown ones are dropped and flagged.
                unknown = set(adv.cited_evidence_ids) - valid_ids
                hyps = []
                for i, h in enumerate(adv.hypotheses, start=1):
                    refs = [r for r in h.evidence_ids if r in valid_ids]
                    unknown |= set(h.evidence_ids) - valid_ids
                    hyps.append(HypothesisRankingItem(
                        hypothesis_id=f"HYP-{i}", title=h.title, confidence=h.confidence,
                        status=h.status, elimination_reason=h.elimination_reason,
                        source="LLM_ESTIMATE", evidence_ids=refs,
                    ))
                if unknown:
                    flags.append("llm_unknown_evidence_ref:" + ",".join(sorted(unknown))[:120])
                seen_selected = False
                for h in hyps:
                    if h.status == "SELECTED":
                        if seen_selected:
                            h.status = "ELIGIBLE_CANDIDATE"
                        seen_selected = True

                out.deterministic_rationale = rec.rationale
                out.rationale = adv.rationale
                if hyps:
                    out.hypothesis_ranking = hyps
                else:
                    self._annotate_hypothesis_sources(out)
                if adv.guided_questions:
                    out.guided_questions = [GuidedQuestionItem(
                        category=q.category, question=q.question,
                        investigation_tip=q.investigation_tip or "Verify against source system of record.",
                    ) for q in adv.guided_questions]
                if adv.consequence_summary:
                    if out.consequence_simulation is None:
                        out.consequence_simulation = _ConsequenceSimulation(
                            estimated_settlement_velocity="n/a", cutoff_deadline_status="n/a",
                            fee_penalty_avoidance="n/a", nostro_liquidity_impact="n/a",
                        )
                    out.consequence_simulation.narrative = adv.consequence_summary
        else:
            flags.append(f"llm_{res.status.value.lower()}")
            self._annotate_hypothesis_sources(out)

        out.llm_flags = flags
        self._audit(context, out, res, disagreement, flags)
        return out

    @staticmethod
    def _audit(context, rec, res, disagreement, flags) -> None:
        """Audit-visible record of the advisory call (never raises)."""
        try:
            from app.services.data_loader import repo
            tags = ["Advisory only", f"LLM:{res.status.value}"]
            if disagreement:
                tags.append("LLM_DISAGREEMENT")
            repo.log_audit_event(
                case_id=context.case_id,
                correlation_id=getattr(context.tokenized_payment, "uetr", None) or context.case_id,
                stage_name="AI_ADVISORY",
                actor_id=res.model_version or "llm-advisor",
                actor_role="LLM_ADVISOR",
                action_name=f"LLM_ADVISORY_{res.status.value}",
                details=(
                    f"status={res.status.value} model_version={res.model_version} prompt_version={res.prompt_version} "
                    f"prompt_tokens={res.prompt_tokens} completion_tokens={res.completion_tokens} "
                    f"latency_ms={res.latency_ms} disagreement={disagreement} flags={flags} "
                    f"(advisory only; deterministic gates unchanged)"
                ),
                control_tags=tags,
            )
        except Exception:
            pass

model_gateway = ModelGateway()
