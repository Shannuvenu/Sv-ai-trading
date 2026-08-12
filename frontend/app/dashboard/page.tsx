"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { apiFetch } from "@/lib/apiClient";
import { TrendingUp, Wallet, Star, CircleDollarSign, Bot, Activity, Brain, Newspaper, AlertTriangle, ArrowRight, Briefcase } from "lucide-react";
import Link from "next/link";
import type { PortfolioSummary, Watchlist, Quote, NewsArticle } from "@/types";

interface IndexItem { symbol: string; name: string; last_price: number; change: number; change_pct: number; }

export default function DashboardPage() {
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [indices, setIndices] = useState<IndexItem[]>([]);
  const [news, setNews] = useState<NewsArticle[]>([]);
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

        const syms = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN"];
        const qts = await Promise.all(syms.map(s => api.getQuote(s).catch(() => null)));
        const map: Record<string, Quote> = {};
        qts.forEach((q,i) => { if (q) map[syms[i]] = q; });
        if (!cancelled) setQuotes(map);

        // Indices
        try {
          const idxRes = await apiFetch("/market/indices");
          const idxData = await idxRes.json();
          if (cancelled) return;
          if (Array.isArray(idxData) && idxData.length > 0 && idxData[0].last_price > 0) {
            setIndices(idxData.slice(0, 8));
          }
        } catch {}

        // Latest news
        try {
          const newsData = await api.getMarketNews("general", 1, 5);
          if (!cancelled && newsData) setNews(newsData.items.slice(0, 5));
        } catch {}

      } catch (e: unknown) { if (!cancelled) setError(e instanceof Error ? e.message : "Load failed"); }
      if (!cancelled) setLoading(false);
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 bg-surface rounded w-48" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {[...Array(6)].map((_, i) => <div key={i} className="h-20 bg-surface rounded-xl" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {[...Array(3)].map((_, i) => <div key={i} className="h-64 bg-surface rounded-xl" />)}
      </div>
    </div>
  );

  const totalEquity = portfolios.reduce((s, p) => s + (p?.equity || 0), 0);
  const totalCash = portfolios.reduce((s, p) => s + (p?.cash_balance || 0), 0);
  const totalPnl = portfolios.reduce((s, p) => s + (p?.unrealised_pnl || 0), 0);
  const allHoldings = portfolios.flatMap(p => p?.holdings || []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <span className="text-xs bg-warning/20 text-warning border border-warning/30 rounded-full px-3 py-1 font-medium">PAPER TRADING</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted">
          <Activity size={14} />
          <span>Market Closed</span>
        </div>
      </div>

      {/* Indices strip */}
      {indices.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {indices.map((idx) => (
            <div key={idx.symbol} className="bg-surface border border-border rounded-xl p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted truncate">{idx.name}</span>
                <TrendingUp size={12} className={idx.change >= 0 ? "text-success" : "text-danger"} />
              </div>
              <p className="text-lg font-bold tabular-nums">{idx.last_price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</p>
              <p className={`text-xs tabular-nums ${idx.change >= 0 ? "text-success" : "text-danger"}`}>
                {idx.change >= 0 ? "+" : ""}{idx.change.toFixed(2)} ({idx.change >= 0 ? "+" : ""}{idx.change_pct.toFixed(2)}%)
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard icon={CircleDollarSign} label="Portfolio Equity" value={`₹${totalEquity.toLocaleString("en-IN",{maximumFractionDigits:0})}`} />
        <StatCard icon={Wallet} label="Cash" value={`₹${totalCash.toLocaleString("en-IN",{maximumFractionDigits:0})}`} />
        <StatCard icon={TrendingUp} label="Unrealised P&L" value={`₹${totalPnl.toLocaleString("en-IN",{maximumFractionDigits:2})}`} color={totalPnl>=0?"text-success":"text-danger"} />
        <StatCard icon={Star} label="Watchlists" value={`${watchlists.length}`} />
        <StatCard icon={Bot} label="Portfolios" value={`${portfolios.length}`} />
        <StatCard icon={Activity} label="Positions" value={`${allHoldings.length}`} />
      </div>

      {error && <div className="bg-surface border border-danger/30 rounded-xl p-3"><p className="text-danger text-sm">{error}</p></div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Market Snapshot */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold flex items-center gap-2"><Activity size={16} />Market Snapshot</h2>
            <Link href="/markets" className="text-xs text-primary hover:underline flex items-center gap-1">Markets <ArrowRight size={12} /></Link>
          </div>
          <div className="space-y-2">
            {Object.entries(quotes).map(([sym, q]) => (
              <Link key={sym} href={`/markets/${sym}`} className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover transition-colors">
                <div><span className="font-medium text-sm text-primary">{sym}</span><p className="text-xs text-muted">{q.name}</p></div>
                <div className="text-right">
                  <div className="text-sm tabular-nums font-medium">₹{Number(q.last_price).toFixed(2)}</div>
                  <div className={`text-xs tabular-nums ${Number(q.change)>=0?"text-success":"text-danger"}`}>{Number(q.change)>=0?"+":""}{Number(q.change).toFixed(2)} ({Number(q.change_pct).toFixed(2)}%)</div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Portfolios */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold flex items-center gap-2"><Briefcase />Portfolios</h2>
            <Link href="/portfolio" className="text-xs text-primary hover:underline flex items-center gap-1">Manage <ArrowRight size={12} /></Link>
          </div>
          {portfolios.length===0?(
            <div className="text-center py-8"><p className="text-muted text-sm mb-2">No portfolios</p><Link href="/portfolio" className="text-xs text-primary hover:underline">Create Portfolio →</Link></div>
          ):(
            <div className="space-y-2">{portfolios.map(pf=>(
              <Link key={pf.portfolio.id} href="/portfolio" className="flex justify-between p-2.5 rounded-lg hover:bg-surface-hover transition-colors">
                <div><p className="font-medium text-sm">{pf.portfolio.name}</p><p className="text-xs text-muted">{pf.holdings.length} holdings</p></div>
                <div className="text-right"><p className="text-sm tabular-nums font-medium">₹{pf.equity.toLocaleString("en-IN",{maximumFractionDigits:0})}</p><p className={`text-xs ${pf.unrealised_pnl>=0?"text-success":"text-danger"}`}>{pf.unrealised_pnl>=0?"+":""}₹{pf.unrealised_pnl.toFixed(2)}</p></div>
              </Link>
            ))}</div>
          )}
        </div>

        {/* Latest News */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold flex items-center gap-2"><Newspaper size={16} />Latest News</h2>
            <Link href="/news" className="text-xs text-primary hover:underline flex items-center gap-1">More <ArrowRight size={12} /></Link>
          </div>
          {news.length === 0 ? (
            <div className="text-center py-8"><p className="text-muted text-sm">No recent news</p></div>
          ) : (
            <div className="space-y-2">
              {news.map((article) => (
                <a key={article.id} href={article.url || "#"} target="_blank" rel="noopener noreferrer" className="block p-2 rounded-lg hover:bg-surface-hover transition-colors">
                  <p className="text-sm leading-snug line-clamp-2">{article.headline}</p>
                  <div className="flex items-center gap-2 mt-1">
                    {article.source && <span className="text-xs text-muted">{article.source}</span>}
                    {article.published_at && <span className="text-xs text-muted">{new Date(article.published_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span>}
                  </div>
                </a>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Holdings + Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold flex items-center gap-2"><Wallet size={16} />Holdings</h2>
            <Link href="/portfolio" className="text-xs text-primary hover:underline flex items-center gap-1">Trade <ArrowRight size={12} /></Link>
          </div>
          {allHoldings.length===0?(
            <div className="text-center py-6"><p className="text-muted text-sm mb-2">No holdings</p><Link href="/portfolio" className="text-xs text-primary hover:underline">Start Trading →</Link></div>
          ):(
            <div className="space-y-1">{allHoldings.slice(0,8).map((h,i)=>(<div key={i} className="flex justify-between p-2 rounded hover:bg-surface-hover"><div><span className="text-sm font-medium">{h.symbol}</span><span className="text-xs text-muted ml-2">{h.quantity} @ ₹{Number(h.average_price).toFixed(2)}</span></div><div className="text-right"><span className="text-sm tabular-nums font-medium">₹{(h.market_value||0).toLocaleString("en-IN",{maximumFractionDigits:0})}</span><span className={`text-xs ml-2 ${(h.unrealised_pnl||0)>=0?"text-success":"text-danger"}`}>{h.unrealised_pnl!=null?`${h.unrealised_pnl>=0?"+":""}₹${Math.abs(h.unrealised_pnl).toFixed(0)}`:""}</span></div></div>))}</div>
          )}
        </div>

        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="font-semibold flex items-center gap-2 mb-3"><Brain size={16} />AI & Research</h2>
          <div className="space-y-3">
            <Link href="/ai-trader" className="flex items-center justify-between p-3 bg-background border border-border rounded-lg hover:bg-surface-hover transition-colors">
              <div className="flex items-center gap-2"><Bot size={18} className="text-primary" /><span className="text-sm font-medium">AI Trader</span></div>
              <ArrowRight size={14} className="text-muted" />
            </Link>
            <Link href="/analysis" className="flex items-center justify-between p-3 bg-background border border-border rounded-lg hover:bg-surface-hover transition-colors">
              <div className="flex items-center gap-2"><TrendingUp size={18} className="text-primary" /><span className="text-sm font-medium">Technical Analysis</span></div>
              <ArrowRight size={14} className="text-muted" />
            </Link>
            <Link href="/backtest" className="flex items-center justify-between p-3 bg-background border border-border rounded-lg hover:bg-surface-hover transition-colors">
              <div className="flex items-center gap-2"><Activity size={18} className="text-primary" /><span className="text-sm font-medium">Backtesting</span></div>
              <ArrowRight size={14} className="text-muted" />
            </Link>
            <Link href="/tools" className="flex items-center justify-between p-3 bg-background border border-border rounded-lg hover:bg-surface-hover transition-colors">
              <div className="flex items-center gap-2"><Wallet size={18} className="text-primary" /><span className="text-sm font-medium">Financial Calculators</span></div>
              <ArrowRight size={14} className="text-muted" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: string; color?: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-3">
      <div className="flex items-center gap-2 text-muted mb-1">
        <Icon size={14}/>
        <span className="text-xs">{label}</span>
      </div>
      <p className={`text-sm font-bold tabular-nums ${color||""}`}>{value}</p>
    </div>
  );
}
