import { Car, Loader2, Sparkles, Wrench } from "lucide-react";
import { useCallback, useState } from "react";
import StlViewer from "../components/StlViewer";
import { apiPath } from "../lib/api";

const API = apiPath("/api/v1");

type CarSource = "auto" | "blender" | "marketplace" | "parametric";

const SOURCES: { id: CarSource; label: string; hint: string }[] = [
	{ id: "auto", label: "Auto", hint: "Blender sculpt, then marketplace, then FreeCAD parametric" },
	{ id: "blender", label: "Blender", hint: "Headless sports_car script via blender-mcp" },
	{ id: "marketplace", label: "Marketplace", hint: "Download community STL from Printables" },
	{ id: "parametric", label: "FreeCAD", hint: "Elaborate Part solids: cabin, arches, torus wheels" },
];

export default function ToyCarDemoPage() {
	const [source, setSource] = useState<CarSource>("auto");
	const [bodyLength, setBodyLength] = useState(120);
	const [bodyWidth, setBodyWidth] = useState(60);
	const [wheelRadius, setWheelRadius] = useState(12);
	const [marketQuery, setMarketQuery] = useState("toy car sports car stl");
	const [outputName, setOutputName] = useState("toy_car.stl");
	const [loading, setLoading] = useState(false);
	const [message, setMessage] = useState<string | null>(null);
	const [resolvedSource, setResolvedSource] = useState<string | null>(null);
	const [stlUrl, setStlUrl] = useState<string | null>(null);

	const buildCar = useCallback(async () => {
		setLoading(true);
		setMessage(null);
		setResolvedSource(null);
		try {
			const res = await fetch(`${API}/control/tool`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					tool: "freecad_model",
					arguments: {
						operation: "toy_car",
						car_source: source,
						output_name: outputName,
						body_length_mm: bodyLength,
						body_width_mm: bodyWidth,
						body_height_mm: 35,
						wheel_radius_mm: wheelRadius,
						wheelbase_mm: 70,
						marketplace_query: marketQuery,
					},
				}),
			});
			const data = await res.json();
			if (!data.success) {
				setMessage(data.error ?? data.stderr ?? "Build failed");
				setStlUrl(null);
				return;
			}
			const out = data.output ?? outputName;
			setResolvedSource(data.car_source ?? data.resolved_via ?? source);
			setStlUrl(`/api/v1/download/${out}?t=${Date.now()}`);
			setMessage(
				`Built ${out} via ${data.car_source ?? data.resolved_via ?? source}` +
					(data.size_kb ? ` (${data.size_kb} KB)` : ""),
			);
		} catch (err) {
			setMessage(String(err));
			setStlUrl(null);
		} finally {
			setLoading(false);
		}
	}, [source, bodyLength, bodyWidth, wheelRadius, marketQuery, outputName]);

	return (
		<div className="p-6 max-w-6xl mx-auto space-y-6">
			<div>
				<h1 className="text-2xl font-bold text-white flex items-center gap-2">
					<Car className="text-amber-400" size={26} />
					Toy Car Demo
				</h1>
				<p className="text-sm text-slate-400 mt-1">
					Multi-source sports toy car: Blender sculpt, marketplace STL, or FreeCAD parametric fallback.
				</p>
			</div>

			<div className="grid lg:grid-cols-2 gap-6">
				<div className="rounded-2xl border border-white/10 bg-white/5 p-5 space-y-4">
					<p className="text-xs uppercase tracking-wider text-slate-500">Source</p>
					<div className="grid grid-cols-2 gap-2">
						{SOURCES.map((s) => (
							<button
								key={s.id}
								type="button"
								onClick={() => setSource(s.id)}
								className={`text-left rounded-xl p-3 border transition-all ${
									source === s.id
										? "border-amber-400/60 bg-amber-500/10 ring-1 ring-amber-400/30"
										: "border-white/10 hover:border-white/20"
								}`}
							>
								<p className="font-semibold text-white text-sm">{s.label}</p>
								<p className="text-xs text-slate-400 mt-1">{s.hint}</p>
							</button>
						))}
					</div>

					<div className="grid grid-cols-2 gap-3 text-sm">
						<label className="flex flex-col gap-1 text-slate-400">
							Body length (mm)
							<input
								type="number"
								value={bodyLength}
								onChange={(e) => setBodyLength(Number(e.target.value))}
								className="bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white"
							/>
						</label>
						<label className="flex flex-col gap-1 text-slate-400">
							Body width (mm)
							<input
								type="number"
								value={bodyWidth}
								onChange={(e) => setBodyWidth(Number(e.target.value))}
								className="bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white"
							/>
						</label>
						<label className="flex flex-col gap-1 text-slate-400">
							Wheel radius (mm)
							<input
								type="number"
								value={wheelRadius}
								onChange={(e) => setWheelRadius(Number(e.target.value))}
								className="bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white"
							/>
						</label>
						<label className="flex flex-col gap-1 text-slate-400">
							Output STL
							<input
								type="text"
								value={outputName}
								onChange={(e) => setOutputName(e.target.value)}
								className="bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white"
							/>
						</label>
					</div>

					{(source === "marketplace" || source === "auto") && (
						<label className="flex flex-col gap-1 text-sm text-slate-400">
							Marketplace query
							<input
								type="text"
								value={marketQuery}
								onChange={(e) => setMarketQuery(e.target.value)}
								className="bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white"
							/>
						</label>
					)}

					<button
						type="button"
						onClick={buildCar}
						disabled={loading}
						className="w-full px-4 py-3 rounded-xl bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white font-medium flex items-center justify-center gap-2"
					>
						{loading ? <Loader2 className="animate-spin" size={18} /> : <Wrench size={18} />}
						Build toy car
					</button>

					{message && (
						<p
							className={`text-sm ${message.includes("failed") || message.includes("Error") ? "text-red-400" : "text-emerald-400"}`}
						>
							{message}
						</p>
					)}
					{resolvedSource && (
						<p className="text-xs text-slate-500 flex items-center gap-1">
							<Sparkles size={12} className="text-amber-400" />
							Resolved via: {resolvedSource}
						</p>
					)}
				</div>

				<div className="rounded-2xl border border-white/10 bg-white/5 p-4">
					<p className="text-xs uppercase tracking-wider text-slate-500 mb-3">Preview</p>
					{stlUrl ? (
						<StlViewer url={stlUrl} height={420} />
					) : (
						<div className="h-[420px] rounded-xl border border-dashed border-white/10 flex items-center justify-center text-slate-500 text-sm">
							Build a car to preview STL
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
