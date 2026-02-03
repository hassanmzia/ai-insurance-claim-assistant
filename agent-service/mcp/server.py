"""
MCP (Model Context Protocol) Server.
Provides a standardized interface for external AI models to call tools.
Runs on port 5062.
"""
import json
import logging
import os
import time
import uuid
from typing import Dict, Any, List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Insurance Claims MCP Server",
    description="Model Context Protocol server for insurance claim processing tools",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================================
# MCP Protocol Models
# ==========================================================================
class MCPServerInfo(BaseModel):
    name: str = "insurance-claims-mcp"
    version: str = "1.0.0"
    protocol_version: str = "2024-11-05"
    capabilities: Dict[str, Any] = {
        "tools": {"listChanged": True},
        "resources": {"subscribe": False, "listChanged": True},
        "prompts": {"listChanged": True},
    }


class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPToolCallRequest(BaseModel):
    method: str = "tools/call"
    params: Dict[str, Any]


class MCPResource(BaseModel):
    uri: str
    name: str
    description: str
    mimeType: str = "application/json"


class MCPPrompt(BaseModel):
    name: str
    description: str
    arguments: List[Dict[str, Any]] = []


# ==========================================================================
# MCP Server Info
# ==========================================================================
@app.get("/")
async def server_info():
    return MCPServerInfo().model_dump()


# ==========================================================================
# MCP Tools
# ==========================================================================
@app.get("/tools/list")
async def list_tools():
    """List all available MCP tools."""
    tools = [
        MCPTool(
            name="parse_claim",
            description="Parse raw claim data into structured ClaimInfo format",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_data": {
                        "type": "object",
                        "description": "Raw claim data with fields: claim_number, policy_number, claimant_name, date_of_loss, loss_description, estimated_repair_cost"
                    }
                },
                "required": ["claim_data"]
            }
        ),
        MCPTool(
            name="generate_policy_queries",
            description="Generate search queries for retrieving relevant policy sections from the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_info": {"type": "object", "description": "Parsed claim information"}
                },
                "required": ["claim_info"]
            }
        ),
        MCPTool(
            name="retrieve_policy_text",
            description="Retrieve relevant policy document sections from ChromaDB vector store",
            inputSchema={
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Search queries for policy retrieval"
                    }
                },
                "required": ["queries"]
            }
        ),
        MCPTool(
            name="generate_recommendation",
            description="Generate a coverage recommendation by evaluating claim against policy text",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_info": {"type": "object"},
                    "policy_text": {"type": "string"}
                },
                "required": ["claim_info", "policy_text"]
            }
        ),
        MCPTool(
            name="finalize_decision",
            description="Produce a final claim decision with coverage determination, deductible, and payout",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_info": {"type": "object"},
                    "recommendation": {"type": "object"},
                    "fraud_result": {"type": "object"}
                },
                "required": ["claim_info", "recommendation"]
            }
        ),
        MCPTool(
            name="detect_fraud",
            description="Analyze a claim for potential fraud indicators",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_data": {"type": "object"}
                },
                "required": ["claim_data"]
            }
        ),
        MCPTool(
            name="process_claim_full",
            description="Run the complete multi-agent claim processing pipeline",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_data": {"type": "object"},
                    "processing_type": {
                        "type": "string",
                        "enum": ["full", "fraud_check", "policy_lookup", "recommendation"]
                    }
                },
                "required": ["claim_data"]
            }
        ),
    ]
    return {"tools": [t.model_dump() for t in tools]}


