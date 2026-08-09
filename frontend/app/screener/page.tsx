"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Filter, ArrowUpDown, Search } from "lucide-react";

export default function ScreenerPage() {
  const [symbols, setSymbols] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ minPrice: "", maxPrice: "", minChange: "", signal: "", exchange: "NSE" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const liquid = [
      "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC","LT","BHARTIARTL",
      "AXISBANK","KOTAKBANK","HINDUNILVR","BAJFINANCE","MARUTI","TITAN","SUNPHARMA",
      "ASIANPAINT","HCLTECH","WIPRO","TECHM","NESTLE","ULTRACEMCO","POWERGRID",
      "NTPC","ONGC","COALINDIA","JSWSTEEL","TATASTEEL","ADANIPORTS","ADANIENT",
      "HDFCLIFE","BAJAJFINSV","INDUSINDBK","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP",
      "BRITANNIA","EICHERMOT","HEROMOTOCO","TATAMOTORS","M&M","BAJAJ-AUTO",
    ];
    setSymbols(liquid.map(s => ({ symbol: s })));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Stock Screener</h1>
        <span className="text-xs bg-surface border border-border rounded-full px-3 py-1 text-muted">UPSTOX</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div><label className="text-xs text-muted">Min Price</label><input type="number" value={filters.minPrice} onChange={e => setFilters({...filters, minPrice: e.target.value})} className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm" placeholder="₹" /></div>
        <div><label className="text-xs text-muted">Max Price</label><input type="number" value={filters.maxPrice} onChange={e => setFilters({...filters, maxPrice: e.target.value})} className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm" placeholder="₹" /></div>
        <div><label className="text-xs text-muted">Min Change %</label><input type="number" value={filters.minChange} onChange={e => setFilters({...filters, minChange: e.target.value})} className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm" placeholder="%" /></div>
        <div><label className="text-xs text-muted">AI Signal</label>
          <select value={filters.signal} onChange={e => setFilters({...filters, signal: e.target.value})} className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm">
            <option value="">All</option><option value="BUY">Buy</option><option value="SELL">Sell</option><option value="HOLD">Hold</option>
          </select>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="p-3">Symbol</th><th className="p-3">Price</th><th className="p-3">Change</th><th className="p-3">Volume</th><th className="p-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {symbols.map((s, i) => (
              <tr key={i} className="border-b border-border hover:bg-surface-hover">
                <td className="p-3"><Link href={`/markets/${s.symbol}`} className="text-primary font-medium text-sm">{s.symbol}</Link></td>
                <td className="p-3 tabular-nums">—</td>
                <td className="p-3 tabular-nums">—</td>
                <td className="p-3 tabular-nums">—</td>
                <td className="p-3"><Link href={`/markets/${s.symbol}`} className="text-primary text-xs hover:underline">View</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted text-center">Showing preselected liquid stocks. Full screener with live price/technical/AI filters coming soon.</p>
    </div>
  );
}
