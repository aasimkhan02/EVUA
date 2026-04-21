import React, { useState } from 'react';
import api from "../../utils/api";
import "../Login/Login.css"; // Reusing common styles from Login directory

const Register = ({ switchToLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (password !== confirmPassword) {
      return setError('Passwords do not match');
    }

    setLoading(true);
    try {
      await api.post('/auth/register', { email, password });
      setSuccess(true);
      setTimeout(() => switchToLogin(), 2000);
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="login-container">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <div className="status-icon success-icon">✓</div>
          <h2 style={{ color: '#fff', marginBottom: '16px' }}>Account Created!</h2>
          <p style={{ color: '#a0abb6' }}>Redirecting you to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="logo-icon">E</div>
          <h2>Join the <span className="brand-highlight">Evolution</span></h2>
          <p className="auth-subtitle">Create your EVUA account to start migrating projects</p>
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
              placeholder="Min. 8 characters"
              required 
            />
          </div>

          <div className="auth-input-group">
            <label>CONFIRM PASSWORD</label>
            <input 
              type="password" 
              value={confirmPassword} 
              onChange={(e) => setConfirmPassword(e.target.value)} 
              placeholder="••••••••"
              required 
            />
          </div>

          <button className="auth-submit-btn" type="submit" disabled={loading}>
            {loading ? 'CREATING ACCOUNT...' : 'CREATE ACCOUNT'}
            <span className="btn-icon">→</span>
          </button>
        </form>

        <div className="auth-footer">
          <p>Already have an account? <button className="auth-link-btn" onClick={switchToLogin}>Sign in</button></p>
        </div>
      </div>
      
      <div className="auth-visual-side" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?q=80&w=2000&auto=format&fit=crop')" }}>
        <div className="neural-grid-overlay"></div>
        <div className="visual-content">
          <span className="visual-tag">ENTERPRISE SCALE</span>
          <h3>Modernize Without the Technical Debt</h3>
          <p>EVUA doesn't just convert code; it architecturally upgrades your systems to modern best practices automatically.</p>
        </div>
      </div>
    </div>
  );
};

export default Register;
