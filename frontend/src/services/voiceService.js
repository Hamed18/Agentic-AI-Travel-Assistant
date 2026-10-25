/**
 * Voice Service — SagaTraveller Web Speech Engine
 * - Speech-to-Text: browser Web Speech API (window.SpeechRecognition / webkitSpeechRecognition)
 * - Text-to-Speech: browser SpeechSynthesis (window.speechSynthesis)
 * Zero external API keys, 100% free, runs client-side with graceful fallback.
 */

export function isSpeechRecognitionSupported() {
  if (typeof window === "undefined") return false;
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}

export function isSpeechSynthesisSupported() {
  if (typeof window === "undefined") return false;
  return "speechSynthesis" in window;
}

// Global cached voices to handle async voiceschanged loading in Chromium
let cachedVoices = [];
function populateVoices() {
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    const v = window.speechSynthesis.getVoices();
    if (v && v.length > 0) {
      cachedVoices = v;
    }
  }
}

if (typeof window !== "undefined" && "speechSynthesis" in window) {
  populateVoices();
  window.speechSynthesis.onvoiceschanged = populateVoices;
}

// Active utterance reference & chunk queue to prevent Chromium garbage collection & length limits
let _activeUtterance = null;
let keepAliveTimer = null;
let speechQueue = [];
let isQueueRunning = false;

function clearKeepAlive() {
  if (keepAliveTimer) {
    clearInterval(keepAliveTimer);
    keepAliveTimer = null;
  }
}

function startKeepAlive() {
  clearKeepAlive();
  // Workaround for Chromium engine auto-pause after 14 seconds on long text
  keepAliveTimer = setInterval(() => {
    if (typeof window !== "undefined" && window.speechSynthesis?.speaking) {
      if (window.speechSynthesis.paused) {
        try {
          window.speechSynthesis.resume();
        } catch (_) {}
      }
    } else {
      clearKeepAlive();
    }
  }, 5000);
}

/**
 * Splits text into small natural sentences to prevent Chromium speech buffer overflow.
 */
export function chunkText(text, maxChunkLen = 180) {
  if (!text) return [];
  const sentences = text.match(/[^.!?\n]+[.!?\n]+/g) || [text];
  const chunks = [];
  let current = "";

  for (const sentence of sentences) {
    const trimmed = sentence.trim();
    if (!trimmed) continue;
    if ((current + " " + trimmed).length <= maxChunkLen) {
      current = current ? current + " " + trimmed : trimmed;
    } else {
      if (current) chunks.push(current);
      if (trimmed.length > maxChunkLen) {
        const words = trimmed.split(" ");
        let subChunk = "";
        for (const word of words) {
          if ((subChunk + " " + word).length <= maxChunkLen) {
            subChunk = subChunk ? subChunk + " " + word : word;
          } else {
            if (subChunk) chunks.push(subChunk);
            subChunk = word;
          }
        }
        if (subChunk) current = subChunk;
      } else {
        current = trimmed;
      }
    }
  }
  if (current) chunks.push(current);
  return chunks.length > 0 ? chunks : [text];
}

/**
 * Creates and starts a SpeechRecognition session.
 * @param {Object} options
 * @param {Function} options.onTranscript (interimText, isFinal) => void
 * @param {Function} options.onError (friendlyErrorMessage) => void
 * @param {Function} options.onStart () => void
 * @param {Function} options.onProcessing () => void
 * @param {Function} options.onEnd () => void
 * @returns {{ stop: () => void }}
 */
