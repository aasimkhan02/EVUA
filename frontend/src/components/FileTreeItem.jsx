const riskColors = {
  SAFE: "bg-green-500/10 text-green-400 border-green-500/30",
  RISKY: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  MANUAL: "bg-red-500/10 text-red-400 border-red-500/30",
};

const statusColors = {
  NEW: "text-green-400",
  MODIFIED: "text-yellow-400",
};

const decisionColors = {
  pending: "bg-gray-800 text-gray-400",
  accepted: "bg-green-500/10 text-green-400",
  reverted: "bg-red-500/10 text-red-400",
};

/* File icon by extension */
function getFileIcon(path) {
  const ext = path.split(".").pop()?.toLowerCase();

  const icons = {
    ts: "📘",
    tsx: "📘",
    js: "📙",
    jsx: "📙",
    html: "📄",
    css: "🎨",
    json: "🧾",
    md: "📝",
  };

  return icons[ext] || "📄";
}

export default function FileTreeItem({
  file,
  isActive,
  onClick,
  onAccept,
  onRevert,
}) {
  const fileName = file.path.split("/").pop();
  const dirPath = file.path.split("/").slice(0, -1).join("/");

  const icon = getFileIcon(file.path);

  const isAccepted = file.decision === "accepted";
  const isReverted = file.decision === "reverted";

  return (
    <div
      className={`group flex items-center gap-2 px-3 py-2 cursor-pointer border-l-2 transition-all ${
        isActive
          ? "bg-gray-800 border-indigo-500"
          : "border-transparent hover:bg-gray-800/40 hover:border-gray-700"
      }`}
      onClick={onClick}
    >
      {/* File icon */}
      <span className="text-sm">{icon}</span>

      {/* File name */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-200 truncate">{fileName}</span>

          {file.status && (
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded ${
                statusColors[file.status] || "text-gray-400"
              }`}
            >
              {file.status}
            </span>
          )}
        </div>

        {dirPath && (
          <div className="text-[11px] text-gray-600 truncate">{dirPath}</div>
        )}
      </div>

      {/* Risk badge */}
      {file.risk_level && file.risk_level !== "SAFE" && (
        <span
          className={`text-[10px] px-1.5 py-0.5 rounded border ${
            riskColors[file.risk_level] || ""
          }`}
        >
          {file.risk_level}
        </span>
      )}

      {/* Decision badge */}
      <span
        className={`text-[10px] px-1.5 py-0.5 rounded ${
          decisionColors[file.decision] || decisionColors.pending
        }`}
      >
        {file.decision || "pending"}
      </span>

      {/* Hover actions */}
      <div className="hidden group-hover:flex items-center gap-1 ml-1">
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (!isAccepted) onAccept?.();
          }}
          disabled={isAccepted}
          className="text-[10px] px-1.5 py-0.5 bg-green-600/20 text-green-400 rounded hover:bg-green-600/40 disabled:opacity-30 cursor-pointer"
          title="Accept change"
        >
          ✓
        </button>

        <button
          onClick={(e) => {
            e.stopPropagation();
            if (!isReverted) onRevert?.();
          }}
          disabled={isReverted}
          className="text-[10px] px-1.5 py-0.5 bg-red-600/20 text-red-400 rounded hover:bg-red-600/40 disabled:opacity-30 cursor-pointer"
          title="Revert change"
        >
          ✕
        </button>
      </div>
    </div>
  );
}