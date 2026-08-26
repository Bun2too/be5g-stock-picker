export function normalizeApiBaseUrl(value) {
  const trimmed = String(value || "").trim();
  if (!trimmed) return "";
  if (/^https?:\/\//i.test(trimmed) || trimmed.startsWith("/")) {
    return trimmed.replace(/\/+$/, "");
  }
  return `https://${trimmed.replace(/\/+$/, "")}`;
}

const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
const API_KEY = import.meta.env.VITE_API_KEY || "";

function getApiBaseUrl() {
  if (!API_BASE_URL) {
    throw new Error(
      "VITE_API_BASE_URL is not set. " +
      "For local dev, add it to apps/web/.env. " +
      "For Netlify, set it under Site → Environment variables."
    );
  }
  return API_BASE_URL;
}

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, options = {}) {
  const { accessToken, ...fetchOptions } = options;
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      ...(fetchOptions.headers || {}),
    },
    ...fetchOptions,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const message = typeof detail === "string" ? detail : detail?.message || "Request failed.";
    throw new ApiError(message, response.status, detail);
  }

  return response.json();
}

export async function getHealth() {
  return request("/healthz");
}

export async function getPlans() {
  return request("/api/plans");
}

export async function searchSymbols({ query = "", market = "", limit = 50 } = {}, accessToken) {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (market) params.set("market", market);
  params.set("limit", String(limit));
  return request(`/api/symbols?${params.toString()}`, { accessToken });
}

export async function getPortfolio(accessToken) {
  return request("/api/portfolio", { accessToken });
}

export async function savePortfolio(symbols, accessToken) {
  return request("/api/portfolio", {
    method: "PUT",
    accessToken,
    body: JSON.stringify({ symbols }),
  });
}

export async function runScreen(settings, accessToken) {
  return request("/api/screen", {
    method: "POST",
    accessToken,
    body: JSON.stringify(settings),
  });
}

export async function explainScreen(settings, candidates, accessToken) {
  return request("/api/explain", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ settings, candidates }),
  });
}
