"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { Layers, SquareCode, Maximize, Newspaper, ShoppingCart, Play, X, RefreshCw, ChevronLeft } from "lucide-react";
import { createChart, ColorType, CandlestickSeries, HistogramSeries, LineSeries } from "lightweight-charts";
import { api } from "@/lib/api";

const INTERVALS = ["1m","3m","5m","15m","30m","1h","4h","1D","1W","1M"];
const QUICK = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC","LT","BHARTIARTL","AXISBANK","KOTAKBANK","TATAMOTORS","HINDUNILVR","EICHERMOT","TATASTEEL","M&M","BAJFINANCE","MARUTI","TITAN","SUNPHARMA"];

const DEFAULT_SCRIPT = `indicator("EMA Cross")\n\nfast = ema(close, 20)\nslow = ema(close, 50)\n\nplot(fast)\nplot(slow)`;

function toTime(iso: string): number { return (new Date(iso)).getTime() / 1000; }

export default function ChartPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = ((params?.symbol as string) || "").toUpperCase();

  const [interval, setInt] = useState("15m");
  const [status, setStatus] = useState<"loading"|"ready"|"error">("loading");
  const [errMsg, setErrMsg] = useState("");
  const [quoteStr, setQuoteStr] = useState("");

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any[]>([]);
  const obsRef = useRef<ResizeObserver | null>(null);

  const hdr = useCallback(() => ({ Authorization: `Bearer ${localStorage.getItem("access_token") || ""}` }), []);

  const loadAndRender = useCallback(async (sym: string, intv: string) => {
    setStatus("loading"); setErrMsg("");
    const container = containerRef.current;
    if (!container) { setErrMsg("Chart container not ready"); setStatus("error"); return; }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    try {
      const days = ["1D","1W","1M"].includes(intv) ? 365 : 7;
      const H = hdr();
      console.log("[CHART] Fetching", sym, intv, "days:", days);

      // Fetch quote (fire-and-forget)
      fetch(`/api/chart/${sym}/quote`, { headers: H, signal: controller.signal })
        .then(r => r.ok ? r.json() : null)
        .then(q => {
          if (q) setQuoteStr(`${sym} NSE  \u20B9${q.last_price?.toFixed(2)}  ${q.change >= 0 ? "+" : ""}${q.change?.toFixed(2)} (${q.change_pct?.toFixed(2)}%)`);
        }).catch(e => { if (e.name !== "AbortError") console.error("quote fetch:", e); });

      // Fetch candles
      const r = await fetch(`/api/chart/${sym}/candles?interval=${intv}&days=${days}`, { headers: H, signal: controller.signal });
      clearTimeout(timeoutId);
      if (!r.ok) throw new Error(`API ${r.status}`);
      const d = await r.json();
      console.log("[CHART] Response:", sym, "candles:", d.total);
      const raw = d.candles || [];
      if (!Array.isArray(raw) || raw.length === 0) {
        setErrMsg(`No data: ${sym} @ ${intv} returned ${raw.length} candles`);
        setStatus("error"); return;
      }

      // Destroy previous chart
      if (chartRef.current) { try { chartRef.current.remove(); } catch {} }
      chartRef.current = null;
      seriesRef.current = [];

      const w = container.clientWidth || 900;
      const h = container.clientHeight || 600;

      const chart = createChart(container, {
        layout: { background: { type: ColorType.Solid, color: "#0d0d1a" }, textColor: "#d1d5db", attributionLogo: false },
        grid: { vertLines: { color: "#1a1a2e" }, horzLines: { color: "#1a1a2e" } },
        crosshair: { mode: 0 },
        rightPriceScale: { borderColor: "#333", scaleMargins: { top: 0.05, bottom: 0.2 } },
        timeScale: { borderColor: "#333", timeVisible: true },
        width: w, height: h,
      });
      chartRef.current = chart;

      // Candlestick
      const candleData: any[] = raw.map((c: any) => ({ time: toTime(c.time), open: +c.open, high: +c.high, low: +c.low, close: +c.close }));
      const cs = chart.addSeries(CandlestickSeries, { upColor: "#22c55e", downColor: "#ef4444", borderUpColor: "#22c55e", borderDownColor: "#ef4444", wickUpColor: "#22c55e", wickDownColor: "#ef4444" } as any);
      cs.setData(candleData as any);
      seriesRef.current.push(cs);

      // Volume
      const vs = chart.addSeries(HistogramSeries, { color: "#3b82f699", priceFormat: { type: "volume" }, priceScaleId: "vol" } as any);
      vs.setData(raw.map((c: any) => ({ time: toTime(c.time), value: +c.volume, color: c.close >= c.open ? "#22c55e66" : "#ef4444" + "66" })) as any);
      chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
      seriesRef.current.push(vs);

      // Indicators (async, non-blocking)
      fetch(`/api/chart/${sym}/indicators?indicators=sma20,ema50,rsi14,macd,volume`, { headers: H })
        .then(r => r.ok ? r.json() : null)
        .then(ind => {
          if (!ind?.indicators || !chartRef.current) return;
          for (const [k, v] of Object.entries(ind.indicators)) {
            if (k.startsWith("__") || k === "volume" || !Array.isArray(v)) continue;
            const data: any[] = (v as any[]).filter(x => x.value != null).map(x => ({ time: toTime(x.time), value: +x.value! }));
            if (data.length === 0) continue;
            if (k === "sma_20") { const s = chart.addSeries(LineSeries, { color: "#f59e0b", lineWidth: 1 } as any) as any; s.setData(data as any); seriesRef.current.push(s); }
            else if (k === "ema_50") { const s = chart.addSeries(LineSeries, { color: "#8b5cf6", lineWidth: 1 } as any) as any; s.setData(data as any); seriesRef.current.push(s); }
            else if (k === "rsi_14") { const s = chart.addSeries(LineSeries, { color: "#eab308", lineWidth: 1, priceScaleId: "rsi" } as any) as any; chart.priceScale("rsi").applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } }); s.setData(data as any); seriesRef.current.push(s); }
            else if (k.startsWith("macd_")) { const s = chart.addSeries(LineSeries, { color: k === "macd_line" ? "#3b82f6" : k === "macd_signal" ? "#ef4444" : "#22c55e", lineWidth: 1, priceScaleId: "macd" } as any) as any; chart.priceScale("macd").applyOptions({ scaleMargins: { top: 0.65, bottom: 0 } }); s.setData(data as any); seriesRef.current.push(s); }
          }
        }).catch(() => {});

      chart.timeScale().fitContent();

      if (!obsRef.current) {
        obsRef.current = new ResizeObserver(() => {
          if (chartRef.current && container) chartRef.current.applyOptions({ width: container.clientWidth, height: container.clientHeight });
        });
        obsRef.current.observe(container);
      }

      setStatus("ready");
    } catch (e: any) {
      clearTimeout(timeoutId);
      const msg = e.name === "AbortError" ? "Request timed out (15s). Check API." : (e.message || "Unknown error");
      setErrMsg(msg);
      setStatus("error");
    }
  }, [hdr]);

  useEffect(() => {
    if (symbol) loadAndRender(symbol, interval);
  }, [symbol, interval, loadAndRender]);

  // Pine
  const [showPine, setPine] = useState(false);
  const [pineScript, setPineScript] = useState(DEFAULT_SCRIPT);
  const [pineRunning, setPineRunning] = useState(false);
  const [pineErr, setPineErr] = useState("");
  const [pineOk, setPineOk] = useState("");
  const runPine = async () => {
    setPineRunning(true); setPineErr(""); setPineOk("");
    try {
      const r = await fetch("/api/pine/run", { method: "POST", headers: { ...hdr(), "Content-Type": "application/json" }, body: JSON.stringify({ symbol, script: pineScript, interval, days: 500 }) });
      const d = await r.json();
      if (d.success) setPineOk(`${d.strategy_name || "Script"} — ${d.plots?.length || 0} plots`);
      else if (d.errors) setPineErr(d.errors.join("\n"));
    } catch (e: any) { setPineErr(e.message); }
    setPineRunning(false);
  };

  // News
  const [showNews, setNews] = useState(false);
  const [newsData, setNewsData] = useState<any>(null);
  useEffect(() => {
    if (!showNews) return;
    fetch(`/api/news/company/${symbol}?page=1&page_size=8`, { headers: hdr() }).then(r => r.json()).then(d => setNewsData(d)).catch(() => {});
  }, [showNews, symbol, hdr]);

  // Trade
  const [showTrade, setTrade] = useState(false);
  const [side, setSide] = useState<"BUY"|"SELL">("BUY");
  const [qty, setQty] = useState("1");
  const [prc, setPrc] = useState("");
  const [tMsg, setTMsg] = useState("");
  const doTrade = async () => {
    setTMsg("");
    try {
      const pfs = await api.listPortfolios().catch(() => []);
      if (!pfs.length) { setTMsg("No portfolio. Create one first."); return; }
      const price = parseFloat(prc) || 0;
      const n = parseInt(qty) || 1;
      if (side === "BUY") await api.buy(pfs[0].id, symbol, n, price);
      else await api.sell(pfs[0].id, symbol, n, price);
      setTMsg(`\u2713 Done: ${side} ${symbol} x${n} @ \u20B9${price}`);
    } catch (e: any) { setTMsg(`\u2717 ${e.message}`); }
  };

  return (
    <div className="flex flex-col h-screen bg-[#0a0a14] overflow-hidden">
      {/* TOP BAR */}
      <div className="h-10 bg-[#13131a] border-b border-[#1a1a2e] flex items-center px-3 gap-3 flex-shrink-0">
        <button onClick={() => router.push("/markets")} className="text-gray-400 hover:text-white"><ChevronLeft size={16} /></button>
        <span className="text-xs text-gray-300 font-mono">{quoteStr || symbol}</span>
        <div className="flex items-center gap-0.5 ml-auto">
          {INTERVALS.map(iv => (
            <button key={iv} onClick={() => setInt(iv)} className={`px-1.5 py-0.5 text-[11px] rounded-sm ${interval===iv?"bg-indigo-900/40 text-indigo-300 font-medium":"text-gray-600 hover:text-gray-400"}`}>{iv}</button>
          ))}
        </div>
        <div className="flex items-center gap-1 border-l border-[#1a1a2e] pl-2">
          <button onClick={() => setPine(!showPine)} className={`p-1 rounded-sm ${showPine?"bg-indigo-900/40 text-indigo-300":"text-gray-600 hover:text-gray-400"}`} title="Pine"><SquareCode size={14} /></button>
          <button onClick={() => setNews(!showNews)} className={`p-1 rounded-sm ${showNews?"bg-indigo-900/40 text-indigo-300":"text-gray-600 hover:text-gray-400"}`} title="News"><Newspaper size={14} /></button>
          <button onClick={() => setTrade(!showTrade)} className={`p-1 rounded-sm ${showTrade?"bg-indigo-900/40 text-indigo-300":"text-gray-600 hover:text-gray-400"}`} title="Trade"><ShoppingCart size={14} /></button>
          <button onClick={() => loadAndRender(symbol, interval)} className="p-1 rounded-sm text-gray-600 hover:text-gray-400" title="Refresh"><RefreshCw size={14} /></button>
          <button onClick={() => document.documentElement.requestFullscreen?.()} className="p-1 rounded-sm text-gray-600 hover:text-gray-400" title="Fullscreen"><Maximize size={14} /></button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* SYMBOL SIDEBAR */}
        <div className="w-14 bg-[#13131a] border-r border-[#1a1a2e] overflow-y-auto flex-shrink-0">
          {QUICK.map(s => (
            <button key={s} onClick={() => router.push(`/chart/${s}`)}
              className={`w-full py-1.5 text-[10px] ${s===symbol?"text-indigo-400 bg-indigo-900/20 font-medium":"text-gray-600 hover:text-gray-400 hover:bg-[#1a1a2e]"}`}>{s}</button>
          ))}
        </div>

        {/* MAIN */}
        <div className="flex-1 flex flex-col min-w-0">
          {status === "loading" && <div className="flex-1 flex items-center justify-center"><div className="animate-spin h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full" /></div>}
          {status === "error" && <div className="flex-1 flex items-center justify-center"><div className="text-center"><p className="text-red-400 text-sm mb-2">{errMsg}</p><button onClick={() => loadAndRender(symbol, interval)} className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded">Retry</button></div></div>}
          {status === "ready" && <div ref={containerRef} className="flex-1" style={{ minHeight: 300 }} />}

          {showPine && (
            <div className="h-44 bg-[#13131a] border-t border-[#1a1a2e] flex flex-col flex-shrink-0">
              <div className="flex items-center justify-between px-3 py-1.5 border-b border-[#1a1a2e]">
                <span className="text-xs text-gray-300 font-semibold"><SquareCode size={12} className="inline mr-1" />Pine Script</span>
                <div className="flex items-center gap-2">
                  <button onClick={runPine} disabled={pineRunning} className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 rounded text-[11px] text-white font-medium"><Play size={10} className="inline mr-1" />{pineRunning?"Running":"Run"}</button>
                  <button onClick={() => setPine(false)} className="text-gray-600 hover:text-gray-300"><X size={14} /></button>
                </div>
              </div>
              <textarea value={pineScript} onChange={e => setPineScript(e.target.value)} className="flex-1 bg-[#0a0a14] text-xs font-mono p-2 resize-none outline-none text-[#c9d1d9]" spellCheck={false} />
              {pineErr && <div className="px-2 py-1 bg-red-950/50 text-red-300 text-[11px] font-mono whitespace-pre-wrap max-h-20 overflow-auto border-t border-red-900/50">{pineErr}</div>}
              {pineOk && <div className="px-2 py-1 bg-emerald-950/50 text-emerald-300 text-[11px] border-t border-emerald-900/50">{pineOk}</div>}
            </div>
          )}
        </div>

        {/* RIGHT PANEL */}
        {(showNews || showTrade) && (
          <div className="w-52 bg-[#13131a] border-l border-[#1a1a2e] overflow-y-auto flex-shrink-0 text-[11px]">
            {showNews && <div className="p-2">
              <h3 className="font-semibold text-gray-400 mb-2">Company News</h3>
              {newsData?.items?.length > 0 ? newsData.items.slice(0, 15).map((a: any, i: number) => (
                <a key={i} href={a.url || "#"} target="_blank" rel="noopener" className="block p-1.5 rounded bg-[#0a0a14] hover:bg-[#1a1a2e] mb-1">
                  <p className="leading-snug line-clamp-2 text-gray-300">{a.headline}</p>
                  <p className="text-[10px] text-gray-600 mt-0.5">{a.source}</p>
                </a>
              )) : <p className="text-gray-600 text-center py-4">Set MARKETAUX_API_KEY<br/>for Indian stock news.</p>}
            </div>}
            {showTrade && <div className="p-2">
              <h3 className="font-semibold text-gray-400 mb-2">Paper Trade</h3>
              <div className="flex gap-1 mb-2">
                <button onClick={() => setSide("BUY")} className={`flex-1 py-0.5 rounded text-[11px] font-medium ${side==="BUY"?"bg-green-900/40 text-green-400":"bg-[#0a0a14] text-gray-600"}`}>BUY</button>
                <button onClick={() => setSide("SELL")} className={`flex-1 py-0.5 rounded text-[11px] font-medium ${side==="SELL"?"bg-red-900/40 text-red-400":"bg-[#0a0a14] text-gray-600"}`}>SELL</button>
              </div>
              <input type="number" value={qty} onChange={e => setQty(e.target.value)} placeholder="Qty" className="w-full px-2 py-1 bg-[#0a0a14] border border-[#1a1a2e] rounded text-gray-300 mb-1" />
              <input type="number" value={prc} onChange={e => setPrc(e.target.value)} placeholder="Price" className="w-full px-2 py-1 bg-[#0a0a14] border border-[#1a1a2e] rounded text-gray-300 mb-1" />
              <button onClick={doTrade} className={`w-full py-1 rounded text-[11px] font-medium ${side==="BUY"?"bg-green-900/30 text-green-400":"bg-red-900/30 text-red-400"}`}>{side}</button>
              {tMsg && <p className={`mt-1 text-[11px] ${tMsg.startsWith("\u2713")?"text-green-400":"text-red-400"}`}>{tMsg}</p>}
            </div>}
          </div>
        )}
      </div>
    </div>
  );
}
