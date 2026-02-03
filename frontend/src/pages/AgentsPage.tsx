import React, { useEffect, useState } from 'react';
import { FiCpu, FiTool, FiDatabase, FiGlobe } from 'react-icons/fi';
import api from '../services/api';
import { AgentCard } from '../types';

const AgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentCard[]>([]);
  const [mcpTools, setMcpTools] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState('agents');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getAgents().catch(() => ({ agents: [] })),
      api.getMCPTools().catch(() => ({ tools: [] })),
    ]).then(([agentData, toolData]) => {
      setAgents(agentData.agents || []);
      setMcpTools(toolData.tools || []);
    }).finally(() => setLoading(false));
  }, []);

  const agentIcons: Record<string, React.ReactNode> = {
    claim_parser: <FiFileIcon />,
    policy_retriever: <FiDatabase />,
    recommendation: <FiCpu />,
    fraud_detector: <FiShieldIcon />,
    decision_maker: <FiCheckIcon />,
    document_analyzer: <FiTool />,
  };

  if (loading) return <div className="loading-screen"><div className="spinner" /></div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>AI Agents & Tools</h2>
          <p className="subtitle">Multi-agent system with MCP and A2A protocol integration</p>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab ${activeTab === 'agents' ? 'active' : ''}`} onClick={() => setActiveTab('agents')}>
          <FiCpu style={{ marginRight: '6px' }} /> A2A Agents ({agents.length})
        </button>
        <button className={`tab ${activeTab === 'mcp' ? 'active' : ''}`} onClick={() => setActiveTab('mcp')}>
          <FiTool style={{ marginRight: '6px' }} /> MCP Tools ({mcpTools.length})
        </button>
      </div>

      {activeTab === 'agents' && (
        <div className="grid-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
          {agents.length > 0 ? agents.map((agent) => (
            <div key={agent.agent_id} className="agent-card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: '#eff6ff', color: '#1a56db', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <FiCpu />
                </div>
                <div>
                  <h4>{agent.name}</h4>
                  <span style={{ fontSize: '11px', color: '#9ca3af' }}>Protocol: {agent.protocol}</span>
                </div>
                <span className="badge" style={{ marginLeft: 'auto', background: '#ecfdf5', color: '#10b981' }}>{agent.status}</span>
              </div>
              <p>{agent.description}</p>
              <div>
                <span style={{ fontSize: '12px', fontWeight: 600, color: '#6b7280' }}>Capabilities:</span>
                <div className="capability-list" style={{ marginTop: '6px' }}>
                  {agent.capabilities?.map((cap, i) => (
                    <span key={i} className="capability-tag">{cap.action}</span>
                  ))}
                </div>
              </div>
            </div>
          )) : (
            <div className="empty-state" style={{ gridColumn: '1 / -1' }}>
              <FiCpu style={{ fontSize: '48px' }} />
              <h3>No agents available</h3>
              <p>Agent service may not be running</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'mcp' && (
        <div>
          <div className="card" style={{ marginBottom: '20px' }}>
            <div className="card-header">
              <h3>MCP Server Information</h3>
              <span className="badge" style={{ background: '#ecfdf5', color: '#10b981' }}>Connected</span>
            </div>
            <div className="card-body">
              <div className="detail-grid">
                <div className="detail-item"><label>Protocol</label><div className="value">Model Context Protocol (MCP) 2024-11-05</div></div>
                <div className="detail-item"><label>Server</label><div className="value">insurance-claims-mcp v1.0.0</div></div>
                <div className="detail-item"><label>Capabilities</label><div className="value">Tools, Resources, Prompts</div></div>
                <div className="detail-item"><label>Endpoint</label><div className="value">/mcp/</div></div>
              </div>
            </div>
          </div>

          <div className="grid-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
            {mcpTools.map((tool: any, i: number) => (
              <div key={i} className="agent-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: '#faf5ff', color: '#7c3aed', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <FiTool />
                  </div>
                  <h4>{tool.name}</h4>
                </div>
                <p>{tool.description}</p>
                {tool.inputSchema?.properties && (
                  <div style={{ marginTop: '8px' }}>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: '#6b7280' }}>Parameters:</span>
                    <div className="capability-list" style={{ marginTop: '6px' }}>
                      {Object.keys(tool.inputSchema.properties).map((param: string) => (
                        <span key={param} className="capability-tag">{param}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Simple inline icon components
const FiFileIcon = () => <FiCpu />;
const FiShieldIcon = () => <FiGlobe />;
const FiCheckIcon = () => <FiCpu />;

export default AgentsPage;
