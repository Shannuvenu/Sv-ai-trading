"use client";
import { Suspense, useState, useEffect, useCallback, useRef } from "react";
import { Search, TrendingUp, TrendingDown, Star, ArrowRight, ChevronRight, Filter } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { apiFetch } from "@/lib/apiClient";

interface InstrumentResult {
  trading_symbol: string;
  name: string;
  exchange: string;
  segment: string;
  instrument_key: string;
  instrument_type: string;
  lot_size: number;
  last_price?: number;
  change?: number;
  change_pct?: number;
  volume?: number;
}

export default function MarketsPage() {
  const [activeTab, setActiveTab] = useState<"nse"|"bse"|"indices"|"fo"|"mtf"|"ipo">("nse");
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<InstrumentResult[]>([]);
  const [indices, setIndices] = useState<any[]>([]);
  const [topMovers, setTopMovers] = useState<any[]>([]);
  const [topLosers, setTopLosers] = useState<any[]>([]);
  const [ipos, setIpos] = useState<any>(null);
  const [mtfStocks, setMtfStocks] = useState<any[]>([]);
  const [foResults, setFoResults] = useState<any[]>([]);
  const [foSearch, setFoSearch] = useState("");
  const [foType, setFoType] = useState("ALL");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const searchTimer = useRef<any>(null);

  const doEquitySearch = useCallback(async (q: string) => {
    if (q.length < 2) { setResults([]); return; }
    setLoading(true); setError("");
    try {
      const res = await apiFetch(`/market/search?q=${encodeURIComponent(q)}&exchange=${activeTab.toUpperCase()}`);
      const data = await res.json();
      setResults(data.results || []);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }, [activeTab]);

  const doFoSearch = useCallback(async (q: string) => {
    if (q.length < 1) { setFoResults([]); return; }
    setLoading(true);
    try {
      const res = await apiFetch(`/market/fo/search?underlying=${encodeURIComponent(q)}&instrument_type=${foType}`);
      const data = await res.json();
      setFoResults(data.results || []);
    } catch {}
    setLoading(false);
  }, [foType]);

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (activeTab === "fo") {
      searchTimer.current = setTimeout(() => doFoSearch(foSearch), 300);
    } else {
      searchTimer.current = setTimeout(() => doEquitySearch(search), 300);
    }
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current); };
  }, [search, foSearch, activeTab, foType, doEquitySearch, doFoSearch]);

  useEffect(() => {
    // Load indices
    apiFetch("/market/indices").then(r => r.json()).then(d => { if (Array.isArray(d)) setIndices(d); }).catch(() => {});
    // Load movers
    Promise.all([
      apiFetch("/market/top-movers?category=gainers&limit=10").then(r => r.json()),
      apiFetch("/market/top-movers?category=losers&limit=10").then(r => r.json()),
    ]).then(([g, l]) => { setTopMovers(g.results || []); setTopLosers(l.results || []); }).catch(() => {});
    // Load IPOs
    apiFetch("/market/ipo").then(r => r.json()).then(d => { if (d.ipos) setIpos(d.ipos); }).catch(() => {});
    // Load MTF
    apiFetch("/market/mtf").then(r => r.json()).then(d => { setMtfStocks(d.results || []); }).catch(() => {});
  }, []);

  const presets = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC","LT","BHARTIARTL","KOTAKBANK"];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Markets</h1>
        <span className="text-xs bg-surface border border-border rounded-full px-3 py-1 text-muted">LIVE — UPSTOX</span>
      </div>

      {/* Index strip */}
      {indices.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {indices.map((idx) => (
            <div key={idx.symbol} className="bg-surface border border-border rounded-xl p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-muted">{idx.name}</span>
                {idx.last_price > 0 ? <span className="text-[10px] text-success">LIVE</span> : <span className="text-[10px] text-muted">CLOSED</span>}
              </div>
              <p className="text-lg font-bold tabular-nums">{idx.last_price > 0 ? idx.last_price.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—"}</p>
              {idx.last_price > 0 && <p className={`text-xs tabular-nums ${idx.change >= 0 ? "text-success" : "text-danger"}`}>{idx.change >= 0 ? "+" : ""}{idx.change?.toFixed(2)} ({idx.change >= 0 ? "+" : ""}{idx.change_pct?.toFixed(2)}%)</p>}
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 overflow-x-auto border-b border-border pb-0">
        {[
          { id: "nse", label: "NSE Stocks" },
          { id: "bse", label: "BSE Stocks" },
          { id: "indices", label: "Indices" },
          { id: "fo", label: "Futures & Options" },
          { id: "mtf", label: "MTF" },
          { id: "ipo", label: "IPOs" },
        ].map((t) => (
          <button key={t.id} onClick={() => { setActiveTab(t.id as typeof activeTab); setSearch(""); setResults([]); }}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg whitespace-nowrap ${activeTab === t.id ? "text-primary border-b-2 border-primary bg-primary/5" : "text-muted hover:text-foreground"}`}>{t.label}</button>
        ))}
      </div>

      {/* Search */}
      {(activeTab !== "indices" && activeTab !== "ipo") && (
        <div className="relative max-w-lg">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input type="text" placeholder={activeTab === "fo" ? "Underlying (NIFTY, RELIANCE...) " : `Search ${activeTab === "mtf" ? "MTF stocks" : activeTab.toUpperCase()}...`}
            value={activeTab === "fo" ? foSearch : search}
            onChange={(e) => activeTab === "fo" ? setFoSearch(e.target.value) : setSearch(e.target.value)}
            className="w-full pl-10 pr-3 py-2.5 bg-surface border border-border rounded-lg focus:outline-none focus:border-primary text-sm" />
          {activeTab === "fo" && (
            <div className="flex gap-2 mt-2">
              {["ALL","FUT","CE","PE"].map(t => <button key={t} onClick={() => setFoType(t)}
                className={`px-3 py-1 text-xs rounded ${foType===t?"bg-primary/20 text-primary":"bg-surface border border-border"}`}>{t}</button>)}
            </div>
          )}
        </div>
      )}

      {loading && <div className="flex justify-center py-8"><div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" /></div>}

      {/* Equity results */}
      {(activeTab === "nse" || activeTab === "bse") && (
        <div>
          {results.length === 0 && !loading && (
            <div className="space-y-2">
              <p className="text-xs text-muted mb-2">Quick select:</p>
              <div className="flex flex-wrap gap-2">{presets.map(s => <button key={s} onClick={() => setSearch(s)}
                className="px-3 py-1.5 bg-surface border border-border rounded-lg hover:bg-surface-hover text-sm">{s}</button>)}</div>
              <p className="text-muted text-center py-8 text-sm">Or type above to search {activeTab.toUpperCase()} stocks.</p>
            </div>
          )}
          <div className="space-y-2 mt-3">
            {results.map((r) => (
              <Link key={r.instrument_key} href={`/markets/${r.trading_symbol}`} className="flex items-center justify-between p-3 bg-surface border border-border rounded-xl hover:bg-surface-hover transition-colors">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-primary">{r.trading_symbol}</span>
                    <span className="text-xs text-muted">{r.exchange}</span>
                    {r.lot_size > 1 && <span className="text-xs bg-surface-hover px-1.5 py-0.5 rounded">Lot {r.lot_size}</span>}
                  </div>
                  <p className="text-xs text-muted truncate">{r.name}</p>
                </div>
                <div className="text-right">
                  {r.last_price ? (
                    <>
                      <p className="text-sm font-bold tabular-nums">₹{r.last_price.toFixed(2)}</p>
                      <p className={`text-xs tabular-nums ${(r.change||0)>=0?"text-success":"text-danger"}`}>{(r.change||0)>=0?"+":""}{r.change?.toFixed(2)} ({(r.change_pct||0).toFixed(2)}%)</p>
                    </>
                  ) : <p className="text-xs text-muted">Tap to view</p>}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Indices tab */}
      {activeTab === "indices" && indices.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {indices.map((idx) => (
            <div key={idx.symbol} className="bg-surface border border-border rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold">{idx.name}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${idx.last_price>0?"bg-success/20 text-success":"bg-surface-hover text-muted"}`}>{idx.last_price>0?"LIVE":"CLOSED"}</span>
              </div>
              <p className="text-2xl font-bold tabular-nums">₹{idx.last_price>0?idx.last_price.toLocaleString("en-IN",{maximumFractionDigits:2}):"—"}</p>
              {idx.last_price > 0 && <p className={`text-sm ${idx.change>=0?"text-success":"text-danger"}`}>{idx.change>=0?"+":""}{idx.change?.toFixed(2)} ({idx.change>=0?"+":""}{idx.change_pct?.toFixed(2)}%)</p>}
            </div>
          ))}
        </div>
      )}

      {/* F&O tab */}
      {activeTab === "fo" && foResults.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-muted">{foResults.length} contracts found</p>
          {foResults.slice(0, 30).map((r: any, i: number) => (
            <div key={i} className="flex items-center justify-between p-3 bg-surface border border-border rounded-xl">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{r.trading_symbol}</p>
                <p className="text-xs text-muted">{r.name} · Lot {r.lot_size} · Exp {r.expiry ? new Date(Number(r.expiry)).toLocaleDateString() : "—"}</p>
              </div>
              <div className="text-right text-xs">
                <span className={`px-2 py-0.5 rounded ${r.instrument_type?.includes("CE")?"bg-success/20 text-success":r.instrument_type?.includes("PE")?"bg-danger/20 text-danger":"bg-surface-hover"}`}>{r.instrument_type}</span>
                {r.strike > 0 && <span className="ml-2 font-medium">₹{r.strike}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* MTF tab */}
      {activeTab === "mtf" && (
        <div>
          {mtfStocks.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted text-sm">Loading MTF stocks from Upstox...</p>
              <p className="text-xs text-muted mt-2">MTF = Margin Trading Facility. Data refreshes daily.</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-muted mb-2">{mtfStocks.length} MTF-eligible stocks</p>
              {mtfStocks.map((r: any) => (
                <Link key={r.instrument_key} href={`/markets/${r.trading_symbol}`} className="flex items-center justify-between p-3 bg-surface border border-border rounded-xl hover:bg-surface-hover">
                  <div><span className="font-semibold text-sm text-primary">{r.trading_symbol}</span><p className="text-xs text-muted">{r.name}</p></div>
                  <div className="text-right">{r.last_price ? <p className="text-sm font-bold">₹{r.last_price.toFixed(2)}</p> : <p className="text-xs text-muted">—</p>}</div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {/* IPO tab */}
      {activeTab === "ipo" && ipos && (
        <div className="space-y-6">
          {["open","upcoming","closed","listed"].map(cat => {
            const items = ipos[cat] || [];
            if (items.length === 0) return null;
            return (
              <div key={cat}>
                <h3 className="font-semibold text-sm mb-2 capitalize">{cat} IPOs</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {items.map((ipo: any, i: number) => (
                    <div key={i} className="bg-surface border border-border rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-sm">{ipo.company_name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${cat==="open"?"bg-success/20 text-success":cat==="upcoming"?"bg-primary/20 text-primary":"bg-surface-hover text-muted"}`}>{cat.toUpperCase()}</span>
                      </div>
                      <div className="text-xs text-muted space-y-1">
                        {ipo.price_band_low && <p>Price: ₹{ipo.price_band_low} - ₹{ipo.price_band_high}</p>}
                        {ipo.lot_size && <p>Lot: {ipo.lot_size}</p>}
                        {ipo.min_investment && <p>Min: ₹{ipo.min_investment.toLocaleString("en-IN")}</p>}
                        {ipo.open_date && <p>Opens: {new Date(ipo.open_date).toLocaleDateString("en-IN")}</p>}
                        {ipo.close_date && <p>Closes: {new Date(ipo.close_date).toLocaleDateString("en-IN")}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Side panels: Gainers + Losers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="font-semibold mb-3 flex items-center gap-2"><TrendingUp size={16} className="text-success" />Top Gainers</h2>
          <div className="space-y-2">
            {topMovers.length===0 ? <p className="text-muted text-sm text-center py-4">Loading...</p> :
              topMovers.map((s,i) => (
                <Link key={i} href={`/markets/${s.symbol}`} className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover">
                  <span className="font-medium text-sm">{s.symbol}</span>
                  <div className="text-right"><span className="text-sm font-bold tabular-nums">₹{s.last_price?.toFixed(2)}</span><span className="text-success text-xs ml-2">+{s.change?.toFixed(2)} (+{s.change_pct?.toFixed(2)}%)</span></div>
                </Link>
              ))}
          </div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="font-semibold mb-3 flex items-center gap-2"><TrendingDown size={16} className="text-danger" />Top Losers</h2>
          <div className="space-y-2">
            {topLosers.length===0 ? <p className="text-muted text-sm text-center py-4">Loading...</p> :
              topLosers.map((s,i) => (
                <Link key={i} href={`/markets/${s.symbol}`} className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover">
                  <span className="font-medium text-sm">{s.symbol}</span>
                  <div className="text-right"><span className="text-sm font-bold tabular-nums">₹{s.last_price?.toFixed(2)}</span><span className="text-danger text-xs ml-2">{s.change?.toFixed(2)} ({s.change_pct?.toFixed(2)}%)</span></div>
                </Link>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