export function startVoiceRecognition({ onTranscript, onError, onStart, onProcessing, onEnd }) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    if (onError) {
      onError("Voice input is not supported in this browser. Please use Chrome, Edge, or Safari.");
    }
    return { stop: () => {} };
  }

  let recognition = null;
  try {
    recognition = new SpeechRecognition();
  } catch (err) {
    if (onError) {
      onError("Could not initialize voice recognition. Please try typing.");
    }
    return { stop: () => {} };
  }

  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "en-US";
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    if (onStart) onStart();
  };

  recognition.onspeechstart = () => {
    if (onStart) onStart();
  };

  recognition.onspeechend = () => {
    // User paused or completed speech; notify UI that speech processing is underway
    if (onProcessing) onProcessing();
  };

  recognition.onaudioend = () => {
    if (onProcessing) onProcessing();
  };

  recognition.onresult = (event) => {
    let interim = "";
    let final = "";
    for (let i = 0; i < event.results.length; i++) {
      const transcriptPiece = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        final += transcriptPiece + " ";
      } else {
        interim += transcriptPiece;
      }
    }
    const combined = (final + interim).trim();
    if (onTranscript && combined) {
      onTranscript(combined);
    }
  };

  recognition.onerror = (event) => {
    let friendlyMessage = "Voice input stopped. Falling back to typing mode.";
    switch (event.error) {
      case "no-speech":
        friendlyMessage = "No speech detected (or too much background noise). Switched to typing mode.";
        break;
      case "audio-capture":
        friendlyMessage = "Microphone not detected. Please verify your mic hardware.";
        break;
      case "not-allowed":
        friendlyMessage = "Microphone access was blocked. Please enable mic permissions in your browser.";
        break;
      case "network":
        friendlyMessage = "Speech network connection issue. Falling back to typing mode.";
        break;
      case "aborted":
        // User manually stopped listening - no error toast needed
        friendlyMessage = "";
        break;
      default:
        friendlyMessage = `Voice recognition error: ${event.error || "unclear speech"}. Switched to typing mode.`;
    }

    if (friendlyMessage && onError) {
      onError(friendlyMessage);
    }
  };

  recognition.onend = () => {
    if (onEnd) onEnd();
  };

  try {
    recognition.start();
  } catch (err) {
    if (onError) {
      onError("Voice recognition failed to start. Falling back to typing mode.");
    }
    if (onEnd) onEnd();
  }

  return {
    stop: () => {
      try {
        recognition.stop();
      } catch (e) {
        try {
          recognition.abort();
        } catch (_) {}
      }
    },
  };
}

/**
 * Strips markdown and special symbols to produce natural spoken narration.
 */
