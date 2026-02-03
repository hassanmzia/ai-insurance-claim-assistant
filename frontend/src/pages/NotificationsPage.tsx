import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiBell, FiCheck, FiCheckCircle } from 'react-icons/fi';
import toast from 'react-hot-toast';
import api from '../services/api';
import { Notification, PaginatedResponse } from '../types';
import { formatDateTime, statusLabel } from '../utils/helpers';

const typeColors: Record<string, string> = {
  claim_update: '#3b82f6',
  claim_approved: '#10b981',
  claim_denied: '#ef4444',
  document_required: '#f59e0b',
  fraud_alert: '#ef4444',
  assignment: '#8b5cf6',
  settlement: '#06b6d4',
  system: '#6b7280',
};

const NotificationsPage: React.FC = () => {
  const [notifications, setNotifications] = useState<PaginatedResponse<Notification> | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.getNotifications().then(setNotifications).catch(console.error).finally(() => setLoading(false));
  }, []);

  const markRead = async (id: string) => {
    await api.markNotificationRead(id);
    setNotifications((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        results: prev.results.map((n) => n.id === id ? { ...n, is_read: true } : n),
      };
    });
  };

  const markAllRead = async () => {
    await api.markAllNotificationsRead();
    toast.success('All notifications marked as read');
    setNotifications((prev) => {
      if (!prev) return prev;
      return { ...prev, results: prev.results.map((n) => ({ ...n, is_read: true })) };
    });
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Notifications</h2>
          <p className="subtitle">{notifications?.results?.filter((n) => !n.is_read).length || 0} unread</p>
        </div>
        <button className="btn btn-secondary" onClick={markAllRead}>
          <FiCheckCircle /> Mark All Read
        </button>
      </div>

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div style={{ padding: '40px', textAlign: 'center' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
          ) : !notifications?.results?.length ? (
            <div className="empty-state">
              <FiBell style={{ fontSize: '48px' }} />
              <h3>No notifications</h3>
              <p>You're all caught up</p>
            </div>
          ) : (
            notifications.results.map((notif) => (
              <div
                key={notif.id}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: '14px',
                  padding: '14px 20px',
                  borderBottom: '1px solid #f3f4f6',
                  background: notif.is_read ? 'white' : '#fafafe',
                  cursor: 'pointer',
                }}
                onClick={() => {
                  markRead(notif.id);
                  if (notif.claim) navigate(`/claims/${notif.claim}`);
                }}
              >
                <div style={{
                  width: '10px', height: '10px', borderRadius: '50%',
                  marginTop: '6px', flexShrink: 0,
                  background: notif.is_read ? '#e5e7eb' : typeColors[notif.notification_type] || '#3b82f6',
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <strong style={{ fontSize: '14px' }}>{notif.title}</strong>
                    <span style={{ fontSize: '12px', color: '#9ca3af', whiteSpace: 'nowrap', marginLeft: '12px' }}>
                      {formatDateTime(notif.created_at)}
                    </span>
                  </div>
                  <p style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>{notif.message}</p>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                    <span className="badge" style={{ background: (typeColors[notif.notification_type] || '#6b7280') + '20', color: typeColors[notif.notification_type] || '#6b7280' }}>
                      {statusLabel(notif.notification_type)}
                    </span>
                    {notif.claim_number && (
                      <span style={{ fontSize: '12px', color: '#1a56db' }}>{notif.claim_number}</span>
                    )}
                  </div>
                </div>
                {!notif.is_read && (
                  <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); markRead(notif.id); }}>
                    <FiCheck />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default NotificationsPage;
