"""
A2A (Agent-to-Agent) Protocol Implementation.
Enables standardized communication between specialized agents.
"""
import logging
import time
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class A2AMessage:
    """Standard A2A message format."""
    def __init__(self, from_agent: str, to_agent: str, action: str,
                 payload: Dict[str, Any], correlation_id: str = None):
        self.message_id = str(uuid.uuid4())
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.action = action
        self.payload = payload
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.timestamp = time.time()

    def to_dict(self):
        return {
            'message_id': self.message_id,
            'from_agent': self.from_agent,
            'to_agent': self.to_agent,
            'action': self.action,
            'payload': self.payload,
            'correlation_id': self.correlation_id,
            'timestamp': self.timestamp,
        }


class A2AProtocol:
    """
    Agent-to-Agent protocol handler.
    Routes messages between agents and manages agent communication.
    """

    def __init__(self, registry, collection=None, embedder=None, redis_client=None):
        self.registry = registry
        self.collection = collection
        self.embedder = embedder
        self.redis_client = redis_client

    async def route_message(self, message) -> Dict[str, Any]:
        """Route an A2A message to the target agent."""
        logger.info(f"[A2A] Routing: {message.from_agent} -> {message.to_agent} ({message.action})")

        agent_class = self.registry.get_agent(message.to_agent)
        if not agent_class:
            return {
                'status': 'error',
                'error': f'Agent {message.to_agent} not found',
                'message_id': message.message_id,
            }

        try:
            # Instantiate agent with dependencies
            if message.to_agent in ('policy_retriever',):
                agent = agent_class(collection=self.collection, embedder=self.embedder)
            else:
                agent = agent_class()

            # Route to the correct method based on action
            action_map = {
                'claim_parser': {'parse': 'parse'},
                'policy_retriever': {
                    'generate_queries': 'generate_queries',
                    'retrieve': 'retrieve',
                },
                'recommendation': {'recommend': 'recommend'},
                'fraud_detector': {'analyze': 'analyze'},
                'decision_maker': {'decide': 'decide'},
                'document_analyzer': {'analyze': 'analyze'},
            }

            agent_actions = action_map.get(message.to_agent, {})
            method_name = agent_actions.get(message.action)

            if not method_name:
                return {
                    'status': 'error',
                    'error': f'Unknown action {message.action} for agent {message.to_agent}',
                }

            method = getattr(agent, method_name)

            # Handle different parameter signatures
            payload = message.payload
            if isinstance(payload, dict) and len(payload) == 1:
                result = method(list(payload.values())[0])
            elif isinstance(payload, dict):
                result = method(**payload)
            else:
                result = method(payload)

            # Handle async methods
            import asyncio
            if asyncio.iscoroutine(result):
                result = await result

            return {
                'status': 'success',
                'message_id': str(uuid.uuid4()),
                'correlation_id': message.correlation_id,
                'from_agent': message.to_agent,
                'result': result,
                'timestamp': time.time(),
            }

        except Exception as e:
            logger.error(f"[A2A] Error routing to {message.to_agent}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'message_id': str(uuid.uuid4()),
                'correlation_id': getattr(message, 'correlation_id', None),
            }
