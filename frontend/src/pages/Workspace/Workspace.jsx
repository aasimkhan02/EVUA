import React, { useState, useEffect, useRef } from 'react';
import { EditorView, basicSetup } from "codemirror";
import { MergeView } from "@codemirror/merge";
import { javascript } from "@codemirror/lang-javascript";
import { Folder, FolderOpen, FileCode, CheckCircle, AlertTriangle, Send, Bot, User, Edit } from 'lucide-react';
import './Workspace.css';

// --- MOCK BACKEND DATA MODEL ---
// Designed robustly so you can easily map a JSON API response here.
const initialTree = [
  {
    id: 'src',
    name: 'src',
    type: 'folder',
    isOpen: true,
    children: [
      {
        id: 'src/components',
        name: 'components',
        type: 'folder',
        isOpen: true,
        children: [
          {
            id: 'src/components/user-card.directive.js',
            name: 'user-card.directive.js',
            type: 'file',
            status: 'warning',
            originalCode: `angular.module('app')\n  .directive('userCard', function() {\n  return {\n    restrict: 'E',\n    scope: { user: '=' },\n    templateUrl: 'user-card.html',\n    controller: function($scope) {\n      $scope.update = function() {\n        // sync logic\n      };\n    }\n  };\n});`,
            modifiedCode: `import { Component, Input } from '@angular/core';\n\n@Component({\n  selector: 'app-user-card',\n  standalone: true,\n  templateUrl: './user-card.component.html'\n})\nexport class UserCardComponent {\n  @Input() user!: User;\n  \n  update() {\n    // modernized sync logic\n  }\n}`
          },
          {
            id: 'src/components/auth-service.factory.js',
            name: 'auth-service.factory.js',
            type: 'file',
            status: 'success',
            originalCode: `// Legacy Auth...`,
            modifiedCode: `// Modern Auth...`
          }
        ]
      },
      {
        id: 'src/services',
        name: 'services',
        type: 'folder',
        isOpen: false,
        children: []
      }
    ]
  }
];

const initialChat = [
  { role: 'assistant', text: 'Hello! I am your AI Architect. I noticed some raw two-way bindings in user-card.directive.js. How would you like to handle those during the refactor?' }
];

