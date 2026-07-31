"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TrendingUp, Wallet, Star, ArrowRight, CircleDollarSign, Bot, Activity } from "lucide-react";
import Link from "next/link";
import type { PortfolioSummary, Watchlist, Quote } from "@/types";

export default function DashboardPage() {
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [pfs, wls] = await Promise.all([
          api.listPortfolios().then(p => Promise.all(p.map(pf => api.getPortfolio(pf.id).catch(() => null)))),
          api.listWatchlists(),
        ]);
        if (!cancelled) { setPortfolios(pfs.filter(Boolean) as PortfolioSummary[]); setWatchlists(wls); }

        // Load quotes for key symbols
        const syms = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN"];
        const qts = await Promise.all(syms.map(s => api.getQuote(s).catch(() => null)));
        const map: Record<string, Quote> = {};
        qts.forEach((q,i) => { if (q) map[syms[i]] = q; });
        if (!cancelled) setQuotes(map);
      } catch (e: unknown) { if (!cancelled) setError(e instanceof Error ? e.message : "Load failed"); }
      if (!cancelled) setLoading(false);
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;

  const totalEquity = portfolios.reduce((s, p) => s + (p?.equity || 0), 0);
  const totalCash = portfolios.reduce((s, p) => s + (p?.cash_balance || 0), 0);
  const totalPnl = portfolios.reduce((s, p) => s + (p?.unrealised_pnl || 0), 0);
  const allHoldings = portfolios.flatMap(p => p?.holdings || []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3"><h1 className="text-2xl font-bold">Dashboard</h1><span className="text-xs bg-warning/20 text-warning border border-warning/30 rounded-full px-3 py-1 font-medium">PAPER TRADING</span></div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard icon={CircleDollarSign} label="Equity" value={`₹${totalEquity.toLocaleString("en-IN",{maximumFractionDigits:0})}`} />
        <StatCard icon={Wallet} label="Cash" value={`₹${totalCash.toLocaleString("en-IN",{maximumFractionDigits:0})}`} />
        <StatCard icon={TrendingUp} label="P&L" value={`₹${totalPnl.toLocaleString("en-IN",{maximumFractionDigits:2})}`} color={totalPnl>=0?"text-success":"text-danger"} />
        <StatCard icon={Star} label="Watchlists" value={`${watchlists.length}`} />
        <StatCard icon={Bot} label="Portfolios" value={`${portfolios.length}`} />
        <StatCard icon={Activity} label="Holdings" value={`${allHoldings.length}`} />
      </div>

      {error && <div className="bg-surface border border-danger/30 rounded-xl p-3"><p className="text-danger text-sm">{error}</p></div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Watchlist + Market snapshot */}
        <div className="bg-surface border border-border rounded-xl p-5 lg:col-span-1">
          <div className="flex items-center justify-between mb-3"><h2 className="font-semibold">Market Snapshot</h2><Link href="/markets" className="text-xs text-primary hover:underline">Markets →</Link></div>
          <div className="space-y-2">
            {Object.entries(quotes).map(([sym, q]) => (
              <Link key={sym} href={`/markets/${sym}`} className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover transition-colors">
                <div><span className="font-medium text-sm text-primary">{sym}</span></div>
                <div className="text-right">
                  <div className="text-sm tabular-nums font-medium">₹{Number(q.last_price).toFixed(2)}</div>
                  <div className={`text-xs tabular-nums ${Number(q.change)>=0?"text-success":"text-danger"}`}>{Number(q.change)>=0?"+":""}{Number(q.change).toFixed(2)} ({Number(q.change_pct).toFixed(2)}%)</div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Portfolios */}
        <div className="bg-surface border border-border rounded-xl p-5 lg:col-span-1">
          <div className="flex items-center justify-between mb-3"><h2 className="font-semibold">Portfolios</h2><Link href="/portfolio" className="text-xs text-primary hover:underline">Manage →</Link></div>
          {portfolios.length===0?<EmptyState message="No portfolios" action="Create" href="/portfolio"/>:(
            <div className="space-y-2">{portfolios.map(pf=>(
              <Link key={pf.portfolio.id} href="/portfolio" className="flex justify-between p-2 rounded-lg hover:bg-surface-hover"><div><p className="font-medium text-sm">{pf.portfolio.name}</p><p className="text-xs text-muted">{pf.holdings.length} holdings</p></div><div className="text-right"><p className="text-sm tabular-nums font-medium">₹{pf.equity.toLocaleString("en-IN",{maximumFractionDigits:0})}</p><p className={`text-xs ${pf.unrealised_pnl>=0?"text-success":"text-danger"}`}>{pf.unrealised_pnl>=0?"+":""}₹{pf.unrealised_pnl.toFixed(2)}</p></div></Link>
            ))}</div>
          )}
        </div>

        {/* Holdings */}
        <div className="bg-surface border border-border rounded-xl p-5 lg:col-span-1">
          <div className="flex items-center justify-between mb-3"><h2 className="font-semibold">Holdings</h2><Link href="/portfolio" className="text-xs text-primary hover:underline">All →</Link></div>
          {allHoldings.length===0?<EmptyState message="No holdings" action="Trade" href="/portfolio"/>:(
            <div className="space-y-1">{allHoldings.slice(0,6).map((h,i)=>(<div key={i} className="flex justify-between p-1.5 rounded hover:bg-surface-hover"><div><span className="text-sm font-medium">{h.symbol}</span><span className="text-xs text-muted ml-2">{h.quantity} sh</span></div><span className={`text-xs tabular-nums ${(h.unrealised_pnl||0)>=0?"text-success":"text-danger"}`}>{h.unrealised_pnl!=null?`${h.unrealised_pnl>=0?"+":""}₹${Math.abs(h.unrealised_pnl).toFixed(2)}`:""}</span></div>))}</div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: string; color?: string }) {
  return <div className="bg-surface border border-border rounded-xl p-3"><div className="flex items-center gap-2 text-muted mb-1"><Icon size={14}/><span className="text-xs">{label}</span></div><p className={`text-sm font-bold tabular-nums ${color||""}`}>{value}</p></div>;
}

function EmptyState({ message, action, href }: { message: string; action: string; href: string }) {
  return <div className="text-center py-6"><p className="text-muted text-sm mb-2">{message}</p><Link href={href} className="text-xs text-primary hover:underline">{action} →</Link></div>;
}
