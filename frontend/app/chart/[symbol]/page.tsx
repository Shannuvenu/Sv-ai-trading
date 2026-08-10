"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { Activity, TrendingUp, TrendingDown, Layers, SquareCode, Maximize, Newspaper, ShoppingCart, Play, X, RefreshCw, ChevronLeft } from "lucide-react";
import { api } from "@/lib/api";

interface CandleData { time: string; open: number; high: number; low: number; close: number; volume: number; }
interface QuoteData { symbol: string; name: string; exchange: string; last_price: number; change: number; change_pct: number; high: number; low: number; volume: number; open: number; }

const INTERVALS = ["1m","3m","5m","15m","30m","1h","4h","1D","1W","1M"];
const QUICK_SYMBOLS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC","LT","BHARTIARTL","AXISBANK","KOTAKBANK"];
const CHART_BG = "#0d0d1a";  const CHART_GRID = "#1a1a2e";
const UP_COLOR = "#22c55e";   const DOWN_COLOR = "#ef4444";

const DEFAULT_SCRIPT = `indicator("EMA Cross")\n\nfast = ema(close, 20)\nslow = ema(close, 50)\n\nplot(fast)\nplot(slow)`;

export default function ChartPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = ((params?.symbol as string) || "").toUpperCase();

  const [candles, setCandles] = useState<CandleData[]>([]);
  const [quote, setQuote] = useState<QuoteData | null>(null);
  const [interval, setInterval_] = useState("15m");
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [fullscreen, setFullscreen] = useState(false);
  const [showPine, setShowPine] = useState(false);
  const [showNews, setShowNews] = useState(false);
  const [showTrade, setShowTrade] = useState(false);
  const [showIndicators, setShowIndicators] = useState(false);
  const [pineScript, setPineScript] = useState(DEFAULT_SCRIPT);
  const [pineResult, setPineResult] = useState<any>(null);
  const [pineRunning, setPineRunning] = useState(false);
  const [pineError, setPineError] = useState("");
  const [indicatorData, setIndicatorData] = useState<any>(null);
  const [newsData, setNewsData] = useState<any>(null);
  const [chartReady, setChartReady] = useState(false);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<any>(null);
  const candleSeriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);
  const indicatorSeriesRef = useRef<any[]>([]);

  const authHeaders = useCallback(() => {
    const t = localStorage.getItem("access_token") || "";
    return { Authorization: `Bearer ${t}` };
  }, []);

  // ─── FETCH DATA ───
  const fetchAll = useCallback(async (sym: string, intv: string) => {
    setLoading(true); setFetchError(""); setChartReady(false);
    try {
      const h = authHeaders();
      const fetchDays = ["1D","1W","1M"].includes(intv) ? 365 : 7;
      const [q, c, ind] = await Promise.all([
        fetch(`/api/chart/${sym}/quote`, { headers: h }).then(r => r.ok ? r.json() : null),
        fetch(`/api/chart/${sym}/candles?interval=${intv}&days=${fetchDays}`, { headers: h }).then(r => r.ok ? r.json() : null),
        fetch(`/api/chart/${sym}/indicators?indicators=sma20,ema50,rsi14,macd,volume`, { headers: h }).then(r => r.ok ? r.json() : null),
      ]);
      if (q) setQuote(q);
      if (c && c.candles && Array.isArray(c.candles) && c.candles.length > 0) {
        setCandles(c.candles);
        setChartReady(true);
      } else {
        setFetchError("No historical market data available for this symbol/timeframe.");
      }
      if (ind && ind.indicators) setIndicatorData(ind.indicators);
    } catch (e: any) {
      setFetchError("Unable to load market data. Please try again.");
      console.error("Chart data fetch error:", e);
    }
    setLoading(false);
  }, [authHeaders]);

  useEffect(() => { if (symbol) fetchAll(symbol, interval); }, [symbol, interval, fetchAll]);

  // ─── RENDER CHART ───
  useEffect(() => {
    if (!chartReady || candles.length === 0 || !chartContainerRef.current) return;

    let disposed = false;
    const container = chartContainerRef.current;

    const buildChart = async () => {
      // destroy previous instance
      if (chartInstanceRef.current) {
        try { chartInstanceRef.current.remove(); } catch {}
        chartInstanceRef.current = null;
      }

      // dynamic import
      let createChartFn: any;
      try {
        const mod = await import("lightweight-charts");
        createChartFn = (mod as any).createChart;
      } catch {
        console.error("Failed to import lightweight-charts");
        return;
      }
      if (!createChartFn || disposed) return;

      const w = container.clientWidth || 800;
      const h = container.clientHeight || 500;

      const chart = createChartFn(container, {
        layout: {
          background: { type: "solid", color: CHART_BG },
          textColor: "#d1d5db",
          attributionLogo: false,
        },
        grid: {
          vertLines: { color: CHART_GRID },
          horzLines: { color: CHART_GRID },
        },
        crosshair: { mode: 0 },
        rightPriceScale: { borderColor: "#333", scaleMargins: { top: 0.05, bottom: 0.2 } },
        timeScale: { borderColor: "#333", timeVisible: true },
        width: w,
        height: h,
      });
      chartInstanceRef.current = chart;
      if (disposed) { chart.remove(); return; }

      // ─── CANDLESTICK SERIES ───
      const candleData = candles.map(c => ({
        time: (new Date(c.time)).getTime() / 1000,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));
      const candleSeries = chart.addCandlestickSeries({
        upColor: UP_COLOR,
        downColor: DOWN_COLOR,
        borderUpColor: UP_COLOR,
        borderDownColor: DOWN_COLOR,
        wickUpColor: UP_COLOR,
        wickDownColor: DOWN_COLOR,
      });
      candleSeries.setData(candleData);
      candleSeriesRef.current = candleSeries;

      // ─── VOLUME ───
      const volSeries = chart.addHistogramSeries({
        color: "#3b82f699",
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });
      volSeries.setData(candles.map(c => ({
        time: (new Date(c.time)).getTime() / 1000,
        value: c.volume,
        color: c.close >= c.open ? UP_COLOR + "66" : DOWN_COLOR + "66",
      })));
      chart.priceScale("volume").applyOptions({
        scaleMargins: { top: 0.85, bottom: 0 },
      });
      volumeSeriesRef.current = volSeries;

      // ─── INDICATORS ───
      const added: any[] = [];
      if (indicatorData) {
        for (const [key, series] of Object.entries(indicatorData)) {
          if (key.startsWith("__") || key === "volume" || !Array.isArray(series)) continue;
          const arr = series as { time: string; value: number | null }[];
          if (arr.length === 0) continue;
          const data = arr
            .filter(d => d.value !== null && d.value !== undefined)
            .map(d => ({ time: (new Date(d.time)).getTime() / 1000, value: d.value! }));
          if (data.length === 0) continue;

          if (key === "sma_20") {
            const s = chart.addLineSeries({ color: "#f59e0b", lineWidth: 1 });
            s.setData(data); added.push(s);
          } else if (key === "sma_50") {
            const s = chart.addLineSeries({ color: "#6366f1", lineWidth: 1 });
            s.setData(data); added.push(s);
          } else if (key === "ema_50") {
            const s = chart.addLineSeries({ color: "#8b5cf6", lineWidth: 1 });
            s.setData(data); added.push(s);
          } else if (key === "rsi_14") {
            const s = chart.addLineSeries({ color: "#eab308", lineWidth: 1, priceScaleId: "rsi" });
            chart.priceScale("rsi").applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } });
            s.setData(data); added.push(s);
          } else if (key.startsWith("macd_")) {
            const color = key === "macd_line" ? "#3b82f6" : key === "macd_signal" ? "#ef4444" : "#22c55e";
            const s = chart.addLineSeries({ color, lineWidth: 1, priceScaleId: "macd" });
            chart.priceScale("macd").applyOptions({ scaleMargins: { top: 0.65, bottom: 0 } });
            s.setData(data); added.push(s);
          }
        }
      }
      indicatorSeriesRef.current = added;

      chart.timeScale().fitContent();

      // Resize observer
      const observer = new ResizeObserver(() => {
        if (chartInstanceRef.current && container) {
          chartInstanceRef.current.applyOptions({ width: container.clientWidth, height: container.clientHeight });
        }
      });
      observer.observe(container);
    };

    buildChart().catch(console.error);

    return () => {
      disposed = true;
      if (chartInstanceRef.current) {
        try { chartInstanceRef.current.remove(); } catch {}
        chartInstanceRef.current = null;
      }
    };
  }, [chartReady, candles, indicatorData]);

  // ─── PINE ───
  const runPine = async () => {
    setPineRunning(true); setPineError("");
    try {
      const resp = await fetch("/api/pine/run", {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, script: pineScript, interval, days: 500 }),
      });
      const data = await resp.json();
      setPineResult(data);
      if (!data.success && data.errors) setPineError(data.errors.join("\n"));
    } catch (e: any) { setPineError(e.message); }
    setPineRunning(false);
  };

  // ─── NEWS ───
  useEffect(() => {
    if (!showNews || !symbol) return;
    fetch(`/api/news/company/${symbol}?page=1&page_size=10`, { headers: authHeaders() })
      .then(r => r.json()).then(d => setNewsData(d)).catch(() => {});
  }, [showNews, symbol, authHeaders]);

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
      const price = parseFloat(tradePrice) || (quote?.last_price || 0);
      const qty = parseInt(tradeQty) || 1;
      if (tradeSide === "BUY") await api.buy(pfs[0].id, symbol, qty, price);
      else await api.sell(pfs[0].id, symbol, qty, price);
      setTradeMsg(`\u2713 ${tradeSide} ${symbol} x${qty} @ \u20B9${price}`);
    } catch (e: any) { setTradeMsg(`\u2717 ${e.message}`); }
  };

  const sc = (quote?.change || 0) >= 0 ? "text-success" : "text-danger";

  // ─── LOADING ───
  if (loading) {
    return (
      <div className="flex flex-col h-screen bg-background">
        <div className="h-12 bg-surface border-b border-border flex items-center px-3">
          <button onClick={() => router.push("/markets")} className="text-muted hover:text-foreground"><ChevronLeft size={18} /></button>
          <span className="font-bold text-primary text-sm ml-2">Loading {symbol}...</span>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin h-10 w-10 border-2 border-primary border-t-transparent rounded-full mx-auto mb-3" />
            <p className="text-muted text-sm">Loading {symbol} market data...</p>
          </div>
        </div>
      </div>
    );
  }

  // ─── ERROR ───
  if (fetchError) {
    return (
      <div className="flex flex-col h-screen bg-background">
        <div className="h-12 bg-surface border-b border-border flex items-center px-3">
          <button onClick={() => router.push("/markets")} className="text-muted hover:text-foreground"><ChevronLeft size={18} /></button>
          <span className="font-bold text-primary text-sm ml-2">{symbol}</span>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <p className="text-danger text-sm mb-3">{fetchError}</p>
            <button onClick={() => fetchAll(symbol, interval)} className="px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">Retry</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-screen bg-background overflow-hidden ${fullscreen ? "fixed inset-0 z-50" : ""}`}>
      {/* TOP BAR */}
      <div className="h-12 bg-surface border-b border-border flex items-center px-3 gap-3 flex-shrink-0">
        <button onClick={() => router.push("/markets")} className="text-muted hover:text-foreground"><ChevronLeft size={18} /></button>
        <span className="font-bold text-primary text-sm">{symbol}</span>
        {quote && (
          <>
            <span className="text-xs text-muted">{quote.exchange}</span>
            <span className={`text-sm font-bold tabular-nums ${sc}`}>₹{quote.last_price?.toFixed(2)}</span>
            <span className={`text-xs tabular-nums ${sc}`}>{(quote.change || 0) >= 0 ? "+" : ""}{quote.change?.toFixed(2)} ({quote.change_pct?.toFixed(2)}%)</span>
            <span className="text-xs text-muted">Vol: {quote.volume?.toLocaleString("en-IN")}</span>
          </>
        )}
        <div className="flex items-center gap-1 ml-auto">
          {INTERVALS.map(iv => (
            <button key={iv} onClick={() => setInterval_(iv)}
              className={`px-2 py-1 text-xs rounded ${interval === iv ? "bg-primary/20 text-primary font-medium" : "text-muted hover:text-foreground"}`}>
              {iv}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 border-l border-border pl-2">
          <button onClick={() => setShowIndicators(!showIndicators)} className={`p-1.5 rounded ${showIndicators ? "bg-primary/20 text-primary" : "text-muted hover:text-foreground"}`} title="Indicators"><Layers size={16} /></button>
          <button onClick={() => setShowPine(!showPine)} className={`p-1.5 rounded ${showPine ? "bg-primary/20 text-primary" : "text-muted hover:text-foreground"}`} title="Pine Editor"><SquareCode size={16} /></button>
          <button onClick={() => setShowNews(!showNews)} className={`p-1.5 rounded ${showNews ? "bg-primary/20 text-primary" : "text-muted hover:text-foreground"}`} title="News"><Newspaper size={16} /></button>
          <button onClick={() => setShowTrade(!showTrade)} className={`p-1.5 rounded ${showTrade ? "bg-primary/20 text-primary" : "text-muted hover:text-foreground"}`} title="Trade"><ShoppingCart size={16} /></button>
          <button onClick={() => setFullscreen(!fullscreen)} className="p-1.5 rounded text-muted hover:text-foreground" title="Fullscreen"><Maximize size={16} /></button>
          <button onClick={() => fetchAll(symbol, interval)} className="p-1.5 rounded text-muted hover:text-foreground" title="Refresh"><RefreshCw size={14} /></button>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <div ref={chartContainerRef} className="flex-1" style={{ minHeight: "400px" }} />

          {/* PINE EDITOR */}
          {showPine && (
            <div className="h-48 bg-surface border-t border-border flex flex-col flex-shrink-0">
              <div className="flex items-center justify-between px-3 py-2 border-b border-border">
                <span className="text-xs font-semibold flex items-center gap-2"><SquareCode size={14} />Pine Script Editor</span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-muted">Safe AST-based interpreter</span>
                  <button onClick={runPine} disabled={pineRunning} className="px-3 py-1 bg-primary hover:bg-primary-hover rounded text-xs font-medium flex items-center gap-1">
                    <Play size={12} />{pineRunning ? "Running..." : "Run Script"}
                  </button>
                  <button onClick={() => setShowPine(false)} className="text-muted hover:text-foreground"><X size={14} /></button>
                </div>
              </div>
              <textarea
                value={pineScript}
                onChange={e => setPineScript(e.target.value)}
                className="flex-1 bg-[#0a0a14] text-sm font-mono p-3 resize-none outline-none text-[#c9d1d9]"
                style={{ fontFamily: "'Fira Code', 'Consolas', 'Courier New', monospace" }}
                spellCheck={false}
              />
              {pineError && (
                <div className="px-3 py-1.5 bg-red-950/50 text-red-300 text-xs font-mono whitespace-pre-wrap max-h-24 overflow-auto border-t border-red-900/50">
                  {pineError}
                </div>
              )}
              {pineResult && pineResult.success && (
                <div className="px-3 py-1.5 bg-emerald-950/50 text-emerald-300 text-xs flex items-center justify-between border-t border-emerald-900/50">
                  <span>{pineResult.strategy_name || "Script"} — {pineResult.plots?.length || 0} plot(s), {pineResult.trades?.length || 0} trade(s)</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* RIGHT PANEL */}
        <div className="w-64 bg-surface border-l border-border flex-shrink-0 flex flex-col overflow-y-auto">
          <div className="p-3 border-b border-border">
            <h3 className="text-xs font-semibold text-muted mb-2">Symbols</h3>
            <div className="space-y-0.5">
              {QUICK_SYMBOLS.map(s => (
                <button key={s} onClick={() => { setChartReady(false); router.push(`/chart/${s}`); }}
                  className={`w-full flex justify-between items-center p-1.5 rounded text-xs hover:bg-surface-hover ${s === symbol ? "bg-primary/10" : ""}`}>
                  <span className={`font-medium ${s === symbol ? "text-primary" : ""}`}>{s}</span>
                </button>
              ))}
            </div>
          </div>

          {showNews && (
            <div className="p-3 border-b border-border flex-1 overflow-y-auto">
              <h3 className="text-xs font-semibold text-muted mb-2">News</h3>
              {newsData?.items?.length > 0 ? (
                newsData.items.slice(0, 12).map((a: any, i: number) => (
                  <a key={i} href={a.url || "#"} target="_blank" rel="noopener" className="block p-2 rounded bg-[#0a0a14] hover:bg-surface-hover mb-1.5">
                    <p className="text-xs leading-snug line-clamp-2">{a.headline}</p>
                    <p className="text-[10px] text-muted mt-1">{a.source}</p>
                  </a>
                ))
              ) : (
                <p className="text-xs text-muted text-center py-6">No Indian stock news.<br/>Set MARKETAUX_API_KEY</p>
              )}
            </div>
          )}

          {showTrade && (
            <div className="p-3 border-b border-border">
              <h3 className="text-xs font-semibold text-muted mb-2">Paper Trade</h3>
              <div className="flex gap-1 mb-2">
                <button onClick={() => setTradeSide("BUY")} className={`flex-1 py-1 text-xs rounded font-medium ${tradeSide === "BUY" ? "bg-green-900/40 text-green-400" : "bg-background text-muted"}`}>BUY</button>
                <button onClick={() => setTradeSide("SELL")} className={`flex-1 py-1 text-xs rounded font-medium ${tradeSide === "SELL" ? "bg-red-900/40 text-red-400" : "bg-background text-muted"}`}>SELL</button>
              </div>
              <div className="space-y-1.5">
                <input type="number" value={tradeQty} onChange={e => setTradeQty(e.target.value)} placeholder="Quantity" className="w-full px-2 py-1 bg-[#0a0a14] border border-border rounded text-xs" />
                <input type="number" value={tradePrice} onChange={e => setTradePrice(e.target.value)} placeholder={quote ? `Price (₹${quote.last_price.toFixed(2)})` : "Price"} className="w-full px-2 py-1 bg-[#0a0a14] border border-border rounded text-xs" />
                <button onClick={executeTrade} className={`w-full py-1.5 rounded text-xs font-medium ${tradeSide === "BUY" ? "bg-green-900/30 text-green-400 hover:bg-green-900/50" : "bg-red-900/30 text-red-400 hover:bg-red-900/50"}`}>
                  Execute {tradeSide}
                </button>
                {tradeMsg && <p className={`text-xs mt-1 ${tradeMsg.startsWith("\u2713") ? "text-green-400" : "text-red-400"}`}>{tradeMsg}</p>}
              </div>
            </div>
          )}

          {showIndicators && (
            <div className="p-3 border-b border-border">
              <h3 className="text-xs font-semibold text-muted mb-2">Active Indicators</h3>
              <div className="space-y-1.5 text-xs">
                {[
                  { name: "SMA 20", color: "#f59e0b" },
                  { name: "EMA 50", color: "#8b5cf6" },
                  { name: "RSI 14", color: "#eab308" },
                  { name: "MACD", color: "#3b82f6" },
                  { name: "Volume", color: "#6366f1" },
                ].map(ind => (
                  <div key={ind.name} className="flex items-center gap-2 py-0.5">
                    <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: ind.color }} />
                    <span className="text-muted">{ind.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {quote && (
            <div className="p-3">
              <h3 className="text-xs font-semibold text-muted mb-2">Quote Details</h3>
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between"><span className="text-muted">Open</span><span className="tabular-nums">₹{quote.open?.toFixed(2)}</span></div>
                <div className="flex justify-between"><span className="text-muted">High</span><span className="tabular-nums text-green-400">₹{quote.high?.toFixed(2)}</span></div>
                <div className="flex justify-between"><span className="text-muted">Low</span><span className="tabular-nums text-red-400">₹{quote.low?.toFixed(2)}</span></div>
                <div className="flex justify-between"><span className="text-muted">Volume</span><span className="tabular-nums">{quote.volume?.toLocaleString("en-IN")}</span></div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
