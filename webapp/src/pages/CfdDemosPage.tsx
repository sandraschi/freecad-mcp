import { Loader2, Play, Sparkles, Waves, Zap } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { CFD_DEMOS } from "../data/cfdDemos";
import { useCfdDemoAnimation } from "../hooks/useCfdDemoAnimation";
import { apiPath } from "../lib/api";

const API = apiPath("/api/v1");

export default function CfdDemosPage() {
	const [activeId, setActiveId] = useState(CFD_DEMOS[0].id);
	const [wingAngleDeg, setWingAngleDeg] = useState(6);
	const [riverSpeed, setRiverSpeed] = useState(0.65);
	const [pyroIntensity, setPyroIntensity] = useState(1);
	const [poolDropPending, setPoolDropPending] = useState(false);
	const [gpuLoading, setGpuLoading] = useState(false);
	const [gpuMessage, setGpuMessage] = useState<string | null>(null);

	const canvasRef = useRef<HTMLCanvasElement>(null);
	const active = CFD_DEMOS.find((d) => d.id === activeId) ?? CFD_DEMOS[0];

	useCfdDemoAnimation(canvasRef, activeId, {
		wingAngleDeg,
		riverSpeed,
		pyroIntensity,
		poolDropPending,
		onPoolDropHandled: () => setPoolDropPending(false),
	});

	const launchGpuCase = useCallback(async () => {
		setGpuLoading(true);
		setGpuMessage(null);
		try {
			const preset = { ...active.gpuPreset };
			const setupRes = await fetch(`${API}/control/tool`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ tool: "cfd_fluidx3d_setup", arguments: preset }),
			});
			const setup = await setupRes.json();
			if (!setup.success) {
				setGpuMessage(setup.error ?? "Setup failed");
				return;
			}
			setGpuMessage(`GPU case "${preset.case_name}" staged. Open FluidX3D tab to compile and run.`);
		} catch (err) {
			setGpuMessage(String(err));
		} finally {
			setGpuLoading(false);
		}
	}, [active]);

	return (
		<div className="p-6 max-w-6xl mx-auto space-y-6">
			<div>
				<h1 className="text-2xl font-bold text-white flex items-center gap-2">
					<Sparkles className="text-cyan-400" size={26} />
					CFD Demo Gallery
				</h1>
				<p className="text-sm text-slate-400 mt-1">Interactive previews plus one-click FluidX3D GPU case presets.</p>
			</div>

			<div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
				{CFD_DEMOS.map((demo) => (
					<button
						key={demo.id}
						type="button"
						onClick={() => setActiveId(demo.id)}
						className={`text-left rounded-2xl p-4 border transition-all bg-gradient-to-br ${demo.gradient} ${
							activeId === demo.id
								? "border-white/40 ring-2 ring-white/30 scale-[1.02]"
								: "border-white/10 opacity-80 hover:opacity-100"
						}`}
					>
						<p className="text-xs uppercase tracking-wider text-white/80">{demo.subtitle}</p>
						<p className="text-lg font-bold text-white mt-1">{demo.title}</p>
					</button>
				))}
			</div>

			<div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
				<div className={`px-5 py-4 border-b border-white/10 bg-gradient-to-r ${active.gradient}`}>
					<h2 className="text-xl font-bold text-white">{active.title}</h2>
					<p className="text-sm text-white/90 mt-1">{active.description}</p>
				</div>

				<div className="p-4">
					<canvas ref={canvasRef} className="w-full rounded-xl border border-white/10 bg-black/40" />
				</div>

				<div className="px-5 pb-5 flex flex-wrap gap-4 items-end">
					{activeId === "pool-splash" && (
						<button
							type="button"
							onClick={() => setPoolDropPending(true)}
							className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium flex items-center gap-2"
						>
							<Waves size={16} />
							Throw ball
						</button>
					)}

					{activeId === "wing-flow" && (
						<label className="flex flex-col gap-1 text-xs text-slate-400 min-w-[200px]">
							Angle of attack ({wingAngleDeg.toFixed(0)} deg)
							<input
								type="range"
								min={-4}
								max={22}
								value={wingAngleDeg}
								onChange={(e) => setWingAngleDeg(Number(e.target.value))}
								className="accent-violet-500"
							/>
						</label>
					)}

					{activeId === "river-bends" && (
						<label className="flex flex-col gap-1 text-xs text-slate-400 min-w-[200px]">
							Flow speed
							<input
								type="range"
								min={0.2}
								max={1}
								step={0.05}
								value={riverSpeed}
								onChange={(e) => setRiverSpeed(Number(e.target.value))}
								className="accent-emerald-500"
							/>
						</label>
					)}

					{activeId === "pyroclastic" && (
						<label className="flex flex-col gap-1 text-xs text-slate-400 min-w-[200px]">
							Surge intensity
							<input
								type="range"
								min={0.4}
								max={1.4}
								step={0.05}
								value={pyroIntensity}
								onChange={(e) => setPyroIntensity(Number(e.target.value))}
								className="accent-orange-500"
							/>
						</label>
					)}

					<button
						type="button"
						disabled={gpuLoading}
						onClick={() => void launchGpuCase()}
						className="ml-auto px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium flex items-center gap-2"
					>
						{gpuLoading ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
						Stage GPU case
					</button>
				</div>

				{gpuMessage && (
					<div className="mx-5 mb-5 px-4 py-3 rounded-xl bg-indigo-950/60 border border-indigo-500/30 text-sm text-indigo-200 flex items-start gap-2">
						<Play size={16} className="shrink-0 mt-0.5" />
						<span>{gpuMessage}</span>
					</div>
				)}
			</div>
		</div>
	);
}
