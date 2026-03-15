import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import api from "../lib/api";
import Navbar from "../components/Navbar";
import Timeline from "../components/Timeline";
import DiffViewer from "../components/DiffViewer";
import FileTreeItem from "../components/FileTreeItem";
import MigrationSummary from "../components/MigrationSummary";

export default function SessionDetail() {
  const { sessionId } = useParams();

  const [session, setSession] = useState(null);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  const [activeFile, setActiveFile] = useState(null);
  const [diffData, setDiffData] = useState(null);
  const [diffLoading, setDiffLoading] = useState(false);

  const [committing, setCommitting] = useState(false);

  const fetchSession = useCallback(async () => {
    try {
      const [sessionRes, filesRes] = await Promise.all([
        api.get(`/sessions/${sessionId}`),
        api.get(`/sessions/${sessionId}/files`)
      ]);

      setSession(sessionRes.data);
      setFiles(filesRes.data || []);

      // auto open first file
      if (filesRes.data?.length) {
        loadDiff(filesRes.data[0].path);
      }

    } catch (err) {
      console.error("Session load failed:", err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  const loadDiff = async (filePath) => {
    setActiveFile(filePath);
    setDiffLoading(true);

    try {
      const res = await api.get(
        `/sessions/${sessionId}/files/${encodeURIComponent(filePath)}`
      );

      setDiffData(res.data);

    } catch (err) {
      console.error("Diff load failed:", err);
    } finally {
      setDiffLoading(false);
    }
  };

  const handleAccept = async (filePath) => {
    try {
      await api.post(
        `/sessions/${sessionId}/files/${encodeURIComponent(filePath)}/accept`
      );

      setFiles((prev) =>
        prev.map((f) =>
          f.path === filePath ? { ...f, decision: "accepted" } : f
        )
      );

      if (diffData?.file_path === filePath) {
        setDiffData((prev) => ({ ...prev, decision: "accepted" }));
      }

    } catch (err) {
      console.error("Accept failed:", err);
    }
  };

  const handleRevert = async (filePath) => {
    try {
      await api.post(
        `/sessions/${sessionId}/files/${encodeURIComponent(filePath)}/revert`
      );

      setFiles((prev) =>
        prev.map((f) =>
          f.path === filePath ? { ...f, decision: "reverted" } : f
        )
      );

      if (diffData?.file_path === filePath) {
        setDiffData((prev) => ({ ...prev, decision: "reverted" }));
      }

    } catch (err) {
      console.error("Revert failed:", err);
    }
  };

  const handleAcceptAll = async () => {
    const pending = files.filter((f) => f.decision === "pending");

    await Promise.all(
      pending.map((f) =>
        api.post(`/sessions/${sessionId}/files/${encodeURIComponent(f.path)}/accept`)
      )
    );

    setFiles((prev) =>
      prev.map((f) =>
        f.decision === "pending" ? { ...f, decision: "accepted" } : f
      )
    );
  };

  const handleRevertAll = async () => {
    const pending = files.filter((f) => f.decision === "pending");

    await Promise.all(
      pending.map((f) =>
        api.post(`/sessions/${sessionId}/files/${encodeURIComponent(f.path)}/revert`)
      )
    );

    setFiles((prev) =>
      prev.map((f) =>
        f.decision === "pending" ? { ...f, decision: "reverted" } : f
      )
    );
  };

  const handleCommit = async () => {
    setCommitting(true);

    try {
      await api.post(`/sessions/${sessionId}/commit`);
      await fetchSession();

    } catch (err) {
      alert(err.response?.data?.detail || "Commit failed");
    } finally {
      setCommitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center text-gray-500">
          Session not found
        </div>
      </div>
    );
  }

  const hasPending = files.some((f) => f.decision === "pending");

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <div className="flex-1 flex overflow-hidden">

        {/* LEFT SIDEBAR */}
        <div className="w-80 border-r border-gray-800 flex flex-col bg-gray-950 shrink-0 overflow-hidden">

          {/* SUMMARY */}
         <div className="p-3 border-b border-gray-800 space-y-3">

          <MigrationSummary session={session} files={files} />

          {/* DOWNLOAD OUTPUTS */}
          {session.job_id && (
            <div className="flex gap-2">

              <a
                href={`/api/migration/${session.job_id}/report`}
                target="_blank"
                rel="noreferrer"
                className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded"
              >
                Report (.md)
              </a>

              <a
                href={`/api/migration/${session.job_id}/stats`}
                target="_blank"
                rel="noreferrer"
                className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded"
              >
                Stats (.json)
              </a>

              <a
                href={`/api/migration/${session.job_id}/diff`}
                target="_blank"
                rel="noreferrer"
                className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded"
              >
                Diff (.txt)
              </a>

            </div>
          )}

        </div>

          {/* ACTION BUTTONS */}
          <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-800">

            <button
              onClick={handleAcceptAll}
              disabled={!hasPending}
              className="flex-1 py-1.5 text-xs font-medium bg-green-600/10 text-green-400 rounded hover:bg-green-600/20 disabled:opacity-30"
            >
              Accept All
            </button>

            <button
              onClick={handleRevertAll}
              disabled={!hasPending}
              className="flex-1 py-1.5 text-xs font-medium bg-red-600/10 text-red-400 rounded hover:bg-red-600/20 disabled:opacity-30"
            >
              Revert All
            </button>

            <button
              onClick={handleCommit}
              disabled={committing || session.status === "committed"}
              className="flex-1 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded hover:bg-indigo-500 disabled:opacity-30"
            >
              {committing ? "..." : "Commit"}
            </button>

          </div>

          {/* FILE LIST */}
          <div className="flex-1 overflow-y-auto">

            <div className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Changed Files ({files.length})
            </div>

            {files.map((file) => (
              <FileTreeItem
                key={file.path}
                file={file}
                isActive={activeFile === file.path}
                onClick={() => loadDiff(file.path)}
                onAccept={() => handleAccept(file.path)}
                onRevert={() => handleRevert(file.path)}
              />
            ))}

          </div>

          {/* TIMELINE */}
          <details className="border-t border-gray-800">
            <summary className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-400">
              Pipeline Timeline ({session.timeline?.length || 0})
            </summary>

            <div className="p-3 max-h-64 overflow-y-auto">
              <Timeline events={session.timeline || []} />
            </div>

          </details>

        </div>

        {/* DIFF VIEWER */}
        <div className="flex-1 flex flex-col bg-gray-950 min-w-0">

          {diffLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-500"></div>
            </div>

          ) : diffData ? (

            <DiffViewer
              filePath={diffData.file_path}
              original={diffData.before_content}
              modified={diffData.after_content}
              decision={diffData.decision}
              onAccept={() => handleAccept(diffData.file_path)}
              onRevert={() => handleRevert(diffData.file_path)}
            />

          ) : (

            <div className="flex-1 flex items-center justify-center text-gray-600">
              <div className="text-center">
                <div className="text-4xl mb-3">📝</div>
                <p className="text-sm">Select a file to view changes</p>
              </div>
            </div>

          )}

        </div>

      </div>
    </div>
  );
}