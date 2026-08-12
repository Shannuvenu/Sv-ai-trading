"use client";
import { useState, useEffect, useCallback } from "react";
import { Activity, Zap, Shield, AlertTriangle, Brain, TrendingUp, TrendingDown, XCircle, CheckCircle, Wallet, BarChart3, History, DollarSign } from "lucide-react";
import { apiFetch } from "@/lib/apiClient";

function rfetch(url: string, opt: RequestInit = {}) {
  return apiFetch(url, opt);
}

const STRATEGIES = [
  { name: "Momentum Breakout", key: "momentum", desc: "MACD + RSI + SMA20" },
  { name: "BB Breakout", key: "breakout", desc: "Bollinger Bands + Volume" },
  { name: "Trend Following", key: "trend_follow", desc: "SMA20 vs SMA50" },
  { name: "Mean Reversion", key: "mean_reversion", desc: "RSI oversold/overbought" },
  { name: "EMA Crossover", key: "ma_crossover", desc: "EMA20 vs EMA50" },
  { name: "Volume Surge", key: "volume_surge", desc: "Volume > 1.5x average" },
];

interface PortfolioInfo { portfolio_id: number; portfolio_name: string; cash_balance: number; equity: number; }
interface ScanResult { symbol: string; last_price: number; strategies: Record<string, { direction: string; score: number; reason: string }>; risk: { entry_price: number; stop_loss: number; take_profit: number; quantity: number; risk_amount: number; capital: number; existing_position: boolean; existing_quantity: number; }; }
interface AIResult { symbol: string; decision: string; confidence: number; summary: string; strategy: string; entry: number; stop_loss: number; take_profit: number; position_size: number; risk_reward: number; time_horizon: string; reasoning: string; technical_reasons: string[]; fundamental_reasons: string[]; news_reasons: string[]; risks: string[]; is_fallback: boolean; last_price: number; }
interface Decision { id: number; symbol: string; direction: string; decision: string; ltp: number; quantity: number; entry_price: number; stop_loss: number; take_profit: number; reasoning: string; risk_score: number; timestamp: string; }
interface Position { symbol: string; quantity: number; average_price: number; ltp: number; invested: number; market_value: number; pnl: number; pnl_pct: number; }

