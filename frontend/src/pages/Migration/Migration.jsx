import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import "./Migration.css";

// ─── constants ────────────────────────────────────────────────────────────────
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const ENGINES = [
  {
    id: "angular",
    label: "Angular",
    lang: "NG",
    title: "AngularJS → Angular",
    sub: "Migrate from AngularJS (1.x) to modern Angular",
    tags: ["controllers", "services", "directives", "routes"],
  },
  {
    id: "php",
    label: "PHP",
    lang: "PHP",
    title: "PHP Legacy → Modern",
    sub: "Upgrade any old PHP version to PHP 8.x",
    tags: ["analyze", "migrate", "report", "rules"],
  },
];

const STRATEGIES = ["full", "dry-run", "diff"];

// Keys that should persist between sessions (engine preference, strategy choice)
// — but NOT project name, file info, or previous results.
const PERSIST_KEY = "evua:migration-prefs";

// ─── component ────────────────────────────────────────────────────────────────
export default function Migration({ setActivePage }) {
  const { token } = useAuth();

  // ── Form state (reset per-run) ─────────────────────────────────────────────
  const [selectedEngine, setSelectedEngine] = useState("angular");
  const [strategy, setStrategy]             = useState("full");
  const [projectName, setProjectName]       = useState("");
  const [targetVersion, setTargetVersion]   = useState("17");
  const [phpSourceVersion, setPhpSourceVersion] = useState("5.6");
  const [phpTargetVersion, setPhpTargetVersion] = useState("8.3");
  const [phpCommand, setPhpCommand]         = useState("migrate");
  const [outputPath, setOutputPath]         = useState("");
  const [file, setFile]                     = useState(null);

  // ── Run state ──────────────────────────────────────────────────────────────
  const [running, setRunning] = useState(false);
  const [result, setResult]   = useState(null);
  const [error, setError]     = useState(null);

  const fileInputRef = useRef();

  // ── Restore only non-sensitive preferences on mount ────────────────────────
  useEffect(() => {
    try {
      const saved = localStorage.getItem(PERSIST_KEY);
      if (!saved) return;
      const prefs = JSON.parse(saved);
      // Only restore safe, non-project-specific preferences
      if (prefs.selectedEngine) setSelectedEngine(prefs.selectedEngine);
      if (prefs.strategy)       setStrategy(prefs.strategy);
      if (prefs.phpCommand)     setPhpCommand(prefs.phpCommand);
      if (prefs.phpSourceVersion) setPhpSourceVersion(prefs.phpSourceVersion);
      if (prefs.phpTargetVersion) setPhpTargetVersion(prefs.phpTargetVersion);
      if (prefs.targetVersion)  setTargetVersion(prefs.targetVersion);
    } catch {
      // Ignore corrupted cache
    }
  }, []);

  // ── Persist only safe preferences (never project name, file, or results) ──
  useEffect(() => {
    localStorage.setItem(PERSIST_KEY, JSON.stringify({
      selectedEngine,
      strategy,
      phpCommand,
      phpSourceVersion,
      phpTargetVersion,
      targetVersion,
    }));
  }, [selectedEngine, strategy, phpCommand, phpSourceVersion, phpTargetVersion, targetVersion]);

  // ── Reset result/error/file/project when engine changes ───────────────────
  const handleEngineChange = (engineId) => {
    setSelectedEngine(engineId);
    setResult(null);
    setError(null);
    // Reset to engine-default versions
    if (engineId === "angular") setTargetVersion("17");
    if (engineId === "php")     { setPhpSourceVersion("5.6"); setPhpTargetVersion("8.3"); }
  };

  // ── File handler ──────────────────────────────────────────────────────────
  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    // Auto-fill project name only if it's currently empty
    if (!projectName.trim()) {
      setProjectName(f.name.replace(/\.(zip|tar\.gz|tar\.bz2)$/i, ""));
    }
    // Always clear stale results when a new file is chosen
    setResult(null);
    setError(null);
  };

  const handleClearFile = () => {
    setFile(null);
    setProjectName("");
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // ── Submit ────────────────────────────────────────────────────────────────
  const handleStartMigration = async () => {
    if (!file)              return alert("Please upload a project archive (.zip) first.");
    if (!projectName.trim()) return alert("Please enter a project name.");

    setRunning(true);
    setResult(null);
    setError(null);

    try {
      const form = new FormData();
      form.append("engine",       selectedEngine);
      form.append("strategy",     strategy);
      form.append("project_name", projectName.trim());
      form.append("output_path",  outputPath.trim() || "./out");
      form.append("file",         file);

      if (selectedEngine === "angular") {
        form.append("target_version", targetVersion);
      } else if (selectedEngine === "php") {
        form.append("source_version", phpSourceVersion);
        form.append("target_version", phpTargetVersion);
        form.append("command",        phpCommand);
      }

      const res = await fetch(`${API_BASE}/migrate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }

      setResult(data);

      // Save to last-run for Validation page
      if (data?.status === "success") {
        localStorage.setItem("evua:last-run", JSON.stringify({
          engine:        selectedEngine,
          projectName:   projectName.trim(),
          status:        data.status,
          strategy,
          command:       selectedEngine === "php" ? phpCommand : "migrate",
          targetVersion: selectedEngine === "php" ? phpTargetVersion : targetVersion,
          sourceVersion: selectedEngine === "php" ? phpSourceVersion : undefined,
          returnCode:    data?.result?.return_code,
          indicators:    data?.result?.indicators || [],
          runAt:         new Date().toISOString(),
        }));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  // ── Derived helpers ───────────────────────────────────────────────────────
  const isReady = Boolean(file && projectName.trim());
  const engineLabel = selectedEngine === "php"
    ? `PHP ${phpSourceVersion} → ${phpTargetVersion} · ${phpCommand.toUpperCase()}`
    : `AngularJS → Angular ${targetVersion} · ${strategy}`;

  // ── render ────────────────────────────────────────────────────────────────
  return (
    <div className="migration-container">

      {/* ── HERO ────────────────────────────────────────────────────────── */}
      <div className="migration-hero">
        <div className="hero-content">
          <h1 className="hero-title">
            Code <span className="hero-title-highlight">Migration</span> Engine
          </h1>
          <p className="hero-description">
            Select your migration engine, upload your project, and configure
            the run parameters. EVUA handles the rest.
          </p>
        </div>
        <div className="hero-actions">
          <button className="btn-secondary">VIEW DOCS</button>
          <button className="btn-primary">CHANGELOG</button>
        </div>
      </div>

      {/* ── DASHBOARD GRID ──────────────────────────────────────────────── */}
      <div className="dashboard-grid">

        {/* CARD 1 — Engine picker */}
        <div className="step-card">
          <p className="section-label">Select Engine</p>
          <div className="engine-options">
            {ENGINES.map((eng) => (
              <button
                key={eng.id}
                className={`engine-option${selectedEngine === eng.id ? " active" : ""}${eng.disabled ? " disabled" : ""}`}
                onClick={() => !eng.disabled && handleEngineChange(eng.id)}
                disabled={eng.disabled}
                title={eng.disabled ? "Coming soon" : undefined}
              >
                <div className="engine-top">
                  <span className={`lang-icon${selectedEngine === eng.id ? " active-lang" : ""}`}>
                    {eng.lang}
                  </span>
                  {selectedEngine === eng.id && (
                    <span className="active-badge">ACTIVE</span>
                  )}
                </div>
                <div className="engine-title">{eng.title}</div>
                <div className="engine-sub">{eng.sub}</div>
                <div className="engine-tags">
                  {eng.tags.map((t) => <span key={t}>{t}</span>)}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* CARD 2 — Upload */}
        <div className="ingest-card">
          <div className="upload-circle">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                 stroke={file ? "#3fb950" : "#00d2ff"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <div className="ingest-title">
            {file?.name || "Upload Project Archive"}
          </div>
          <div className="ingest-desc">
            {file
              ? `${(file.size / 1024).toFixed(1)} KB · ready to migrate`
              : `Drop a .zip of your ${selectedEngine === "php" ? "PHP" : "AngularJS"} project here or browse to select it.`}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,.tar.gz,.tar.bz2"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
          <div style={{ display: "flex", gap: "8px" }}>
            <button className="browse-btn" onClick={() => fileInputRef.current.click()}>
              {file ? "CHANGE FILE" : "BROWSE FILES"}
            </button>
            {file && (
              <button
                className="browse-btn"
                onClick={handleClearFile}
                style={{ background: "rgba(248,81,73,0.12)", color: "#f85149", border: "1px solid rgba(248,81,73,0.25)" }}
                title="Clear file and project name"
              >
                CLEAR
              </button>
            )}
          </div>
        </div>

        {/* CARD 3 — Params */}
        <div className="step-card">
          <p className="section-label">Run Parameters</p>
          <div className="param-inputs" style={{ flexWrap: "wrap", gap: "16px" }}>

            <div className="input-group" style={{ minWidth: "180px" }}>
              <label>PROJECT NAME</label>
              <input
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder={selectedEngine === "php" ? "my-php-app" : "my-angular-app"}
              />
            </div>

            {selectedEngine === "angular" && (
              <div className="input-group" style={{ minWidth: "120px" }}>
                <label>TARGET VERSION</label>
                <div className="select-wrapper">
                  <select
                    value={targetVersion}
                    onChange={(e) => setTargetVersion(e.target.value)}
                  >
                    <option value="17">Angular 17</option>
                    <option value="16">Angular 16</option>
                    <option value="15">Angular 15</option>
                  </select>
                  <span className="select-icon">▾</span>
                </div>
              </div>
            )}

            {selectedEngine === "php" && (
              <>
                <div className="input-group" style={{ minWidth: "120px" }}>
                  <label>SOURCE VERSION</label>
                  <div className="select-wrapper">
                    <select
                      value={phpSourceVersion}
                      onChange={(e) => setPhpSourceVersion(e.target.value)}
                    >
                      <option value="5.3">PHP 5.3</option>
                      <option value="5.4">PHP 5.4</option>
                      <option value="5.5">PHP 5.5</option>
                      <option value="5.6">PHP 5.6</option>
                      <option value="7.0">PHP 7.0</option>
                      <option value="7.1">PHP 7.1</option>
                      <option value="7.2">PHP 7.2</option>
                      <option value="7.3">PHP 7.3</option>
                      <option value="7.4">PHP 7.4</option>
                    </select>
                    <span className="select-icon">▾</span>
                  </div>
                </div>

                <div className="input-group" style={{ minWidth: "120px" }}>
                  <label>TARGET VERSION</label>
                  <div className="select-wrapper">
                    <select
                      value={phpTargetVersion}
                      onChange={(e) => setPhpTargetVersion(e.target.value)}
                    >
                      <option value="8.0">PHP 8.0</option>
                      <option value="8.1">PHP 8.1</option>
                      <option value="8.2">PHP 8.2</option>
                      <option value="8.3">PHP 8.3</option>
                    </select>
                    <span className="select-icon">▾</span>
                  </div>
                </div>

                <div className="input-group" style={{ width: "100%" }}>
                  <label>COMMAND</label>
                  <div className="strategy-toggles">
                    {["analyze", "migrate"].map((cmd) => (
                      <button
                        key={cmd}
                        className={`strategy-btn${phpCommand === cmd ? " active" : ""}`}
                        onClick={() => setPhpCommand(cmd)}
                      >
                        {cmd.toUpperCase()}
                      </button>
                    ))}
                  </div>
                  {phpCommand === "analyze" && (
                    <p style={{ fontSize: 11, color: "#5a7482", marginTop: 8, margin: "8px 0 0" }}>
                      Analysis generates a JSON report viewable in Validation. No files are modified.
                    </p>
                  )}
                  {phpCommand === "migrate" && (
                    <p style={{ fontSize: 11, color: "#5a7482", marginTop: 8, margin: "8px 0 0" }}>
                      Full migration rewrites PHP source files to the target version.
                    </p>
                  )}
                </div>
              </>
            )}

            {/* Strategy only shown for Angular. PHP uses its own command toggle above. */}
            {selectedEngine === "angular" && (
              <div className="input-group" style={{ width: "100%" }}>
                <label>STRATEGY</label>
                <div className="strategy-toggles">
                  {STRATEGIES.map((s) => (
                    <button
                      key={s}
                      className={`strategy-btn${strategy === s ? " active" : ""}`}
                      onClick={() => setStrategy(s)}
                    >
                      {s.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="input-group" style={{ width: "100%" }}>
              <label>OUTPUT PATH <span style={{ opacity: 0.5, fontWeight: 400 }}>(OPTIONAL)</span></label>
              <input
                value={outputPath}
                onChange={(e) => setOutputPath(e.target.value)}
                placeholder="./out"
              />
            </div>

          </div>
        </div>

        {/* CARD 4 — AI card */}
        <div className="ai-card">
          <div className="ai-bg" style={{
            background: "radial-gradient(ellipse at 80% 20%, #0d3b4f 0%, #0d1117 70%)"
          }}/>
          <div className="ai-overlay"/>
          <div className="ai-content">
            <span className="neural-tag">AI-ASSIST</span>
            <div className="ai-title">
              Neural refactoring<br/>for complex patterns
            </div>
            <div className="ai-footer">
              GEMINI · POST-PROCESS · STUBS
            </div>
          </div>
        </div>

      </div>{/* end dashboard-grid */}

      {/* ── ACTION BAR ──────────────────────────────────────────────────── */}
      <div className="migration-action-bar">
        <div className="action-status">
          <div className="action-icon">
            {running ? (
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
                   stroke="#00d2ff" strokeWidth="2"
                   style={{ animation: "spin 1s linear infinite" }}>
                <circle cx="12" cy="12" r="10" strokeDasharray="31.4" strokeDashoffset="10"/>
              </svg>
            ) : (
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            )}
          </div>
          <div className="status-text">
            <h4>{running ? "RUNNING ENGINE…" : isReady ? "READY TO MIGRATE" : "AWAITING CONFIGURATION"}</h4>
            <p>
              {running
                ? "Processing — check the terminal for live output"
                : isReady
                  ? `${file.name} · ${engineLabel}`
                  : "Upload a project archive and set a project name to begin"}
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          {result && (
            <button
              className="btn-secondary"
              style={{ padding: "8px 16px", fontSize: "10px", letterSpacing: "1px" }}
              onClick={() => { setResult(null); setError(null); }}
            >
              CLEAR RESULT
            </button>
          )}
          <button
            className="start-migration-btn"
            onClick={handleStartMigration}
            disabled={running || !isReady}
            style={!isReady && !running ? { opacity: 0.5, cursor: "not-allowed" } : {}}
          >
            {running ? "RUNNING…" : "START MIGRATION"}
            <span className="btn-icon">→</span>
          </button>
        </div>
      </div>

      {/* ── RESULT PANEL ────────────────────────────────────────────────── */}
      {error && (
        <div className="result-panel result-error" style={panelStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={badgeStyle("#ff4d4d")}>FAILED</span>
            <button
              style={{ background: "transparent", border: "none", color: "#5a7482", cursor: "pointer", fontSize: 20, lineHeight: 1 }}
              onClick={() => setError(null)}
              title="Dismiss"
            >×</button>
          </div>
          <p style={{ color: "#ff8080", marginTop: 12, fontFamily: "monospace", fontSize: 13 }}>{error}</p>
        </div>
      )}

      {result && !error && (
        <div className="result-panel" style={panelStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <span style={badgeStyle(result.status === "success" ? "#00d2ff" : "#ff4d4d")}>
                {result.status?.toUpperCase?.() ?? "DONE"}
              </span>
              {result.job_id && (
                <span style={{ fontSize: 11, color: "#5a7482", fontFamily: "monospace" }}>
                  JOB #{result.job_id}
                </span>
              )}
            </div>

            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              {result.status === "success" && (
                <>
                  <button
                    className="btn-primary"
                    style={{ padding: "8px 16px", fontSize: "10px" }}
                    onClick={() => setActivePage("validation")}
                  >
                    VIEW REPORT
                  </button>
                  <button
                    className="btn-secondary"
                    style={{ padding: "8px 16px", fontSize: "10px" }}
                    onClick={() => setActivePage("workspace")}
                  >
                    CHECK DIFF
                  </button>
                </>
              )}
              <button
                style={{ background: "transparent", border: "none", color: "#5a7482", cursor: "pointer", fontSize: 20, lineHeight: 1 }}
                onClick={() => { setResult(null); setError(null); }}
                title="Dismiss"
              >×</button>
            </div>
          </div>

          {/* Engine output indicators */}
          {result.result?.indicators?.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <p style={labelStyle}>ENGINE OUTPUT</p>
              <pre style={preStyle}>
                {result.result.indicators.join("\n")}
              </pre>
            </div>
          )}

          {/* Message when no indicators */}
          {!result.result?.indicators?.length && result.result?.message && (
            <p style={{ color: "#a0abb6", marginTop: 12, fontSize: 13 }}>{result.result.message}</p>
          )}

          {/* Full log (collapsed) */}
          {result.result?.log?.length > 0 && (
            <details style={{ marginTop: 16 }}>
              <summary style={{ color: "#5a7482", cursor: "pointer", fontSize: 11, letterSpacing: 1, userSelect: "none" }}>
                FULL LOG ({result.result.log.length} lines)
              </summary>
              <pre style={{ ...preStyle, maxHeight: 320, overflowY: "auto", marginTop: 8 }}>
                {result.result.log.join("\n")}
              </pre>
            </details>
          )}
        </div>
      )}

      {/* inline keyframe for spinner */}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .engine-option.disabled { opacity: 0.4; cursor: not-allowed; }
        .start-migration-btn:disabled { box-shadow: none; transform: none !important; }
      `}</style>

    </div>
  );
}

// ─── tiny inline style helpers ──────────────────────────────────────────────
const panelStyle = {
  margin: "0 60px 40px",
  padding: "28px 32px",
  background: "#1e1f22",
  borderRadius: 16,
};
const badgeStyle = (color) => ({
  display: "inline-block",
  background: color,
  color: "#000",
  fontSize: 10,
  fontWeight: 800,
  letterSpacing: 1,
  padding: "4px 10px",
  borderRadius: 4,
});
const labelStyle = {
  fontSize: 10,
  color: "#5d676e",
  letterSpacing: 1,
  fontWeight: 700,
  marginBottom: 8,
};
const preStyle = {
  background: "#121314",
  borderRadius: 8,
  padding: "16px",
  fontSize: 12,
  color: "#a0abb6",
  fontFamily: "monospace",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
  margin: 0,
};