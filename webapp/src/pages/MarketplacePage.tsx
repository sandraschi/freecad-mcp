import { useState, useEffect, useRef } from "react";
import { Search, Download, ExternalLink, Loader2, ShoppingBag, Image, Star, LayoutGrid, List, ChevronLeft, ChevronRight, Upload, CheckCircle, FileText } from "lucide-react";
import { API_BASE } from "../lib/api";

interface ModelResult {
  id: string; title: string; summary: string; author: string;
  downloads: number; likes: number; image_url: string;
  model_url: string; download_url: string; source: string;
}

interface Category { id: string; label: string }

const SOURCES = [
  { key: "printables", label: "Printables", color: "bg-orange-600" },
  { key: "thingiverse", label: "Thingiverse", color: "bg-cyan-600" },
  { key: "grabcad", label: "GrabCAD", color: "bg-blue-600" },
];
const PAGE_SIZE = 20;

export default function MarketplacePage() {
  const [source, setSource] = useState("printables");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);
  const [results, setResults] = useState<ModelResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [viewMode, setViewMode] = useState<"card" | "list">("card");
  const [uploading, setUploading] = useState(false);
  const [recentUploads, setRecentUploads] = useState<{ name: string; title: string }[]>([]);
  const [showDropZone, setShowDropZone] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCount = useRef(0);

  const search = async (p?: number) => {
    const q = query.trim();
    const hasCategory = category !== "";
    if (!q && !hasCategory) return;
    const pageNum = p ?? 1;
    setLoading(true);
    setError("");
    if (p === undefined) setResults([]);
    try {
      const params = new URLSearchParams({ source, query: q || category, limit: String(PAGE_SIZE), page: String(pageNum) });
      if (category) params.set("category", category);
      const r = await fetch(API_BASE + `/api/v1/marketplace/search?${params}`);
      const j = await r.json();
      if (j.success) { setResults(j.results); setTotal(j.total); setPage(pageNum); }
      else { setError(j.error || "Search failed"); }
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const handleFileUpload = async (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !["stl", "step", "stp", "zip"].includes(ext)) {
      setError(`Unsupported format: .${ext}. Use .stl, .step, .stp, or .zip`);
      return;
    }
    setUploading(true);
    setError("");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const r = await fetch(API_BASE + "/api/v1/upload", { method: "POST", body: formData });
      const j = await r.json();
      if (j.success) {
        setRecentUploads((prev) => [{ name: j.filename, title: file.name.replace(/\.[^.]+$/, "") }, ...prev].slice(0, 5));
      } else {
        setError(j.error || "Upload failed");
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) { await handleFileUpload(file); e.target.value = ""; }
  };

  const downloadModel = async (item: ModelResult) => {
    if (!item.download_url) {
      window.open(item.model_url, "_blank", "noopener");
      setShowDropZone(true);
      return;
    }
    setDownloading(item.id);
    try {
      const ext = item.source === "thingiverse" ? ".zip"
        : item.download_url.toLowerCase().includes(".step") ? ".STEP"
        : item.download_url.toLowerCase().includes(".stp") ? ".stp" : ".stl";
      const filename = `${item.title.replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 60)}${ext}`;
      const r = await fetch(API_BASE + "/api/v1/marketplace/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: item.source, model_id: item.id, file_url: item.download_url, filename }),
      });
      const j = await r.json();
      if (j.success) {
        setError("");
        const extracted = j.extracted?.map((f: any) => f.filename).join(", ") || "";
        alert(`Downloaded: ${j.filename} (${(j.size_bytes / 1024).toFixed(1)} KB)${extracted ? `\nExtracted: ${extracted}` : ""}`);
      } else {
        setError(j.error || "Download failed");
      }
    } catch (e: any) { setError(e.message); }
    finally { setDownloading(null); }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Marketplace</h1>
      </div>

      <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-4 space-y-4">
        <div className="flex flex-wrap gap-2">
          {SOURCES.map((s) => (
            <button key={s.key} onClick={() => setSource(s.key)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                source === s.key ? `${s.color} text-white shadow-lg` : "bg-white/5 text-slate-400 hover:bg-white/10"
              }`}
            >{s.label}</button>
          ))}
        </div>

        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input type="text" value={query} onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder={`Search ${SOURCES.find((s) => s.key === source)?.label}... (pick category + Search to browse all)`}
              className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <button onClick={() => search()} disabled={loading}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-sm font-bold flex items-center gap-2"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            Search
          </button>
        </div>

        {categories.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {categories.map((c) => (
              <button key={c.id} onClick={() => setCategory(c.id === category ? "" : c.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  category === c.id
                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                    : c.id === "" ? "bg-white/5 text-slate-400 hover:bg-white/10"
                    : "bg-white/5 text-slate-500 hover:text-slate-300 hover:bg-white/10"
                }`}
              >{c.label}</button>
            ))}
          </div>
        )}

        {error && <p className="text-red-400 text-sm">{error}</p>}
      </div>

      {total > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-slate-500 text-sm">
            Page {page} of {totalPages} — {total} result{total !== 1 ? "s" : ""}
            {category && <span className="text-slate-600"> in <span className="text-indigo-400">{categories.find((c) => c.id === category)?.label}</span></span>}
          </p>
          <div className="flex items-center gap-2">
            <button onClick={() => setViewMode(viewMode === "card" ? "list" : "card")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-all"
            >
              {viewMode === "card" ? <List size={14} /> : <LayoutGrid size={14} />}
              {viewMode === "card" ? "List" : "Cards"}
            </button>
          </div>
        </div>
      )}

      <div className={viewMode === "card" ? "grid grid-cols-2 gap-4" : "space-y-2"}>
        {results.map((item) => viewMode === "card" ? (
          <CardResult key={item.id} item={item} downloading={downloading} onDownload={downloadModel} />
        ) : (
          <ListResult key={item.id} item={item} downloading={downloading} onDownload={downloadModel} />
        ))}
      </div>

      {!loading && results.length === 0 && (query.trim() || category) && !error && (
        <div className="text-center py-12 text-slate-600">
          <ShoppingBag size={48} className="mx-auto mb-4 opacity-30" />
          <p>No results. Try removing the category filter, or use a shorter search term.</p>
        </div>
      )}

      {showDropZone && (
        <div
          onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add("border-indigo-500"); }}
          onDragLeave={(e) => { e.currentTarget.classList.remove("border-indigo-500"); }}
          onDrop={async (e) => { e.preventDefault(); e.currentTarget.classList.remove("border-indigo-500"); const f = e.dataTransfer.files[0]; if (f) await handleFileUpload(f); }}
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-white/10 hover:border-indigo-500/50 rounded-2xl p-6 text-center cursor-pointer transition-all group"
        >
          <input ref={fileInputRef} type="file" accept=".stl,.step,.stp,.zip" onChange={handleFile} className="hidden" />
          {uploading ? (
            <div className="flex items-center justify-center gap-2 text-slate-400"><Loader2 size={20} className="animate-spin" /> Uploading...</div>
          ) : (
            <div className="space-y-2">
              <Upload size={28} className="mx-auto text-slate-500 group-hover:text-indigo-400 transition-colors" />
              <p className="text-sm text-slate-400">Downloaded from the marketplace? <strong className="text-indigo-400">Drop your file here</strong> or click to select</p>
              <p className="text-xs text-slate-600">STL / STEP / ZIP files only</p>
            </div>
          )}
        </div>
      )}

      {recentUploads.length > 0 && (
        <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-4 space-y-2">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Recently imported to depot</h3>
          {recentUploads.map((u) => (
            <a key={u.name} href={`/api/v1/download/${u.name}`} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-2 p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-sm text-slate-300 transition-all group"
            >
              <FileText size={14} className="text-indigo-400 shrink-0" />
              <span className="truncate">{u.title}</span>
              <span className="text-xs text-slate-600 shrink-0 ml-auto">View in Models →</span>
            </a>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-2">
          <button onClick={() => search(page - 1)} disabled={page <= 1 || loading}
            className="flex items-center gap-1 px-4 py-2 rounded-xl text-sm font-bold bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-20 disabled:hover:bg-white/5 transition-all"
          ><ChevronLeft size={16} /> Previous</button>
          <span className="text-slate-600 text-sm">Page {page} of {totalPages}</span>
          <button onClick={() => search(page + 1)} disabled={page >= totalPages || loading}
            className="flex items-center gap-1 px-4 py-2 rounded-xl text-sm font-bold bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-20 disabled:hover:bg-white/5 transition-all"
          >Next <ChevronRight size={16} /></button>
        </div>
      )}
    </div>
  );
}

function CardResult({ item, downloading, onDownload }: { item: ModelResult; downloading: string | null; onDownload: (item: ModelResult) => void }) {
  return (
    <div className="bg-[#0f0f12] border border-white/5 rounded-2xl overflow-hidden hover:border-indigo-500/30 transition-all">
      <div className="h-40 bg-[#1a1a1f] flex items-center justify-center overflow-hidden">
        {item.image_url ? <img src={item.image_url} alt={item.title} className="w-full h-full object-cover" loading="lazy" /> : <Image size={48} className="text-slate-700" />}
      </div>
      <div className="p-4 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-bold text-white line-clamp-2 leading-tight">{item.title}</h3>
          <a href={item.model_url} target="_blank" rel="noopener noreferrer" className="text-slate-600 hover:text-slate-400 shrink-0"><ExternalLink size={14} /></a>
        </div>
        {item.author && <p className="text-xs text-slate-500">by {item.author}</p>}
        {item.summary && <p className="text-xs text-slate-600 line-clamp-2">{item.summary}</p>}
        <div className="flex items-center justify-between pt-2 border-t border-white/5">
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1"><Download size={12} /> {item.downloads.toLocaleString()}</span>
            <span className="flex items-center gap-1"><Star size={12} /> {item.likes.toLocaleString()}</span>
          </div>
          <button onClick={() => onDownload(item)} disabled={downloading === item.id}
            className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/40 disabled:opacity-30 text-indigo-400 rounded-lg text-xs font-bold transition-all"
          >{downloading === item.id ? <Loader2 size={12} className="animate-spin" /> : item.download_url ? <><Download size={12} /> Import</> : "Open ↗"}</button>
        </div>
      </div>
    </div>
  );
}

function ListResult({ item, downloading, onDownload }: { item: ModelResult; downloading: string | null; onDownload: (item: ModelResult) => void }) {
  return (
    <div className="bg-[#0f0f12] border border-white/5 rounded-xl p-3 flex items-center gap-4 hover:border-indigo-500/30 transition-all">
      <div className="w-16 h-16 shrink-0 bg-[#1a1a1f] rounded-lg overflow-hidden flex items-center justify-center">
        {item.image_url ? <img src={item.image_url} alt={item.title} className="w-full h-full object-cover" loading="lazy" /> : <Image size={20} className="text-slate-700" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-white truncate">{item.title}</h3>
          <a href={item.model_url} target="_blank" rel="noopener noreferrer" className="text-slate-600 hover:text-slate-400 shrink-0"><ExternalLink size={12} /></a>
        </div>
        {item.author && <p className="text-xs text-slate-500">by {item.author}</p>}
        {item.summary && <p className="text-xs text-slate-600 truncate">{item.summary}</p>}
      </div>
      <div className="flex items-center gap-3 text-xs text-slate-500 shrink-0">
        <span className="flex items-center gap-1"><Download size={12} /> {item.downloads.toLocaleString()}</span>
        <span className="flex items-center gap-1"><Star size={12} /> {item.likes.toLocaleString()}</span>
      </div>
      <button onClick={() => onDownload(item)} disabled={downloading === item.id}
        className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/40 disabled:opacity-30 text-indigo-400 rounded-lg text-xs font-bold transition-all shrink-0"
      >{downloading === item.id ? <Loader2 size={12} className="animate-spin" /> : item.download_url ? <><Download size={12} /> Import</> : "Open ↗"}</button>
    </div>
  );
}
