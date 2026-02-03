import React, { useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const justRegistered = (location.state as any)?.registered;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h2>ClaimAssist AI</h2>
        <p className="subtitle">AI-Powered Insurance Claim Processing Platform</p>

        {justRegistered && (
          <div style={{
            padding: '10px 16px', marginBottom: '16px', borderRadius: '6px',
            background: '#ecfdf5', color: '#065f46', fontSize: '14px', border: '1px solid #bbf7d0',
          }}>
            Account created successfully! Please sign in.
          </div>
        )}

        {error && <div className="error-msg">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              className="form-control"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              className="form-control"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>
          <button type="submit" className="btn btn-primary btn-lg" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '14px', color: '#6b7280' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ color: '#1a56db', textDecoration: 'none', fontWeight: 600 }}>
            Create Account
          </Link>
        </div>

        <div className="demo-info">
          <strong>Demo Credentials:</strong><br />
          Admin: admin / admin123<br />
          Adjuster: demo / demo123
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
