"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/apiClient";

export default function CalculatorsPage() {
  const [active, setActive] = useState("sip");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Financial Calculators</h1>
      <div className="flex flex-wrap gap-2">
        {["sip","lumpsum","cagr","emi","compound","fd","rd"].map((t) => (
          <button key={t} onClick={() => setActive(t)} className={`px-4 py-1.5 rounded-lg text-sm font-medium ${active===t ? "bg-primary/20 text-primary" : "bg-surface border border-border hover:bg-surface-hover"}`}>
            {t.toUpperCase()}
          </button>
        ))}
      </div>
      <div className="bg-surface border border-border rounded-xl p-6 max-w-md">
        {active === "sip" && <SIPCalc />}
        {active === "lumpsum" && <LumpsumCalc />}
        {active === "cagr" && <CAGRCalc />}
        {active === "emi" && <EMICalc />}
        {active === "compound" && <CompoundCalc />}
        {active === "fd" && <FDCalc />}
        {active === "rd" && <RDCalc />}
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "number", min, max, step }: { label: string; value: string; onChange: (v: string) => void; type?: string; min?: string; max?: string; step?: string }) {
  return <div className="mb-3"><label className="text-xs text-muted">{label}</label><input type={type} value={value} onChange={(e) => onChange(e.target.value)} min={min} max={max} step={step} className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm" /></div>;
}

function Result({ data }: { data: Record<string, number> }) {
  return <div className="mt-4 space-y-2 pt-4 border-t border-border">{Object.entries(data).map(([k, v]) => (<div key={k} className="flex justify-between text-sm"><span className="text-muted capitalize">{k.replace(/_/g, " ")}</span><span className="font-medium tabular-nums">₹{v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span></div>))}</div>;
}

function SIPCalc() {
  const [m, setM] = useState("5000"); const [y, setY] = useState("10"); const [r, setR] = useState("12");
  const [res, setRes] = useState<Record<string,number>|null>(null);
  const calc = async () => {
    const resp = await apiFetch(`/calculators/sip?monthly=${m}&years=${y}&rate=${r}`);
    const d = await resp.json(); setRes(d.result);
  };
  return <div><Field label="Monthly Investment (₹)" value={m} onChange={setM} /><Field label="Years" value={y} onChange={setY} /><Field label="Expected Return (%)" value={r} onChange={setR} /><button onClick={calc} className="w-full py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">Calculate</button>{res && <Result data={res} />}</div>;
}

function LumpsumCalc() {
  const [p, setP] = useState("100000"); const [y, setY] = useState("10"); const [r, setR] = useState("10");
  const [res, setRes] = useState<Record<string,number>|null>(null);
  const calc = async () => {
    const resp = await apiFetch(`/calculators/lumpsum?principal=${p}&years=${y}&rate=${r}`);
    const d = await resp.json(); setRes(d.result);
  };
  return <div><Field label="Principal (₹)" value={p} onChange={setP} /><Field label="Years" value={y} onChange={setY} /><Field label="Return Rate (%)" value={r} onChange={setR} /><button onClick={calc} className="w-full py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">Calculate</button>{res && <Result data={res} />}</div>;
}

function CAGRCalc() {
  const [i, setI] = useState("100000"); const [f, setF] = useState("250000"); const [y, setY] = useState("5");
  const [res, setRes] = useState<Record<string,number>|null>(null);
  const calc = async () => {
    const resp = await apiFetch(`/calculators/cagr?initial=${i}&final=${f}&years=${y}`);
    const d = await resp.json(); setRes(d.result);
  };
  return <div><Field label="Initial Value (₹)" value={i} onChange={setI} /><Field label="Final Value (₹)" value={f} onChange={setF} /><Field label="Years" value={y} onChange={setY} /><button onClick={calc} className="w-full py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">Calculate</button>{res && <div className="mt-4 space-y-2 pt-4 border-t border-border">{Object.entries(res).map(([k,v])=>(<div key={k} className="flex justify-between text-sm"><span className="text-muted capitalize">{k.replace(/_/g," ")}</span><span className="font-medium tabular-nums">{k==="cagr"?v.toFixed(2)+"%":v.toFixed(2)+"%"}</span></div>))}</div>}</div>;
}

function EMICalc() {
  const [p, setP] = useState("1000000"); const [y, setY] = useState("20"); const [r, setR] = useState("8.5");
  const [res, setRes] = useState<Record<string,number>|null>(null);
  const calc = async () => {
    const resp = await apiFetch(`/calculators/emi?principal=${p}&years=${y}&rate=${r}`);
    const d = await resp.json(); setRes(d.result);
  };
  return <div><Field label="Loan Amount (₹)" value={p} onChange={setP} /><Field label="Tenure (Years)" value={y} onChange={setY} /><Field label="Interest Rate (%)" value={r} onChange={setR} /><button onClick={calc} className="w-full py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">Calculate</button>{res && <div className="mt-4 space-y-2 pt-4 border-t border-border"><div className="text-center"><p className="text-xs text-muted">Monthly EMI</p><p className="text-2xl font-bold text-primary tabular-nums">₹{res.emi.toLocaleString("en-IN")}</p></div><Result data={res} /></div>}</div>;
}

function CompoundCalc() {
  const [p, setP] = useState("100000"); const [y, setY] = useState("10"); const [r, setR] = useState("8"); const [c, setC] = useState("1");
  const [res, setRes] = useState<Record<string,number>|null>(null);
  const calc = async () => {
    const resp = await apiFetch(`/calculators/compound?principal=${p}&years=${y}&rate=${r}&compounding=${c}`);
    const d = await resp.json(); setRes(d.result);
  };
  return <div><Field label="Principal (₹)" value={p} onChange={setP} /><Field label="Years" value={y} onChange={setY} /><Field label="Rate (%)" value={r} onChange={setR} /><Field label="Compounding/year" value={c} onChange={setC} /><button onClick={calc} className="w-full py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">Calculate</button>{res && <Result data={res} />}</div>;
}

function FDCalc() {
  const [p, setP] = useState("100000"); const [y, setY] = useState("5"); const [r, setR] = useState("7");
  const [res, setRes] = useState<Record<string,number>|null>(null);
  const calc = async () => {
    const resp = await apiFetch(`/calculators/fd?principal=${p}&years=${y}&rate=${r}`);
    const d = await resp.json(); setRes(d.result);
  };
  return <div><Field label="Deposit Amount (₹)" value={p} onChange={setP} /><Field label="Years" value={y} onChange={setY} /><Field label="Interest Rate (%)" value={r} onChange={setR} /><button onClick={calc} className="w-full py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">Calculate</button>{res && <Result data={res} />}</div>;
}

function RDCalc() {
  const [m, setM] = useState("5000"); const [mo, setMo] = useState("60"); const [r, setR] = useState("7");
  const [res, setRes] = useState<Record<string,number>|null>(null);
  const calc = async () => {
    const resp = await apiFetch(`/calculators/rd?monthly=${m}&months=${mo}&rate=${r}`);
    const d = await resp.json(); setRes(d.result);
  };
  return <div><Field label="Monthly Deposit (₹)" value={m} onChange={setM} /><Field label="Months" value={mo} onChange={setMo} /><Field label="Interest Rate (%)" value={r} onChange={setR} /><button onClick={calc} className="w-full py-2 bg-primary hover:bg-primary-hover rounded-lg text-sm font-medium">Calculate</button>{res && <Result data={res} />}</div>;
}
