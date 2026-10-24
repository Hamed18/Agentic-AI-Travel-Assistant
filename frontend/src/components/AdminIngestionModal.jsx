import React, { useState, useEffect } from "react";
import {
  uploadDocument,
  ingestText,
  listDocuments,
  deleteDocument,
  getProfile,
  consolidateProfile,
  runReaper,
  getReaperStatus,
} from "../api";
import {
  X,
  Upload,
  FileText,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Database,
  Shield,
  Sparkles,
  Clock,
  RefreshCw,
} from "lucide-react";

export default function AdminIngestionModal({ isOpen, onClose, user }) {
  const [activeTab, setActiveTab] = useState("upload"); // "upload" | "text" | "documents" | "profile"
  const [documents, setDocuments] = useState([]);
  const [profile, setProfile] = useState(null);
  const [reaperStats, setReaperStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetchingDocs, setFetchingDocs] = useState(false);
  const [feedback, setFeedback] = useState({ type: "", message: "" });

  // File upload state
  const [selectedFile, setSelectedFile] = useState(null);

  // Text ingestion state
  const [textTitle, setTextTitle] = useState("");
  const [textContent, setTextContent] = useState("");

  const loadDocs = async () => {
    setFetchingDocs(true);
    try {
      const res = await listDocuments();
      setDocuments(res.documents || []);
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setFetchingDocs(false);
    }
  };

  const loadProfileAndReaper = async () => {
    try {
      const profRes = await getProfile().catch(() => null);
      if (profRes && profRes.profile) setProfile(profRes.profile);

      const rStats = await getReaperStatus().catch(() => null);
      if (rStats && rStats.reaper_telemetry) setReaperStats(rStats.reaper_telemetry);
    } catch (err) {
      console.error("Failed to load profile/reaper:", err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadDocs();
      loadProfileAndReaper();
      setFeedback({ type: "", message: "" });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setLoading(true);
    setFeedback({ type: "", message: "" });

    try {
      const res = await uploadDocument(selectedFile);
      setFeedback({
        type: "success",
        message: `Successfully ingested "${res.filename}" (${res.chunks_indexed} vector chunks indexed). Profile consolidation triggered in background.`,
      });
      setSelectedFile(null);
      loadDocs();
      loadProfileAndReaper();
    } catch (err) {
      setFeedback({
        type: "error",
        message: err.message || "Failed to upload and ingest document.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTextIngest = async (e) => {
    e.preventDefault();
    if (!textTitle.trim() || !textContent.trim()) return;

    setLoading(true);
    setFeedback({ type: "", message: "" });

    try {
      const res = await ingestText({ title: textTitle, content: textContent });
      setFeedback({
        type: "success",
        message: `Successfully indexed "${res.title}" (${res.chunks_indexed} vector chunks indexed). Profile consolidation triggered in background.`,
      });
      setTextTitle("");
      setTextContent("");
      loadDocs();
      loadProfileAndReaper();
    } catch (err) {
      setFeedback({
        type: "error",
        message: err.message || "Failed to ingest text content.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (filename) => {
    if (!confirm(`Are you sure you want to delete "${filename}" and its vector embeddings?`)) return;

    try {
      await deleteDocument(filename);
      setFeedback({
        type: "success",
        message: `Deleted "${filename}" successfully.`,
      });
      loadDocs();
    } catch (err) {
      setFeedback({
        type: "error",
        message: err.message || "Failed to delete document.",
      });
    }
  };

  const handleManualConsolidate = async () => {
    setLoading(true);
    setFeedback({ type: "", message: "" });
    try {
      const res = await consolidateProfile();
      if (res.profile) {
        setProfile(res.profile);
        setFeedback({
          type: "success",
          message: "Traveler profile consolidated successfully from ingested knowledge!",
        });
      } else {
        setFeedback({
          type: "error",
          message: "No documents available to synthesize a profile yet.",
        });
      }
    } catch (err) {
      setFeedback({
        type: "error",
        message: err.message || "Failed to synthesize profile.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRunReaper = async () => {
    setLoading(true);
    setFeedback({ type: "", message: "" });
    try {
      const res = await runReaper(2.0);
      setFeedback({
        type: "success",
        message: `TTL Reaper executed in ${res.details.duration_ms}ms. Purged: ${res.details.purged_memories} memories, ${res.details.purged_documents} documents, ${res.details.purged_storage_dirs} guest folders.`,
      });
      loadProfileAndReaper();
    } catch (err) {
      setFeedback({
        type: "error",
        message: err.message || "Failed to execute TTL reaper.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 sm:p-8 text-slate-100 flex flex-col max-h-[90vh]">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight flex items-center gap-2">
              Admin Knowledge & Ingestion Hub
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 font-medium">
                P5 Reaper & P6 Profile Active
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Ingest travel guidelines, synthesize consolidated user profiles, and manage TTL reapers.
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="grid grid-cols-4 p-1 bg-slate-950/60 rounded-xl mb-4 border border-slate-800/80">
          <button
            type="button"
            onClick={() => setActiveTab("upload")}
            className={`py-2 text-[11px] sm:text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeTab === "upload"
                ? "bg-purple-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            Upload
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("text")}
            className={`py-2 text-[11px] sm:text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeTab === "text"
                ? "bg-purple-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Paste Guide
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("documents")}
            className={`py-2 text-[11px] sm:text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeTab === "documents"
                ? "bg-purple-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            Index ({documents.length})
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab("profile");
              loadProfileAndReaper();
            }}
            className={`py-2 text-[11px] sm:text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeTab === "profile"
                ? "bg-purple-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Profile & Reaper
          </button>
        </div>

        {/* Feedback message */}
        {feedback.message && (
          <div
            className={`flex items-center gap-2 p-3 mb-4 text-xs rounded-xl border ${
              feedback.type === "success"
                ? "text-emerald-300 bg-emerald-950/40 border-emerald-800/50"
                : "text-red-300 bg-red-950/40 border-red-800/50"
            }`}
          >
            {feedback.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
            )}
            <span>{feedback.message}</span>
          </div>
        )}

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto pr-1">
          {activeTab === "upload" && (
            <form onSubmit={handleFileUpload} className="space-y-4">
              <div className="border-2 border-dashed border-slate-800 hover:border-purple-500/50 rounded-2xl p-6 text-center transition bg-slate-950/40">
                <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                <p className="text-sm font-medium text-slate-300">
                  Select a document to index
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Supports TXT, MD, PDF, JSON travel guidebooks & itineraries
                </p>
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files[0] || null)}
                  className="mt-4 block w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-purple-600/20 file:text-purple-300 hover:file:bg-purple-600/30 file:cursor-pointer"
                />
              </div>

              {selectedFile && (
                <div className="text-xs text-slate-400">
                  Selected: <strong className="text-white">{selectedFile.name}</strong> ({(selectedFile.size / 1024).toFixed(1)} KB)
                </div>
              )}

              <button
                type="submit"
                disabled={!selectedFile || loading}
                className="w-full py-2.5 px-4 bg-purple-600 hover:bg-purple-500 font-semibold text-sm rounded-xl text-white shadow-lg shadow-purple-500/25 transition disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Index Document into Tenant Vector DB"}
              </button>
            </form>
          )}

          {activeTab === "text" && (
            <form onSubmit={handleTextIngest} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Document / Guide Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Company Tokyo Travel Policy 2026"
                  value={textTitle}
                  onChange={(e) => setTextTitle(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Text Content to Chunk & Embed
                </label>
                <textarea
                  required
                  rows={6}
                  placeholder="Paste travel advice, custom guidelines, hotel preferences, or packing checklists..."
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 transition"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !textTitle.trim() || !textContent.trim()}
                className="w-full py-2.5 px-4 bg-purple-600 hover:bg-purple-500 font-semibold text-sm rounded-xl text-white shadow-lg shadow-purple-500/25 transition disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Index Custom Knowledge"}
              </button>
            </form>
          )}

          {activeTab === "documents" && (
            <div className="space-y-2">
              {fetchingDocs ? (
                <div className="flex items-center justify-center py-8 text-slate-400 gap-2 text-xs">
                  <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                  Loading tenant documents...
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-xs">
                  No documents indexed yet for this tenant. Upload a file to get started.
                </div>
              ) : (
                documents.map((doc, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 bg-slate-950/50 border border-slate-800/80 rounded-xl text-xs hover:border-slate-700 transition"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText className="w-4 h-4 text-purple-400 shrink-0" />
                      <div className="truncate">
                        <div className="font-medium text-slate-200 truncate">{doc.filename}</div>
                        <div className="text-slate-500 text-[10px]">
                          {doc.chunks_count} chunk(s) • {(doc.file_size / 1024).toFixed(1)} KB • {new Date(doc.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDelete(doc.filename)}
                      className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-red-950/30 transition shrink-0 ml-2 cursor-pointer"
                      title="Delete document and vector embeddings"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "profile" && (
            <div className="space-y-4 text-xs">
              {/* Profile Card (Phase 6) */}
              <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-amber-400" /> Consolidated Traveler Profile
                  </span>
                  <button
                    type="button"
                    onClick={handleManualConsolidate}
                    disabled={loading}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-300 text-[11px] font-medium transition cursor-pointer"
                  >
                    <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
                    Re-synthesize
                  </button>
                </div>

                {profile ? (
                  <div className="space-y-2 mt-2">
                    <div className="text-slate-300 leading-relaxed whitespace-pre-line bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
                      {profile.summary}
                    </div>
                    {profile.preferences && Object.keys(profile.preferences).length > 0 && (
                      <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-400 pt-1">
                        {Object.entries(profile.preferences).map(([k, v]) => (
                          <div key={k} className="p-2 rounded bg-slate-900/40 border border-slate-800/60">
                            <span className="text-slate-500 capitalize">{k.replace(/_/g, " ")}:</span>{" "}
                            <span className="text-slate-200">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="text-[10px] text-slate-500">
                      Synthesized from {profile.source_doc_count} document chunk(s) • Last updated: {profile.updated_at}
                    </div>
                  </div>
                ) : (
                  <p className="text-slate-500 italic py-2">
                    No profile synthesized yet. Upload travel documents or guidelines to automatically build your profile.
                  </p>
                )}
              </div>

              {/* TTL Reaper Card (Phase 5) */}
              <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-amber-400" /> Automated 2-Hour TTL Reaper
                  </span>
                  <button
                    type="button"
                    onClick={handleRunReaper}
                    disabled={loading}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 text-[11px] font-medium transition cursor-pointer"
                  >
                    Run Purge Now
                  </button>
                </div>

                <p className="text-slate-400 text-[11px]">
                  Background worker purges guest interactions, uploaded files, and vector embeddings older than 2 hours.
                </p>

                {reaperStats && (
                  <div className="grid grid-cols-4 gap-2 pt-1 text-center">
                    <div className="p-2 rounded bg-slate-900/40 border border-slate-800">
                      <div className="text-base font-bold text-white">{reaperStats.total_purged_memories}</div>
                      <div className="text-[10px] text-slate-500">Memories Purged</div>
                    </div>
                    <div className="p-2 rounded bg-slate-900/40 border border-slate-800">
                      <div className="text-base font-bold text-white">{reaperStats.total_purged_documents}</div>
                      <div className="text-[10px] text-slate-500">Docs Purged</div>
                    </div>
                    <div className="p-2 rounded bg-slate-900/40 border border-slate-800">
                      <div className="text-base font-bold text-white">{reaperStats.total_purged_users}</div>
                      <div className="text-[10px] text-slate-500">Guests Cleared</div>
                    </div>
                    <div className="p-2 rounded bg-slate-900/40 border border-slate-800">
                      <div className="text-base font-bold text-white">{reaperStats.total_purged_dirs}</div>
                      <div className="text-[10px] text-slate-500">Folders Removed</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
