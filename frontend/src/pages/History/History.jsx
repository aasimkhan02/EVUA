import React, { useState, useEffect } from 'react';
import { Filter, ArrowLeftRight, Zap, Layers, Brain, ChevronLeft, ChevronRight, CheckCircle2, XCircle, Info, Database, Globe } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './History.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const History = () => {
  const { token } = useAuth();
  const [migrations, setMigrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE}/jobs`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (!res.ok) throw new Error('Failed to fetch history');
        const data = await res.json();
        setMigrations(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchHistory();
    }
  }, [token]);

  const getEngineInfo = (job) => {
    const src = job.source_version || 'Legacy';
    if (src.toLowerCase().includes('php')) {
      return {
        label: 'PHP Modernization',
        icon: <Database size={16} />,
        colorClass: 'icon-3',
        source: `PHP ${job.source_version}`,
        target: `PHP ${job.target_version}`
      };
    }
    return {
      label: 'AngularJS Migration',
      icon: <Globe size={16} />,
      colorClass: 'icon-1',
      source: 'AngularJS 1.x',
      target: `Angular ${job.target_version || '17+'}`
    };
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return { date: '-', time: '-' };
    const date = new Date(dateStr);
    return {
      date: date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }),
      time: date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' UTC'
    };
  };

  return (
    <div className="history-container">
      <div className="history-header">
        <div className="history-title-section">
          <h1 className="history-title">
            Migration <span className="highlight-text">History</span>
          </h1>
          <p className="history-desc">
            Track lifecycle snapshots of code transformations. Review checkpoints, 
            compare structural diffs, and audit automated refactor cycles.
          </p>
        </div>
        <div className="history-actions">
          <button className="btn btn-secondary">
            <Filter size={14} />
            Filter Logs
          </button>
          <button className="btn btn-primary">
            <ArrowLeftRight size={14} />
            Compare Selected
          </button>
        </div>
      </div>

      <div className="history-summary-grid">
        <div className="info-card diff-engine-card">
          <div className="info-card-content">
            <h2 className="info-card-title">Advanced Difference Engine</h2>
            <p className="info-card-text">
              Selecting two migration events allows you to analyze the structural changes in transformation logic. 
              Our AST-aware comparison highlights logic drifts, dependency updates, and performance bottlenecks.
            </p>
            <div className="info-card-footer">
              <div className="analyzer-avatars">
                <div className="avatar">AS</div>
                <div className="avatar">OB</div>
                <div className="avatar">SRC</div>
              </div>
              <span className="footer-status-text">Analyzers ready for comparison</span>
            </div>
          </div>
        </div>

        <div className="info-card health-card">
          <div className="info-card-content">
            <span className="health-label">SYSTEM HEALTH</span>
            <h2 className="health-title">Integrity Guard Active</h2>
            <div className="progress-section">
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: '100%' }}></div>
              </div>
              <div className="progress-labels">
                <span className="progress-tag">DATABASE_SYNC</span>
                <span className="progress-percent">100%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="history-content">
        <div className="data-table-container">
          <table className="migration-table">
            <thead>
              <tr>
                <th className="th-checkbox">
                  <input type="checkbox" className="custom-checkbox" />
                </th>
                <th>TIMESTAMP / PROJECT</th>
                <th>ENGINE TYPE</th>
                <th>SOURCE / TARGET</th>
                <th>STATUS</th>
                <th className="text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: '#6e7681' }}>Fetching history...</td></tr>
              ) : migrations.length === 0 ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: '#6e7681' }}>No migrations found. Start your first mission in the Migration tab!</td></tr>
              ) : migrations.map((job) => {
                const engine = getEngineInfo(job);
                const { date, time } = formatDate(job.created_at);
                return (
                  <tr key={job.id}>
                    <td>
                      <input 
                        type="checkbox" 
                        className="custom-checkbox" 
                      />
                    </td>
                    <td className="td-timestamp">
                      <div className="ts-date">{date}</div>
                      <div className="ts-time">{job.project_name || 'Unnamed Project'}</div>
                    </td>
                    <td className="td-engine">
                      <div className="engine-wrapper">
                        <div className={`engine-icon-bg ${engine.colorClass}`}>
                          {engine.icon}
                        </div>
                        <span className="engine-name">{engine.label}</span>
                      </div>
                    </td>
                    <td className="td-source-target">
                      <div className="path-pair">
                        <span className="path-chip">{engine.source}</span>
                        <ChevronRight size={12} className="path-arrow" />
                        <span className="path-chip highlight">{engine.target}</span>
                      </div>
                    </td>
                    <td className="td-status">
                      <div className={`status-pill ${job.status.toLowerCase()}`}>
                        <span className="status-dot"></span>
                        {job.status.toUpperCase()}
                      </div>
                    </td>
                    <td className="td-actions text-right">
                      <button className="icon-btn">
                        <Info size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="table-footer">
            <div className="metrics-group">
              <div className="metric-item">
                <span className="metric-label">TOTAL MIGRATIONS</span>
                <span className="metric-value">{migrations.length}</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">SUCCESS RATE</span>
                <span className="metric-value highlight-blue">
                   {migrations.length > 0 ? Math.round((migrations.filter(m => m.status === 'completed').length / migrations.length) * 100) : 0}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">DATABASE SYNC</span>
                <span className="metric-value">ACTIVE</span>
              </div>
            </div>

            <div className="pagination">
              <button className="page-btn"><ChevronLeft size={18} /></button>
              <span className="page-info">Page <span className="white-text">1</span> of 1</span>
              <button className="page-btn"><ChevronRight size={18} /></button>
            </div>
          </div>
        </div>
      </div>
      
      <button className="help-fab">
        <span className="fab-icon">?</span>
      </button>
    </div>
  );
};

export default History;