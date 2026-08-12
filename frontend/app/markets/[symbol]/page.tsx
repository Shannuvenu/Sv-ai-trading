"use client";
import { Suspense, useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Search, TrendingUp, TrendingDown, Minus, Star, Bell, ArrowLeft, NewspaperIcon, ExternalLink, Maximize } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { apiFetch } from "@/lib/apiClient";
import type { Quote, NewsArticle, NewsListResponse } from "@/types";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

function StockContent() {
  const params = useParams();
  const router = useRouter();
  const symbol = (params?.symbol as string || "").toUpperCase();
  const [quote, setQuote] = useState<Quote | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"overview"|"chart"|"technicals"|"news">("overview");
  const [newsData, setNewsData] = useState<NewsListResponse | null>(null);

  const load = useCallback(async (sym: string) => {
    setLoading(true); setError("");
    try {
      const [q, h, s, n] = await Promise.all([
        api.getQuote(sym).catch(() => null),
        api.getHistory(sym).catch(() => ({ data: [] })),
        apiFetch(`/analysis/technical-summary/${sym}`).then(r => r.ok ? r.json() : null).catch(() => null),
        api.getCompanyNews(sym, 1, 10).catch(() => null),
      ]);
      setQuote(q);
      setHistory(h?.data?.slice(-90) || []);
      setSummary(s);
      setNewsData(n);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  }, []);

  useEffect(() => { if (symbol) load(symbol); }, [symbol]);

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  if (error) return <div className="text-center py-20"><p className="text-danger">{error}</p></div>;
  if (!quote) return <div className="text-center py-20"><p className="text-muted">Instrument not found</p></div>;

  const chartData = history.map((h: any) => ({ time: new Date(h.timestamp).toLocaleDateString("en-IN", { month: "short", day: "numeric" }), close: Number(h.close) }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/markets")} className="text-muted hover:text-foreground"><ArrowLeft size={20} /></button>
          <div>
            <h1 className="text-2xl font-bold">{quote.name}</h1>
            <div className="flex items-center gap-2 text-sm text-muted"><span className="text-primary font-medium">{quote.symbol}</span> · {quote.exchange}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a href={`/chart/${quote.symbol}`} className="text-xs bg-primary/20 text-primary border border-primary/30 rounded-full px-3 py-1 font-medium hover:bg-primary/30 flex items-center gap-1"><Maximize size={12} />Full Chart</a>
          <span className="text-xs bg-surface border border-border rounded-full px-3 py-1 text-muted">MARKET CLOSED · UPSTOX</span>
        </div>
      </div>

      {/* Price strip */}
      <div className="grid grid-cols-4 sm:grid-cols-8 gap-3">
        {[["LTP", `₹${Number(quote.last_price).toFixed(2)}`],["Change",<span key="ch" className={Number(quote.change)>=0?"text-success":"text-danger"}>{Number(quote.change)>=0?"+":""}{Number(quote.change).toFixed(2)} ({Number(quote.change_pct).toFixed(2)}%)</span>],["Open",`₹${Number(quote.open).toFixed(2)}`],["High",`₹${Number(quote.high).toFixed(2)}`],["Low",`₹${Number(quote.low).toFixed(2)}`],["Close",`₹${Number(quote.close).toFixed(2)}`],["Volume",quote.volume?.toLocaleString("en-IN")||"—"],["Source","UPSTOX"]].map(([l,v])=>(
          <div key={l as string} className="bg-surface border border-border rounded-xl p-3 text-center"><p className="text-xs text-muted mb-1">{l}</p><p className="text-sm font-bold tabular-nums">{v}</p></div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-border">
        {["overview","chart","technicals","news"].map(t=>(<button key={t} onClick={()=>setActiveTab(t as any)} className={`pb-2 text-sm font-medium capitalize ${activeTab===t?"text-primary border-b-2 border-primary":"text-muted hover:text-foreground"}`}>{t}</button>))}
      </div>

      {activeTab==="overview" && summary && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 bg-surface border border-border rounded-xl p-5">
            <div className={`text-2xl font-bold ${summary.summary.overall.includes("BUY")?"text-success":summary.summary.overall.includes("SELL")?"text-danger":"text-warning"}`}>{summary.summary.overall}</div>
            <div className="text-sm text-muted">Technical Summary · {summary.summary.oscillators.rating} oscillators · {summary.summary.moving_averages.rating} MAs</div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-surface border border-border rounded-xl p-4"><p className="text-xs text-muted mb-2">Oscillators</p>
              <div className="flex gap-3 text-sm"><span className="text-success">Buy {summary.summary.oscillators.buy}</span><span className="text-muted">Neutral {summary.summary.oscillators.neutral}</span><span className="text-danger">Sell {summary.summary.oscillators.sell}</span></div></div>
            <div className="bg-surface border border-border rounded-xl p-4"><p className="text-xs text-muted mb-2">Moving Averages</p>
              <div className="flex gap-3 text-sm"><span className="text-success">Buy {summary.summary.moving_averages.buy}</span><span className="text-muted">Neutral {summary.summary.moving_averages.neutral}</span><span className="text-danger">Sell {summary.summary.moving_averages.sell}</span></div></div>
            <div className="bg-surface border border-border rounded-xl p-4"><p className="text-xs text-muted mb-2">Indicators</p><div className="grid grid-cols-2 gap-1 text-xs">{Object.entries(summary.indicators||{}).slice(0,6).map(([k,v])=>(<div key={k} className="flex justify-between"><span className="text-muted">{k}</span><span className="tabular-nums">{v!=null?String(v):"—"}</span></div>))}</div></div>
          </div>
        </div>
      )}

      {activeTab==="chart" && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="font-semibold mb-3">Price History</h3>
          {chartData.length>0?<ResponsiveContainer width="100%" height={400}><LineChart data={chartData}><CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e"/><XAxis dataKey="time" tick={{fontSize:11,fill:"#71717a"}} interval="preserveStartEnd"/><YAxis tick={{fontSize:11,fill:"#71717a"}} domain={["auto","auto"]}/><Tooltip contentStyle={{background:"#13131a",border:"1px solid #1e1e2e",borderRadius:"8px"}}/><Line type="monotone" dataKey="close" stroke="#6366f1" dot={false} strokeWidth={2}/></LineChart></ResponsiveContainer>:<p className="text-muted text-center py-12">No data</p>}
        </div>
      )}

      {activeTab==="technicals" && summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Object.entries(summary.moving_averages||{}).map(([k,v])=>(<div key={k} className="bg-surface border border-border rounded-xl p-2 text-center"><p className="text-xs text-muted">{k}</p><p className="font-medium tabular-nums text-sm">{v!=null?`₹${Number(v).toFixed(2)}`:"—"}</p></div>))}
          {Object.entries(summary.indicators||{}).map(([k,v])=>(<div key={k} className="bg-surface border border-border rounded-xl p-2 text-center"><p className="text-xs text-muted">{k}</p><p className="font-medium tabular-nums text-sm">{v!=null?Number(v).toFixed(2):"—"}</p></div>))}
        </div>
      )}

      {activeTab === "news" && (
        <div className="space-y-3">
          {newsData && newsData.items.length > 0 ? (
            newsData.items.map((article) => (
              <a key={article.id} href={article.url || "#"} target="_blank" rel="noopener noreferrer"
                className="block bg-surface border border-border rounded-xl p-4 hover:bg-surface-hover transition-colors group">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {article.source && <span className="text-xs text-muted">{article.source}</span>}
                    </div>
                    <h3 className="font-medium text-sm leading-snug group-hover:text-primary transition-colors">{article.headline}</h3>
                    {article.summary && <p className="text-xs text-muted mt-1 line-clamp-2">{article.summary}</p>}
                    <div className="flex items-center gap-3 mt-2">
                      {article.published_at && <span className="text-xs text-muted">{new Date(article.published_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</span>}
                      <ExternalLink size={12} className="text-muted group-hover:text-primary" />
                    </div>
                  </div>
                  {article.image_url && (
                    <img src={article.image_url} alt="" className="w-20 h-14 rounded-lg object-cover flex-shrink-0" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                  )}
                </div>
              </a>
            ))
          ) : (
            <div className="bg-surface border border-border rounded-xl p-12 text-center">
              <NewspaperIcon size={40} className="mx-auto text-muted mb-3" />
              <p className="text-muted">No recent news for this stock.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function StockPage() {
  return <Suspense fallback={<div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>}><StockContent /></Suspense>;
}
