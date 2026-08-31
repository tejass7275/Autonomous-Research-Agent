// client.js
// Centralized axios instance + typed helper functions for talking to the
// FastAPI backend. Import these functions from components/hooks instead of
// calling axios directly, so auth headers and error handling stay consistent.

import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach the bearer token (if present) to every outgoing request.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401s (expired/invalid token).
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.dispatchEvent(new CustomEvent("auth:expired"));
    }
    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export async function login(email, password) {
  const { data } = await apiClient.post("/api/auth/login", { email, password });
  localStorage.setItem("access_token", data.access_token);
  return data;
}

export async function register(email, password, fullName) {
  const { data } = await apiClient.post("/api/auth/register", {
    email,
    password,
    full_name: fullName,
  });
  return data;
}

export function logout() {
  localStorage.removeItem("access_token");
}

// ---------------------------------------------------------------------------
// Papers
// ---------------------------------------------------------------------------
export async function listPapers({ page = 1, pageSize = 10, source = null } = {}) {
  const { data } = await apiClient.get("/api/papers", {
    params: { page, page_size: pageSize, source },
  });
  return data;
}

// Fetches papers for a topic from arXiv/Semantic Scholar, indexes them into
// FAISS, and persists their metadata to Postgres — all in one call. This is
// the only supported way to populate the corpus; running the standalone
// rag_engine ingest script directly leaves Postgres out of sync.
export async function ingestPapers(query, maxResults = 10) {
  const { data } = await apiClient.post("/api/papers/ingest", null, {
    params: { query, max_results: maxResults },
  });
  return data;
}

export async function getPaper(paperId) {
  const { data } = await apiClient.get(`/api/papers/${paperId}`);
  return data;
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------
export async function searchPapers(query, { sources = null, topK = 10 } = {}) {
  const { data } = await apiClient.post("/api/search", {
    query,
    sources,
    top_k: topK,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Summary / QA
// ---------------------------------------------------------------------------
export async function summarizePaper(paperId, forceRegenerate = false) {
  const { data } = await apiClient.post("/api/summary", {
    paper_id: paperId,
    force_regenerate: forceRegenerate,
  });
  return data;
}

export async function askQuestion(question, paperId = null) {
  const { data } = await apiClient.post("/api/summary/ask", {
    question,
    paper_id: paperId,
  });
  return data;
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------
export async function getHistory({ limit = 50, queryType = null } = {}) {
  const { data } = await apiClient.get("/api/history", {
    params: { limit, query_type: queryType },
  });
  return data;
}

export async function deleteHistoryEntry(logId) {
  await apiClient.delete(`/api/history/${logId}`);
}

export default apiClient;