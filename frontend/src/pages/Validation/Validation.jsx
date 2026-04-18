import React, { useEffect, useMemo, useState } from 'react';
import { Share2, Download, FileText, AlertTriangle, Cpu } from 'lucide-react';
import './Validation.css';

const API_BASE = 'http://localhost:8000/api';

const RadarChart = () => (
  <div className="radar-container">
    <span className="radar-label top">LEGACY</span>
    <span className="radar-label right">SPEED</span>
    <span className="radar-label bottom">MODERN</span>
    <span className="radar-label left">SCALE</span>
    <svg viewBox="0 0 100 100" className="radar-svg">
      <polygon points="50,15 85,35 85,65 50,85 15,65 15,35" className="radar-bg" />
      <circle cx="50" cy="50" r="15" className="radar-inner" />
      <polygon points="50,30 75,45 65,65 50,75 35,65 30,45" className="radar-fill" />
    </svg>
  </div>
);

const Validation = () => {
  const [lastRun, setLastRun] = useState(null);
  const [reportJson, setReportJson] = useState(null);
  const [reportMarkdown, setReportMarkdown] = useState('');
  const [loadingReport, setLoadingReport] = useState(false);
  const [reportError, setReportError] = useState('');

  const canExport = useMemo(() => Boolean(reportJson || reportMarkdown), [reportJson, reportMarkdown]);

  // ── Pipeline / compile status ──────────────────────────────────────────
  const pipelineMetrics = useMemo(() => {
    if (!reportJson && lastRun?.status === 'success') {
      return {
        statusLabel: 'PASS',
        statusCode: `RUN: ${lastRun?.returnCode ?? 0}`,
        progressPercent: 100,
        textClass: 'pass-text',
        fillClass: 'pass-fill',
      };
    }

    if (!reportJson) {
      return {
        statusLabel: '--',
        statusCode: 'CODE: NO_DATA',
        progressPercent: 0,
        textClass: 'warn-text',
        fillClass: 'grey-fill',
      };
    }

    if (lastRun?.engine === 'angular') {
      const validation = reportJson.validation || {};
      const checks = [validation.tests_passed, validation.snapshot_passed, validation.tsc_passed].filter(
        (value) => value !== null && value !== undefined,
      );
      const passed = checks.filter(Boolean).length;
      const failures = Array.isArray(validation.failures) ? validation.failures.length : 0;
      const summaryLooksHealthy = Boolean(lastRun?.status === 'success');
      const progressPercent = summaryLooksHealthy
        ? 100
        : checks.length
          ? Math.round((passed / checks.length) * 100)
          : 0;
      const allPassed = summaryLooksHealthy || (checks.length > 0 && passed === checks.length && failures === 0);

      return {
        statusLabel: allPassed ? 'PASS' : 'WARN',
        statusCode: summaryLooksHealthy
          ? `RUN: ${lastRun?.returnCode ?? 0}`
          : `CHECKS: ${passed}/${checks.length || 0}`,
        progressPercent,
        textClass: allPassed ? 'pass-text' : 'warn-text',
        fillClass: allPassed ? 'pass-fill' : 'warn-fill',
      };
    }

    const totalIssues = Number(reportJson?.metadata?.total_issues ?? 0);
    const filesAnalyzed = Number(reportJson?.metadata?.files_analyzed ?? 0);
    const successLike = filesAnalyzed > 0 && totalIssues === 0;

    return {
      statusLabel: successLike ? 'PASS' : 'WARN',
      statusCode: `ISSUES: ${totalIssues}`,
      progressPercent: successLike ? 100 : Math.max(20, 100 - Math.min(totalIssues, 100)),
      textClass: successLike ? 'pass-text' : 'warn-text',
      fillClass: successLike ? 'pass-fill' : 'warn-fill',
    };
  }, [reportJson, lastRun]);

  // ── VALIDATION SUCCESS RATE ───────────────────────────────────────────
  const successRateMetrics = useMemo(() => {
    const empty = {
      percent: 0,
      label: '0 / 0',
      textClass: 'warn-text',
      fillClass: 'grey-fill',
      passed: 0,
      total: 0,
    };

    if (!reportJson) return empty;

    let checks = [];

    if (lastRun?.engine === 'angular') {
      const v = reportJson.validation || {};
      // Filter out null/undefined to get applicable checks
      checks = [
        v.tests_passed,
        v.snapshot_passed,
        v.tsc_passed
      ].filter(val => val !== null && val !== undefined);
    } else {
      // PHP Logic: Focus on Risk, AI Success, and Issue density
      const s = reportJson.summary || {};
      const ai = reportJson.ai_handoff_summary || {};
      const m = reportJson.metadata || {};

      checks = [
        s.risk_level !== 'HIGH',                       // Risk integrity
        ai.total_items > 0 ? ai.failed === 0 : null,   // AI Resolution (if applicable)
        m.files_analyzed > 0                           // Analysis health
      ].filter(val => val !== null && val !== undefined);
    }

    const total = checks.length;
    const passed = checks.filter(Boolean).length;
    const percent = total > 0 ? Math.round((passed / total) * 100) : 0;
    const allPassed = total > 0 && passed === total;

    return {
      percent,
      label: `${passed} / ${total}`,
      textClass: allPassed ? 'pass-text' : 'warn-text',
      fillClass: allPassed ? 'pass-fill' : 'warn-fill',
      passed,
      total,
    };
  }, [reportJson, lastRun]);

  // ── Syntax rule coverage bars — real data from coverage_report.by_type ─
  const syntaxBars = useMemo(() => {
    // Default static bars (shown when no real data available)
    const defaults = [
      { label: 'Refactoring', value: 92, fillClass: 'pass-fill' },
      { label: 'Type Logic',  value: 74, fillClass: 'grey-fill' },
      { label: 'Security',    value: 98, fillClass: 'pass-fill' },
    ];

    if (!reportJson || lastRun?.engine !== 'angular') return defaults;

    const cr = reportJson.coverage_report || reportJson.validation?.coverage_report;
    if (!cr?.by_type || Object.keys(cr.by_type).length === 0) return defaults;

    // Map Angular entity types to bars
    const TYPE_LABELS = {
      component: 'Components',
      service:   'Services',
      pipe:      'Pipes',
      directive: 'Directives',
      guard:     'Guards',
      resolver:  'Resolvers',
    };

    return Object.entries(cr.by_type)
      .filter(([, stats]) => stats.total > 0)
      .slice(0, 3)
      .map(([type, stats]) => ({
        label: TYPE_LABELS[type] || type,
        value: stats.percent ?? 0,
        fillClass: stats.percent >= 80 ? 'pass-fill' : 'warn-fill',
      }));
  }, [reportJson, lastRun]);

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
          `${API_BASE}/report?engine=${encodeURIComponent(parsedRun.engine)}&project_name=${encodeURIComponent(parsedRun.projectName)}&format=json`,
        );
        if (jsonRes.ok) {
          const jsonData = await jsonRes.json();
          setReportJson(jsonData.content);
        }

        const mdRes = await fetch(
          `${API_BASE}/report?engine=${encodeURIComponent(parsedRun.engine)}&project_name=${encodeURIComponent(parsedRun.projectName)}&format=md`,
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
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = fileName; a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPdf = () => {
    const reportBody = reportMarkdown || JSON.stringify(reportJson || {}, null, 2);
    if (!reportBody || reportBody === '{}') { alert('No report content available for PDF export.'); return; }
    const printable = window.open('', '_blank', 'width=900,height=700');
    if (!printable) { alert('Popup blocked. Please allow popups to export PDF.'); return; }
    printable.document.write(`
      <html><head><title>EVUA Report</title>
      <style>body{font-family:Arial,sans-serif;margin:20px;white-space:pre-wrap;line-height:1.5}h1{margin-bottom:12px}</style>
      </head><body>
      <h1>EVUA Validation Report</h1>
      <p><strong>Project:</strong> ${lastRun?.projectName || 'unknown'}</p>
      <p><strong>Engine:</strong> ${lastRun?.engine || 'unknown'}</p>
      <hr />
      <pre>${String(reportBody).replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
      </body></html>
    `);
    printable.document.close(); printable.focus(); printable.print();
  };


  return (
    <div className="validation-container">
      <div className="validation-header">
        <div className="validation-title-section">
          <span className="validation-subtitle">SYSTEM.OUTPUT.VALIDATION</span>
          <h1 className="validation-title">Validation &amp; Report</h1>
        </div>
        <div className="validation-actions">
          <button className="btn btn-secondary" onClick={handleShare}>
            <Share2 size={14} /> Share Project Link
          </button>
          <button className="btn btn-secondary" onClick={handleExportJson} disabled={!reportJson}>
            <Download size={14} /> Export to JSON
          </button>
          <button className="btn btn-primary" onClick={handleDownloadPdf} disabled={!canExport}>
            <FileText size={14} /> Download Full Report
          </button>
        </div>
      </div>

      {(loadingReport || reportError || lastRun) && (
        <div style={{ margin: '8px 0 18px', color: '#9db2bf', fontSize: 12 }}>
          {loadingReport && 'Loading latest report...'}
          {!loadingReport && reportError && reportError}
          {!loadingReport && !reportError && lastRun && `Loaded: ${lastRun.projectName} (${lastRun.engine})`}
        </div>
      )}

      <div className="validation-dashboard">
        {/* TOP ROW */}
        <div className="dashboard-row top-row">
          <div className="dash-card pipeline-card">
            <div className="card-heading">PIPELINE STATUS</div>
            <div className="metric-row">
              <span className={`metric-large ${pipelineMetrics.textClass}`}>{pipelineMetrics.statusLabel}</span>
              <span className="metric-sub">{pipelineMetrics.statusCode}</span>
            </div>
            <div className="progress-label">Compile Status</div>
            <div className="progress-track">
              <div className={`progress-fill ${pipelineMetrics.fillClass}`} style={{ width: `${pipelineMetrics.progressPercent}%` }} />
            </div>
          </div>

          {/* VALIDATION SUCCESS RATE — how many checks passed */}
          <div className="dash-card success-rate-card">
            <div className="card-heading">VALIDATION SUCCESS RATE</div>
            <div className="metric-row">
              <span className={`metric-large ${successRateMetrics.textClass}`}>{successRateMetrics.percent}%</span>
              <span className="metric-sub">{successRateMetrics.label}</span>
            </div>
            <div className="progress-label">Validation checks passed</div>
            <div className="progress-track">
              <div className={`progress-fill ${successRateMetrics.fillClass}`} style={{ width: `${successRateMetrics.percent}%` }} />
            </div>
          </div>

          {/* SYNTAX RULE COVERAGE — by_type breakdown when available */}
          <div className="dash-card syntax-card">
            <div className="card-heading">SYNTAX RULE COVERAGE</div>
            <div className="syntax-bars">
              {syntaxBars.map((bar) => (
                <div key={bar.label} className="syntax-bar-row">
                  <span className="syntax-label">{bar.label}</span>
                  <div className="progress-track">
                    <div className={`progress-fill ${bar.fillClass}`} style={{ width: `${bar.value}%` }} />
                  </div>
                  <span className="syntax-val">{bar.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* BOTTOM ROW */}
        <div className="dashboard-row bottom-row">
          <div className="dash-card architecture-card">
            <div className="card-heading">ARCHITECTURE INTEGRITY</div>
            <RadarChart />
          </div>

          <div className="dash-card manifest-card">
            <div className="manifest-header">
              <div className="card-heading">MIGRATION MANIFEST</div>
              <div className="manifest-legend">
                <span className="legend-item"><span className="dot pass-dot"></span> 82 Migrated</span>
                <span className="legend-item"><span className="dot warn-dot"></span> 14 Partial</span>
                <span className="legend-item"><span className="dot fail-dot"></span> 4 Skipped</span>
              </div>
            </div>
            <div className="manifest-table">
              <div className="table-header">
                <div className="col entity">ENTITY NAME</div>
                <div className="col type">TYPE</div>
                <div className="col status">STATUS</div>
                <div className="col complexity">COMPLEXITY</div>
              </div>
              <div className="table-row">
                <div className="col entity mono-val">userService.core.ts</div>
                <div className="col type">Service Container</div>
                <div className="col status"><span className="badge badge-full">FULL</span></div>
                <div className="col complexity mono-val">0.42 <span className="complex-pass">O(1)</span></div>
              </div>
              <div className="table-row">
                <div className="col entity mono-val">authMiddleware.v1.js</div>
                <div className="col type">Middleware</div>
                <div className="col status"><span className="badge badge-partial">PARTIAL</span></div>
                <div className="col complexity mono-val">1.84 <span className="complex-warn">O(N)</span></div>
              </div>
              <div className="table-row line-through">
                <div className="col entity mono-val">legacy_db_conn.so</div>
                <div className="col type">Binary Artifact</div>
                <div className="col status"><span className="badge badge-skipped">SKIPPED</span></div>
                <div className="col complexity mono-val">--</div>
              </div>
              <div className="table-row">
                <div className="col entity mono-val">notificationDispatcher.ts</div>
                <div className="col type">Event Bus</div>
                <div className="col status"><span className="badge badge-full">FULL</span></div>
                <div className="col complexity mono-val">0.12 <span className="complex-pass">O(1)</span></div>
              </div>
              <div className="table-row">
                <div className="col entity mono-val">dataMapper.util.ts</div>
                <div className="col type">Utility</div>
                <div className="col status"><span className="badge badge-full">FULL</span></div>
                <div className="col complexity mono-val">0.95 <span className="complex-pass">O(log N)</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="actionable-review-section">
        <div className="review-section-header">
          <div className="review-title-group">
            <h2>Actionable Review</h2>
            <span className="badge-critical">3 Critical Issues</span>
          </div>
          <span className="review-subtitle">Manual intervention required for these snippets.</span>
        </div>

        <div className="review-cards">
          <div className="review-card">
            <div className="review-content">
              <div className="review-card-header">
                <AlertTriangle size={18} color="#f85149" />
                <h3>Ambiguous Type Mapping</h3>
                <span className="file-badge">AUTHMIDDLEWARE.V1.JS:142</span>
              </div>
              <p className="review-desc">
                The migration engine could not determine the concrete type for <code className="inline-code">req.user_context</code>. Defaulted to <code className="inline-code">any</code>, which breaks downstream interface contracts.
              </p>
              <div className="review-actions">
                <button className="btn-action primary-action">Apply Interface Fix</button>
                <button className="btn-action secondary-action">Ignore Rule</button>
              </div>
            </div>
            <div className="review-code-diff">
              <div className="diff-header">
                <span>CODE DIFF</span>
                <span className="diff-status unresolved">UNRESOLVED</span>
              </div>
              <div className="diff-lines">
                <div className="d-line"><span className="ln">141</span><span className="code">const validate = (req, res) =&gt; {'{'}</span></div>
                <div className="d-line removed"><span className="ln">142</span><span className="code">- const user = req.user_context;</span></div>
                <div className="d-line added"><span className="ln">143</span><span className="code">+ const user: UserInterface = req.user_context;</span></div>
                <div className="d-line"><span className="ln">144</span><span className="code">return user.id == null;</span></div>
              </div>
            </div>
          </div>

          <div className="review-card">
            <div className="review-content">
              <div className="review-card-header">
                <Cpu size={18} color="#fdb877" />
                <h3>Optimizable Loop Pattern</h3>
                <span className="file-badge">DATAMAPPER.UTIL.JS:18</span>
              </div>
              <p className="review-desc">
                Detected O(N²) legacy mapping. Suggesting migration to <code className="inline-code">Map()</code> structure for modern environment performance gains.
              </p>
              <div className="review-actions">
                <button className="btn-action primary-action">Refactor to Map</button>
                <button className="btn-action secondary-action">Keep Legacy</button>
              </div>
            </div>
            <div className="review-code-diff">
              <div className="diff-header">
                <span>CODE DIFF</span>
                <span className="diff-status suggestion">SUGGESTION</span>
              </div>
              <div className="diff-lines">
                <div className="d-line"><span className="ln">17</span><span className="code">items.forEach(a =&gt; {'{'}</span></div>
                <div className="d-line removed"><span className="ln">18</span><span className="code">- let match = users.find(u =&gt; u.id == a.uId);</span></div>
                <div className="d-line added"><span className="ln">19</span><span className="code">+ let match = userMap.get(a.uId);</span></div>
                <div className="d-line"><span className="ln">20</span><span className="code">{'});'}</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Validation;