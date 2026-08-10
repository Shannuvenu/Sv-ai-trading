"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Filter, ArrowUpDown, Search, TrendingUp, TrendingDown } from "lucide-react";
import { api } from "@/lib/api";

interface QuoteRow { symbol: string; name: string; last_price: number; change: number; change_pct: number; volume: number; }

export default function ScreenerPage() {
  const [symbols, setSymbols] = useState<QuoteRow[]>([]);
  const [allSymbols, setAllSymbols] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ minPrice: "", maxPrice: "", minChange: "", signal: "", exchange: "NSE" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const liquid = [
    "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC","LT","BHARTIARTL",
    "AXISBANK","KOTAKBANK","HINDUNILVR","BAJFINANCE","MARUTI","TITAN","SUNPHARMA",
    "ASIANPAINT","HCLTECH","WIPRO","TECHM","NESTLE","ULTRACEMCO","POWERGRID",
    "NTPC","ONGC","COALINDIA","JSWSTEEL","TATASTEEL","ADANIPORTS","ADANIENT",
    "HDFCLIFE","BAJAJFINSV","INDUSINDBK","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP",
    "BRITANNIA","EICHERMOT","HEROMOTOCO","TATAMOTORS","M&M","BAJAJ-AUTO",
  ];

  const fetchQuotes = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const batchSize = 25;
      const batch1 = liquid.slice(0, batchSize);
      const batch2 = liquid.slice(batchSize);
      const r1 = await fetch(`/api/market/batch-quotes?symbols=${batch1.join(",")}&exchange=NSE`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` }
      });
      const d1 = await r1.json();
      const r2 = await fetch(`/api/market/batch-quotes?symbols=${batch2.join(",")}&exchange=NSE`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` }
      });
      const d2 = await r2.json();
      const quotes = { ...(d1.quotes || {}), ...(d2.quotes || {}) };
      const rows: QuoteRow[] = liquid.map(s => ({
        symbol: s, name: "", last_price: 0, change: 0, change_pct: 0, volume: 0, ...(quotes[s] || {}),
      }));
      setSymbols(rows);
      setAllSymbols(liquid);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchQuotes(); }, [fetchQuotes]);

  const filtered = symbols.filter(s => {
    if (search && !s.symbol.toLowerCase().includes(search.toLowerCase())) return false;
    if (filters.minPrice && s.last_price < parseFloat(filters.minPrice)) return false;
    if (filters.maxPrice && s.last_price > parseFloat(filters.maxPrice)) return false;
    if (filters.minChange && Math.abs(s.change_pct) < parseFloat(filters.minChange)) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Stock Screener</h1>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-surface border border-border rounded-full px-3 py-1 text-muted">UPSTOX LIVE</span>
          <button onClick={fetchQuotes} className="text-xs text-primary hover:underline">Refresh</button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative max-w-xs flex-1">
          <Search size={16} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
          <input type="text" placeholder="Filter by symbol..." value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-surface border border-border rounded-lg text-sm" />
        </div>
        <div className="flex gap-2 flex-wrap">
          <input type="number" placeholder="Min ₹" value={filters.minPrice} onChange={e => setFilters({...filters, minPrice: e.target.value})}
            className="w-24 px-2 py-2 bg-surface border border-border rounded-lg text-sm" />
          <input type="number" placeholder="Max ₹" value={filters.maxPrice} onChange={e => setFilters({...filters, maxPrice: e.target.value})}
            className="w-24 px-2 py-2 bg-surface border border-border rounded-lg text-sm" />
          <input type="number" placeholder="Min Δ%" value={filters.minChange} onChange={e => setFilters({...filters, minChange: e.target.value})}
            className="w-24 px-2 py-2 bg-surface border border-border rounded-lg text-sm" />
        </div>
      </div>

      {error && <div className="bg-surface border border-danger/30 rounded-xl p-3"><p className="text-danger text-sm">{error}</p></div>}
      {loading && <div className="flex justify-center py-8"><div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" /></div>}

      {!loading && filtered.length > 0 && (
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted">
                <th className="p-3">Symbol</th><th className="p-3 text-right">LTP</th><th className="p-3 text-right">Change</th><th className="p-3 text-right">Chg%</th><th className="p-3 text-right">Volume</th><th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <tr key={i} className="border-b border-border hover:bg-surface-hover">
                  <td className="p-3">
                    <Link href={`/markets/${s.symbol}`} className="text-primary font-medium text-sm">{s.symbol}</Link>
                    {s.name && <p className="text-xs text-muted">{s.name}</p>}
                  </td>
                  <td className="p-3 text-right tabular-nums font-medium">{s.last_price > 0 ? `₹${s.last_price.toFixed(2)}` : "—"}</td>
                  <td className={`p-3 text-right tabular-nums text-sm ${(s.change||0) >= 0 ? "text-success" : "text-danger"}`}>{s.last_price > 0 ? `${(s.change||0)>=0?"+":""}${s.change?.toFixed(2)}` : "—"}</td>
                  <td className={`p-3 text-right tabular-nums text-sm ${(s.change_pct||0) >= 0 ? "text-success" : "text-danger"}`}>{s.last_price > 0 ? `${(s.change_pct||0)>=0?"+":""}${s.change_pct?.toFixed(2)}%` : "—"}</td>
                  <td className="p-3 text-right tabular-nums text-xs text-muted">{s.volume > 0 ? s.volume.toLocaleString("en-IN") : "—"}</td>
                  <td className="p-3"><Link href={`/markets/${s.symbol}`} className="text-primary text-xs hover:underline">View</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="text-center py-12 bg-surface border border-border rounded-xl">
          <p className="text-muted text-sm">No stocks match your filters.</p>
        </div>
      )}
    </div>
  );
}
