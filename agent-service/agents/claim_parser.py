"""
Claim Parser Agent - Extracts and validates structured claim information.
Mirrors the parse_claim tool from the notebook.
"""
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ClaimInfo(BaseModel):
    """Extracted insurance claim information."""
    claim_number: str
    policy_number: str
    claimant_name: str
    date_of_loss: str
    loss_description: str
    loss_type: str = "collision"
    estimated_repair_cost: float
    vehicle_details: Optional[Dict[str, Any]] = None
    third_party_involved: bool = False


class ClaimParserAgent:
    """Parses raw claim data into structured ClaimInfo."""

    agent_id = "claim_parser"
    agent_name = "Claim Parser Agent"
    description = "Extracts and validates structured claim information from raw data"

    def parse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse claim data into structured format."""
        logger.info(f"[ClaimParserAgent] Parsing claim: {data.get('claim_number', 'unknown')}")

        try:
            # Map incoming fields to ClaimInfo
            claim_info = ClaimInfo(
                claim_number=data.get('claim_number', ''),
                policy_number=data.get('policy_number', ''),
                claimant_name=data.get('claimant_name', ''),
                date_of_loss=data.get('date_of_loss', ''),
                loss_description=data.get('loss_description', ''),
                loss_type=data.get('loss_type', 'collision'),
                estimated_repair_cost=float(data.get('estimated_repair_cost', 0)),
                vehicle_details=data.get('vehicle_details'),
                third_party_involved=data.get('third_party_involved', False),
            )
            result = claim_info.model_dump()
            logger.info(f"[ClaimParserAgent] Successfully parsed claim {claim_info.claim_number}")
            return result
        except Exception as e:
            logger.error(f"[ClaimParserAgent] Error parsing claim: {e}")
            return {"error": str(e), "raw_data": data}
