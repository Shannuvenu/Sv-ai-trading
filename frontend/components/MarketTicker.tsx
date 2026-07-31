"use client";
import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface TickerItem {
  symbol: string;
  name: string;
  last_price: number;
  change: number;
  change_pct: number;
  source: string;
}

export default function MarketTicker() {
  const [items, setItems] = useState<TickerItem[]>([]);
  const [status, setStatus] = useState<"loading" | "live" | "unavailable">("loading");

  useEffect(() => {
    async function fetchIndices() {
      try {
        const res = await fetch("/api/market/indices");
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0 && data[0].last_price > 0) {
          setItems(data.slice(0, 6));
          setStatus("live");
        } else {
          setStatus("unavailable");
        }
      } catch {
        setStatus("unavailable");
      }
    }
    fetchIndices();
    const interval = setInterval(fetchIndices, 30000);
    return () => clearInterval(interval);
  }, []);

  if (status === "loading") return null;

  const major = items.filter((i) => ["NIFTY_50", "SENSEX", "NIFTY_BANK", "INDIA_VIX"].includes(i.symbol));

  return (
    <div className="w-full bg-surface border-b border-border overflow-hidden">
      <div className="flex items-center h-9 px-4 gap-6 overflow-x-auto text-sm whitespace-nowrap">
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${status === "live" ? "text-success bg-success/10" : "text-muted bg-surface-hover"}`}>
          {status === "live" ? "LIVE" : "UNAVAILABLE"}
        </span>
        {major.length > 0 ? major.map((item) => (
          <div key={item.symbol} className="flex items-center gap-2 tabular-nums">
            <span className="text-muted text-xs font-medium">{item.name}</span>
            <span className="font-medium">{item.last_price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
            <span className={`text-xs flex items-center gap-0.5 ${item.change >= 0 ? "text-success" : "text-danger"}`}>
              {item.change >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {item.change >= 0 ? "+" : ""}{item.change.toFixed(2)} ({item.change >= 0 ? "+" : ""}{item.change_pct.toFixed(2)}%)
            </span>
          </div>
        )) : (
          <span className="text-muted text-xs">Market data loading...</span>
        )}
      </div>
    </div>
  );
}
