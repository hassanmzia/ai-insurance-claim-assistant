# AI Insurance Claim Assistant

A professional-grade, multi-agent AI-powered insurance claim processing platform built with Django, React/TypeScript, and Node.js. Features MCP (Model Context Protocol), A2A (Agent-to-Agent) protocol, RAG-powered claim analysis, fraud detection, and real-time processing pipeline visualization.

## Architecture

```
                        +------------------+
                        |   React/TS UI    |
                        |   Port 3062      |
                        +--------+---------+
                                 |
                        +--------+---------+
                        | Node.js Gateway  |
                        |   Port 4062      |
                        +---+----------+---+
                            |          |
              +-------------+    +-----+-----------+
              |                  |                  |
    +---------+---------+  +----+--------+  +------+------+
    | Django Backend API |  | Agent Svc  |  | MCP Server  |
    |    Port 8062      |  | Port 9062  |  | Port 5062   |
    +---------+---------+  +----+--------+  +-------------+
              |                 |
    +---------+-----+    +-----+--------+
    | PostgreSQL    |    |  ChromaDB    |
    | Port 5462     |    |  Port 8562   |
    +---------------+    +--------------+
              |
    +---------+-----+
    |    Redis      |
    |  Port 6382    |
    +---------------+
```

## Features

### From Notebook (AgenticRAG with Smolagents)
- **Claim Parsing** - Structured extraction of claim data into ClaimInfo
- **Policy Query Generation** - AI-generated queries for policy retrieval
- **RAG Policy Retrieval** - ChromaDB vector search for relevant policy sections
- **Coverage Recommendation** - AI evaluation of claims against policy text
- **Decision Finalization** - Automated claim decisions with deductible and payout calculation
- **Pydantic Schema Models** - ClaimInfo, PolicyQueries, PolicyRecommendation, ClaimDecision
- **Custom Prompt Templates** - Planning, managed agent, and final answer prompts

### Enhanced Professional Features
- **Multi-Agent System** - 6 specialized AI agents with orchestrator coordination
- **MCP Protocol** - Model Context Protocol server with tools, resources, and prompts
- **A2A Protocol** - Agent-to-Agent communication with registry and discovery
- **Fraud Detection** - Rule-based + AI-powered fraud analysis with scoring
- **Document Analysis** - AI-powered extraction from invoices, reports, and photos
- **Real-time Updates** - WebSocket-based claim status and dashboard updates
- **RBAC** - Role-based access control (Admin, Adjuster, Reviewer, Customer)
- **Audit Trail** - Complete audit logging for all claim actions
- **Dashboard Analytics** - Charts, trends, KPIs with period filtering
- **Notification System** - Real-time notifications for claim lifecycle events
- **Policy Document Management** - Upload, index, and search policy PDFs

### AI Agents
| Agent | Description |
|-------|-------------|
| Orchestrator | Coordinates the multi-agent processing pipeline |
| Claim Parser | Extracts structured ClaimInfo from raw data |
| Policy Retriever | Generates queries and retrieves from ChromaDB |
| Recommendation | Evaluates claims against policy text |
| Fraud Detector | Analyzes claims for fraud indicators |
| Decision Maker | Produces final coverage decisions |
| Document Analyzer | Extracts data from uploaded documents |

## Tech Stack

| Layer | Technology | Port |
|-------|-----------|------|
| Frontend | React 18, TypeScript, Chart.js | 3062 |
| API Gateway | Node.js, Express | 4062 |
| Backend API | Django 5.1, DRF, Channels | 8062 |
| Agent Service | FastAPI, smolagents, OpenAI | 9062 |
| MCP Server | FastAPI (MCP Protocol) | 5062 |
| Database | PostgreSQL 16 | 5462 |
| Vector Store | ChromaDB | 8562 |
| Cache/Queue | Redis 7 | 6382 |

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### Setup

1. Clone and configure:
```bash
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
```

2. Start all services:
```bash
docker compose up --build -d
```

3. Access the application:
```
http://172.168.1.95:3062
```

### Demo Credentials
| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Adjuster | demo | demo123 |

## API Endpoints

### Authentication
- `POST /api/token/` - Get JWT tokens
- `POST /api/token/refresh/` - Refresh token
- `POST /api/auth/register/` - Register user

### Claims
- `GET /api/claims/` - List claims
- `POST /api/claims/` - Create claim
- `GET /api/claims/{id}/` - Claim detail
- `POST /api/claims/{id}/process/` - AI process claim
- `POST /api/claims/{id}/assign/` - Assign adjuster
- `POST /api/claims/{id}/update_status/` - Update status

### MCP Protocol
- `GET /mcp/tools/list` - List MCP tools
- `POST /mcp/tools/call` - Execute MCP tool
- `GET /mcp/resources/list` - List resources
- `GET /mcp/prompts/list` - List prompts

### A2A Protocol
- `GET /agents/agents` - Agent discovery
- `POST /agents/a2a/message` - Send A2A message
- `GET /agents/a2a/agents/{id}/card` - Agent card

## Port Reference

All ports are non-default to avoid conflicts:

| Service | Internal | External |
|---------|----------|----------|
| Frontend | 3062 | 3062 |
| API Gateway | 4062 | 4062 |
| MCP Server | 5062 | 5062 |
| PostgreSQL | 5432 | 5462 |
| Redis | 6379 | 6382 |
| Django Backend | 8062 | 8062 |
| ChromaDB | 8000 | 8562 |
| Agent Service | 9062 | 9062 |
