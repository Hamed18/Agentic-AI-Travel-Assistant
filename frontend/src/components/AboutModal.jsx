import React from "react";
import {
  X,
  Compass,
  CheckCircle2,
  AlertTriangle,
  Plane,
  Hotel,
  CloudSun,
  DollarSign,
  FileText,
  UserCheck,
  Zap,
  Shield,
  HelpCircle,
} from "lucide-react";

export default function AboutModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      {/* Click outside backdrop */}
      <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />

      {/* Modal Card */}
      <div className="relative w-full max-w-2xl max-h-[90dvh] bg-[#0d1322] border border-[#1e293b] rounded-2xl shadow-2xl flex flex-col overflow-hidden z-10">
        
        {/* Header - Fixed & Never Broken */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 sm:py-4 border-b border-[#1e293b] bg-[#111827]/90 flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-400 flex items-center justify-center shadow-lg shadow-blue-500/25 flex-shrink-0">
              <Compass className="w-5 h-5 text-white" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-base sm:text-lg font-extrabold text-white tracking-tight whitespace-nowrap">
                  Saga<span className="text-blue-400">Traveller</span>
                </span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 whitespace-nowrap">
                  User Guide
                </span>
              </div>
              <p className="text-xs text-slate-400 truncate">Your Personal AI Travel Concierge</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 sm:p-2 rounded-xl text-slate-400 hover:text-white hover:bg-[#1f293d] transition-colors flex-shrink-0"
            title="Close"
            aria-label="Close guide"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 text-xs sm:text-sm text-slate-300 leading-relaxed">
          
          {/* Section 1: What is SagaTraveller? */}
          <div className="space-y-2">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Compass className="w-4 h-4 text-blue-400 flex-shrink-0" /> What is SagaTraveller?
            </h3>
            <p className="text-slate-300 leading-relaxed">
              <strong className="text-white">SagaTraveller</strong> is your all-in-one smart travel assistant designed to make planning journeys effortless, enjoyable, and completely personalized.
            </p>
            <p className="text-slate-400 leading-relaxed">
              Instead of spending hours jumping between travel blogs, flight search engines, hotel booking sites, and weather apps, you simply tell SagaTraveller what kind of trip you want. It searches live flights, finds quality hotel stays, monitors local destination weather, organizes your budget, and delivers a complete day-by-day travel plan ready to download as a PDF.
            </p>

            <div className="grid sm:grid-cols-2 gap-2.5 pt-1">
              <div className="p-3 rounded-xl bg-red-950/20 border border-red-900/30 space-y-1">
                <span className="text-red-400 font-semibold text-xs flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" /> Ordinary Chatbots
                </span>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Make up non-existent flight routes, guess hotel rates, ignore real weather disruptions, and cannot help with practical travel emergencies.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-900/30 space-y-1">
                <span className="text-emerald-400 font-semibold text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" /> With SagaTraveller
                </span>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Every recommendation is checked against live flight information and local forecasts. You get complete review control before anything is finalized.
                </p>
              </div>
            </div>
          </div>

          {/* Section 2: Real-World Use Cases */}
          <div className="space-y-2.5 pt-2 border-t border-[#1e293b]">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400 flex-shrink-0" /> How It Helps You (Real-World Examples)
            </h3>
            <div className="grid sm:grid-cols-2 gap-2.5">
              <div className="p-3 rounded-xl bg-[#131b2e] border border-[#1e293b] space-y-1">
                <span className="font-semibold text-white text-xs block text-blue-300">1. Complete Trip Planning</span>
                <p className="text-[11px] text-slate-400">
                  <em>Example:</em> "Plan a 4-day luxury trip to Paris focusing on art and food for $3000."
                </p>
                <p className="text-[11px] text-slate-400">
                  Finds real flights, recommends verified hotels, plans balanced daily activities, and fits everything neatly inside your budget.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[#131b2e] border border-[#1e293b] space-y-1">
                <span className="font-semibold text-white text-xs block text-blue-300">2. In-Trip Emergencies &amp; Advice</span>
                <p className="text-[11px] text-slate-400">
                  <em>Example:</em> "I forgot my warm blanket and it's a freezing winter night in Munich."
                </p>
                <p className="text-[11px] text-slate-400">
                  Gives immediate practical advice on 24/7 stores, warm essentials, and local tips without making up unwanted vacation plans.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[#131b2e] border border-[#1e293b] space-y-1">
                <span className="font-semibold text-white text-xs block text-blue-300">3. Health &amp; Outdoor Safety</span>
                <p className="text-[11px] text-slate-400">
                  <em>Example:</em> "I'm feeling dizzy while hiking at high altitude in the Alps."
                </p>
                <p className="text-[11px] text-slate-400">
                  Provides emergency health steps, local emergency numbers, and safe descent guidance right away.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[#131b2e] border border-[#1e293b] space-y-1">
                <span className="font-semibold text-white text-xs block text-blue-300">4. Travel Documents &amp; Checklists</span>
                <p className="text-[11px] text-slate-400">
                  <em>Example:</em> "What documents do I need to visit Japan?"
                </p>
                <p className="text-[11px] text-slate-400">
                  Delivers clear passport validity guidelines, visa requirements, customs rules, and packing tips.
                </p>
              </div>
            </div>
          </div>

          {/* Section 3: How It Works Behind the Scenes (User-Friendly) */}
          <div className="space-y-2.5 pt-2 border-t border-[#1e293b]">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-sky-400 flex-shrink-0" /> How Your Journey is Built
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl text-center">
                <Plane className="w-4 h-4 text-sky-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Flight Finder</span>
                <span className="text-[10px] text-slate-400">Real flight routes &amp; timings</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl text-center">
                <Hotel className="w-4 h-4 text-indigo-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Hotel Scout</span>
                <span className="text-[10px] text-slate-400">Top-rated stays in safe areas</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl text-center">
                <CloudSun className="w-4 h-4 text-amber-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Weather Check</span>
                <span className="text-[10px] text-slate-400">Live destination forecasts</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl text-center">
                <DollarSign className="w-4 h-4 text-emerald-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Budget Calculator</span>
                <span className="text-[10px] text-slate-400">Keeps spending on target</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl text-center">
                <UserCheck className="w-4 h-4 text-pink-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Your Review Gate</span>
                <span className="text-[10px] text-slate-400">You approve before finalize</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl text-center">
                <FileText className="w-4 h-4 text-teal-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">PDF Export</span>
                <span className="text-[10px] text-slate-400">Ready-to-print itinerary</span>
              </div>
            </div>
          </div>

          {/* Section 4: Privacy & Protection */}
          <div className="space-y-2 pt-2 border-t border-[#1e293b]">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Shield className="w-4 h-4 text-emerald-400 flex-shrink-0" /> Privacy &amp; Data Protection
            </h3>
            <div className="p-3 bg-[#131b2e] border border-[#1e293b] rounded-xl text-xs text-slate-300 space-y-1">
              <p>
                <strong>Automatic Privacy Shield:</strong> Your sensitive financial information (such as credit card numbers) is automatically detected and blocked. The system never stores, processes, or shares payment credentials.
              </p>
              <p className="text-slate-400 text-[11px]">
                Enjoy peace of mind knowing your travel planning is secure, confidential, and completely private.
              </p>
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="p-3.5 sm:p-4 border-t border-[#1e293b] bg-[#111827]/90 flex items-center justify-between flex-shrink-0">
          <span className="text-[11px] text-slate-400">
            Created by{" "}
            <a
              href="https://hamedhasan.vercel.app/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 font-semibold underline underline-offset-2"
            >
              Hamed Hasan
            </a>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-md active:scale-95 transition-all"
          >
            Got it, Let's Plan!
          </button>
        </div>
      </div>
    </div>
  );
}
