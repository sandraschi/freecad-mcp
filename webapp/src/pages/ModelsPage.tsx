import { useEffect, useState } from "react";
import { Box, FileText, Loader2, RefreshCw } from "lucide-react";

export default function ModelsPage() {
  const [uploads, setUploads] = useState<{ name: string; size_kb: number }[]>([]);
  const [outputs, setOutputs] = useState<{ name: string; size_kb: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [info, setInfo] = useState<any>(null);
  const [selected, setSelected] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/v1/files"); const j = await r.json();
      setUploads(j.uploads || []); setOutputs(j.outputs || []);
    } catch {} finally { setLoading(false); }
  };

  const getInfo = async (name: string) => {
    setSelected(name); setInfo(null);
    try {
      const r = await fetch("/api/v1/control/tool", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool: "model_info", arguments: { file_name: name } }),
      });
      setInfo(await r.json());
    } catch {}
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Models</h1>
        <button onClick={load} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white"><RefreshCw size={14} /> Refresh</button>
      </div>
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-4 space-y-2">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Uploads</h2>
          {loading ? <Loader2 className="animate-spin" /> : uploads.length === 0 ? <p className="text-slate-600 text-sm">No files</p> : uploads.map((f) => (
            <div key={f.name} onClick={() => getInfo(f.name)} className={`flex items-center justify-between p-3 rounded-xl cursor-pointer text-sm ${selected === f.name ? "bg-indigo-500/10 border border-indigo-500/30" : "bg-white/5 hover:bg-white/10"}`}>
              <span className="flex items-center gap-2"><FileText size={14} className="text-indigo-400"/> {f.name}</span>
              <span className="text-slate-500">{f.size_kb} KB</span>
            </div>
          ))}
        </div>
        <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-4 space-y-2">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Outputs</h2>
          {outputs.length === 0 ? <p className="text-slate-600 text-sm">No STL files yet</p> : outputs.map((f) => (
            <div key={f.name} className="flex items-center justify-between p-3 rounded-xl bg-white/5 text-sm">
              <span className="flex items-center gap-2"><Box size={14} className="text-emerald-400"/> {f.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-slate-500">{f.size_kb} KB</span>
                <a href={`/api/v1/download/${f.name}`} download className="text-emerald-400 hover:text-emerald-300 text-xs font-bold">↓</a>
              </div>
            </div>
          ))}
        </div>
      </div>
      {info && (
        <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-4 space-y-2">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Model Info — {selected}</h2>
          <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap">{JSON.stringify(info.data || info, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
