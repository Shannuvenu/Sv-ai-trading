"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { Instrument, BacktestResult } from "@/types";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("RELIANCE");
  const [capital, setCapital] = useState("100000");
  const [positionSize, setPositionSize] = useState("0.2");
  const [commission, setCommission] = useState("0.1");
  const [slippage, setSlippage] = useState("0.001");
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [search, setSearch] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { api.getInstruments().then(setInstruments).catch(() => {}); }, []);

  const filtered = instruments.filter((i) =>
    i.symbol.toLowerCase().includes(search.toLowerCase()) || i.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleRun = async () => {
    setLoading(true); setError(""); setShowDropdown(false); setResult(null);
    try {
      const res = await api.runBacktest({ symbol, initial_capital: parseFloat(capital), position_size_pct: parseFloat(positionSize), commission: parseFloat(commission), slippage: parseFloat(slippage) }, 252);
      setResult(res);
    } catch (err: unknown) { setError(err instanceof Error ? err.message : "Backtest failed"); }
    setLoading(false);
  };

  const rt = result;
  const trades = rt ? rt.trades : [];
  const eqCurve = rt ? rt.equity_curve : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Backtesting</h1>
        <span className="text-xs bg-surface border border-border rounded-full px-3 py-1 text-muted">UPSTOX DATA</span>
      </div>
      <div className="bg-surface border border-border rounded-xl p-5">
        <h3 className="font-semibold mb-4">Parameters</h3>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
          <div className="relative">
            <label className="text-xs text-muted">Symbol</label>
            <input type="text" value={search} placeholder={symbol} onFocus={() => setShowDropdown(true)} onBlur={() => setTimeout(() => setShowDropdown(false), 250)}
              onChange={(e) => { setSearch(e.target.value); setShowDropdown(true); }} className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm" />
            {showDropdown && filtered.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-surface border border-border rounded-lg max-h-40 overflow-auto shadow-lg">
                {filtered.map((inst) => (<button key={inst.id} onClick={() => { setSymbol(inst.symbol); setSearch(inst.symbol); setShowDropdown(false); }} className="w-full text-left px-3 py-2 hover:bg-surface-hover text-sm">{inst.symbol} — {inst.name}</button>))}
              </div>
            )}
          </div>
          <div><label className="text-xs text-muted">Capital (₹)</label><input type="number" value={capital} onChange={(e) => setCapital(e.target.value)} className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm" /></div>
          <div><label className="text-xs text-muted">Position %</label><input type="number" step="0.05" min="0.05" max="1" value={positionSize} onChange={(e) => setPositionSize(e.target.value)} className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm" /></div>
          <div><label className="text-xs text-muted">Commission %</label><input type="number" step="0.01" min="0" value={commission} onChange={(e) => setCommission(e.target.value)} className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm" /></div>
          <div><label className="text-xs text-muted">Slippage %</label><input type="number" step="0.001" min="0" value={slippage} onChange={(e) => setSlippage(e.target.value)} className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm" /></div>
        </div>
        <button onClick={handleRun} disabled={loading} className="w-full lg:w-auto px-8 py-2.5 bg-primary hover:bg-primary-hover rounded-lg font-medium text-sm disabled:opacity-50">{loading ? "Running..." : "Run Backtest"}</button>
      </div>
      {error && <div className="bg-surface border border-danger/30 rounded-xl p-4"><p className="text-danger text-sm">{error}</p></div>}
      {result && rt && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatBox label="Initial Capital" value={`₹${rt.initial_capital.toLocaleString("en-IN")}`} />
            <StatBox label="Final Equity" value={`₹${rt.final_equity.toLocaleString("en-IN")}`} />
            <StatBox label="Total Return" value={`₹${rt.total_return.toFixed(2)} (${rt.total_return_pct.toFixed(2)}%)`} color={rt.total_return >= 0 ? "text-success" : "text-danger"} />
            <StatBox label="Max Drawdown" value={`${rt.max_drawdown_pct.toFixed(2)}%`} color="text-danger" />
            <StatBox label="Win Rate" value={`${(rt.win_rate * 100).toFixed(1)}%`} />
            <StatBox label="Profit Factor" value={rt.profit_factor !== 0 ? rt.profit_factor.toFixed(2) : "N/A"} />
            <StatBox label="Sharpe" value={rt.sharpe_ratio != null ? rt.sharpe_ratio.toFixed(2) : "N/A"} />
            <StatBox label="Sortino" value={rt.sortino_ratio != null ? rt.sortino_ratio.toFixed(2) : "N/A"} />
            <StatBox label="Trades" value={`${rt.num_trades}`} />
            <StatBox label="Winning" value={`${rt.winning_trades}`} color="text-success" />
            <StatBox label="Losing" value={`${rt.losing_trades}`} color="text-danger" />
          </div>
          <div className="bg-surface border border-border rounded-xl p-5">
            <h3 className="font-semibold mb-3">Equity Curve</h3>
            {eqCurve.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={eqCurve}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 10, fill: "#71717a" }} tickFormatter={(v: string) => new Date(v).toLocaleDateString("en-IN", { month: "short" })} />
                  <YAxis tick={{ fontSize: 11, fill: "#71717a" }} />
                  <Tooltip contentStyle={{ background: "#13131a", border: "1px solid #1e1e2e", borderRadius: "8px" }} />
                  <Line type="monotone" dataKey="equity" stroke="#22c55e" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : <p className="text-muted text-center py-12">No equity curve data</p>}
          </div>
          {trades.length > 0 && (
            <div className="bg-surface border border-border rounded-xl p-5">
              <h3 className="font-semibold mb-3">Trade History</h3>
              <div className="grid grid-cols-5 gap-2 px-3 py-2 bg-surface-hover text-xs text-muted rounded"><div>Date</div><div>Side</div><div>Price</div><div>Qty</div><div>Value</div></div>
              <div className="max-h-60 overflow-auto">
                {trades.slice(0, 30).map((t, i) => {
                  const val = (t.cost || t.proceeds || 0);
                  return (
                  <div key={i} className="grid grid-cols-5 gap-2 px-3 py-2 border-t border-border text-sm">
                    <div className="text-xs text-muted">{new Date(t.timestamp).toLocaleDateString("en-IN")}</div>
                    <div className={t.side === "BUY" ? "text-success font-medium" : "text-danger font-medium"}>{t.side}</div>
                    <div className="tabular-nums">₹{t.price.toFixed(2)}</div>
                    <div className="tabular-nums">{t.quantity}</div>
                    <div className="text-muted tabular-nums">₹{val.toFixed(2)}</div>
                  </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function StatBox({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <p className="text-xs text-muted mb-1">{label}</p>
      <p className={`text-sm lg:text-base font-bold tabular-nums ${color || ""}`}>{value}</p>
    </div>
  );
}
