import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ClaimsPage from './pages/ClaimsPage';
import ClaimDetailPage from './pages/ClaimDetailPage';
import NewClaimPage from './pages/NewClaimPage';
import FraudAlertsPage from './pages/FraudAlertsPage';
import AgentsPage from './pages/AgentsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import NotificationsPage from './pages/NotificationsPage';
import PolicyDocumentsPage from './pages/PolicyDocumentsPage';
import './App.css';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading...</p>
      </div>
    );
  }
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

/** Route guard that checks user role. Shows access denied if unauthorized. */
const RoleRoute: React.FC<{ roles: string[]; children: React.ReactNode }> = ({ roles, children }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" />;
  if (!roles.includes(user.role)) {
    return (
      <div style={{ padding: '60px 20px', textAlign: 'center' }}>
        <h2 style={{ color: '#ef4444', marginBottom: '8px' }}>Access Denied</h2>
        <p style={{ color: '#6b7280' }}>You don't have permission to view this page.</p>
        <a href="/" style={{ color: '#1a56db', marginTop: '16px', display: 'inline-block' }}>
          Return to Dashboard
        </a>
      </div>
    );
  }
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
            <Route index element={<DashboardPage />} />
            <Route path="claims" element={<ClaimsPage />} />
            <Route path="claims/new" element={<NewClaimPage />} />
            <Route path="claims/:id" element={<ClaimDetailPage />} />
            <Route path="policy-documents" element={
              <RoleRoute roles={['admin', 'adjuster', 'reviewer']}>
                <PolicyDocumentsPage />
              </RoleRoute>
            } />
            <Route path="fraud-alerts" element={
              <RoleRoute roles={['admin', 'adjuster', 'reviewer']}>
                <FraudAlertsPage />
              </RoleRoute>
            } />
            <Route path="agents" element={
              <RoleRoute roles={['admin']}>
                <AgentsPage />
              </RoleRoute>
            } />
            <Route path="analytics" element={
              <RoleRoute roles={['admin', 'reviewer']}>
                <AnalyticsPage />
              </RoleRoute>
            } />
            <Route path="notifications" element={<NotificationsPage />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
