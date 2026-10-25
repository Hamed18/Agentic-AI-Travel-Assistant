import React, { useState, useEffect, useRef } from "react";
import Sidebar from "./components/Sidebar";
import DestinationCards from "./components/DestinationCards";
import AgentTimeline from "./components/AgentTimeline";
import HumanApprovalCard from "./components/HumanApprovalCard";
import MessageItem from "./components/MessageItem";
import AboutModal from "./components/AboutModal";
import AuthModal from "./components/AuthModal";
import GuestBanner from "./components/GuestBanner";
import AdminIngestionModal from "./components/AdminIngestionModal";
import { checkHealth, streamChat, resumeChat, getMe, createGuestSession, clearStoredAuth, getStoredUser } from "./api";
import {
  Send,
  Compass,
  Sparkles,
  Loader2,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  ChevronDown,
  BookOpen,
  Shield,
  User,
  LogIn,
  LogOut,
  Database,
  Mic,
  MicOff,
  AlertCircle,
} from "lucide-react";
import {
  startVoiceRecognition,
  isSpeechRecognitionSupported,
  stopSpeaking,
  speakText,
} from "./services/voiceService";

// Remove legacy shared storage key to prevent data leakage across users & sessions
try {
  localStorage.removeItem("travel_assistant_threads");
} catch (e) {}

function getStorageKey(u) {
  if (!u) return null;
  const id = u.id || u.user_id || u.tenant_id;
  if (!id) return null;
  return u.is_guest
    ? `travel_assistant_threads_guest_${id}`
    : `travel_assistant_threads_user_${id}`;
}

function createFreshThread() {
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
}

