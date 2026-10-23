import React from "react";
import {
  Plus,
  MessageSquare,
  Trash2,
  Compass,
  ChevronLeft,
  Sparkles,
  ShieldCheck,
  Info,
  ChevronRight,
  Database,
  LogOut,
  User,
  Shield,
} from "lucide-react";

export default function Sidebar({
  isOpen,
  onClose,
  threads,
  activeThreadId,
  onSelectThread,
  onNewTrip,
  onDeleteThread,
  healthStatus,
  onOpenAbout,
  user,
  onOpenAuth,
  onOpenAdmin,
  onLogout,
}) {
  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/75 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300"
          aria-hidden="true"
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-[#0d1322] border-r border-[#1e293b] flex flex-col h-full select-none transition-all duration-300 ease-in-out lg:static ${
          isOpen ? "translate-x-0 lg:ml-0" : "-translate-x-full lg:-ml-72 lg:pointer-events-none"
        }`}
      >
        {/* Brand Header with SagaTraveller Logo */}
        <div className="p-4 border-b border-[#1e293b] flex-shrink-0">
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

            {/* Collapse Arrow Button */}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#1a2540] transition-colors"
              title="Close sidebar"
              aria-label="Close sidebar"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          </div>

          {/* New Trip Button */}
          <button
            onClick={() => {
              onNewTrip();
              if (window.innerWidth < 1024) onClose();
            }}
            className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition-all duration-200 shadow-lg shadow-blue-600/25 active:scale-95 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            New Travel Plan
          </button>
        </div>

        {/* User Account / Tenant Card */}
        <div className="px-4 py-2.5 border-b border-[#1e293b]/60 bg-[#090d16]/40 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 min-w-0">
            <div className={`w-6 h-6 rounded-lg flex items-center justify-center ${user?.role === "admin" ? "bg-purple-600/20 text-purple-400 border border-purple-500/30" : "bg-blue-600/20 text-blue-400 border border-blue-500/30"}`}>
              {user?.role === "admin" ? <Shield className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
            </div>
            <div className="truncate">
              <div className="font-semibold text-slate-200 truncate">
                {user?.name || (user?.is_guest ? "Guest Traveler" : user?.email || "Traveler")}
              </div>
              <div className="text-[10px] text-slate-500 capitalize">
                {user?.role === "admin" ? "Admin Privileges" : user?.is_guest ? "2h Temporary Session" : "Registered User"}
              </div>
            </div>
          </div>

          {user?.is_guest ? (
            <button
              onClick={onOpenAuth}
              className="text-[11px] text-blue-400 hover:text-blue-300 font-medium px-2 py-1 rounded bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 transition cursor-pointer"
            >
              Sign In
            </button>
          ) : (
            <button
              onClick={onLogout}
              className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-red-950/20 transition cursor-pointer"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Admin Knowledge Ingestion Button (If Admin) */}
        {user?.role === "admin" && (
          <div className="px-3 pt-3">
            <button
              onClick={() => {
                if (onOpenAdmin) onOpenAdmin();
                if (window.innerWidth < 1024) onClose();
              }}
              className="w-full flex items-center justify-between p-2.5 rounded-xl bg-purple-950/40 border border-purple-500/30 text-purple-300 hover:text-white hover:bg-purple-900/30 text-xs font-semibold transition shadow-sm active:scale-95 cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-purple-400" />
                <span>Knowledge Ingestion Hub</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-600/30 text-purple-200 border border-purple-500/40">
                Admin
              </span>
            </button>
          </div>
        )}

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
                    if (window.innerWidth < 1024) onClose();
                  }}
                  className={`group flex items-center justify-between p-2.5 rounded-xl text-xs font-medium cursor-pointer transition-all ${
                    isActive
                      ? "bg-[#1a2540] text-blue-300 border border-blue-500/30 shadow-sm"
                      : "text-slate-400 hover:text-slate-200 hover:bg-[#131b2e]"
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <MessageSquare className="w-4 h-4 shrink-0" />
                    <span className="truncate">{t.title}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteThread(t.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 rounded transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Sidebar Footer: About SagaTraveller & Status Card */}
        <div className="p-3 border-t border-[#1e293b] bg-[#0a0f1d] space-y-2 flex-shrink-0">
          <button
            onClick={() => {
              if (onOpenAbout) onOpenAbout();
              if (window.innerWidth < 1024) onClose();
            }}
            className="w-full flex items-center justify-between p-2.5 rounded-xl bg-gradient-to-r from-blue-900/30 to-indigo-900/30 border border-blue-500/30 text-blue-300 hover:text-white hover:bg-blue-600/20 text-xs font-medium transition-all group shadow-sm active:scale-95 cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-blue-400 group-hover:rotate-12 transition-transform" />
              <span>About SagaTraveller</span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-blue-400" />
          </button>

          <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl space-y-1.5 text-[11px]">
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

            <div className="pt-1.5 border-t border-[#1e293b] flex items-center justify-between text-[10px]">
              <span className="text-slate-400 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-blue-400" /> Multi-Tenant
              </span>
              <span className="text-slate-300 font-medium">JWT &amp; Vector Isolated</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
