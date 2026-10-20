import React, { useState, useEffect, useRef } from "react";
import Sidebar from "./components/Sidebar";
import DestinationCards from "./components/DestinationCards";
import AgentTimeline from "./components/AgentTimeline";
import HumanApprovalCard from "./components/HumanApprovalCard";
import MessageItem from "./components/MessageItem";
import { checkHealth, streamChat, resumeChat } from "./api";
import { Send, Compass, Sparkles, Loader2, Menu, PanelLeftClose, PanelLeftOpen, ChevronDown } from "lucide-react";

export default function App() {
  const [threads, setThreads] = useState(() => {
    const saved = localStorage.getItem("travel_assistant_threads");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {}
    }
    const initialId = "trip_" + Math.random().toString(36).substring(2, 9);
    return [
      {
        id: initialId,
        title: "New Trip",
        messages: [],
        isInterrupted: false,
        isRevision: false,
      },
    ];
  });

  const [activeThreadId, setActiveThreadId] = useState(() => threads[0]?.id || "default_trip");
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth >= 768;
    }
    return true;
  });

  const [inputQuery, setInputQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);
  const [healthStatus, setHealthStatus] = useState(null);

  // Active stage states for timeline
  const [activeStages, setActiveStages] = useState({
    supervisor: "pending",
    parallel_specialists: "pending",
    budget_agent: "pending",
    itinerary_agent: "pending",
    human_approval: "pending",
  });

  const chatBottomRef = useRef(null);
  const chatContainerRef = useRef(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  // Check whether user is scrolled up from bottom
  const checkScrollPosition = () => {
    const el = chatContainerRef.current;
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    const notAtBottom = scrollHeight - scrollTop - clientHeight > 60;
    setShowScrollBottom(notAtBottom);
  };

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Save threads to localStorage
  useEffect(() => {
    localStorage.setItem("travel_assistant_threads", JSON.stringify(threads));
  }, [threads]);

  // Check backend health periodically
  useEffect(() => {
    checkHealth().then(setHealthStatus);
    const interval = setInterval(() => {
      checkHealth().then(setHealthStatus);
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // Responsive resize handler for sidebar state
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768 && isSidebarOpen) {
        setIsSidebarOpen(false);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [isSidebarOpen]);

  // Current active thread
  const currentThread = threads.find((t) => t.id === activeThreadId) || threads[0];

  // Viewport scroll behavior: on new messages auto-scroll down, on new chat keep at top
  useEffect(() => {
    if (currentThread?.messages?.length > 0 || isStreaming) {
      chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    } else {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTop = 0;
      }
    }
    const timer = setTimeout(checkScrollPosition, 100);
    return () => clearTimeout(timer);
  }, [currentThread?.id, currentThread?.messages?.length, isStreaming, currentThread?.isInterrupted]);

  // When switching thread, scroll to top if empty or bottom if has messages
  useEffect(() => {
    if (chatContainerRef.current) {
      if (currentThread?.messages?.length === 0) {
        chatContainerRef.current.scrollTop = 0;
      } else {
        chatBottomRef.current?.scrollIntoView({ behavior: "instant" });
      }
      setTimeout(checkScrollPosition, 80);
    }
  }, [activeThreadId]);

  // Create New Trip
  const handleNewTrip = () => {
    const newId = "trip_" + Math.random().toString(36).substring(2, 9);
    const newThread = {
      id: newId,
      title: "New Trip",
      messages: [],
      isInterrupted: false,
      isRevision: false,
    };
    setThreads((prev) => [newThread, ...prev]);
    setActiveThreadId(newId);
    setActiveStages({
      supervisor: "pending",
      parallel_specialists: "pending",
      budget_agent: "pending",
      itinerary_agent: "pending",
      human_approval: "pending",
    });

    // Ensure the top of the viewport appears when user starts a new chat
    setTimeout(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTop = 0;
      }
      checkScrollPosition();
    }, 50);
  };

  // Delete Thread
  const handleDeleteThread = (id) => {
    const remaining = threads.filter((t) => t.id !== id);
    if (remaining.length === 0) {
      handleNewTrip();
    } else {
      setThreads(remaining);
      if (activeThreadId === id) {
        setActiveThreadId(remaining[0].id);
      }
    }
  };

  // Helper to update current thread in state
  const updateCurrentThread = (updater) => {
    setThreads((prev) =>
      prev.map((t) => (t.id === activeThreadId ? updater(t) : t))
    );
  };

  // Send Trip Query (Initiates SSE Stream)
  const handleSend = async (queryToSend = inputQuery) => {
    const query = (queryToSend || "").trim();
    if (!query || isStreaming) return;

    setInputQuery("");
    setIsStreaming(true);

    // Reset timeline stages to running
    setActiveStages({
      supervisor: "running",
      parallel_specialists: "pending",
      budget_agent: "pending",
      itinerary_agent: "pending",
      human_approval: "pending",
    });

    // Append user message & update title if first message
    updateCurrentThread((t) => {
      const isFirst = t.messages.length === 0;
      const title = isFirst ? query.substring(0, 32) + (query.length > 32 ? "..." : "") : t.title;
      return {
        ...t,
        title,
        isInterrupted: false,
        messages: [...t.messages, { role: "user", content: query }],
      };
    });

    let draftItinerary = "";

    await streamChat({
      query,
      threadId: activeThreadId,
      onEvent: ({ event, data }) => {
        // Handle LangGraph stage completions
        if (event === "node_complete" && data?.node) {
          const node = data.node;
          setActiveStages((prev) => {
            const next = { ...prev, [node]: "complete" };
            if (node === "supervisor") next.parallel_specialists = "running";
            else if (node === "parallel_specialists") next.budget_agent = "running";
            else if (node === "budget_agent") next.itinerary_agent = "running";
            return next;
          });

          if (data.itinerary) {
            draftItinerary = data.itinerary;
          }
        }

        // Handle Human-in-the-Loop Interrupt
        if (event === "interrupt") {
          const draft = data.draft_itinerary || draftItinerary;
          setActiveStages((prev) => ({
            ...prev,
            itinerary_agent: "complete",
            human_approval: "running",
          }));

          updateCurrentThread((t) => ({
            ...t,
            isInterrupted: true,
            isRevision: Boolean(data.is_revision),
            messages: [
              ...t.messages,
              {
                role: "assistant",
                type: "draft_plan",
                content: draft,
              },
            ],
          }));
          setIsStreaming(false);
        }

        // Handle Final Plan Completion
        if (event === "complete") {
          setActiveStages({
            supervisor: "complete",
            parallel_specialists: "complete",
            budget_agent: "complete",
            itinerary_agent: "complete",
            human_approval: "complete",
          });

          const final = data.final_response || data.itinerary;
          updateCurrentThread((t) => ({
            ...t,
            isInterrupted: false,
            messages: [
              ...t.messages,
              {
                role: "assistant",
                type: "final_plan",
                content: final,
              },
            ],
          }));
          setIsStreaming(false);
        }
      },
      onError: (err) => {
        console.error("Stream failed:", err);
        setIsStreaming(false);
      },
      onComplete: () => {
        setIsStreaming(false);
      },
    });
  };

  // Submit Human Approval Decision (Calls /api/chat/resume)
  const handleApprovalDecision = async ({ approved, feedback }) => {
    setIsSubmittingApproval(true);

    if (!approved) {
      updateCurrentThread((t) => ({
        ...t,
        messages: [
          ...t.messages,
          {
            role: "user",
            content: `📝 **Revision Requested:** ${feedback}`,
          },
        ],
      }));
    }

    let finalResponse = "";

    await resumeChat({
      threadId: activeThreadId,
      approved,
      feedback,
      onEvent: ({ event, data }) => {
        if (event === "node_complete" && data?.node) {
          const node = data.node;
          setActiveStages((prev) => ({ ...prev, [node]: "complete" }));
        }

        if (event === "interrupt") {
          updateCurrentThread((t) => ({
            ...t,
            isInterrupted: true,
            isRevision: true,
            messages: [
              ...t.messages,
              {
                role: "assistant",
                type: "draft_plan",
                content: data.draft_itinerary,
              },
            ],
          }));
        }

        if (event === "complete") {
          finalResponse = data.final_response || data.itinerary;
          updateCurrentThread((t) => ({
            ...t,
            isInterrupted: false,
            messages: [
              ...t.messages,
              {
                role: "assistant",
                type: "final_plan",
                content: finalResponse,
              },
            ],
          }));
        }
      },
      onError: (err) => {
        console.error("Resume error:", err);
        alert(`Failed to update plan: ${err.message}`);
      },
      onComplete: () => {
        setIsSubmittingApproval(false);
      },
    });
  };

  return (
    <div className="flex h-screen bg-[#090d16] text-slate-100 overflow-hidden font-sans">
      {/* Sidebar Drawer */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={setActiveThreadId}
        onNewTrip={handleNewTrip}
        onDeleteThread={handleDeleteThread}
        healthStatus={healthStatus}
      />

      {/* Main Conversation Canvas */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative min-w-0">
        {/* Top Navbar */}
        <header className="h-14 border-b border-[#1e293b] bg-[#0d1322]/90 backdrop-blur-md flex items-center justify-between px-3 sm:px-6 z-10 flex-shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            {/* Sidebar Toggle Button */}
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 rounded-xl bg-[#131b2e] border border-[#1e293b] hover:bg-[#1a2540] text-slate-300 hover:text-white transition-colors flex-shrink-0"
              title={isSidebarOpen ? "Collapse sidebar" : "Open sidebar"}
              aria-label="Toggle sidebar"
            >
              {isSidebarOpen ? (
                <PanelLeftClose className="w-4 h-4 hidden md:block" />
              ) : (
                <PanelLeftOpen className="w-4 h-4 hidden md:block" />
              )}
              <Menu className="w-4 h-4 md:hidden" />
            </button>

            {/* SagaTraveller Logo Format */}
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-400 flex items-center justify-center shadow-md shadow-blue-500/20 text-white flex-shrink-0">
                <Compass className="w-4 h-4 text-white" />
              </div>
              <span className="font-extrabold text-sm sm:text-base tracking-tight text-white flex-shrink-0">
                Saga<span className="text-blue-400">Traveller</span>
              </span>
              <span className="text-slate-600 hidden sm:inline flex-shrink-0">/</span>
              <h2 className="font-medium text-xs text-slate-400 truncate max-w-[120px] sm:max-w-xs md:max-w-md hidden sm:block">
                {currentThread?.title || "New Journey"}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
            <div className="flex items-center gap-1.5 text-[10px] sm:text-[11px] text-slate-400 bg-[#131b2e] px-2.5 py-1 rounded-full border border-[#1e293b]">
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${healthStatus?.status === "healthy" ? "bg-emerald-400" : "bg-amber-400"}`} />
              <span className="hidden sm:inline">{healthStatus?.status === "healthy" ? "Concierge Online" : "Connecting..."}</span>
              <span className="sm:hidden">{healthStatus?.status === "healthy" ? "Online" : "..."}</span>
            </div>
          </div>
        </header>

        {/* Scrollable Chat Area */}
        <div
          ref={chatContainerRef}
          onScroll={checkScrollPosition}
          className="flex-1 overflow-y-auto px-3 sm:px-6 py-4 max-w-5xl mx-auto w-full relative scroll-smooth"
        >
          {currentThread?.messages.length === 0 ? (
            <div className="py-4 sm:py-8">
              {/* Hero Banner */}
              <div className="text-center space-y-2 mb-6 sm:mb-8">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Intelligent Journey Companion</span>
                </div>
                <h1 className="text-2xl sm:text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                  Where would you like to explore next?
                </h1>
                <p className="text-xs sm:text-sm text-slate-400 max-w-lg mx-auto leading-relaxed px-2">
                  Real-time flight options, hotel recommendations, local weather insights, and customized daily itineraries tailored to your style and budget.
                </p>
              </div>

              {/* Starter Destination Cards */}
              <DestinationCards onSelectPrompt={(p) => handleSend(p)} />
            </div>
          ) : (
            <div className="space-y-1">
              {currentThread?.messages.map((msg, i) => (
                <MessageItem key={i} message={msg} />
              ))}
            </div>
          )}

          {/* Real-time Agent Execution Timeline */}
          {isStreaming && (
            <AgentTimeline stages={activeStages} />
          )}

          {/* Human-in-the-Loop Review & Approval Card */}
          {currentThread?.isInterrupted && (
            <HumanApprovalCard
              onDecision={handleApprovalDecision}
              isSubmitting={isSubmittingApproval}
              isRevision={currentThread?.isRevision}
            />
          )}

          <div ref={chatBottomRef} className="h-4" />
        </div>

        {/* Floating Scroll-to-Bottom Arrow Button */}
        {showScrollBottom && (
          <button
            onClick={scrollToBottom}
            className="fixed bottom-20 sm:bottom-24 right-5 sm:right-8 z-30 flex items-center gap-1.5 px-3 py-2 sm:px-3.5 sm:py-2.5 bg-blue-600/95 hover:bg-blue-500 text-white rounded-full shadow-2xl shadow-blue-500/40 border border-blue-400/40 backdrop-blur-md transition-all duration-300 animate-bounce active:scale-90 group cursor-pointer"
            title="Jump to latest"
            aria-label="Scroll to bottom"
          >
            <ChevronDown className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
            <span className="text-[11px] font-semibold hidden sm:inline">Latest</span>
          </button>
        )}

        {/* Fixed Bottom Input Bar with Mobile Safe Area */}
        <div className="p-2.5 sm:p-4 border-t border-[#1e293b] bg-[#0d1322]/95 backdrop-blur-md pb-[max(0.75rem,env(safe-area-inset-bottom))] flex-shrink-0">
          <div className="max-w-4xl mx-auto">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="relative flex items-center bg-[#131b2e] border border-[#1e293b] focus-within:border-blue-500 rounded-2xl shadow-xl transition-all"
            >
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                disabled={isStreaming || currentThread?.isInterrupted}
                placeholder={
                  currentThread?.isInterrupted
                    ? "Review the draft plan above to approve or request revisions..."
                    : "Plan a trip, luxury weekend, or vacation..."
                }
                className="w-full bg-transparent py-3 sm:py-3.5 pl-3.5 sm:pl-4 pr-12 sm:pr-14 text-base sm:text-xs text-white placeholder-slate-500 focus:outline-none disabled:opacity-50"
              />

              <button
                type="submit"
                disabled={!inputQuery.trim() || isStreaming || currentThread?.isInterrupted}
                className="absolute right-2 p-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:hover:bg-blue-600 text-white rounded-xl transition-all shadow-md active:scale-95 flex items-center justify-center min-w-[36px] min-h-[36px]"
              >
                {isStreaming ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>

            <div className="text-center mt-1.5 sm:mt-2 text-[10px] text-slate-500 hidden sm:block">
              <span className="font-semibold text-slate-300">Saga<span className="text-blue-400">Traveller</span></span> · Smart AI Travel Concierge · Crafted for seamless journeys
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
