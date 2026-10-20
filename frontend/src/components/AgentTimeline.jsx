import React from "react";
import { CheckCircle2, Loader2, Clock, Plane, Hotel, CloudSun, Calculator, MapPin, UserCheck, ShieldAlert } from "lucide-react";

export default function AgentTimeline({ stages, activeStage, isInterrupted, error }) {
  const stageDefs = [
    {
      id: "supervisor",
      label: "Supervisor Guardrail & Routing",
      icon: ShieldAlert,
      desc: "Validates trip intent, extracts destination & coordinates specialists",
    },
    {
      id: "parallel_specialists",
      label: "Parallel Specialists",
      icon: Plane,
      desc: "Concurrently executes Flight MCP, Hotel Search & Weather MCP tools",
    },
    {
      id: "budget_agent",
      label: "Budget Math Engine",
      icon: Calculator,
      desc: "Computes itemized allocations, flights, lodging & activity reserves",
    },
    {
      id: "itinerary_agent",
      label: "Itinerary Synthesis",
      icon: MapPin,
      desc: "Generates multi-day itinerary with Morning, Afternoon & Evening schedules",
    },
    {
      id: "human_approval",
      label: "Human Review & Approval",
      icon: UserCheck,
      desc: "Pauses execution for your personal review, approval or custom revisions",
    },
  ];

  return (
    <div className="bg-[#131b2e] border border-[#1e293b] rounded-2xl p-3.5 sm:p-4 my-3 shadow-xl backdrop-blur-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#1e293b] mb-3">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse flex-shrink-0" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Multi-Agent Pipeline Execution
          </h3>
        </div>
        <span className="text-[10px] sm:text-[11px] font-medium text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20">
          Groq LPUs Concurrency
        </span>
      </div>

      <div className="space-y-2">
        {stageDefs.map((def) => {
          const status = stages[def.id] || "pending";
          const Icon = def.icon;

          return (
            <div
              key={def.id}
              className={`flex items-start gap-2.5 sm:gap-3 p-2.5 rounded-xl transition-all duration-200 border ${
                status === "running"
                  ? "bg-blue-950/30 border-blue-500/40 shadow-md shadow-blue-500/5"
                  : status === "complete"
                  ? "bg-[#0d1424] border-emerald-500/20 text-slate-300"
                  : "bg-transparent border-transparent text-slate-500"
              }`}
            >
              {/* Status Icon */}
              <div className="mt-0.5 flex-shrink-0">
                {status === "complete" ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : status === "running" ? (
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                ) : (
                  <Clock className="w-4 h-4 text-slate-600" />
                )}
              </div>

              {/* Stage Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 font-semibold text-xs text-slate-200 truncate">
                    <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${status === "running" ? "text-blue-400" : status === "complete" ? "text-emerald-400" : "text-slate-500"}`} />
                    <span className="truncate">{def.label}</span>
                  </div>

                  <span
                    className={`text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full flex-shrink-0 ${
                      status === "complete"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : status === "running"
                        ? "bg-blue-500/10 text-blue-400 animate-pulse"
                        : "text-slate-600"
                    }`}
                  >
                    {status}
                  </span>
                </div>

                <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                  {def.desc}
                </p>

                {/* Detailed Badges if Stage is Complete or Running */}
                {def.id === "parallel_specialists" && status === "complete" && (
                  <div className="flex flex-wrap items-center gap-1.5 mt-2 pt-1.5 border-t border-[#1e293b]/50 text-[10px]">
                    <span className="flex items-center gap-1 text-slate-300 bg-[#1a2540] px-2 py-0.5 rounded-md border border-[#2d3f5e]">
                      <Plane className="w-3 h-3 text-sky-400" /> Flights
                    </span>
                    <span className="flex items-center gap-1 text-slate-300 bg-[#1a2540] px-2 py-0.5 rounded-md border border-[#2d3f5e]">
                      <Hotel className="w-3 h-3 text-amber-400" /> Hotels
                    </span>
                    <span className="flex items-center gap-1 text-slate-300 bg-[#1a2540] px-2 py-0.5 rounded-md border border-[#2d3f5e]">
                      <CloudSun className="w-3 h-3 text-emerald-400" /> Forecast
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {error && (
        <div className="mt-3 p-3 bg-red-950/40 border border-red-500/30 rounded-xl text-xs text-red-300 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span>Error in agent pipeline: {error}</span>
        </div>
      )}
    </div>
  );
}
