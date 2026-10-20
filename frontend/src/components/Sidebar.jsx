import React from "react";
import { Plus, MessageSquare, Trash2, Compass, X, ChevronLeft, Sparkles, ShieldCheck } from "lucide-react";

export default function Sidebar({
  isOpen,
  onClose,
  threads,
  activeThreadId,
  onSelectThread,
  onNewTrip,
  onDeleteThread,
  healthStatus,
}) {
  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 md:hidden transition-opacity animate-fadeIn"
          aria-hidden="true"
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-[#0d1322] border-r border-[#1e293b] flex flex-col h-screen select-none transition-transform duration-300 ease-in-out md:static ${
          isOpen ? "translate-x-0" : "-translate-x-full md:-ml-72"
        }`}
      >
        {/* Brand Header with SagaTraveller Logo */}
        <div className="p-4 border-b border-[#1e293b]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-400 flex items-center justify-center shadow-lg shadow-blue-500/25 flex-shrink-0">
                <Compass className="w-5 h-5 text-white" />
              </div>
              <div className="min-w-0">
                <h1 className="font-extrabold text-base tracking-tight text-white truncate">
                  Saga<span className="text-blue-400">Traveller</span>
                </h1>
                <p className="text-[11px] text-slate-400 font-medium">Personal Travel Concierge</p>
              </div>
            </div>

            {/* Close button (Arrow / X) */}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#1a2540] transition-colors"
              title="Close sidebar"
              aria-label="Close sidebar"
            >
              <span className="hidden md:inline">
                <ChevronLeft className="w-5 h-5" />
              </span>
              <span className="md:hidden">
                <X className="w-5 h-5" />
              </span>
            </button>
          </div>

          {/* New Trip Button */}
          <button
            onClick={() => {
              onNewTrip();
              if (window.innerWidth < 768) onClose();
            }}
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
                  onClick={() => {
                    onSelectThread(t.id);
                    if (window.innerWidth < 768) onClose();
                  }}
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

        {/* User-Friendly Concierge Features Card */}
        <div className="p-3 border-t border-[#1e293b] bg-[#0a0f1d] space-y-2">
          <div className="p-3 bg-[#131b2e] border border-[#1e293b] rounded-xl space-y-2 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-slate-200 flex items-center gap-1.5 font-semibold">
                <Sparkles className="w-3.5 h-3.5 text-blue-400" /> Smart Concierge
              </span>
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Ready
              </span>
            </div>
            <p className="text-[10px] text-slate-400 leading-relaxed">
              Instant flights, verified hotel stays, local weather forecasts, and custom daily itineraries.
            </p>

            <div className="pt-2 border-t border-[#1e293b] flex items-center justify-between text-[10px]">
              <span className="text-slate-400 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-blue-400" /> Cloud Sync
              </span>
              <span className="text-slate-300 font-medium">Automatic &amp; Secure</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
