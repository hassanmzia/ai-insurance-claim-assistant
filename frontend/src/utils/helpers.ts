import { ClaimStatus, Priority } from '../types';

export const formatCurrency = (amount: number | string | null): string => {
  if (amount === null || amount === undefined) return '$0.00';
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);
};

export const formatDate = (dateStr: string): string => {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
};

export const formatDateTime = (dateStr: string): string => {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

export const statusColor = (status: ClaimStatus): string => {
  const colors: Record<string, string> = {
    draft: '#6b7280',
    submitted: '#3b82f6',
    under_review: '#f59e0b',
    ai_processing: '#8b5cf6',
    pending_info: '#f97316',
    approved: '#10b981',
    partially_approved: '#14b8a6',
    denied: '#ef4444',
    appealed: '#ec4899',
    settled: '#06b6d4',
    closed: '#6b7280',
  };
  return colors[status] || '#6b7280';
};

export const statusLabel = (status: string): string => {
  return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
};

export const priorityColor = (priority: Priority): string => {
  const colors: Record<string, string> = {
    low: '#10b981',
    medium: '#f59e0b',
    high: '#f97316',
    urgent: '#ef4444',
  };
  return colors[priority] || '#6b7280';
};

export const fraudScoreColor = (score: number | null): string => {
  if (score === null) return '#6b7280';
  if (score < 0.15) return '#10b981';
  if (score < 0.3) return '#f59e0b';
  if (score < 0.6) return '#f97316';
  return '#ef4444';
};

export const fraudScoreLabel = (score: number | null): string => {
  if (score === null) return 'N/A';
  if (score < 0.15) return 'Low Risk';
  if (score < 0.3) return 'Minor Risk';
  if (score < 0.6) return 'Moderate Risk';
  if (score < 0.8) return 'High Risk';
  return 'Critical Risk';
};
