"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TrendingUp, Wallet, Star, ArrowRight, CircleDollarSign } from "lucide-react";
import Link from "next/link";
import type { PortfolioSummary, Watchlist } from "@/types";

export default function DashboardPage() {
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [pfs, wls] = await Promise.all([
          api.listPortfolios().then((p) => Promise.all(p.map((pf) => api.getPortfolio(pf.id).catch(() => null)))),
          api.listWatchlists(),
        ]);
        if (!cancelled) {
          setPortfolios(pfs.filter(Boolean) as PortfolioSummary[]);
          setWatchlists(wls);
        }
      } catch (e: unknown) { if (!cancelled) setError(e instanceof Error ? e.message : "Load failed"); }
      if (!cancelled) setLoading(false);
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  }

  const totalEquity = portfolios.reduce((s, p) => s + (p?.equity || 0), 0);
  const totalCash = portfolios.reduce((s, p) => s + (p?.cash_balance || 0), 0);
  const totalPnl = portfolios.reduce((s, p) => s + (p?.unrealised_pnl || 0), 0);
  const allHoldings = portfolios.flatMap(p => p?.holdings || []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <span className="text-xs bg-warning/20 text-warning border border-warning/30 rounded-full px-3 py-1 font-medium">PAPER TRADING</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={CircleDollarSign} label="Total Equity" value={`₹${totalEquity.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} />
        <StatCard icon={Wallet} label="Available Cash" value={`₹${totalCash.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} />
        <StatCard icon={TrendingUp} label="Unrealised P&L" value={`₹${totalPnl.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`} color={totalPnl >= 0 ? "text-success" : "text-danger"} />
        <StatCard icon={Star} label="Watchlists" value={`${watchlists.length}`} />
      </div>

      {error && <div className="bg-surface border border-danger/30 rounded-xl p-3"><p className="text-danger text-sm">{error}</p></div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Portfolios</h2>
            <Link href="/portfolio" className="text-sm text-primary hover:underline flex items-center gap-1">View All <ArrowRight size={14} /></Link>
          </div>
          {portfolios.length === 0 ? (
            <EmptyState message="No portfolios yet" action="Create Portfolio" href="/portfolio" />
          ) : (
            <div className="space-y-3">
              {portfolios.map((pf) => (
                <Link key={pf.portfolio.id} href="/portfolio" className="flex items-center justify-between p-3 rounded-lg hover:bg-surface-hover transition-colors">
                  <div>
                    <p className="font-medium">{pf.portfolio.name}</p>
                    <p className="text-xs text-muted">{pf.holdings.length} holdings</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium tabular-nums">₹{pf.equity.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</p>
                    <p className={`text-sm tabular-nums ${pf.unrealised_pnl >= 0 ? "text-success" : "text-danger"}`}>
                      {pf.unrealised_pnl >= 0 ? "+" : ""}₹{pf.unrealised_pnl.toFixed(2)}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Holdings</h2>
            <Link href="/portfolio" className="text-sm text-primary hover:underline flex items-center gap-1">View All <ArrowRight size={14} /></Link>
          </div>
          {allHoldings.length === 0 ? (
            <EmptyState message="No holdings yet" action="Start Trading" href="/portfolio" />
          ) : (
            <div className="space-y-2">
              {allHoldings.slice(0, 8).map((h, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover">
                  <div>
                    <span className="font-medium text-sm">{h.symbol}</span>
                    <span className="text-xs text-muted ml-2">{h.quantity} shares</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm tabular-nums">₹{h.market_value?.toFixed(0) || "—"}</span>
                    <span className={`text-xs ml-2 tabular-nums ${(h.unrealised_pnl || 0) >= 0 ? "text-success" : "text-danger"}`}>
                      {h.unrealised_pnl != null ? `${h.unrealised_pnl >= 0 ? "+" : ""}₹${Math.abs(h.unrealised_pnl).toFixed(2)}` : ""}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {watchlists.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="font-semibold mb-3">Watchlists</h2>
          <div className="flex flex-wrap gap-2">
            {watchlists.map((wl) => (
              <Link key={wl.id} href="/watchlists" className="px-3 py-1.5 bg-surface-hover border border-border rounded-lg text-sm hover:border-primary transition-colors">
                {wl.name} ({wl.item_count})
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: string; color?: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <div className="flex items-center gap-2 text-muted mb-2">
        <Icon size={16} /><span className="text-sm">{label}</span>
      </div>
      <p className={`text-lg lg:text-xl font-bold tabular-nums ${color || ""}`}>{value}</p>
    </div>
  );
}

function EmptyState({ message, action, href }: { message: string; action: string; href: string }) {
  return (
    <div className="text-center py-8">
      <p className="text-muted mb-3">{message}</p>
      <Link href={href} className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
        {action} <ArrowRight size={14} />
      </Link>
    </div>
  );
}
