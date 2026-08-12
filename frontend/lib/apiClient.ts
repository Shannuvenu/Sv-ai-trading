"use client";

export function getApiBase(): string {
  if (typeof window !== "undefined") {
    // Check if running on Vercel production
    const host = window.location.host;
    if (host.includes("vercel.app")) {
      return process.env.NEXT_PUBLIC_API_URL || "https://sv-ai-trading-backend.onrender.com";
    }
    // Local development — proxy through nginx on port 80
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }
  return "http://localhost:8000";
}

export function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const base = getApiBase();
  const fullUrl = url.startsWith("http") ? url : `${base}${url}`;
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(fullUrl, { ...options, headers });
}

export async function apiGet<T = any>(path: string): Promise<T> {
  const r = await apiFetch(path);
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text().catch(() => r.statusText)}`);
  return r.json();
}

export async function apiPost<T = any>(path: string, body: unknown): Promise<T> {
  const r = await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text().catch(() => r.statusText)}`);
  return r.json();
}
