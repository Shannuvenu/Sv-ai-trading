"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Bell, Plus, Trash2 } from "lucide-react";
import type { Alert, Instrument } from "@/types";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [symbol, setSymbol] = useState("");
  const [alertType, setAlertType] = useState("PRICE_ABOVE");
  const [threshold, setThreshold] = useState("");
  const [loading, setLoading] = useState(true);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [search, setSearch] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.listAlerts().then((a) => { if (!cancelled) setAlerts(a); }).catch(() => {});
    api.getInstruments().then((i) => { if (!cancelled) setInstruments(i); }).catch(() => {});
    const t = setTimeout(() => { if (!cancelled) setLoading(false); }, 100);
    return () => { cancelled = true; clearTimeout(t); };
  }, []);

  const filteredInstruments = instruments.filter((i) =>
    i.symbol.toLowerCase().includes(search.toLowerCase()) || i.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleCreate = async () => {
    setError(""); setSuccessMsg("");
    if (!symbol) { setError("Symbol is required"); return; }
    try {
      await api.createAlert({ symbol: symbol.toUpperCase(), alert_type: alertType, threshold_value: threshold ? parseFloat(threshold) : null });
      setSuccessMsg(`Alert for ${symbol.toUpperCase()} created`);
      setSymbol(""); setSearch(""); setThreshold("");
      const a = await api.listAlerts(); setAlerts(a);
    } catch (err: unknown) { setError(err instanceof Error ? err.message : "Failed to create"); }
  };

  const handleDelete = async (id: number) => {
    try { await api.deleteAlert(id); const a = await api.listAlerts(); setAlerts(a); } catch (err: unknown) { setError(err instanceof Error ? err.message : "Failed to delete"); }
  };

  if (loading) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  }

  const alertTypeLabels: Record<string, string> = { PRICE_ABOVE: "Price Above", PRICE_BELOW: "Price Below", SIGNAL_BUY: "BUY Signal", SIGNAL_SELL: "SELL Signal" };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Alerts</h1>
      <div className="bg-surface border border-border rounded-xl p-5">
        <h3 className="font-semibold mb-3">Create Alert</h3>
        <div className="flex gap-2 flex-wrap items-end">
          <div className="relative">
            <label className="text-xs text-muted">Symbol</label>
            <input type="text" value={search} onChange={(e) => { setSearch(e.target.value.toUpperCase()); setShowSuggestions(true); }} onFocus={() => setShowSuggestions(true)} onBlur={() => setTimeout(() => setShowSuggestions(false), 250)} placeholder="e.g., RELIANCE" className="w-36 px-3 py-2 bg-background border border-border rounded-lg text-sm" />
            {showSuggestions && search && filteredInstruments.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-surface border border-border rounded-lg max-h-32 overflow-auto shadow-lg">
                {filteredInstruments.map((inst) => (<button key={inst.id} onClick={() => { setSymbol(inst.symbol); setSearch(inst.symbol); setShowSuggestions(false); }} className="w-full text-left px-3 py-1.5 hover:bg-surface-hover text-xs">{inst.symbol} — {inst.name}</button>))}
              </div>
            )}
          </div>
          <div>
            <label className="text-xs text-muted">Type</label>
            <select value={alertType} onChange={(e) => setAlertType(e.target.value)} className="w-36 px-3 py-2 bg-background border border-border rounded-lg text-sm">
              {Object.entries(alertTypeLabels).map(([k, v]) => (<option key={k} value={k}>{v}</option>))}
            </select>
          </div>
          {(alertType === "PRICE_ABOVE" || alertType === "PRICE_BELOW") && (
            <div><label className="text-xs text-muted">Price (₹)</label><input type="number" value={threshold} onChange={(e) => setThreshold(e.target.value)} min="0.01" step="0.01" className="w-28 px-3 py-2 bg-background border border-border rounded-lg text-sm" /></div>
          )}
          <button onClick={handleCreate} className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium"><Plus size={16} /> Create</button>
        </div>
      </div>
      {error && <div className="bg-surface border border-danger/30 rounded-xl p-3"><p className="text-danger text-sm">{error}</p></div>}
      {successMsg && <div className="bg-surface border border-success/30 rounded-xl p-3"><p className="text-success text-sm">{successMsg}</p></div>}
      {alerts.length === 0 ? (
        <p className="text-muted text-center py-12">No alerts configured. Create one above.</p>
      ) : (
        <div className="space-y-2">
          {alerts.map((a) => (
            <div key={a.id} className="flex items-center justify-between bg-surface border border-border rounded-xl p-4">
              <div className="flex items-center gap-3">
                <Bell size={18} className="text-warning" />
                <div><span className="font-medium">{a.symbol}</span><span className="text-muted ml-2 text-sm">{alertTypeLabels[a.alert_type] || a.alert_type}</span>{a.threshold_value != null && <span className="text-muted ml-2 text-sm">@ ₹{Number(a.threshold_value).toFixed(2)}</span>}</div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-xs px-2 py-0.5 rounded ${a.is_active ? "text-success bg-success/10" : "text-muted bg-surface-hover"}`}>{a.is_active ? "Active" : "Inactive"}</span>
                <button onClick={() => handleDelete(a.id)} className="text-muted hover:text-danger transition-colors" title="Delete"><Trash2 size={16} /></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
