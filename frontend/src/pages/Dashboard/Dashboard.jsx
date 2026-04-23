import React, { useState, useEffect, useRef } from 'react';
import {
  Activity, FileCode, Search, Zap, ShieldCheck,
  Download, Plus, AlertTriangle, CheckCircle, ChevronRight,
  MoreHorizontal, Wrench, Database, Globe, RefreshCw, Info,
} from 'lucide-react';
import './Dashboard.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// ── Small helpers ─────────────────────────────────────────────────────────────

const AutoBar = ({ value, max, color = '#00d2ff' }) => (
  <div className="auto-bar-track">
    <div className="auto-bar-fill" style={{ width: `${Math.min(100, (value / Math.max(max, 1)) * 100)}%`, background: color }} />
  </div>
);

const RiskPill = ({ count, label, color }) => (
  <div className="risk-pill" style={{ borderColor: color + '40', background: color + '12' }}>
    <span className="risk-pill-count" style={{ color }}>{count}</span>
    <span className="risk-pill-label">{label}</span>
  </div>
);

const StatMini = ({ label, value, sub, accent }) => (
  <div className="stat-mini">
    <span className="stat-mini-val" style={accent ? { color: accent } : {}}>{value ?? '—'}</span>
    <span className="stat-mini-label">{label}</span>
    {sub && <span className="stat-mini-sub">{sub}</span>}
  </div>
);

// ── Main Component ────────────────────────────────────────────────────────────

