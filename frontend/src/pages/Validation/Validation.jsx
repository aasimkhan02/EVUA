import React from 'react';
import { Share2, Download, FileText, AlertTriangle, Cpu } from 'lucide-react';
import './Validation.css';

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
  return (
    <div className="validation-container">
      <div className="validation-header">
        <div className="validation-title-section">
          <span className="validation-subtitle">SYSTEM.OUTPUT.VALIDATION</span>
          <h1 className="validation-title">Validation & Report</h1>
        </div>
        <div className="validation-actions">
          <button className="btn btn-secondary">
            <Share2 size={14} />
            Share Project Link
          </button>
          <button className="btn btn-secondary">
            <Download size={14} />
            Export to JSON
          </button>
          <button className="btn btn-primary">
            <FileText size={14} />
            Download Full Report
          </button>
        </div>
      </div>

      <div className="validation-dashboard">
        {/* TOP ROW */}
        <div className="dashboard-row top-row">
          <div className="dash-card pipeline-card">
            <div className="card-heading">PIPELINE STATUS</div>
            <div className="metric-row">
              <span className="metric-large pass-text">PASS</span>
              <span className="metric-sub">CODE: 200_OK</span>
            </div>
            <div className="progress-label">Compile Status</div>
            <div className="progress-track"><div className="progress-fill pass-fill" style={{ width: '100%' }}></div></div>
          </div>

          <div className="dash-card coverage-card">
            <div className="card-heading">TEST COVERAGE</div>
            <div className="metric-row">
              <span className="metric-large warn-text">88%</span>
              <span className="metric-sub">1,420 / 1,614</span>
            </div>
            <div className="progress-label">Success Rate</div>
            <div className="progress-track"><div className="progress-fill warn-fill" style={{ width: '88%' }}></div></div>
          </div>

          <div className="dash-card syntax-card">
            <div className="card-heading">SYNTAX RULE COVERAGE</div>
            <div className="syntax-bars">
              <div className="syntax-bar-row">
                <span className="syntax-label">Refactoring</span>
                <div className="progress-track"><div className="progress-fill pass-fill" style={{ width: '92%' }}></div></div>
                <span className="syntax-val">92%</span>
              </div>
              <div className="syntax-bar-row">
                <span className="syntax-label">Type Logic</span>
                <div className="progress-track"><div className="progress-fill grey-fill" style={{ width: '74%' }}></div></div>
                <span className="syntax-val">74%</span>
              </div>
              <div className="syntax-bar-row">
                <span className="syntax-label">Security</span>
                <div className="progress-track"><div className="progress-fill pass-fill" style={{ width: '98%' }}></div></div>
                <span className="syntax-val">98%</span>
              </div>
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
          {/* Card 1 */}
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

          {/* Card 2 */}
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