@app.post("/tools/call")
async def call_tool(request: MCPToolCallRequest):
    """Execute an MCP tool call."""
    tool_name = request.params.get("name")
    arguments = request.params.get("arguments", {})

    logger.info(f"[MCP] Tool call: {tool_name}")

    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        if tool_name == "parse_claim":
            from agents.claim_parser import ClaimParserAgent
            agent = ClaimParserAgent()
            result = agent.parse(arguments.get("claim_data", {}))

        elif tool_name == "generate_policy_queries":
            from agents.policy_retriever import PolicyRetrieverAgent
            agent = PolicyRetrieverAgent()
            result = agent.generate_queries(arguments.get("claim_info", {}))

        elif tool_name == "retrieve_policy_text":
            from agents.policy_retriever import PolicyRetrieverAgent
            agent = PolicyRetrieverAgent()
            result = agent.retrieve(arguments.get("queries", []))

        elif tool_name == "generate_recommendation":
            from agents.recommendation import RecommendationAgent
            agent = RecommendationAgent()
            result = agent.recommend(
                arguments.get("claim_info", {}),
                arguments.get("policy_text", "")
            )

        elif tool_name == "finalize_decision":
            from agents.decision_maker import DecisionMakerAgent
            agent = DecisionMakerAgent()
            result = agent.decide(
                arguments.get("claim_info", {}),
                arguments.get("recommendation", {}),
                arguments.get("fraud_result")
            )

        elif tool_name == "detect_fraud":
            from agents.fraud_detector import FraudDetectorAgent
            agent = FraudDetectorAgent()
            result = agent.analyze(arguments.get("claim_data", {}))

        elif tool_name == "process_claim_full":
            from agents.orchestrator import OrchestratorAgent
            orchestrator = OrchestratorAgent()
            processing_log = []
            claim_data = arguments.get("claim_data", {})
            claim_data['processing_type'] = arguments.get("processing_type", "full")
            result = await orchestrator.process(claim_data, processing_log)
            result['processing_log'] = processing_log

        else:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                "isError": True,
            }

        return {
            "content": [{"type": "text", "text": json.dumps(result, default=str)}],
            "isError": False,
        }

    except Exception as e:
        logger.error(f"[MCP] Tool error: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "isError": True,
        }


# ==========================================================================
# MCP Resources
# ==========================================================================
@app.get("/resources/list")
async def list_resources():
    """List available MCP resources."""
    resources = [
        MCPResource(
            uri="insurance://policy/auto/standard",
            name="Standard Auto Insurance Policy",
            description="The standard auto insurance policy document used for claim evaluation",
        ),
        MCPResource(
            uri="insurance://claims/schema",
            name="Claim Data Schema",
            description="The expected schema for insurance claim data",
        ),
        MCPResource(
            uri="insurance://agents/registry",
            name="Agent Registry",
            description="List of all available AI agents and their capabilities",
        ),
    ]
    return {"resources": [r.model_dump() for r in resources]}


@app.get("/resources/read")
async def read_resource(uri: str):
    """Read an MCP resource."""
    if uri == "insurance://claims/schema":
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps({
                    "claim_number": "string",
                    "policy_number": "string",
                    "claimant_name": "string",
                    "date_of_loss": "string (YYYY-MM-DD)",
                    "loss_description": "string",
                    "loss_type": "collision|comprehensive|liability|theft|vandalism|weather",
                    "estimated_repair_cost": "number",
                    "vehicle_details": "object",
                    "third_party_involved": "boolean",
                }, indent=2)
            }]
        }
    return {"contents": []}


# ==========================================================================
# MCP Prompts
# ==========================================================================
@app.get("/prompts/list")
async def list_prompts():
    """List available MCP prompts."""
    prompts = [
        MCPPrompt(
            name="process_claim",
            description="Process an insurance claim through the multi-agent pipeline",
            arguments=[{
                "name": "claim_json",
                "description": "JSON string of claim data",
                "required": True,
            }]
        ),
        MCPPrompt(
            name="fraud_analysis",
            description="Perform fraud analysis on a claim",
            arguments=[{
                "name": "claim_json",
                "description": "JSON string of claim data",
                "required": True,
            }]
        ),
    ]
    return {"prompts": [p.model_dump() for p in prompts]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5062)
