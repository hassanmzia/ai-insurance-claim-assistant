"""
Fraud Detection Agent - Analyzes claims for potential fraud indicators.
Enhanced feature beyond the notebook for professional-grade application.
"""
import logging
import os
import json
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class FraudDetectorAgent:
    """Analyzes insurance claims for potential fraud."""

    agent_id = "fraud_detector"
    agent_name = "Fraud Detection Agent"
    description = "Analyzes claims for potential fraud indicators using rule-based and AI-powered detection"

    # Known fraud indicators with weights
    INDICATORS = {
        'high_cost_ratio': {
            'description': 'Estimated repair cost exceeds typical range',
            'weight': 0.15,
        },
        'recent_policy': {
            'description': 'Claim filed shortly after policy inception',
            'weight': 0.10,
        },
        'frequency': {
            'description': 'Multiple claims in short period',
            'weight': 0.20,
        },
        'vague_description': {
            'description': 'Loss description lacks specific details',
            'weight': 0.12,
        },
        'no_police_report': {
            'description': 'No police report for significant damage',
            'weight': 0.08,
        },
        'suspicious_timing': {
            'description': 'Claim filed on weekend/holiday or at unusual hours',
            'weight': 0.05,
        },
        'mismatched_damage': {
            'description': 'Damage description inconsistent with loss type',
            'weight': 0.15,
        },
        'high_value_vehicle': {
            'description': 'Claim on recently acquired high-value vehicle',
            'weight': 0.10,
        },
        'total_loss_new_vehicle': {
            'description': 'Total loss claim on relatively new vehicle',
            'weight': 0.15,
        },
    }

    def analyze(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a claim for fraud indicators."""
        logger.info(f"[FraudDetectorAgent] Analyzing claim {claim_data.get('claim_number')}")

        flags = []
        score = 0.0

        cost = float(claim_data.get('estimated_repair_cost', 0))
        description = claim_data.get('loss_description', '')
        loss_type = claim_data.get('loss_type', '')

        # Rule-based checks
        if cost > 10000:
            flags.append({
                'indicator': 'high_cost_ratio',
                'description': f'High repair cost: ${cost:.2f}',
                'severity': 'medium',
            })
            score += self.INDICATORS['high_cost_ratio']['weight']

        if len(description.split()) < 10:
            flags.append({
                'indicator': 'vague_description',
                'description': 'Loss description is unusually brief',
                'severity': 'low',
            })
            score += self.INDICATORS['vague_description']['weight']

        if cost > 5000 and not claim_data.get('police_report_number'):
            flags.append({
                'indicator': 'no_police_report',
                'description': 'No police report for high-value claim',
                'severity': 'medium',
            })
            score += self.INDICATORS['no_police_report']['weight']

        # Check for damage/loss type mismatch
        mismatch_keywords = {
            'theft': ['stolen', 'theft', 'break-in', 'missing'],
            'collision': ['hit', 'crash', 'rear-end', 'collide', 'accident', 'struck'],
            'weather': ['storm', 'hail', 'flood', 'wind', 'tornado', 'hurricane'],
            'vandalism': ['keyed', 'vandal', 'graffiti', 'broken window', 'slashed'],
        }
        if loss_type in mismatch_keywords:
            keywords = mismatch_keywords[loss_type]
            if not any(kw in description.lower() for kw in keywords):
                flags.append({
                    'indicator': 'mismatched_damage',
                    'description': f'Description may not match loss type: {loss_type}',
                    'severity': 'medium',
                })
                score += self.INDICATORS['mismatched_damage']['weight']

        # Try LLM-enhanced analysis
        try:
            llm_result = self._llm_fraud_analysis(claim_data)
            if llm_result:
                if llm_result.get('additional_flags'):
                    flags.extend(llm_result['additional_flags'])
                if llm_result.get('score_adjustment'):
                    score = min(1.0, score + llm_result['score_adjustment'])
        except Exception as e:
            logger.warning(f"[FraudDetectorAgent] LLM analysis unavailable: {e}")

        # Cap score
        score = min(1.0, max(0.0, score))

        severity = 'low'
        if score > 0.3:
            severity = 'medium'
        if score > 0.6:
            severity = 'high'
        if score > 0.8:
            severity = 'critical'

        result = {
            'fraud_score': round(score, 4),
            'severity': severity,
            'flags': flags,
            'flag_count': len(flags),
            'recommendation': self._get_recommendation(score),
            'requires_review': score > 0.3,
        }

        logger.info(f"[FraudDetectorAgent] Score: {score:.2f}, Flags: {len(flags)}")
        return result

    def _llm_fraud_analysis(self, claim_data: Dict) -> Dict:
        """Use LLM for advanced fraud pattern detection."""
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return {}

        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[{
                "role": "user",
                "content": f"""Analyze this insurance claim for fraud indicators. Return JSON:
{{"additional_flags": [{{"indicator": "str", "description": "str", "severity": "low|medium|high"}}], "score_adjustment": float_0_to_0.3, "analysis": "str"}}
Claim: {json.dumps(claim_data, default=str)[:3000]}"""
            }],
            response_format={"type": "json_object"},
            max_tokens=400,
        )
        return json.loads(response.choices[0].message.content)

    def _get_recommendation(self, score: float) -> str:
        if score < 0.15:
            return "Low risk. Proceed with standard processing."
        elif score < 0.3:
            return "Minor indicators detected. Standard review recommended."
        elif score < 0.6:
            return "Moderate risk. Manual review by senior adjuster recommended."
        elif score < 0.8:
            return "High risk. Detailed investigation required before processing."
        else:
            return "Critical risk. Refer to Special Investigations Unit (SIU) immediately."
