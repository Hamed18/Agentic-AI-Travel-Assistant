import React, { useState, useEffect } from "react";
import { uploadDocument, ingestText, listDocuments, deleteDocument } from "../api";
import { X, Upload, FileText, Trash2, CheckCircle2, AlertCircle, Loader2, Database, Shield } from "lucide-react";

export default function AdminIngestionModal({ isOpen, onClose, user }) {
  const [activeTab, setActiveTab] = useState("upload"); // "upload" | "text" | "documents"
  const [documents, setDocuments] = useState([]);
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

  useEffect(() => {
    if (isOpen) {
      loadDocs();
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
        message: `Successfully ingested "${res.filename}" (${res.chunks_indexed} vector chunks indexed for tenant ${res.owner_id}).`,
      });
      setSelectedFile(null);
      loadDocs();
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
        message: `Successfully indexed "${res.title}" (${res.chunks_indexed} vector chunks indexed for tenant ${res.owner_id}).`,
      });
      setTextTitle("");
      setTextContent("");
      loadDocs();
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 sm:p-8 text-slate-100 flex flex-col max-h-[90vh]">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
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
                Tenant Isolated
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Ingest travel guidelines, policies, or itineraries into your isolated vector database.
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="grid grid-cols-3 p-1 bg-slate-950/60 rounded-xl mb-4 border border-slate-800/80">
          <button
            type="button"
            onClick={() => setActiveTab("upload")}
            className={`py-2 text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              activeTab === "upload"
                ? "bg-purple-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            File Upload
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("text")}
            className={`py-2 text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              activeTab === "text"
                ? "bg-purple-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Paste Guide/Policy
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("documents")}
            className={`py-2 text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              activeTab === "documents"
                ? "bg-purple-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            Tenant Index ({documents.length})
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
                      className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-red-950/30 transition shrink-0 ml-2"
                      title="Delete document and vector embeddings"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
