import { Settings as SettingsIcon, Cpu, Globe, Key } from "lucide-react";
import { useEffect, useState } from "react";

export default function SettingsPage() {
  const [ollamaUrl, setOllamaUrl] = useState("http://192.168.1.11:11434");
  const [model, setModel] = useState("gemma3:1b");
  const [thingiverseKey, setThingiverseKey] = useState("");
  const [grabcadKey, setGrabcadKey] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch("/api/v1/settings").then(r => r.json()).then(j => {
      if (j.ollama_url) setOllamaUrl(j.ollama_url);
      if (j.model) setModel(j.model);
      if (j.marketplace?.thingiverse_api_key !== undefined) setThingiverseKey(j.marketplace.thingiverse_api_key);
      if (j.marketplace?.grabcad_api_key !== undefined) setGrabcadKey(j.marketplace.grabcad_api_key);
    }).catch(() => {});
  }, []);

  const save = async () => {
    setStatus("Saving...");
    try {
      const r = await fetch("/api/v1/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ollama_url: ollamaUrl, model, thingiverse_api_key: thingiverseKey, grabcad_api_key: grabcadKey }),
      });
      if (r.ok) setStatus("Saved.");
      else setStatus("Error saving.");
    } catch { setStatus("Error saving."); }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3"><SettingsIcon className="text-indigo-400" /> Settings</h1>

      <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 mb-2"><Cpu size={16} className="text-indigo-400" /><h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">LLM Provider</h3></div>
        <label className="block text-sm text-slate-400">Ollama / LMStudio URL</label>
        <input value={ollamaUrl} onChange={(e) => setOllamaUrl(e.target.value)} className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500/30" />
        <label className="block text-sm text-slate-400">Model</label>
        <input value={model} onChange={(e) => setModel(e.target.value)} className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500/30" />
      </div>

      <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 mb-2"><Key size={16} className="text-amber-400" /><h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Marketplace API Keys</h3></div>
        <p className="text-xs text-slate-600">Some marketplaces require an API key for search. Save your keys here — they persist for the session.</p>

        <label className="block text-sm text-slate-400">
          <span className="flex items-center gap-1.5"><Globe size={12} className="text-cyan-400" /> Thingiverse API Key</span>
        </label>
        <input value={thingiverseKey} onChange={(e) => setThingiverseKey(e.target.value)} placeholder="Paste your Thingiverse access token" className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500/30 font-mono" />

        <label className="block text-sm text-slate-400">
          <span className="flex items-center gap-1.5"><Globe size={12} className="text-blue-400" /> GrabCAD API Key</span>
        </label>
        <input value={grabcadKey} onChange={(e) => setGrabcadKey(e.target.value)} placeholder="Paste your GrabCAD API key" className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500/30 font-mono" />
      </div>

      <button onClick={save} className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold">Save Settings</button>
      {status && <p className="text-sm text-slate-400">{status}</p>}
    </div>
  );
}
