import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../utils/api';
import './Login.css';

const Login = ({ switchToRegister, onLoginSuccess }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await api.post('/auth/login', { email, password });
      login(data.access_token, { email }); // In a real app, 'data' would contain user info
      if (onLoginSuccess) onLoginSuccess();
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="logo-icon">E</div>
          <h2>Welcome back to <span className="brand-highlight">EVUA</span></h2>
          <p className="auth-subtitle">Sign in to continue your enterprise migration</p>
        </div>

        {error && <div className="auth-error-banner">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-input-group">
            <label>EMAIL ADDRESS</label>
            <input 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              placeholder="name@company.com"
              required 
            />
          </div>

          <div className="auth-input-group">
            <label>PASSWORD</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              placeholder="••••••••"
              required 
            />
          </div>

          <button className="auth-submit-btn" type="submit" disabled={loading}>
            {loading ? 'AUTHENTICATING...' : 'SIGN IN'}
            <span className="btn-icon">→</span>
          </button>
        </form>

        <div className="auth-footer">
          <p>Don't have an account? <button className="auth-link-btn" onClick={switchToRegister}>Create one</button></p>
        </div>
      </div>
      
      <div className="auth-visual-side">
        <div className="neural-grid-overlay"></div>
        <div className="visual-content">
          <span className="visual-tag">ENTERPRISE READY</span>
          <h3>AI-Powered Automated Refactoring</h3>
          <p>EVUA leverages neural patterns to modernize legacy AngularJS and PHP architectures with 95% automation.</p>
        </div>
      </div>
    </div>
  );
};

export default Login;
