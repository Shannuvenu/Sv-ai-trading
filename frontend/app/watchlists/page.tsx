"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Plus, Trash2, X } from "lucide-react";
import type { Watchlist, WatchlistItem, Quote } from "@/types";
import Link from "next/link";

export default function WatchlistsPage() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selected, setSelected] = useState<Watchlist | null>(null);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [newName, setNewName] = useState("");
  const [symbolInput, setSymbolInput] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    api.listWatchlists().then((wls) => { setWatchlists(wls); if (wls.length > 0 && !selectedId) setSelectedId(wls[0].id); });
  }, [selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    api.getWatchlist(selectedId).then((wl) => {
      setSelected(wl);
      if (wl.items?.length) {
        Promise.all(wl.items.map((i: WatchlistItem) => api.getQuote(i.symbol).catch(() => null))).then((qts) => {
          const map: Record<string, Quote> = {};
          qts.forEach((q) => { if (q) map[q.symbol] = q; });
          setQuotes(map);
        });
      } else setQuotes({});
    });
  }, [selectedId]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    const wl = await api.createWatchlist(newName);
    setNewName(""); setShowCreate(false);
    const wls = await api.listWatchlists(); setWatchlists(wls);
    setSelectedId(wl.id);
  };

  const handleDelete = async (id: number) => {
    await api.deleteWatchlist(id);
    setSelectedId(null); setSelected(null);
    const wls = await api.listWatchlists(); setWatchlists(wls);
  };

  const handleAddSymbol = async () => {
    if (!selectedId || !symbolInput.trim()) return;
    await api.addWatchlistItem(selectedId, symbolInput.trim().toUpperCase());
    setSymbolInput("");
    const wl = await api.getWatchlist(selectedId); setSelected(wl);
  };

  const handleRemoveItem = async (itemId: number) => {
    if (!selectedId) return;
    await api.removeWatchlistItem(selectedId, itemId);
    const wl = await api.getWatchlist(selectedId); setSelected(wl);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Watchlists</h1>
        <button onClick={() => setShowCreate(!showCreate)} className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium"><Plus size={16} /> New Watchlist</button>
      </div>
      {showCreate && (
        <div className="flex gap-2">
          <input type="text" placeholder="Watchlist name..." value={newName} onChange={(e) => setNewName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleCreate()} className="flex-1 px-3 py-2 bg-surface border border-border rounded-lg focus:outline-none focus:border-primary" />
          <button onClick={handleCreate} className="px-4 py-2 bg-primary rounded-lg">Create</button>
          <button onClick={() => setShowCreate(false)} className="px-4 py-2"><X size={18} /></button>
        </div>
      )}
      <div className="flex gap-6">
        <div className="w-64 space-y-1">
          {watchlists.map((wl) => (
            <button key={wl.id} onClick={() => setSelectedId(wl.id)} className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center justify-between ${selectedId === wl.id ? "bg-primary/20 text-primary" : "hover:bg-surface-hover"}`}>
              <span>{wl.name} <span className="text-muted text-xs">({wl.item_count})</span></span>
              <button onClick={(e) => { e.stopPropagation(); handleDelete(wl.id); }}><Trash2 size={14} className="text-muted hover:text-danger" /></button>
            </button>
          ))}
        </div>
        <div className="flex-1 bg-surface border border-border rounded-xl p-5">
          {selected ? (
            <>
              <div className="flex gap-2 mb-4">
                <input type="text" placeholder="Add symbol (e.g., RELIANCE)..." value={symbolInput} onChange={(e) => setSymbolInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleAddSymbol()} className="flex-1 px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-sm" />
                <button onClick={handleAddSymbol} className="px-4 py-2 bg-primary rounded-lg text-sm">Add</button>
              </div>
              {selected.items && selected.items.length > 0 ? (
                <div className="space-y-1">
                  {selected.items.map((item) => {
                    const q = quotes[item.symbol];
                    return (
                      <div key={item.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover">
                        <Link href={`/analysis?symbol=${item.symbol}`} className="flex-1 flex items-center justify-between">
                          <div><span className="font-medium text-primary">{item.symbol}</span></div>
                          <div className="text-right flex gap-6">
                            <span className="tabular-nums">₹{q?.last_price?.toFixed(2) || "—"}</span>
                            <span className={`w-24 text-right tabular-nums ${q?.change_pct != null && q.change_pct >= 0 ? "text-success" : "text-danger"}`}>{q ? `${q.change_pct >= 0 ? "+" : ""}${q.change_pct.toFixed(2)}%` : "—"}</span>
                          </div>
                        </Link>
                        <button onClick={() => handleRemoveItem(item.id)} className="ml-3 text-muted hover:text-danger"><X size={14} /></button>
                      </div>
                    );
                  })}
                </div>
              ) : (<p className="text-muted text-center py-8">No symbols in this watchlist</p>)}
            </>
          ) : (<p className="text-muted text-center py-8">Select or create a watchlist</p>)}
        </div>
      </div>
    </div>
  );
}
