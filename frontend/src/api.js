const BASE = "";

let token = localStorage.getItem("access_token");

export function setToken(newToken) {
  token = newToken;
  if (token) localStorage.setItem("access_token", token);
  else localStorage.removeItem("access_token");
}

export function getToken() {
  return token;
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { ...headers, ...(options.headers || {}) },
  });
  if (res.status === 401) {
    setToken(null);
    window.location.reload();
    return; // reload is already in flight; don't also fall through to the throw below
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch { /* non-JSON error body */ }
    throw new Error(detail);
  }
  return res.json();
}

export const getHealth = () => request("/api/health");
export const getRoles = () => request("/api/roles");
export const advise = (payload) =>
  request("/api/advise", { method: "POST", body: JSON.stringify(payload) });

export const login = (email, password) => {
  const params = new URLSearchParams();
  params.append("username", email);
  params.append("password", password);
  return request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: params
  });
};

export const register = (email, password) =>
  request("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password }) });

export const getJourneys = () => request("/api/tracker/journeys");

export const recordProgress = (stepId, update) =>
  request(`/api/tracker/step/${stepId}/progress`, {
    method: "POST", body: JSON.stringify(update),
  });

export const getStepQuiz = (stepId) =>
  request(`/api/tracker/step/${stepId}/quiz`, { method: "POST" });

export const submitStepQuiz = (stepId, answers) =>
  request(`/api/tracker/step/${stepId}/quiz/submit`, {
    method: "POST", body: JSON.stringify({ answers }),
  });

export const syncGithub = (username) =>
  request("/api/github/sync", { method: "POST", body: JSON.stringify({ username }) });

export const recalculateJourney = (journeyId) =>
  request(`/api/tracker/journey/${journeyId}/recalculate`, { method: "POST" });

export const getCompetencyHistory = () =>
  request("/api/tracker/competency-history");

export const extractPdf = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  
  const res = await fetch(`${BASE}/api/extract_pdf`, {
    method: "POST",
    body: formData,
  });
  
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
};

export const analyzeRepo = (username, repo_name) =>
  request(`/api/github/repo/${encodeURIComponent(username)}/${encodeURIComponent(repo_name)}/analyze`, { method: "POST" });

export const chatRepo = (username, repo_name, query) =>
  request(`/api/github/repo/${encodeURIComponent(username)}/${encodeURIComponent(repo_name)}/chat`, {
    method: "POST", body: JSON.stringify({ query }),
  });
