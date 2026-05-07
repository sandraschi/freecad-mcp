import { Bot, Loader2, Send } from "lucide-react";
import { useState, useRef, useEffect } from "react";

const SYSTEM_PROMPT = "You are a CAD expert assistant specialised in FreeCAD, OpenCASCADE, STEP/STL conversion, parametric modelling, and mechanical design. Help the user with CAD questions, FreeCAD usage, file format conversions, and design best practices. Keep answers concise and technically accurate.";

interface Msg { role: "user" | "assistant"; content: string; }

export default function ChatPage() {
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "assistant", content: "Hi! I'm your CAD expert. Ask me about FreeCAD, STEP/STL conversion, parametric modelling, or mechanical design." }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState("gemma3:1b");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView(); }, [msgs]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Msg = { role: "user", content: input.trim() };
    setMsgs((p) => [...p, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const r = await fetch("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [...msgs, userMsg], system: SYSTEM_PROMPT, provider, model }),
      });
      const j = await r.json();
      setMsgs((p) => [...p, { role: "assistant", content: j.content || "No response." }]);
    } catch {
      setMsgs((p) => [...p, { role: "assistant", content: "Error: chat unreachable." }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3"><Bot className="text-indigo-400" /> CAD Expert</h1>
      <div className="flex-1 overflow-y-auto space-y-3 p-4 bg-[#0f0f12] border border-white/5 rounded-2xl">
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] p-3 rounded-2xl text-sm ${m.role === "user" ? "bg-indigo-600 text-white" : "bg-white/5 text-slate-300"}`}>{m.content}</div>
          </div>
        ))}
        {loading && <div className="flex justify-start"><Loader2 className="animate-spin text-indigo-400" /></div>}
        <div ref={bottomRef} />
      </div>
      <div className="flex gap-3">
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask about FreeCAD, STEP files, modelling..." className="flex-1 bg-[#0f0f12] border border-white/5 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-indigo-500/30" />
        <button onClick={send} disabled={loading || !input.trim()} className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-bold"><Send size={16} /></button>
      </div>
    </div>
  );
}
