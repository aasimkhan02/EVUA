import React, { useEffect, useMemo, useState } from 'react';
import { Share2, Download, FileText, AlertTriangle, Search, ListChecks, Cpu as CpuIcon } from 'lucide-react';
import './Validation.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const Validation = () => {
  const [lastRun, setLastRun] = useState(null);
  const [reportJson, setReportJson] = useState(null);
  const [reportMarkdown, setReportMarkdown] = useState('');
  const [loadingReport, setLoadingReport] = useState(false);
  const [reportError, setReportError] = useState('');

  const canExport = useMemo(() => Boolean(reportJson || reportMarkdown), [reportJson, reportMarkdown]);

  // ── Load report on mount ──────────────────────────────────────────────────
  useEffect(() => {
    const savedRun = localStorage.getItem('evua:last-run');
    if (!savedRun) return;

    let parsedRun;
    try {
      parsedRun = JSON.parse(savedRun);
      setLastRun(parsedRun);
    } catch {
      setReportError('Unable to parse last run details.');
      return;
    }

    if (!parsedRun?.engine || !parsedRun?.projectName) {
      setReportError('Last run details are incomplete.');
      return;
    }

    const loadReports = async () => {
      setLoadingReport(true);
      setReportError('');
      try {
        const jsonRes = await fetch(
          `${API_BASE}/report?engine=${encodeURIComponent(parsedRun.engine)}&project_name=${encodeURIComponent(parsedRun.projectName)}&format=json`
        );
        if (jsonRes.ok) {
          const jsonData = await jsonRes.json();
          setReportJson(jsonData.content);
        }

        const mdRes = await fetch(
          `${API_BASE}/report?engine=${encodeURIComponent(parsedRun.engine)}&project_name=${encodeURIComponent(parsedRun.projectName)}&format=md`
        );
        if (mdRes.ok) {
          const mdData = await mdRes.json();
          setReportMarkdown(mdData.content || '');
        }

        if (!jsonRes.ok && !mdRes.ok) {
          setReportError('No report found for the last migration run yet.');
        }
      } catch {
        setReportError('Failed to fetch report data from backend.');
      } finally {
        setLoadingReport(false);
      }
    };

    loadReports();
  }, []);

  // ── Derived data from JSON ────────────────────────────────────────────────
  const m         = reportJson?.metadata || {};
  const s         = reportJson?.summary  || {};
  const files     = reportJson?.files    || [];
  const pathSteps = reportJson?.migration_path || [];
  const ai        = reportJson?.ai_handoff_summary || null;

  const totalFiles  = m.files_analyzed || files.length || 0;
  const autoChanges = s.automatable_changes   || 0;
  const manualItems = s.manual_review_items   || 0;
  const effortHours = typeof s.estimated_effort_hours === 'number' ? s.estimated_effort_hours : 0;
  const riskLevel   = s.risk_level || (totalFiles === 0 ? 'N/A' : (manualItems > 10 ? 'HIGH' : manualItems > 0 ? 'MEDIUM' : 'LOW'));
  const issues      = m.total_issues !== undefined ? m.total_issues : manualItems;
  const riskColor   = riskLevel === 'HIGH' ? '#f85149' : riskLevel === 'MEDIUM' ? '#e3b341' : '#3fb950';

  const autoBarWidth   = `${(autoChanges   / Math.max(autoChanges + manualItems, 1)) * 100}%`;
  const manualBarWidth = `${(manualItems   / Math.max(autoChanges + manualItems, 1)) * 100}%`;

  // Aggregate every manual_review item from every file
  const allManualReviews = useMemo(() => {
    const list = [];
    files.forEach(f => {
      if (Array.isArray(f.manual_review)) {
        f.manual_review.forEach(rev => {
          list.push({
            file:       f.path,
            line:       rev.line,
            snippet:    rev.snippet,
            reason:     rev.reason,
            confidence: rev.confidence,
          });
        });
      }
    });
    return list;
  }, [files]);

  // ── Action handlers ───────────────────────────────────────────────────────
  const handleShare = async () => {
    const shareText = lastRun
      ? `EVUA report for ${lastRun.projectName} (${lastRun.engine})`
      : 'EVUA validation report';

    if (navigator.share) {
      try {
        await navigator.share({ title: 'EVUA Validation Report', text: shareText, url: window.location.href });
        return;
      } catch { /* user cancelled */ }
    }
    try {
      await navigator.clipboard.writeText(window.location.href);
      alert('Share link copied to clipboard.');
    } catch {
      alert('Share options are unavailable in this browser.');
    }
  };

  const handleExportJson = () => {
    if (!reportJson) { alert('JSON report is not available yet.'); return; }
    const fileName = `${lastRun?.projectName || 'evua-report'}.json`;
    const blob = new Blob([JSON.stringify(reportJson, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPdf = () => {
    const reportBody = reportMarkdown || JSON.stringify(reportJson || {}, null, 2);
    if (!reportBody || reportBody === '{}') { alert('No report content available for PDF export.'); return; }
    const printable = window.open('', '_blank', 'width=900,height=700');
    if (!printable) { alert('Popup blocked. Please allow popups to export PDF.'); return; }
    printable.document.write(
      '<html><head><title>EVUA Report</title>' +
      '<style>body{font-family:Arial,sans-serif;margin:20px;white-space:pre-wrap;line-height:1.5}h1{margin-bottom:12px}</style>' +
      '</head><body>' +
      '<h1>EVUA Validation Report</h1>' +
      '<p><strong>Project:</strong> ' + (lastRun?.projectName || 'unknown') + '</p>' +
      '<p><strong>Engine:</strong> '  + (lastRun?.engine      || 'unknown') + '</p>' +
      '<hr />' +
      '<pre>' + String(reportBody).replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre>' +
      '</body></html>'
    );
    printable.document.close();
    printable.focus();
    printable.print();
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="validation-container">

      {/* HEADER */}
      <div className="validation-header">
        <div className="validation-title-section">
          <span className="validation-subtitle">SYSTEM.OUTPUT.VALIDATION</span>
          <h1 className="validation-title">Data Validation &amp; Report</h1>
          <p style={{ marginTop: '5px', color: '#9db2bf', fontSize: '12px', maxWidth: '600px', margin: '6px 0 0' }}>
            Diagnostic feedback and automated metrics collected during your last migration execution.
            Review actionable warnings and architecture audits below.
          </p>
        </div>
        <div className="validation-actions">
          <button className="btn btn-secondary" onClick={handleShare} disabled={!canExport}>
            <Share2 size={14} /> Share Report
          </button>
          <button className="btn btn-secondary" onClick={handleExportJson} disabled={!reportJson}>
            <Download size={14} /> JSON Output
          </button>
          <button className="btn btn-primary" onClick={handleDownloadPdf} disabled={!canExport}>
            <FileText size={14} /> Print PDF
          </button>
        </div>
      </div>

      {/* STATUS BANNER */}
      {(loadingReport || reportError || lastRun) && (
        <div style={{
          margin: '0 0 24px', padding: '10px 16px', background: '#1c1f24',
          borderRadius: '8px', color: '#9db2bf', fontSize: 13,
          border: '1px solid #2d333b', display: 'flex', alignItems: 'center', gap: '8px',
        }}>
          {loadingReport
            ? <span style={{ width: 14, height: 14, border: '2px solid #5a7482', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite', display: 'inline-block' }} />
            : <Search size={16} />
          }
          {loadingReport && 'Crunching telemetry and loading latest engine report...'}
          {!loadingReport && reportError && <span style={{ color: '#f85149' }}>{reportError}</span>}
          {!loadingReport && !reportError && lastRun && (
            <span>
              Target: <strong style={{ color: '#c9d1d9' }}>{lastRun.projectName}</strong>
              {' · '}Engine: <strong style={{ color: '#c9d1d9' }}>{lastRun.engine.toUpperCase()}</strong>
              {' · '}Time: {m.timestamp ? new Date(m.timestamp).toLocaleString() : 'Recent'}
            </span>
          )}
        </div>
      )}

      {/* MAIN CONTENT — only shown when report is loaded */}
      {reportJson && !loadingReport && (
        <div className="validation-dashboard">

          {/* ── TOP METRICS ROW ─────────────────────────────────────────── */}
          <div className="dashboard-row top-row">

            <div className="dash-card metric-block">
              <div className="card-heading">SYSTEM RISK LEVEL</div>
              <div className="metric-row">
                <span className="metric-large" style={{ color: riskColor }}>{riskLevel}</span>
              </div>
              <div className="progress-label">{issues} Total Flags Triggered</div>
            </div>

            <div className="dash-card metric-block">
              <div className="card-heading">ESTIMATED EFFORT</div>
              <div className="metric-row">
                <span className="metric-large" style={{ color: effortHours > 0 ? '#e3b341' : '#3fb950' }}>
                  {effortHours}
                  <span style={{ fontSize: '18px', opacity: 0.7, marginLeft: 6 }}>Hrs</span>
                </span>
              </div>
              <div className="progress-label">To Resolve Manual Items</div>
            </div>

            <div className="dash-card metric-block">
              <div className="card-heading">CODEBASE SURFACE</div>
              <div className="metric-row">
                <span className="metric-large pass-text">{totalFiles}</span>
                <span className="metric-sub">FILES</span>
              </div>
              <div className="progress-label">Analyzed in execution</div>
            </div>

            <div className="dash-card metric-block">
              <div className="card-heading">ACTION DISTRIBUTION</div>
              <div className="action-dist-bars">
                <div className="dist-row">
                  <div style={{ width: '60px', fontSize: 13, color: '#c9d1d9' }}>Auto</div>
                  <div className="progress-track" style={{ flex: 1 }}>
                    <div className="progress-fill pass-fill" style={{ width: autoBarWidth }} />
                  </div>
                  <div style={{ width: '30px', textAlign: 'right', color: '#3fb950', fontSize: 13 }}>{autoChanges}</div>
                </div>
                <div className="dist-row">
                  <div style={{ width: '60px', fontSize: 13, color: '#c9d1d9' }}>Manual</div>
                  <div className="progress-track" style={{ flex: 1 }}>
                    <div className="progress-fill warn-fill" style={{ width: manualBarWidth }} />
                  </div>
                  <div style={{ width: '30px', textAlign: 'right', color: '#e3b341', fontSize: 13 }}>{manualItems}</div>
                </div>
              </div>
            </div>

          </div>

          {/* ── MIDDLE ROW ──────────────────────────────────────────────── */}
          <div className="dashboard-row bottom-row">

            {/* Migration Path Timeline */}
            <div className="dash-card path-card" style={{ flex: 1 }}>
              <div className="card-heading">MIGRATION PATH CONTINUUM</div>
              {pathSteps.length > 0 ? (
                <div className="path-timeline">
                  {pathSteps.map((step, idx) => (
                    <React.Fragment key={step.step}>
                      <div className="path-node">
                        <span style={{ fontSize: '12px', color: '#5a7482', fontWeight: 600 }}>v{step.from}</span>
                        <div style={{ width: 16, height: 16, borderRadius: '50%', background: '#3fb950', border: '3px solid #1c1f24', boxShadow: '0 0 0 2px #3fb95040' }} />
                      </div>
                      <div className="path-line" />
                      {idx === pathSteps.length - 1 && (
                        <div className="path-node">
                          <span style={{ fontSize: '12px', color: '#00d2ff', fontWeight: 600 }}>v{step.to}</span>
                          <div style={{ width: 18, height: 18, borderRadius: '50%', background: '#00d2ff', border: '3px solid #1c1f24', boxShadow: '0 0 0 2px #00d2ff40' }} />
                        </div>
                      )}
                    </React.Fragment>
                  ))}
                </div>
              ) : (
                <div style={{ height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#5a7482', fontSize: 13 }}>
                  Standard full-run strategy — no explicit version path.
                </div>
              )}
            </div>

            {/* AI Handoff Stats */}
            {ai && (
              <div className="dash-card" style={{ width: 380 }}>
                <div className="card-heading" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CpuIcon size={14} color="#a855f7" />
                  <span>AI NEURAL RESOLUTION</span>
                </div>
                <div className="ai-stats-grid">
                  <div style={{ background: '#121418', padding: 12, borderRadius: 6 }}>
                    <div style={{ fontSize: 10, color: '#5a7482', fontWeight: 700, letterSpacing: 1 }}>ACCURACY</div>
                    <div style={{ fontSize: 28, fontWeight: 300, color: '#c9d1d9', marginTop: 4 }}>
                      {ai.total_items > 0 ? Math.round((ai.successful / ai.total_items) * 100) : 0}%
                    </div>
                  </div>
                  <div style={{ background: '#121418', padding: 12, borderRadius: 6 }}>
                    <div style={{ fontSize: 10, color: '#5a7482', fontWeight: 700, letterSpacing: 1 }}>PROCESSED</div>
                    <div style={{ fontSize: 28, fontWeight: 300, color: '#c9d1d9', marginTop: 4 }}>
                      {ai.processed} / {ai.total_items}
                    </div>
                  </div>
                  <div style={{ background: '#121418', padding: 12, borderRadius: 6 }}>
                    <div style={{ fontSize: 10, color: '#5a7482', fontWeight: 700, letterSpacing: 1 }}>SUCCESSFUL</div>
                    <div style={{ fontSize: 28, fontWeight: 300, color: '#3fb950', marginTop: 4 }}>{ai.successful}</div>
                  </div>
                  <div style={{ background: '#121418', padding: 12, borderRadius: 6 }}>
                    <div style={{ fontSize: 10, color: '#5a7482', fontWeight: 700, letterSpacing: 1 }}>FAILED</div>
                    <div style={{ fontSize: 28, fontWeight: 300, color: ai.failed > 0 ? '#f85149' : '#c9d1d9', marginTop: 4 }}>{ai.failed}</div>
                  </div>
                </div>
              </div>
            )}

          </div>

          {/* ── FILE INTEGRITY TABLE ─────────────────────────────────────── */}
          <div className="dash-card manifest-card" style={{ marginTop: 24 }}>
            <div className="manifest-header" style={{ marginBottom: 16 }}>
              <div className="card-heading">ARCHITECTURAL FILE INTEGRITY</div>
              <div className="manifest-legend">
                <span className="legend-item"><span className="dot pass-dot" /> Low Risk</span>
                <span className="legend-item"><span className="dot warn-dot" /> Needs Review</span>
              </div>
            </div>

            <div className="manifest-table" style={{ maxHeight: 350, overflowY: 'auto' }}>
              <div className="table-header">
                <div className="col entity" style={{ flex: 2 }}>FILE PATH</div>
                <div className="col type">COMPLEXITY</div>
                <div className="col type">LOC</div>
                <div className="col status">STATUS</div>
                <div className="col complexity">RISK SCORE</div>
              </div>

              {files.map((file, i) => {
                const isWarn    = file.manual_review?.length > 0;
                const segments  = file.path.split(/[\\/]/);
                const baseName  = segments.pop();
                const dir       = segments.join('/');
                return (
                  <div className="table-row" key={i}>
                    <div className="col entity mono-val" style={{ flex: 2, display: 'flex', flexDirection: 'column' }}>
                      <span style={{ color: '#c9d1d9', fontWeight: 500 }}>{baseName}</span>
                      <span style={{ fontSize: 10, color: '#5a7482' }}>{dir || '/'}</span>
                    </div>
                    <div className="col type mono-val">{file.metrics?.cyclomatic_complexity ?? '--'}</div>
                    <div className="col type mono-val">{file.metrics?.lines_of_code ?? '--'}</div>
                    <div className="col status">
                      {isWarn
                        ? <span className="badge badge-partial">REVIEW</span>
                        : <span className="badge badge-full">PASS</span>
                      }
                    </div>
                    <div className="col complexity mono-val">
                      {file.risk_score !== undefined ? file.risk_score.toFixed(2) : '--'}
                      {file.risk_score > 0.1 && (
                        <span className="complex-warn" style={{ marginLeft: 8 }}>O(N)</span>
                      )}
                    </div>
                  </div>
                );
              })}

              {files.length === 0 && (
                <div style={{ textAlign: 'center', padding: 30, color: '#5a7482', fontSize: 13 }}>
                  No structural file metrics recorded in this execution run.
                </div>
              )}
            </div>
          </div>

          {/* ── ACTIONABLE REVIEW LOG ────────────────────────────────────── */}
          <div className="actionable-review-section">
            <div className="review-section-header">
              <div className="review-title-group">
                <h2>Actionable Review Log</h2>
                {allManualReviews.length > 0 && (
                  <span className="badge-critical">{allManualReviews.length} Interventions</span>
                )}
              </div>
              <span className="review-subtitle">
                Code blocks demanding manual developer intervention due to missing migration heuristics.
              </span>
            </div>

            <div className="review-cards">
              {allManualReviews.map((rev, idx) => {
                const truncFile = rev.file.split(/[\\/]/).pop();
                return (
                  <div className="review-card" key={idx}>
                    <div className="review-content">
                      <div className="review-card-header">
                        <AlertTriangle size={18} color="#fdb877" />
                        <h3>{rev.reason || 'Intervention Required'}</h3>
                        <span className="file-badge" style={{ textTransform: 'uppercase' }}>
                          {truncFile}:{rev.line}
                        </span>
                      </div>
                      <p className="review-desc">
                        The migration engine flagged this snippet during AST traversal.
                        Engine confidence:{' '}
                        <strong style={{ color: '#00d2ff' }}>
                          {typeof rev.confidence === 'number' ? `${Math.round(rev.confidence * 100)}%` : 'N/A'}
                        </strong>
                      </p>
                      <div className="review-actions">
                        <button className="btn-action primary-action">Resolve in Editor</button>
                        <button className="btn-action secondary-action">Ignore Rule</button>
                      </div>
                    </div>

                    <div className="review-code-diff">
                      <div className="diff-header">
                        <span>OBSTRUCTING SNIPPET</span>
                        <span className="diff-status unresolved">UNRESOLVED</span>
                      </div>
                      <div className="diff-lines">
                        <div className="d-line removed">
                          <span className="ln">{rev.line}</span>
                          <span className="code" style={{ color: '#ffb3b0' }}>{rev.snippet}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {allManualReviews.length === 0 && (
                <div style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 40,
                  background: '#1c1f24', borderRadius: 12, border: '1px dashed #2d333b', color: '#9db2bf',
                }}>
                  <ListChecks size={32} style={{ marginBottom: 16, color: '#3fb950' }} />
                  <h3 style={{ fontSize: 15, color: '#c9d1d9', marginBottom: 8 }}>Clean Traversal</h3>
                  <p style={{ fontSize: 13 }}>
                    The migration engine resolved all AST nodes automatically. No manual review required.
                  </p>
                </div>
              )}
            </div>
          </div>

        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default Validation;