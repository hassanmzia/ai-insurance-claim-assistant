"""
Orchestrator Agent - Coordinates multi-agent claim processing pipeline.
Manages the A2A workflow between specialized agents.
"""
import logging
import time
from typing import Dict, Any, List

from .claim_parser import ClaimParserAgent
from .policy_retriever import PolicyRetrieverAgent
from .recommendation import RecommendationAgent
from .fraud_detector import FraudDetectorAgent
from .decision_maker import DecisionMakerAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Orchestrates the multi-agent claim processing pipeline.
    Coordinates: ClaimParser -> PolicyRetriever -> Recommendation -> FraudDetector -> DecisionMaker
    """

    def __init__(self, collection=None, embedder=None, redis_client=None):
        self.collection = collection
        self.embedder = embedder
        self.redis_client = redis_client

    async def process(self, claim_data: Dict[str, Any], processing_log: List) -> Dict[str, Any]:
        """Run the full claim processing pipeline."""
        processing_type = claim_data.get('processing_type', 'full')

        # Step 1: Parse Claim
        step_start = time.time()
        processing_log.append({
            'step': 'claim_parsing', 'agent': 'ClaimParserAgent',
            'status': 'started', 'timestamp': step_start,
        })

        parser = ClaimParserAgent()
        claim_info = parser.parse(claim_data)

        processing_log.append({
            'step': 'claim_parsing', 'agent': 'ClaimParserAgent',
            'status': 'completed', 'duration_ms': int((time.time() - step_start) * 1000),
            'result_summary': f"Parsed claim {claim_info.get('claim_number', 'N/A')}",
        })

        if processing_type == 'fraud_check':
            return await self._fraud_check_only(claim_data, claim_info, processing_log)

        # Step 2: Generate queries and retrieve policy text
        step_start = time.time()
        processing_log.append({
            'step': 'policy_retrieval', 'agent': 'PolicyRetrieverAgent',
            'status': 'started', 'timestamp': step_start,
        })

        retriever = PolicyRetrieverAgent(collection=self.collection, embedder=self.embedder)
        queries = retriever.generate_queries(claim_info)
        policy_text = retriever.retrieve(queries.get('queries', []))

        processing_log.append({
            'step': 'policy_retrieval', 'agent': 'PolicyRetrieverAgent',
            'status': 'completed', 'duration_ms': int((time.time() - step_start) * 1000),
            'result_summary': f"Retrieved {len(queries.get('queries', []))} policy sections",
        })

        if processing_type == 'policy_lookup':
            return {
                'claim_info': claim_info,
                'queries': queries,
                'policy_text': policy_text,
            }

        # Step 3: Generate Recommendation
        step_start = time.time()
        processing_log.append({
            'step': 'recommendation', 'agent': 'RecommendationAgent',
            'status': 'started', 'timestamp': step_start,
        })

        recommender = RecommendationAgent()
        recommendation = recommender.recommend(claim_info, policy_text.get('policy_text', ''))

        processing_log.append({
            'step': 'recommendation', 'agent': 'RecommendationAgent',
            'status': 'completed', 'duration_ms': int((time.time() - step_start) * 1000),
            'result_summary': recommendation.get('recommendation_summary', 'N/A'),
        })

        if processing_type == 'recommendation':
            return {
                'claim_info': claim_info,
                'recommendation': recommendation,
                'policy_text': policy_text,
            }

        # Step 4: Fraud Detection (parallel with recommendation in production)
        step_start = time.time()
        processing_log.append({
            'step': 'fraud_detection', 'agent': 'FraudDetectorAgent',
            'status': 'started', 'timestamp': step_start,
        })

        fraud_detector = FraudDetectorAgent()
        fraud_result = fraud_detector.analyze(claim_data)

        processing_log.append({
            'step': 'fraud_detection', 'agent': 'FraudDetectorAgent',
            'status': 'completed', 'duration_ms': int((time.time() - step_start) * 1000),
            'result_summary': f"Fraud score: {fraud_result.get('fraud_score', 0):.2f}",
        })

        # Step 5: Final Decision
        step_start = time.time()
        processing_log.append({
            'step': 'decision', 'agent': 'DecisionMakerAgent',
            'status': 'started', 'timestamp': step_start,
        })

        decision_maker = DecisionMakerAgent()
        decision = decision_maker.decide(claim_info, recommendation, fraud_result)

        processing_log.append({
            'step': 'decision', 'agent': 'DecisionMakerAgent',
            'status': 'completed', 'duration_ms': int((time.time() - step_start) * 1000),
            'result_summary': f"Decision: {'Covered' if decision.get('covered') else 'Denied'}",
        })

        return {
            'claim_info': claim_info,
            'recommendation': recommendation,
            'fraud_score': fraud_result.get('fraud_score', 0),
            'fraud_flags': fraud_result.get('flags', []),
            'fraud_analysis': fraud_result,
            'decision': decision,
        }

    async def _fraud_check_only(self, claim_data, claim_info, processing_log):
        step_start = time.time()
        processing_log.append({
            'step': 'fraud_detection', 'agent': 'FraudDetectorAgent',
            'status': 'started', 'timestamp': step_start,
        })
        fraud_detector = FraudDetectorAgent()
        fraud_result = fraud_detector.analyze(claim_data)
        processing_log.append({
            'step': 'fraud_detection', 'agent': 'FraudDetectorAgent',
            'status': 'completed', 'duration_ms': int((time.time() - step_start) * 1000),
        })
        return {
            'claim_info': claim_info,
            'fraud_score': fraud_result.get('fraud_score', 0),
            'fraud_flags': fraud_result.get('flags', []),
            'fraud_analysis': fraud_result,
            'decision': {'covered': fraud_result.get('fraud_score', 0) < 0.7},
        }
