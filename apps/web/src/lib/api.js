const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
if (!API_BASE_URL) {
  throw new Error(
    "VITE_API_BASE_URL is not set. " +
    "For local dev, add it to apps/web/.env. " +
    "For Netlify, set it under Site → Environment variables."
  );
}

const API_KEY = import.meta.env.VITE_API_KEY || "";

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      ...(options.headers || {}),
    },
    ...options,
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

export async function runScreen(settings) {
  return request("/api/screen", {
    method: "POST",
    body: JSON.stringify(settings),
  });
}

export async function explainScreen(settings, candidates) {
  return request("/api/explain", {
    method: "POST",
    body: JSON.stringify({ settings, candidates }),
  });
}
