export default function MigrationSummary({ session, files = [] }) {
  const accepted = files.filter((f) => f.decision === "accepted").length;
  const reverted = files.filter((f) => f.decision === "reverted").length;
  const pending = files.filter((f) => f.decision === "pending").length;
  const total = files.length;

  const risk = session?.risk_summary || { SAFE: 0, RISKY: 0, MANUAL: 0 };
  const progress = total > 0 ? ((accepted + reverted) / total) * 100 : 0;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-200">Migration Summary</h3>
        <span
          className={`text-xs px-2 py-0.5 rounded ${
            session?.status === "completed"
              ? "bg-green-500/10 text-green-400"
              : session?.status === "failed"
              ? "bg-red-500/10 text-red-400"
              : "bg-yellow-500/10 text-yellow-400"
          }`}
        >
          {session?.status || "unknown"}
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
          <span>Review progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-3">
        <div className="text-center">
          <div className="text-lg font-semibold text-green-400">{accepted}</div>
          <div className="text-xs text-gray-500">Accepted</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-semibold text-red-400">{reverted}</div>
          <div className="text-xs text-gray-500">Reverted</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-semibold text-yellow-400">{pending}</div>
          <div className="text-xs text-gray-500">Pending</div>
        </div>
      </div>

      {/* Risk breakdown */}
      <div className="flex items-center gap-3 text-xs">
        <span className="text-gray-500">Risk:</span>
        <span className="text-green-400">
          {risk.SAFE} safe
        </span>
        <span className="text-orange-400">
          {risk.RISKY} risky
        </span>
        <span className="text-red-400">
          {risk.MANUAL} manual
        </span>
      </div>
    </div>
  );
}
