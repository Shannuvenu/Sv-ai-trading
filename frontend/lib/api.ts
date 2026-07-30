const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers });

  if (res.status === 204) return undefined as T;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  register: (data: { email: string; username: string; password: string }) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify(data) }),

  login: (data: { username: string; password: string }) =>
    request<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  refresh: (refresh_token: string) =>
    request<{ access_token: string; refresh_token: string }>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),

  getMe: () => request<User>("/users/me"),

  getInstruments: () => request<Instrument[]>("/market/instruments"),
  searchInstruments: (q: string) => request<Instrument[]>(`/market/instruments/search?q=${encodeURIComponent(q)}`),
  getInstrument: (symbol: string) => request<Instrument>(`/market/instruments/${symbol}`),
  getQuote: (symbol: string) => request<Quote>(`/market/quote/${symbol}`),
  getHistory: (symbol: string) => request<{ symbol: string; data: OHLCVPoint[] }>(`/market/history/${symbol}`),

  createWatchlist: (name: string) =>
    request<Watchlist>("/watchlists", { method: "POST", body: JSON.stringify({ name }) }),
  listWatchlists: () => request<Watchlist[]>("/watchlists"),
  getWatchlist: (id: number) => request<Watchlist>(`/watchlists/${id}`),
  updateWatchlist: (id: number, name: string) =>
    request<Watchlist>(`/watchlists/${id}`, { method: "PATCH", body: JSON.stringify({ name }) }),
  deleteWatchlist: (id: number) =>
    request<void>(`/watchlists/${id}`, { method: "DELETE" }),
  addWatchlistItem: (wlId: number, symbol: string) =>
    request<WatchlistItem>(`/watchlists/${wlId}/items`, { method: "POST", body: JSON.stringify({ symbol }) }),
  removeWatchlistItem: (wlId: number, itemId: number) =>
    request<void>(`/watchlists/${wlId}/items/${itemId}`, { method: "DELETE" }),

  createPortfolio: (name: string, initialCash: number) =>
    request<Portfolio>("/portfolio", { method: "POST", body: JSON.stringify({ name, initial_cash: initialCash }) }),
  listPortfolios: () => request<Portfolio[]>("/portfolio"),
  getPortfolio: (id: number) => request<PortfolioSummary>(`/portfolio/${id}`),
  getTransactions: (id: number) => request<Transaction[]>(`/portfolio/${id}/transactions`),
  buy: (pfId: number, symbol: string, quantity: number, price: number) =>
    request<Transaction>(`/portfolio/${pfId}/buy`, {
      method: "POST",
      body: JSON.stringify({ symbol, quantity, price }),
    }),
  sell: (pfId: number, symbol: string, quantity: number, price: number) =>
    request<Transaction>(`/portfolio/${pfId}/sell`, {
      method: "POST",
      body: JSON.stringify({ symbol, quantity, price }),
    }),
  deletePortfolio: (id: number) =>
    request<void>(`/portfolio/${id}`, { method: "DELETE" }),

  analyze: (symbol: string, days = 100) =>
    request<Analysis>(`/analysis/${symbol}?days=${days}`),

  runBacktest: (params: {
    symbol: string;
    initial_capital?: number;
    position_size_pct?: number;
    commission?: number;
    slippage?: number;
  }, days = 252) =>
    request<BacktestResult>(`/backtest?days=${days}`, {
      method: "POST",
      body: JSON.stringify(params),
    }),

  getRisk: (pfId: number) => request<RiskAnalysis>(`/risk/portfolio/${pfId}`),

  createAlert: (data: { symbol: string; alert_type: string; threshold_value?: number | null }) =>
    request<Alert>("/alerts", { method: "POST", body: JSON.stringify(data) }),
  listAlerts: () => request<Alert[]>("/alerts"),
  deleteAlert: (id: number) => request<void>(`/alerts/${id}`, { method: "DELETE" }),
};

import type {
  User, Instrument, Quote, OHLCVPoint, Watchlist, WatchlistItem,
  Portfolio, Transaction, PortfolioSummary,
  Analysis, BacktestResult, Alert, RiskAnalysis,
} from "@/types";

