import { useState } from "react";
import { Upload, Download, Loader2, Box, FileText } from "lucide-react";

const API = "";

export default function ConvertPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [converting, setConverting] = useState(false);
  const [result, setResult] = useState<{ output: string; size_kb: number; objects?: number } | null>(null);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true); setError("");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await fetch(`${API}/api/v1/upload`, { method: "POST", body: fd });
      const j = await r.json();
      if (!j.success) throw new Error(j.detail || "Upload failed");
      // Now convert
      setConverting(true);
      const conv = await fetch(`${API}/api/v1/control/tool`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool: "step_to_stl", arguments: { file_name: file.name, output_name: file.name.replace(/\.(step|stp)$/i, ".stl") } }),
      });
      const cj = await conv.json();
      if (cj.success) {
        setResult(cj);
      } else {
        setError(cj.error || "Conversion failed");
      }
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setUploading(false);
      setConverting(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-white">STEP → STL Conversion</h1>
      <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-6 space-y-4">
        <label className="block border-2 border-dashed border-white/10 rounded-xl p-8 text-center cursor-pointer hover:border-indigo-500/40 transition-all">
          <Upload className="mx-auto mb-2 text-slate-500" size={32} />
          <p className="text-slate-400">{file ? file.name : "Drop a STEP file here or click to browse"}</p>
          <input type="file" accept=".step,.stp" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </label>
        <button onClick={handleUpload} disabled={!file || uploading || converting} className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-bold flex items-center justify-center gap-2">
          {uploading || converting ? <Loader2 className="animate-spin" size={18} /> : <Box size={18} />}
          {uploading ? "Uploading..." : converting ? "Converting..." : "Upload & Convert"}
        </button>
        {error && <div className="p-3 rounded-xl bg-red-950/40 border border-red-500/20 text-red-400 text-sm">{error}</div>}
        {result && (
          <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-500/20 space-y-2">
            <p className="text-emerald-400 font-bold flex items-center gap-2"><Download size={16} /> Conversion Complete</p>
            <p className="text-sm text-slate-400">{result.output} — {result.size_kb} KB</p>
            {result.objects && <p className="text-sm text-slate-400">{result.objects} objects exported</p>}
            <a href={`${API}/api/v1/download/${result.output}`} download className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold">
              <Download size={14} /> Download STL
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
