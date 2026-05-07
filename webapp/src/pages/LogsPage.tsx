import { Activity, Circle, Download, Filter, Pause, Play, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export default function LogsPage() {
  const [lines, setLines] = useState<string[]>([]);
  const [paused, setPaused] = useState(false);
  const [sseState, setSseState] = useState<"connecting" | "open" | "error">("connecting");
  const [filter, setFilter] = useState("");
  const pausedRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => { pausedRef.current = paused; }, [paused]);

  useEffect(() => {
    let es: EventSource | null = new EventSource("/api/v1/logs/stream");
    setSseState("connecting");
    es.onopen = () => setSseState("open");
    es.onmessage = (ev) => { if (!pausedRef.current) setLines((p) => [...p.slice(-1999), ev.data]); };
    es.onerror = () => { setSseState("error"); es?.close(); };
    return () => { es?.close(); };
  }, []);

  useEffect(() => { if (!paused) bottomRef.current?.scrollIntoView(); }, [lines, paused]);

  const display = useMemo(() => {
    if (!filter.trim()) return lines;
    return lines.filter((l) => l.toLowerCase().includes(filter.toLowerCase()));
  }, [lines, filter]);

  return (
    <div className="space-y-4 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3"><Activity className="text-emerald-500" /> Server Logs</h1>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/10 bg-[#0f0f12] flex-1 min-w-[200px] max-w-sm">
          <Filter size={14} className="text-slate-500 shrink-0" />
          <input type="text" placeholder="Filter..." value={filter} onChange={(e) => setFilter(e.target.value)} className="bg-transparent text-sm text-slate-200 placeholder-slate-600 outline-none w-full" />
        </div>
        <span className={`text-xs font-mono px-2.5 py-1.5 rounded-lg border ${sseState === "open" ? "border-emerald-500/30 text-emerald-400" : "border-red-500/30 text-red-400"}`}>SSE {sseState}</span>
        <button onClick={() => setPaused((p) => !p)} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-white/10 text-xs text-slate-300 hover:bg-white/5">{paused ? <Play size={12} /> : <Pause size={12} />} {paused ? "Tail" : "Pause"}</button>
        <button onClick={() => { const b = new Blob([lines.join("\n")], { type: "text/plain" }); const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = "freecad-mcp.log"; a.click(); }} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-emerald-500/20 text-xs text-emerald-300 hover:bg-emerald-500/10"><Download size={12} /> Export</button>
        <button onClick={() => setLines([])} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-red-500/20 text-xs text-red-300 hover:bg-red-500/10"><Trash2 size={12} /> Clear</button>
      </div>
      <div className="bg-[#0a0a0c] border border-white/5 rounded-xl overflow-hidden">
        <div className="px-4 py-2 border-b border-white/5 flex items-center justify-between text-xs text-slate-500">
          <span className="flex items-center gap-2"><Circle size={6} className="fill-emerald-500 text-emerald-500" /> /api/v1/logs/stream</span>
          <span>{display.length} lines</span>
        </div>
        <div className="h-[60vh] overflow-y-auto p-4 font-mono text-sm text-slate-300 whitespace-pre-wrap break-all">
          {display.length === 0 ? <span className="text-slate-600 italic">No log lines.</span> : display.map((l, i) => <div key={i} className="hover:bg-white/[0.02] py-px">{l}</div>)}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
