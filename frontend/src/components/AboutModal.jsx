import React from "react";
import {
  X,
  Compass,
  ShieldAlert,
  Activity,
  Layers,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Plane,
  Hotel,
  CloudSun,
  DollarSign,
  FileText,
  UserCheck,
  Zap,
  Lock,
  Search,
} from "lucide-react";

export default function AboutModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      {/* Click outside backdrop */}
      <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />

      {/* Modal Card */}
      <div className="relative w-full max-w-3xl max-h-[90dvh] bg-[#0d1322] border border-[#1e293b] rounded-2xl shadow-2xl flex flex-col overflow-hidden z-10">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1e293b] bg-[#111827]/70 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-400 flex items-center justify-center shadow-lg shadow-blue-500/25 flex-shrink-0">
              <Compass className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                About Saga<span className="text-blue-400">Traveller</span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  Production v1.0
                </span>
              </h2>
              <p className="text-xs text-slate-400">Enterprise-Grade Multi-Agent Travel Planning System</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-[#1f293d] transition-colors"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6 text-xs sm:text-sm text-slate-300 leading-relaxed">
          
          {/* Section 1: What is SagaTraveller & Problem Solved */}
          <div className="space-y-2.5">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Compass className="w-4 h-4 text-blue-400" /> What is SagaTraveller?
            </h3>
            <p className="text-slate-300 text-xs sm:text-sm">
              <strong className="text-white">SagaTraveller</strong> is a stateful, autonomous AI travel concierge designed to overcome the critical flaws of traditional single-prompt chatbots. Powered by a decoupled <strong>FastAPI backend</strong>, <strong>LangGraph state engine</strong>, and <strong>React 19 frontend</strong>, it connects real-world travel tools to build accurate, actionable journey itineraries.
            </p>

            <div className="grid sm:grid-cols-2 gap-3 pt-2">
              <div className="p-3 rounded-xl bg-red-950/20 border border-red-900/30 space-y-1.5">
                <span className="text-red-400 font-semibold text-xs flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" /> The Problem with Traditional LLMs
                </span>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Standard LLMs fabricate non-existent flight routes, hallucinate hotel prices, ignore weather disruptions, and cannot adapt to real-world logistical emergencies without making up fake schedules.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-900/30 space-y-1.5">
                <span className="text-emerald-400 font-semibold text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> The SagaTraveller Solution
                </span>
                <p className="text-[11px] text-slate-400 leading-normal">
                  Live data verification through <strong>Model Context Protocol (FastMCP)</strong>, deterministic security screening, multi-agent parallel execution, and a strict <strong>Human-in-the-Loop review gate</strong>.
                </p>
              </div>
            </div>
          </div>

          {/* Section 2: Real-World Use Cases */}
          <div className="space-y-3 pt-2 border-t border-[#1e293b]">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" /> Real-World Use Cases &amp; Examples
            </h3>
            <div className="grid sm:grid-cols-2 gap-2.5">
              <div className="p-3 rounded-xl bg-[#131b2e] border border-[#1e293b] space-y-1">
                <span className="font-semibold text-white text-xs block text-blue-300">1. Complete Itinerary Planning</span>
                <p className="text-[11px] text-slate-400">
                  <em>Example:</em> "Plan a 4-day luxury trip to Paris focusing on art and food for $3000."
                </p>
                <p className="text-[11px] text-slate-400">
                  Coordinates Flights (AviationStack), Hotels (Tavily), Weather (OpenWeather), and Budget Optimization into a publication-grade PDF.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[#131b2e] border border-[#1e293b] space-y-1">
                <span className="font-semibold text-white text-xs block text-blue-300">2. In-Trip Situational Mishaps</span>
                <p className="text-[11px] text-slate-400">
                  <em>Example:</em> "I forgot my blanket and it's a freezing winter night in Munich."
                </p>
                <p className="text-[11px] text-slate-400">
                  Supervisor fast-paths directly to emergency situational assistance with 24/7 store advice, avoiding hallucinated tour plans.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[#131b2e] border border-[#1e293b] space-y-1">
                <span className="font-semibold text-white text-xs block text-blue-300">3. Health, Altitude &amp; Safety</span>
                <p className="text-[11px] text-slate-400">
                  <em>Example:</em> "I feel sick and dizzy while hiking in the Alps."
                </p>
                <p className="text-[11px] text-slate-400">
                  Immediate emergency safety protocols, local emergency contact routing, and descent guidelines.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[#131b2e] border border-[#1e293b] space-y-1">
                <span className="font-semibold text-white text-xs block text-blue-300">4. Travel Documents &amp; Compliance</span>
                <p className="text-[11px] text-slate-400">
                  <em>Example:</em> "What documents do I need to visit Japan?"
                </p>
                <p className="text-[11px] text-slate-400">
                  Returns exact visa requirements, passport validity rules, and customs declaration steps without triggering expensive tool pipelines.
                </p>
              </div>
            </div>
          </div>

          {/* Section 3: Security & Guardrails */}
          <div className="space-y-2.5 pt-2 border-t border-[#1e293b]">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Lock className="w-4 h-4 text-emerald-400" /> Security Layers &amp; Guardrails (&lt;50ms)
            </h3>
            <p className="text-xs text-slate-400">
              Before any user input reaches an LLM, it passes through deterministic mathematical and regex filters:
            </p>
            <div className="space-y-2">
              <div className="p-2.5 rounded-xl bg-[#131b2e] border border-[#1e293b] flex items-start gap-2.5">
                <ShieldAlert className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-semibold text-slate-200">Financial PII &amp; Credit Card Protection (Luhn Algorithm)</span>
                  <p className="text-[11px] text-slate-400">
                    Pre-compiled regexes identify credit card numbers and validate them using the mathematical Luhn checksum algorithm. Valid numbers are instantly blocked with a privacy refusal notice.
                  </p>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-[#131b2e] border border-[#1e293b] flex items-start gap-2.5">
                <Lock className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-semibold text-slate-200">Adversarial Jailbreak &amp; Prompt Injection Defense</span>
                  <p className="text-[11px] text-slate-400">
                    Zero-latency heuristic patterns intercept system prompt extraction, role overrides, and DAN jailbreak attempts in &lt;1ms.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Section 4: Multi-Agent Architecture & FastMCP */}
          <div className="space-y-2.5 pt-2 border-t border-[#1e293b]">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-sky-400" /> Multi-Agent Engine &amp; FastMCP Tools
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl">
                <Cpu className="w-4 h-4 text-blue-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Supervisor</span>
                <span className="text-[10px] text-slate-400">Intent Routing</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl">
                <Plane className="w-4 h-4 text-sky-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Flight MCP</span>
                <span className="text-[10px] text-slate-400">AviationStack</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl">
                <Hotel className="w-4 h-4 text-indigo-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Hotel Agent</span>
                <span className="text-[10px] text-slate-400">Tavily Search</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl">
                <CloudSun className="w-4 h-4 text-amber-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Weather MCP</span>
                <span className="text-[10px] text-slate-400">OpenWeather</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl">
                <DollarSign className="w-4 h-4 text-emerald-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Budget Agent</span>
                <span className="text-[10px] text-slate-400">Cost Optimization</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl">
                <FileText className="w-4 h-4 text-purple-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Itinerary</span>
                <span className="text-[10px] text-slate-400">Synthesis Engine</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl">
                <UserCheck className="w-4 h-4 text-pink-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">Human Gate</span>
                <span className="text-[10px] text-slate-400">Pause / Approval</span>
              </div>
              <div className="p-2.5 bg-[#131b2e] border border-[#1e293b] rounded-xl">
                <FileText className="w-4 h-4 text-teal-400 mx-auto mb-1" />
                <span className="font-semibold text-[11px] text-white block">PDF Engine</span>
                <span className="text-[10px] text-slate-400">ReportLab Doc</span>
              </div>
            </div>
          </div>

          {/* Section 5: Observability & Resilience */}
          <div className="space-y-2 pt-2 border-t border-[#1e293b]">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-400" /> Observability &amp; Distributed Resilience
            </h3>
            <div className="p-3 bg-[#131b2e] border border-[#1e293b] rounded-xl space-y-1.5 text-xs text-slate-300">
              <p>
                <strong>LangSmith:</strong> Native LangGraph execution DAG tracing, providing step-by-step visibility into every agent node transition.
              </p>
              <p>
                <strong>Langfuse v5:</strong> Real-time token analytics, exact USD cost tracking, and P50/P99 latency distribution per user session.
              </p>
              <p>
                <strong>Distributed Failover:</strong> Ultra-fast Groq LPU (Qwen 27B / GPT-OSS 120B) automatically fails over to Google Gemini 3.5 Flash Lite if rate limits occur, guaranteeing 100% free-tier uptime.
              </p>
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="p-3.5 sm:p-4 border-t border-[#1e293b] bg-[#111827]/70 flex items-center justify-between flex-shrink-0">
          <span className="text-[11px] text-slate-400">
            Built by{" "}
            <a
              href="https://www.linkedin.com/in/devhamed/"
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
            Got it, Let's Explore!
          </button>
        </div>
      </div>
    </div>
  );
}
