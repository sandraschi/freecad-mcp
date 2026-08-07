import { useEffect, useState } from "react";
import { Box, FileText, Loader2, RefreshCw } from "lucide-react";
import StlViewer from "../components/StlViewer";
import { API_BASE } from "../lib/api";

export default function ModelsPage() {
  const [uploads, setUploads] = useState<{ name: string; size_kb: number }[]>([]);
  const [outputs, setOutputs] = useState<{ name: string; size_kb: number }[]>([]);
  const [gcodes, setGcodes] = useState<{ name: string; size_kb: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [info, setInfo] = useState<any>(null);
  const [selected, setSelected] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(API_BASE + "/api/v1/files"); const j = await r.json();
      setUploads(j.uploads || []); setOutputs(j.outputs || []); setGcodes(j.gcodes || []);
    } catch {} finally { setLoading(false); }
  };

  const getInfo = async (name: string) => {
    setSelected(name); setInfo(null);
    try {
      const r = await fetch(API_BASE + "/api/v1/control/tool", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool: "model_info", arguments: { file_name: name } }),
      });
      setInfo(await r.json());
    } catch {}
  };

  useEffect(() => { load(); }, []);

  const isStl = (name: string) => name.toLowerCase().endsWith(".stl");
  const isStep = (name: string) => /\.(step|stp)$/i.test(name);

  return (
    <div className="max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Models</h1>
        <button onClick={load} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white"><RefreshCw size={14} /> Refresh</button>
      </div>

      {selected && isStl(selected) && (
        <StlViewer url={`/api/v1/download/${selected}`} height={350} />
      )}

      <div className="grid grid-cols-3 gap-6">
        <FileList title="Uploads" files={uploads} loading={loading} selected={selected} onSelect={getInfo} icon={FileText} iconColor="text-indigo-400" />
        <FileList title="Outputs" files={outputs} loading={loading} selected={selected} onSelect={getInfo} icon={Box} iconColor="text-emerald-400" download />
        <FileList title="G-code" files={gcodes} loading={loading} selected={selected} onSelect={() => {}} icon={FileText} iconColor="text-amber-400" download />
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

function FileList({
  title, files, loading, selected, onSelect, icon: Icon, iconColor, download,
}: {
  title: string; files: { name: string; size_kb: number }[]; loading: boolean;
  selected: string; onSelect: (name: string) => void; icon: any; iconColor: string; download?: boolean;
}) {
  return (
    <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-4 space-y-2">
      <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider">{title}</h2>
      {loading ? <Loader2 className="animate-spin" /> : files.length === 0 ? <p className="text-slate-600 text-sm">No files</p> : files.map((f) => (
        <div key={f.name} onClick={() => onSelect(f.name)} className={`flex items-center justify-between p-3 rounded-xl cursor-pointer text-sm ${selected === f.name ? "bg-indigo-500/10 border border-indigo-500/30" : "bg-white/5 hover:bg-white/10"}`}>
          <span className="flex items-center gap-2 truncate"><Icon size={14} className={iconColor} /> {f.name}</span>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-slate-500 text-xs">{f.size_kb} KB</span>
            {download && (
              <a href={`/api/v1/download/${f.name}`} download className="text-emerald-400 hover:text-emerald-300 text-xs font-bold">↓</a>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
