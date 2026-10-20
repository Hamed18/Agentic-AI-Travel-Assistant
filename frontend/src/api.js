/**
 * api.js - Production API Client for FastAPI Backend
 * Handles Server-Sent Events (SSE) streaming, thread management, and PDF generation.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Checks backend health and database connectivity
 */
export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend health check failed:", err);
    return { status: "disconnected", error: err.message };
  }
}

/**
 * Streams real-time agent updates from POST /api/chat/stream using Fetch ReadableStream
 */
export async function streamChat({ query, threadId, userId = "demo_user", onEvent, onError, onComplete }) {
  const url = `${API_BASE_URL}/api/chat/stream`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        thread_id: threadId,
        user_id: userId,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`API error (${response.status}): ${errText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // keep incomplete line in buffer

      let currentEvent = null;

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith("event:")) {
          currentEvent = trimmed.replace("event:", "").trim();
        } else if (trimmed.startsWith("data:")) {
          const rawData = trimmed.replace("data:", "").trim();
          try {
            const parsed = JSON.parse(rawData);
            onEvent({ event: currentEvent || "message", data: parsed });
          } catch (e) {
            onEvent({ event: currentEvent || "message", data: rawData });
          }
        }
      }
    }

    if (onComplete) onComplete();
  } catch (err) {
    console.error("Stream error:", err);
    if (onError) onError(err);
  }
}

/**
 * Resumes paused Human-in-the-Loop graph from POST /api/chat/resume
 */
export async function resumeChat({ threadId, approved, feedback = "", onEvent, onError, onComplete }) {
  const url = `${API_BASE_URL}/api/chat/resume`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        thread_id: threadId,
        approved,
        feedback,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`API error (${response.status}): ${errText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = null;

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith("event:")) {
          currentEvent = trimmed.replace("event:", "").trim();
        } else if (trimmed.startsWith("data:")) {
          const rawData = trimmed.replace("data:", "").trim();
          try {
            const parsed = JSON.parse(rawData);
            onEvent({ event: currentEvent || "message", data: parsed });
          } catch (e) {
            onEvent({ event: currentEvent || "message", data: rawData });
          }
        }
      }
    }

    if (onComplete) onComplete();
  } catch (err) {
    console.error("Resume stream error:", err);
    if (onError) onError(err);
  }
}

/**
 * Downloads publication-grade PDF from POST /api/pdf
 */
export async function downloadPdf({ itineraryMarkdown, filename = "Travel_Plan.pdf" }) {
  const url = `${API_BASE_URL}/api/pdf`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      itinerary_markdown: itineraryMarkdown,
      filename,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to generate PDF (${response.status})`);
  }

  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(blobUrl);
}
