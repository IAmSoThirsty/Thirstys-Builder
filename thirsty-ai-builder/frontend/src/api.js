// Shared client for the ThirstyAi Builder backend. Falls back to a no-op
// in dev if the backend is unreachable so the UI can still render.
const BASE = process.env.REACT_APP_BACKEND_URL || "http://localhost:8001";

async function safeJson(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  return safeJson(res);
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return safeJson(res);
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
    pdfUrl: (id) => `${BASE}/api/commander/audits/${id}/pdf`,
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