export default function AITraderPage() {
  const [tab, setTab] = useState<"scanner"|"analysis"|"positions"|"history">("scanner");
  const [pfInfo, setPfInfo] = useState<PortfolioInfo | null>(null);
  const [scSymbol, setScSymbol] = useState("");
  const [scResult, setScResult] = useState<ScanResult | null>(null);
  const [scLoading, setScLoading] = useState(false);
  const [aiSymbol, setAiSymbol] = useState("");
  const [aiResult, setAiResult] = useState<AIResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ text: string; type: "ok"|"err" } | null>(null);
  const [executing, setExecuting] = useState(false);

  // Modal
  const [modal, setModal] = useState<{ side: string; sym: string; price: number; qty: number; strat: string; reason: string } | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [cfg, decs, pfs] = await Promise.all([
        rfetch("/api/ai-trader/config").then(r => r.ok ? r.json() : null),
        rfetch("/api/ai-trader/decisions?limit=30").then(r => r.ok ? r.json() : []),
        rfetch("/api/portfolio").then(r => r.ok ? r.json() : []),
      ]);
      if (cfg?.portfolio_id) setPfInfo(cfg);
      setDecisions(Array.isArray(decs) ? decs : []);
      if (Array.isArray(pfs) && pfs.length > 0) {
        const p = pfs[0];
        const s = await rfetch(`/api/portfolio/${p.id}`).then(r => r.ok ? r.json() : null);
        if (s) {
          setPositions((s.holdings || []).map((h: any) => ({
            symbol: h.symbol, quantity: h.quantity, average_price: Number(h.average_price),
            ltp: h.current_price || 0, invested: h.cost_basis || 0, market_value: h.market_value || 0,
            pnl: h.unrealised_pnl || 0, pnl_pct: h.unrealised_pnl_pct || 0,
          })));
          if (!pfInfo) setPfInfo({ portfolio_id: p.id, portfolio_name: p.portfolio?.name || "Paper Portfolio", cash_balance: s.cash_balance || 0, equity: s.equity || 0 });
        }
      }
    } catch {}
    setLoading(false);
  }, [pfInfo]);

  useEffect(() => { loadAll(); }, []);

  const doScan = async () => {
    if (!scSymbol) return;
    setScLoading(true); setScResult(null);
    const r = await rfetch(`/api/ai-trader/scan?symbol=${scSymbol.toUpperCase()}`, { method: "POST" });
    if (r.ok) setScResult(await r.json());
    else setMsg({ text: `Scan failed: ${await r.text().catch(() => r.statusText)}`, type: "err" });
    setScLoading(false);
  };

  const doAI = async () => {
    if (!aiSymbol) return;
    setAiLoading(true); setAiResult(null);
    const r = await rfetch("/api/ai/analyze", { method: "POST", body: JSON.stringify({ symbol: aiSymbol.toUpperCase() }) });
    if (r.ok) setAiResult(await r.json());
    else setMsg({ text: `AI failed: ${await r.text().catch(() => r.statusText)}`, type: "err" });
    setAiLoading(false);
  };

  const executeTrade = async (side: string, sym: string, price: number, qty: number, strat: string, reason: string) => {
    setExecuting(true); setMsg(null);
    try {
      const r = await rfetch("/api/ai-trader/execute", { method: "POST", body: JSON.stringify({ symbol: sym.toUpperCase(), direction: side, price, quantity: qty, strategy: strat, reasoning: reason }) });
      const d = await r.json();
      if (!r.ok) { setMsg({ text: d.detail || d.reason || `Order failed (${r.status})`, type: "err" }); setModal(null); return; }
      if (d.decision !== "EXECUTED") { setMsg({ text: `Rejected: ${d.reason || "Unknown reason"}`, type: "err" }); setModal(null); return; }
      setMsg({ text: `\u2713 ${side} ${sym} x${qty} @ \u20B9${price.toFixed(2)} | Txn #${d.transaction_id}`, type: "ok" });
      setModal(null);
      await loadAll();
    } catch (e: any) { setMsg({ text: e.message || "Execution error", type: "err" }); setModal(null); }
    setExecuting(false);
  };

  const signalIcon = (d: string) => d === "BUY" ? <TrendingUp size={14} className="text-green-400" /> : d === "SELL" ? <TrendingDown size={14} className="text-red-400" /> : <Activity size={14} className="text-yellow-400" />;

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">AI Trader</h1>
          <span className="text-xs bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 rounded-full px-3 py-1 font-medium">PAPER MODE</span>
        </div>
        {pfInfo && (
          <div className="flex items-center gap-4 text-xs">
            <span className="text-muted">{pfInfo.portfolio_name}</span>
            <span className="tabular-nums text-green-400 font-medium">\u20B9{pfInfo.cash_balance?.toLocaleString("en-IN", { maximumFractionDigits: 0 })} cash</span>
            <span className="tabular-nums text-muted">{positions.length} positions</span>
          </div>
        )}
      </div>

      {/* PORTFOLIO STRIP */}
      {pfInfo && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { label: "Available Cash", value: `\u20B9${pfInfo.cash_balance?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}` },
            { label: "Open Positions", value: positions.length },
            { label: "Invested", value: `\u20B9${positions.reduce((s,p) => s + p.invested, 0).toLocaleString("en-IN",{maximumFractionDigits:0})}` },
            { label: "Market Value", value: `\u20B9${positions.reduce((s,p) => s + p.market_value, 0).toLocaleString("en-IN",{maximumFractionDigits:0})}` },
            { label: "P&L", value: `\u20B9${positions.reduce((s,p) => s + p.pnl, 0).toLocaleString("en-IN",{maximumFractionDigits:0})}`, color: positions.reduce((s,p) => s + p.pnl, 0) >= 0 ? "text-green-400" : "text-red-400" },
          ].map((s, i) => <div key={i} className="bg-surface border border-border rounded-xl p-3"><p className="text-xs text-muted mb-0.5">{s.label}</p><p className={`text-sm font-bold tabular-nums ${s.color||""}`}>{s.value}</p></div>)}
        </div>
      )}

      {/* TOAST */}
      {msg && <div className={`bg-surface border rounded-xl p-3 flex items-center gap-2 ${msg.type==="ok"?"border-green-500/30":"border-red-500/30"}`}>
        {msg.type==="ok"?<CheckCircle size={16} className="text-green-400"/>:<XCircle size={16} className="text-red-400"/>}
        <span className={`text-sm ${msg.type==="ok"?"text-green-400":"text-red-400"}`}>{msg.text}</span>
        <button onClick={() => setMsg(null)} className="ml-auto text-muted hover:text-foreground text-xs">Dismiss</button>
      </div>}

      {/* TABS */}
      <div className="flex gap-4 border-b border-border">
        {[{id:"scanner",label:"Strategy Scanner"},{id:"analysis",label:"AI Analysis"},{id:"positions",label:"Positions"},{id:"history",label:"Trade History"}].map(t => (
          <button key={t.id} onClick={() => setTab(t.id as any)} className={`pb-2 text-sm font-medium ${tab===t.id?"text-primary border-b-2 border-primary":"text-muted hover:text-foreground"}`}>{t.label}</button>
        ))}
      </div>

      {/* SCANNER */}
      {tab === "scanner" && <div className="space-y-4">
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="flex gap-2 mb-3">
            <input value={scSymbol} onChange={e => setScSymbol(e.target.value.toUpperCase())} placeholder="Symbol (e.g. TCS)" className="px-3 py-2 bg-background border border-border rounded-lg text-sm w-40" />
            <button onClick={doScan} disabled={scLoading} className="px-6 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">{scLoading?"Scanning...":"Scan All Strategies"}</button>
            <button onClick={() => setScSymbol("")} className="px-2 text-xs text-muted hover:text-foreground">Clear</button>
          </div>
          {scResult && <>
            <div className="flex items-center gap-3 mb-3"><span className="font-bold text-lg">{scResult.symbol}</span><span className="tabular-nums text-lg">\u20B9{scResult.last_price}</span>{scResult.risk?.existing_position && <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded">Holding: {scResult.risk.existing_quantity}</span>}</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mb-3">
              {Object.entries(scResult.strategies).map(([k, s]) => (
                <div key={k} className={`bg-background border rounded-lg p-2.5 text-center ${s.direction==="BUY"?"border-green-500/30":s.direction==="SELL"?"border-red-500/30":"border-border"}`}>
                  <p className="text-[10px] text-muted capitalize">{k.replace(/_/g," ")}</p>
                  <p className={`text-sm font-bold ${s.direction==="BUY"?"text-green-400":s.direction==="SELL"?"text-red-400":"text-muted"}`}>{s.direction}</p>
                  <p className="text-[10px] text-muted">Score: {(s.score*100).toFixed(0)}%</p>
                </div>
              ))}
            </div>
            {scResult.risk && <div className="grid grid-cols-5 gap-2 bg-background border border-border rounded-lg p-3">
              {[["Entry",scResult.risk.entry_price],["Stop Loss",scResult.risk.stop_loss,"text-red-400"],["Take Profit",scResult.risk.take_profit,"text-green-400"],["Qty",scResult.risk.quantity],["Risk",scResult.risk.risk_amount]].map(([l,v,c]) => <div key={l as string} className="text-center"><p className="text-[10px] text-muted">{l}</p><p className={`text-sm font-bold tabular-nums ${c||""}`}>{typeof v==="number"?`\u20B9${v.toFixed(0)}`:v}</p></div>)}
            </div>}
            {Object.values(scResult.strategies).some(s => s.direction !== "HOLD") && <button onClick={() => setModal({side:Object.values(scResult.strategies).find(s=>s.direction==="BUY")?"BUY":"SELL",sym:scResult.symbol,price:scResult.risk?.entry_price||scResult.last_price,qty:scResult.risk?.quantity||1,strat:"scanner",reason:"Strategy signal"})} className="mt-3 w-full py-2 bg-green-900/20 text-green-400 hover:bg-green-900/30 rounded-lg font-medium text-sm">Execute Trade</button>}
          </>}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {STRATEGIES.map(s => <div key={s.key} className="bg-surface border border-border rounded-xl p-3"><div className="flex items-center gap-2 mb-1"><Shield size={14} className="text-primary"/><h4 className="font-semibold text-xs">{s.name}</h4></div><p className="text-[10px] text-muted mb-1.5">{s.desc}</p><span className="text-[10px] px-2 py-0.5 rounded bg-surface-hover text-muted">PAPER · 1D</span></div>)}
        </div>
      </div>}

      {/* AI ANALYSIS */}
      {tab === "analysis" && <div className="bg-surface border border-border rounded-xl p-5 space-y-4">
        <h3 className="font-semibold flex items-center gap-2"><Brain size={18} className="text-primary"/>Gemini AI Analysis</h3>
        <div className="flex gap-2">
          <input value={aiSymbol} onChange={e => setAiSymbol(e.target.value.toUpperCase())} placeholder="Symbol (e.g. TCS)" className="px-3 py-2 bg-background border border-border rounded-lg text-sm w-40" />
          <button onClick={doAI} disabled={aiLoading} className="px-6 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">{aiLoading?"Analyzing...":"Analyze with Gemini"}</button>
        </div>
        {aiResult && <>
          <div className="flex items-center gap-3"><div className={`text-xl font-bold flex items-center gap-2 ${aiResult.decision==="BUY"?"text-green-400":aiResult.decision==="SELL"?"text-red-400":"text-yellow-400"}`}>{signalIcon(aiResult.decision)}{aiResult.decision}</div><span className="text-sm text-muted">{aiResult.confidence}% confidence · {aiResult.strategy}</span>{aiResult.is_fallback && <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded">RULE-BASED</span>}</div>
          <div className="grid grid-cols-5 gap-3">
            <div className="bg-background border border-border rounded-lg p-2.5 text-center"><p className="text-xs text-muted">Entry</p><p className="font-bold">\u20B9{aiResult.entry}</p></div>
            <div className="bg-background border border-border rounded-lg p-2.5 text-center"><p className="text-xs text-muted">Stop Loss</p><p className="font-bold text-red-400">\u20B9{aiResult.stop_loss}</p></div>
            <div className="bg-background border border-border rounded-lg p-2.5 text-center"><p className="text-xs text-muted">Take Profit</p><p className="font-bold text-green-400">\u20B9{aiResult.take_profit}</p></div>
            <div className="bg-background border border-border rounded-lg p-2.5 text-center"><p className="text-xs text-muted">Position</p><p className="font-bold">{aiResult.position_size}</p></div>
            <div className="bg-background border border-border rounded-lg p-2.5 text-center"><p className="text-xs text-muted">Risk/Reward</p><p className="font-bold">1:{aiResult.risk_reward}</p></div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">{[
            { title: "Technical", items: aiResult.technical_reasons }, { title: "Fundamental", items: aiResult.fundamental_reasons }, { title: "News", items: aiResult.news_reasons }
          ].filter(r => r.items.length > 0).map(r => <div key={r.title} className="bg-background border border-border rounded-lg p-3"><p className="text-xs font-medium text-primary mb-1">{r.title}</p><ul className="text-xs text-muted space-y-0.5">{r.items.map((x,i) => <li key={i}>· {x}</li>)}</ul></div>)}</div>
          {aiResult.decision !== "HOLD" && <button onClick={() => setModal({side:aiResult.decision,sym:aiResult.symbol,price:aiResult.entry,qty:aiResult.position_size,strat:aiResult.strategy,reason:aiResult.reasoning})} className={`w-full py-2 rounded-lg font-medium text-sm ${aiResult.decision==="BUY"?"bg-green-900/20 text-green-400 hover:bg-green-900/30":"bg-red-900/20 text-red-400 hover:bg-red-900/30"}`}>Execute {aiResult.decision} {aiResult.symbol} x{aiResult.position_size}</button>}
        </>}
      </div>}

      {/* POSITIONS */}
      {tab === "positions" && <div className="bg-surface border border-border rounded-xl overflow-hidden">
        {positions.length === 0 ? <div className="p-12 text-center"><Wallet size={40} className="mx-auto text-muted mb-3"/><p className="text-muted">No open positions</p></div> :
        <table className="w-full text-sm"><thead><tr className="border-b border-border text-left text-xs text-muted"><th className="p-3">Symbol</th><th className="p-3 text-right">Qty</th><th className="p-3 text-right">Avg Price</th><th className="p-3 text-right">LTP</th><th className="p-3 text-right">Invested</th><th className="p-3 text-right">Value</th><th className="p-3 text-right">P&L</th><th className="p-3 text-right">P&L%</th><th className="p-3">Action</th></tr></thead>
        <tbody>{positions.map((p,i) => <tr key={i} className="border-b border-border hover:bg-surface-hover">
          <td className="p-3"><span className="text-primary font-medium">{p.symbol}</span></td>
          <td className="p-3 text-right tabular-nums">{p.quantity}</td>
          <td className="p-3 text-right tabular-nums">\u20B9{p.average_price.toFixed(2)}</td>
          <td className="p-3 text-right tabular-nums">\u20B9{p.ltp.toFixed(2)}</td>
          <td className="p-3 text-right tabular-nums">\u20B9{p.invested.toFixed(0)}</td>
          <td className="p-3 text-right tabular-nums">\u20B9{p.market_value.toFixed(0)}</td>
          <td className={`p-3 text-right tabular-nums font-medium ${p.pnl>=0?"text-green-400":"text-red-400"}`}>{p.pnl>=0?"+":""}\u20B9{p.pnl.toFixed(2)}</td>
          <td className={`p-3 text-right tabular-nums ${p.pnl_pct>=0?"text-green-400":"text-red-400"}`}>{p.pnl_pct>=0?"+":""}{p.pnl_pct.toFixed(2)}%</td>
          <td className="p-3"><button onClick={() => setModal({side:"SELL",sym:p.symbol,price:p.ltp,qty:p.quantity,strat:"manual",reason:"Close position"})} className="text-xs text-red-400 hover:underline">SELL</button></td>
        </tr>)}</tbody></table>}
      </div>}

      {/* TRADE HISTORY */}
      {tab === "history" && <div>
        {decisions.length === 0 ? <div className="bg-surface border border-border rounded-xl p-12 text-center"><History size={40} className="mx-auto text-muted mb-3"/><p className="text-muted">No trades yet. Execute one from Scanner or AI Analysis.</p></div> :
        <div className="space-y-2">{decisions.map(d => <div key={d.id} className={`bg-surface border rounded-xl p-4 ${d.decision==="EXECUTED"?"border-border":d.decision==="REJECTED"?"border-red-500/30":"border-yellow-500/30"}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">{signalIcon(d.direction)}<div><span className="font-semibold text-sm">{d.symbol}</span>
              <span className={`ml-2 text-xs px-2 py-0.5 rounded ${d.decision==="EXECUTED"?"bg-green-500/20 text-green-400":d.decision==="REJECTED"?"bg-red-500/20 text-red-400":"bg-yellow-500/20 text-yellow-400"}`}>{d.decision}</span></div></div>
            <div className="text-right text-sm"><span className="tabular-nums font-medium">\u20B9{d.ltp?.toFixed(2)} x {d.quantity}</span>{d.timestamp && <p className="text-xs text-muted">{new Date(d.timestamp).toLocaleString("en-IN")}</p>}</div>
          </div>
          {d.reasoning && <p className="text-xs text-muted mt-1">{d.reasoning}</p>}
        </div>)}</div>}
      </div>}

      {/* CONFIRMATION MODAL */}
      {modal && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setModal(null)}>
        <div className="bg-surface border border-border rounded-xl p-6 w-96 max-w-full mx-4" onClick={e => e.stopPropagation()}>
          <h3 className="font-bold text-lg mb-1">Confirm Paper Order</h3>
          <p className="text-xs text-yellow-400 mb-4">This is a PAPER TRADE. No real money is used.</p>
          <div className="space-y-2 text-sm mb-5">
            <div className="flex justify-between"><span className="text-muted">Direction</span><span className={`font-bold ${modal.side==="BUY"?"text-green-400":"text-red-400"}`}>{modal.side}</span></div>
            <div className="flex justify-between"><span className="text-muted">Symbol</span><span className="font-semibold">{modal.sym}</span></div>
            <div className="flex justify-between"><span className="text-muted">Quantity</span><span className="font-bold tabular-nums">{modal.qty}</span></div>
            <div className="flex justify-between"><span className="text-muted">Price</span><span className="font-bold tabular-nums">\u20B9{modal.price.toFixed(2)}</span></div>
            <div className="flex justify-between"><span className="text-muted">Order Value</span><span className="font-bold tabular-nums">\u20B9{(modal.price*modal.qty).toLocaleString("en-IN",{maximumFractionDigits:2})}</span></div>
            {pfInfo && <div className="flex justify-between"><span className="text-muted">Remaining Cash</span><span className="tabular-nums">\u20B9{(pfInfo.cash_balance - modal.price*modal.qty).toLocaleString("en-IN",{maximumFractionDigits:0})}</span></div>}
            <div className="flex justify-between"><span className="text-muted">Strategy</span><span className="text-xs">{modal.strat}</span></div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setModal(null)} className="flex-1 py-2 bg-surface-hover border border-border rounded-lg text-sm font-medium">Cancel</button>
            <button onClick={() => executeTrade(modal.side, modal.sym, modal.price, modal.qty, modal.strat, modal.reason)} disabled={executing} className={`flex-1 py-2 rounded-lg text-sm font-medium text-white ${modal.side==="BUY"?"bg-green-600 hover:bg-green-700":"bg-red-600 hover:bg-red-700"} disabled:opacity-50`}>{executing?"Executing...":`Confirm ${modal.side}`}</button>
          </div>
        </div>
      </div>}
    </div>
  );
}
