import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiPlus, FiSearch, FiFilter } from 'react-icons/fi';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Claim, PaginatedResponse } from '../types';
import { formatCurrency, formatDate, statusColor, statusLabel, priorityColor, fraudScoreLabel, fraudScoreColor } from '../utils/helpers';

const ClaimsPage: React.FC = () => {
  const [claims, setClaims] = useState<PaginatedResponse<Claim> | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: '', priority: '', loss_type: '', search: '' });
  const navigate = useNavigate();
  const { user } = useAuth();
  const isStaff = ['admin', 'manager', 'adjuster', 'reviewer', 'agent'].includes(user?.role || '');

  const fetchClaims = (params?: Record<string, any>) => {
    setLoading(true);
    const queryParams: Record<string, any> = {};
    if (filters.status) queryParams.status = filters.status;
    if (filters.priority) queryParams.priority = filters.priority;
    if (filters.loss_type) queryParams.loss_type = filters.loss_type;
    if (filters.search) queryParams.search = filters.search;
    Object.assign(queryParams, params);

    api.getClaims(queryParams)
      .then(setClaims)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchClaims(); }, []); // eslint-disable-line

  const handleFilterChange = (key: string, value: string) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    const queryParams: Record<string, any> = {};
    if (newFilters.status) queryParams.status = newFilters.status;
    if (newFilters.priority) queryParams.priority = newFilters.priority;
    if (newFilters.loss_type) queryParams.loss_type = newFilters.loss_type;
    if (newFilters.search) queryParams.search = newFilters.search;
    setLoading(true);
    api.getClaims(queryParams).then(setClaims).catch(console.error).finally(() => setLoading(false));
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Claims Management</h2>
          <p className="subtitle">{claims?.count || 0} total claims</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/claims/new')}>
          <FiPlus /> New Claim
        </button>
      </div>

      <div className="filter-bar">
        <FiFilter style={{ color: '#6b7280' }} />
        <select className="form-control" value={filters.status} onChange={(e) => handleFilterChange('status', e.target.value)}>
          <option value="">All Statuses</option>
          <option value="submitted">Submitted</option>
          <option value="under_review">Under Review</option>
          <option value="ai_processing">AI Processing</option>
          <option value="approved">Approved</option>
          <option value="denied">Denied</option>
          <option value="settled">Settled</option>
          <option value="pending_info">Pending Info</option>
        </select>
        <select className="form-control" value={filters.priority} onChange={(e) => handleFilterChange('priority', e.target.value)}>
          <option value="">All Priorities</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
        <select className="form-control" value={filters.loss_type} onChange={(e) => handleFilterChange('loss_type', e.target.value)}>
          <option value="">All Types</option>
          <option value="collision">Collision</option>
          <option value="comprehensive">Comprehensive</option>
          <option value="liability">Liability</option>
          <option value="theft">Theft</option>
          <option value="vandalism">Vandalism</option>
          <option value="weather">Weather</option>
        </select>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
          <FiSearch style={{ color: '#9ca3af' }} />
          <input
            className="form-control"
            placeholder="Search claims..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
            style={{ flex: 1 }}
          />
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Claim #</th>
                <th>Claimant</th>
                <th>Policy</th>
                <th>Type</th>
                <th>Status</th>
                {isStaff && <th>Assigned To</th>}
                <th>Priority</th>
                <th>Date of Loss</th>
                <th>Est. Cost</th>
                <th>Fraud Risk</th>
                <th>Docs</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={isStaff ? 11 : 10} style={{ textAlign: 'center', padding: '40px' }}><div className="spinner" style={{ margin: '0 auto' }} /></td></tr>
              ) : claims?.results?.length === 0 ? (
                <tr><td colSpan={isStaff ? 11 : 10} style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>No claims found</td></tr>
              ) : (
                claims?.results?.map((claim) => (
                  <tr key={claim.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/claims/${claim.id}`)}>
                    <td style={{ fontWeight: 600, color: '#1a56db' }}>{claim.claim_number}</td>
                    <td>{claim.claimant_name}</td>
                    <td style={{ fontSize: '13px', color: '#6b7280' }}>{claim.policy_number}</td>
                    <td><span className="badge" style={{ background: '#f3f4f6', color: '#374151' }}>{statusLabel(claim.loss_type)}</span></td>
                    <td>
                      <span className="badge" style={{ background: statusColor(claim.status) + '20', color: statusColor(claim.status) }}>
                        {statusLabel(claim.status)}
                      </span>
                    </td>
                    {isStaff && (
                      <td style={{ fontSize: '13px' }}>
                        {claim.adjuster_name ? (
                          <span style={{ color: '#374151', fontWeight: 500 }}>{claim.adjuster_name}</span>
                        ) : (
                          <span style={{ color: '#d1d5db', fontStyle: 'italic' }}>Unassigned</span>
                        )}
                      </td>
                    )}
                    <td>
                      <span className="badge" style={{ background: priorityColor(claim.priority) + '20', color: priorityColor(claim.priority) }}>
                        {claim.priority.toUpperCase()}
                      </span>
                    </td>
                    <td>{formatDate(claim.date_of_loss)}</td>
                    <td style={{ fontWeight: 500 }}>{formatCurrency(claim.estimated_repair_cost)}</td>
                    <td>
                      {claim.fraud_score !== null ? (
                        <span style={{ color: fraudScoreColor(claim.fraud_score), fontWeight: 600, fontSize: '12px' }}>
                          {fraudScoreLabel(claim.fraud_score)}
                        </span>
                      ) : <span style={{ color: '#9ca3af', fontSize: '12px' }}>--</span>}
                    </td>
                    <td style={{ color: '#6b7280' }}>{claim.document_count || 0}</td>
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

export default ClaimsPage;
