import React, { useEffect, useState } from 'react';
import { FiAlertTriangle, FiShield } from 'react-icons/fi';
import toast from 'react-hot-toast';
import api from '../services/api';
import { FraudAlert, PaginatedResponse } from '../types';
import { formatDateTime, statusLabel } from '../utils/helpers';

const severityColors: Record<string, string> = {
  low: '#10b981', medium: '#f59e0b', high: '#f97316', critical: '#ef4444',
};

const FraudAlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<PaginatedResponse<FraudAlert> | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  const fetchAlerts = () => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (filter) params.severity = filter;
    api.getFraudAlerts(params).then(setAlerts).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { fetchAlerts(); }, [filter]); // eslint-disable-line

  const handleResolve = async (id: string, resolution: string) => {
    try {
      await api.resolveFraudAlert(id, resolution, '');
      toast.success('Alert resolved');
      fetchAlerts();
    } catch {
      toast.error('Failed to resolve alert');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Fraud Alerts</h2>
          <p className="subtitle">AI-powered fraud detection and monitoring</p>
        </div>
      </div>

      <div className="filter-bar">
        <FiShield style={{ color: '#6b7280' }} />
        <select className="form-control" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All Severities</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Claim</th>
                <th>Alert Type</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Description</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} style={{ textAlign: 'center', padding: '40px' }}><div className="spinner" style={{ margin: '0 auto' }} /></td></tr>
              ) : !alerts?.results?.length ? (
                <tr><td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
                  <FiAlertTriangle style={{ fontSize: '24px', marginBottom: '8px', display: 'block', margin: '0 auto 8px' }} />
                  No fraud alerts found
                </td></tr>
              ) : (
                alerts.results.map((alert) => (
                  <tr key={alert.id}>
                    <td style={{ fontWeight: 600, color: '#1a56db' }}>{alert.claim_number}</td>
                    <td>{alert.alert_type}</td>
                    <td>
                      <span className="badge" style={{ background: severityColors[alert.severity] + '20', color: severityColors[alert.severity] }}>
                        {alert.severity.toUpperCase()}
                      </span>
                    </td>
                    <td><span className="badge" style={{ background: '#f3f4f6', color: '#374151' }}>{statusLabel(alert.status)}</span></td>
                    <td style={{ fontWeight: 600 }}>{(alert.ai_confidence * 100).toFixed(0)}%</td>
                    <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{alert.description}</td>
                    <td style={{ fontSize: '13px', color: '#6b7280' }}>{formatDateTime(alert.created_at)}</td>
                    <td>
                      {alert.status === 'open' && (
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button className="btn btn-success btn-sm" onClick={() => handleResolve(alert.id, 'resolved')}>Legit</button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleResolve(alert.id, 'confirmed')}>Fraud</button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default FraudAlertsPage;
