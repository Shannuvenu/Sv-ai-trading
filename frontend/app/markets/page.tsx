"use client";
import { Suspense, useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Search, TrendingUp, TrendingDown, Minus } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Analysis, OHLCVPoint, Quote, Instrument } from "@/types";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, ComposedChart } from "recharts";

const presets = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"];

function StockDetailContent() {
  const searchParams = useSearchParams();
  const initialSymbol = searchParams.get("symbol");
  const didAutoLoadRef = useRef(false);
  const [symbol, setSymbol] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [history, setHistory] = useState<OHLCVPoint[]>([]);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [suggestions, setSuggestions] = useState<Instrument[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "chart" | "technicals">("overview");

  const handleAnalyze = useCallback(async (sym: string) => {
    setLoading(true); setError(""); setSymbol(sym); setSearch(""); setSuggestions([]); setAnalysis(null);
    try {
      const [an, q, hist] = await Promise.all([api.analyze(sym, 100), api.getQuote(sym), api.getHistory(sym)]);
      setAnalysis(an); setQuote(q); setHistory(hist.data.slice(-90));
    } catch (err: unknown) { setError(err instanceof Error ? err.message : "Analysis failed"); }
    setLoading(false);
  }, []);

  useEffect(() => { if (initialSymbol && !didAutoLoadRef.current) { didAutoLoadRef.current = true; handleAnalyze(initialSymbol); } }, [initialSymbol, handleAnalyze]);

  useEffect(() => { if (!search || search.length < 1) return; const timer = setTimeout(() => { api.searchInstruments(search).then(setSuggestions).catch(() => {}); }, 200); return () => clearTimeout(timer); }, [search]);

  const chartData = history.map((h) => ({ time: new Date(h.timestamp).toLocaleDateString("en-IN", { month: "short", day: "numeric" }), close: Number(h.close), volume: Number(h.volume) }));

  const SignalIcon = analysis?.signal.direction === "BUY" ? TrendingUp : analysis?.signal.direction === "SELL" ? TrendingDown : Minus;
  const signalColor = analysis?.signal.direction === "BUY" ? "text-success" : analysis?.signal.direction === "SELL" ? "text-danger" : "text-warning";

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  if (error) return <div className="text-center py-20"><p className="text-danger">{error}</p></div>;

  return (
    <div className="space-y-6">
      {/* Header + Search */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Stock Research</h1>
        <span className="text-xs bg-surface border border-border rounded-full px-3 py-1 text-muted">MARKET CLOSED · UPSTOX</span>
      </div>
      <div className="relative max-w-md">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input type="text" placeholder="Search symbol..." value={search} onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-3 py-2.5 bg-surface border border-border rounded-lg focus:outline-none focus:border-primary" />
        {suggestions.length > 0 && (
          <div className="absolute z-10 w-full mt-1 bg-surface border border-border rounded-lg overflow-hidden shadow-lg">
            {suggestions.map((s) => (<button key={s.id} onClick={() => handleAnalyze(s.symbol)} className="w-full text-left px-3 py-2 hover:bg-surface-hover text-sm"><span className="font-medium">{s.symbol}</span> — {s.name}</button>))}
          </div>
        )}
      </div>

      {!symbol && <div><p className="text-muted text-sm mb-3">Quick select:</p><div className="flex flex-wrap gap-2">{presets.map((s) => (<button key={s} onClick={() => handleAnalyze(s)} className="px-4 py-2 bg-surface border border-border rounded-lg hover:bg-surface-hover text-sm font-medium">{s}</button>))}</div></div>}

      {analysis && quote && (
        <>
          {/* Price header */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="bg-surface border border-border rounded-xl p-4"><p className="text-xs text-muted">{analysis.symbol}</p><p className="text-xl font-bold">{analysis.name}</p><p className="text-xs text-muted">{analysis.exchange}</p></div>
            <div className="bg-surface border border-border rounded-xl p-4"><p className="text-xs text-muted">Last Price</p><p className="text-xl font-bold tabular-nums">₹{Number(quote.last_price).toFixed(2)}</p><p className={`text-sm tabular-nums ${Number(quote.change) >= 0 ? "text-success" : "text-danger"}`}>{Number(quote.change) >= 0 ? "+" : ""}{Number(quote.change).toFixed(2)} ({Number(quote.change_pct).toFixed(2)}%)</p></div>
            <div className="bg-surface border border-border rounded-xl p-4"><p className="text-xs text-muted">Open</p><p className="text-lg font-bold tabular-nums">₹{Number(quote.open).toFixed(2)}</p></div>
            <div className="bg-surface border border-border rounded-xl p-4"><p className="text-xs text-muted">High / Low</p><p className="text-sm tabular-nums"><span className="text-success">₹{Number(quote.high).toFixed(2)}</span> / <span className="text-danger">₹{Number(quote.low).toFixed(2)}</span></p></div>
            <div className="bg-surface border border-border rounded-xl p-4"><p className="text-xs text-muted">Volume</p><p className="text-lg font-bold tabular-nums">{quote.volume.toLocaleString("en-IN")}</p></div>
          </div>

          {/* Tabs */}
          <div className="flex gap-4 border-b border-border">
            {["overview","chart","technicals"].map((t) => (<button key={t} onClick={() => setActiveTab(t as typeof activeTab)} className={`pb-2 text-sm font-medium capitalize ${activeTab===t?"text-primary border-b-2 border-primary":"text-muted hover:text-foreground"}`}>{t}</button>))}
          </div>

          {activeTab === "overview" && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[["Signal",analysis.signal.direction,signalColor],[`Confidence`,(analysis.signal.confidence*100).toFixed(0)+"%",""],["RSI (14)",analysis.indicators.rsi_14!=null?Number(analysis.indicators.rsi_14).toFixed(1):"—",""],["MACD",analysis.indicators.macd_line!=null?Number(analysis.indicators.macd_line).toFixed(2):"—",""]].map(([label,val,color])=>(
                <div key={String(label)} className="bg-surface border border-border rounded-xl p-4"><p className="text-xs text-muted">{label}</p><p className={`text-lg font-bold tabular-nums ${color}`}>{String(val)}</p></div>
              ))}
            </div>
          )}

          {activeTab === "chart" && (
            <div className="bg-surface border border-border rounded-xl p-5">
              <h3 className="font-semibold mb-3">Price History</h3>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={400}>
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
                    <XAxis dataKey="time" tick={{fontSize:11,fill:"#71717a"}} interval="preserveStartEnd" />
                    <YAxis yAxisId="left" tick={{fontSize:11,fill:"#71717a"}} domain={["auto","auto"]} />
                    <Tooltip contentStyle={{background:"#13131a",border:"1px solid #1e1e2e",borderRadius:"8px"}} />
                    <Line yAxisId="left" type="monotone" dataKey="close" stroke="#6366f1" dot={false} strokeWidth={2} name="Close" />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : <p className="text-muted text-center py-12">No data available</p>}
            </div>
          )}

          {activeTab === "technicals" && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {[["SMA 20","sma_20"],["SMA 50","sma_50"],["EMA 20","ema_20"],["ATR 14","atr_14"],["BB Upper","bb_upper"],["BB Middle","bb_middle"],["BB Lower","bb_lower"],["MACD Signal","macd_signal"],["MACD Hist","macd_histogram"],["Vol SMA 20","volume_sma_20"]].map(([label,key])=>{
                const val=(analysis.indicators as Record<string,number|null>)[key];
                return (<div key={key} className="bg-surface border border-border rounded-xl p-3 text-center"><p className="text-xs text-muted">{label}</p><p className="font-semibold tabular-nums">{val!=null?Number(val).toFixed(2):"—"}</p></div>);
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function StockDetailPage() {
  return <Suspense fallback={<div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>}><StockDetailContent /></Suspense>;
}
