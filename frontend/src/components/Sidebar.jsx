import React from "react";
import { Plus, MessageSquare, Trash2, Cpu, Activity, ShieldCheck, Compass } from "lucide-react";

export default function Sidebar({
  threads,
  activeThreadId,
  onSelectThread,
  onNewTrip,
  onDeleteThread,
  healthStatus,
}) {
  return (
    <aside className="w-72 bg-[#0d1322] border-r border-[#1e293b] flex flex-col h-screen select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-[#1e293b]">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Compass className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-wide text-white">TRAVEL ASSISTANT</h1>
            <p className="text-[11px] text-blue-400 font-medium">Multi-Agent System</p>
          </div>
        </div>

        {/* New Trip Button */}
        <button
          onClick={onNewTrip}
          className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition-all duration-200 shadow-lg shadow-blue-600/25 active:scale-95"
        >
          <Plus className="w-4 h-4" />
          New Travel Plan
        </button>
      </div>

      {/* Threads List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="px-2 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Saved Itineraries
        </div>

        {threads.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-500 italic">
            No previous trips yet. Start by planning your first journey!
          </div>
        ) : (
          threads.map((t) => {
            const isActive = t.id === activeThreadId;
            return (
              <div
                key={t.id}
                onClick={() => onSelectThread(t.id)}
                className={`group flex items-center justify-between p-2.5 rounded-xl cursor-pointer text-xs transition-all duration-150 ${
                  isActive
                    ? "bg-[#1a2540] text-blue-300 font-medium border border-blue-500/30 shadow-md"
                    : "text-slate-400 hover:bg-[#131b2e] hover:text-slate-200"
                }`}
              >
                <div className="flex items-center gap-2.5 truncate pr-2">
                  <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? "text-blue-400" : "text-slate-500"}`} />
                  <span className="truncate">{t.title || "Untitled Trip"}</span>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteThread(t.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 text-slate-500 rounded transition-opacity"
                  title="Delete chat"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* System Telemetry & Model Tiering Info Card */}
      <div className="p-3 border-t border-[#1e293b] bg-[#0a0f1d] space-y-2">
        <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl space-y-2 text-[11px]">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5 font-medium">
              <Cpu className="w-3.5 h-3.5 text-blue-400" /> Model Tiering
            </span>
            <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[10px] font-semibold">
              Distributed
            </span>
          </div>
          <p className="text-[10px] text-slate-400 leading-relaxed">
            Groq LPU (Qwen 27B / GPT-OSS 120B) with automatic failover to Google Gemini 3.5 Flash Lite.
          </p>

          <div className="pt-1.5 border-t border-[#1e293b] flex items-center justify-between text-[10px]">
            <span className="text-slate-400 flex items-center gap-1">
              <Activity className="w-3 h-3 text-emerald-400" /> Tracing
            </span>
            <span className="text-emerald-400 font-medium">LangSmith + Langfuse</span>
          </div>

          <div className="flex items-center justify-between text-[10px]">
            <span className="text-slate-400 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-indigo-400" /> Backend
            </span>
            <span className={healthStatus?.status === "healthy" ? "text-emerald-400" : "text-amber-400"}>
              {healthStatus?.status === "healthy" ? "Online (Neon DB)" : "Connecting..."}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
