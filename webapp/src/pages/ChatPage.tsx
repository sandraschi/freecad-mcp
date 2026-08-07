import { Bot, Loader2, Send, Download, Trash2 } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { API_BASE } from "../lib/api";

const LS_KEY = "freecad-mcp-chat-history";
const PERS_KEY = "freecad-mcp-chat-personality";

const SYSTEM_PROMPT = "You are a CAD expert assistant specialised in FreeCAD, OpenCASCADE, STEP/STL conversion, parametric modelling, and mechanical design. Help the user with CAD questions, FreeCAD usage, file format conversions, and design best practices. Keep answers concise and technically accurate.";

interface Msg { role: "user" | "assistant"; content: string; }

const PERSONALITIES = [
  { id: "cad-expert", label: "CAD Expert", prompt: "You are a CAD expert. Explain parametric modelling and FreeCAD workflows." },
  { id: "mechanical-designer", label: "Mechanical Designer", prompt: "You are a mechanical designer. Focus on practical design and manufacturing." },
  { id: "quick-summarizer", label: "Quick Summarizer", prompt: "Keep responses brief and to the point." },
  { id: "custom", label: "Custom", prompt: "" },
];

const EXAMPLE_PROMPTS = [
  { group: "FreeCAD", items: ["How do I create a parametric sketch?", "Explain the Part Design workbench", "How to export STL from FreeCAD?"] },
  { group: "Modelling", items: ["Create a simple bracket", "How to use constraints?", "Tips for fillet and chamfer"] },
  { group: "Conversion", items: ["Convert STEP to STL", "How to repair meshes?", "Import DXF and extrude"] },
];

function loadHistory(): Msg[] {
  try { const d = localStorage.getItem(LS_KEY); return d ? JSON.parse(d) : [{ role: "assistant" as const, content: "Hi! I'm your CAD expert. Ask me about FreeCAD, STEP/STL conversion, parametric modelling, or mechanical design." }]; } catch { return [{ role: "assistant" as const, content: "Hi! I'm your CAD expert. Ask me about FreeCAD, STEP/STL conversion, parametric modelling, or mechanical design." }]; }
}
function saveHistory(msgs: Msg[]) { try { localStorage.setItem(LS_KEY, JSON.stringify(msgs.slice(-100))); } catch {} }
function loadPersonality(): string { try { return localStorage.getItem(PERS_KEY) || "cad-expert"; } catch { return "cad-expert"; } }

export default function ChatPage() {
  const [msgs, setMsgs] = useState<Msg[]>(() => loadHistory());
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState("gemma3:1b");
  const [personalityId, setPersonalityId] = useState(() => loadPersonality());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView(); }, [msgs]);
  useEffect(() => { saveHistory(msgs); }, [msgs]);
  useEffect(() => { localStorage.setItem(PERS_KEY, personalityId); }, [personalityId]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Msg = { role: "user", content: input.trim() };
    setMsgs((p) => [...p, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const r = await fetch(API_BASE + "/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [...msgs, userMsg], system: SYSTEM_PROMPT, provider, model, personality: personalityId }),
      });
      const j = await r.json();
      setMsgs((p) => [...p, { role: "assistant", content: j.content || "No response." }]);
    } catch {
      setMsgs((p) => [...p, { role: "assistant", content: "Error: chat unreachable." }]);
    } finally { setLoading(false); }
  };

  const exportChat = () => {
    const text = msgs.map(m => `${m.role === "user" ? "You" : "CAD Expert"}: ${m.content}`).join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `freecad-chat-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto space-y-4" data-testid="chat-page">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-white flex items-center gap-3"><Bot className="text-indigo-400" /> CAD Expert</h1>
          <span className="text-xs text-indigo-400 bg-indigo-900/30 px-2 py-0.5 rounded border border-indigo-800/50" data-testid="skill-badge">freecad-mcp</span>
        </div>
        <div className="flex items-center gap-2" data-testid="chat-controls">
          <span className={`inline-block w-2 h-2 rounded-full ${provider ? "bg-green-500" : "bg-red-500"}`} data-testid="backend-dot" />
          <select value={personalityId} onChange={(e) => setPersonalityId(e.target.value)} className="rounded-md border border-white/10 bg-zinc-900 px-2 py-1 text-xs text-slate-200" data-testid="personality-select">
            {PERSONALITIES.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
          <button type="button" onClick={exportChat} disabled={msgs.length === 0} className="text-xs text-slate-400 hover:text-white p-1" data-testid="chat-export"><Download size={14} /></button>
          <button type="button" onClick={() => setMsgs([])} disabled={msgs.length === 0} className="text-xs text-red-400 hover:text-red-300 p-1" data-testid="chat-clear"><Trash2 size={14} /></button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto space-y-3 p-4 bg-[#0f0f12] border border-white/5 rounded-2xl" data-testid="chat-messages">
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] p-3 rounded-2xl text-sm ${m.role === "user" ? "bg-indigo-600 text-white" : "bg-white/5 text-slate-300"}`}>{m.content}</div>
          </div>
        ))}
        {loading && <div className="flex justify-start"><Loader2 className="animate-spin text-indigo-400" /></div>}
        <div ref={bottomRef} />
      </div>
      <div className="space-y-2">
        <div className="flex flex-wrap gap-1" data-testid="example-prompts">
          {EXAMPLE_PROMPTS.flatMap(g => g.items).map((p, i) => (
            <button key={i} type="button" onClick={() => setInput(p)} className="text-xs bg-white/5 hover:bg-white/10 text-slate-400 px-2 py-1 rounded border border-white/10 transition-colors">{p}</button>
          ))}
        </div>
        <div className="flex gap-3">
          <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask about FreeCAD, STEP files, modelling..." className="flex-1 bg-[#0f0f12] border border-white/5 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-indigo-500/30" data-testid="chat-input" />
          <button onClick={send} disabled={loading || !input.trim()} className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-bold" data-testid="chat-send"><Send size={16} /></button>
        </div>
      </div>
    </div>
  );
}
