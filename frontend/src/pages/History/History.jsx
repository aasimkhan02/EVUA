import React, { useState, useEffect, useMemo } from 'react';
import {
  Filter, ArrowLeftRight, ChevronLeft, ChevronRight,
  CheckCircle2, XCircle, Info, Database, Globe,
  Clock, RefreshCw, TrendingUp, Activity, X, Trash2
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './History.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const PAGE_SIZE = 10;

// ── Engine detection ─────────────────────────────────────────────────────────
// Backend sets source_version = "AngularJS" for angular jobs,
// and source_version = "5.6" / "7.0" etc (numeric PHP version) for PHP jobs.
const detectEngine = (job) => {
  const src = (job.source_version || '').toLowerCase();
  const tgt = (job.target_version || '').toLowerCase();

  // PHP: source_version is a numeric PHP version like "5.6", "7.0"
  // Angular: source_version is "AngularJS" or target_version has no dots (just "17")
  const isPhp = /^\d+\.\d+/.test(src) || src === 'php' || tgt.startsWith('php');
  const isAngular = src.includes('angular') || (!isPhp && /^\d+$/.test(tgt));

  if (isPhp) {
    return {
      key: 'php',
      label: 'PHP Modernization',
      icon: <Database size={15} />,
      colorClass: 'icon-3',
      color: '#58a6ff',
      source: `PHP ${job.source_version}`,
      target: `PHP ${job.target_version || '8.x'}`,
    };
  }
  return {
    key: 'angular',
    label: 'AngularJS Migration',
    icon: <Globe size={15} />,
    colorClass: 'icon-1',
    color: '#1ce3ff',
    source: 'AngularJS 1.x',
    target: `Angular ${job.target_version || '17+'}`,
  };
};

// ── Status helpers ───────────────────────────────────────────────────────────
const STATUS_MAP = {
  completed: { label: 'COMPLETED', color: '#1ce3ff', bg: 'rgba(28,227,255,0.08)', icon: <CheckCircle2 size={12} /> },
  failed:    { label: 'FAILED',    color: '#f85149', bg: 'rgba(248,81,73,0.08)',   icon: <XCircle size={12} /> },
  running:   { label: 'RUNNING',   color: '#e3b341', bg: 'rgba(227,179,65,0.08)', icon: <RefreshCw size={12} style={{ animation: 'spin 1.2s linear infinite' }} /> },
  pending:   { label: 'PENDING',   color: '#8b949e', bg: 'rgba(139,148,158,0.08)', icon: <Clock size={12} /> },
};

const statusInfo = (status) => STATUS_MAP[status?.toLowerCase()] || STATUS_MAP.pending;

const formatDate = (dateStr) => {
  if (!dateStr) return { date: '—', time: '—' };
  const d = new Date(dateStr);
  return {
    date: d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }),
    time: d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }),
  };
};

