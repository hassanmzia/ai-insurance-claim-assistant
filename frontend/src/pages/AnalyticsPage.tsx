import React, { useEffect, useState } from 'react';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement,
  Title, Tooltip, Legend,
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import { FiTrendingUp, FiDollarSign, FiPieChart } from 'react-icons/fi';
import api from '../services/api';
import { formatCurrency, statusLabel } from '../utils/helpers';

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend);

const AnalyticsPage: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [period, setPeriod] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getAnalytics(period).then(setData).catch(console.error).finally(() => setLoading(false));
  }, [period]);

  if (loading) return <div className="loading-screen"><div className="spinner" /></div>;
  if (!data) return <div className="empty-state"><h3>Analytics unavailable</h3></div>;

  const statusData = {
    labels: Object.keys(data.by_status || {}).map(statusLabel),
    datasets: [{
      data: Object.values(data.by_status || {}),
      backgroundColor: ['#3b82f6', '#f59e0b', '#8b5cf6', '#10b981', '#ef4444', '#06b6d4', '#f97316', '#ec4899'],
      borderWidth: 0,
    }],
  };

  const typeData = {
    labels: Object.keys(data.by_type || {}).map(statusLabel),
    datasets: [{
      label: 'Claims',
      data: Object.values(data.by_type || {}),
      backgroundColor: '#3b82f6',
      borderRadius: 4,
    }],
  };

  const priorityData = {
    labels: Object.keys(data.by_priority || {}).map((p) => p.toUpperCase()),
    datasets: [{
      data: Object.values(data.by_priority || {}),
      backgroundColor: ['#10b981', '#f59e0b', '#f97316', '#ef4444'],
      borderWidth: 0,
    }],
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Analytics & Reports</h2>
          <p className="subtitle">Claims performance and operational metrics</p>
        </div>
        <select className="form-control" style={{ width: 'auto' }} value={period} onChange={(e) => setPeriod(Number(e.target.value))}>
          <option value={7}>Last 7 Days</option>
          <option value={30}>Last 30 Days</option>
          <option value={90}>Last 90 Days</option>
          <option value={365}>Last Year</option>
        </select>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#eff6ff', color: '#1a56db' }}><FiTrendingUp /></div>
          <div className="stat-content">
            <div className="stat-value">{data.total_claims}</div>
            <div className="stat-label">Claims ({period}d)</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#fef3c7', color: '#f59e0b' }}><FiDollarSign /></div>
          <div className="stat-content">
            <div className="stat-value">{formatCurrency(data.total_estimated)}</div>
            <div className="stat-label">Total Estimated</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ecfdf5', color: '#10b981' }}><FiDollarSign /></div>
          <div className="stat-content">
            <div className="stat-value">{formatCurrency(data.total_approved)}</div>
            <div className="stat-label">Total Approved</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ede9fe', color: '#7c3aed' }}><FiDollarSign /></div>
          <div className="stat-content">
            <div className="stat-value">{formatCurrency(data.total_settled)}</div>
            <div className="stat-label">Total Settled</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#fef2f2', color: '#ef4444' }}><FiPieChart /></div>
          <div className="stat-content">
            <div className="stat-value">{data.fraud_alerts}</div>
            <div className="stat-label">Fraud Alerts</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#f0fdf4', color: '#16a34a' }}><FiTrendingUp /></div>
          <div className="stat-content">
            <div className="stat-value">{data.avg_fraud_score !== null ? `${(data.avg_fraud_score * 100).toFixed(0)}%` : 'N/A'}</div>
            <div className="stat-label">Avg Fraud Score</div>
          </div>
        </div>
      </div>

      <div className="grid-3" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
        <div className="card">
          <div className="card-header"><h3>By Status</h3></div>
          <div className="card-body" style={{ display: 'flex', justifyContent: 'center' }}>
            <div style={{ maxWidth: '250px' }}>
              <Doughnut data={statusData} options={{ plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 6, font: { size: 10 } } } } }} />
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3>By Type</h3></div>
          <div className="card-body">
            <Bar data={typeData} options={{ responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }} />
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h3>By Priority</h3></div>
          <div className="card-body" style={{ display: 'flex', justifyContent: 'center' }}>
            <div style={{ maxWidth: '250px' }}>
              <Doughnut data={priorityData} options={{ plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 6, font: { size: 10 } } } } }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;
