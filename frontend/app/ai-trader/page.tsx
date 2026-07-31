"use client";
import { useState } from "react";
import { Activity, Zap, Shield, AlertTriangle } from "lucide-react";

interface ScanResult {
  symbol: string;
  last_price: number;
  strategies: Record<string, { direction: string; score: number; reason: string }>;
  risk?: {
    entry_price: number;
    stop_loss: number;
    take_profit: number;
    quantity: number;
    risk_amount: number;
    capital: number;
  };
}

export default function AITraderPage() {
  const [scanSymbol, setScanSymbol] = useState("");
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [scanLoading, setScanLoading] = useState(false);
  const [error, setError] = useState("");

  const handleScan = async () => {
    if (!scanSymbol) return;
    setScanLoading(true); setError("");
    const token = localStorage.getItem("access_token");
    try {
      const resp = await fetch(`/api/ai-trader/scan?symbol=${scanSymbol.toUpperCase()}`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Unable to run market scan");
      setScanResult(data as ScanResult);
    } catch (err: unknown) { setError(err instanceof Error ? err.message : "Unable to run market scan"); }
    setScanLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">AI Trader</h1>
          <span className="text-xs bg-warning/20 text-warning border border-warning/30 rounded-full px-3 py-1 font-medium">PAPER MODE</span>
        </div>
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-muted" />
          <span className="text-sm text-muted">Monitoring · 6 strategies</span>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-xl p-5">
        <h3 className="font-semibold mb-3 flex items-center gap-2"><Zap size={18} />Market Scan</h3>
        <div className="flex gap-2">
          <input type="text" value={scanSymbol} onChange={(e) => setScanSymbol(e.target.value.toUpperCase())}
            placeholder="Symbol (e.g., TCS)" className="px-3 py-2 bg-background border border-border rounded-lg text-sm w-40" />
          <button onClick={handleScan} disabled={scanLoading} className="px-6 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">
            {scanLoading ? "Scanning..." : "Scan"}
          </button>
        </div>
        {error && <p className="text-danger text-sm mt-2">{error}</p>}
        {scanResult && (
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-3">
              <span className="font-bold text-lg">{scanResult.symbol}</span>
              <span className="tabular-nums text-lg">₹{scanResult.last_price}</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {Object.entries(scanResult.strategies).map(([name, s]) => (
                <div key={name} className={`bg-background border rounded-lg p-3 ${s.direction === "BUY" ? "border-success/30" : s.direction === "SELL" ? "border-danger/30" : "border-border"}`}>
                  <p className="text-xs text-muted capitalize">{name.replace(/_/g, " ")}</p>
                  <p className={`font-bold text-sm ${s.direction === "BUY" ? "text-success" : s.direction === "SELL" ? "text-danger" : "text-muted"}`}>{s.direction}</p>
                  <p className="text-xs text-muted">Score: {(s.score * 100).toFixed(0)}%</p>
                </div>
              ))}
            </div>
            {scanResult.risk && (
              <div className="bg-background border border-border rounded-lg p-4 text-sm space-y-1">
                <p><span className="text-muted">Entry:</span> ₹{scanResult.risk.entry_price}</p>
                <p><span className="text-muted">Stop Loss:</span> <span className="text-danger">₹{scanResult.risk.stop_loss}</span></p>
                <p><span className="text-muted">Take Profit:</span> <span className="text-success">₹{scanResult.risk.take_profit}</span></p>
                <p><span className="text-muted">Suggested Qty:</span> {scanResult.risk.quantity}</p>
                <p><span className="text-muted">Risk Amount:</span> ₹{scanResult.risk.risk_amount}</p>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[
          { name: "Momentum Breakout", key: "momentum", desc: "MACD + RSI + SMA20" },
          { name: "BB Breakout", key: "breakout", desc: "Bollinger Bands + Volume" },
          { name: "Trend Following", key: "trend_follow", desc: "SMA20 vs SMA50" },
          { name: "Mean Reversion", key: "mean_reversion", desc: "RSI oversold/overbought" },
          { name: "EMA Crossover", key: "ma_crossover", desc: "EMA20 vs EMA50" },
          { name: "Volume Surge", key: "volume_surge", desc: "Volume &gt; 1.5x average" },
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
