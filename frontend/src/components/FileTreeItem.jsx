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

export default function FileTreeItem({
  file,
  isActive,
  onClick,
  onAccept,
  onRevert,
}) {
  const fileName = file.path.split("/").pop();
  const dirPath = file.path.split("/").slice(0, -1).join("/");

  return (
    <div
      className={`group flex items-center gap-2 px-3 py-2 cursor-pointer border-l-2 transition-all ${
        isActive
          ? "bg-gray-800/80 border-indigo-500"
          : "border-transparent hover:bg-gray-800/40 hover:border-gray-700"
      }`}
      onClick={onClick}
    >
      {/* File icon */}
      <span className={`text-xs ${statusColors[file.status] || "text-gray-400"}`}>
        {file.status === "NEW" ? "+" : "~"}
      </span>

      {/* File name */}
      <div className="flex-1 min-w-0">
        <div className="text-sm text-gray-200 truncate">{fileName}</div>
        {dirPath && (
          <div className="text-xs text-gray-600 truncate">{dirPath}</div>
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
        {file.decision}
      </span>

      {/* Action buttons (visible on hover) */}
      <div className="hidden group-hover:flex items-center gap-1">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onAccept?.();
          }}
          className="text-[10px] px-1.5 py-0.5 bg-green-600/20 text-green-400 rounded hover:bg-green-600/40 cursor-pointer"
          title="Accept change"
        >
          ✓
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRevert?.();
          }}
          className="text-[10px] px-1.5 py-0.5 bg-red-600/20 text-red-400 rounded hover:bg-red-600/40 cursor-pointer"
          title="Revert change"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
