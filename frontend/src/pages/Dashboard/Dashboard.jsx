import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Layers, 
  FileCode, 
  Terminal, 
  CheckCircle, 
  Download, 
  Search, 
  Zap, 
  ShieldCheck, 
  Plus,
  ArrowRight,
  MoreHorizontal,
  Layout,
  AlertTriangle,
  Code2,
  GitMerge,
  Cpu,
  BarChart2,
  RefreshCw,
  ChevronRight,
  PackageOpen,
  Wrench,
  Database,
  Globe,
} from 'lucide-react';
import './Dashboard.css';

// ── Static data derived from real engine runs ─────────────────────────────────

const ENGINES = {
  angularjs: {
    label: 'AngularJS → Angular 17+',
    badge: 'AngularJS',
    color: '#dd0031',
    accent: '#00d2ff',
    version: 'v8.4.1 (Obsidian Core)',
    project: 'taskflow',
    filesScanned: 9,
    jsFiles: 5,
    classesFound: 18,
    routesMigrated: 11,
    changesProposed: 80,
    generatedFiles: 35,
    risk: { safe: 17, risky: 0, manual: 12 },
    confidence: Math.round((17 / 29) * 100),
    // derived
    autoModernized: [
      'TeamCtrl', 'TaskDetailCtrl', 'TaskBoardCtrl', 'ProjectDetailCtrl',
      'ProjectFormCtrl', 'ProjectListCtrl', 'DashboardCtrl', 'AuthCtrl',
      'AppCtrl', 'StorageService', 'NotificationService', 'StatsService',
      'UserService', 'TaskService', 'ProjectService', 'AuthService', 'AuthInterceptor',
    ],
    manualRequired: [
      'ProfileCtrl', 'tfNotifications', 'tfDatepicker', 'tfTooltip',
      'tfClickOutside', 'tfInfiniteScroll', 'tfTaskCard', 'tfAvatar',
      'tfProgressBar', 'tfConfirmClick', 'tfAutofocus', 'tfPriorityBadge',
    ],
    generatedFilesList: [
      { name: 'app-routing.module.ts', type: 'Router Config' },
      { name: 'auth.component.ts', type: 'Angular Component' },
      { name: 'dashboard.component.ts', type: 'Angular Component' },
      { name: 'auth.service.ts', type: 'Injectable Service' },
      { name: 'app.module.ts', type: 'NgModule' },
    ],
    logs: [
      { ts: '[08:34:01]', lvl: 'INFO',    msg: 'Ingestion: 9 files scanned (5 JS)' },
      { ts: '[08:34:02]', lvl: 'INFO',    msg: 'Analysis: 18 classes, 11 routes, 0 http calls detected' },
      { ts: '[08:34:03]', lvl: 'MAPPED',  msg: 'ControllerToComponent: 9 controllers → components' },
      { ts: '[08:34:04]', lvl: 'MAPPED',  msg: 'ServiceToInjectable: 8 services converted' },
      { ts: '[08:34:05]', lvl: 'MAPPED',  msg: 'RouteMigrator: 11 routes → provideRouter' },
      { ts: '[08:34:06]', lvl: 'MAPPED',  msg: 'DirectiveToPipe: 8 filters → Angular Pipes' },
      { ts: '[08:34:07]', lvl: 'WARN',    msg: 'MANUAL: ProfileCtrl — Deep $watch (behavioral coupling)' },
      { ts: '[08:34:08]', lvl: 'WARN',    msg: 'MANUAL: 11 directives — no deterministic Angular migration' },
      { ts: '[08:34:09]', lvl: 'INFO',    msg: 'Transform: 80 changes proposed, 35 files generated' },
      { ts: '[08:34:10]', lvl: 'SUCCESS', msg: 'Risk: 17 SAFE • 0 RISKY • 12 MANUAL' },
    ],
    pipelineStatus: 'complete', // scan, analyze, transform done; validate partly done
  },
  php: {
    label: 'PHP 5.6 → PHP 8.0',
    badge: 'PHP',
    color: '#8892bf',
    accent: '#f7df1e',
    version: 'v2.1.0 (Amber Core)',
    project: 'old_php_project',
    filesScanned: 3,
    jsFiles: null,
    classesFound: null,
    routesMigrated: null,
    changesProposed: 6, // total_issues
    generatedFiles: null,
    risk: { safe: 0, risky: 0, manual: 6 },
    confidence: 73,
    // PHP-specific
    automatable: 0,
    manualReview: 6,
    riskLevel: 'MEDIUM',
    effortHours: 2,
    changesByCategory: {
      deprecated_functions: 6,
      type_system_changes: 0,
      namespace_updates: 0,
      error_handling: 0,
      syntax_changes: 0,
    },
    migrationPath: [
      { from: '5.6', to: '7.0', label: '5.6 → 7.0' },
      { from: '7.0', to: '7.4', label: '7.0 → 7.4' },
      { from: '7.4', to: '8.0', label: '7.4 → 8.0' },
    ],
    manualItems: [
      { file: 'db.php',   line: 5,  snippet: 'mysql_connect(…)',    concern: 'mysql_* removed in PHP 7' },
      { file: 'db.php',   line: 7,  snippet: 'mysql_error()',       concern: 'mysql_* removed in PHP 7' },
      { file: 'user.php', line: 8,  snippet: 'mysql_query($query)', concern: 'mysql_* removed in PHP 7' },
      { file: 'user.php', line: 11, snippet: 'mysql_error()',       concern: 'mysql_* removed in PHP 7' },
      { file: 'user.php', line: 14, snippet: 'mysql_fetch_assoc()', concern: 'mysql_* removed in PHP 7' },
    ],
    aiHandoff: {
      total: 6, processed: 6, successful: 6, failed: 0,
    },
    logs: [
      { ts: '[09:01:00]', lvl: 'INFO',    msg: 'PHP engine initialized — source: 5.6 → target: 8.0' },
      { ts: '[09:01:01]', lvl: 'INFO',    msg: 'Scanning old_php_project: 3 PHP files found' },
      { ts: '[09:01:02]', lvl: 'INFO',    msg: 'Analyzing config.php — complexity: 2, LOC: 4' },
      { ts: '[09:01:03]', lvl: 'INFO',    msg: 'Analyzing db.php — complexity: 5, LOC: 11' },
      { ts: '[09:01:04]', lvl: 'WARN',    msg: 'MANUAL: db.php:5 — mysql_connect() removed in PHP 7' },
      { ts: '[09:01:05]', lvl: 'WARN',    msg: 'MANUAL: db.php:7 — mysql_error() removed in PHP 7' },
      { ts: '[09:01:06]', lvl: 'WARN',    msg: 'MANUAL: db.php:10 — mysql_select_db() removed in PHP 7' },
      { ts: '[09:01:07]', lvl: 'INFO',    msg: 'Analyzing user.php — complexity: 4, LOC: 12' },
      { ts: '[09:01:08]', lvl: 'WARN',    msg: 'MANUAL: user.php:8 — mysql_query() removed in PHP 7' },
      { ts: '[09:01:09]', lvl: 'WARN',    msg: 'MANUAL: user.php:11 — mysql_error() removed in PHP 7' },
      { ts: '[09:01:10]', lvl: 'WARN',    msg: 'MANUAL: user.php:14 — mysql_fetch_assoc() removed in PHP 7' },
      { ts: '[09:01:11]', lvl: 'INFO',    msg: 'AI Handoff: 6 items queued → 6 processed, 6 successful' },
      { ts: '[09:01:12]', lvl: 'SUCCESS', msg: 'Migration path: 5.6 → 7.0 → 7.4 → 8.0 (3 steps)' },
    ],
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const AutoBar = ({ value, max, color = '#00d2ff' }) => (
  <div className="auto-bar-track">
    <div className="auto-bar-fill" style={{ width: `${(value / max) * 100}%`, background: color }} />
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
    <span className="stat-mini-val" style={accent ? { color: accent } : {}}>{value}</span>
    <span className="stat-mini-label">{label}</span>
    {sub && <span className="stat-mini-sub">{sub}</span>}
  </div>
);

// ── Main Component ────────────────────────────────────────────────────────────

const Dashboard = () => {
  const [activeEngine, setActiveEngine] = useState('angularjs');
  const [logVisible, setLogVisible] = useState(true);
  const terminalRef = useRef(null);
  const eng = ENGINES[activeEngine];

  // Auto-scroll terminal on log change
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [activeEngine]);

  const totalNodes = (eng.risk?.safe ?? 0) + (eng.risk?.risky ?? 0) + (eng.risk?.manual ?? 0);
  const safePercent  = totalNodes > 0 ? Math.round((eng.risk.safe   / totalNodes) * 100) : 0;
  const riskyPercent = totalNodes > 0 ? Math.round((eng.risk.risky  / totalNodes) * 100) : 0;
  const manualPercent= totalNodes > 0 ? Math.round((eng.risk.manual / totalNodes) * 100) : 0;

  return (
    <div className="dashboard-container">

      {/* ── HEADER ──────────────────────────────────────────────────────────── */}
      <header className="dashboard-header">
        <div className="header-left">
          <div className="session-badge">
            <span className="badge-tag">MISSION CONTROL</span>
            <span className="session-id">Engine Report</span>
          </div>
          <h1 className="header-title">Migration Dashboard</h1>
          <div className="header-subtitle">
            <span className="engine-badge" style={{ borderColor: eng.accent + '40', color: eng.accent }}>
              {eng.label}
            </span>
            <span className="engine-version">Engine: {eng.version}</span>
          </div>
        </div>

        {/* Engine switcher + top metrics */}
        <div className="header-right">
          {/* Engine tabs */}
          <div className="engine-tabs">
            <button
              className={`engine-tab ${activeEngine === 'angularjs' ? 'active' : ''}`}
              onClick={() => setActiveEngine('angularjs')}
              style={activeEngine === 'angularjs' ? { borderColor: '#00d2ff', color: '#00d2ff' } : {}}
            >
              <Globe size={14} /> AngularJS
            </button>
            <button
              className={`engine-tab ${activeEngine === 'php' ? 'active' : ''}`}
              onClick={() => setActiveEngine('php')}
              style={activeEngine === 'php' ? { borderColor: '#f7df1e', color: '#f7df1e' } : {}}
            >
              <Database size={14} /> PHP
            </button>
          </div>

          {/* Top metric cards */}
          <div className="metric-card">
            <span className="metric-label">Confidence</span>
            <span className="metric-value highlight" style={{ color: eng.accent }}>{eng.confidence}%</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Files Scanned</span>
            <span className="metric-value">{eng.filesScanned}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Changes Proposed</span>
            <span className="metric-value">{eng.changesProposed}</span>
          </div>
        </div>
      </header>

      {/* ── PIPELINE TIMELINE ───────────────────────────────────────────────── */}
      <section className="pipeline-section">
        <PipelineStep icon={<Search size={18}/>}     label="Scan"
          status={activeEngine === 'angularjs' ? 'completed' : 'completed'}
          detail={activeEngine === 'angularjs' ? `${eng.filesScanned} files (${eng.jsFiles} JS)` : `${eng.filesScanned} PHP files`} />
        <div className="pipeline-connector" />
        <PipelineStep icon={<Activity size={18}/>}   label="Analyze"
          status="completed"
          detail={activeEngine === 'angularjs' ? `${eng.classesFound} classes, ${eng.routesMigrated} routes` : `${eng.changesProposed} issues found`} />
        <div className="pipeline-connector" />
        <PipelineStep icon={<Zap size={18}/>}        label="Transform"
          status={activeEngine === 'angularjs' ? 'active' : 'complete-partial'}
          detail={activeEngine === 'angularjs' ? `${eng.changesProposed} changes, ${eng.generatedFiles} files` : `${eng.automatable} auto-fix`} />
        <div className="pipeline-connector" />
        <PipelineStep icon={<ShieldCheck size={18}/>} label="Validate"
          status={activeEngine === 'angularjs' ? 'pending' : 'complete-partial'}
          detail={activeEngine === 'angularjs' ? 'Awaiting TSC' : `AI: ${eng.aiHandoff?.successful ?? 0}/${eng.aiHandoff?.total ?? 0} ok`} />
      </section>

      {/* ── MAIN GRID ───────────────────────────────────────────────────────── */}
      <main className="dashboard-main-grid">

        {/* ── Risk Breakdown ── */}
        <div className="grid-card">
          <h3 className="card-title">Risk Breakdown</h3>
          <p className="card-subtitle">By Migration Category</p>

          <div className="risk-pills-row">
            <RiskPill count={eng.risk.safe}   label="SAFE"   color="#22c55e" />
            <RiskPill count={eng.risk.risky}  label="RISKY"  color="#f59e0b" />
            <RiskPill count={eng.risk.manual} label="MANUAL" color="#f87171" />
          </div>

          <div className="risk-bars">
            <div className="risk-bar-row">
              <span className="risk-bar-label">Safe</span>
              <AutoBar value={eng.risk.safe}   max={Math.max(totalNodes, 1)} color="#22c55e" />
              <span className="risk-bar-pct">{safePercent}%</span>
            </div>
            <div className="risk-bar-row">
              <span className="risk-bar-label">Risky</span>
              <AutoBar value={eng.risk.risky}  max={Math.max(totalNodes, 1)} color="#f59e0b" />
              <span className="risk-bar-pct">{riskyPercent}%</span>
            </div>
            <div className="risk-bar-row">
              <span className="risk-bar-label">Manual</span>
              <AutoBar value={eng.risk.manual} max={Math.max(totalNodes, 1)} color="#f87171" />
              <span className="risk-bar-pct">{manualPercent}%</span>
            </div>
          </div>

          {/* Radar SVG */}
          <div className="radar-container">
            <svg viewBox="0 0 200 200" width="100%" height="100%">
              <polygon points="100,20 180,75 150,165 50,165 20,75" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
              <polygon points="100,50 150,85 130,140 70,140 50,85" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
              <polygon
                points={`100,${40 + (eng.risk.manual/Math.max(totalNodes,1))*30} ${140 + (eng.risk.risky/Math.max(totalNodes,1))*20},${80 + (eng.risk.risky/Math.max(totalNodes,1))*10} ${135 - (eng.risk.risky/Math.max(totalNodes,1))*10},${148} ${65},${130} ${40 + (eng.risk.safe/Math.max(totalNodes,1))*20},${70 + (eng.risk.safe/Math.max(totalNodes,1))*10}`}
                fill={`${eng.accent}26`}
                stroke={eng.accent}
                strokeWidth="1.5"
              />
              <circle cx="100" cy="40" r="3" fill="#f87171" />
              <circle cx="160" cy="80" r="3" fill="#fff" />
              <circle cx="140" cy="150" r="3" fill="#fff" />
              <circle cx="60"  cy="130" r="3" fill={eng.accent} />
              <circle cx="40"  cy="70"  r="3" fill="#fff" />
            </svg>
          </div>
          <div className="radar-labels">
            <div className="radar-label"><span className="dot" style={{background: '#22c55e'}}></span> SAFE</div>
            <div className="radar-label"><span className="dot" style={{background: '#f87171'}}></span> MANUAL</div>
          </div>
        </div>

        {/* ── Engine Stats / Key Metrics ── */}
        <div className="grid-card stats-card">
          <h3 className="card-title">Engine Stats</h3>
          <p className="card-subtitle">Live run — {eng.project}</p>

          {activeEngine === 'angularjs' ? (
            <div className="stats-grid-4">
              <StatMini label="Classes"         value={eng.classesFound}    accent={eng.accent} />
              <StatMini label="Routes Migrated" value={eng.routesMigrated}  accent={eng.accent} />
              <StatMini label="Generated Files" value={eng.generatedFiles}  />
              <StatMini label="Auto-Modernized" value={eng.autoModernized?.length} />
              <StatMini label="Needs Manual"    value={eng.manualRequired?.length} accent="#f87171" />
              <StatMini label="0 Risky"         value={eng.risk.risky}      accent="#f59e0b" />
              <StatMini label="JS Files"        value={eng.jsFiles}         sub="of total" />
              <StatMini label="Confidence"      value={`${eng.confidence}%`} accent={eng.accent} />
            </div>
          ) : (
            <div className="stats-grid-4">
              <StatMini label="PHP Files"      value={eng.filesScanned}    accent={eng.accent} />
              <StatMini label="Total Issues"   value={eng.changesProposed} accent="#f87171" />
              <StatMini label="Auto-fixable"   value={eng.automatable}     accent="#22c55e" />
              <StatMini label="Manual Review"  value={eng.manualReview}    accent="#f87171" />
              <StatMini label="Effort (hrs)"   value={eng.effortHours}     />
              <StatMini label="Risk Level"     value={eng.riskLevel}       accent="#f59e0b" />
              <StatMini label="AI Processed"   value={eng.aiHandoff?.successful}  accent={eng.accent} />
              <StatMini label="Confidence"     value={`${eng.confidence}%`} accent={eng.accent} />
            </div>
          )}

          {/* Migration path for PHP or transformation summary for AngularJS */}
          {activeEngine === 'php' && (
            <div className="migration-path">
              <h4 className="path-title">Migration Path</h4>
              <div className="path-steps">
                {eng.migrationPath.map((s, i) => (
                  <React.Fragment key={i}>
                    <div className="path-step">
                      <span className="path-ver">{s.from}</span>
                    </div>
                    <ChevronRight size={12} color="#4b5563" />
                    {i === eng.migrationPath.length - 1 && (
                      <div className="path-step active">
                        <span className="path-ver" style={{ color: eng.accent }}>{s.to}</span>
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}

          {activeEngine === 'angularjs' && (
            <div className="category-bars">
              <h4 className="path-title" style={{ marginBottom: '12px' }}>Change Breakdown</h4>
              {[
                { label: 'Controllers → Components', val: 9, max: 18, color: eng.accent },
                { label: 'Services → Injectables', val: 8, max: 18, color: '#818cf8' },
                { label: 'Directives → Components', val: 11, max: 18, color: '#f87171' },
                { label: 'Filters → Pipes', val: 8, max: 18, color: '#22c55e' },
                { label: 'Routes Migrated', val: eng.routesMigrated, max: 18, color: '#f59e0b' },
              ].map((row, i) => (
                <div key={i} className="cat-bar-row">
                  <span className="cat-bar-label">{row.label}</span>
                  <AutoBar value={row.val} max={row.max} color={row.color} />
                  <span className="cat-bar-val">{row.val}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Complexity / Category Heatmap ── */}
        <div className="grid-card heatmap-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <div>
              <h3 className="card-title">{activeEngine === 'angularjs' ? 'Complexity Heatmap' : 'Issue Category Map'}</h3>
              <p className="card-subtitle" style={{ marginBottom: 0 }}>
                {activeEngine === 'angularjs' ? 'Codebase Surface Analysis' : 'Deprecated API Surface'}
              </p>
            </div>
            <MoreHorizontal size={18} color="#4b5563" />
          </div>

          {activeEngine === 'angularjs' ? (
            <>
              <div className="heatmap-grid">
                {Array.from({ length: 40 }).map((_, i) => {
                  const levels = ['low', 'low', 'med', 'low', 'high', 'low', 'risky', 'low', 'med', 'low'];
                  return <div key={i} className={`heatmap-square ${levels[i % levels.length]}`} />;
                })}
              </div>
              <div className="heatmap-legend">
                {[['low','#1e293b','Low'],['med','#334155','Medium'],['high','#00d2ff','High'],['risky','#f87171','Risky']].map(([k,c,l])=>(
                  <span key={k} className="legend-item"><span className="legend-dot" style={{background:c}}/>{l}</span>
                ))}
              </div>
              <div className="heatmap-footer">
                <div className="heatmap-info">
                  <h5>Legacy Components</h5>
                  <p>{eng.manualRequired?.length} Require Manual Work</p>
                </div>
              </div>
              <div className="heatmap-progress">
                <div className="progress-fill" style={{ width: `${safePercent}%`, background: eng.accent }} />
              </div>
            </>
          ) : (
            <>
              {/* PHP category breakdown */}
              <div className="php-category-list">
                {Object.entries(eng.changesByCategory || {}).map(([cat, count]) => (
                  <div key={cat} className="php-category-row">
                    <span className="php-cat-label">{cat.replace(/_/g, ' ')}</span>
                    <div className="php-cat-bar-wrap">
                      <div className="php-cat-bar" style={{ width: count > 0 ? `${Math.min(100, count * 16)}%` : '4px', background: count > 0 ? '#f87171' : '#1e293b' }} />
                    </div>
                    <span className="php-cat-count" style={{ color: count > 0 ? '#f87171' : '#4b5563' }}>{count}</span>
                  </div>
                ))}
              </div>
              {/* Manual review items */}
              <h4 className="path-title" style={{ marginTop: '16px', marginBottom: '10px' }}>Manual Review Items</h4>
              <div className="manual-items-list">
                {eng.manualItems?.slice(0, 4).map((item, i) => (
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
        </div>

        {/* ── Terminal Log ── */}
        <div className="grid-card terminal-card">
          <div className="terminal-header">
            <div className="terminal-dots">
              <span className="t-dot" style={{ background: '#ff5f57' }} />
              <span className="t-dot" style={{ background: '#febc2e' }} />
              <span className="t-dot" style={{ background: '#28c840' }} />
            </div>
            <div className="terminal-title">
              terminal.evua — {activeEngine}-engine-log
            </div>
            <div style={{ fontSize: '9px', color: '#30363d', letterSpacing: '1px' }}>● LIVE</div>
          </div>
          <div className="terminal-body" ref={terminalRef} id="dashboard-terminal">
            {eng.logs.map((log, i) => (
              <div key={i} className="log-line">
                <span className="log-ts">{log.ts}</span>
                <span className={`log-lvl ${log.lvl.toLowerCase()}`}>{log.lvl}</span>
                <span className="log-msg">{log.msg}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Artifacts / Auto-Modernized ── */}
        <div className="grid-card artifacts-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 className="card-title">
              {activeEngine === 'angularjs' ? 'Generated Artifacts' : 'AI Handoff Summary'}
            </h3>
            <span style={{ fontSize: '10px', color: '#4b5563' }}>
              {activeEngine === 'angularjs' ? `${eng.generatedFiles} Total` : `${eng.aiHandoff?.total} Items`}
            </span>
          </div>

          {activeEngine === 'angularjs' ? (
            <>
              <div className="artifacts-list">
                {eng.generatedFilesList.map((art, i) => (
                  <div key={i} className="artifact-item">
                    <div className="artifact-icon"><FileCode size={16} /></div>
                    <div className="artifact-info">
                      <span className="artifact-name">{art.name}</span>
                      <span className="artifact-type">{art.type}</span>
                    </div>
                    <button className="download-btn"><Download size={16}/></button>
                  </div>
                ))}
              </div>
              <button className="export-btn">EXPORT ALL {eng.generatedFiles} ARTIFACTS</button>
            </>
          ) : (
            <>
              {/* AI Handoff stats */}
              <div className="ai-handoff-stats">
                <div className="ai-stat">
                  <span className="ai-stat-num" style={{ color: '#22c55e' }}>{eng.aiHandoff?.successful}</span>
                  <span className="ai-stat-label">Successful</span>
                </div>
                <div className="ai-stat">
                  <span className="ai-stat-num" style={{ color: '#f87171' }}>{eng.aiHandoff?.failed}</span>
                  <span className="ai-stat-label">Failed</span>
                </div>
                <div className="ai-stat">
                  <span className="ai-stat-num">{eng.aiHandoff?.processed}</span>
                  <span className="ai-stat-label">Processed</span>
                </div>
              </div>
              <div style={{ marginTop: '16px' }}>
                <h4 className="path-title" style={{ marginBottom: '10px' }}>Auto-Fix Suggestions</h4>
                {eng.manualItems?.slice(0,3).map((item, i) => (
                  <div key={i} className="artifact-item" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '6px' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', width: '100%' }}>
                      <div className="artifact-icon" style={{ background: '#f8711120' }}><Wrench size={14} color="#f87171"/></div>
                      <div className="artifact-info">
                        <span className="artifact-name">{item.file}:{item.line}</span>
                        <span className="artifact-type">Replace with mysqli_* or PDO</span>
                      </div>
                      <CheckCircle size={14} color="#22c55e" />
                    </div>
                  </div>
                ))}
              </div>
              <button className="export-btn" style={{ marginTop: '16px' }}>EXPORT PHP MIGRATION REPORT</button>
            </>
          )}
        </div>

      </main>

      {/* FAB */}
      <div className="fab-container">
        <button className="fab" style={{ background: eng.accent, boxShadow: `0 10px 30px ${eng.accent}66` }}>
          <Plus size={24} />
        </button>
      </div>

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
