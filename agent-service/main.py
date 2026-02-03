"""
AI Insurance Claim Assistant - Multi-Agent Service
Implements MCP (Model Context Protocol) and A2A (Agent-to-Agent) patterns
with specialized agents for claim processing, fraud detection, and policy retrieval.
"""
import os
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import chromadb
import httpx
import redis

from agents.orchestrator import OrchestratorAgent
from agents.claim_parser import ClaimParserAgent
from agents.policy_retriever import PolicyRetrieverAgent
from agents.recommendation import RecommendationAgent
from agents.fraud_detector import FraudDetectorAgent
from agents.decision_maker import DecisionMakerAgent
from agents.document_analyzer import DocumentAnalyzerAgent
from a2a.protocol import A2AProtocol
from a2a.registry import AgentRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
chroma_client = None
collection = None
embedder = None
agent_registry = None
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global chroma_client, collection, embedder, agent_registry, redis_client

    # ChromaDB
    chromadb_url = os.environ.get('CHROMADB_URL', 'http://chromadb:8000')
    try:
        chroma_client = chromadb.HttpClient(host=chromadb_url.replace('http://', '').split(':')[0],
                                             port=int(chromadb_url.split(':')[-1]))
        collection = chroma_client.get_or_create_collection(name="auto_insurance_policy")
        logger.info("ChromaDB connected successfully")
    except Exception as e:
        logger.warning(f"ChromaDB connection deferred: {e}")

    # Embedding model
    try:
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded")
    except Exception as e:
        logger.warning(f"Embedding model load deferred: {e}")

    # Redis
    try:
        redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
        redis_client = redis.from_url(redis_url)
        redis_client.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection deferred: {e}")

    # Agent Registry (A2A)
    agent_registry = AgentRegistry()
    agent_registry.register_agents()
    logger.info("Agent registry initialized with A2A protocol")

    yield

    logger.info("Shutting down agent service")


