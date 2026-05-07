import { useEffect, useState } from "react";
import { Box, CheckCircle2, Cpu, FileText, Gauge, Loader2, XCircle } from "lucide-react";

export default function Dashboard() {
  const [status, setStatus] = useState<any>(null);
  const [files, setFiles] = useState<{ uploads: number; outputs: number }>({ uploads: 0, outputs: 0 });

  useEffect(() => {
    fetch("/api/v1/status").then(r => r.json()).then(setStatus).catch(() => setStatus({ freecad_ok: false }));
    fetch("/api/v1/files").then(r => r.json()).then(j => setFiles({ uploads: (j.uploads || []).length, outputs: (j.outputs || []).length })).catch(() => {});
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-indigo-400"><Cpu size={18} /> FreeCAD Engine</div>
          {status?.freecad_ok === undefined ? <Loader2 className="animate-spin" /> : (
            <div className="flex items-center gap-2 text-sm">
              {status.freecad_ok ? <CheckCircle2 size={16} className="text-emerald-400" /> : <XCircle size={16} className="text-red-400" />}
              <span className="text-slate-300">{status.freecad_ok ? status.freecad_version?.split(" ").slice(0, 2).join(" ") : "Not found"}</span>
            </div>
          )}
          <p className="text-xs text-slate-600">{status?.bridge_mode === "tcp" ? "TCP Bridge (AP214 capable)" : "Subprocess (limited STEP)"}</p>
        </div>
        <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-emerald-400"><Box size={18} /> Files</div>
          <p className="text-2xl font-bold text-white">{files.uploads} <span className="text-sm font-normal text-slate-500">uploads</span></p>
          <p className="text-2xl font-bold text-white">{files.outputs} <span className="text-sm font-normal text-slate-500">STL outputs</span></p>
        </div>
        <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-amber-400"><Gauge size={18} /> Quick Actions</div>
          <a href="/convert" className="block text-sm text-indigo-400 hover:underline">Convert STEP → STL</a>
          <a href="/chat" className="block text-sm text-indigo-400 hover:underline">Ask CAD Expert</a>
          <a href="/help" className="block text-sm text-indigo-400 hover:underline">FreeCAD Help</a>
        </div>
      </div>
    </div>
  );
}
