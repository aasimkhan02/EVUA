import React from 'react';
import { Filter, ArrowLeftRight, Zap, Layers, Brain, ChevronLeft, ChevronRight, CheckCircle2, XCircle, Info } from 'lucide-react';
import './History.css';

const MIGRATIONS = [
  {
    id: 1,
    timestamp: 'Nov 02, 2023',
    time: '14:22:10 UTC',
    engineType: 'Turbo-Rust Refactor',
    engineIcon: <Zap size={16} className="engine-icon-zap" />,
    source: 'Legacy JS',
    target: 'Rust v1.72',
    status: 'COMPLETED',
    selected: true,
  },
  {
    id: 2,
    timestamp: 'Oct 31, 2023',
    time: '09:15:44 UTC',
    engineType: 'Schema Evolution',
    engineIcon: <Layers size={16} className="engine-icon-layers" />,
    source: 'v1.2 Beta',
    target: 'v1.2.1 Stable',
    status: 'FAILED',
    selected: true,
  },
  {
    id: 3,
    timestamp: 'Oct 28, 2023',
    time: '18:02:11 UTC',
    engineType: 'AI Optimization',
    engineIcon: <Brain size={16} className="engine-icon-brain" />,
    source: 'Python 3.8',
    target: 'Python 3.11',
    status: 'COMPLETED',
    selected: false,
  }
];

const History = () => {
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
                <th>TIMESTAMP</th>
                <th>ENGINE TYPE</th>
                <th>SOURCE / TARGET</th>
                <th>STATUS</th>
                <th className="text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {MIGRATIONS.map((migration) => (
                <tr key={migration.id} className={migration.selected ? 'row-selected' : ''}>
                  <td>
                    <input 
                      type="checkbox" 
                      className="custom-checkbox" 
                      checked={migration.selected}
                      readOnly
                    />
                  </td>
                  <td className="td-timestamp">
                    <div className="ts-date">{migration.timestamp}</div>
                    <div className="ts-time">{migration.time}</div>
                  </td>
                  <td className="td-engine">
                    <div className="engine-wrapper">
                      <div className={`engine-icon-bg icon-${migration.id}`}>
                        {migration.engineIcon}
                      </div>
                      <span className="engine-name">{migration.engineType}</span>
                    </div>
                  </td>
                  <td className="td-source-target">
                    <div className="path-pair">
                      <span className="path-chip">{migration.source}</span>
                      <ChevronRight size={12} className="path-arrow" />
                      <span className="path-chip highlight">{migration.target}</span>
                    </div>
                  </td>
                  <td className="td-status">
                    <div className={`status-pill ${migration.status.toLowerCase()}`}>
                      <span className="status-dot"></span>
                      {migration.status}
                    </div>
                  </td>
                  <td className="td-actions text-right">
                    <button className="icon-btn">
                      <Info size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="table-footer">
            <div className="metrics-group">
              <div className="metric-item">
                <span className="metric-label">TOTAL MIGRATIONS</span>
                <span className="metric-value">1,284</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">SUCCESS RATE</span>
                <span className="metric-value highlight-blue">98.2%</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">COMPUTE USED</span>
                <span className="metric-value">42.8 TFLOPS</span>
              </div>
            </div>

            <div className="pagination">
              <button className="page-btn"><ChevronLeft size={18} /></button>
              <span className="page-info">Page <span className="white-text">1</span> of 64</span>
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
