import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  FiArrowLeft, FiCpu, FiAlertTriangle, FiCheckCircle, FiXCircle,
  FiClock, FiDollarSign, FiFileText, FiMessageSquare, FiInfo,
  FiSend, FiRotateCw,
} from 'react-icons/fi';
import toast from 'react-hot-toast';
import api from '../services/api';
import { Claim } from '../types';
import {
  formatCurrency, formatDate, formatDateTime, statusColor, statusLabel,
  priorityColor, fraudScoreColor, fraudScoreLabel,
} from '../utils/helpers';

const agentColors: Record<string, string> = {
  ClaimParser: '#6366f1',
  PolicyRetriever: '#0891b2',
  FraudDetector: '#dc2626',
  RecommendationAgent: '#059669',
  DecisionMaker: '#7c3aed',
  Orchestrator: '#ea580c',
};

const ClaimDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [claim, setClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('details');
  const [noteContent, setNoteContent] = useState('');
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const navigate = useNavigate();

  useEffect(() => {
    if (id) {
      api.getClaim(id).then(setClaim).catch(console.error).finally(() => setLoading(false));
    }
  }, [id]);

  const handleAIProcess = async (type: string = 'full') => {
    if (!id) return;
    setProcessing(true);
    try {
      const result = await api.processClaim(id, type);
      toast.success(`AI processing complete: ${statusLabel(result.status)}`);
      api.getClaim(id).then(setClaim);
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Processing failed');
    } finally {
      setProcessing(false);
    }
  };

  const handleStatusUpdate = async (status: string) => {
    if (!id) return;
    try {
      await api.updateClaimStatus(id, status);
      toast.success(`Status updated to ${statusLabel(status)}`);
      api.getClaim(id).then(setClaim);
    } catch (err: any) {
      toast.error('Failed to update status');
    }
  };

  const handleAddNote = async () => {
    if (!id || !noteContent.trim()) return;
    try {
      await api.addClaimNote(id, noteContent);
      setNoteContent('');
      toast.success('Note added');
      api.getClaim(id).then(setClaim);
    } catch {
      toast.error('Failed to add note');
    }
  };

  const toggleStep = (index: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  if (loading) return <div className="loading-screen"><div className="spinner" /></div>;
  if (!claim) return <div className="empty-state"><h3>Claim not found</h3></div>;

  const aiDecision = claim.ai_recommendation?.ai_decision;

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/claims')}>
            <FiArrowLeft /> Back
          </button>
          <div>
            <h2>{claim.claim_number}</h2>
            <p className="subtitle">{claim.claimant_name} &middot; {claim.policy_number}</p>
          </div>
        </div>
        <div className="header-actions">
          {/* AI Process - available for submitted, under_review, pending_info */}
          {['submitted', 'under_review', 'pending_info'].includes(claim.status) && (
            <button
              className="btn btn-primary"
              onClick={() => handleAIProcess('full')}
              disabled={processing || claim.status === 'ai_processing'}
            >
              <FiCpu /> {processing ? 'Processing...' : claim.ai_recommendation ? 'Re-process AI' : 'AI Process'}
            </button>
          )}

          {/* Approve / Deny - available when under_review */}
          {claim.status === 'under_review' && (
            <>
              <button className="btn btn-success" onClick={() => handleStatusUpdate('approved')}>
                <FiCheckCircle /> Approve
              </button>
              <button className="btn btn-danger" onClick={() => handleStatusUpdate('denied')}>
                <FiXCircle /> Deny
              </button>
              <button className="btn btn-secondary" onClick={() => handleStatusUpdate('pending_info')}>
                <FiInfo /> Request Info
              </button>
            </>
          )}

          {/* Settle - available when approved */}
          {claim.status === 'approved' && (
            <button className="btn btn-success" onClick={() => handleStatusUpdate('settled')}>
              <FiDollarSign /> Settle
            </button>
          )}

          {/* Resubmit - available when pending_info */}
          {claim.status === 'pending_info' && (
            <button className="btn btn-secondary" onClick={() => handleStatusUpdate('submitted')}>
              <FiSend /> Mark Info Received
            </button>
          )}

          {/* Appeal - available when denied */}
          {claim.status === 'denied' && (
            <button className="btn btn-secondary" onClick={() => handleStatusUpdate('appealed')}>
              <FiRotateCw /> Appeal
            </button>
          )}

          {/* Re-open appeal as under_review */}
          {claim.status === 'appealed' && (
            <button className="btn btn-primary" onClick={() => handleStatusUpdate('under_review')}>
              <FiCpu /> Review Appeal
            </button>
          )}
        </div>
      </div>

      {/* AI Decision Banner */}
      {claim.status === 'under_review' && aiDecision && (
        <div style={{
          padding: '12px 20px', borderRadius: '8px', marginBottom: '16px',
          display: 'flex', alignItems: 'center', gap: '12px',
          background: aiDecision === 'approve' ? '#ecfdf5' : '#fef2f2',
          border: `1px solid ${aiDecision === 'approve' ? '#10b981' : '#ef4444'}`,
        }}>
          <FiCpu style={{ color: aiDecision === 'approve' ? '#10b981' : '#ef4444', fontSize: '20px' }} />
          <div>
            <strong style={{ color: aiDecision === 'approve' ? '#065f46' : '#991b1b' }}>
              AI Recommends: {aiDecision === 'approve' ? 'APPROVE' : 'DENY'}
            </strong>
            <span style={{ color: '#6b7280', marginLeft: '12px', fontSize: '13px' }}>
              Awaiting human reviewer decision
            </span>
          </div>
        </div>
      )}

      {/* Status bar */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: statusColor(claim.status) + '20', color: statusColor(claim.status) }}><FiFileText /></div>
          <div className="stat-content">
            <div className="stat-value" style={{ fontSize: '16px' }}>{statusLabel(claim.status)}</div>
            <div className="stat-label">Status</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: priorityColor(claim.priority) + '20', color: priorityColor(claim.priority) }}><FiAlertTriangle /></div>
          <div className="stat-content">
            <div className="stat-value" style={{ fontSize: '16px' }}>{claim.priority.toUpperCase()}</div>
            <div className="stat-label">Priority</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#eff6ff', color: '#1a56db' }}><FiDollarSign /></div>
          <div className="stat-content">
            <div className="stat-value" style={{ fontSize: '16px' }}>{formatCurrency(claim.estimated_repair_cost)}</div>
            <div className="stat-label">Est. Cost</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ecfdf5', color: '#10b981' }}><FiDollarSign /></div>
          <div className="stat-content">
            <div className="stat-value" style={{ fontSize: '16px' }}>{formatCurrency(claim.settlement_amount)}</div>
            <div className="stat-label">Settlement</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: (claim.fraud_score !== null ? fraudScoreColor(claim.fraud_score) : '#6b7280') + '20', color: claim.fraud_score !== null ? fraudScoreColor(claim.fraud_score) : '#6b7280' }}>
            <FiAlertTriangle />
          </div>
          <div className="stat-content">
            <div className="stat-value" style={{ fontSize: '16px' }}>{claim.fraud_score !== null ? `${(claim.fraud_score * 100).toFixed(0)}%` : 'N/A'}</div>
            <div className="stat-label">Fraud Score</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {['details', 'ai_results', 'processing_log', 'notes', 'audit'].map((tab) => (
          <button key={tab} className={`tab ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
            {statusLabel(tab)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'details' && (
        <div className="grid-2">
          <div className="card">
            <div className="card-header"><h3>Claim Information</h3></div>
            <div className="card-body">
              <div className="detail-grid">
                <div className="detail-item"><label>Loss Type</label><div className="value">{statusLabel(claim.loss_type)}</div></div>
                <div className="detail-item"><label>Date of Loss</label><div className="value">{formatDate(claim.date_of_loss)}</div></div>
                <div className="detail-item"><label>Date Reported</label><div className="value">{formatDate(claim.date_reported)}</div></div>
                <div className="detail-item"><label>Location</label><div className="value">{claim.loss_location || 'Not specified'}</div></div>
                <div className="detail-item"><label>Third Party</label><div className="value">{claim.third_party_involved ? 'Yes' : 'No'}</div></div>
                <div className="detail-item"><label>Police Report</label><div className="value">{claim.police_report_number || 'None'}</div></div>
                <div className="detail-item"><label>Adjuster</label><div className="value">{claim.adjuster_name || 'Unassigned'}</div></div>
                <div className="detail-item"><label>Deductible</label><div className="value">{formatCurrency(claim.deductible_applied)}</div></div>
              </div>
              <div style={{ marginTop: '16px' }}>
                <label style={{ fontSize: '12px', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Loss Description</label>
                <p style={{ marginTop: '4px', fontSize: '14px', lineHeight: '1.6' }}>{claim.loss_description}</p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><h3>Vehicle Details</h3></div>
            <div className="card-body">
              {claim.vehicle_details && Object.entries(claim.vehicle_details).map(([key, value]) => (
                <div key={key} className="detail-item" style={{ marginBottom: '12px' }}>
                  <label>{statusLabel(key)}</label>
                  <div className="value">{String(value)}</div>
                </div>
              ))}
              {(!claim.vehicle_details || Object.keys(claim.vehicle_details).length === 0) && (
                <p style={{ color: '#9ca3af' }}>No vehicle details available</p>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'ai_results' && (
        <div className="grid-2">
          <div className="card">
            <div className="card-header">
              <h3>AI Recommendation</h3>
              {aiDecision && (
                <span className="badge" style={{
                  background: aiDecision === 'approve' ? '#ecfdf5' : '#fef2f2',
                  color: aiDecision === 'approve' ? '#059669' : '#dc2626',
                  fontSize: '13px', padding: '4px 12px',
                }}>
                  AI: {aiDecision === 'approve' ? 'Approve' : 'Deny'}
                </span>
              )}
            </div>
            <div className="card-body">
              {claim.ai_recommendation && Object.keys(claim.ai_recommendation).length > 0 ? (
                <div className="detail-grid">
                  <div className="detail-item"><label>Policy Section</label><div className="value">{claim.ai_recommendation.policy_section}</div></div>
                  <div className="detail-item"><label>Deductible</label><div className="value">{formatCurrency(claim.ai_recommendation.deductible)}</div></div>
                  <div className="detail-item"><label>Settlement</label><div className="value">{formatCurrency(claim.ai_recommendation.settlement_amount)}</div></div>
                  <div className="detail-item" style={{ gridColumn: '1 / -1' }}>
                    <label>Summary</label>
                    <div className="value" style={{ lineHeight: '1.6' }}>{claim.ai_recommendation.recommendation_summary}</div>
                  </div>
                </div>
              ) : (
                <div className="empty-state" style={{ padding: '40px' }}>
                  <FiCpu style={{ fontSize: '32px' }} />
                  <p>No AI recommendation yet. Click "AI Process" to analyze this claim.</p>
                </div>
              )}
            </div>
          </div>
          <div className="card">
            <div className="card-header"><h3>Fraud Analysis</h3></div>
            <div className="card-body">
              {claim.fraud_score !== null ? (
                <>
                  <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <div style={{ fontSize: '48px', fontWeight: 700, color: fraudScoreColor(claim.fraud_score) }}>
                      {(claim.fraud_score * 100).toFixed(0)}%
                    </div>
                    <div style={{ color: fraudScoreColor(claim.fraud_score), fontWeight: 600 }}>
                      {fraudScoreLabel(claim.fraud_score)}
                    </div>
                  </div>
                  {claim.fraud_flags && claim.fraud_flags.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: '14px', marginBottom: '8px' }}>Fraud Indicators</h4>
                      {claim.fraud_flags.map((flag, i) => (
                        <div key={i} style={{
                          padding: '8px 12px', marginBottom: '8px',
                          background: flag.severity === 'high' ? '#fef2f2' : flag.severity === 'medium' ? '#fef3c7' : '#f0fdf4',
                          borderRadius: '6px', fontSize: '13px',
                        }}>
                          <strong>{flag.indicator}</strong>: {flag.description}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-state" style={{ padding: '40px' }}>
                  <FiAlertTriangle style={{ fontSize: '32px' }} />
                  <p>No fraud analysis yet.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'processing_log' && (
        <div className="card">
          <div className="card-header">
            <h3>AI Agent Processing Pipeline</h3>
            {claim.ai_processing_log && claim.ai_processing_log.length > 0 && (
              <span style={{ fontSize: '13px', color: '#6b7280' }}>
                {claim.ai_processing_log.length} agents executed
              </span>
            )}
          </div>
          <div className="card-body">
            {claim.ai_processing_log && claim.ai_processing_log.length > 0 ? (
              <div className="processing-steps">
                {claim.ai_processing_log.map((entry, i) => {
                  const color = agentColors[entry.agent] || '#6b7280';
                  const isExpanded = expandedSteps.has(i);
                  return (
                    <div key={i} style={{ marginBottom: '4px' }}>
                      <div
                        className={`processing-step ${entry.status}`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => toggleStep(i)}
                      >
                        <div style={{
                          width: '28px', height: '28px', borderRadius: '50%',
                          background: entry.status === 'completed' ? '#ecfdf5' : '#fef2f2',
                          color: entry.status === 'completed' ? '#10b981' : '#ef4444',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: '12px', fontWeight: 700, flexShrink: 0,
                        }}>
                          {entry.status === 'completed' ? <FiCheckCircle /> : <FiClock />}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontWeight: 600, fontSize: '14px' }}>
                              Step {i + 1}: {statusLabel(entry.step)}
                            </span>
                            <span className="badge" style={{
                              background: color + '18', color, fontSize: '11px', padding: '2px 8px',
                            }}>
                              {entry.agent}
                            </span>
                          </div>
                          <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>
                            {entry.result_summary}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right', flexShrink: 0 }}>
                          {entry.duration_ms && (
                            <div style={{ fontSize: '12px', color: '#6b7280' }}>
                              {entry.duration_ms}ms
                            </div>
                          )}
                          <div style={{ fontSize: '10px', color: '#9ca3af' }}>
                            {isExpanded ? '▲' : '▼'}
                          </div>
                        </div>
                      </div>
                      {isExpanded && (
                        <div style={{
                          margin: '0 0 0 40px', padding: '12px 16px',
                          background: '#f8fafc', borderRadius: '0 0 8px 8px',
                          border: '1px solid #e2e8f0', borderTop: 'none',
                          fontSize: '13px',
                        }}>
                          <div style={{ marginBottom: '8px' }}>
                            <strong style={{ color }}>Agent: {entry.agent}</strong>
                            <span style={{ color: '#6b7280', marginLeft: '12px' }}>
                              Status: {entry.status} | Duration: {entry.duration_ms || 'N/A'}ms
                            </span>
                          </div>
                          <div style={{
                            background: '#1e293b', color: '#e2e8f0', padding: '12px',
                            borderRadius: '6px', fontFamily: 'monospace', fontSize: '12px',
                            lineHeight: '1.6', whiteSpace: 'pre-wrap',
                          }}>
                            <span style={{ color: '#94a3b8' }}>{'>'} Agent </span>
                            <span style={{ color: '#60a5fa' }}>{entry.agent}</span>
                            <span style={{ color: '#94a3b8' }}> received task: </span>
                            <span style={{ color: '#fbbf24' }}>{statusLabel(entry.step)}</span>
                            {'\n'}
                            <span style={{ color: '#94a3b8' }}>{'>'} Processing...</span>
                            {'\n'}
                            <span style={{ color: '#94a3b8' }}>{'>'} Result: </span>
                            <span style={{ color: '#4ade80' }}>{entry.result_summary}</span>
                            {'\n'}
                            <span style={{ color: '#94a3b8' }}>{'>'} Completed in </span>
                            <span style={{ color: '#fb923c' }}>{entry.duration_ms}ms</span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
                {/* Total summary */}
                <div style={{
                  padding: '12px 16px', background: '#f0fdf4', borderRadius: '8px',
                  border: '1px solid #bbf7d0', marginTop: '8px',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <span style={{ fontWeight: 600, color: '#166534' }}>
                    Pipeline Complete
                  </span>
                  <span style={{ color: '#166534', fontSize: '13px' }}>
                    Total: {claim.ai_processing_log.reduce((sum, e) => sum + (e.duration_ms || 0), 0).toLocaleString()}ms
                    {' | '}{claim.ai_processing_log.filter(e => e.status === 'completed').length}/{claim.ai_processing_log.length} steps completed
                  </span>
                </div>
              </div>
            ) : (
              <div className="empty-state" style={{ padding: '40px' }}>
                <FiCpu style={{ fontSize: '32px' }} />
                <p>No processing log available. Run AI processing to see the agent pipeline.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'notes' && (
        <div className="card">
          <div className="card-header"><h3>Notes & Comments</h3></div>
          <div className="card-body">
            <div style={{ marginBottom: '20px', display: 'flex', gap: '12px' }}>
              <textarea
                className="form-control"
                placeholder="Add a note..."
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
                style={{ flex: 1 }}
              />
              <button className="btn btn-primary" onClick={handleAddNote} disabled={!noteContent.trim()}>
                <FiMessageSquare /> Add
              </button>
            </div>
            {claim.notes && claim.notes.length > 0 ? (
              <div className="timeline">
                {claim.notes.map((note) => (
                  <div key={note.id} className="timeline-item">
                    <div className="time">
                      {note.author_name} &middot; {formatDateTime(note.created_at)}
                      {note.is_ai_generated && <span className="badge" style={{ marginLeft: '8px', background: '#ede9fe', color: '#7c3aed' }}>AI</span>}
                    </div>
                    <div className="content">{note.content}</div>
                  </div>
                ))}
              </div>
            ) : <p style={{ color: '#9ca3af', textAlign: 'center' }}>No notes yet</p>}
          </div>
        </div>
      )}

      {activeTab === 'audit' && (
        <div className="card">
          <div className="card-header"><h3>Audit Trail</h3></div>
          <div className="card-body">
            {claim.audit_logs && claim.audit_logs.length > 0 ? (
              <div className="timeline">
                {claim.audit_logs.map((log) => {
                  const actionColors: Record<string, string> = {
                    created: '#3b82f6', assigned: '#8b5cf6', status_change: '#f59e0b',
                    ai_processed: '#6366f1', fraud_check: '#ef4444', approved: '#10b981',
                    denied: '#ef4444', settled: '#059669', document_added: '#0891b2',
                    note_added: '#6b7280',
                  };
                  const color = actionColors[log.action] || '#6b7280';
                  return (
                    <div key={log.id} className="timeline-item">
                      <div className="time">
                        <span className="badge" style={{ background: color + '18', color, marginRight: '8px' }}>
                          {statusLabel(log.action)}
                        </span>
                        {log.user_name} &middot; {formatDateTime(log.timestamp)}
                      </div>
                      <div className="content">
                        {log.action === 'status_change' && log.old_value && log.new_value && (
                          <span>
                            Status changed from <strong>{statusLabel(log.old_value.status)}</strong> to{' '}
                            <strong>{statusLabel(log.new_value.status)}</strong>
                          </span>
                        )}
                        {log.action === 'ai_processed' && log.details && (
                          <span>
                            AI processing completed
                            {log.details.ai_recommendation && (
                              <> &mdash; Recommendation: <strong>{log.details.ai_recommendation}</strong></>
                            )}
                            {log.details.fraud_score != null && (
                              <> | Fraud score: <strong>{Math.round(log.details.fraud_score * 100)}%</strong></>
                            )}
                          </span>
                        )}
                        {log.action === 'approved' && (
                          <span>
                            Claim approved
                            {log.details?.approved_amount > 0 && (
                              <> &mdash; Amount: <strong>${Number(log.details.approved_amount).toLocaleString()}</strong></>
                            )}
                          </span>
                        )}
                        {log.action === 'denied' && <span>Claim denied</span>}
                        {log.action === 'settled' && <span>Claim settled and payment processed</span>}
                        {log.action === 'assigned' && log.details && (
                          <span>Assigned to <strong>{log.details.assigned_to || 'adjuster'}</strong></span>
                        )}
                        {log.action === 'created' && <span>Claim submitted via {log.details?.source || 'portal'}</span>}
                        {log.action === 'fraud_check' && log.details && (
                          <span>
                            Fraud check by <strong>{log.details.agent || 'FraudDetector'}</strong>
                            {' '}&mdash; Score: <strong>{Math.round((log.details.fraud_score || 0) * 100)}%</strong>
                          </span>
                        )}
                        {log.action === 'document_added' && <span>Document uploaded: {log.details?.filename}</span>}
                        {log.action === 'note_added' && <span>Note added to claim</span>}
                        {log.details?.notes && (
                          <div style={{ marginTop: '4px', fontSize: '12px', color: '#6b7280', fontStyle: 'italic' }}>
                            Note: {log.details.notes}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : <p style={{ color: '#9ca3af', textAlign: 'center' }}>No audit logs</p>}
          </div>
        </div>
      )}
    </div>
  );
};

export default ClaimDetailPage;
