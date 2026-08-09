"use client";
import { useState, useEffect, useCallback } from "react";
import { Activity, Zap, Shield, AlertTriangle, Brain, TrendingUp, TrendingDown, RotateCw, Play, Pause, StopCircle, Check, X, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import type { Portfolio, PortfolioSummary } from "@/types";

interface AIAnalysis {
  symbol: string;
  name: string;
  exchange: string;
  decision: string;
  confidence: number;
  summary: string;
  strategy: string;
  entry: number;
  stop_loss: number;
  take_profit: number;
  position_size: number;
  risk_reward: number;
  time_horizon: string;
  reasoning: string;
  technical_reasons: string[];
  fundamental_reasons: string[];
  news_reasons: string[];
  market_context: string;
  risks: string[];
  is_fallback: boolean;
  last_price: number;
}

interface TradeDecision {
  id: number;
  symbol: string;
  direction: string;
  decision: string;
  ltp: number;
  quantity: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  reasoning: string;
  risk_score: number;
  market_regime: string;
  timestamp: string;
}

interface StrategyScan {
  [key: string]: { direction: string; score: number; reason: string };
}

interface ScanResult {
  symbol: string;
  last_price: number;
  strategies: StrategyScan;
  risk: {
    entry_price: number; stop_loss: number; take_profit: number;
    quantity: number; risk_amount: number; capital: number;
    existing_position: boolean; existing_quantity: number;
  };
}

export default function AITraderPage() {
  const [activeTab, setActiveTab] = useState<"scanner" | "analysis" | "positions" | "history">("scanner");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Scanner
  const [scanSymbol, setScanSymbol] = useState("");
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [scanLoading, setScanLoading] = useState(false);

  // Gemini AI
  const [aiSymbol, setAiSymbol] = useState("");
  const [aiResult, setAiResult] = useState<AIAnalysis | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  // Decisions
  const [decisions, setDecisions] = useState<TradeDecision[]>([]);

  // Portfolio
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);

  useEffect(() => {
    loadContext();
  }, []);

  const loadContext = async () => {
    try {
      const pfs = await api.listPortfolios();
      if (pfs.length > 0) {
        const summary = await api.getPortfolio(pfs[0].id);
        setPortfolio(summary);
      }
      const decs = await fetchWithAuth("/api/ai-trader/decisions?limit=20");
      setDecisions(Array.isArray(decs) ? decs : []);
    } catch {}
  };

  const fetchWithAuth = async (url: string) => {
    const token = localStorage.getItem("access_token");
    const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    return res.json();
  };

  const handleScan = async () => {
    if (!scanSymbol) return;
    setScanLoading(true); setError("");
    const token = localStorage.getItem("access_token");
    try {
      const resp = await fetch(`/api/ai-trader/scan?symbol=${scanSymbol.toUpperCase()}`, {
        method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Scan failed");
      setScanResult(data);
    } catch (err: any) { setError(err.message); }
    setScanLoading(false);
  };

  const handleAiAnalyze = async () => {
    if (!aiSymbol) return;
    setAiLoading(true); setError("");
    const token = localStorage.getItem("access_token");
    try {
      const resp = await fetch(`/api/ai/analyze`, {
        method: "POST", headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ symbol: aiSymbol.toUpperCase() }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "AI analysis failed");
      setAiResult(data);
    } catch (err: any) { setError(err.message); }
    setAiLoading(false);
  };

  const handleExecute = async (direction: string, symbol: string, price: number, qty: number, strategy: string, reasoning: string) => {
    const token = localStorage.getItem("access_token");
    try {
      const resp = await fetch("/api/ai-trader/execute", {
        method: "POST", headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ symbol, direction, price, quantity: qty, strategy, reasoning }),
      });
      const data = await resp.json();
      if (data.decision === "EXECUTED") {
        setError(`✓ ${direction} ${symbol} x${qty} @ ₹${price} executed`);
        loadContext();
      } else {
        setError(`✗ ${data.reason || "Rejected"}`);
      }
    } catch (err: any) { setError(err.message); }
  };

  const SignalIcon = ({ direction }: { direction: string }) =>
    direction === "BUY" ? <TrendingUp size={16} className="text-success" /> :
    direction === "SELL" ? <TrendingDown size={16} className="text-danger" /> :
    <Activity size={16} className="text-warning" />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">AI Trader</h1>
          <span className="text-xs bg-warning/20 text-warning border border-warning/30 rounded-full px-3 py-1 font-medium">PAPER MODE</span>
        </div>
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-primary" />
          <span className="text-sm text-muted">{aiResult?.is_fallback === false ? "Gemini AI Active" : "Rule-based Mode"}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-border">
        {[
          { id: "scanner", label: "Strategy Scanner" },
          { id: "analysis", label: "Gemini AI Analysis" },
          { id: "history", label: "Trade History" },
        ].map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id as typeof activeTab)}
            className={`pb-2 text-sm font-medium ${activeTab === t.id ? "text-primary border-b-2 border-primary" : "text-muted hover:text-foreground"}`}>{t.label}</button>
        ))}
      </div>

      {error && <div className={`bg-surface border ${error.startsWith("✓") ? "border-success/30" : "border-danger/30"} rounded-xl p-3`}><p className={`text-sm ${error.startsWith("✓") ? "text-success" : "text-danger"}`}>{error}</p></div>}

      {/* STRATEGY SCANNER */}
      {activeTab === "scanner" && (
        <div className="space-y-4">
          <div className="bg-surface border border-border rounded-xl p-5">
            <h3 className="font-semibold mb-3 flex items-center gap-2"><Zap size={18} />Strategy Scanner</h3>
            <div className="flex gap-2">
              <input type="text" value={scanSymbol} onChange={(e) => setScanSymbol(e.target.value.toUpperCase())}
                placeholder="Symbol (e.g., TCS)" className="px-3 py-2 bg-background border border-border rounded-lg text-sm w-40" />
              <button onClick={handleScan} disabled={scanLoading} className="px-6 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">
                {scanLoading ? "Scanning..." : "Scan All Strategies"}
              </button>
            </div>
            {scanResult && <ScanResults result={scanResult} onExecute={handleExecute} />}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { name: "Momentum Breakout", key: "momentum", desc: "MACD + RSI + SMA20" },
              { name: "BB Breakout", key: "breakout", desc: "Bollinger Bands + Volume" },
              { name: "Trend Following", key: "trend_follow", desc: "SMA20 vs SMA50" },
              { name: "Mean Reversion", key: "mean_reversion", desc: "RSI oversold/overbought" },
              { name: "EMA Crossover", key: "ma_crossover", desc: "EMA20 vs EMA50" },
              { name: "Volume Surge", key: "volume_surge", desc: "Volume > 1.5x average" },
            ].map((s) => (
              <div key={s.key} className="bg-surface border border-border rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Shield size={16} className="text-primary" /><h4 className="font-semibold text-sm">{s.name}</h4>
                </div>
                <p className="text-xs text-muted mb-2">{s.desc}</p>
                <span className="text-xs px-2 py-0.5 rounded bg-surface-hover text-muted">PAPER · 1D</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* GEMINI AI ANALYSIS */}
      {activeTab === "analysis" && (
        <div className="space-y-4">
          <div className="bg-surface border border-border rounded-xl p-5">
            <h3 className="font-semibold mb-3 flex items-center gap-2"><Brain size={18} className="text-primary" />Gemini AI Market Intelligence</h3>
            <div className="flex gap-2">
              <input type="text" value={aiSymbol} onChange={(e) => setAiSymbol(e.target.value.toUpperCase())}
                placeholder="Symbol (e.g., RELIANCE)" className="px-3 py-2 bg-background border border-border rounded-lg text-sm w-40" />
              <button onClick={handleAiAnalyze} disabled={aiLoading} className="px-6 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">
                {aiLoading ? "Analyzing..." : "Analyze with Gemini"}
              </button>
            </div>
            {aiResult && (
              <div className="mt-4 space-y-4">
                <div className="flex items-center gap-3">
                  <div className={`text-2xl font-bold ${aiResult.decision === "BUY" ? "text-success" : aiResult.decision === "SELL" ? "text-danger" : "text-warning"}`}>
                    <div className="flex items-center gap-2"><SignalIcon direction={aiResult.decision} />{aiResult.decision}</div>
                  </div>
                  <div className="text-sm text-muted">
                    <span className="font-bold">{aiResult.confidence}%</span> confidence · {aiResult.strategy} · {aiResult.time_horizon}
                  </div>
                  {aiResult.is_fallback && <span className="text-xs bg-warning/20 text-warning px-2 py-0.5 rounded">RULE-BASED</span>}
                </div>

                <p className="text-sm">{aiResult.summary}</p>

                {/* Price levels */}
                <div className="grid grid-cols-5 gap-3">
                  <div className="bg-background border border-border rounded-lg p-3 text-center">
                    <p className="text-xs text-muted">Entry</p><p className="font-bold tabular-nums">₹{aiResult.entry}</p></div>
                  <div className="bg-background border border-border rounded-lg p-3 text-center">
                    <p className="text-xs text-muted">Stop Loss</p><p className="font-bold tabular-nums text-danger">₹{aiResult.stop_loss}</p></div>
                  <div className="bg-background border border-border rounded-lg p-3 text-center">
                    <p className="text-xs text-muted">Take Profit</p><p className="font-bold tabular-nums text-success">₹{aiResult.take_profit}</p></div>
                  <div className="bg-background border border-border rounded-lg p-3 text-center">
                    <p className="text-xs text-muted">Position</p><p className="font-bold tabular-nums">{aiResult.position_size}</p></div>
                  <div className="bg-background border border-border rounded-lg p-3 text-center">
                    <p className="text-xs text-muted">Risk/Reward</p><p className="font-bold tabular-nums">1:{aiResult.risk_reward}</p></div>
                </div>

                {/* Reasoning */}
                <div className="bg-background border border-border rounded-lg p-4">
                  <h4 className="text-sm font-semibold mb-2">Reasoning</h4>
                  <p className="text-sm text-muted mb-3">{aiResult.reasoning}</p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {aiResult.technical_reasons.length > 0 && (
                      <div><p className="text-xs font-medium text-primary mb-1">Technical</p>
                        <ul className="text-xs text-muted space-y-1">{aiResult.technical_reasons.map((r, i) => <li key={i}>• {r}</li>)}</ul></div>
                    )}
                    {aiResult.fundamental_reasons.length > 0 && (
                      <div><p className="text-xs font-medium text-primary mb-1">Fundamental</p>
                        <ul className="text-xs text-muted space-y-1">{aiResult.fundamental_reasons.map((r, i) => <li key={i}>• {r}</li>)}</ul></div>
                    )}
                    {aiResult.news_reasons.length > 0 && (
                      <div><p className="text-xs font-medium text-primary mb-1">News</p>
                        <ul className="text-xs text-muted space-y-1">{aiResult.news_reasons.map((r, i) => <li key={i}>• {r}</li>)}</ul></div>
                    )}
                  </div>
                </div>

                {/* Risks */}
                <div className="bg-background border border-warning/30 rounded-lg p-4">
                  <h4 className="text-sm font-semibold mb-2 flex items-center gap-2"><AlertTriangle size={14} className="text-warning" />Risks & Invalidating Conditions</h4>
                  <ul className="text-xs text-muted space-y-1">{aiResult.risks?.map((r, i) => <li key={i}>• {r}</li>)}</ul>
                </div>

                {/* Execute */}
                {aiResult.decision !== "HOLD" && (
                  <button onClick={() => handleExecute(aiResult.decision, aiResult.symbol, aiResult.entry, aiResult.position_size, aiResult.strategy, aiResult.reasoning)}
                    className={`w-full py-2 rounded-lg font-medium text-sm ${aiResult.decision === "BUY" ? "bg-success/20 text-success hover:bg-success/30" : "bg-danger/20 text-danger hover:bg-danger/30"}`}>
                    Execute {aiResult.decision} {aiResult.symbol} x{aiResult.position_size}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TRADE HISTORY */}
      {activeTab === "history" && (
        <div className="space-y-4">
          <h3 className="font-semibold flex items-center gap-2"><Activity size={18} />Recent Trading Decisions</h3>
          {decisions.length === 0 ? (
            <div className="bg-surface border border-border rounded-xl p-12 text-center"><p className="text-muted">No trading decisions yet.</p></div>
          ) : (
            <div className="space-y-2">
              {decisions.map((d) => (
                <div key={d.id} className={`bg-surface border ${d.decision === "EXECUTED" ? "border-border" : d.decision === "REJECTED" ? "border-danger/30" : "border-warning/30"} rounded-xl p-4`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <SignalIcon direction={d.direction} />
                      <div>
                        <span className="font-semibold text-sm">{d.symbol}</span>
                        <span className={`ml-2 text-xs px-2 py-0.5 rounded ${d.decision === "EXECUTED" ? "bg-success/20 text-success" : d.decision === "REJECTED" ? "bg-danger/20 text-danger" : "bg-warning/20 text-warning"}`}>{d.decision}</span>
                      </div>
                    </div>
                    <div className="text-right text-sm">
                      {d.direction !== "HOLD" && <span className="tabular-nums font-medium">₹{d.ltp?.toFixed(2)} × {d.quantity}</span>}
                      {d.timestamp && <p className="text-xs text-muted">{new Date(d.timestamp).toLocaleString("en-IN")}</p>}
                    </div>
                  </div>
                  {d.reasoning && <p className="text-xs text-muted mt-2">{d.reasoning}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Risk Controls Footer */}
      <div className="bg-surface border border-warning/30 rounded-xl p-5">
        <h3 className="font-semibold mb-2 flex items-center gap-2"><AlertTriangle size={16} className="text-warning" />Risk Controls</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div><span className="text-muted">Max/Trade:</span> <span className="font-medium">1% risk</span></div>
          <div><span className="text-muted">Daily Loss:</span> <span className="font-medium">2% cap</span></div>
          <div><span className="text-muted">Max DD:</span> <span className="font-medium">15%</span></div>
          <div><span className="text-muted">Positions:</span> <span className="font-medium">3 max</span></div>
        </div>
      </div>
    </div>
  );
}

function ScanResults({ result, onExecute }: { result: ScanResult; onExecute: (dir: string, sym: string, price: number, qty: number, strat: string, reason: string) => void }) {
  const buyStrategies = Object.entries(result.strategies).filter(([, s]) => s.direction === "BUY");
  const sellStrategies = Object.entries(result.strategies).filter(([, s]) => s.direction === "SELL");

  return (
    <div className="mt-4 space-y-3">
      <div className="flex items-center gap-3">
        <span className="font-bold text-lg">{result.symbol}</span>
        <span className="tabular-nums text-lg">₹{result.last_price}</span>
        {result.risk?.existing_position && <span className="text-xs bg-warning/20 text-warning px-2 py-0.5 rounded">Position: {result.risk.existing_quantity}</span>}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Object.entries(result.strategies).map(([name, s]) => (
          <div key={name} className={`bg-background border rounded-lg p-3 ${s.direction === "BUY" ? "border-success/30" : s.direction === "SELL" ? "border-danger/30" : "border-border"}`}>
            <p className="text-xs text-muted capitalize">{name.replace(/_/g, " ")}</p>
            <p className={`font-bold text-sm ${s.direction === "BUY" ? "text-success" : s.direction === "SELL" ? "text-danger" : "text-muted"}`}>{s.direction}</p>
            <p className="text-xs text-muted">Score: {(s.score * 100).toFixed(0)}%</p>
          </div>
        ))}
      </div>

      {result.risk && (
        <div className="bg-background border border-border rounded-lg p-4 text-sm space-y-1">
          <div className="grid grid-cols-5 gap-3">
            <div><p className="text-xs text-muted">Entry</p><p className="font-bold">₹{result.risk.entry_price}</p></div>
            <div><p className="text-xs text-muted">Stop Loss</p><p className="font-bold text-danger">₹{result.risk.stop_loss}</p></div>
            <div><p className="text-xs text-muted">Take Profit</p><p className="font-bold text-success">₹{result.risk.take_profit}</p></div>
            <div><p className="text-xs text-muted">Qty</p><p className="font-bold">{result.risk.quantity}</p></div>
            <div><p className="text-xs text-muted">Risk</p><p className="font-bold">₹{result.risk.risk_amount}</p></div>
          </div>
        </div>
      )}

      {buyStrategies.length > 0 && (
        <button onClick={() => onExecute("BUY", result.symbol, result.risk?.entry_price || result.last_price, result.risk?.quantity || 1, "scanner", "Strategy scan recommended BUY")}
          className="w-full py-2 bg-success/20 text-success hover:bg-success/30 rounded-lg font-medium text-sm">Execute BUY</button>
      )}
    </div>
  );
}
