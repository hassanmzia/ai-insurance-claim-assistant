"""
Agent Registry - Manages agent discovery and registration for A2A protocol.
"""
import logging
from typing import Dict, Any, Optional, List

from agents.claim_parser import ClaimParserAgent
from agents.policy_retriever import PolicyRetrieverAgent
from agents.recommendation import RecommendationAgent
from agents.fraud_detector import FraudDetectorAgent
from agents.decision_maker import DecisionMakerAgent
from agents.document_analyzer import DocumentAnalyzerAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for all available agents. Supports A2A agent discovery."""

    def __init__(self):
        self._agents: Dict[str, type] = {}
        self._agent_cards: Dict[str, Dict[str, Any]] = {}

    def register_agents(self):
        """Register all available agents."""
        agents = [
            ClaimParserAgent,
            PolicyRetrieverAgent,
            RecommendationAgent,
            FraudDetectorAgent,
            DecisionMakerAgent,
            DocumentAnalyzerAgent,
        ]

        for agent_cls in agents:
            agent_id = agent_cls.agent_id
            self._agents[agent_id] = agent_cls
            self._agent_cards[agent_id] = {
                'agent_id': agent_id,
                'name': agent_cls.agent_name,
                'description': agent_cls.description,
                'protocol': 'a2a/1.0',
                'capabilities': self._get_capabilities(agent_cls),
                'status': 'available',
            }
            logger.info(f"Registered agent: {agent_id} ({agent_cls.agent_name})")

    def _get_capabilities(self, agent_cls) -> List[Dict[str, str]]:
        """Extract agent capabilities from its public methods."""
        capabilities = []
        for name in dir(agent_cls):
            if not name.startswith('_') and name not in ('agent_id', 'agent_name', 'description'):
                method = getattr(agent_cls, name, None)
                if callable(method):
                    capabilities.append({
                        'action': name,
                        'description': (method.__doc__ or '').strip()[:200],
                    })
        return capabilities

    def get_agent(self, agent_id: str) -> Optional[type]:
        return self._agents.get(agent_id)

    def get_agent_card(self, agent_id: str) -> Optional[Dict]:
        return self._agent_cards.get(agent_id)

    def get_agent_cards(self) -> List[Dict]:
        return list(self._agent_cards.values())

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())
