import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import Navbar from "../components/Navbar";

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const statusStyles = {
  completed: "bg-green-500/10 text-green-400",
  running: "bg-yellow-500/10 text-yellow-400",
  failed: "bg-red-500/10 text-red-400",
};

export default function Home() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/sessions")
      .then((res) => setSessions(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Dashboard</h1>
            <p className="text-gray-500 text-sm mt-1">
              Manage your AngularJS migration sessions
            </p>
          </div>
          <Link
            to="/benchmarks"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            + New Migration
          </Link>
        </div>

        {/* Sessions */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-4xl mb-4">🚀</div>
            <h2 className="text-lg font-medium text-gray-300 mb-2">
              No migration sessions yet
            </h2>
            <p className="text-gray-500 text-sm mb-6">
              Select a benchmark project to start your first migration
            </p>
            <Link
              to="/benchmarks"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Browse Benchmarks
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sessions.map((session) => (
              <Link
                key={session.id}
                to={`/sessions/${session.id}`}
                className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors group"
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-sm font-semibold text-white group-hover:text-indigo-400 transition-colors">
                    {session.benchmark_name}
                  </h3>
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      statusStyles[session.status] || statusStyles.running
                    }`}
                  >
                    {session.status}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                  <span>{session.file_count} files</span>
                  <span>{formatDate(session.created_at)}</span>
                </div>

                {session.risk_summary && (
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-green-400">
                      {session.risk_summary.SAFE} safe
                    </span>
                    <span className="text-orange-400">
                      {session.risk_summary.RISKY} risky
                    </span>
                    <span className="text-red-400">
                      {session.risk_summary.MANUAL} manual
                    </span>
                  </div>
                )}
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
