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

  const [files, setFiles] = useState([]);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api.get("/sessions")
      .then((res) => setSessions(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleMigration = async () => {

    if (!files.length) {
      alert("Upload a project first");
      return;
    }

    try {

      setRunning(true);

      const formData = new FormData();

      files.forEach((file) => {
        formData.append("file", file);
      });

      await api.post("/migration/upload", formData);

      const res = await api.get("/sessions");
      setSessions(res.data);

    } catch (err) {
      console.error(err);
      alert("Migration failed");
    } finally {
      setRunning(false);
    }

  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-950">
      <Navbar />

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-10">

        {/* HEADER */}
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold text-white">EVUA Migration Engine</h1>
          <p className="text-gray-400 mt-2">
            Upload a legacy project to automatically migrate it
          </p>
        </div>

        {/* UPLOAD CARD */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 mb-10 flex flex-col items-center gap-6">

          <div className="text-gray-300 text-sm">
            Upload a project folder or zip archive
          </div>

          <div className="flex gap-6">

            {/* ZIP Upload */}
            <label className="cursor-pointer bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded text-sm text-white">
              Upload ZIP
              <input
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => setFiles([e.target.files[0]])}
              />
            </label>

            {/* Folder Upload */}
            <label className="cursor-pointer bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded text-sm text-white">
              Upload Folder
              <input
                type="file"
                webkitdirectory="true"
                directory=""
                multiple
                className="hidden"
                onChange={(e) => setFiles([...e.target.files])}
              />
            </label>

          </div>

          <button
            onClick={handleMigration}
            disabled={running}
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
          >
            {running ? "Running Migration..." : "Run Migration"}
          </button>

        </div>

        {/* SESSIONS */}

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
          </div>

        ) : sessions.length === 0 ? (

          <div className="text-center py-20 text-gray-500">
            No migration sessions yet
          </div>

        ) : (

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

            {sessions.map((session) => (

              <Link
                key={session.id}
                to={`/sessions/${session.id}`}
                className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors"
              >

                <div className="flex justify-between mb-3">

                  <h3 className="text-sm font-semibold text-white">
                    {session.benchmark_name || "Custom Migration"}
                  </h3>

                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      statusStyles[session.status] || statusStyles.running
                    }`}
                  >
                    {session.status}
                  </span>

                </div>

                <div className="text-xs text-gray-500 flex justify-between">
                  <span>{session.file_count || 0} files</span>
                  <span>{formatDate(session.created_at)}</span>
                </div>

              </Link>

            ))}

          </div>

        )}

      </main>
    </div>
  );
}