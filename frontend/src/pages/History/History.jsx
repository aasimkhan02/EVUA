import React from 'react';
import { Filter, ArrowLeftRight } from 'lucide-react';
import './History.css';

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
            compare structural diffs, and audit automated refactor cycles across your 
            repository stack.
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
      
      <div className="history-content">
        <div className="timeline-card">
          <div className="timeline-card-header">
            <span className="timeline-label">EXECUTION TIMELINE</span>
            <span className="timeline-version-badge">v2.4.0 Pipeline Status</span>
          </div>
          <div className="timeline-track">
            <div className="timeline-line"></div>

            <div className="timeline-node">
              <div className="timeline-dot dot-active"></div>
              <div className="timeline-node-label">
                <span className="node-id">MIG-801</span>
                <span className="node-time">2H AGO</span>
              </div>
            </div>

            <div className="timeline-node">
              <div className="timeline-dot dot-inactive"></div>
              <div className="timeline-node-label">
                <span className="node-id">MIG-794</span>
                <span className="node-time">YESTERDAY</span>
              </div>
            </div>

            <div className="timeline-node">
              <div className="timeline-dot dot-warning"></div>
              <div className="timeline-node-label">
                <span className="node-id active-node-id">MIG-782</span>
                <span className="node-time">3 DAYS AGO</span>
              </div>
            </div>

            <div className="timeline-node">
              <div className="timeline-dot dot-inactive"></div>
              <div className="timeline-node-label">
                <span className="node-id">MIG-766</span>
                <span className="node-time">OCT 24</span>
              </div>
            </div>

            <div className="timeline-node">
              <div className="timeline-dot dot-faded"></div>
              <div className="timeline-node-label">
                <span className="node-id faded-id">MIG-741</span>
                <span className="node-time faded-id">OCT 12</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default History;
