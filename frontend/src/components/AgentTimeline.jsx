import React from "react";
import { CheckCircle2, Loader2, Clock, Plane, Hotel, CloudSun, Calculator, MapPin, UserCheck, Compass, Sparkles } from "lucide-react";

export default function AgentTimeline({ stages = {}, intent = "trip_planning", error }) {
  // Direct response fast-path indicator (for greetings, emergency, situational, how-to)
  if (intent && intent !== "trip_planning") {
    return (
      <div className="bg-[#131b2e] border border-blue-500/30 rounded-2xl p-4 my-3 shadow-xl backdrop-blur-sm animate-pulse">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-400 flex items-center justify-center shadow-lg shadow-blue-500/20 text-white flex-shrink-0">
            <Compass className="w-5 h-5 animate-spin" />
          </div>
          <div className="min-w-0">
            <h4 className="text-xs sm:text-sm font-bold text-white flex items-center gap-1.5">
              <span>SagaTraveller Concierge Answering</span>
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
            </h4>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Formulating practical travel guidance and verified recommendations...
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Multi-agent trip planning progress stages
  const stageDefs = [
    {
      id: "supervisor",
      label: "Trip Preferences & Destination Analysis",
      icon: Compass,
      desc: "Analyzing destination, trip duration, travel style & personal preferences",
    },
    {
      id: "parallel_specialists",
      label: "Live Travel Research",
      icon: Plane,
      desc: "Simultaneously searching live flights, verified hotels & local weather forecasts",
    },
    {
      id: "budget_agent",
      label: "Smart Budget Allocation",
      icon: Calculator,
      desc: "Optimizing itemized costs for flights, hotels, dining & sightseeing activities",
    },
    {
      id: "itinerary_agent",
      label: "Personalized Daily Schedule",
      icon: MapPin,
      desc: "Crafting day-by-day morning, afternoon & evening experiences",
    },
    {
      id: "human_approval",
      label: "Personal Plan Review",
      icon: UserCheck,
      desc: "Ready for your review — approve the plan or request any custom adjustments",
    },
  ];

  // Calculate live progress percentage and active micro-status for user trust
  let progressPercent = 15;
  let microStatus = "Analyzing travel preferences...";

  if (stages.human_approval === "running" || stages.human_approval === "complete") {
    progressPercent = 100;
    microStatus = "Personal plan ready for your review!";
  } else if (stages.itinerary_agent === "running" || stages.itinerary_agent === "complete") {
    progressPercent = 88;
    microStatus = "Structuring day-by-day morning, afternoon & evening activities...";
  } else if (stages.budget_agent === "running" || stages.budget_agent === "complete") {
    progressPercent = 68;
    microStatus = "Optimizing budget breakdown and estimating category totals...";
  } else if (stages.parallel_specialists === "running" || stages.parallel_specialists === "complete") {
    progressPercent = 42;
    microStatus = "Searching live flight options, hotel accommodations & weather trends...";
  } else if (stages.supervisor === "complete") {
    progressPercent = 25;
    microStatus = "Destination preferences locked. Dispatching specialist agents...";
  }

  return (
    <div className="bg-[#131b2e] border border-[#1e293b] rounded-2xl p-3.5 sm:p-4 my-3 shadow-xl backdrop-blur-sm">
      {/* Header with Title and Pulse */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#1e293b] mb-3">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse flex-shrink-0" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Trip Planning in Progress
          </h3>
        </div>
        <span className="text-[10px] sm:text-[11px] font-medium text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20 flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-blue-400" />
          <span>Live Orchestration Active</span>
        </span>
      </div>

      {/* Trust-Building Progress Meter */}
      <div className="mb-4 bg-[#0d1424] p-3 rounded-xl border border-[#1e293b]">
        <div className="flex items-center justify-between text-[11px] mb-1.5">
          <span className="text-slate-300 font-medium flex items-center gap-1.5">
            <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin" />
            <span className="truncate">{microStatus}</span>
          </span>
          <span className="text-blue-400 font-bold">{progressPercent}%</span>
        </div>
        <div className="w-full h-2 bg-[#131b2e] rounded-full overflow-hidden border border-white/5">
          <div
            className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-sky-400 transition-all duration-500 rounded-full"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Stage Breakdown Cards */}
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
                    {status === "complete" ? "Completed" : status === "running" ? "In Progress..." : "Upcoming"}
                  </span>
                </div>

                <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                  {def.desc}
                </p>

                {/* Sub-Badges for Specialists */}
                {def.id === "parallel_specialists" && status === "complete" && (
                  <div className="flex flex-wrap items-center gap-1.5 mt-2 pt-1.5 border-t border-[#1e293b]/50 text-[10px]">
                    <span className="flex items-center gap-1 text-slate-300 bg-[#1a2540] px-2 py-0.5 rounded-md border border-[#2d3f5e]">
                      <Plane className="w-3 h-3 text-sky-400" /> Flights Found
                    </span>
                    <span className="flex items-center gap-1 text-slate-300 bg-[#1a2540] px-2 py-0.5 rounded-md border border-[#2d3f5e]">
                      <Hotel className="w-3 h-3 text-amber-400" /> Hotels Evaluated
                    </span>
                    <span className="flex items-center gap-1 text-slate-300 bg-[#1a2540] px-2 py-0.5 rounded-md border border-[#2d3f5e]">
                      <CloudSun className="w-3 h-3 text-emerald-400" /> Weather Analyzed
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
          <span>Notice: {error}</span>
        </div>
      )}
    </div>
  );
}
