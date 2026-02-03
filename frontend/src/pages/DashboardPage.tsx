import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement,
  Title, Tooltip, Legend, PointElement, LineElement,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import { FiFileText, FiCheckCircle, FiXCircle, FiClock, FiDollarSign, FiAlertTriangle } from 'react-icons/fi';
import api from '../services/api';
import { DashboardSummary } from '../types';
import { formatCurrency, formatDate, statusColor, statusLabel } from '../utils/helpers';

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend, PointElement, LineElement);

const DashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.getDashboard()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-screen"><div className="spinner" /></div>;
  if (!data) return <div className="empty-state"><h3>Unable to load dashboard</h3></div>;

  const statusChartData = {
    labels: Object.keys(data.claims_by_status).map(statusLabel),
    datasets: [{
      data: Object.values(data.claims_by_status),
      backgroundColor: Object.keys(data.claims_by_status).map((s) => statusColor(s as any)),
      borderWidth: 0,
    }],
  };

  const trendData = {
    labels: data.monthly_trend.map((m) => {
      const d = new Date(m.month);
      return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
    }),
    datasets: [
      {
        label: 'Claims',
        data: data.monthly_trend.map((m) => m.count),
        borderColor: '#1a56db',
        backgroundColor: 'rgba(26,86,219,0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const typeChartData = {
    labels: Object.keys(data.claims_by_type).map(statusLabel),
    datasets: [{
      label: 'Claims by Type',
      data: Object.values(data.claims_by_type),
      backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899'],
      borderWidth: 0,
      borderRadius: 4,
    }],
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p className="subtitle">AI Insurance Claim Processing Overview</p>
        </div>
        <div className="header-actions">
          <button className="btn btn-primary" onClick={() => navigate('/claims/new')}>
            <FiFileText /> New Claim
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#eff6ff', color: '#1a56db' }}><FiFileText /></div>
          <div className="stat-content">
            <div className="stat-value">{data.total_claims}</div>
            <div className="stat-label">Total Claims</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#fef3c7', color: '#f59e0b' }}><FiClock /></div>
          <div className="stat-content">
            <div className="stat-value">{data.pending_claims}</div>
            <div className="stat-label">Pending Claims</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ecfdf5', color: '#10b981' }}><FiCheckCircle /></div>
          <div className="stat-content">
            <div className="stat-value">{data.approved_claims}</div>
            <div className="stat-label">Approved</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#fef2f2', color: '#ef4444' }}><FiXCircle /></div>
          <div className="stat-content">
            <div className="stat-value">{data.denied_claims}</div>
            <div className="stat-label">Denied</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ecfdf5', color: '#10b981' }}><FiDollarSign /></div>
          <div className="stat-content">
            <div className="stat-value">{formatCurrency(data.total_payout)}</div>
            <div className="stat-label">Total Payouts</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#fef2f2', color: '#ef4444' }}><FiAlertTriangle /></div>
          <div className="stat-content">
            <div className="stat-value">{data.fraud_alerts_count}</div>
            <div className="stat-label">Active Fraud Alerts</div>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: '24px' }}>
        <div className="card">
          <div className="card-header"><h3>Claims Trend (12 Months)</h3></div>
          <div className="card-body">
            <Line data={trendData} options={{ responsive: true, plugins: { legend: { display: false } } }} />
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3>Claims by Status</h3></div>
          <div className="card-body" style={{ display: 'flex', justifyContent: 'center' }}>
            <div style={{ maxWidth: '280px' }}>
              <Doughnut data={statusChartData} options={{ responsive: true, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 8, font: { size: 11 } } } } }} />
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><h3>Claims by Type</h3></div>
          <div className="card-body">
            <Bar data={typeChartData} options={{ responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }} />
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <h3>Recent Claims</h3>
            <button className="btn btn-secondary btn-sm" onClick={() => navigate('/claims')}>View All</button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container">
              <table>
                <thead>
                  <tr><th>Claim #</th><th>Claimant</th><th>Status</th><th>Amount</th></tr>
                </thead>
                <tbody>
                  {data.recent_claims.slice(0, 5).map((claim) => (
                    <tr key={claim.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/claims/${claim.id}`)}>
                      <td style={{ fontWeight: 600 }}>{claim.claim_number}</td>
                      <td>{claim.claimant_name}</td>
                      <td>
                        <span className="badge" style={{ background: statusColor(claim.status) + '20', color: statusColor(claim.status) }}>
                          {statusLabel(claim.status)}
                        </span>
                      </td>
                      <td>{formatCurrency(claim.estimated_repair_cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
