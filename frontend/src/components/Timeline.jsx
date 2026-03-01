const stageConfig = {
  ingestion: { icon: "📂", color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/30" },
  analysis: { icon: "🔍", color: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/30" },
  patterns: { icon: "🧩", color: "text-cyan-400", bg: "bg-cyan-500/10", border: "border-cyan-500/30" },
  transformation: { icon: "⚡", color: "text-green-400", bg: "bg-green-500/10", border: "border-green-500/30" },
  risk: { icon: "⚠️", color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/30" },
  validation: { icon: "✅", color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/30" },
  reporting: { icon: "📊", color: "text-indigo-400", bg: "bg-indigo-500/10", border: "border-indigo-500/30" },
  decision: { icon: "🎯", color: "text-pink-400", bg: "bg-pink-500/10", border: "border-pink-500/30" },
};

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function Timeline({ events = [] }) {
  if (events.length === 0) {
    return (
      <div className="text-gray-500 text-sm p-4 text-center">
        No timeline events yet.
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {events.map((evt, i) => {
        const config = stageConfig[evt.stage] || stageConfig.reporting;
        const isLast = i === events.length - 1;
        return (
          <div key={i} className="flex gap-3 items-start">
            {/* Timeline line + dot */}
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full ${config.bg} border ${config.border} flex items-center justify-center text-sm shrink-0`}
              >
                {config.icon}
              </div>
              {!isLast && (
                <div className="w-px h-full min-h-[24px] bg-gray-700"></div>
              )}
            </div>

            {/* Content */}
            <div className="pb-4 flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span
                  className={`text-xs font-medium uppercase tracking-wider ${config.color}`}
                >
                  {evt.stage}
                </span>
                <span className="text-xs text-gray-600">
                  {formatTime(evt.timestamp)}
                </span>
                {evt.level === "error" && (
                  <span className="text-xs bg-red-500/10 text-red-400 px-1.5 py-0.5 rounded">
                    error
                  </span>
                )}
                {evt.level === "warning" && (
                  <span className="text-xs bg-yellow-500/10 text-yellow-400 px-1.5 py-0.5 rounded">
                    warning
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-300">{evt.message}</p>
              {evt.detail && (
                <div className="mt-1 text-xs text-gray-500 bg-gray-800/50 rounded px-2 py-1 font-mono">
                  {Object.entries(evt.detail).map(([k, v]) => (
                    <span key={k} className="mr-3">
                      {k}: <span className="text-gray-400">{v}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
