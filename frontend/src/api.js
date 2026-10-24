/**
 * api.js - Production API Client for FastAPI Backend
 * Handles Server-Sent Events (SSE) streaming, thread management, PDF generation,
 * JWT authentication, and Multi-Tenant document ingestion.
 */

const rawBaseUrl = import.meta.env.VITE_API_URL || "http://localhost:8001";
export const API_BASE_URL = rawBaseUrl.replace(/\/+$/, "");

/**
 * Token management helpers
 */
export function getStoredToken() {
  return localStorage.getItem("travel_assistant_token") || "";
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem("travel_assistant_token", token);
  } else {
    localStorage.removeItem("travel_assistant_token");
  }
}

export function getStoredUser() {
  const u = localStorage.getItem("travel_assistant_user");
  if (!u) return null;
  try {
    return JSON.parse(u);
  } catch (e) {
    return null;
  }
}

export function setStoredUser(user) {
  if (user) {
    localStorage.setItem("travel_assistant_user", JSON.stringify(user));
  } else {
    localStorage.removeItem("travel_assistant_user");
  }
}

export function clearStoredAuth() {
  localStorage.removeItem("travel_assistant_token");
  localStorage.removeItem("travel_assistant_user");
}

function getAuthHeaders(extra = {}) {
  const token = getStoredToken();
  const headers = { ...extra };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

// ── Auth Endpoints (Phase 1 & Phase 4) ───────────────────────────────────────
export async function registerUser({ email, password, name = "", role = "user" }) {
  const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name, role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Registration failed" }));
    throw new Error(err.detail || "Registration failed");
  }
  const data = await res.json();
  setStoredToken(data.access_token);
  setStoredUser(data.user);
  return data;
}

export async function loginUser({ email, password }) {
  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(err.detail || "Invalid credentials");
  }
  const data = await res.json();
  setStoredToken(data.access_token);
  setStoredUser(data.user);
  return data;
}

export async function createGuestSession() {
  const res = await fetch(`${API_BASE_URL}/api/auth/guest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    throw new Error("Failed to initialize guest session");
  }
  const data = await res.json();
  setStoredToken(data.access_token);
  setStoredUser(data.user);
  return data;
}

export async function getMe() {
  const token = getStoredToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      if (res.status === 401) {
        clearStoredAuth();
        return null;
      }
      throw new Error(`HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    console.warn("Failed fetching /api/auth/me:", e);
    return null;
  }
}

// ── Multi-Tenant Ingestion (Phase 2 & Phase 4) ───────────────────────────────
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Failed to upload document");
  }
  return await res.json();
}

export async function ingestText({ title, content, metadata = {} }) {
  const res = await fetch(`${API_BASE_URL}/api/documents/ingest-text`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ title, content, metadata }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Ingestion failed" }));
    throw new Error(err.detail || "Failed to ingest text");
  }
  return await res.json();
}

export async function listDocuments() {
  const res = await fetch(`${API_BASE_URL}/api/documents`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error("Failed to list tenant documents");
  }
  return await res.json();
}

export async function deleteDocument(filename) {
  const res = await fetch(`${API_BASE_URL}/api/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error("Failed to delete document");
  }
  return await res.json();
}

// ── Episodic Memory (Phase 3) ────────────────────────────────────────────────
export async function getMemoryHistory(limit = 10) {
  const res = await fetch(`${API_BASE_URL}/api/memory/history?limit=${limit}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error("Failed to fetch memory history");
  }
  return await res.json();
}

// ── User Profile & Consolidation (Phase 6) ──────────────────────────────────
export async function getProfile() {
  const res = await fetch(`${API_BASE_URL}/api/profile`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch user profile");
  return await res.json();
}

export async function consolidateProfile() {
  const res = await fetch(`${API_BASE_URL}/api/profile/consolidate`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to trigger profile consolidation");
  return await res.json();
}

// ── TTL Reaper (Phase 5) ────────────────────────────────────────────────────
export async function runReaper(maxAgeHours = 2.0) {
  const res = await fetch(`${API_BASE_URL}/api/admin/reaper/run?max_age_hours=${maxAgeHours}`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to execute TTL reaper");
  return await res.json();
}

export async function getReaperStatus() {
  const res = await fetch(`${API_BASE_URL}/api/admin/reaper/status`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch TTL reaper status");
  return await res.json();
}

/**
 * Checks backend health and database connectivity
 */
export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`, {
      headers: getAuthHeaders(),
    });
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
      headers: getAuthHeaders({
        "Content-Type": "application/json",
      }),
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
      headers: getAuthHeaders({
        "Content-Type": "application/json",
      }),
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
    headers: getAuthHeaders({
      "Content-Type": "application/json",
    }),
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