app = FastAPI(
    title="AI Insurance Claim Assistant - Agent Service",
    description="Multi-Agent system with MCP and A2A protocols for insurance claim processing",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================================
# Request/Response Models
# ==========================================================================
class ClaimProcessRequest(BaseModel):
    claim_id: str
    claim_number: str
    policy_number: str
    claimant_name: str
    date_of_loss: str
    loss_description: str
    loss_type: str = "collision"
    estimated_repair_cost: float
    vehicle_details: Dict[str, Any] = {}
    third_party_involved: bool = False
    processing_type: str = "full"


class PolicyIndexRequest(BaseModel):
    document_id: str
    file_url: str
    policy_type: str = "auto"


class AgentMessage(BaseModel):
    """A2A Protocol message format."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str
    to_agent: str
    action: str
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class MCPToolCall(BaseModel):
    """MCP Tool Call format."""
    tool_name: str
    parameters: Dict[str, Any]
    context: Dict[str, Any] = {}


class MCPToolResult(BaseModel):
    """MCP Tool Result format."""
    tool_name: str
    result: Any
    status: str = "success"
    error: Optional[str] = None


# ==========================================================================
# Health & Info Endpoints
# ==========================================================================
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "agent-service",
        "agents": agent_registry.list_agents() if agent_registry else [],
    }


@app.get("/api/agents")
async def list_agents():
    """List all registered agents and their capabilities (A2A discovery)."""
    if not agent_registry:
        return {"agents": []}
    return {"agents": agent_registry.get_agent_cards()}


# ==========================================================================
# Claim Processing (Orchestrator)
# ==========================================================================
@app.post("/api/process-claim")
async def process_claim(request: ClaimProcessRequest):
    """
    Main claim processing endpoint. The Orchestrator agent coordinates
    multiple specialized agents via A2A protocol.
    """
    start_time = time.time()
    processing_log = []

    try:
        claim_data = request.model_dump()
        orchestrator = OrchestratorAgent(
            collection=collection,
            embedder=embedder,
            redis_client=redis_client,
        )

        result = await orchestrator.process(claim_data, processing_log)

        processing_time_ms = int((time.time() - start_time) * 1000)
        result['processing_log'] = processing_log
        result['processing_time_ms'] = processing_time_ms

        logger.info(f"Claim {request.claim_number} processed in {processing_time_ms}ms")
        return result

    except Exception as e:
        logger.error(f"Claim processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================================
# Policy Document Indexing
# ==========================================================================
@app.post("/api/index-policy")
async def index_policy(request: PolicyIndexRequest):
    """Index a policy PDF document into ChromaDB."""
    try:
        if not collection or not embedder:
            raise HTTPException(status_code=503, detail="Vector store not initialized")

        # Fetch the PDF
        async with httpx.AsyncClient() as client:
            resp = await client.get(request.file_url, timeout=30.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Could not fetch document")

        import io
        import PyPDF2

        pdf_reader = PyPDF2.PdfReader(io.BytesIO(resp.content))
        chunks = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text and text.strip():
                # Split pages into smaller chunks
                paragraphs = text.split('\n\n')
                chunks.extend([p.strip() for p in paragraphs if p.strip()])

        if not chunks:
            return {"status": "empty", "chunk_count": 0}

        # Generate embeddings and store in ChromaDB
        chunk_ids = [f"{request.document_id}_chunk_{i}" for i in range(len(chunks))]
        chunk_embeddings = embedder.encode(chunks).tolist()

        collection.add(
            documents=chunks,
            embeddings=chunk_embeddings,
            ids=chunk_ids,
            metadatas=[{
                "document_id": request.document_id,
                "policy_type": request.policy_type,
                "chunk_index": i,
            } for i in range(len(chunks))]
        )

        logger.info(f"Indexed {len(chunks)} chunks for document {request.document_id}")
        return {"status": "indexed", "chunk_count": len(chunks)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Policy indexing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================================
# MCP Protocol Endpoints
# ==========================================================================
@app.post("/api/mcp/tools/call", response_model=MCPToolResult)
async def mcp_tool_call(request: MCPToolCall):
    """
    MCP (Model Context Protocol) tool execution endpoint.
    Allows external models/agents to call tools through a standardized interface.
    """
    tool_map = {
        "parse_claim": _mcp_parse_claim,
        "generate_policy_queries": _mcp_generate_queries,
        "retrieve_policy_text": _mcp_retrieve_policy,
        "generate_recommendation": _mcp_generate_recommendation,
        "finalize_decision": _mcp_finalize_decision,
        "detect_fraud": _mcp_detect_fraud,
        "analyze_document": _mcp_analyze_document,
    }

    handler = tool_map.get(request.tool_name)
    if not handler:
        return MCPToolResult(
            tool_name=request.tool_name,
            result=None,
            status="error",
            error=f"Unknown tool: {request.tool_name}"
        )

    try:
        result = await handler(request.parameters, request.context)
        return MCPToolResult(tool_name=request.tool_name, result=result)
    except Exception as e:
        return MCPToolResult(
            tool_name=request.tool_name, result=None,
            status="error", error=str(e)
        )


@app.get("/api/mcp/tools")
async def mcp_list_tools():
    """MCP tool discovery endpoint - lists all available tools."""
    return {
        "tools": [
            {
                "name": "parse_claim",
                "description": "Parse claim data and extract structured ClaimInfo",
                "parameters": {"claim_data": "dict - Raw claim data"},
            },
            {
                "name": "generate_policy_queries",
                "description": "Generate queries to retrieve relevant policy sections",
                "parameters": {"claim_info": "dict - Parsed claim information"},
            },
            {
                "name": "retrieve_policy_text",
                "description": "Retrieve policy text from vector store using queries",
                "parameters": {"queries": "list[str] - Query strings"},
            },
            {
                "name": "generate_recommendation",
                "description": "Generate coverage recommendation based on claim and policy",
                "parameters": {
                    "claim_info": "dict - Claim information",
                    "policy_text": "str - Retrieved policy text",
                },
            },
            {
                "name": "finalize_decision",
                "description": "Produce final claim decision from recommendation",
                "parameters": {
                    "claim_info": "dict - Claim information",
                    "recommendation": "dict - Policy recommendation",
                },
            },
            {
                "name": "detect_fraud",
                "description": "Analyze claim for potential fraud indicators",
                "parameters": {"claim_data": "dict - Full claim data"},
            },
            {
                "name": "analyze_document",
                "description": "Analyze uploaded claim document (invoice, photo, report)",
                "parameters": {"document_url": "str", "document_type": "str"},
            },
        ]
    }


# ==========================================================================
# A2A Protocol Endpoints
# ==========================================================================
@app.post("/api/a2a/message")
async def a2a_send_message(message: AgentMessage):
    """
    A2A (Agent-to-Agent) message passing endpoint.
    Routes messages between specialized agents.
    """
    if not agent_registry:
        raise HTTPException(status_code=503, detail="Agent registry not initialized")

    protocol = A2AProtocol(agent_registry, collection, embedder, redis_client)
    result = await protocol.route_message(message)
    return result


@app.get("/api/a2a/agents/{agent_id}/card")
async def a2a_agent_card(agent_id: str):
    """Get the A2A agent card for a specific agent."""
    if not agent_registry:
        raise HTTPException(status_code=503, detail="Agent registry not initialized")
    card = agent_registry.get_agent_card(agent_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return card


# ==========================================================================
# MCP Tool Handlers
# ==========================================================================
async def _mcp_parse_claim(params: dict, context: dict):
    agent = ClaimParserAgent()
    return agent.parse(params.get('claim_data', {}))


async def _mcp_generate_queries(params: dict, context: dict):
    agent = PolicyRetrieverAgent(collection=collection, embedder=embedder)
    return agent.generate_queries(params.get('claim_info', {}))


async def _mcp_retrieve_policy(params: dict, context: dict):
    if not collection or not embedder:
        return {"error": "Vector store not initialized"}
    agent = PolicyRetrieverAgent(collection=collection, embedder=embedder)
    return agent.retrieve(params.get('queries', []))


async def _mcp_generate_recommendation(params: dict, context: dict):
    agent = RecommendationAgent()
    return agent.recommend(params.get('claim_info', {}), params.get('policy_text', ''))


async def _mcp_finalize_decision(params: dict, context: dict):
    agent = DecisionMakerAgent()
    return agent.decide(params.get('claim_info', {}), params.get('recommendation', {}))


async def _mcp_detect_fraud(params: dict, context: dict):
    agent = FraudDetectorAgent()
    return agent.analyze(params.get('claim_data', {}))


async def _mcp_analyze_document(params: dict, context: dict):
    agent = DocumentAnalyzerAgent()
    return await agent.analyze(params.get('document_url', ''), params.get('document_type', 'other'))
