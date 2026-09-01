import { Box, CheckCircle2, Cpu, Database, FileText, Gauge, Loader2, Waves, XCircle, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

export default function Dashboard() {
	const [status, setStatus] = useState<any>(null);
	const [health, setHealth] = useState<any>(null);
	const [files, setFiles] = useState<{ uploads: number; outputs: number; depot: number }>({
		uploads: 0,
		outputs: 0,
		depot: 0,
	});

	useEffect(() => {
		fetch(API_BASE + "/api/v1/status")
			.then((r) => r.json())
			.then(setStatus)
			.catch(() => setStatus({ freecad_ok: false }));
		fetch(API_BASE + "/api/v1/health")
			.then((r) => r.json())
			.then(setHealth)
			.catch(() => {});
		fetch(API_BASE + "/api/v1/files")
			.then((r) => r.json())
			.then((j) => setFiles((p) => ({ ...p, uploads: (j.uploads || []).length, outputs: (j.outputs || []).length })))
			.catch(() => {});
		fetch(API_BASE + "/api/v1/depot")
			.then((r) => r.json())
			.then((j) => setFiles((p) => ({ ...p, depot: (j.files || []).length })))
			.catch(() => {});
	}, []);

	return (
		<div className="space-y-6 animate-in fade-in">
			<h1 className="text-2xl font-bold text-white">Dashboard</h1>
			<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
				{/* FreeCAD */}
				<div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-5 space-y-3">
					<div className="flex items-center gap-2 text-indigo-400">
						<Cpu size={18} /> FreeCAD Engine
					</div>
					{status?.freecad_ok === undefined ? (
						<Loader2 className="animate-spin" />
					) : (
						<div className="flex items-center gap-2 text-sm">
							{status.freecad_ok ? (
								<CheckCircle2 size={16} className="text-emerald-400" />
							) : (
								<XCircle size={16} className="text-red-400" />
							)}
							<span className="text-slate-300">
								{status.freecad_ok ? status.freecad_version?.split(" ").slice(0, 2).join(" ") : "Not found"}
							</span>
						</div>
					)}
					<p className="text-xs text-slate-600">
						{status?.bridge_mode === "tcp"
							? "TCP Bridge (AP214 capable)"
							: status?.bridge_mode === "subprocess"
								? "Subprocess (limited)"
								: "Offline"}
					</p>
				</div>

				{/* OpenFOAM & Docker */}
				<div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-5 space-y-3">
					<div className="flex items-center gap-2 text-emerald-400">
						<Waves size={18} /> OpenFOAM
					</div>
					{health ? (
						<>
							<div className="flex items-center gap-2 text-sm">
								{health.docker_available ? (
									<CheckCircle2 size={16} className="text-emerald-400" />
								) : (
									<XCircle size={16} className="text-red-400" />
								)}
								<span className="text-slate-300">{health.docker_available ? "Docker" : "Docker not found"}</span>
							</div>
							{health.openfoam_image && <p className="text-xs text-emerald-400/70">OpenFOAM image ready</p>}
							{!health.openfoam_image && health.docker_available && (
								<p className="text-xs text-amber-400/70">Run: docker pull openfoam/openfoam10-paraview56</p>
							)}
						</>
					) : (
						<Loader2 className="animate-spin" />
					)}
				</div>

				{/* FluidX3D */}
				<div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-5 space-y-3">
					<div className="flex items-center gap-2 text-amber-400">
						<Zap size={18} /> FluidX3D (GPU)
					</div>
					{health ? (
						<>
							<div className="flex items-center gap-2 text-sm">
								{health.fluidx3d_path ? (
									<CheckCircle2 size={16} className="text-emerald-400" />
								) : (
									<XCircle size={16} className="text-red-400" />
								)}
								<span className="text-slate-300">{health.fluidx3d_path ? "FluidX3D found" : "Not cloned"}</span>
							</div>
							{health.compiler && <p className="text-xs text-slate-500 font-mono">Compiler: {health.compiler}</p>}
							{!health.fluidx3d_path && (
								<p className="text-xs text-amber-400/70">git clone https://github.com/ProjectPhysX/FluidX3D.git</p>
							)}
						</>
					) : (
						<Loader2 className="animate-spin" />
					)}
				</div>

				{/* Depot */}
				<div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-5 space-y-3">
					<div className="flex items-center gap-2 text-indigo-400">
						<Database size={18} /> CAD Depot
					</div>
					<p className="text-2xl font-bold text-white">
						{files.depot} <span className="text-sm font-normal text-slate-500">files</span>
					</p>
					<a href="/depot" className="text-xs text-indigo-400 hover:underline">
						Browse depot →
					</a>
				</div>
			</div>

			{/* Quick Actions */}
			<div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-5">
				<div className="flex items-center gap-2 text-amber-400 mb-3">
					<Gauge size={18} /> Quick Actions
				</div>
				<div className="grid grid-cols-2 md:grid-cols-4 gap-2">
					<a
						href="/depot"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-indigo-400 text-center"
					>
						CAD Depot
					</a>
					<a
						href="/convert"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-indigo-400 text-center"
					>
						Convert STEP → STL
					</a>
					<a
						href="/cfd-demos"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-cyan-400 text-center"
					>
						CFD Demos
					</a>
					<a
						href="/toy-car"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-amber-400 text-center"
					>
						Toy Car
					</a>
					<a
						href="/cfd"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-emerald-400 text-center"
					>
						OpenFOAM CFD
					</a>
					<a
						href="/fluidx3d"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-amber-400 text-center"
					>
						FluidX3D GPU
					</a>
					<a
						href="/pipeline"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-purple-400 text-center"
					>
						Pipeline Wizard
					</a>
					<a
						href="/chat"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-sky-400 text-center"
					>
						Ask CAD Expert
					</a>
					<a
						href="/marketplace"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-orange-400 text-center"
					>
						Marketplace
					</a>
					<a
						href="/apps"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-slate-300 text-center"
					>
						App Launcher
					</a>
					<a
						href="/help"
						className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-slate-500 text-center"
					>
						Help
					</a>
				</div>
			</div>
		</div>
	);
}
