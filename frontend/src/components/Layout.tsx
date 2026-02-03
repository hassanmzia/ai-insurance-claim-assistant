import React, { useEffect, useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  FiHome, FiFileText, FiAlertTriangle, FiCpu, FiBarChart2,
  FiBell, FiLogOut, FiPlusCircle,
} from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    api.getNotifications()
      .then((res) => {
        const unread = res.results?.filter((n) => !n.is_read).length || 0;
        setUnreadCount(unread);
      })
      .catch(() => {});
  }, [location]);

  const navItems = [
    { path: '/', icon: <FiHome />, label: 'Dashboard' },
    { path: '/claims', icon: <FiFileText />, label: 'Claims' },
    { path: '/claims/new', icon: <FiPlusCircle />, label: 'New Claim' },
    { path: '/fraud-alerts', icon: <FiAlertTriangle />, label: 'Fraud Alerts' },
    { path: '/agents', icon: <FiCpu />, label: 'AI Agents' },
    { path: '/analytics', icon: <FiBarChart2 />, label: 'Analytics' },
    { path: '/notifications', icon: <FiBell />, label: 'Notifications', badge: unreadCount },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const initials = user
    ? `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase() || user.username[0].toUpperCase()
    : '?';

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>ClaimAssist AI</h1>
          <p>Multi-Agent Insurance Platform</p>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <button
              key={item.path}
              className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
              onClick={() => navigate(item.path)}
            >
              {item.icon}
              <span>{item.label}</span>
              {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">{initials}</div>
            <div className="user-details">
              <div className="name">{user?.first_name} {user?.last_name}</div>
              <div className="role">{user?.role}</div>
            </div>
            <button className="logout-btn" onClick={handleLogout} title="Logout">
              <FiLogOut />
            </button>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
