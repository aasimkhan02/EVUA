import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";
import Navbar from "../components/Navbar";

export default function BenchmarkSelector() {
  const [benchmarks, setBenchmarks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [migrating, setMigrating] = useState(null); // benchmark id being migrated
  const navigate = useNavigate();

  useEffect(() => {
    api
      .get("/benchmarks")
      .then((res) => setBenchmarks(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleMigrate = async (benchmarkId) => {
    setMigrating(benchmarkId);
    try {
      const res = await api.post(`/benchmarks/${benchmarkId}/migrate`);
      navigate(`/sessions/${res.data.session_id}`);
    } catch (err) {
      alert(err.response?.data?.detail || "Migration failed");
    } finally {
      setMigrating(null);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">
            Select a Benchmark
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Choose an AngularJS benchmark project to migrate
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {benchmarks.map((bench) => (
              <div
                key={bench.id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors"
              >
                <div className="mb-3">
                  <h3 className="text-sm font-semibold text-white mb-1">
                    {bench.name}
                  </h3>
                  <p className="text-xs text-gray-500 line-clamp-2">
                    {bench.description || "No description available"}
                  </p>
                </div>

                <div className="flex items-center gap-4 text-xs text-gray-500 mb-4">
                  <span className="flex items-center gap-1">
                    <span className="text-gray-600">📁</span>
                    {bench.file_count} files
                  </span>
                  <span className="font-mono text-gray-600">{bench.id}</span>
                </div>

                <button
                  onClick={() => handleMigrate(bench.id)}
                  disabled={migrating !== null}
                  className={`w-full py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer ${
                    migrating === bench.id
                      ? "bg-indigo-700 text-indigo-300"
                      : "bg-indigo-600 hover:bg-indigo-500 text-white"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {migrating === bench.id ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="animate-spin inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full"></span>
                      Running Migration...
                    </span>
                  ) : (
                    "Run Migration"
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
