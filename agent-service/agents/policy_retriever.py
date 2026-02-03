"""
Policy Retriever Agent - Generates queries and retrieves policy text from ChromaDB.
Mirrors generate_policy_queries + retrieve_policy_text tools from the notebook.
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PolicyRetrieverAgent:
    """Retrieves relevant policy sections from the vector store."""

    agent_id = "policy_retriever"
    agent_name = "Policy Retriever Agent"
    description = "Generates queries and retrieves relevant policy sections from ChromaDB"

    def __init__(self, collection=None, embedder=None):
        self.collection = collection
        self.embedder = embedder

    def generate_queries(self, claim_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate search queries based on claim information."""
        logger.info(f"[PolicyRetrieverAgent] Generating queries for {claim_info.get('claim_number')}")

        loss_type = claim_info.get('loss_type', 'collision')
        description = claim_info.get('loss_description', '')
        cost = claim_info.get('estimated_repair_cost', 0)
        third_party = claim_info.get('third_party_involved', False)

        queries = [
            f"{loss_type} coverage policy terms and conditions",
            f"deductible amount for {loss_type} claims",
            f"claim settlement procedures and limits",
        ]

        if third_party:
            queries.append("third party liability coverage and procedures")

        if cost > 5000:
            queries.append("high value claim review and approval process")

        if 'theft' in description.lower() or loss_type == 'theft':
            queries.append("theft coverage exclusions and requirements")

        if 'weather' in description.lower() or loss_type == 'weather':
            queries.append("comprehensive coverage weather related damage")

        # Try to use LLM for better queries
        try:
            from openai import OpenAI
            api_key = os.environ.get('OPENAI_API_KEY')
            if api_key:
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
                    messages=[{
                        "role": "user",
                        "content": f"""Generate 3-5 search queries to find relevant auto insurance policy sections for this claim:
                        Loss type: {loss_type}
                        Description: {description}
                        Cost: ${cost}
                        Third party: {third_party}
                        Return a JSON object: {{"queries": ["query1", "query2", ...]}}"""
                    }],
                    response_format={"type": "json_object"},
                    max_tokens=300,
                )
                result = json.loads(response.choices[0].message.content)
                if 'queries' in result:
                    queries = result['queries']
        except Exception as e:
            logger.warning(f"LLM query generation fallback: {e}")

        logger.info(f"[PolicyRetrieverAgent] Generated {len(queries)} queries")
        return {"queries": queries}

    def retrieve(self, queries: List[str]) -> Dict[str, Any]:
        """Retrieve policy text from ChromaDB."""
        logger.info(f"[PolicyRetrieverAgent] Retrieving policy text with {len(queries)} queries")

        if not self.collection or not self.embedder:
            logger.warning("[PolicyRetrieverAgent] Vector store not available, returning default policy text")
            return {
                "policy_text": self._get_default_policy_text(),
                "source": "default",
                "chunks_retrieved": 0,
            }

        try:
            all_texts = []
            for query in queries:
                query_embedding = self.embedder.encode([query])[0].tolist()
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=3,
                )
                if results and results['documents']:
                    all_texts.extend(results['documents'][0])

            # Deduplicate
            seen = set()
            unique_texts = []
            for text in all_texts:
                if text not in seen:
                    seen.add(text)
                    unique_texts.append(text)

            policy_text = "\n\n".join(unique_texts) if unique_texts else self._get_default_policy_text()

            return {
                "policy_text": policy_text,
                "source": "chromadb" if unique_texts else "default",
                "chunks_retrieved": len(unique_texts),
            }
        except Exception as e:
            logger.error(f"[PolicyRetrieverAgent] Retrieval error: {e}")
            return {
                "policy_text": self._get_default_policy_text(),
                "source": "default_fallback",
                "chunks_retrieved": 0,
            }

    def _get_default_policy_text(self) -> str:
        return """
STANDARD AUTO INSURANCE POLICY

PART A - LIABILITY COVERAGE
We will pay damages for bodily injury or property damage for which any insured becomes legally responsible because of an auto accident. The most we pay is the limit shown on the declarations page.

PART B - MEDICAL PAYMENTS COVERAGE
We will pay reasonable medical expenses for bodily injury caused by an accident. Coverage applies to the named insured and family members while occupying a motor vehicle.

PART C - UNINSURED MOTORISTS COVERAGE
We will pay compensatory damages which an insured is legally entitled to recover from the owner or operator of an uninsured motor vehicle.

PART D - COLLISION COVERAGE
We will pay for direct and accidental loss to your covered auto caused by collision less any applicable deductible. Standard deductibles: $250, $500, $750, $1000.

PART E - COMPREHENSIVE COVERAGE
We will pay for direct and accidental loss to your covered auto not caused by collision. This includes theft, vandalism, weather damage, falling objects, fire, and animal collisions.

EXCLUSIONS:
- Damage from wear and tear, mechanical failure, or road damage to tires
- Loss from nuclear hazard or war
- Loss to equipment not factory-installed
- Damage while vehicle used for commercial purposes without endorsement
- Damage while vehicle operated by unlicensed driver
- Losses occurring outside the coverage territory

CLAIM PROCEDURES:
1. Report the claim within 48 hours of the incident
2. Provide a police report for theft, vandalism, or accidents involving injury
3. Submit repair estimates from certified repair facilities
4. Cooperate with the claims investigation
5. Do not authorize repairs without prior approval for claims exceeding $2,000

DEDUCTIBLES:
Standard deductible applies per incident. Deductible is waived if the insured is not at fault and the at-fault party is identified.

SETTLEMENT:
Claims are settled based on actual cash value or repair cost, whichever is less. Depreciation applies to parts replacement. Maximum payout per incident shall not exceed the coverage limit.
"""
