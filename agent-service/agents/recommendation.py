"""
Recommendation Agent - Evaluates claims against policy text.
Mirrors generate_recommendation tool from the notebook.
"""
import json
import logging
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PolicyRecommendation(BaseModel):
    """Policy recommendation regarding a given claim."""
    policy_section: str = Field(default="General Coverage")
    recommendation_summary: str = Field(default="")
    deductible: Optional[float] = None
    settlement_amount: Optional[float] = None


class RecommendationAgent:
    """Evaluates claims against policy text to produce recommendations."""

    agent_id = "recommendation"
    agent_name = "Recommendation Agent"
    description = "Evaluates claims against retrieved policy text to produce coverage recommendations"

    def recommend(self, claim_info: Dict[str, Any], policy_text: str) -> Dict[str, Any]:
        """Generate a recommendation based on claim info and policy text."""
        logger.info(f"[RecommendationAgent] Evaluating claim {claim_info.get('claim_number')}")

        try:
            from openai import OpenAI
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                return self._fallback_recommendation(claim_info, policy_text)

            client = OpenAI(api_key=api_key)
            prompt = f"""Evaluate the following auto insurance claim against the policy text:
- Determine if the collision is covered, the deductible, settlement amount, and applicable policy section.
- Claim Info: {json.dumps(claim_info)}
- Policy Text: {policy_text[:4000]}
- Return a JSON object:
  {{
    "policy_section": "str",
    "recommendation_summary": "str",
    "deductible": float or null,
    "settlement_amount": float or null
  }}"""

            response = client.chat.completions.create(
                model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=500,
            )

            result = json.loads(response.choices[0].message.content)
            rec = PolicyRecommendation.model_validate(result)
            logger.info(f"[RecommendationAgent] Recommendation: {rec.recommendation_summary[:100]}")
            return rec.model_dump()

        except Exception as e:
            logger.warning(f"[RecommendationAgent] LLM fallback: {e}")
            return self._fallback_recommendation(claim_info, policy_text)

    def _fallback_recommendation(self, claim_info: Dict, policy_text: str) -> Dict[str, Any]:
        """Rule-based fallback when LLM is unavailable."""
        cost = claim_info.get('estimated_repair_cost', 0)
        loss_type = claim_info.get('loss_type', 'collision')

        section_map = {
            'collision': 'Part D - Collision Coverage',
            'comprehensive': 'Part E - Comprehensive Coverage',
            'liability': 'Part A - Liability Coverage',
            'personal_injury': 'Part B - Medical Payments Coverage',
            'property_damage': 'Part A - Liability Coverage',
            'theft': 'Part E - Comprehensive Coverage',
            'vandalism': 'Part E - Comprehensive Coverage',
            'weather': 'Part E - Comprehensive Coverage',
        }

        deductible = 500.0
        settlement = max(0, cost - deductible)

        return PolicyRecommendation(
            policy_section=section_map.get(loss_type, 'General Coverage'),
            recommendation_summary=f"Claim appears covered under {section_map.get(loss_type, 'standard policy')}. "
                                    f"Estimated repair cost: ${cost:.2f}. Standard deductible of ${deductible:.2f} applies. "
                                    f"Recommended settlement: ${settlement:.2f}.",
            deductible=deductible,
            settlement_amount=settlement,
        ).model_dump()
