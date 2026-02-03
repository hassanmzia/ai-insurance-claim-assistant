"""
Decision Maker Agent - Produces final claim decisions.
Mirrors finalize_decision tool from the notebook.
"""
import logging
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ClaimDecision(BaseModel):
    """Final claim decision."""
    claim_number: str
    covered: bool
    deductible: float = 0.0
    recommended_payout: float = 0.0
    notes: Optional[str] = None
    decision_factors: list = []


class DecisionMakerAgent:
    """Makes final claim decisions based on recommendations and fraud analysis."""

    agent_id = "decision_maker"
    agent_name = "Decision Maker Agent"
    description = "Produces final claim decisions based on recommendations and fraud analysis"

    def decide(self, claim_info: Dict, recommendation: Dict, fraud_result: Dict = None) -> Dict[str, Any]:
        """Produce a final claim decision."""
        logger.info(f"[DecisionMakerAgent] Deciding on claim {claim_info.get('claim_number')}")

        fraud_score = fraud_result.get('fraud_score', 0) if fraud_result else 0
        decision_factors = []

        # Extract recommendation details
        rec_summary = recommendation.get('recommendation_summary', '')
        deductible = recommendation.get('deductible') or 0.0
        settlement = recommendation.get('settlement_amount') or 0.0
        policy_section = recommendation.get('policy_section', 'General')

        # Determine coverage
        covered = True
        notes_parts = []

        # Check if recommendation indicates denial
        denial_keywords = ['denied', 'excluded', 'not covered', 'exclusion', 'ineligible']
        if any(kw in rec_summary.lower() for kw in denial_keywords):
            covered = False
            decision_factors.append('Recommendation indicates exclusion or denial')
            notes_parts.append(f"Denied based on {policy_section}.")

        # Fraud check
        if fraud_score > 0.7:
            covered = False
            decision_factors.append(f'High fraud score: {fraud_score:.2f}')
            notes_parts.append("Claim flagged for investigation due to high fraud risk.")
        elif fraud_score > 0.3:
            decision_factors.append(f'Moderate fraud score: {fraud_score:.2f} - manual review advised')
            notes_parts.append("Moderate fraud indicators detected. Review recommended.")

        if covered:
            decision_factors.append(f'Coverage confirmed under {policy_section}')
            cost = claim_info.get('estimated_repair_cost', 0)
            if settlement <= 0:
                settlement = max(0, cost - deductible)
            notes_parts.append(rec_summary if rec_summary else f"Claim covered under {policy_section}.")

        decision = ClaimDecision(
            claim_number=claim_info.get('claim_number', ''),
            covered=covered,
            deductible=deductible if covered else 0,
            recommended_payout=settlement if covered else 0,
            notes=' '.join(notes_parts),
            decision_factors=decision_factors,
        )

        logger.info(f"[DecisionMakerAgent] Decision: covered={covered}, payout={settlement}")
        return decision.model_dump()
