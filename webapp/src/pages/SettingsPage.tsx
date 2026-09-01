import {
	AlertTriangle,
	CheckCircle2,
	Cpu,
	Globe,
	Key,
	Loader2,
	RefreshCw,
	Settings as SettingsIcon,
	XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { API } from "../lib/api";

interface ProviderInfo {
	name: string;
	base: string;
	models: string[];
	status: string;
}

interface DiscoverResult {
	providers: ProviderInfo[];
	status: Record<string, string>;
	selected_provider: string;
	selected_model: string;
}

export default function SettingsPage() {
	const [ollamaUrl, setOllamaUrl] = useState("http://127.0.0.1:11434");
	const [model, setModel] = useState("gemma3:1b");
	const [provider, setProvider] = useState("ollama");
	const [thingiverseKey, setThingiverseKey] = useState("");
	const [grabcadKey, setGrabcadKey] = useState("");
	const [status, setStatus] = useState("");

	const [discover, setDiscover] = useState<DiscoverResult | null>(null);
	const [probing, setProbing] = useState(true);
	const [detectedProviders, setDetectedProviders] = useState<ProviderInfo[]>([]);
	const [availableModels, setAvailableModels] = useState<string[]>([]);

	useEffect(() => {
		fetchSettings();
		discoverProviders();
	}, []);

	const fetchSettings = async () => {
		try {
			const r = await fetch(`${API}/settings`);
			const j = await r.json();
			if (j.ollama_url) setOllamaUrl(j.ollama_url);
			if (j.model) setModel(j.model);
			if (j.marketplace?.thingiverse_api_key !== undefined) setThingiverseKey(j.marketplace.thingiverse_api_key);
			if (j.marketplace?.grabcad_api_key !== undefined) setGrabcadKey(j.marketplace.grabcad_api_key);
		} catch {}
	};

	const discoverProviders = async () => {
		setProbing(true);
		try {
			const r = await fetch(`${API.replace("/api/v1", "")}/api/llm/discover`);
			const j: DiscoverResult = await r.json();
			setDiscover(j);
			const detected = j.providers.filter((p) => p.status === "detected");
			setDetectedProviders(detected);

			// Restore saved provider if still detected
			const savedProvider = localStorage.getItem("llm_provider");
			const savedModel = localStorage.getItem("llm_model");
			const activeProvider =
				savedProvider && detected.find((p) => p.name === savedProvider) ? savedProvider : detected[0]?.name || "ollama";
			setProvider(activeProvider);

			const prov = detected.find((p) => p.name === activeProvider);
			setAvailableModels(prov?.models || []);

			// Restore saved model if still available
			if (savedModel && prov?.models.includes(savedModel)) {
				setModel(savedModel);
			} else if (prov?.models.length) {
				setModel(prov.models[0]);
			}
		} catch {
			setDiscover(null);
		} finally {
			setProbing(false);
		}
	};

	const onProviderChange = (newProvider: string) => {
		setProvider(newProvider);
		localStorage.setItem("llm_provider", newProvider);
		const prov = detectedProviders.find((p) => p.name === newProvider);
		setAvailableModels(prov?.models || []);
		if (prov?.models.length) {
			setModel(prov.models[0]);
			localStorage.setItem("llm_model", prov.models[0]);
		}
	};

	const onModelChange = (newModel: string) => {
		setModel(newModel);
		localStorage.setItem("llm_model", newModel);
	};

	const save = async () => {
		setStatus("Saving...");
		try {
			const r = await fetch(`${API}/settings`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					ollama_url: ollamaUrl,
					model,
					thingiverse_api_key: thingiverseKey,
					grabcad_api_key: grabcadKey,
				}),
			});
			if (r.ok) setStatus("Saved.");
			else setStatus("Error saving.");
		} catch {
			setStatus("Error saving.");
		}
	};

	const ProviderStatusIcon = ({ name }: { name: string }) => {
		const s = discover?.status[name];
		if (probing) return <Loader2 size={14} className="animate-spin text-slate-500" />;
		if (s === "detected") return <CheckCircle2 size={14} className="text-emerald-400" />;
		return <XCircle size={14} className="text-slate-600" />;
	};

	return (
		<div className="max-w-2xl space-y-6" data-testid="settings-page">
			<h1 className="text-2xl font-bold text-white flex items-center gap-3">
				<SettingsIcon className="text-indigo-400" /> Settings
			</h1>

			{/* LLM Provider Detection */}
			<div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-6 space-y-4" data-testid="llm-section">
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-2">
						<Cpu size={16} className="text-indigo-400" />
						<h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">LLM Provider</h3>
					</div>
					<button
						onClick={discoverProviders}
						className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-all"
					>
						<RefreshCw size={12} className={probing ? "animate-spin" : ""} /> Refresh
					</button>
				</div>

				{/* Provider probes */}
				<div className="grid grid-cols-3 gap-2">
					{[
						{ id: "ollama", label: "Ollama", port: 11434 },
						{ id: "lm_studio", label: "LM Studio", port: 1234 },
						{ id: "vllm", label: "vLLM", port: 8000 },
					].map((p) => (
						<div
							key={p.id}
							className={`flex items-center gap-2 p-3 rounded-xl border text-xs ${discover?.status[p.id] === "detected" ? "bg-emerald-500/10 border-emerald-500/20" : "bg-white/5 border-white/10"}`}
						>
							<ProviderStatusIcon name={p.id} />
							<div>
								<p className="text-slate-300 font-medium">{p.label}</p>
								<p className="text-slate-600">:{p.port}</p>
							</div>
						</div>
					))}
				</div>

				{/* GPU opportunity prompt */}
				{!detectedProviders.length && !probing && (
					<div className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
						<AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
						<p className="text-xs text-amber-200">
							Install Ollama or LM Studio to enable local AI features.{" "}
							<a
								href="https://ollama.com"
								target="_blank"
								rel="noopener noreferrer"
								className="text-indigo-400 hover:underline"
							>
								ollama.com
							</a>
						</p>
					</div>
				)}

				{/* Provider selector */}
				<div>
					<label className="block text-sm text-slate-400 mb-1">Provider</label>
					<select
						value={provider}
						onChange={(e) => onProviderChange(e.target.value)}
						data-testid="llm-provider-select"
						className="w-full bg-zinc-800 text-zinc-100 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-indigo-500/30"
					>
						{detectedProviders.length ? (
							detectedProviders.map((p) => (
								<option key={p.name} value={p.name}>
									{p.name.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
								</option>
							))
						) : (
							<option value="" disabled>
								No local LLM detected
							</option>
						)}
					</select>
				</div>

				{/* Model selector */}
				<div>
					<label className="block text-sm text-slate-400 mb-1">Model</label>
					<select
						value={model}
						onChange={(e) => onModelChange(e.target.value)}
						data-testid="llm-model-select"
						className="w-full bg-zinc-800 text-zinc-100 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-indigo-500/30"
					>
						{availableModels.length ? (
							availableModels.map((m) => (
								<option key={m} value={m}>
									{m}
								</option>
							))
						) : (
							<option value={model}>{model}</option>
						)}
					</select>
				</div>

				{/* Fallback URL input (for custom endpoints) */}
				<div>
					<label className="block text-sm text-slate-400 mb-1">Custom API URL</label>
					<input
						value={ollamaUrl}
						onChange={(e) => setOllamaUrl(e.target.value)}
						className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500/30"
					/>
				</div>
			</div>

			{/* Marketplace API Keys */}
			<div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-6 space-y-4">
				<div className="flex items-center gap-2 mb-2">
					<Key size={16} className="text-amber-400" />
					<h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Marketplace API Keys</h3>
				</div>
				<p className="text-xs text-slate-600">
					Some marketplaces require an API key for search. Save your keys here — they persist for the session.
				</p>

				<label className="block text-sm text-slate-400">
					<span className="flex items-center gap-1.5">
						<Globe size={12} className="text-cyan-400" /> Thingiverse API Key
					</span>
				</label>
				<input
					value={thingiverseKey}
					onChange={(e) => setThingiverseKey(e.target.value)}
					placeholder="Paste your Thingiverse access token"
					className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500/30 font-mono"
				/>

				<label className="block text-sm text-slate-400">
					<span className="flex items-center gap-1.5">
						<Globe size={12} className="text-blue-400" /> GrabCAD API Key
					</span>
				</label>
				<input
					value={grabcadKey}
					onChange={(e) => setGrabcadKey(e.target.value)}
					placeholder="Paste your GrabCAD API key"
					className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500/30 font-mono"
				/>
			</div>

			<button
				onClick={save}
				className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold"
			>
				Save Settings
			</button>
			{status && <p className="text-sm text-slate-400">{status}</p>}
		</div>
	);
}
