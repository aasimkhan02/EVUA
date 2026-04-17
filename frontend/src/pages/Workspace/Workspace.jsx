import React, { useState, useEffect, useLayoutEffect, useRef, useMemo } from 'react';
import { EditorView, basicSetup } from 'codemirror';
import { MergeView } from '@codemirror/merge';
import { javascript } from '@codemirror/lang-javascript';
import {
  Folder, FolderOpen, FileCode, FileEdit,
  CheckCircle2, AlertCircle, PlusCircle, MinusCircle,
  ChevronDown, ChevronRight as ChevronRightIcon,
  GitMerge, Lightbulb, ArrowLeftRight, Copy, Check,
} from 'lucide-react';
import './Workspace.css';

// ─────────────────────────────────────────────────────────────────────────────
// DATA MODEL
//
// Every entry in FILES represents one "logical file" in the migration.
// Fields:
//   id          — unique key
//   status      — 'overwritten' | 'new' | 'deleted'
//   legacyPath  — path shown in Legacy tree  (null if status === 'new')
//   modernPath  — path shown in Modern tree  (null if status === 'deleted')
//   legacyCode  — original source            (null if status === 'new')
//   modernCode  — migrated source            (null if status === 'deleted')
//
// LOGIC:
//   overwritten → file exists in BOTH sides → show MergeView diff
//   new         → only in Modern  → show modern code + "New file" banner
//   deleted     → only in Legacy  → show legacy code + "Manual review" banner
// ─────────────────────────────────────────────────────────────────────────────

