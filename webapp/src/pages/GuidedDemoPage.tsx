import {
	AlertCircle,
	ArrowRight,
	Box,
	Car,
	CheckCircle2,
	Database,
	Download,
	Loader2,
	Pencil,
	PlayCircle,
	RefreshCw,
	Trash2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import StlViewer from "../components/StlViewer";
import { API_BASE } from "../lib/api";

type Metrics = {
	volume_mm3?: number;
	size_kb?: number;
	wheels?: number;
	car_source?: string;
	shape_type?: string;
};

type Built = { file: string; metrics: Metrics };

type DepotFile = {
	name: string;
	size_kb: number;
	modified: string;
	meta?: { description?: string };
};

async function callTool(tool: string, args: Record<string, unknown>): Promise<Record<string, any>> {
	const res = await fetch(`${API_BASE}/api/v1/control/tool`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ tool, arguments: args }),
	});
	const data = await res.json();
	if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
	const result = data.result ?? data;
	if (!result.success) throw new Error(result.error || result.message || `${tool} failed`);
	return result;
}

/** Hands-Off wraps the FreeCAD script payload one level deeper than Hands-In. */
function metricsOf(result: Record<string, any>): Metrics {
	return result.data?.data ?? result.data ?? {};
}

export default function GuidedDemoPage() {
	const [log, setLog] = useState<string[]>([]);
	const pushLog = useCallback((message: string) => {
		setLog((entries) => [`${new Date().toLocaleTimeString()}  ${message}`, ...entries].slice(0, 12));
	}, []);

	// Step 1 - cube
	const [cubeSize, setCubeSize] = useState({ width: 20, height: 20, depth: 20 });
	const [cubeBusy, setCubeBusy] = useState(false);
	const [cubeSaving, setCubeSaving] = useState(false);
	const [cube, setCube] = useState<Built | null>(null);
	const [cubeError, setCubeError] = useState("");

	// Step 2 - car
	const [carSource, setCarSource] = useState<"parametric" | "auto">("parametric");
	const [carBusy, setCarBusy] = useState(false);
	const [carSaving, setCarSaving] = useState(false);
	const [car, setCar] = useState<Built | null>(null);
	const [carError, setCarError] = useState("");

	// Step 3 - depot
	const [files, setFiles] = useState<DepotFile[]>([]);
	const [depotBusy, setDepotBusy] = useState(false);
	const [depotError, setDepotError] = useState("");
	const [selected, setSelected] = useState("");
	const [renameValue, setRenameValue] = useState("");

	const loadDepot = useCallback(async () => {
		setDepotBusy(true);
		setDepotError("");
		try {
			const res = await fetch(`${API_BASE}/api/v1/depot`);
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			const data = await res.json();
			setFiles(data.files ?? []);
		} catch (err: any) {
			setDepotError(err.message || "Could not load the depot");
		} finally {
			setDepotBusy(false);
		}
	}, []);

	useEffect(() => {
		void loadDepot();
	}, [loadDepot]);

	const buildCube = async () => {
		setCubeBusy(true);
		setCubeError("");
		try {
			const result = await callTool("freecad_model", {
				operation: "create_primitive",
				primitive_type: "box",
				params: cubeSize,
				output_name: "demo_cube.stl",
			});
			const built = { file: result.output || "demo_cube.stl", metrics: metricsOf(result) };
			setCube(built);
			pushLog(`cube built: ${built.file} (${built.metrics.size_kb ?? "?"} kB)`);
		} catch (err: any) {
			setCube(null);
			setCubeError(err.message || "Cube build failed");
			pushLog(`cube failed: ${err.message}`);
		} finally {
			setCubeBusy(false);
		}
	};

	const buildCar = async () => {
		setCarBusy(true);
		setCarError("");
		try {
			const result = await callTool("freecad_model", {
				operation: "toy_car",
				car_source: carSource,
				output_name: "demo_car.stl",
				body_length_mm: 90,
				body_width_mm: 45,
				body_height_mm: 35,
				wheel_radius_mm: 10,
				wheelbase_mm: 70,
			});
			const built = { file: result.output || "demo_car.stl", metrics: metricsOf(result) };
			setCar(built);
			pushLog(`car built: ${built.file} via ${built.metrics.car_source ?? carSource}`);
		} catch (err: any) {
			setCar(null);
			setCarError(err.message || "Car build failed");
			pushLog(`car failed: ${err.message}`);
		} finally {
			setCarBusy(false);
		}
	};

	const saveToDepot = async (file: string, setBusy: (v: boolean) => void) => {
		setBusy(true);
		try {
			const fileRes = await fetch(`${API_BASE}/api/v1/download/${encodeURIComponent(file)}`);
			if (!fileRes.ok) throw new Error(`STL not available (${fileRes.status})`);
			const blob = await fileRes.blob();
			const form = new FormData();
			form.append("file", blob, file);
			const upload = await fetch(`${API_BASE}/api/v1/depot/upload`, { method: "POST", body: form });
			if (upload.status === 409) {
				pushLog(`${file} is already in the depot`);
			} else {
				const data = await upload.json();
				if (!data.success) throw new Error(data.detail || data.error || "Upload failed");
				pushLog(`${file} saved to depot (${data.size_bytes} B)`);
			}
			await loadDepot();
		} catch (err: any) {
			setDepotError(err.message || "Saving to depot failed");
			pushLog(`save failed: ${err.message}`);
		} finally {
			setBusy(false);
		}
	};

	const renameSelected = async () => {
		if (!selected || !renameValue.trim()) return;
		setDepotBusy(true);
		setDepotError("");
		try {
			const res = await fetch(`${API_BASE}/api/v1/depot/${encodeURIComponent(selected)}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ name: renameValue.trim() }),
			});
			if (!res.ok) {
				const data = await res.json();
				throw new Error(data.detail || "Rename failed");
			}
			pushLog(`renamed ${selected} -> ${renameValue.trim()}`);
			setSelected(renameValue.trim());
			setRenameValue("");
			await loadDepot();
		} catch (err: any) {
			setDepotError(err.message || "Rename failed");
		} finally {
			setDepotBusy(false);
		}
	};

	const deleteSelected = async () => {
		if (!selected) return;
		setDepotBusy(true);
		setDepotError("");
		try {
			const res = await fetch(`${API_BASE}/api/v1/depot/${encodeURIComponent(selected)}`, { method: "DELETE" });
			if (!res.ok) {
				const data = await res.json();
				throw new Error(data.detail || "Delete failed");
			}
			pushLog(`deleted ${selected}`);
			setSelected("");
			setRenameValue("");
			await loadDepot();
		} catch (err: any) {
			setDepotError(err.message || "Delete failed");
		} finally {
			setDepotBusy(false);
		}
	};

	return (
		<div className="max-w-5xl space-y-6 animate-in fade-in pb-12" data-testid="demo-page">
			<header className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 via-[#0f0f12] to-[#0f0f12] p-6 space-y-2">
				<h1 className="text-2xl font-bold text-white flex items-center gap-2">
					<PlayCircle className="text-indigo-400" size={26} /> Guided demo
				</h1>
				<p className="text-sm text-slate-300 max-w-3xl">
					One page, start to finish: build a cube, build a toy car, then exercise the depot CRUD. Every button calls the
					same REST/MCP path the agent uses; nothing here is pre-baked.
				</p>
				<p className="text-sm text-slate-400">
					FreeCAD must be installed for steps 1 and 2 (see{" "}
					<a
						className="text-indigo-400 hover:underline"
						href="https://github.com/sandraschi/freecad-mcp/blob/master/docs/ONBOARDING.md"
						target="_blank"
						rel="noreferrer"
					>
						onboarding
					</a>
					).
				</p>
			</header>

			{/* Step 1 */}
			<section className="rounded-2xl bg-[#0f0f12] border border-white/5 p-6 space-y-4" data-testid="demo-step-cube">
				<div className="flex items-center gap-2">
					<Box className="text-indigo-400" size={20} />
					<h2 className="text-lg font-bold text-white">1. Make a cube</h2>
				</div>
				<div className="flex flex-wrap items-end gap-3 text-sm">
					{(["width", "height", "depth"] as const).map((axis) => (
						<label key={axis} className="space-y-1">
							<span className="block text-slate-300 capitalize">{axis} (mm)</span>
							<input
								type="number"
								min={1}
								value={cubeSize[axis]}
								data-testid={`demo-cube-${axis}`}
								onChange={(e) => setCubeSize({ ...cubeSize, [axis]: Number(e.target.value) })}
								className="w-28 rounded-lg border border-white/10 bg-[#17171c] px-3 py-2 text-slate-100"
							/>
						</label>
					))}
					<button
						onClick={buildCube}
						disabled={cubeBusy}
						data-testid="demo-cube-build"
						className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-500 disabled:opacity-40"
					>
						{cubeBusy ? <Loader2 size={16} className="animate-spin" /> : <Box size={16} />}
						{cubeBusy ? "Building..." : "Build cube"}
					</button>
					<button
						onClick={() => cube && saveToDepot(cube.file, setCubeSaving)}
						disabled={!cube || cubeSaving}
						data-testid="demo-cube-save"
						className="inline-flex items-center gap-2 rounded-xl bg-white/5 px-4 py-2 font-semibold text-indigo-300 hover:bg-white/10 disabled:opacity-40"
					>
						{cubeSaving ? <Loader2 size={16} className="animate-spin" /> : <Database size={16} />}
						Save cube to depot
					</button>
				</div>
				{cubeError && (
					<p className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-950/30 p-3 text-sm text-red-300">
						<AlertCircle size={16} /> {cubeError}
					</p>
				)}
				{cube ? (
					<div className="space-y-3" data-testid="demo-cube-result">
						<p className="flex flex-wrap items-center gap-3 text-sm text-slate-300">
							<CheckCircle2 size={16} className="text-emerald-400" />
							<span className="font-mono">{cube.file}</span>
							{cube.metrics.volume_mm3 ? <span>{cube.metrics.volume_mm3.toLocaleString()} mm³</span> : null}
							{cube.metrics.size_kb ? <span>{cube.metrics.size_kb} kB</span> : null}
							<a
								className="inline-flex items-center gap-1 text-indigo-400 hover:underline"
								href={`${API_BASE}/api/v1/download/${encodeURIComponent(cube.file)}`}
							>
								<Download size={14} /> download
							</a>
						</p>
						<StlViewer url={`${API_BASE}/api/v1/download/${encodeURIComponent(cube.file)}`} height={320} />
					</div>
				) : (
					<p className="text-sm text-slate-400">No cube yet - press Build cube.</p>
				)}
			</section>

			{/* Step 2 */}
			<section className="rounded-2xl bg-[#0f0f12] border border-white/5 p-6 space-y-4" data-testid="demo-step-car">
				<div className="flex items-center gap-2">
					<Car className="text-amber-400" size={20} />
					<h2 className="text-lg font-bold text-white">2. Make a toy car</h2>
				</div>
				<div className="flex flex-wrap items-end gap-3 text-sm">
					<label className="space-y-1">
						<span className="block text-slate-300">Source</span>
						<select
							value={carSource}
							data-testid="demo-car-source"
							onChange={(e) => setCarSource(e.target.value as "parametric" | "auto")}
							className="rounded-lg border border-white/10 bg-[#17171c] px-3 py-2 text-slate-100"
						>
							<option value="parametric">FreeCAD parametric</option>
							<option value="auto">Auto (Blender → marketplace → FreeCAD)</option>
						</select>
					</label>
					<button
						onClick={buildCar}
						disabled={carBusy}
						data-testid="demo-car-build"
						className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-500 disabled:opacity-40"
					>
						{carBusy ? <Loader2 size={16} className="animate-spin" /> : <Car size={16} />}
						{carBusy ? "Building..." : "Build car"}
					</button>
					<button
						onClick={() => car && saveToDepot(car.file, setCarSaving)}
						disabled={!car || carSaving}
						data-testid="demo-car-save"
						className="inline-flex items-center gap-2 rounded-xl bg-white/5 px-4 py-2 font-semibold text-amber-300 hover:bg-white/10 disabled:opacity-40"
					>
						{carSaving ? <Loader2 size={16} className="animate-spin" /> : <Database size={16} />}
						Save car to depot
					</button>
				</div>
				{carError && (
					<p className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-950/30 p-3 text-sm text-red-300">
						<AlertCircle size={16} /> {carError}
					</p>
				)}
				{car ? (
					<div className="space-y-3" data-testid="demo-car-result">
						<p className="flex flex-wrap items-center gap-3 text-sm text-slate-300">
							<CheckCircle2 size={16} className="text-emerald-400" />
							<span className="font-mono">{car.file}</span>
							{car.metrics.car_source ? <span>via {car.metrics.car_source}</span> : null}
							{car.metrics.wheels ? <span>{car.metrics.wheels} wheels</span> : null}
							{car.metrics.volume_mm3 ? <span>{car.metrics.volume_mm3.toLocaleString()} mm³</span> : null}
							<a
								className="inline-flex items-center gap-1 text-indigo-400 hover:underline"
								href={`${API_BASE}/api/v1/download/${encodeURIComponent(car.file)}`}
							>
								<Download size={14} /> download
							</a>
						</p>
						<StlViewer url={`${API_BASE}/api/v1/download/${encodeURIComponent(car.file)}`} height={320} />
					</div>
				) : (
					<p className="text-sm text-slate-400">No car yet - press Build car (parametric is fastest).</p>
				)}
			</section>

			{/* Step 3 */}
			<section className="rounded-2xl bg-[#0f0f12] border border-white/5 p-6 space-y-4" data-testid="demo-step-depot">
				<div className="flex flex-wrap items-center justify-between gap-2">
					<div className="flex items-center gap-2">
						<Database className="text-emerald-400" size={20} />
						<h2 className="text-lg font-bold text-white">3. Depot CRUD</h2>
					</div>
					<button
						onClick={loadDepot}
						disabled={depotBusy}
						data-testid="demo-depot-refresh"
						className="inline-flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2 text-sm font-semibold text-slate-200 hover:bg-white/10 disabled:opacity-40"
					>
						<RefreshCw size={14} className={depotBusy ? "animate-spin" : ""} /> Refresh
					</button>
				</div>
				{depotError && (
					<p className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-950/30 p-3 text-sm text-red-300">
						<AlertCircle size={16} /> {depotError}
					</p>
				)}
				{files.length === 0 ? (
					<p className="text-sm text-slate-400">Depot is empty. Save the cube or the car above, then refresh.</p>
				) : (
					<div className="overflow-x-auto" data-testid="demo-depot-list">
						<table className="w-full text-left text-sm">
							<thead className="text-slate-300">
								<tr>
									<th className="py-2 pr-4">File</th>
									<th className="py-2 pr-4">Size</th>
									<th className="py-2 pr-4">Description</th>
								</tr>
							</thead>
							<tbody>
								{files.map((file) => (
									<tr
										key={file.name}
										onClick={() => {
											setSelected(file.name);
											setRenameValue(file.name);
										}}
										className={`cursor-pointer border-t border-white/5 ${selected === file.name ? "bg-indigo-500/10" : "hover:bg-white/5"}`}
									>
										<td className="py-2 pr-4 font-mono text-slate-200">{file.name}</td>
										<td className="py-2 pr-4 text-slate-300">{file.size_kb} kB</td>
										<td className="py-2 pr-4 text-slate-400">{file.meta?.description || "-"}</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				)}
				<div className="flex flex-wrap items-end gap-3 text-sm">
					<label className="space-y-1">
						<span className="block text-slate-300">Rename selected</span>
						<input
							value={renameValue}
							onChange={(e) => setRenameValue(e.target.value)}
							placeholder="select a file above"
							data-testid="demo-rename-input"
							className="w-72 rounded-lg border border-white/10 bg-[#17171c] px-3 py-2 font-mono text-slate-100"
						/>
					</label>
					<button
						onClick={renameSelected}
						disabled={!selected || !renameValue.trim() || depotBusy}
						data-testid="demo-rename-button"
						className="inline-flex items-center gap-2 rounded-xl bg-white/5 px-4 py-2 font-semibold text-indigo-300 hover:bg-white/10 disabled:opacity-40"
					>
						<Pencil size={16} /> Rename
					</button>
					<button
						onClick={deleteSelected}
						disabled={!selected || depotBusy}
						data-testid="demo-delete-button"
						className="inline-flex items-center gap-2 rounded-xl bg-red-600/80 px-4 py-2 font-semibold text-white hover:bg-red-500 disabled:opacity-40"
					>
						<Trash2 size={16} /> Delete
					</button>
					<a href="/depot" className="inline-flex items-center gap-1 px-2 py-2 text-indigo-400 hover:underline">
						Full depot page <ArrowRight size={14} />
					</a>
				</div>
			</section>

			{/* Activity log */}
			<section className="rounded-2xl bg-[#0f0f12] border border-white/5 p-6 space-y-2" data-testid="demo-log">
				<h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">Activity</h2>
				{log.length === 0 ? (
					<p className="text-sm text-slate-400">Actions appear here.</p>
				) : (
					<ul className="space-y-1 font-mono text-sm text-slate-300">
						{log.map((entry) => (
							<li key={entry}>{entry}</li>
						))}
					</ul>
				)}
			</section>
		</div>
	);
}