const Workspace = () => {
  // STATE MANAGEMENT matching a backend-driven approach
  const [fileSystem, setFileSystem] = useState(initialTree);
  const [activeFileId, setActiveFileId] = useState('src/components/user-card.directive.js');
  const [chatMessages, setChatMessages] = useState(initialChat);
  const [chatInput, setChatInput] = useState('');
  const cmContainerRef = useRef(null);

  // Defined inside the component via useMemo so EditorView is guaranteed
  // to be fully initialized before this runs — fixes "Cannot access before
  // initialization" TDZ errors caused by module-level EditorView.theme() calls
  // being evaluated before the codemirror module graph settles.
  const customTheme = React.useMemo(() => EditorView.theme({
    "&": { backgroundColor: "#0E0E0F", height: "100%", color: "#c9d1d9" },
    ".cm-scroller": { fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: "13px", overflow: "auto" },
    ".cm-gutters": { backgroundColor: "#0E0E0F", color: "#8b949e", border: "none" },
    ".cm-mergeView": { height: "100%", overflow: "hidden" },
    ".cm-mergeView .cm-editor": { height: "100%" },
    ".cm-merge-a .cm-deletedText": { backgroundColor: "#1B0C0E", textDecoration: "line-through", textDecorationColor: "rgba(255,255,255,0.2)" },
    ".cm-merge-a .cm-deletedLine": { backgroundColor: "#1B0C0E" },
    ".cm-merge-b .cm-insertedText": { backgroundColor: "#102416", textDecoration: "none" },
    ".cm-merge-b .cm-insertedLine": { backgroundColor: "#102416" }
  }), []);

  // Find the selected file cleanly
  const findFile = (nodes, id) => {
    for (let node of nodes) {
      if (node.id === id) return node;
      if (node.children) {
        const found = findFile(node.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  const activeFile = findFile(fileSystem, activeFileId);

  useEffect(() => {
    if (!cmContainerRef.current) return;
    cmContainerRef.current.innerHTML = '';
    
    if (activeFile && activeFile.type === 'file') {
      const view = new MergeView({
        a: {
          doc: activeFile.originalCode,
          extensions: [basicSetup, javascript(), customTheme, EditorView.editable.of(false)]
        },
        b: {
          doc: activeFile.modifiedCode,
          extensions: [basicSetup, javascript(), customTheme, EditorView.editable.of(false)]
        },
        parent: cmContainerRef.current
      });
      return () => view.destroy();
    }
  }, [activeFile, customTheme]);

  const toggleFolder = (id) => {
    const toggleNode = (nodes) => {
      return nodes.map(node => {
        if (node.id === id) return { ...node, isOpen: !node.isOpen };
        if (node.children) return { ...node, children: toggleNode(node.children) };
        return node;
      });
    };
    setFileSystem(toggleNode(fileSystem));
  };

  const handleSendChat = () => {
    if (!chatInput.trim()) return;
    setChatMessages(prev => [...prev, { role: 'user', text: chatInput }]);
    setChatInput('');
    
    // Simulate smart backend response
    setTimeout(() => {
      setChatMessages(prev => [...prev, { role: 'assistant', text: 'I will prepare the @Output event emitters to replace those legacy bindings. Let me know when you map the dependencies.' }]);
    }, 1000);
  };

  // Recursively render the dynamic file tree
  const renderTree = (nodes, level = 0) => {
    return nodes.map(node => {
      const isFolder = node.type === 'folder';
      const isActive = activeFileId === node.id;
      
      return (
        <React.Fragment key={node.id}>
          <div 
            className={`tree-node ${isActive ? 'active' : ''}`}
            style={{ paddingLeft: `${level * 16 + 16}px` }}
            onClick={() => isFolder ? toggleFolder(node.id) : setActiveFileId(node.id)}
          >
            {isFolder ? (
              node.isOpen ? <FolderOpen size={16} className="tree-icon" /> : <Folder size={16} className="tree-icon" />
            ) : (
              <FileCode size={16} className="tree-icon file-icon" />
            )}
            <span className="tree-name">{node.name}</span>
            {!isFolder && node.status === 'warning' && <AlertTriangle size={14} color="#f59e0b" className="status-icon" />}
            {!isFolder && node.status === 'success' && <CheckCircle size={14} color="#10b981" className="status-icon" />}
          </div>
          {isFolder && node.isOpen && node.children && (
             <div className="tree-children">
               {renderTree(node.children, level + 1)}
             </div>
          )}
        </React.Fragment>
      );
    });
  };

  return (
    <div className="workspace-layout">
      {/* LEFT: File System */}
      <div className="workspace-sidebar">
        <div className="sidebar-header">FILESYSTEM</div>
        <div className="file-tree">
          {renderTree(fileSystem)}
        </div>
      </div>

      {/* CENTER: Monaco Diff Editor */}
      <div className="workspace-editor">
        <div className="editor-topbar">
          <div className="editor-tab active">
            <Edit size={14} />
            <span>{activeFile?.name || 'No file selected'}</span>
          </div>
        </div>
        <div className="editor-headers">
           <div className="editor-header-left">LEGACY: ANGULARJS 1.X <span className="badge deprecated">DEPRECATED</span></div>
           <div className="editor-header-right">CURRENT: ANGULAR 17+ <span className="badge transformed">TRANSFORMED</span></div>
        </div>
        <div className="cm-container" ref={cmContainerRef}>
           {(!activeFile || activeFile.type !== 'file') && (
             <div className="no-file">Select a valid code file from the filesystem to view the migration diff.</div>
           )}
        </div>
      </div>

      {/* RIGHT: Chatbot Interface */}
      <div className="workspace-chatbot">
         <div className="chatbot-header">
           <Bot size={18} color="#00d2ff"/>
           AI Migration Engine
         </div>
         <div className="chatbot-messages">
           {chatMessages.map((msg, i) => (
             <div key={i} className={`chat-message ${msg.role}`}>
               <div className="chat-avatar">
                 {msg.role === 'assistant' ? <Bot size={14} /> : <User size={14} />}
               </div>
               <div className="chat-bubble">
                 {msg.text}
               </div>
             </div>
           ))}
         </div>
         <div className="chatbot-inputbox">
            <textarea 
              placeholder="Query the engine..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendChat(); } }}
            />
            <button className="chat-send-btn" onClick={handleSendChat}>
              <Send size={16} />
            </button>
         </div>
      </div>
    </div>
  );
};

export default Workspace;