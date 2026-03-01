import { DiffEditor } from "@monaco-editor/react";
import { useState } from "react";

function getLanguage(filePath) {
  const ext = filePath.split(".").pop()?.toLowerCase();
  const map = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    html: "html",
    css: "css",
    json: "json",
    md: "markdown",
  };
  return map[ext] || "plaintext";
}

export default function DiffViewer({
  filePath,
  original,
  modified,
  onAccept,
  onRevert,
  decision,
}) {
  const [inline, setInline] = useState(false);
  const language = getLanguage(filePath);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono text-gray-300">{filePath}</span>
          {decision && (
            <span
              className={`text-xs px-2 py-0.5 rounded font-medium ${
                decision === "accepted"
                  ? "bg-green-500/10 text-green-400"
                  : decision === "reverted"
                  ? "bg-red-500/10 text-red-400"
                  : "bg-yellow-500/10 text-yellow-400"
              }`}
            >
              {decision}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setInline(!inline)}
            className="text-xs px-2 py-1 rounded bg-gray-800 text-gray-400 hover:text-white transition-colors cursor-pointer"
          >
            {inline ? "Side by Side" : "Inline"}
          </button>
          {onAccept && (
            <button
              onClick={onAccept}
              disabled={decision === "accepted"}
              className="text-xs px-3 py-1 rounded bg-green-600 hover:bg-green-500 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            >
              Accept
            </button>
          )}
          {onRevert && (
            <button
              onClick={onRevert}
              disabled={decision === "reverted"}
              className="text-xs px-3 py-1 rounded bg-red-600 hover:bg-red-500 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            >
              Revert
            </button>
          )}
        </div>
      </div>

      {/* Monaco Diff Editor */}
      <div className="flex-1 min-h-0">
        <DiffEditor
          height="100%"
          language={language}
          original={original || ""}
          modified={modified || ""}
          theme="vs-dark"
          options={{
            readOnly: true,
            renderSideBySide: !inline,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 13,
            lineNumbers: "on",
            renderOverviewRuler: false,
            diffWordWrap: "on",
            originalEditable: false,
          }}
        />
      </div>
    </div>
  );
}
