"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Activity, TrendingUp, TrendingDown, Layers, SquareCode,
  Maximize, Minimize, Newspaper, ShoppingCart, Play, X, RefreshCw,
  ChevronLeft,
} from "lucide-react";
import { api } from "@/lib/api";

interface CandleData { time: string; open: number; high: number; low: number; close: number; volume: number; }
interface QuoteData { symbol: string; name: string; exchange: string; last_price: number; change: number; change_pct: number; high: number; low: number; volume: number; open: number; }

const INTERVALS = ["1m","3m","5m","15m","30m","1h","4h","1D","1W","1M"];
const QUICK_SYMBOLS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC","LT","BHARTIARTL","AXISBANK","KOTAKBANK"];
const CHART_COLORS = { up: "#22c55e", down: "#ef4444", wick: "#71717a", volume: "#3b82f1", bg: "#0d0d1a", grid: "#1a1a2e" };

const defaultScript = `indicator("EMA Cross")\n\nfast = ema(close, 20)\nslow = ema(close, 50)\n\nplot(fast)\nplot(slow)`;

export default function ChartPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = ((params?.symbol as string) || "").toUpperCase();
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [quote, setQuote] = useState<QuoteData | null>(null);
  const [interval, setInterval_] = useState("1D");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [fullscreen, setFullscreen] = useState(false);
  const [showIndicators, setShowIndicators] = useState(false);
  const [showPine, setShowPine] = useState(false);
  const [showNews, setShowNews] = useState(false);
  const [showTrade, setShowTrade] = useState(false);
  const [pineScript, setPineScript] = useState(defaultScript);
  const [pineResult, setPineResult] = useState<any>(null);
  const [pineRunning, setPineRunning] = useState(false);
  const [pineError, setPineError] = useState("");
  const [indicatorData, setIndicatorData] = useState<any>(null);
  const [newsData, setNewsData] = useState<any>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  const headers = useCallback(() => {
    const t = localStorage.getItem("access_token") || "";
    return { Authorization: `Bearer ${t}` };
  }, []);

  const fetchData = useCallback(async (sym: string, intv: string) => {
    setLoading(true); setError("");
    try {
      const h = headers();
      const [q, c] = await Promise.all([
        fetch(`/api/chart/${sym}/quote`, { headers: h }).then(r => r.ok ? r.json() : null),
        fetch(`/api/chart/${sym}/candles?interval=${intv}&days=365`, { headers: h }).then(r => r.ok ? r.json() : null),
      ]);
      if (q) setQuote(q);
      if (c) setCandles(c.candles || []);
      fetch(`/api/chart/${sym}/indicators?indicators=sma20,ema50,rsi14,macd,volume`, { headers: h })
        .then(r => r.ok ? r.json() : null).then(d => { if (d) setIndicatorData(d.indicators || {}); }).catch(() => {});
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }, [headers]);

  useEffect(() => { if (symbol) fetchData(symbol, interval); }, [symbol, interval, fetchData]);

  // ─── CHART RENDERING ───
  useEffect(() => {
    if (typeof window === "undefined" || !chartRef.current || candles.length === 0) return;
    let chart: any = null;
    let disposed = false;

    const init = async () => {
      const mod = await import("lightweight-charts");
      const createChart = (mod as any).createChart || (mod as any).default?.createChart;
      if (!createChart) return;

      chart = createChart(chartRef.current, {
        layout: { background: { color: CHART_COLORS.bg }, textColor: "#d1d5db" },
        grid: { vertLines: { color: CHART_COLORS.grid }, horzLines: { color: CHART_COLORS.grid } },
        crosshair: { mode: 0 },
        rightPriceScale: { borderColor: "#333" },
        timeScale: { borderColor: "#333", timeVisible: true },
        width: chartRef.current!.clientWidth,
        height: chartRef.current!.clientHeight || 600,
      });

      const main = (chart as any).addCandlestickSeries({
        upColor: CHART_COLORS.up, downColor: CHART_COLORS.down,
        borderUpColor: CHART_COLORS.up, borderDownColor: CHART_COLORS.down,
        wickUpColor: CHART_COLORS.up, wickDownColor: CHART_COLORS.down,
      });
      main.setData(candles.map(c => ({ time: (new Date(c.time)).getTime() / 1000, open: c.open, high: c.high, low: c.low, close: c.close })));

      const vol = (chart as any).addHistogramSeries({
        color: CHART_COLORS.volume + "99", priceFormat: { type: "volume" },
        priceScaleId: "vol", scaleMargins: { top: 0.8, bottom: 0 },
      });
      vol.setData(candles.map(c => ({ time: (new Date(c.time)).getTime() / 1000, value: c.volume, color: c.close >= c.open ? CHART_COLORS.up + "66" : CHART_COLORS.down + "66" })));
      chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

      if (indicatorData) {
        for (const [key, series] of Object.entries(indicatorData)) {
          if (key.startsWith("__") || key === "volume") continue;
          const arr = series as { time: string; value: number | null }[];
          if (!arr || !Array.isArray(arr)) continue;
          const data = arr.filter(d => d.value !== null).map(d => ({ time: (new Date(d.time)).getTime() / 1000, value: d.value! }));
          if (data.length === 0) continue;
          if (key === "rsi_14") {
            const r = (chart as any).addLineSeries({ color: "#eab308", lineWidth: 1, priceScaleId: "rsi_scale" });
            chart.priceScale("rsi_scale").applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } });
            r.setData(data);
          } else if (key.startsWith("macd_")) {
            const m = (chart as any).addLineSeries({ color: key === "macd_line" ? "#3b82f6" : key === "macd_signal" ? "#ef4444" : "#22c55e", lineWidth: 1, priceScaleId: "macd_scale" });
            chart.priceScale("macd_scale").applyOptions({ scaleMargins: { top: 0.65, bottom: 0 } });
            m.setData(data);
          } else if (key.startsWith("sma_") || key.startsWith("ema_")) {
            const l = (chart as any).addLineSeries({ color: key.startsWith("sma_") ? "#f59e0b" : "#8b5cf6", lineWidth: 1 });
            l.setData(data);
          }
        }
      }
      if (!disposed) chart.timeScale().fitContent();
    };
    init().catch(() => {});
    return () => { disposed = true; if (chart) chart.remove(); };
  }, [candles, indicatorData]);

  // ─── PINE ───
  const runPine = async () => {
    setPineRunning(true); setPineError(""); setPineResult(null);
    try {
      const resp = await fetch("/api/pine/run", { method: "POST", headers: { ...headers(), "Content-Type": "application/json" }, body: JSON.stringify({ symbol, script: pineScript, interval, days: 500 }) });
      const data = await resp.json();
      setPineResult(data);
      if (!data.success && data.errors) setPineError(data.errors.join("\n"));
    } catch (e: any) { setPineError(e.message); }
    setPineRunning(false);
  };

  // ─── NEWS ───
  useEffect(() => {
    if (!showNews || !symbol) return;
    fetch(`/api/news/company/${symbol}?page=1&page_size=10`, { headers: headers() })
      .then(r => r.json()).then(d => setNewsData(d)).catch(() => {});
  }, [showNews, symbol, headers]);

  // ─── TRADE ───
  const [tradeSide, setTradeSide] = useState<"BUY"|"SELL">("BUY");
  const [tradeQty, setTradeQty] = useState("1");
  const [tradePrice, setTradePrice] = useState("");
  const [tradeMsg, setTradeMsg] = useState("");
  const executeTrade = async () => {
    setTradeMsg("");
    try {
      const pfs = await api.listPortfolios().catch(() => []);
      if (pfs.length === 0) { setTradeMsg("Create a portfolio first"); return; }
      const pfId = pfs[0].id;
      const price = parseFloat(tradePrice) || (quote?.last_price || 0);
      const qty = parseInt(tradeQty) || 1;
      if (tradeSide === "BUY") await api.buy(pfId, symbol, qty, price);
      else await api.sell(pfId, symbol, qty, price);
      setTradeMsg(`\u2713 ${tradeSide} ${symbol} x${qty} @ \u20B9${price}`);
    } catch (e: any) { setTradeMsg(`\u2717 ${e.message}`); }
  };

  if (loading) return <div className="flex justify-center items-center h-screen bg-background"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  if (error && !quote) return <div className="flex justify-center items-center h-screen bg-background"><div className="text-center"><p className="text-danger mb-2">{error}</p><button onClick={() => fetchData(symbol, interval)} className="text-primary text-sm hover:underline">Retry</button></div></div>;

  const sc = (quote?.change || 0) >= 0 ? "text-success" : "text-danger";

  return (
    <div className={`flex flex-col h-screen bg-background overflow-hidden ${fullscreen ? "fixed inset-0 z-50" : ""}`}>
      {/* TOP BAR */}
      <div className="h-12 bg-surface border-b border-border flex items-center px-3 gap-3 flex-shrink-0">
        <button onClick={() => router.push("/markets")} className="text-muted hover:text-foreground"><ChevronLeft size={18} /></button>
        <span className="font-bold text-primary text-sm">{symbol}</span>
        {quote && <>
          <span className="text-xs text-muted">{quote.exchange}</span>
          <span className={`text-sm font-bold tabular-nums ${sc}`}>₹{quote.last_price?.toFixed(2)}</span>
          <span className={`text-xs tabular-nums ${sc}`}>{(quote.change || 0) >= 0 ? "+" : ""}{quote.change?.toFixed(2)} ({quote.change_pct?.toFixed(2)}%)</span>
        </>}
        <div className="flex items-center gap-1 ml-auto">
          {INTERVALS.map(iv => <button key={iv} onClick={() => setInterval_(iv)} className={`px-2 py-1 text-xs rounded ${interval===iv?"bg-primary/20 text-primary font-medium":"text-muted hover:text-foreground"}`}>{iv}</button>)}
        </div>
        <div className="flex items-center gap-1 border-l border-border pl-2">
          <button onClick={() => setShowIndicators(!showIndicators)} className={`p-1.5 rounded ${showIndicators?"bg-primary/20 text-primary":"text-muted hover:text-foreground"}`} title="Indicators"><Layers size={16} /></button>
          <button onClick={() => setShowPine(!showPine)} className={`p-1.5 rounded ${showPine?"bg-primary/20 text-primary":"text-muted hover:text-foreground"}`} title="Pine Editor"><SquareCode size={16} /></button>
          <button onClick={() => setShowNews(!showNews)} className={`p-1.5 rounded ${showNews?"bg-primary/20 text-primary":"text-muted hover:text-foreground"}`} title="News"><Newspaper size={16} /></button>
          <button onClick={() => setShowTrade(!showTrade)} className={`p-1.5 rounded ${showTrade?"bg-primary/20 text-primary":"text-muted hover:text-foreground"}`} title="Trade"><ShoppingCart size={16} /></button>
          <button onClick={() => setFullscreen(!fullscreen)} className="p-1.5 rounded text-muted hover:text-foreground">{fullscreen ? <Maximize size={16} /> : <Maximize size={16} />}</button>
          <button onClick={() => fetchData(symbol, interval)} className="p-1.5 rounded text-muted hover:text-foreground"><RefreshCw size={14} /></button>
        </div>
      </div>

      {/* CONTENT */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <div ref={chartRef} className="flex-1" style={{ minHeight: "400px" }} />
          {showPine && (
            <div className="h-48 bg-surface border-t border-border flex flex-col flex-shrink-0">
              <div className="flex items-center justify-between px-3 py-2 border-b border-border">
                <span className="text-xs font-semibold flex items-center gap-2"><SquareCode size={14} />Pine Script</span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-muted">Safe interpreter</span>
                  <button onClick={runPine} disabled={pineRunning} className="px-3 py-1 bg-primary hover:bg-primary-hover rounded text-xs font-medium flex items-center gap-1"><Play size={12} />{pineRunning?"Running":"Run"}</button>
                  <button onClick={() => setShowPine(false)} className="text-muted hover:text-foreground"><X size={14} /></button>
                </div>
              </div>
              <textarea value={pineScript} onChange={e => setPineScript(e.target.value)} className="flex-1 bg-background text-sm font-mono p-3 resize-none outline-none text-foreground" spellCheck={false} />
              {pineError && <div className="px-3 py-1 bg-danger/10 text-danger text-xs font-mono whitespace-pre-wrap max-h-24 overflow-auto">{pineError}</div>}
              {pineResult && pineResult.success && <div className="px-3 py-2 bg-success/10 text-success text-xs flex items-center justify-between"><span>{pineResult.strategy_name} — {pineResult.plots.length} plot(s)</span><span className="text-muted text-[10px]">Rendered on chart</span></div>}
            </div>
          )}
        </div>

        {/* RIGHT PANEL */}
        <div className="w-64 bg-surface border-l border-border flex-shrink-0 flex flex-col overflow-y-auto">
          <div className="p-3 border-b border-border">
            <h3 className="text-xs font-semibold text-muted mb-2">Symbols</h3>
            <div className="space-y-1">
              {QUICK_SYMBOLS.map(s => (
                <button key={s} onClick={() => router.push(`/chart/${s}`)} className={`w-full flex justify-between p-1.5 rounded text-xs hover:bg-surface-hover ${s===symbol?"bg-primary/10":""}`}>
                  <span className={`font-medium ${s===symbol?"text-primary":""}`}>{s}</span>
                </button>
              ))}
            </div>
          </div>

          {showNews && <div className="p-3 border-b border-border flex-1 overflow-y-auto">
            <h3 className="text-xs font-semibold text-muted mb-2">News</h3>
            {newsData && newsData.items && newsData.items.length > 0 ? newsData.items.slice(0, 10).map((a: any, i: number) => (
              <a key={i} href={a.url || "#"} target="_blank" rel="noopener" className="block p-2 rounded bg-background hover:bg-surface-hover mb-1">
                <p className="text-xs leading-snug line-clamp-2">{a.headline}</p>
                <p className="text-[10px] text-muted mt-0.5">{a.source}</p>
              </a>
            )) : <p className="text-xs text-muted text-center py-4">No news. Set MARKETAUX_API_KEY for Indian stock news.</p>}
          </div>}

          {showTrade && <div className="p-3 border-b border-border">
            <h3 className="text-xs font-semibold text-muted mb-2">Paper Trade</h3>
            <div className="flex gap-1 mb-2">
              <button onClick={() => setTradeSide("BUY")} className={`flex-1 py-1 text-xs rounded font-medium ${tradeSide==="BUY"?"bg-success/20 text-success":"bg-background text-muted"}`}>BUY</button>
              <button onClick={() => setTradeSide("SELL")} className={`flex-1 py-1 text-xs rounded font-medium ${tradeSide==="SELL"?"bg-danger/20 text-danger":"bg-background text-muted"}`}>SELL</button>
            </div>
            <div className="space-y-1.5">
              <input type="number" value={tradeQty} onChange={e => setTradeQty(e.target.value)} placeholder="Qty" className="w-full px-2 py-1 bg-background border border-border rounded text-xs" />
              <input type="number" value={tradePrice} onChange={e => setTradePrice(e.target.value)} placeholder={quote ? `Price (₹${quote.last_price.toFixed(2)})` : "Price"} className="w-full px-2 py-1 bg-background border border-border rounded text-xs" />
              <button onClick={executeTrade} className={`w-full py-1.5 rounded text-xs font-medium ${tradeSide==="BUY"?"bg-success/20 text-success":"bg-danger/20 text-danger"}`}>Execute {tradeSide}</button>
              {tradeMsg && <p className={`text-xs ${tradeMsg.startsWith("\u2713")?"text-success":"text-danger"}`}>{tradeMsg}</p>}
            </div>
          </div>}

          {showIndicators && <div className="p-3 border-b border-border">
            <h3 className="text-xs font-semibold text-muted mb-2">Indicators</h3>
            {["SMA 20","EMA 50","RSI 14","MACD","Volume"].map(ind => (
              <label key={ind} className="flex items-center gap-2 text-xs text-muted cursor-pointer hover:text-foreground py-0.5">
                <input type="checkbox" defaultChecked readOnly className="accent-primary" />{ind}
              </label>
            ))}
          </div>}

          {quote && <div className="p-3">
            <h3 className="text-xs font-semibold text-muted mb-2">Details</h3>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span className="text-muted">Open</span><span className="tabular-nums">₹{quote.open?.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-muted">High</span><span className="tabular-nums text-success">₹{quote.high?.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-muted">Low</span><span className="tabular-nums text-danger">₹{quote.low?.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-muted">Volume</span><span className="tabular-nums">{quote.volume?.toLocaleString("en-IN")}</span></div>
            </div>
          </div>}
        </div>
      </div>
    </div>
  );
}
