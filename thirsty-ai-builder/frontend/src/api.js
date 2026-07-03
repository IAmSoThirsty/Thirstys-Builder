// Shared client for the ThirstyAi Builder backend. Production defaults
// to same-origin: nginx serves the SPA and proxies /api to the backend.
const BASE = process.env.REACT_APP_BACKEND_URL || "";
const TOKEN_KEY = "thirsty_ai_builder_api_token";

export function getApiToken() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(TOKEN_KEY) || "";
}

export function setApiToken(token) {
  if (typeof window === "undefined") return;
  const clean = (token || "").trim();
  if (clean) {
    window.localStorage.setItem(TOKEN_KEY, clean);
  } else {
    window.localStorage.removeItem(TOKEN_KEY);
  }
  window.dispatchEvent(new Event("thirsty-auth-token-changed"));
}

function authHeaders(extra) {
  const headers = { ...(extra || {}) };
  const token = getApiToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function safeJson(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
  return safeJson(res);
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body || {}),
  });
  return safeJson(res);
}

async function download(path, filename) {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export const api = {
  home: () => get("/api/home"),
  health: () => get("/api/health"),
  ownership: () => get("/api/ownership"),
  about: () => get("/api/about"),
  architecture: () => get("/api/architecture"),
  commander: {
    list: () => get("/api/commander/audits"),
    run: (target) => post("/api/commander/audits/run", { target }),
    downloadPdf: (id) => download(`/api/commander/audits/${id}/pdf`, `${id}.pdf`),
  },
  dove: (message, history) => post("/api/dove/chat", { message, history }),
  holli: (message, history) => post("/api/holli/chat", { message, history }),
  appstore: {
    list: () => get("/api/appstore/tools"),
    installs: () => get("/api/appstore/installs"),
    install: (tool_id) => post("/api/appstore/install", { tool_id }),
  },
  business: {
    list: () => get("/api/business/clients"),
    create: (payload) => post("/api/business/clients", payload),
  },
  socials: {
    list: () => get("/api/socials/posts"),
    queue: (channel, text) => post("/api/socials/posts", { channel, text }),
  },
  marketing: (topic, voice, audience) =>
    post("/api/marketing/copy", { topic, voice, audience }),
  rag: {
    embed: (text, source) => post("/api/rag/embed", { text, source }),
    query: (query, k) => post("/api/rag/query", { query, k }),
  },
};

export const backendUrl = BASE;
