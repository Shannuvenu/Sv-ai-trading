"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Plus } from "lucide-react";
import type { Portfolio, PortfolioSummary, Transaction } from "@/types";

export default function PortfolioPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createCash, setCreateCash] = useState("100000");
  const [tradeSymbol, setTradeSymbol] = useState("");
  const [tradeQty, setTradeQty] = useState("");
  const [tradePrice, setTradePrice] = useState("");
  const [tradeTab, setTradeTab] = useState<"BUY" | "SELL">("BUY");
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [activeTab, setActiveTab] = useState<"holdings" | "transactions">("holdings");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.listPortfolios().then((pfs) => {
      if (cancelled) return;
      setPortfolios(pfs);
      if (pfs.length > 0 && !selectedId) setSelectedId(pfs[0].id);
      setLoading(false);
    }).catch((e: unknown) => { if (!cancelled) { setPageError(e instanceof Error ? e.message : "Failed to load"); setLoading(false); } });
    return () => { cancelled = true; };
  }, [selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    Promise.all([api.getPortfolio(selectedId).catch(() => null), api.getTransactions(selectedId).catch(() => [])]).then(([s, txs]) => {
      if (s) setSummary(s);
      setTransactions(txs as Transaction[] || []);
    });
  }, [selectedId]);

  const handleCreatePF = async () => {
    if (!createName || !createCash) return;
    try {
      const pf = await api.createPortfolio(createName, parseFloat(createCash));
      setShowCreate(false); setCreateName(""); setCreateCash("100000"); setSelectedId(pf.id);
      const pfs = await api.listPortfolios(); setPortfolios(pfs);
    } catch (err: unknown) { setError(err instanceof Error ? err.message : "Failed to create"); }
  };

  const handleTrade = async () => {
    setError(""); setSuccessMsg("");
    if (!selectedId || !tradeSymbol || !tradeQty || !tradePrice) { setError("All fields required"); return; }
    try {
      const qty = parseInt(tradeQty); const price = parseFloat(tradePrice);
      if (qty <= 0 || price <= 0) { setError("Quantity and price must be positive"); return; }
      if (tradeTab === "BUY") await api.buy(selectedId, tradeSymbol, qty, price);
      else await api.sell(selectedId, tradeSymbol, qty, price);
      setSuccessMsg(`${tradeTab} order executed`);
      setTradeSymbol(""); setTradeQty(""); setTradePrice("");
      const [s, txs] = await Promise.all([api.getPortfolio(selectedId), api.getTransactions(selectedId)]);
      setSummary(s); setTransactions(txs);
    } catch (err: unknown) { setError(err instanceof Error ? err.message : "Trade failed"); }
  };

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  if (pageError) return <div className="text-center py-20"><p className="text-danger mb-2">Failed to load portfolios</p><p className="text-muted text-sm">{pageError}</p></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3"><h1 className="text-2xl font-bold">Portfolio</h1><span className="text-xs bg-warning/20 text-warning border border-warning/30 rounded-full px-3 py-1 font-medium">PAPER TRADING</span></div>
        <button onClick={() => setShowCreate(!showCreate)} className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium"><Plus size={16} /> New Portfolio</button>
      </div>
      {showCreate && (
        <div className="bg-surface border border-border rounded-xl p-4 flex gap-3 items-end">
          <div><label className="text-xs text-muted">Portfolio Name</label><input type="text" value={createName} onChange={(e) => setCreateName(e.target.value)} className="px-3 py-2 bg-background border border-border rounded-lg text-sm w-48" placeholder="My Portfolio" /></div>
          <div><label className="text-xs text-muted">Initial Cash (₹)</label><input type="number" value={createCash} onChange={(e) => setCreateCash(e.target.value)} className="px-3 py-2 bg-background border border-border rounded-lg text-sm w-36" /></div>
          <button onClick={handleCreatePF} className="px-4 py-2 bg-primary rounded-lg text-sm font-medium">Create</button>
          <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-muted text-sm">Cancel</button>
        </div>
      )}
      {portfolios.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {portfolios.map((pf) => (<button key={pf.id} onClick={() => { setSelectedId(pf.id); setError(""); setSuccessMsg(""); }} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${selectedId === pf.id ? "bg-primary/20 text-primary" : "bg-surface border border-border hover:bg-surface-hover"}`}>{pf.name}</button>))}
        </div>
      )}
      {error && <div className="bg-surface border border-danger/30 rounded-xl p-3"><p className="text-danger text-sm">{error}</p></div>}
      {successMsg && <div className="bg-surface border border-success/30 rounded-xl p-3"><p className="text-success text-sm">{successMsg}</p></div>}
      {summary && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <StatBox label="Cash" value={`₹${summary.cash_balance.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} />
            <StatBox label="Invested" value={`₹${summary.invested_cost.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} />
            <StatBox label="Mkt Value" value={`₹${summary.market_value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} />
            <StatBox label="Equity" value={`₹${summary.equity.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} color="text-primary" />
            <StatBox label="Unrealised P&L" value={`₹${summary.unrealised_pnl.toFixed(2)}`} color={summary.unrealised_pnl >= 0 ? "text-success" : "text-danger"} />
            <StatBox label="P&L %" value={`${summary.unrealised_pnl_pct.toFixed(2)}%`} color={summary.unrealised_pnl_pct >= 0 ? "text-success" : "text-danger"} />
          </div>
          <div className="bg-surface border border-border rounded-xl p-5">
            <h3 className="font-semibold mb-3 text-sm uppercase tracking-wide text-warning">Paper Trading — Execute Trade</h3>
            <div className="flex gap-2 mb-3">
              <button onClick={() => setTradeTab("BUY")} className={`px-4 py-1.5 rounded text-sm font-medium ${tradeTab === "BUY" ? "bg-success/20 text-success" : "bg-surface-hover"}`}>BUY</button>
              <button onClick={() => setTradeTab("SELL")} className={`px-4 py-1.5 rounded text-sm font-medium ${tradeTab === "SELL" ? "bg-danger/20 text-danger" : "bg-surface-hover"}`}>SELL</button>
            </div>
            <div className="flex gap-2 flex-wrap items-end">
              <div><label className="text-xs text-muted">Symbol</label><input type="text" value={tradeSymbol} onChange={(e) => setTradeSymbol(e.target.value.toUpperCase())} className="w-28 px-3 py-2 bg-background border border-border rounded-lg text-sm" placeholder="RELIANCE" /></div>
              <div><label className="text-xs text-muted">Quantity</label><input type="number" value={tradeQty} onChange={(e) => setTradeQty(e.target.value)} min="1" className="w-24 px-3 py-2 bg-background border border-border rounded-lg text-sm" /></div>
              <div><label className="text-xs text-muted">Price (₹)</label><input type="number" value={tradePrice} onChange={(e) => setTradePrice(e.target.value)} min="0.01" step="0.01" className="w-32 px-3 py-2 bg-background border border-border rounded-lg text-sm" /></div>
              <button onClick={handleTrade} className={`px-6 py-2 rounded-lg text-sm font-medium transition-colors ${tradeTab === "BUY" ? "bg-success hover:bg-green-600" : "bg-danger hover:bg-red-600"}`}>{tradeTab === "BUY" ? "Place BUY" : "Place SELL"}</button>
            </div>
          </div>
          <div className="flex gap-4 border-b border-border">
            <button onClick={() => setActiveTab("holdings")} className={`pb-2 text-sm font-medium transition-colors ${activeTab === "holdings" ? "text-primary border-b-2 border-primary" : "text-muted hover:text-foreground"}`}>Holdings ({summary.holdings.length})</button>
            <button onClick={() => setActiveTab("transactions")} className={`pb-2 text-sm font-medium transition-colors ${activeTab === "transactions" ? "text-primary border-b-2 border-primary" : "text-muted hover:text-foreground"}`}>Transactions ({transactions.length})</button>
          </div>
          {activeTab === "holdings" ? (
            summary.holdings.length === 0 ? (<p className="text-muted text-center py-8">No holdings. Use the trade form above to start paper trading.</p>) : (
              <div className="bg-surface border border-border rounded-xl overflow-x-auto">
                <div className="grid grid-cols-8 gap-2 px-4 py-3 bg-surface-hover text-xs text-muted font-medium min-w-[600px]"><div>Symbol</div><div>Qty</div><div>Avg Price</div><div>Current</div><div>Cost Basis</div><div>Mkt Value</div><div>P&L</div><div>P&L %</div></div>
                {summary.holdings.map((h) => (
                  <div key={h.id} className="grid grid-cols-8 gap-2 px-4 py-2.5 border-t border-border text-sm min-w-[600px]">
                    <div className="font-medium text-primary">{h.symbol}</div><div className="tabular-nums">{h.quantity}</div><div className="tabular-nums">₹{h.average_price?.toFixed(2)}</div><div className="tabular-nums">₹{h.current_price?.toFixed(2) || "—"}</div>
                    <div className="text-muted tabular-nums">₹{h.cost_basis?.toFixed(0) || "—"}</div><div className="tabular-nums">₹{h.market_value?.toFixed(0) || "—"}</div>
                    <div className={`tabular-nums ${(h.unrealised_pnl || 0) >= 0 ? "text-success" : "text-danger"}`}>{h.unrealised_pnl != null ? `${h.unrealised_pnl >= 0 ? "+" : ""}₹${Math.abs(h.unrealised_pnl).toFixed(2)}` : "—"}</div>
                    <div className={`tabular-nums ${(h.unrealised_pnl_pct || 0) >= 0 ? "text-success" : "text-danger"}`}>{h.unrealised_pnl_pct != null ? `${h.unrealised_pnl_pct >= 0 ? "+" : ""}${h.unrealised_pnl_pct.toFixed(2)}%` : "—"}</div>
                  </div>
                ))}
              </div>
            )
          ) : (
            transactions.length === 0 ? (<p className="text-muted text-center py-8">No transactions yet</p>) : (
              <div className="bg-surface border border-border rounded-xl overflow-x-auto">
                <div className="grid grid-cols-6 gap-2 px-4 py-3 bg-surface-hover text-xs text-muted font-medium min-w-[500px]"><div>Date</div><div>Symbol</div><div>Side</div><div>Qty</div><div>Price</div><div>Total</div></div>
                {transactions.map((t) => (
                  <div key={t.id} className="grid grid-cols-6 gap-2 px-4 py-2.5 border-t border-border text-sm min-w-[500px]">
                    <div className="text-muted text-xs">{new Date(t.executed_at).toLocaleDateString("en-IN")}</div><div className="font-medium">{t.symbol}</div>
                    <div className={t.side === "BUY" ? "text-success font-medium" : "text-danger font-medium"}>{t.side}</div><div className="tabular-nums">{t.quantity}</div>
                    <div className="tabular-nums">₹{t.price.toFixed(2)}</div><div className="text-muted tabular-nums">₹{t.total_value?.toFixed(2)}</div>
                  </div>
                ))}
              </div>
            )
          )}
        </>
      )}
      {portfolios.length === 0 && !loading && (
        <div className="text-center py-12"><p className="text-muted mb-3">Create your first paper trading portfolio</p><button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">Create Portfolio</button></div>
      )}
    </div>
  );
}

function StatBox({ label, value, color }: { label: string; value: string; color?: string }) {
  return (<div className="bg-surface border border-border rounded-xl p-4"><p className="text-xs text-muted mb-1">{label}</p><p className={`text-sm lg:text-base font-bold tabular-nums ${color || ""}`}>{value}</p></div>);
}
