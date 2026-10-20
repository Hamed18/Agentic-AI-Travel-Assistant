import React, { useState } from "react";
import { UserCheck, Check, Edit3, Send, Sparkles, Loader2 } from "lucide-react";

export default function HumanApprovalCard({ onDecision, isSubmitting, isRevision }) {
  const [choice, setChoice] = useState("approve"); // "approve" or "revise"
  const [feedback, setFeedback] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    const approved = choice === "approve";
    onDecision({ approved, feedback: feedback.trim() });
  };

  return (
    <div className="bg-gradient-to-b from-[#16213e] to-[#0f172a] border border-blue-500/40 rounded-2xl p-3.5 sm:p-5 my-4 shadow-2xl backdrop-blur-md relative overflow-hidden">
      {/* Top Accent Line */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500" />

      <div className="flex items-center gap-2.5 mb-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 flex-shrink-0">
          <UserCheck className="w-4 h-4" />
        </div>
        <div>
          <h4 className="text-xs sm:text-sm font-bold text-white tracking-wide">
            {isRevision ? "Review Revised Travel Plan" : "Human Approval Required"}
          </h4>
          <p className="text-[11px] sm:text-xs text-slate-400">
            Review the drafted itinerary above. You can finalize it now or provide custom adjustments.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 mt-4">
        {/* Choice Radios */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3">
          <label
            onClick={() => setChoice("approve")}
            className={`flex items-start sm:items-center gap-3 p-3 sm:p-3.5 rounded-xl border cursor-pointer transition-all duration-150 ${
              choice === "approve"
                ? "bg-blue-600/15 border-blue-500 text-white font-medium shadow-md shadow-blue-500/10"
                : "bg-[#131b2e] border-[#1e293b] text-slate-400 hover:border-slate-600"
            }`}
          >
            <div
              className={`w-4 h-4 mt-0.5 sm:mt-0 rounded-full border flex items-center justify-center flex-shrink-0 ${
                choice === "approve" ? "border-blue-500 bg-blue-500" : "border-slate-500"
              }`}
            >
              {choice === "approve" && <Check className="w-2.5 h-2.5 text-white" />}
            </div>
            <div className="text-xs">
              <p className="font-semibold text-slate-200 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Yes, generate final plan
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                Finalizes plan and enables publication PDF download
              </p>
            </div>
          </label>

          <label
            onClick={() => setChoice("revise")}
            className={`flex items-start sm:items-center gap-3 p-3 sm:p-3.5 rounded-xl border cursor-pointer transition-all duration-150 ${
              choice === "revise"
                ? "bg-indigo-600/15 border-indigo-500 text-white font-medium shadow-md shadow-indigo-500/10"
                : "bg-[#131b2e] border-[#1e293b] text-slate-400 hover:border-slate-600"
            }`}
          >
            <div
              className={`w-4 h-4 mt-0.5 sm:mt-0 rounded-full border flex items-center justify-center flex-shrink-0 ${
                choice === "revise" ? "border-indigo-500 bg-indigo-500" : "border-slate-500"
              }`}
            >
              {choice === "revise" && <Check className="w-2.5 h-2.5 text-white" />}
            </div>
            <div className="text-xs">
              <p className="font-semibold text-slate-200 flex items-center gap-1.5">
                <Edit3 className="w-3.5 h-3.5 text-indigo-400" /> No, revise with feedback
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                Instruct agents to modify dates, budget, or activities
              </p>
            </div>
          </label>
        </div>

        {/* Feedback Input if Requesting Revision */}
        {choice === "revise" && (
          <div className="space-y-1.5 animate-fadeIn">
            <label className="text-xs font-semibold text-slate-300">
              Revision Instructions
            </label>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="e.g. Choose 4-star boutique hotels instead, or add more outdoor activities on Day 2..."
              rows={3}
              required={choice === "revise"}
              className="w-full bg-[#0a0f1d] border border-[#1e293b] rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end pt-1">
          <button
            type="submit"
            disabled={isSubmitting || (choice === "revise" && !feedback.trim())}
            className="flex items-center justify-center gap-2 py-2.5 px-5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-lg shadow-blue-500/20 transition-all active:scale-95 w-full sm:w-auto"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing Decision...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>{choice === "approve" ? "Confirm & Finalize Plan" : "Send Revision Instructions"}</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
