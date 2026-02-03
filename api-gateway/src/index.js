/**
 * API Gateway for AI Insurance Claim Assistant
 * Routes requests to backend (Django) and agent-service, handles WebSocket proxying.
 * Port: 4062
 */
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const { createProxyMiddleware, fixRequestBody } = require('http-proxy-middleware');
const rateLimit = require('express-rate-limit');
const { WebSocketServer } = require('ws');
const http = require('http');

const app = express();
const PORT = process.env.PORT || 4062;
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8062';
const AGENT_SERVICE_URL = process.env.AGENT_SERVICE_URL || 'http://agent-service:9062';
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'http://agent-service:5062';

// Middleware - order matters: CORS and helmet first, then logging
app.use(helmet({ crossOriginResourcePolicy: false }));
app.use(cors({
  origin: [
    'http://172.168.1.95:3062',
    'http://localhost:3062',
    'http://frontend:3062',
  ],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-ID'],
}));
app.use(morgan('combined'));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 1000,
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(limiter);

// Health check (only this route needs body parsing)
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'api-gateway',
    timestamp: new Date().toISOString(),
    upstreams: {
      backend: BACKEND_URL,
      agentService: AGENT_SERVICE_URL,
      mcpServer: MCP_SERVER_URL,
    },
  });
});

// ============================================================
// Proxy: /api/* -> Django Backend
// ============================================================
app.use('/api', createProxyMiddleware({
  target: BACKEND_URL,
  changeOrigin: true,
  timeout: 120000,
  onError: (err, req, res) => {
    console.error(`[Proxy] Backend error: ${err.message}`);
    res.status(502).json({ error: 'Backend service unavailable' });
  },
}));

// ============================================================
// Proxy: /agents/* -> Agent Service
// ============================================================
app.use('/agents', createProxyMiddleware({
  target: AGENT_SERVICE_URL,
  changeOrigin: true,
  pathRewrite: { '^/agents': '/api' },
  timeout: 180000,
  onError: (err, req, res) => {
    console.error(`[Proxy] Agent service error: ${err.message}`);
    res.status(502).json({ error: 'Agent service unavailable' });
  },
}));

// ============================================================
// Proxy: /mcp/* -> MCP Server
// ============================================================
app.use('/mcp', createProxyMiddleware({
  target: MCP_SERVER_URL,
  changeOrigin: true,
  pathRewrite: { '^/mcp': '' },
  timeout: 60000,
  onError: (err, req, res) => {
    console.error(`[Proxy] MCP server error: ${err.message}`);
    res.status(502).json({ error: 'MCP server unavailable' });
  },
}));

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Error handler
app.use((err, req, res, next) => {
  console.error(`[Gateway Error] ${err.message}`);
  res.status(500).json({ error: 'Internal gateway error' });
});

// ============================================================
// HTTP Server + WebSocket
// ============================================================
const server = http.createServer(app);

const wss = new WebSocketServer({ server, path: '/ws' });

wss.on('connection', (ws, req) => {
  console.log(`[WS] Client connected: ${req.url}`);

  const WebSocket = require('ws');
  const backendWsUrl = `ws://${BACKEND_URL.replace('http://', '')}${req.url}`;
  const backendWs = new WebSocket(backendWsUrl);

  backendWs.on('open', () => {
    console.log(`[WS] Backend connection established: ${req.url}`);
  });

  backendWs.on('message', (data) => {
    if (ws.readyState === ws.OPEN) ws.send(data.toString());
  });

  ws.on('message', (data) => {
    if (backendWs.readyState === backendWs.OPEN) backendWs.send(data.toString());
  });

  ws.on('close', () => {
    backendWs.close();
    console.log(`[WS] Client disconnected: ${req.url}`);
  });

  backendWs.on('error', (err) => {
    console.error(`[WS] Backend error: ${err.message}`);
  });

  backendWs.on('close', () => {
    ws.close();
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`API Gateway running on port ${PORT}`);
  console.log(`  Backend: ${BACKEND_URL}`);
  console.log(`  Agent Service: ${AGENT_SERVICE_URL}`);
  console.log(`  MCP Server: ${MCP_SERVER_URL}`);
});