// ── Component ────────────────────────────────────────────────────────────────
const History = () => {
  const { token } = useAuth();

  const [migrations, setMigrations] = useState([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [filterEngine, setFilterEngine] = useState('all'); // 'all' | 'angular' | 'php'
  const [filterStatus, setFilterStatus] = useState('all'); // 'all' | 'completed' | 'failed' | 'running' | 'pending'
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // ── Fetch ─────────────────────────────────────────────────────────────────
  const fetchHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch history`);
      const data = await res.json();
      setMigrations(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchHistory();
  }, [token]);

  // ── Derived stats ──────────────────────────────────────────────────────────
  const total     = migrations.length;
  const completed = migrations.filter(m => m.status === 'completed').length;
  const failed    = migrations.filter(m => m.status === 'failed').length;
  const running   = migrations.filter(m => m.status === 'running').length;
  const successRate = total > 0 ? Math.round((completed / total) * 100) : 0;

  const phpCount     = migrations.filter(m => detectEngine(m).key === 'php').length;
  const angularCount = migrations.filter(m => detectEngine(m).key === 'angular').length;

  // ── Filtered + paginated ──────────────────────────────────────────────────
  const filtered = useMemo(() => {
    return migrations.filter(job => {
      const eng = detectEngine(job);
      const engineMatch = filterEngine === 'all' || eng.key === filterEngine;
      const statusMatch = filterStatus === 'all' || job.status?.toLowerCase() === filterStatus;
      return engineMatch && statusMatch;
    });
  }, [migrations, filterEngine, filterStatus]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // ── Selection ─────────────────────────────────────────────────────────────
  const toggleSelect = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === paginated.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(paginated.map(j => j.id)));
    }
  };

  const deleteJobs = async (ids) => {
    if (!window.confirm(`Are you sure you want to delete ${ids.length === 1 ? 'this job' : `${ids.length} jobs`}? This action cannot be undone.`)) return;
    
    setIsDeleting(true);
    let errorOccurred = false;
    for (const id of ids) {
      try {
        const res = await fetch(`${API_BASE}/jobs/${id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) errorOccurred = true;
      } catch {
        errorOccurred = true;
      }
    }
    
    if (errorOccurred) {
      alert("Some jobs could not be deleted or encountered an error.");
    }
    
    setSelectedIds(new Set());
    await fetchHistory();
    setIsDeleting(false);
  };

  // Reset page when filter changes
  useEffect(() => { setPage(1); }, [filterEngine, filterStatus]);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="history-container">

      {/* HEADER */}
      <div className="history-header">
        <div className="history-title-section">
          <h1 className="history-title">
            Migration <span className="highlight-text">History</span>
          </h1>
          <p className="history-desc">
            Every migration job logged and persisted. Filter by engine or status,
            track outcomes, and audit automated refactor cycles.
          </p>
        </div>
        <div className="history-actions">
          <button className="btn btn-secondary" onClick={() => setShowFilters(v => !v)}>
            <Filter size={14} />
            {showFilters ? 'Hide Filters' : 'Filter'}
          </button>
          <button className="btn btn-secondary" onClick={fetchHistory} disabled={loading || isDeleting}>
            <RefreshCw size={14} style={loading ? { animation: 'spin 1s linear infinite' } : {}} />
            Refresh
          </button>
          {selectedIds.size > 0 && (
            <button className="btn btn-danger" onClick={() => deleteJobs(Array.from(selectedIds))} disabled={isDeleting}>
              <Trash2 size={14} />
              {isDeleting ? 'Deleting...' : `Delete (${selectedIds.size})`}
            </button>
          )}
          <button className="btn btn-primary" disabled={selectedIds.size < 2 || isDeleting}>
            <ArrowLeftRight size={14} />
            Compare Selected
          </button>
        </div>
      </div>

      {/* STATS ROW */}
      <div className="history-stats-row">
        <div className="stat-tile">
          <div className="stat-tile-value">{total}</div>
          <div className="stat-tile-label">TOTAL JOBS</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile-value" style={{ color: '#1ce3ff' }}>{successRate}%</div>
          <div className="stat-tile-label">SUCCESS RATE</div>
          <div className="stat-mini-bar">
            <div className="stat-mini-fill" style={{ width: `${successRate}%`, background: '#1ce3ff' }} />
          </div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile-value" style={{ color: '#3fb950' }}>{completed}</div>
          <div className="stat-tile-label">COMPLETED</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile-value" style={{ color: '#f85149' }}>{failed}</div>
          <div className="stat-tile-label">FAILED</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile-value" style={{ color: '#e3b341' }}>{running}</div>
          <div className="stat-tile-label">RUNNING</div>
        </div>
        <div className="stat-tile engine-split">
          <div className="engine-split-row">
            <Globe size={13} style={{ color: '#1ce3ff' }} />
            <span style={{ color: '#1ce3ff', fontWeight: 700, fontSize: 15 }}>{angularCount}</span>
            <span className="stat-tile-label" style={{ margin: 0 }}>Angular</span>
          </div>
          <div className="engine-split-row" style={{ marginTop: 8 }}>
            <Database size={13} style={{ color: '#58a6ff' }} />
            <span style={{ color: '#58a6ff', fontWeight: 700, fontSize: 15 }}>{phpCount}</span>
            <span className="stat-tile-label" style={{ margin: 0 }}>PHP</span>
          </div>
        </div>
      </div>

      {/* FILTER BAR */}
      {showFilters && (
        <div className="filter-bar">
          <div className="filter-group">
            <span className="filter-label">ENGINE</span>
            <div className="filter-pills">
              {['all', 'angular', 'php'].map(e => (
                <button
                  key={e}
                  className={`filter-pill ${filterEngine === e ? 'active' : ''}`}
                  onClick={() => setFilterEngine(e)}
                >
                  {e === 'all' ? 'All Engines' : e === 'angular' ? 'AngularJS' : 'PHP'}
                </button>
              ))}
            </div>
          </div>
          <div className="filter-group">
            <span className="filter-label">STATUS</span>
            <div className="filter-pills">
              {['all', 'completed', 'failed', 'running', 'pending'].map(s => (
                <button
                  key={s}
                  className={`filter-pill ${filterStatus === s ? 'active' : ''}`}
                  onClick={() => setFilterStatus(s)}
                  style={filterStatus === s && s !== 'all' ? { borderColor: statusInfo(s).color, color: statusInfo(s).color } : {}}
                >
                  {s === 'all' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>
          </div>
          {(filterEngine !== 'all' || filterStatus !== 'all') && (
            <button
              className="clear-filters-btn"
              onClick={() => { setFilterEngine('all'); setFilterStatus('all'); }}
            >
              <X size={12} /> Clear Filters
            </button>
          )}
        </div>
      )}

      {/* ERROR */}
      {error && (
        <div className="error-banner">
          <XCircle size={16} />
          <span>{error}</span>
          <button className="btn btn-secondary" onClick={fetchHistory} style={{ padding: '4px 12px', fontSize: 12 }}>
            Retry
          </button>
        </div>
      )}

      {/* TABLE */}
      <div className="history-content">
        <div className="data-table-container">

          {/* Result count */}
          {!loading && (
            <div className="table-result-count">
              Showing {filtered.length === total ? `all ${total}` : `${filtered.length} of ${total}`} migrations
              {(filterEngine !== 'all' || filterStatus !== 'all') && (
                <span className="filter-active-badge">Filtered</span>
              )}
            </div>
          )}

          <table className="migration-table">
            <thead>
              <tr>
                <th className="th-checkbox">
                  <input
                    type="checkbox"
                    className="custom-checkbox"
                    checked={paginated.length > 0 && selectedIds.size === paginated.length}
                    onChange={toggleAll}
                  />
                </th>
                <th>TIMESTAMP / PROJECT</th>
                <th>ENGINE</th>
                <th>SOURCE → TARGET</th>
                <th>STATUS</th>
                <th>DURATION</th>
                <th className="text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="7" className="table-empty-state">
                    <RefreshCw size={20} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
                    <div>Loading migration history...</div>
                  </td>
                </tr>
              ) : paginated.length === 0 ? (
                <tr>
                  <td colSpan="7" className="table-empty-state">
                    <Activity size={28} style={{ marginBottom: 12, opacity: 0.3 }} />
                    <div style={{ fontWeight: 600, color: '#c9d1d9', marginBottom: 6 }}>
                      {filtered.length === 0 && total > 0 ? 'No jobs match your filters' : 'No migrations yet'}
                    </div>
                    <div style={{ fontSize: 13, color: '#6e7681' }}>
                      {filtered.length === 0 && total > 0
                        ? 'Try adjusting the engine or status filter.'
                        : 'Run your first migration from the Migration tab.'}
                    </div>
                  </td>
                </tr>
              ) : paginated.map((job) => {
                const eng    = detectEngine(job);
                const stat   = statusInfo(job.status);
                const { date, time } = formatDate(job.created_at);
                const isSelected = selectedIds.has(job.id);

                // Duration
                let duration = '—';
                if (job.started_at && job.completed_at) {
                  const ms = new Date(job.completed_at) - new Date(job.started_at);
                  duration = ms < 60000 ? `${Math.round(ms / 1000)}s` : `${Math.round(ms / 60000)}m`;
                }

                return (
                  <tr key={job.id} className={isSelected ? 'row-selected' : ''}>
                    <td>
                      <input
                        type="checkbox"
                        className="custom-checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(job.id)}
                      />
                    </td>

                    <td className="td-timestamp">
                      <div className="ts-date">{date}</div>
                      <div className="ts-time">{time} · <span style={{ color: '#c9d1d9' }}>{job.project_name || 'Unnamed'}</span></div>
                    </td>

                    <td className="td-engine">
                      <div className="engine-wrapper">
                        <div className={`engine-icon-bg ${eng.colorClass}`}>
                          {eng.icon}
                        </div>
                        <span className="engine-name">{eng.label}</span>
                      </div>
                    </td>

                    <td className="td-source-target">
                      <div className="path-pair">
                        <span className="path-chip">{eng.source}</span>
                        <ChevronRight size={12} className="path-arrow" />
                        <span className="path-chip highlight">{eng.target}</span>
                      </div>
                    </td>

                    <td className="td-status">
                      <div className="status-pill" style={{ color: stat.color, background: stat.bg }}>
                        {stat.icon}
                        <span>{stat.label}</span>
                      </div>
                    </td>

                    <td className="td-duration">
                      <span className="duration-val">{duration}</span>
                    </td>

                    <td className="td-actions text-right">
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                        <button className="icon-btn" title="View Details">
                          <Info size={16} />
                        </button>
                        <button className="icon-btn icon-btn-danger" title="Delete Job" onClick={() => deleteJobs([job.id])} disabled={isDeleting}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* TABLE FOOTER */}
          <div className="table-footer">
            <div className="metrics-group">
              <div className="metric-item">
                <span className="metric-label">TOTAL MIGRATIONS</span>
                <span className="metric-value">{total}</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">SUCCESS RATE</span>
                <span className="metric-value highlight-blue">{successRate}%</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">SELECTED</span>
                <span className="metric-value">{selectedIds.size}</span>
              </div>
            </div>

            <div className="pagination">
              <button className="page-btn" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
                <ChevronLeft size={18} />
              </button>
              <span className="page-info">
                Page <span className="white-text">{page}</span> of <span className="white-text">{totalPages}</span>
              </span>
              <button className="page-btn" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default History;