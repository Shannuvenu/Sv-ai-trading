"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Search } from "lucide-react";
import Link from "next/link";
import type { Instrument, Quote } from "@/types";

export default function MarketsPage() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.getInstruments()
      .then((data) => {
        if (cancelled) return;
        setInstruments(data);
        return Promise.all(data.map((i) => api.getQuote(i.symbol).catch(() => null)));
      })
      .then((qts) => {
        if (cancelled || !qts) return;
        const map: Record<string, Quote> = {};
        qts.forEach((q) => { if (q) map[q.symbol] = q; });
        setQuotes(map);
      })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const filtered = instruments.filter((i) =>
    i.symbol.toLowerCase().includes(search.toLowerCase()) ||
    i.name.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  }

  if (error) {
    return <div className="text-center py-20"><p className="text-danger mb-2">Failed to load markets</p><p className="text-muted text-sm">{error}</p></div>;
  }

  const fmtChg = (v: number | unknown) => `${Number(v) >= 0 ? "+" : ""}${Number(v).toFixed(2)}`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Markets</h1>
        <span className="text-xs bg-surface border border-border rounded-full px-3 py-1 text-muted">MARKET CLOSED · UPSTOX</span>
      </div>
      <div className="relative max-w-md">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input type="text" placeholder="Search by symbol or company..." value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-3 py-2.5 bg-surface border border-border rounded-lg focus:outline-none focus:border-primary" />
      </div>
      {filtered.length === 0 ? (
        <p className="text-muted text-center py-12">No instruments found</p>
      ) : (
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          <div className="grid grid-cols-7 gap-4 px-4 py-3 bg-surface-hover text-sm text-muted font-medium">
            <div>Symbol</div><div className="col-span-2">Company</div><div>Sector</div><div className="text-right">Price</div><div className="text-right">Change</div><div className="text-right">Change %</div>
          </div>
          {filtered.map((inst) => {
            const q = quotes[inst.symbol];
            return (
              <Link key={inst.id} href={`/analysis?symbol=${inst.symbol}`}
                className="grid grid-cols-7 gap-4 px-4 py-3 border-t border-border hover:bg-surface-hover transition-colors text-sm">
                <div className="font-medium text-primary">{inst.symbol}</div>
                <div className="col-span-2 truncate">{inst.name}</div>
                <div className="text-muted">{inst.sector}</div>
                <div className="text-right tabular-nums">₹{q?.last_price != null ? Number(q.last_price).toFixed(2) : "—"}</div>
                <div className={`text-right tabular-nums ${q?.change != null && Number(q.change) >= 0 ? "text-success" : "text-danger"}`}>{q ? fmtChg(q.change) : "—"}</div>
                <div className={`text-right tabular-nums ${q?.change_pct != null && Number(q.change_pct) >= 0 ? "text-success" : "text-danger"}`}>{q ? `${fmtChg(q.change_pct)}%` : "—"}</div>
              </Link>
            );
          })}
        </div>
      )}
      <p className="text-xs text-muted text-center pt-4">Market data shown is simulated for development and testing. Not live exchange data.</p>
    </div>
  );
}