const FILES = [
  // ── app.module ──────────────────────────────────────────────────────────────
  {
    id: 'app.module',
    status: 'overwritten',
    legacyPath: ['src', 'app.module.js'],
    modernPath: ['src', 'app', 'app.module.ts'],
    legacyCode: `// AngularJS root module
angular.module('taskflow', [
  'ngRoute',
  'ngResource',
  'ui.bootstrap',
])
.config(['$routeProvider', function($routeProvider) {
  $routeProvider
    .when('/dashboard', {
      templateUrl: 'views/dashboard.html',
      controller:  'DashboardCtrl',
    })
    .when('/tasks', {
      templateUrl: 'views/tasks.html',
      controller:  'TaskBoardCtrl',
    })
    .when('/profile', {
      templateUrl: 'views/profile.html',
      controller:  'ProfileCtrl',
    })
    .otherwise({ redirectTo: '/dashboard' });
}]);`,
    modernCode: `import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { AppComponent } from './app.component';
import { AppRoutingModule } from './app-routing.module';
import { DashboardComponent } from './dashboard/dashboard.component';
import { TaskboardComponent } from './taskboard/taskboard.component';

@NgModule({
  declarations: [
    AppComponent,
    DashboardComponent,
    TaskboardComponent,
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    AppRoutingModule,
  ],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}`,
  },

  // ── app-routing (NEW — generated) ───────────────────────────────────────────
  {
    id: 'app-routing',
    status: 'new',
    legacyPath: null,
    modernPath: ['src', 'app', 'app-routing.module.ts'],
    legacyCode: null,
    modernCode: `import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard.component';
import { TaskboardComponent } from './taskboard/taskboard.component';

const routes: Routes = [
  { path: 'dashboard', component: DashboardComponent },
  { path: 'tasks',     component: TaskboardComponent },
  { path: '',          redirectTo: 'dashboard', pathMatch: 'full' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}`,
  },

  // ── DashboardCtrl → DashboardComponent ──────────────────────────────────────
  {
    id: 'dashboard.component',
    status: 'overwritten',
    legacyPath: ['src', 'controllers', 'DashboardCtrl.js'],
    modernPath: ['src', 'app', 'dashboard', 'dashboard.component.ts'],
    legacyCode: `angular.module('taskflow')
  .controller('DashboardCtrl', [
    '$scope', 'TaskService', 'StatsService',
    function($scope, TaskService, StatsService) {
      $scope.stats = {};
      $scope.tasks = [];

      StatsService.get().then(function(res) {
        $scope.stats = res.data;
      });

      TaskService.getAll().then(function(res) {
        $scope.tasks = res.data;
      });

      $scope.createTask = function(task) {
        TaskService.create(task).then(function() {
          $scope.tasks.push(task);
        });
      };
    }
  ]);`,
    modernCode: `import { Component, OnInit } from '@angular/core';
import { TaskService } from '../services/task.service';
import { StatsService } from '../services/stats.service';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
})
export class DashboardComponent implements OnInit {
  stats: Record<string, unknown> = {};
  tasks: unknown[] = [];

  constructor(
    private taskService: TaskService,
    private statsService: StatsService,
  ) {}

  ngOnInit(): void {
    this.statsService.get().subscribe(res => (this.stats = res));
    this.taskService.getAll().subscribe(res => (this.tasks = res));
  }

  createTask(task: unknown): void {
    this.taskService.create(task).subscribe(() => {
      this.tasks.push(task);
    });
  }
}`,
  },

  // ── AuthService → auth.service.ts ───────────────────────────────────────────
  {
    id: 'auth.service',
    status: 'overwritten',
    legacyPath: ['src', 'services', 'AuthService.js'],
    modernPath: ['src', 'app', 'services', 'auth.service.ts'],
    legacyCode: `angular.module('taskflow')
  .factory('AuthService', ['$http', function($http) {
    return {
      login: function(creds) {
        return $http.post('/api/login', creds);
      },
      logout: function() {
        return $http.post('/api/logout');
      },
      me: function() {
        return $http.get('/api/me');
      },
    };
  }]);`,
    modernCode: `import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

interface Credentials { username: string; password: string; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  constructor(private http: HttpClient) {}

  login(creds: Credentials): Observable<unknown> {
    return this.http.post('/api/login', creds);
  }

  logout(): Observable<unknown> {
    return this.http.post('/api/logout', {});
  }

  me(): Observable<unknown> {
    return this.http.get('/api/me');
  }
}`,
  },

  // ── TaskService → task.service.ts ───────────────────────────────────────────
  {
    id: 'task.service',
    status: 'overwritten',
    legacyPath: ['src', 'services', 'TaskService.js'],
    modernPath: ['src', 'app', 'services', 'task.service.ts'],
    legacyCode: `angular.module('taskflow')
  .factory('TaskService', ['$http', function($http) {
    return {
      getAll: function()   { return $http.get('/api/tasks'); },
      create: function(t)  { return $http.post('/api/tasks', t); },
      update: function(t)  { return $http.put('/api/tasks/' + t.id, t); },
      remove: function(id) { return $http.delete('/api/tasks/' + id); },
    };
  }]);`,
    modernCode: `import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class TaskService {
  constructor(private http: HttpClient) {}

  getAll(): Observable<unknown[]>      { return this.http.get<unknown[]>('/api/tasks'); }
  create(t: unknown): Observable<unknown> { return this.http.post('/api/tasks', t); }
  update(t: any): Observable<unknown>  { return this.http.put(\`/api/tasks/\${t.id}\`, t); }
  remove(id: string): Observable<unknown>{ return this.http.delete(\`/api/tasks/\${id}\`); }
}`,
  },

  // ── ProfileCtrl — DELETED (manual migration required) ───────────────────────
  {
    id: 'profile.ctrl',
    status: 'deleted',
    legacyPath: ['src', 'controllers', 'ProfileCtrl.js'],
    modernPath: null,
    legacyCode: `angular.module('taskflow')
  .controller('ProfileCtrl', [
    '$scope', 'UserService',
    function($scope, UserService) {
      // Deep $watch — no deterministic Angular equivalent
      $scope.$watch('user', function(newVal, oldVal) {
        if (newVal !== oldVal) {
          UserService.save(newVal);
        }
      }, true);

      $scope.updateAvatar = function(file) {
        UserService.uploadAvatar(file).then(function(res) {
          $scope.user.avatar = res.data.url;
        });
      };
    }
  ]);`,
    modernCode: null,
  },

  // ── tfTaskCard directive — DELETED ──────────────────────────────────────────
  {
    id: 'tf-task-card',
    status: 'deleted',
    legacyPath: ['src', 'directives', 'tfTaskCard.directive.js'],
    modernPath: null,
    legacyCode: `angular.module('taskflow')
  .directive('tfTaskCard', function() {
    return {
      restrict: 'E',
      transclude: true,
      link: function(scope, element, attrs) {
        // DOM manipulation — link() has no direct Angular equivalent
        element.on('click', function() {
          scope.$apply(function() {
            scope.selected = !scope.selected;
          });
        });
        element.on('mouseenter', function() {
          element.addClass('hovered');
        });
        element.on('mouseleave', function() {
          element.removeClass('hovered');
        });
      },
    };
  });`,
    modernCode: null,
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Build virtual file trees from the flat FILES array.
// Each tree is an array of folder/file nodes that the renderer understands.
// ─────────────────────────────────────────────────────────────────────────────

function buildTree(files, pathKey) {
  // pathKey is 'legacyPath' or 'modernPath'
  // root is a map of folder-name → { children }
  const root = { children: [] };

  for (const file of files) {
    const segments = file[pathKey];
    if (!segments) continue; // file doesn't exist on this side

    let cursor = root;
    // Walk all but the last segment as folders
    for (let i = 0; i < segments.length - 1; i++) {
      const seg = segments[i];
      let folder = cursor.children.find(c => c.type === 'folder' && c.name === seg);
      if (!folder) {
        folder = { id: segments.slice(0, i + 1).join('/'), name: seg, type: 'folder', isOpen: true, children: [] };
        cursor.children.push(folder);
      }
      cursor = folder;
    }

    // Last segment = the file
    const fileName = segments[segments.length - 1];
    cursor.children.push({
      id: segments.join('/'),
      name: fileName,
      type: 'file',
      status: file.status,
      fileRef: file, // pointer back to the full file record
    });
  }

  return root.children;
}

// ─────────────────────────────────────────────────────────────────────────────
// STATUS CONFIG
// ─────────────────────────────────────────────────────────────────────────────

const STATUS = {
  overwritten: { label: 'DIFF',    color: '#e3b341', Icon: GitMerge   },
  new:         { label: 'NEW',     color: '#3fb950', Icon: PlusCircle  },
  deleted:     { label: 'MANUAL',  color: '#f85149', Icon: MinusCircle },
};

// ─────────────────────────────────────────────────────────────────────────────
// CODEMIRROR THEME (monochrome, diff via background tints only)
// ─────────────────────────────────────────────────────────────────────────────

function buildCmTheme() {
  return EditorView.theme({
    '&':                { backgroundColor: '#0d1117', height: '100%', color: '#c9d1d9' },
    '.cm-scroller':     { fontFamily: "'JetBrains Mono','Fira Code',monospace", fontSize: '12.5px', lineHeight: '1.75', overflow: 'auto' },
    '.cm-content':      { padding: '8px 0' },
    '.cm-focused':      { outline: 'none' },
    '.cm-activeLine':   { backgroundColor: 'rgba(255,255,255,0.012)' },
    '.cm-gutters':      { backgroundColor: '#0d1117', border: 'none' },
    '.cm-gutter':       { backgroundColor: '#0d1117' },
    '.cm-lineNumbers .cm-gutterElement': { color: '#3b434b', minWidth: '3ch', padding: '0 12px 0 4px', textAlign: 'right' },
    '.cm-mergeView':               { height: '100%' },
    '.cm-mergeView .cm-editor':    { height: '100%' },
    '.cm-mergeView-gutter':        { width: '28px', backgroundColor: '#0d1117', borderLeft: '1px solid rgba(255,255,255,0.04)', borderRight: '1px solid rgba(255,255,255,0.04)' },
    // Left (legacy) — red tint
    '.cm-merge-a .cm-deletedLine': { backgroundColor: 'rgba(200,60,60,0.09)' },
    '.cm-merge-a .cm-changedLine': { backgroundColor: 'rgba(200,60,60,0.09)' },
    '.cm-merge-a .cm-deletedText': { backgroundColor: 'rgba(200,60,60,0.22)', borderRadius: '2px', textDecoration: 'none' },
    '.cm-merge-a .cm-changedText': { backgroundColor: 'rgba(200,60,60,0.22)', borderRadius: '2px' },
    // Right (modern) — blue tint
    '.cm-merge-b .cm-insertedLine': { backgroundColor: 'rgba(30,100,200,0.1)' },
    '.cm-merge-b .cm-changedLine':  { backgroundColor: 'rgba(30,100,200,0.1)' },
    '.cm-merge-b .cm-insertedText': { backgroundColor: 'rgba(30,100,200,0.24)', borderRadius: '2px', textDecoration: 'none' },
    '.cm-merge-b .cm-changedText':  { backgroundColor: 'rgba(30,100,200,0.24)', borderRadius: '2px' },
    // Flatten all syntax tokens
    '.cm-keyword,.cm-def,.cm-variable,.cm-function,.cm-type,.cm-class,.cm-tag,.cm-constant,.cm-builtin,.cm-bool,.cm-null,.cm-atom': { color: '#c9d1d9' },
    '.cm-operator,.cm-punctuation,.cm-bracket,.cm-meta,.cm-error': { color: '#8b949e' },
    '.cm-string,.cm-string2,.cm-number,.cm-attribute':             { color: '#a8b1bd' },
    '.cm-comment': { color: '#484f58', fontStyle: 'italic' },
    // Lezer tokenizer tokens (CM6)
    '.ͼ1,.ͼ2,.ͼd,.ͼ8,.ͼ9,.ͼa,.ͼb,.ͼf,.ͼg,.ͼk,.ͼl,.ͼm': { color: '#c9d1d9' },
    '.ͼ3,.ͼ6,.ͼc':                                      { color: '#8b949e' },
    '.ͼ4,.ͼ5,.ͼe':                                      { color: '#a8b1bd' },
    '.ͼ7,.ͼj':                                           { color: '#484f58', fontStyle: 'italic' },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// WORKSPACE COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function Workspace() {
  const [viewMode, setViewMode]       = useState('legacy');   // 'legacy' | 'modern'
  const [selectedFile, setSelectedFile] = useState(null);     // a FILES entry
  const [openFolders, setOpenFolders] = useState({});         // id → bool
  const [copied, setCopied]           = useState(false);
  const cmRef   = useRef(null);   // div that CodeMirror mounts INTO
  const theme   = useMemo(buildCmTheme, []);

  // Build both trees once
  const legacyTree = useMemo(() => buildTree(FILES, 'legacyPath'), []);
  const modernTree = useMemo(() => buildTree(FILES, 'modernPath'), []);
  const activeTree = viewMode === 'legacy' ? legacyTree : modernTree;

  // Pre-open all folders by default
  useEffect(() => {
    const ids = {};
    function collect(nodes) {
      for (const n of nodes) {
        if (n.type === 'folder') { ids[n.id] = true; if (n.children) collect(n.children); }
      }
    }
    collect(legacyTree);
    collect(modernTree);
    setOpenFolders(ids);
  }, []); // eslint-disable-line

  // Mount / remount CodeMirror MergeView only when diff is active
  // useLayoutEffect guarantees cmRef.current is set before this runs
  useLayoutEffect(() => {
    if (!cmRef.current) return;
    if (!selectedFile || selectedFile.status !== 'overwritten') return;

    let view;
    try {
      view = new MergeView({
        a: {
          doc: selectedFile.legacyCode ?? '',
          extensions: [basicSetup, javascript(), theme, EditorView.editable.of(false)],
        },
        b: {
          doc: selectedFile.modernCode ?? '',
          extensions: [basicSetup, javascript(), theme, EditorView.editable.of(false)],
        },
        parent: cmRef.current,
      });
    } catch (e) {
      console.error('MergeView init error:', e);
    }
    return () => view?.destroy();
  }, [selectedFile, theme]);

  // Toggle folder open/closed
  function toggleFolder(id) {
    setOpenFolders(prev => ({ ...prev, [id]: !prev[id] }));
  }

  // Copy to clipboard
  function copy(text) {
    navigator.clipboard.writeText(text ?? '').catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // What are we displaying in the center?
  const status   = selectedFile?.status;
  const fileName = selectedFile
    ? (viewMode === 'legacy'
        ? selectedFile.legacyPath?.at(-1)
        : selectedFile.modernPath?.at(-1)) ?? selectedFile.legacyPath?.at(-1)
    : null;

  // ── JSX ──────────────────────────────────────────────────────────────────────
  return (
    <div className="workspace-layout">

      {/* ── SIDEBAR ─────────────────────────────────────────────────────── */}
      <div className="workspace-sidebar">

        {/* Toggle */}
        <div className="sidebar-selector">
          <button
            className={`selector-tab ${viewMode === 'legacy' ? 'active legacy' : ''}`}
            onClick={() => setViewMode('legacy')}
          >
            Legacy
          </button>
          <button
            className={`selector-tab ${viewMode === 'modern' ? 'active modern' : ''}`}
            onClick={() => setViewMode('modern')}
          >
            Modern
          </button>
        </div>

        <div className="sidebar-section-label">
          {viewMode === 'legacy' ? 'ORIGINAL FILES' : 'MIGRATED OUTPUT'}
        </div>

        {/* File tree */}
        <div className="file-tree">
          <FileTree
            nodes={activeTree}
            openFolders={openFolders}
            selectedId={selectedFile?.id}
            onFile={node => setSelectedFile(node.fileRef)}
            onFolder={toggleFolder}
          />
        </div>

        {/* Legend */}
        <div className="sidebar-legend">
          {Object.entries(STATUS).map(([key, { label, color, Icon }]) => (
            <div key={key} className="legend-row">
              <Icon size={11} style={{ color }} />
              <span style={{ color: '#4b5563', fontSize: '9px', letterSpacing: '1px' }}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── MAIN EDITOR AREA ────────────────────────────────────────────── */}
      <div className="workspace-editor">

        {/* Top bar */}
        <div className="workspace-main-header">
          <div className="file-tabs">
            {selectedFile ? (
              <div className="file-tab active">
                <FileEdit size={13} className="tab-icon" />
                <span>{fileName}</span>
                {status && (
                  <span
                    className="tab-badge"
                    style={{
                      background: STATUS[status]?.color + '22',
                      color:      STATUS[status]?.color,
                    }}
                  >
                    {STATUS[status]?.label}
                  </span>
                )}
              </div>
            ) : (
              <div className="file-tab">
                <span style={{ color: '#3b434b' }}>no file selected</span>
              </div>
            )}
          </div>

          <div className="header-right-actions">
            {selectedFile && (
              <button
                className="copy-btn"
                onClick={() => copy(
                  status === 'deleted' ? selectedFile.legacyCode : selectedFile.modernCode
                )}
              >
                {copied ? <Check size={13} /> : <Copy size={13} />}
                <span>{copied ? 'Copied!' : status === 'deleted' ? 'Copy Original' : 'Copy Modern'}</span>
              </button>
            )}
            <div className="engine-status">
              <span className="status-dot-pulse" />
              ENGINE READY
            </div>
          </div>
        </div>

        {/* Diff column labels — only for overwritten files */}
        {status === 'overwritten' && (
          <div className="diff-context-header">
            <div className="column-label">
              <span className="label-text">{selectedFile.legacyPath?.at(-1)}</span>
              <span className="badge deprecated">LEGACY</span>
            </div>
            <div className="diff-gutter-label" />
            <div className="column-label right">
              <span className="label-text">{selectedFile.modernPath?.at(-1)}</span>
              <span className="badge transformed">MIGRATED</span>
            </div>
          </div>
        )}

        {/* Center content area — outer wrapper only for layout */}
        <div className="cm-container">

          {/* ── Empty state ──────────────────────────────────────────────── */}
          {!selectedFile && (
            <div className="no-file">
              <ArrowLeftRight size={36} opacity={0.1} />
              <span>Select a file to inspect</span>
              <p className="no-file-hint">
                <GitMerge size={12} style={{ display: 'inline', verticalAlign: 'middle', color: '#e3b341', marginRight: 4 }} />
                Overwritten → unified diff view<br />
                <PlusCircle size={12} style={{ display: 'inline', verticalAlign: 'middle', color: '#3fb950', marginRight: 4 }} />
                New → generated file preview<br />
                <MinusCircle size={12} style={{ display: 'inline', verticalAlign: 'middle', color: '#f85149', marginRight: 4 }} />
                Deleted → manual migration guide
              </p>
            </div>
          )}

          {/* ── DIFF: dedicated div for CodeMirror to mount into ─────────── */}
          {status === 'overwritten' && (
            <div
              key={selectedFile?.id}
              ref={cmRef}
              style={{ height: '100%', overflow: 'hidden' }}
            />
          )}

          {/* ── NEW FILE ─────────────────────────────────────────────────── */}
          {status === 'new' && (
            <div className="single-viewer">
              <div className="viewer-banner new">
                <PlusCircle size={16} />
                <div>
                  <div className="banner-title">New File Generated</div>
                  <div className="banner-sub">
                    This file has no equivalent in the original project.
                    The migration engine created it automatically.
                  </div>
                </div>
              </div>
              <CodePreview
                code={selectedFile.modernCode}
                filename={selectedFile.modernPath?.at(-1)}
                accent="#3fb950"
              />
            </div>
          )}

          {/* ── DELETED ──────────────────────────────────────────────────── */}
          {status === 'deleted' && (
            <div className="single-viewer">
              <div className="viewer-banner deleted">
                <MinusCircle size={16} />
                <div>
                  <div className="banner-title">Manual Migration Required</div>
                  <div className="banner-sub">
                    The engine could not produce a deterministic Angular equivalent.
                    Review the original below and migrate it manually.
                  </div>
                </div>
              </div>
              <div className="migration-tips">
                <AlertCircle size={13} style={{ color: '#f87171', flexShrink: 0 }} />
                <ul>
                  <li>Replace <code>link()</code> with <code>@Directive</code> / <code>@Component</code></li>
                  <li>Replace deep <code>$watch</code> with RxJS <code>BehaviorSubject</code></li>
                  <li>Transclude → use <code>&lt;ng-content&gt;</code> in the template</li>
                  <li>Refer to the Angular migration guide for your pattern</li>
                </ul>
              </div>
              <CodePreview
                code={selectedFile.legacyCode}
                filename={selectedFile.legacyPath?.at(-1)}
                accent="#f85149"
                label="ORIGINAL"
              />
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// FILE TREE — recursive renderer
// ─────────────────────────────────────────────────────────────────────────────

function FileTree({ nodes, openFolders, selectedId, onFile, onFolder, level = 0 }) {
  return nodes.map(node => {
    const isFolder = node.type === 'folder';
    const isSelected = !isFolder && node.fileRef?.id === selectedId;
    const isOpen   = isFolder && (openFolders[node.id] !== false);
    const indent   = level * 12 + 14;
    const st       = !isFolder && STATUS[node.status];

    return (
      <React.Fragment key={node.id}>
        <div
          className={`tree-node${isSelected ? ' active' : ''}${isFolder ? ' is-folder' : ''}`}
          style={{ paddingLeft: indent }}
          onClick={() => isFolder ? onFolder(node.id) : onFile(node)}
        >
          {/* Expand chevron */}
          <span className="tree-chevron">
            {isFolder
              ? (isOpen ? <ChevronDown size={12} /> : <ChevronRightIcon size={12} />)
              : <span style={{ width: 12, display: 'inline-block' }} />}
          </span>

          {/* Icon */}
          <span className="tree-item-icon">
            {isFolder
              ? (isOpen
                  ? <FolderOpen size={14} className="icon-folder-open" />
                  : <Folder size={14} className="icon-folder" />)
              : <FileCode size={13} className="icon-file" />}
          </span>

          {/* Name */}
          <span className="tree-name">{node.name}</span>

          {/* Status icon */}
          {st && (
            <span className="tree-status" style={{ color: st.color }} title={st.label}>
              <st.Icon size={11} />
            </span>
          )}
        </div>

        {/* Recurse into children */}
        {isFolder && isOpen && node.children && (
          <FileTree
            nodes={node.children}
            openFolders={openFolders}
            selectedId={selectedId}
            onFile={onFile}
            onFolder={onFolder}
            level={level + 1}
          />
        )}
      </React.Fragment>
    );
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// CODE PREVIEW — syntax-highlighted static block (no CodeMirror overhead)
// ─────────────────────────────────────────────────────────────────────────────

function CodePreview({ code, filename, accent = '#1ce3ff', label = 'GENERATED' }) {
  return (
    <div className="code-preview-wrap">
      <div className="code-preview-header">
        <span>{filename}</span>
        <span style={{ color: accent, fontSize: '10px', fontWeight: 700 }}>● {label}</span>
      </div>
      <pre className="code-preview-body">{code}</pre>
    </div>
  );
}