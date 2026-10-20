import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, FileText, CheckCircle2, User, Bot, Loader2, Sparkles } from "lucide-react";
import { downloadPdf } from "../api";

export default function MessageItem({ message }) {
  const isUser = message.role === "user";
  const [downloading, setDownloading] = useState(false);

  // Detect if message contains a complete itinerary eligible for publication PDF
  const hasItinerary =
    !isUser &&
    message.content &&
    (message.content.includes("## 1️⃣ FLIGHT OPTIONS") ||
      message.content.includes("## FLIGHT OPTIONS") ||
      message.content.includes("## OVERALL BUDGET SUMMARY") ||
      message.type === "final_plan" ||
      message.type === "draft_plan");

  const handleDownload = async () => {
    if (downloading) return;
    setDownloading(true);
    try {
      await downloadPdf({
        itineraryMarkdown: message.content,
        filename: "Personalized_Travel_Itinerary.pdf",
      });
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className={`flex gap-3 my-4 ${isUser ? "justify-end" : "justify-start"}`}>
      {/* Bot Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-md shadow-blue-500/20 text-white mt-1">
          <Bot className="w-4 h-4" />
        </div>
      )}

      {/* Message Bubble Container */}
      <div
        className={`max-w-[85%] rounded-2xl p-4 shadow-xl text-xs leading-relaxed ${
          isUser
            ? "bg-[#1e3a8a] text-white rounded-tr-none font-medium"
            : "bg-[#131b2e] border border-[#1e293b] text-slate-200 rounded-tl-none w-full"
        }`}
      >
        {/* Header Indicator for Assistant Plans */}
        {!isUser && message.type === "final_plan" && (
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#1e293b]">
            <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-xs uppercase tracking-wider">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <span>Approved & Polished Travel Plan</span>
            </div>
            <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full font-semibold border border-emerald-500/20">
              Publication Ready
            </span>
          </div>
        )}

        {!isUser && message.type === "draft_plan" && (
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#1e293b]">
            <div className="flex items-center gap-1.5 text-blue-400 font-bold text-xs uppercase tracking-wider">
              <FileText className="w-4 h-4 text-blue-400" />
              <span>Draft Itinerary for Review</span>
            </div>
            <span className="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full font-semibold border border-blue-500/20">
              Needs Approval
            </span>
          </div>
        )}

        {/* Message Content */}
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* PDF Download Action Bar */}
        {hasItinerary && (
          <div className="mt-5 pt-3.5 border-t border-[#1e293b] flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-400 text-[11px]">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Complete tables, schedule &amp; anti-aliased budget donut chart included</span>
            </div>

            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-2 py-2 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white font-semibold rounded-xl text-xs shadow-lg shadow-blue-500/25 transition-all active:scale-95"
            >
              {downloading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Compiling PDF...</span>
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Publication PDF</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-slate-700 flex items-center justify-center flex-shrink-0 text-white mt-1">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
}