function loadUserThreads(u) {
  const key = getStorageKey(u);
  if (key) {
    try {
      const saved = localStorage.getItem(key);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (e) {}
  }
  return createFreshThread();
}

export default function App() {
  const [user, setUser] = useState(() => getStoredUser());
  const [threads, setThreads] = useState(() => loadUserThreads(getStoredUser()));
  const [activeThreadId, setActiveThreadId] = useState(() => threads[0]?.id || "default_trip");
  
  // Always closed by default on initial landing across all devices (mobile, tablet, desktop)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [inputQuery, setInputQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);
  const [healthStatus, setHealthStatus] = useState(null);
  const [currentIntent, setCurrentIntent] = useState("trip_planning");
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isAdminOpen, setIsAdminOpen] = useState(false);

  // Voice input state
  const [isListening, setIsListening] = useState(false);
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  const [voiceNotice, setVoiceNotice] = useState(null);
  const [activeSpeakingIndex, setActiveSpeakingIndex] = useState(null);
  const recognitionRef = useRef(null);

  const handleVoiceToggle = () => {
    if (isListening || isProcessingVoice) {
      setIsListening(false);
      setIsProcessingVoice(false);
      setIsProcessingVoice(true);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {}
      }
      return;
    }

    if (!isSpeechRecognitionSupported()) {
      setVoiceNotice("Voice input is not supported in this browser. Please use Chrome, Edge, or Safari.");
      setTimeout(() => setVoiceNotice(null), 5000);
      return;
    }

    setVoiceNotice(null);
    setIsListening(true);
    setIsProcessingVoice(false);
    const session = startVoiceRecognition({
      onStart: () => {
        setIsListening(true);
        setIsProcessingVoice(false);
      },
      onProcessing: () => {
        setIsListening(false);
      setIsProcessingVoice(false);
        setIsProcessingVoice(true);
      },
      onTranscript: (transcript) => {
        setInputQuery(transcript);
      },
      onError: (friendlyMsg) => {
        setIsListening(false);
      setIsProcessingVoice(false);
        setIsProcessingVoice(false);
        if (friendlyMsg) {
          setVoiceNotice(friendlyMsg);
          setTimeout(() => setVoiceNotice(null), 5000);
        }
      },
      onEnd: () => {
        setIsListening(false);
      setIsProcessingVoice(false);
        setIsProcessingVoice(false);
      },
    });

    recognitionRef.current = session;
  };

  // Initialize and verify user auth / guest session
  useEffect(() => {
    getMe().then((me) => {
      if (me) {
        setUser(me);
        const loaded = loadUserThreads(me);
        setThreads(loaded);
        setActiveThreadId(loaded[0]?.id || "default_trip");
      } else {
        createGuestSession()
          .then((res) => {
            setUser(res.user);
            const loaded = loadUserThreads(res.user);
            setThreads(loaded);
            setActiveThreadId(loaded[0]?.id || "default_trip");
          })
          .catch((e) => console.warn("Guest session init error:", e));
      }
    });
  }, []);

  const handleLogout = async () => {
    // 1. Purge guest data if active session was a guest
    if (user?.is_guest) {
      const guestKey = getStorageKey(user);
      if (guestKey) {
        try {
          localStorage.removeItem(guestKey);
        } catch (e) {}
      }
    }

    // 2. Clear stored auth credentials
    clearStoredAuth();

    // 3. Reset in-memory threads data state immediately
    const fresh = createFreshThread();
    setThreads(fresh);
    setActiveThreadId(fresh[0].id);

    // 4. Initialize clean isolated guest session
    try {
      const guest = await createGuestSession();
      setUser(guest.user);
      const guestFresh = createFreshThread();
      setThreads(guestFresh);
      setActiveThreadId(guestFresh[0].id);
    } catch (e) {
      setUser(null);
    }
  };

  const handleAuthSuccess = (authenticatedUser) => {
    // 1. Clear previous temporary guest data when transitioning to authenticated session
    if (user?.is_guest) {
      const guestKey = getStorageKey(user);
      if (guestKey) {
        try {
          localStorage.removeItem(guestKey);
        } catch (e) {}
      }
    }

    // 2. Set authenticated user
    setUser(authenticatedUser);

    // 3. Load isolated threads belonging strictly to this user
    const loaded = loadUserThreads(authenticatedUser);
    setThreads(loaded);
    setActiveThreadId(loaded[0]?.id || "default_trip");
  };

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

  // Dedicated container-only scroll to protect fixed header from shifting on mobile
  const scrollToBottom = (behavior = "smooth") => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior,
      });
    }
  };

  // Save threads to isolated user-specific / session-specific storage key
  useEffect(() => {
    const key = getStorageKey(user);
    if (key && threads) {
      try {
        localStorage.setItem(key, JSON.stringify(threads));
      } catch (e) {}
    }
  }, [threads, user]);

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
      if (window.innerWidth < 1024 && isSidebarOpen) {
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
      scrollToBottom("smooth");
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
    stopSpeaking();
    setActiveSpeakingIndex(null);
    if (chatContainerRef.current) {
      if (currentThread?.messages?.length === 0) {
        chatContainerRef.current.scrollTop = 0;
      } else {
        scrollToBottom("instant");
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

    stopSpeaking();
    setActiveSpeakingIndex(null);

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (_) {}
      setIsListening(false);
      setIsProcessingVoice(false);
    }

    setInputQuery("");
    setIsStreaming(true);
    setCurrentIntent("trip_planning");

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
          if (data.intent) {
            setCurrentIntent(data.intent);
          }

          setActiveStages((prev) => {
            const next = { ...prev, [node]: "complete" };
            if (node === "supervisor") {
              if (data.intent && data.intent !== "trip_planning") {
                // Direct response fast path: specialist stages are skipped
              } else {
                next.parallel_specialists = "running";
              }
            } else if (node === "parallel_specialists") {
              next.budget_agent = "running";
            } else if (node === "budget_agent") {
              next.itinerary_agent = "running";
            }
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

        // Handle Final Plan / Chat Completion
        if (event === "complete") {
          setActiveStages({
            supervisor: "complete",
            parallel_specialists: "complete",
            budget_agent: "complete",
            itinerary_agent: "complete",
            human_approval: "complete",
          });

          const final = data.final_response || data.itinerary;
          const isDirectChat = data.response_type === "chat" || (data.intent && data.intent !== "trip_planning");

          updateCurrentThread((t) => ({
            ...t,
            isInterrupted: false,
            messages: [
              ...t.messages,
              {
                role: "assistant",
                type: isDirectChat ? "chat" : "final_plan",
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
    stopSpeaking();
    setActiveSpeakingIndex(null);
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
    <div className="fixed inset-0 w-full h-[100dvh] bg-[#090d16] text-slate-100 flex overflow-hidden font-sans select-none">
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
        onOpenAbout={() => setIsAboutOpen(true)}
        user={user}
        onOpenAuth={() => setIsAuthOpen(true)}
        onOpenAdmin={() => setIsAdminOpen(true)}
        onLogout={handleLogout}
      />

      {/* Main Conversation Canvas */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative min-w-0">
        {/* Top Navbar - Fixed & Never Scrolls Off */}
        <header className="h-14 border-b border-[#1e293b] bg-[#0d1322] flex items-center justify-between px-3 sm:px-6 z-20 flex-shrink-0 w-full">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            {/* Sidebar Toggle Button */}
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 rounded-xl bg-[#131b2e] border border-[#1e293b] hover:bg-[#1a2540] text-slate-300 hover:text-white transition-colors flex-shrink-0"
              title={isSidebarOpen ? "Collapse sidebar" : "Open sidebar"}
              aria-label="Toggle sidebar"
            >
              {isSidebarOpen ? (
                <PanelLeftClose className="w-4 h-4 hidden lg:block" />
              ) : (
                <PanelLeftOpen className="w-4 h-4 hidden lg:block" />
              )}
              <Menu className="w-4 h-4 lg:hidden" />
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
            {/* Admin Knowledge Ingestion Button */}
            {user?.role === "admin" && (
              <button
                onClick={() => setIsAdminOpen(true)}
                className="flex items-center gap-1.5 text-[11px] sm:text-xs text-purple-300 hover:text-white bg-purple-950/40 hover:bg-purple-900/40 px-2.5 sm:px-3 py-1.5 rounded-full border border-purple-500/30 hover:border-purple-500/60 transition-all shadow-sm active:scale-95 cursor-pointer font-semibold"
                title="Open Admin Knowledge & Ingestion Hub"
              >
                <Database className="w-3.5 h-3.5 text-purple-400" />
                <span className="hidden sm:inline">Ingestion Hub</span>
              </button>
            )}

            {/* Auth Profile / Login Button */}
            {user?.is_guest ? (
              <button
                onClick={() => setIsAuthOpen(true)}
                className="flex items-center gap-1.5 text-[11px] sm:text-xs text-blue-300 hover:text-white bg-blue-600/20 hover:bg-blue-600/30 px-3 py-1.5 rounded-full border border-blue-500/40 transition-all shadow-sm active:scale-95 cursor-pointer font-semibold"
              >
                <LogIn className="w-3.5 h-3.5 text-blue-400" />
                <span>Sign In</span>
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsAuthOpen(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#131b2e] border border-slate-700/80 text-xs text-slate-200 hover:border-blue-500/50 transition cursor-pointer"
                  title="Account Details"
                >
                  {user?.role === "admin" ? (
                    <Shield className="w-3.5 h-3.5 text-purple-400" />
                  ) : (
                    <User className="w-3.5 h-3.5 text-blue-400" />
                  )}
                  <span className="max-w-[70px] sm:max-w-[120px] truncate text-[11px] sm:text-xs font-medium">
                    {user?.name || user?.email}
                  </span>
                </button>
                <button
                  onClick={handleLogout}
                  className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-slate-800 transition cursor-pointer"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* User Guide Interactive Button */}
            <button
              onClick={() => setIsAboutOpen(true)}
              className="flex items-center gap-1.5 text-[11px] sm:text-xs text-blue-300 hover:text-white bg-[#131b2e] hover:bg-[#1a2540] px-2.5 sm:px-3 py-1.5 rounded-full border border-blue-500/30 hover:border-blue-500/60 transition-all shadow-sm active:scale-95 cursor-pointer"
              title="Open User Guide & About SagaTraveller"
              aria-label="User Guide"
            >
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${healthStatus?.status === "healthy" ? "bg-emerald-400" : "bg-amber-400"}`} />
              <BookOpen className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
              <span className="font-semibold hidden sm:inline">User Guide</span>
            </button>
          </div>
        </header>

        {/* Guest-Mode Banner (Phase 4) */}
        {user?.is_guest && <GuestBanner onOpenAuth={() => setIsAuthOpen(true)} />}

        {/* Scrollable Chat Area - Full width so scrollbar stays at edge */}
        <div
          ref={chatContainerRef}
          onScroll={checkScrollPosition}
          className="flex-1 overflow-y-auto overscroll-contain w-full relative scroll-smooth min-h-0"
        >
          <div className="max-w-5xl mx-auto px-3 sm:px-6 py-2 sm:py-3 w-full">
            {currentThread?.messages.length === 0 ? (
              <div className="py-1 sm:py-2">
                {/* Hero Banner */}
                <div className="text-center space-y-1 sm:space-y-1.5 mb-2 sm:mb-4">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[11px] font-semibold">
                    <Sparkles className="w-3 h-3" />
                    <span>Intelligent Journey Companion</span>
                  </div>
                  <h1 className="text-lg sm:text-2xl lg:text-3xl font-extrabold text-white tracking-tight">
                    Where would you like to explore next?
                  </h1>
                  <p className="text-[11px] sm:text-xs text-slate-400 max-w-lg mx-auto leading-relaxed px-2">
                    Real-time flight options, hotel recommendations, local weather insights, and customized daily itineraries tailored to your style and budget.
                  </p>
                </div>

                {/* Starter Destination Cards */}
                <DestinationCards onSelectPrompt={(p) => handleSend(p)} />
              </div>
            ) : (
              <div className="space-y-1">
                {currentThread?.messages.map((msg, i) => (
                  <MessageItem
                    key={i}
                    message={msg}
                    isSpeaking={activeSpeakingIndex === i}
                    onToggleSpeech={() => {
                      if (activeSpeakingIndex === i) {
                        stopSpeaking();
                        setActiveSpeakingIndex(null);
                      } else {
                        stopSpeaking();
                        setActiveSpeakingIndex(i);
                        speakText(msg.content, {
                          onEnd: () => setActiveSpeakingIndex(null),
                          onError: () => setActiveSpeakingIndex(null),
                        });
                      }
                    }}
                  />
                ))}
              </div>
            )}

            {/* Real-time Agent Execution Timeline */}
            {isStreaming && (
              <AgentTimeline stages={activeStages} intent={currentIntent} />
            )}

            {/* Human-in-the-Loop Review & Approval Card */}
            {currentThread?.isInterrupted && (
              <HumanApprovalCard
                onDecision={handleApprovalDecision}
                isSubmitting={isSubmittingApproval}
                isRevision={currentThread?.isRevision}
              />
            )}

            <div ref={chatBottomRef} className="h-2" />
          </div>
        </div>

        {/* Floating Scroll-to-Bottom Arrow Button */}
        {showScrollBottom && (
          <button
            onClick={() => scrollToBottom("smooth")}
            className="fixed bottom-16 sm:bottom-20 right-4 sm:right-8 z-30 flex items-center gap-1.5 px-3 py-2 sm:px-3.5 sm:py-2.5 bg-blue-600/95 hover:bg-blue-500 text-white rounded-full shadow-2xl shadow-blue-500/40 border border-blue-400/40 backdrop-blur-md transition-all duration-300 animate-bounce active:scale-90 group cursor-pointer"
            title="Jump to latest"
            aria-label="Scroll to bottom"
          >
            <ChevronDown className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
            <span className="text-[11px] font-semibold hidden sm:inline">Latest</span>
          </button>
        )}

        {/* Fixed Bottom Input Bar - Matches Content Max Width */}
        <div className="py-2 px-3 sm:px-6 border-t border-[#1e293b] bg-[#0d1322] flex-shrink-0 w-full z-20 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
          <div className="max-w-5xl mx-auto w-full">
            {/* Voice feedback banner / fallback notice */}
            {voiceNotice && (
              <div className="flex items-center gap-1.5 px-3 py-1 mb-1.5 bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] rounded-lg">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 text-amber-400" />
                <span className="truncate">{voiceNotice}</span>
              </div>
            )}
            {isProcessingVoice && (
              <div className="flex items-center justify-between gap-2 px-3 py-1.5 mb-1.5 bg-gradient-to-r from-blue-900/40 to-indigo-900/40 border border-blue-500/40 text-blue-200 text-[11px] rounded-xl shadow-md animate-in fade-in">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 flex-shrink-0 text-blue-400 animate-spin" />
                  <span className="font-medium text-white">Converting speech to text... please hold a moment</span>
                </div>
                <span className="text-[10px] bg-blue-500/20 text-blue-300 font-mono px-2 py-0.5 rounded-full border border-blue-500/30 font-semibold">
                  AI Transcribing
                </span>
              </div>
            )}
            {isListening && !isProcessingVoice && !voiceNotice && (
              <div className="flex items-center justify-between gap-2 px-3 py-1.5 mb-1.5 bg-red-500/10 border border-red-500/30 text-red-300 text-[11px] rounded-xl shadow-md animate-pulse">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping flex-shrink-0" />
                  <span className="font-medium">Listening... Speak your travel plans now (click mic when done)</span>
                </div>
                <span className="text-[10px] text-red-400 font-mono font-semibold">Live Mic</span>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="relative flex items-center bg-[#131b2e] border border-[#1e293b] focus-within:border-blue-500 rounded-2xl shadow-xl transition-all"
            >
              <input
                id="trip_query"
                name="trip_query"
                aria-label="Plan a trip, luxury weekend, or vacation"
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                disabled={isStreaming || currentThread?.isInterrupted}
                placeholder={
                  currentThread?.isInterrupted
                    ? "Review draft plan above..."
                    : isProcessingVoice
                    ? "Processing your voice... please hold"
                    : isListening
                    ? "Listening... speak now"
                    : "Plan a trip, luxury weekend, or vacation..."
                }
                className="w-full bg-transparent py-2.5 sm:py-3 pl-3.5 sm:pl-4 pr-20 sm:pr-24 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none disabled:opacity-50"
              />

              <div className="absolute right-1.5 sm:right-2 flex items-center gap-1">
                {/* Voice Input Microphone Button */}
                <button
                  type="button"
                  onClick={handleVoiceToggle}
                  disabled={isStreaming || currentThread?.isInterrupted}
                  className={`p-1.5 sm:p-2 rounded-xl transition-all shadow-md active:scale-95 flex items-center justify-center min-w-[32px] min-h-[32px] sm:min-w-[36px] sm:min-h-[36px] cursor-pointer ${
                    isProcessingVoice
                      ? "bg-blue-600/20 text-blue-300 border border-blue-500/50 animate-pulse hover:bg-blue-600/30"
                      : isListening
                      ? "bg-red-500/20 text-red-400 border border-red-500/50 animate-pulse hover:bg-red-500/30"
                      : "bg-[#1a233b] hover:bg-[#222e4d] text-slate-300 hover:text-white border border-[#1e293b]"
                  }`}
                  title={
                    isProcessingVoice
                      ? "Processing your voice... please hold"
                      : isListening
                      ? "Listening... click to stop and transcribe"
                      : "Speak to SagaTraveller (Voice Input)"
                  }
                  aria-label={
                    isProcessingVoice
                      ? "Processing voice input"
                      : isListening
                      ? "Stop and process speech"
                      : "Start voice input"
                  }
                >
                  {isProcessingVoice ? (
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  ) : isListening ? (
                    <MicOff className="w-4 h-4 text-red-400" />
                  ) : (
                    <Mic className="w-4 h-4 text-slate-300" />
                  )}
                </button>

                {/* Send Query Button */}
                <button
                  type="submit"
                  disabled={!inputQuery.trim() || isStreaming || currentThread?.isInterrupted}
                  className="p-1.5 sm:p-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:hover:bg-blue-600 text-white rounded-xl transition-all shadow-md active:scale-95 flex items-center justify-center min-w-[32px] min-h-[32px] sm:min-w-[36px] sm:min-h-[36px] cursor-pointer"
                >
                  {isStreaming ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </div>
            </form>

            <div className="text-center mt-1 text-[10px] text-slate-500">
              Developed by{" "}
              <a
                href="https://www.linkedin.com/in/devhamed/"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-blue-400 hover:text-blue-300 underline underline-offset-2 transition-colors"
              >
                Hamed Hasan
              </a>
            </div>
          </div>
        </div>
      </main>

      {/* About SagaTraveller Modal */}
      <AboutModal isOpen={isAboutOpen} onClose={() => setIsAboutOpen(false)} />

      {/* Auth Modal (Phase 4) */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />

      {/* Admin Knowledge & Ingestion Modal (Phase 4) */}
      <AdminIngestionModal
        isOpen={isAdminOpen}
        onClose={() => setIsAdminOpen(false)}
        user={user}
      />
    </div>
  );
}