export function cleanMarkdownForSpeech(markdown) {
  if (!markdown) return "";
  let text = markdown;

  // Remove table lines and pipe symbols
  text = text.replace(/\|[^\n]+\|/g, (match) => {
    // Convert table row into comma separated words
    const cells = match.split("|").map((c) => c.trim()).filter(Boolean);
    if (cells.length > 0 && !cells[0].includes("---")) {
      return cells.join(", ") + ". ";
    }
    return "";
  });

  // Remove markdown headings (##, ###)
  text = text.replace(/^#{1,6}\s+/gm, "");
  // Remove bold / italic markers
  text = text.replace(/[*_]{1,3}(.*?)[*_]{1,3}/g, "$1");
  // Remove markdown links [Label](url) -> Label
  text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
  // Remove code blocks and inline backticks
  text = text.replace(/`{1,3}[^`]*`{1,3}/g, "");
  // Remove bullet markers
  text = text.replace(/^\s*[-*•]\s+/gm, "");
  // Remove numbered bullet markers
  text = text.replace(/^\s*\d+\.\s+/gm, "");
  // Remove variation selectors
  text = text.replace(/[\uFE00-\uFE0F]/g, "");
  // Remove emoji, flag indicators, and miscellaneous non-verbal symbols
  text = text.replace(
    /[\u{1F1E6}-\u{1F1FF}\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu,
    ""
  );
  // Collapse whitespace
  text = text.replace(/\s+/g, " ").trim();

  return text;
}

/**
 * Speaks the given text using browser SpeechSynthesis with sentence chunking
 * to prevent Chromium 15-second cut-offs and buffer overflows on long itineraries.
 * @param {string} text Markdown or plain text
 * @param {Object} options
 * @param {Function} options.onStart
 * @param {Function} options.onEnd
 * @param {Function} options.onError
 * @returns {{ cancel: () => void }}
 */
export function speakText(text, { onStart, onEnd, onError } = {}) {
  if (!isSpeechSynthesisSupported()) {
    if (onError) onError("Text-to-speech is not supported in this browser.");
    return { cancel: () => {} };
  }

  const clean = cleanMarkdownForSpeech(text);
  if (!clean) {
    if (onEnd) onEnd();
    return { cancel: () => {} };
  }

  // Cancel any ongoing speech queue
  stopSpeaking();

  const chunks = chunkText(clean, 170);
  if (chunks.length === 0) {
    if (onEnd) onEnd();
    return { cancel: () => {} };
  }

  speechQueue = chunks;
  isQueueRunning = true;
  let chunkIndex = 0;

  // Unstick Chrome speech queue if paused
  if (typeof window !== "undefined" && window.speechSynthesis.paused) {
    try {
      window.speechSynthesis.resume();
    } catch (_) {}
  }

  function playNextChunk() {
    if (!isQueueRunning || chunkIndex >= speechQueue.length) {
      isQueueRunning = false;
      stopSpeaking();
      if (onEnd) onEnd();
      return;
    }

    const chunk = speechQueue[chunkIndex];
    chunkIndex++;

    const utterance = new SpeechSynthesisUtterance(chunk);
    utterance.lang = "en-US";
    utterance.volume = 1.0;
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Pick best natural or local system voice
    const voices = cachedVoices.length > 0 ? cachedVoices : window.speechSynthesis.getVoices();
    if (voices && voices.length > 0) {
      const preferred =
        voices.find((v) => v.lang.startsWith("en") && v.localService) ||
        voices.find((v) => v.lang.startsWith("en") && (v.name.includes("Natural") || v.name.includes("Google") || v.name.includes("David") || v.name.includes("Zira"))) ||
        voices.find((v) => v.lang.startsWith("en"));
      if (preferred) {
        utterance.voice = preferred;
      }
    }

    // Persist window & module references to prevent Chrome V8 garbage collection mid-speech
    _activeUtterance = utterance;
    if (typeof window !== "undefined") {
      window._sagaSpeechUtterance = utterance;
    }

    utterance.onstart = () => {
      startKeepAlive();
      if (typeof window !== "undefined" && window.speechSynthesis.paused) {
        try {
          window.speechSynthesis.resume();
        } catch (_) {}
      }
      if (chunkIndex === 1 && onStart) {
        onStart();
      }
    };

    utterance.onend = () => {
      // Play next sentence chunk
      playNextChunk();
    };

    utterance.onerror = (e) => {
      if (e.error === "canceled" || e.error === "interrupted") {
        return;
      }
      console.warn("SpeechSynthesis chunk warning:", e.error);
      // Advance to next chunk if minor audio glitch
      playNextChunk();
    };

    try {
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.error("speechSynthesis.speak error:", err);
      if (onError) onError("Failed to speak text");
      if (onEnd) onEnd();
    }
  }

  // 50ms micro-delay after cancel() to let Chrome's audio thread clear
  setTimeout(() => {
    if (isQueueRunning) {
      playNextChunk();
    }
  }, 50);

  return {
    cancel: () => {
      stopSpeaking();
      if (onEnd) onEnd();
    },
  };
}

export function stopSpeaking() {
  speechQueue = [];
  isQueueRunning = false;
  clearKeepAlive();
  _activeUtterance = null;
  if (typeof window !== "undefined") {
    window._sagaSpeechUtterance = null;
    if (isSpeechSynthesisSupported()) {
      try {
        window.speechSynthesis.cancel();
      } catch (_) {}
    }
  }
}
