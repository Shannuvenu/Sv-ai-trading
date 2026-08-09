"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, Newspaper, ExternalLink, ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import type { NewsArticle, NewsListResponse } from "@/types";

const MARKET_CATEGORIES = [
  { value: "general", label: "General" },
  { value: "forex", label: "Forex" },
  { value: "crypto", label: "Crypto" },
  { value: "merger", label: "Mergers" },
];

export default function NewsPage() {
  const [activeTab, setActiveTab] = useState<"company" | "market" | "search">("market");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [companySymbol, setCompanySymbol] = useState("");
  const [companyData, setCompanyData] = useState<NewsListResponse | null>(null);

  const [marketCategory, setMarketCategory] = useState("general");
  const [marketData, setMarketData] = useState<NewsListResponse | null>(null);
  const [marketPage, setMarketPage] = useState(1);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchData, setSearchData] = useState<NewsListResponse | null>(null);
  const [searchPage, setSearchPage] = useState(1);

  const fetchCompanyNews = useCallback(async (symbol: string, page: number) => {
    if (!symbol) return;
    setLoading(true); setError("");
    try {
      const data = await api.getCompanyNews(symbol, page, 10);
      setCompanyData(data);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Failed to load news"); }
    setLoading(false);
  }, []);

  const fetchMarketNews = useCallback(async (category: string, page: number) => {
    setLoading(true); setError("");
    try {
      const data = await api.getMarketNews(category, page, 10);
      setMarketData(data);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Failed to load news"); }
    setLoading(false);
  }, []);

  const fetchSearch = useCallback(async (q: string, page: number) => {
    if (q.length < 2) return;
    setLoading(true); setError("");
    try {
      const data = await api.searchNews(q, page, 10);
      setSearchData(data);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Failed to search news"); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchMarketNews(marketCategory, marketPage); }, [marketCategory, marketPage, fetchMarketNews]);

  useEffect(() => {
    if (searchQuery.length >= 2) {
      const t = setTimeout(() => { setSearchPage(1); fetchSearch(searchQuery, 1); }, 400);
      return () => clearTimeout(t);
    }
  }, [searchQuery, fetchSearch]);

  const handleCompanySubmit = (e: React.FormEvent) => { e.preventDefault(); setCompanyData(null); fetchCompanyNews(companySymbol.toUpperCase(), 1); };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">News</h1>
        <span className="text-xs bg-surface border border-border rounded-full px-3 py-1 text-muted">Powered by Finnhub</span>
      </div>

      <div className="flex gap-4 border-b border-border">
        {[
          { id: "market", label: "Market News" },
          { id: "company", label: "Company News" },
          { id: "search", label: "Search" },
        ].map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id as typeof activeTab)}
            className={`pb-2 text-sm font-medium ${activeTab === t.id ? "text-primary border-b-2 border-primary" : "text-muted hover:text-foreground"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading && <div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>}
      {error && <div className="bg-surface border border-danger/30 rounded-xl p-4"><p className="text-danger text-sm">{error}</p></div>}

      {activeTab === "company" && (
        <div className="space-y-4">
          <form onSubmit={handleCompanySubmit} className="flex gap-3 max-w-md">
            <div className="relative flex-1">
              <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input type="text" placeholder="Enter symbol (e.g. RELIANCE)"
                value={companySymbol} onChange={(e) => setCompanySymbol(e.target.value.toUpperCase())}
                className="w-full pl-10 pr-3 py-2.5 bg-surface border border-border rounded-lg focus:outline-none focus:border-primary text-sm" />
            </div>
            <button type="submit" className="px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">Load</button>
          </form>
          {companyData && <NewsList items={companyData.items} total={companyData.total} page={companyData.page} pageSize={companyData.page_size} onPageChange={(p) => fetchCompanyNews(companySymbol, p)} />}
        </div>
      )}

      {activeTab === "market" && (
        <div className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            {MARKET_CATEGORIES.map((c) => (
              <button key={c.value} onClick={() => { setMarketCategory(c.value); setMarketPage(1); }}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium ${marketCategory === c.value ? "bg-primary/20 text-primary" : "bg-surface border border-border hover:bg-surface-hover"}`}>{c.label}</button>
            ))}
          </div>
          {marketData && <NewsList items={marketData.items} total={marketData.total} page={marketData.page} pageSize={marketData.page_size} onPageChange={(p) => setMarketPage(p)} />}
        </div>
      )}

      {activeTab === "search" && (
        <div className="space-y-4">
          <div className="relative max-w-md">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input type="text" placeholder="Search news..." value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-3 py-2.5 bg-surface border border-border rounded-lg focus:outline-none focus:border-primary text-sm" />
          </div>
          {searchData && <NewsList items={searchData.items} total={searchData.total} page={searchData.page} pageSize={searchData.page_size} onPageChange={(p) => fetchSearch(searchQuery, p)} />}
        </div>
      )}
    </div>
  );
}

function NewsList({ items, total, page, pageSize, onPageChange }: {
  items: NewsArticle[]; total: number; page: number; pageSize: number; onPageChange: (p: number) => void;
}) {
  const totalPages = Math.ceil(total / pageSize);
  if (items.length === 0) return (
    <div className="bg-surface border border-border rounded-xl p-12 text-center">
      <Newspaper size={40} className="mx-auto text-muted mb-3" />
      <p className="text-muted">No news articles found.</p>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="grid gap-3">
        {items.map((article) => (
          <a key={article.id} href={article.url || "#"} target="_blank" rel="noopener noreferrer"
            className="block bg-surface border border-border rounded-xl p-4 hover:bg-surface-hover transition-colors group">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  {article.symbol && <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded font-medium">{article.symbol}</span>}
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
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button onClick={() => onPageChange(page - 1)} disabled={page <= 1}
            className={`p-2 rounded-lg ${page <= 1 ? "text-muted cursor-not-allowed" : "hover:bg-surface-hover text-muted hover:text-foreground"}`}><ChevronLeft size={18} /></button>
          <span className="text-sm text-muted">Page {page} of {totalPages}</span>
          <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}
            className={`p-2 rounded-lg ${page >= totalPages ? "text-muted cursor-not-allowed" : "hover:bg-surface-hover text-muted hover:text-foreground"}`}><ChevronRight size={18} /></button>
        </div>
      )}
    </div>
  );
}
