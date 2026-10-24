import React from "react";
import { Clock, ArrowRight } from "lucide-react";

export default function GuestBanner({ onOpenAuth }) {
  return (
    <div className="bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-amber-500/10 border-b border-amber-500/20 px-4 py-1.5 text-xs text-amber-200/90 flex items-center justify-between gap-3 shadow-inner shrink-0">
      <div className="flex items-center gap-2 overflow-hidden">
        <span className="flex h-2 w-2 relative shrink-0">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
        </span>
        <Clock className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span className="truncate">
          <strong className="text-amber-300 font-medium">Guest Mode:</strong> Your session and data are temporary (auto-purged after 2 hours).
        </span>
      </div>

      <button
        type="button"
        onClick={onOpenAuth}
        className="shrink-0 flex items-center gap-1.5 px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 rounded-lg text-amber-200 hover:text-white font-medium transition cursor-pointer"
      >
        <span>Sign In / Register</span>
        <ArrowRight className="w-3 h-3" />
      </button>
    </div>
  );
}