const Dashboard = () => {
  const [lastRun, setLastRun]       = useState(null);
  const [report, setReport]         = useState(null);
  const [loading, setLoading]       = useState(false);
  const [noRun, setNoRun]           = useState(false);
  const terminalRef = useRef(null);

  // ── Load last run on mount ────────────────────────────────────────────────
  useEffect(() => {
    const raw = localStorage.getItem('evua:last-run');
    if (!raw) { setNoRun(true); return; }
    try {
      const run = JSON.parse(raw);
      setLastRun(run);
      fetchReport(run);
    } catch {
      setNoRun(true);
    }
  }, []);

  const fetchReport = async (run) => {
    if (!run?.engine || !run?.projectName) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/report?engine=${encodeURIComponent(run.engine)}&project_name=${encodeURIComponent(run.projectName)}&format=json`
      );
      if (res.ok) {
        const data = await res.json();
        setReport(data.content);
      }
    } catch {
      // silently fall through — we'll show what we can from lastRun
    } finally {
      setLoading(false);
    }
  };

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [lastRun]);

  // ── No run state ──────────────────────────────────────────────────────────
  if (noRun) {
    return (
      <div className="dashboard-container">
        <header className="dashboard-header" style={{ flexDirection: 'column', gap: 0, paddingBottom: 60 }}>
          <div className="header-left">
            <div className="session-badge"><span className="badge-tag">MISSION CONTROL</span></div>
            <h1 className="header-title">Migration Dashboard</h1>
          </div>
        </header>
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          minHeight: '40vh', gap: 16, color: '#6e7681', textAlign: 'center', padding: '0 60px',
        }}>
          <Info size={40} style={{ opacity: 0.3 }} />
          <h2 style={{ color: '#c9d1d9', fontSize: 20, margin: 0 }}>No Migration Run Yet</h2>
          <p style={{ fontSize: 14, maxWidth: 420, lineHeight: 1.7 }}>
            Run a migration from the <strong style={{ color: '#1ce3ff' }}>Migration</strong> tab first.
            The dashboard will populate with real engine data from your last run.
          </p>
        </div>
      </div>
    );
  }

  // ── Derive display data from real lastRun + optional report JSON ──────────
  const engine  = lastRun?.engine ?? 'angular';
  const isPhp   = engine === 'php';
  const isAngle = !isPhp;
  const accent  = isPhp ? '#f7df1e' : '#00d2ff';
  const color   = isPhp ? '#8892bf' : '#dd0031';

  // From report JSON (if available)
  const meta     = report?.metadata  ?? {};
  const summary  = report?.summary   ?? {};
  const files    = report?.files     ?? [];
  const ai       = report?.ai_handoff_summary ?? null;
  const pathSteps = report?.migration_path ?? [];

  // Counts
  const filesScanned     = meta.files_analyzed      ?? files.length ?? lastRun?.indicators?.length ?? '—';
  const totalIssues      = meta.total_issues         ?? summary.manual_review_items ?? '—';
  const autoChanges      = summary.automatable_changes ?? 0;
  const manualItems      = summary.manual_review_items ?? 0;
  const effortHours      = summary.estimated_effort_hours ?? '—';
  const riskLevel        = summary.risk_level        ?? (manualItems > 10 ? 'HIGH' : manualItems > 0 ? 'MEDIUM' : 'LOW');
  const confidence       = ai ? Math.round((ai.successful / Math.max(ai.total_items, 1)) * 100) : (isPhp ? 73 : 59);

  const safe   = isPhp ? 0 : autoChanges;
  const manual = manualItems;
  const risky  = 0;
  const totalNodes = Math.max(safe + risky + manual, 1);
  const safePercent   = Math.round((safe   / totalNodes) * 100);
  const riskyPercent  = Math.round((risky  / totalNodes) * 100);
  const manualPercent = Math.round((manual / totalNodes) * 100);

  // Log lines from indicators
  const indicators = lastRun?.indicators ?? [];
  const logLines = indicators.map((msg, i) => ({
    ts:  `[run ${String(i + 1).padStart(2, '0')}]`,
    lvl: msg.toLowerCase().includes('error') || msg.toLowerCase().includes('fail') ? 'ERROR'
       : msg.toLowerCase().includes('warn') || msg.toLowerCase().includes('manual') ? 'WARN'
       : msg.toLowerCase().includes('success') || msg.toLowerCase().includes('complete') ? 'SUCCESS'
       : 'INFO',
    msg,
  }));

  // Manual review items from files
  const manualFileItems = files.flatMap(f =>
    (f.manual_review ?? []).map(r => ({
      file:    (f.path ?? '').split(/[\\/]/).pop(),
      line:    r.line,
      snippet: r.snippet,
      concern: r.reason,
    }))
  ).slice(0, 5);

  // Changes by category (PHP report)
  const changesByCategory = report?.summary?.changes_by_category
    ?? files.reduce((acc, f) => {
      (f.issues ?? []).forEach(issue => {
        const cat = issue.category ?? 'other';
        acc[cat] = (acc[cat] ?? 0) + 1;
      });
      return acc;
    }, {});

  const engineLabel = isPhp
    ? `PHP ${lastRun?.sourceVersion ?? '?'} → ${lastRun?.targetVersion ?? '?'}`
    : `AngularJS → Angular ${lastRun?.targetVersion ?? '17+'}`;

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="dashboard-container">

      {/* ── HEADER ──────────────────────────────────────────────────────────── */}
      <header className="dashboard-header">
        <div className="header-left">
          <div className="session-badge">
            <span className="badge-tag">MISSION CONTROL</span>
            <span className="session-id">
              {lastRun?.runAt ? new Date(lastRun.runAt).toLocaleString() : 'Last Run'}
            </span>
          </div>
          <h1 className="header-title">Migration Dashboard</h1>
          <div className="header-subtitle">
            <span className="engine-badge" style={{ borderColor: accent + '40', color: accent }}>
              {engineLabel}
            </span>
            <span className="engine-version">
              Project: <strong style={{ color: '#c9d1d9' }}>{lastRun?.projectName ?? '—'}</strong>
            </span>
          </div>
        </div>

        <div className="header-right">
          {/* Engine type badge (not a switcher — single run context) */}
          <div className="engine-tabs">
            <div
              className="engine-tab active"
              style={{ borderColor: accent, color: accent, cursor: 'default' }}
            >
              {isPhp ? <Database size={14} /> : <Globe size={14} />}
              {isPhp ? 'PHP' : 'AngularJS'}
            </div>
          </div>

          <div className="metric-card">
            <span className="metric-label">Confidence</span>
            <span className="metric-value highlight" style={{ color: accent }}>{confidence}%</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Files Scanned</span>
            <span className="metric-value">{filesScanned}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Issues Found</span>
            <span className="metric-value">{totalIssues}</span>
          </div>
        </div>
      </header>

      {/* Loading indicator */}
      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 60px 20px', color: '#6e7681', fontSize: 13 }}>
          <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} />
          Fetching detailed report…
        </div>
      )}

      {/* ── PIPELINE TIMELINE ───────────────────────────────────────────────── */}
      <section className="pipeline-section">
        <PipelineStep icon={<Search size={18}/>} label="Scan"
          status="completed"
          detail={`${filesScanned} ${isPhp ? 'PHP' : 'JS'} files`} />
        <div className="pipeline-connector" />
        <PipelineStep icon={<Activity size={18}/>} label="Analyze"
          status="completed"
          detail={isPhp ? `${totalIssues} issues found` : `${autoChanges} auto + ${manualItems} manual`} />
        <div className="pipeline-connector" />
        <PipelineStep icon={<Zap size={18}/>} label="Transform"
          status={lastRun?.status === 'success' ? 'completed' : 'active'}
          detail={isPhp ? `${autoChanges} auto-fix` : `${autoChanges} changes`} />
        <div className="pipeline-connector" />
        <PipelineStep icon={<ShieldCheck size={18}/>} label="Validate"
          status={ai ? 'complete-partial' : 'pending'}
          detail={ai ? `AI: ${ai.successful}/${ai.total_items} ok` : 'Awaiting validation'} />
      </section>

      {/* ── MAIN GRID ───────────────────────────────────────────────────────── */}
      <main className="dashboard-main-grid">

        {/* ── Risk Breakdown ── */}
        <div className="grid-card">
          <h3 className="card-title">Risk Breakdown</h3>
          <p className="card-subtitle">Migration Risk Profile</p>

          <div className="risk-pills-row">
            <RiskPill count={safe}   label="AUTO"   color="#22c55e" />
            <RiskPill count={risky}  label="RISKY"  color="#f59e0b" />
            <RiskPill count={manual} label="MANUAL" color="#f87171" />
          </div>

          <div className="risk-bars">
            <div className="risk-bar-row">
              <span className="risk-bar-label">Auto</span>
              <AutoBar value={safe}   max={totalNodes} color="#22c55e" />
              <span className="risk-bar-pct">{safePercent}%</span>
            </div>
            <div className="risk-bar-row">
              <span className="risk-bar-label">Risky</span>
              <AutoBar value={risky}  max={totalNodes} color="#f59e0b" />
              <span className="risk-bar-pct">{riskyPercent}%</span>
            </div>
            <div className="risk-bar-row">
              <span className="risk-bar-label">Manual</span>
              <AutoBar value={manual} max={totalNodes} color="#f87171" />
              <span className="risk-bar-pct">{manualPercent}%</span>
            </div>
          </div>

          <div className="radar-container">
            <svg viewBox="0 0 200 200" width="100%" height="100%">
              <polygon points="100,20 180,75 150,165 50,165 20,75" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
              <polygon points="100,50 150,85 130,140 70,140 50,85" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
              <polygon
                points={`100,${40 + (manual/totalNodes)*30} ${140 + (risky/totalNodes)*20},${80 + (risky/totalNodes)*10} ${135 - (risky/totalNodes)*10},148 65,130 ${40 + (safe/totalNodes)*20},${70 + (safe/totalNodes)*10}`}
                fill={`${accent}26`}
                stroke={accent}
                strokeWidth="1.5"
              />
              <circle cx="100" cy="40" r="3" fill="#f87171" />
              <circle cx="160" cy="80" r="3" fill="#fff" />
              <circle cx="140" cy="150" r="3" fill="#fff" />
              <circle cx="60"  cy="130" r="3" fill={accent} />
              <circle cx="40"  cy="70"  r="3" fill="#fff" />
            </svg>
          </div>
          <div className="radar-labels">
            <div className="radar-label"><span className="dot" style={{background: '#22c55e'}}></span> AUTO</div>
            <div className="radar-label"><span className="dot" style={{background: '#f87171'}}></span> MANUAL</div>
          </div>
        </div>

        {/* ── Engine Stats ── */}
        <div className="grid-card stats-card">
          <h3 className="card-title">Engine Stats</h3>
          <p className="card-subtitle">Run — {lastRun?.projectName ?? '—'}</p>

          {isPhp ? (
            <div className="stats-grid-4">
              <StatMini label="PHP Files"    value={filesScanned}  accent={accent} />
              <StatMini label="Total Issues" value={totalIssues}   accent="#f87171" />
              <StatMini label="Auto-fixable" value={autoChanges}   accent="#22c55e" />
              <StatMini label="Manual"       value={manualItems}   accent="#f87171" />
              <StatMini label="Effort (hrs)" value={effortHours}   />
              <StatMini label="Risk Level"   value={riskLevel}     accent="#f59e0b" />
              <StatMini label="AI Processed" value={ai?.successful ?? '—'} accent={accent} />
              <StatMini label="Confidence"   value={`${confidence}%`} accent={accent} />
            </div>
          ) : (
            <div className="stats-grid-4">
              <StatMini label="Files"        value={filesScanned}  accent={accent} />
              <StatMini label="Auto Actions" value={autoChanges}   accent={accent} />
              <StatMini label="Manual"       value={manualItems}   accent="#f87171" />
              <StatMini label="Effort (hrs)" value={effortHours}   />
              <StatMini label="Risk"         value={riskLevel}     accent="#f59e0b" />
              <StatMini label="AI ok"        value={ai?.successful ?? '—'} accent="#22c55e" />
              <StatMini label="AI failed"    value={ai?.failed ?? '—'}     accent="#f87171" />
              <StatMini label="Confidence"   value={`${confidence}%`} accent={accent} />
            </div>
          )}

          {/* Migration path for PHP */}
          {isPhp && pathSteps.length > 0 && (
            <div className="migration-path">
              <h4 className="path-title">Migration Path</h4>
              <div className="path-steps">
                {pathSteps.map((s, i) => (
                  <React.Fragment key={i}>
                    <div className="path-step">
                      <span className="path-ver">{s.from}</span>
                    </div>
                    <ChevronRight size={12} color="#4b5563" />
                    {i === pathSteps.length - 1 && (
                      <div className="path-step active">
                        <span className="path-ver" style={{ color: accent }}>{s.to}</span>
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}

          {/* Change breakdown for Angular from files */}
          {isAngle && files.length > 0 && (
            <div className="category-bars">
              <h4 className="path-title" style={{ marginBottom: '12px' }}>File Risk Distribution</h4>
              {files.slice(0, 5).map((f, i) => {
                const name = (f.path ?? '').split(/[\\/]/).pop();
                const score = f.risk_score ?? 0;
                return (
                  <div key={i} className="cat-bar-row">
                    <span className="cat-bar-label" style={{ fontSize: 11 }}>{name}</span>
                    <AutoBar value={score} max={1} color={score > 0.5 ? '#f87171' : score > 0.2 ? '#f59e0b' : accent} />
                    <span className="cat-bar-val">{score.toFixed(2)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── Heatmap / Issue Category ── */}
        <div className="grid-card heatmap-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <div>
              <h3 className="card-title">{isPhp ? 'Issue Category Map' : 'Complexity Heatmap'}</h3>
              <p className="card-subtitle" style={{ marginBottom: 0 }}>
                {isPhp ? 'Deprecated API Surface' : 'Codebase Surface Analysis'}
              </p>
            </div>
            <MoreHorizontal size={18} color="#4b5563" />
          </div>

          {isPhp && Object.keys(changesByCategory).length > 0 ? (
            <>
              <div className="php-category-list">
                {Object.entries(changesByCategory).map(([cat, count]) => (
                  <div key={cat} className="php-category-row">
                    <span className="php-cat-label">{cat.replace(/_/g, ' ')}</span>
                    <div className="php-cat-bar-wrap">
                      <div className="php-cat-bar" style={{ width: count > 0 ? `${Math.min(100, count * 16)}%` : '4px', background: count > 0 ? '#f87171' : '#1e293b' }} />
                    </div>
                    <span className="php-cat-count" style={{ color: count > 0 ? '#f87171' : '#4b5563' }}>{count}</span>
                  </div>
                ))}
              </div>
              {manualFileItems.length > 0 && (
                <>
                  <h4 className="path-title" style={{ marginTop: '16px', marginBottom: '10px' }}>Manual Review Items</h4>
                  <div className="manual-items-list">
                    {manualFileItems.map((item, i) => (
                      <div key={i} className="manual-item">
                        <div className="manual-item-header">
                          <span className="manual-file">{item.file}:{item.line}</span>
                          <AlertTriangle size={12} color="#f87171" />
                        </div>
                        <code className="manual-snippet">{item.snippet}</code>
                        <span className="manual-concern">{item.concern}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          ) : (
            <>
              {/* Generic heatmap based on files */}
              <div className="heatmap-grid">
                {files.length > 0 ? files.slice(0, 40).map((f, i) => {
                  const score = f.risk_score ?? 0;
                  const cls = score > 0.5 ? 'risky' : score > 0.2 ? 'high' : score > 0.05 ? 'med' : 'low';
                  return <div key={i} className={`heatmap-square ${cls}`} title={(f.path ?? '').split(/[\\/]/).pop()} />;
                }) : Array.from({ length: 20 }).map((_, i) => (
                  <div key={i} className="heatmap-square low" />
                ))}
              </div>
              <div className="heatmap-legend">
                {[['low','#1e293b','Clean'],['med','#334155','Low'],['high','#00d2ff','Med'],['risky','#f87171','High']].map(([k,c,l])=>(
                  <span key={k} className="legend-item"><span className="legend-dot" style={{background:c}}/>{l}</span>
                ))}
              </div>
              <div className="heatmap-footer">
                <div className="heatmap-info">
                  <h5>Files Needing Review</h5>
                  <p>{files.filter(f => (f.manual_review?.length ?? 0) > 0).length} of {files.length} files</p>
                </div>
              </div>
              <div className="heatmap-progress">
                <div className="progress-fill" style={{ width: `${safePercent}%`, background: accent }} />
              </div>
            </>
          )}
        </div>

        {/* ── Terminal / Indicator Log ── */}
        <div className="grid-card terminal-card">
          <div className="terminal-header">
            <div className="terminal-dots">
              <span className="t-dot" style={{ background: '#ff5f57' }} />
              <span className="t-dot" style={{ background: '#febc2e' }} />
              <span className="t-dot" style={{ background: '#28c840' }} />
            </div>
            <div className="terminal-title">
              terminal.evua — {engine}-engine-log
            </div>
            <div style={{ fontSize: '9px', color: '#30363d', letterSpacing: '1px' }}>● LIVE</div>
          </div>
          <div className="terminal-body" ref={terminalRef} id="dashboard-terminal">
            {logLines.length > 0 ? logLines.map((log, i) => (
              <div key={i} className="log-line">
                <span className="log-ts">{log.ts}</span>
                <span className={`log-lvl ${log.lvl.toLowerCase()}`}>{log.lvl}</span>
                <span className="log-msg">{log.msg}</span>
              </div>
            )) : (
              <div className="log-line">
                <span className="log-ts">[--:--:--]</span>
                <span className="log-lvl info">INFO</span>
                <span className="log-msg">No indicator output recorded for this run. Check the Migration terminal for full logs.</span>
              </div>
            )}
          </div>
        </div>

        {/* ── AI Handoff / Artifacts ── */}
        <div className="grid-card artifacts-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 className="card-title">{ai ? 'AI Handoff Summary' : 'Run Summary'}</h3>
            <span style={{ fontSize: '10px', color: '#4b5563' }}>
              {ai ? `${ai.total_items} Items` : lastRun?.status?.toUpperCase() ?? '—'}
            </span>
          </div>

          {ai ? (
            <>
              <div className="ai-handoff-stats">
                <div className="ai-stat">
                  <span className="ai-stat-num" style={{ color: '#22c55e' }}>{ai.successful}</span>
                  <span className="ai-stat-label">Successful</span>
                </div>
                <div className="ai-stat">
                  <span className="ai-stat-num" style={{ color: '#f87171' }}>{ai.failed}</span>
                  <span className="ai-stat-label">Failed</span>
                </div>
                <div className="ai-stat">
                  <span className="ai-stat-num">{ai.processed}</span>
                  <span className="ai-stat-label">Processed</span>
                </div>
              </div>
              {manualFileItems.length > 0 && (
                <div style={{ marginTop: '16px' }}>
                  <h4 className="path-title" style={{ marginBottom: '10px' }}>Auto-Fix Suggestions</h4>
                  {manualFileItems.slice(0, 3).map((item, i) => (
                    <div key={i} className="artifact-item" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '6px' }}>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', width: '100%' }}>
                        <div className="artifact-icon" style={{ background: '#f8711120' }}><Wrench size={14} color="#f87171"/></div>
                        <div className="artifact-info">
                          <span className="artifact-name">{item.file}:{item.line}</span>
                          <span className="artifact-type">{item.concern}</span>
                        </div>
                        <CheckCircle size={14} color="#22c55e" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 13, color: '#8b949e', lineHeight: 1.6 }}>
                AI handoff data not available for this run.
                {isPhp && ' Run the <strong>analyze</strong> command to generate a full report with AI metrics.'}
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 11, color: '#5a7482', letterSpacing: 1, fontWeight: 700, marginBottom: 8 }}>RUN DETAILS</div>
                {[
                  ['Engine',   engine?.toUpperCase()],
                  ['Strategy', lastRun?.strategy ?? '—'],
                  ['Command',  lastRun?.command  ?? '—'],
                  ['Status',   lastRun?.status   ?? '—'],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #21262d', fontSize: 13 }}>
                    <span style={{ color: '#6e7681' }}>{k}</span>
                    <span style={{ color: '#c9d1d9', fontFamily: 'monospace' }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </main>

      <div className="fab-container">
        <button className="fab" style={{ background: accent, boxShadow: `0 10px 30px ${accent}66` }}>
          <Plus size={24} />
        </button>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

// ── Pipeline Step sub-component ───────────────────────────────────────────────

const PipelineStep = ({ icon, label, status, detail }) => {
  const statusClass = status === 'completed' ? 'completed' : status === 'active' ? 'active' : status === 'complete-partial' ? 'complete-partial' : '';
  return (
    <div className={`pipeline-step ${statusClass}`}>
      <div className="step-icon-box">{icon}</div>
      <div className="step-info">
        <h4>{label}</h4>
        <p>{detail}</p>
        {status === 'completed' && <span className="step-check"><CheckCircle size={12} /></span>}
      </div>
    </div>
  );
};

export default Dashboard;
