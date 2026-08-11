"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { SquareCode, Newspaper, ShoppingCart, Play, X, RefreshCw, ChevronLeft, Maximize } from "lucide-react";
import { api } from "@/lib/api";

const INTERVALS = ["1m","3m","5m","15m","30m","1h","4h","1D","1W","1M"];
const STOCKS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC","LT","BHARTIARTL","AXISBANK","KOTAKBANK","TATAMOTORS","HINDUNILVR","EICHERMOT","TATASTEEL","M&M","BAJFINANCE","MARUTI","TITAN","SUNPHARMA"];

function fmtPrice(n: number) { return n ? "\u20B9" + n.toFixed(2) : "\u2014"; }
function chr(up: boolean) { return up ? "#22c55e" : "#ef4444"; }

export default function ChartPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = ((params?.symbol as string) || "").toUpperCase();
  const [interval, setInt] = useState("15m");
  const [state, setState] = useState<"load"|"ok"|"err">("load");
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const hdr = useCallback(() => ({ Authorization: `Bearer ${localStorage.getItem("access_token") || ""}` }), []);

  const renderChart = useCallback((raw: any[]) => {
    const canvas = canvasRef.current;
    const box = containerRef.current;
    if (!canvas || !box) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = box.clientWidth;
    const H = box.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.scale(dpr, dpr);

    const candles = raw.map(c => ({ t: new Date(c.time).getTime() / 1000, o: +c.open, h: +c.high, l: +c.low, c: +c.close, v: +c.volume }));
    const n = candles.length;
    if (n === 0) return;

    const padLeft = 60, padRight = 20, padTop = 20, padBottom = 30;
    const volHeight = 60;
    const chartW = W - padLeft - padRight;
    const chartH = H - padTop - padBottom - volHeight;
    const minT = candles[0].t, maxT = candles[n - 1].t;
    let minP = Infinity, maxP = -Infinity;
    for (const c of candles) { if (c.l < minP) minP = c.l; if (c.h > maxP) maxP = c.h; }
    const priceMargin = (maxP - minP) * 0.05 || 10;
    minP -= priceMargin;
    maxP += priceMargin;
    const xScale = (t: number) => padLeft + ((t - minT) / (maxT - minT)) * chartW;
    const yScale = (p: number) => padTop + (1 - (p - minP) / (maxP - minP)) * chartH;
    const candleW = Math.max(1, Math.min(8, chartW / n * 0.8));

    // Draw background
    ctx.fillStyle = "#0d0d1a";
    ctx.fillRect(0, 0, W, H);

    // Grid
    ctx.strokeStyle = "#1a1a2e";
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 5; i++) {
      const y = padTop + (chartH / 5) * i;
      ctx.beginPath(); ctx.moveTo(padLeft, y); ctx.lineTo(padLeft + chartW, y); ctx.stroke();
      const price = maxP - ((maxP - minP) / 5) * i;
      ctx.fillStyle = "#52525b";
      ctx.font = "9px monospace";
      ctx.textAlign = "right";
      ctx.fillText("\u20B9" + price.toFixed(i === 0 ? 0 : 1), padLeft - 4, y + 3);
    }

    // Candles
    for (const c of candles) {
      const x = xScale(c.t);
      const yO = yScale(c.o), yC = yScale(c.c), yH = yScale(c.h), yL = yScale(c.l);
      const up = c.c >= c.o;
      const color = up ? chr(true) : chr(false);
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      // Wick
      ctx.beginPath(); ctx.moveTo(x, yH); ctx.lineTo(x, yL); ctx.stroke();
      // Body
      const bodyH = Math.max(1, Math.abs(yO - yC));
      ctx.fillRect(x - candleW / 2, Math.min(yO, yC), Math.max(1, candleW), bodyH);
    }

    // Volume
    const maxV = Math.max(...raw.map(c => +c.volume));
    const volTop = H - padBottom - volHeight;
    const volYS = maxV > 0 ? volHeight / maxV : 0;
    for (const c of candles) {
      const x = xScale(c.t);
      const h = Math.max(1, c.v * volYS);
      const up = c.c >= c.o;
      ctx.fillStyle = (up ? chr(true) : chr(false)) + "44";
      ctx.fillRect(x - candleW / 2, volTop + volHeight - h, Math.max(1, candleW), h);
    }
    // Vol axis
    ctx.fillStyle = "#52525b";
    ctx.font = "9px monospace";
    ctx.textAlign = "right";
    ctx.fillText(maxV.toLocaleString(), padLeft - 4, volTop + 10);

    // Time labels
    if (n > 0) {
      ctx.textAlign = "center";
      const showEvery = Math.max(1, Math.floor(n / 8));
      for (let i = 0; i < n; i += showEvery) {
        const d = new Date(candles[i].t * 1000);
        const label = d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
        ctx.fillText(label, xScale(candles[i].t), H - padBottom + 12);
      }
    }

    // Crosshair
    const crossX = n > 0 ? xScale(candles[n - 1].t) : padLeft;
    ctx.strokeStyle = "#6366f1";
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(crossX, padTop); ctx.lineTo(crossX, chartH + padTop); ctx.stroke();
    if (n > 0) {
      const last = candles[n - 1];
      ctx.fillStyle = "#6366f1";
      ctx.font = "10px monospace";
      ctx.textAlign = "left";
      ctx.fillText(`O:${last.o.toFixed(2)} H:${last.h.toFixed(2)} L:${last.l.toFixed(2)} C:${last.c.toFixed(2)} V:${last.v.toLocaleString()}`, padLeft + 4, padTop + chartH / 2 - 10);
    }
  }, []);

  const fetchAndDraw = useCallback(async (sym: string, intv: string) => {
    setState("load"); setErr(""); setInfo(`Loading ${sym} ${intv}...`);
    try {
      const H = hdr();
      const days = ["1D","1W","1M"].includes(intv) ? 365 : 7;
      // Fetch quote
      const qr = await fetch(`/api/chart/${sym}/quote`, { headers: H, signal: AbortSignal.timeout(5000) });
      if (qr.ok) {
        const q = await qr.json();
        setInfo(`${sym} NSE ${fmtPrice(q.last_price)} ${q.change>=0?"+":""}${q.change?.toFixed(2)} (${q.change_pct?.toFixed(2)}%) | O:${q.open?.toFixed(2)} H:${q.high?.toFixed(2)} L:${q.low?.toFixed(2)}`);
      }
      // Fetch candles
      const cr = await fetch(`/api/chart/${sym}/candles?interval=${intv}&days=${days}`, { headers: H, signal: AbortSignal.timeout(20000) });
      if (!cr.ok) throw new Error(`Candles API returned ${cr.status}`);
      const cd = await cr.json();
      const raw = cd.candles || [];
      if (!Array.isArray(raw) || raw.length < 2) {
        setErr(`No data for ${sym} at ${intv}`);
        setState("err"); return;
      }
      renderChart(raw);
      setState("ok");
    } catch (e: any) {
      setErr(e.name === "TimeoutError" ? "Request timed out" : (e.message || "Failed to load chart"));
      setState("err");
    }
  }, [hdr, renderChart]);

  useEffect(() => { if (symbol) fetchAndDraw(symbol, interval); }, [symbol, interval, fetchAndDraw]);

  // Resize
  useEffect(() => {
    const obs = new ResizeObserver(() => { if (state === "ok" && canvasRef.current) { /* re-render will be triggered by fetchAndDraw */ } });
    const el = containerRef.current;
    if (el) obs.observe(el);
    return () => obs.disconnect();
  }, [state]);

  // Pine
  const [showPine, setPine] = useState(false);
  const [pineScript, setPineScript] = useState(`indicator("EMA Cross")\n\nfast = ema(close, 20)\nslow = ema(close, 50)\n\nplot(fast)\nplot(slow)`);
  const [pineRunning, setPineRunning] = useState(false);
  const [pineMsg, setPineMsg] = useState("");
  const runPine = async () => {
    setPineRunning(true); setPineMsg("");
    try {
      const r = await fetch("/api/pine/run", { method: "POST", headers: { ...hdr(), "Content-Type": "application/json" }, body: JSON.stringify({ symbol, script: pineScript, interval, days: 500 }) });
      const d = await r.json();
      setPineMsg(d.success ? `${d.strategy_name||"Script"} — ${d.plots?.length||0} plots` : (d.errors||["Error"]).join("\n"));
    } catch (e: any) { setPineMsg(e.message); }
    setPineRunning(false);
  };

  // News
  const [showNews, setNews] = useState(false);
  const [newsData, setNewsData] = useState<any>(null);
  useEffect(() => {
    if (!showNews) return;
    fetch(`/api/news/company/${symbol}?page=1&page_size=10`, { headers: hdr() }).then(r => r.json()).then(d => setNewsData(d)).catch(() => {});
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
      if (!pfs.length) { setTMsg("Create a portfolio first"); return; }
      const price = parseFloat(prc) || 0;
      const n = parseInt(qty) || 1;
      if (side === "BUY") await api.buy(pfs[0].id, symbol, n, price);
      else await api.sell(pfs[0].id, symbol, n, price);
      setTMsg(`${side} ${symbol} x${n} @ \u20B9${price} \u2713`);
    } catch (e: any) { setTMsg(e.message); }
  };

  return (
    <div className="h-screen flex flex-col bg-[#0a0a14] overflow-hidden">
      {/* Top bar */}
      <div className="h-9 bg-[#13131a] border-b border-[#1a1a2e] flex items-center px-3 gap-2 flex-shrink-0">
        <button onClick={() => router.push("/markets")} className="text-gray-400 hover:text-white p-0.5"><ChevronLeft size={14} /></button>
        <span className="text-[11px] text-gray-300 font-mono truncate flex-1">{info || symbol}</span>
        <div className="flex gap-0.5">
          {INTERVALS.map(iv => <button key={iv} onClick={() => setInt(iv)} className={`px-1.5 py-0.5 text-[10px] rounded-sm ${interval===iv?"bg-indigo-900/40 text-indigo-300":"text-gray-600 hover:text-gray-400"}`}>{iv}</button>)}
        </div>
        <div className="flex gap-1 ml-2 border-l border-[#1a1a2e] pl-2">
          <button onClick={() => setPine(!showPine)} className={`p-0.5 rounded ${showPine?"text-indigo-400":"text-gray-600 hover:text-gray-400"}`} title="Pine"><SquareCode size={12} /></button>
          <button onClick={() => setNews(!showNews)} className={`p-0.5 rounded ${showNews?"text-indigo-400":"text-gray-600 hover:text-gray-400"}`} title="News"><Newspaper size={12} /></button>
          <button onClick={() => setTrade(!showTrade)} className={`p-0.5 rounded ${showTrade?"text-indigo-400":"text-gray-600 hover:text-gray-400"}`} title="Trade"><ShoppingCart size={12} /></button>
          <button onClick={() => fetchAndDraw(symbol, interval)} className="p-0.5 rounded text-gray-600 hover:text-gray-400" title="Refresh"><RefreshCw size={12} /></button>
          <button onClick={() => document.documentElement.requestFullscreen?.()} className="p-0.5 rounded text-gray-600 hover:text-gray-400" title="Fullscreen"><Maximize size={12} /></button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Stock sidebar */}
        <div className="w-12 bg-[#13131a] border-r border-[#1a1a2e] overflow-y-auto flex-shrink-0">
          {STOCKS.map(s => <button key={s} onClick={() => router.push(`/chart/${s}`)} className={`w-full py-1 text-[9px] font-medium ${s===symbol?"text-indigo-400 bg-indigo-900/20":"text-gray-600 hover:text-gray-400 hover:bg-[#1a1a2e]"}`}>{s}</button>)}
        </div>

        {/* Chart area */}
        <div className="flex-1 flex flex-col min-w-0">
          {state === "load" && <div className="flex-1 flex items-center justify-center"><div className="animate-spin h-5 w-5 border-2 border-indigo-500 border-t-transparent rounded-full" /></div>}
          {state === "err" && <div className="flex-1 flex items-center justify-center"><div className="text-center"><p className="text-red-400 text-xs mb-2">{err}</p><button onClick={() => fetchAndDraw(symbol, interval)} className="px-3 py-1 bg-indigo-600 text-white text-xs rounded">Retry</button></div></div>}
          {state === "ok" && <div ref={containerRef} className="flex-1 relative"><canvas ref={canvasRef} className="absolute inset-0 w-full h-full" /></div>}

          {showPine && <div className="h-40 bg-[#13131a] border-t border-[#1a1a2e] flex flex-col flex-shrink-0">
            <div className="flex items-center justify-between px-2 py-1 border-b border-[#1a1a2e]">
              <span className="text-[10px] text-gray-300 font-semibold">Pine Script</span>
              <div className="flex gap-1">
                <button onClick={runPine} disabled={pineRunning} className="px-2 py-0.5 bg-indigo-600 text-white rounded text-[10px]">{pineRunning?"Running":"Run"}</button>
                <button onClick={() => setPine(false)} className="text-gray-600 hover:text-gray-300"><X size={12} /></button>
              </div>
            </div>
            <textarea value={pineScript} onChange={e => setPineScript(e.target.value)} className="flex-1 bg-[#0a0a14] text-[10px] font-mono p-2 resize-none outline-none text-[#c9d1d9]" spellCheck={false} />
            {pineMsg && <div className={`px-2 py-1 text-[10px] font-mono border-t ${pineMsg.includes("Error")||pineMsg.includes("rror")?"bg-red-950/50 text-red-300 border-red-900/50":"bg-emerald-950/50 text-emerald-300 border-emerald-900/50"}`}>{pineMsg}</div>}
          </div>}
        </div>

        {/* Right panel */}
        {(showNews || showTrade) && <div className="w-44 bg-[#13131a] border-l border-[#1a1a2e] overflow-y-auto flex-shrink-0 text-[10px]">
          {showNews && <div className="p-2">
            <h3 className="font-semibold text-gray-400 mb-1">Company News</h3>
            {newsData?.items?.length > 0 ? newsData.items.slice(0, 15).map((a: any, i: number) => <a key={i} href={a.url||"#"} target="_blank" rel="noopener" className="block p-1 rounded bg-[#0a0a14] hover:bg-[#1a1a2e] mb-1"><p className="leading-snug line-clamp-2 text-gray-300">{a.headline}</p><p className="text-[9px] text-gray-600 mt-0.5">{a.source}</p></a>) : <p className="text-gray-600 text-center py-4">Set MARKETAUX_API_KEY<br/>for Indian stock news</p>}
          </div>}
          {showTrade && <div className="p-2">
            <h3 className="font-semibold text-gray-400 mb-1">Trade</h3>
            <div className="flex gap-0.5 mb-1">
              <button onClick={() => setSide("BUY")} className={`flex-1 py-0.5 rounded text-[10px] ${side==="BUY"?"bg-green-900/40 text-green-400":"bg-[#0a0a14] text-gray-600"}`}>BUY</button>
              <button onClick={() => setSide("SELL")} className={`flex-1 py-0.5 rounded text-[10px] ${side==="SELL"?"bg-red-900/40 text-red-400":"bg-[#0a0a14] text-gray-600"}`}>SELL</button>
            </div>
            <input type="number" value={qty} onChange={e => setQty(e.target.value)} placeholder="Qty" className="w-full px-1.5 py-0.5 bg-[#0a0a14] border border-[#1a1a2e] rounded text-gray-300 mb-0.5" />
            <input type="number" value={prc} onChange={e => setPrc(e.target.value)} placeholder="Price" className="w-full px-1.5 py-0.5 bg-[#0a0a14] border border-[#1a1a2e] rounded text-gray-300 mb-0.5" />
            <button onClick={doTrade} className={`w-full py-0.5 rounded text-[10px] font-medium ${side==="BUY"?"bg-green-900/30 text-green-400":"bg-red-900/30 text-red-400"}`}>{side}</button>
            {tMsg && <p className={`mt-0.5 ${tMsg.includes("✓")||tMsg.includes("\u2713")?"text-green-400":"text-red-400"}`}>{tMsg}</p>}
          </div>}
        </div>}
      </div>
    </div>
  );
}
