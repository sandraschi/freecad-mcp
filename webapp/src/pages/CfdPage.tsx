import {
	AlertTriangle,
	BarChart3,
	Beaker,
	Box,
	BrainCircuit,
	CheckCircle2,
	Cpu,
	Download,
	FileText,
	FlaskConical,
	Gauge,
	GitBranch,
	Layers,
	Loader2,
	Network,
	Play,
	Rabbit,
	RefreshCw,
	Search,
	Settings2,
	Sparkles,
	Terminal,
	Upload,
	Waves,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
	CartesianGrid,
	Legend,
	Line,
	LineChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";

const API = "/api/v1";

interface CfdStatus {
	success: boolean;
	docker_available: boolean;
	docker_exe: string;
	openfoam_image: boolean;
	bridge_mode: string;
	cfd_case_dir: string;
}

interface ToolResult {
	success: boolean;
	error?: string;
	case_name?: string;
	case_dir?: string;
	data?: Record<string, unknown>;
}

interface CaseInfo {
	name: string;
	has_config: boolean;
	has_results: boolean;
}

const tabs = [
	{ id: "status", label: "Status", icon: Gauge },
	{ id: "create", label: "Domain", icon: Box, legacy: true },
	{ id: "physics", label: "Physics", icon: FlaskConical, legacy: true },
	{ id: "boundary", label: "Boundaries", icon: Layers, legacy: true },
	{ id: "build", label: "Build", icon: Settings2, legacy: true },
	{ id: "run", label: "Run", icon: Play, legacy: true },
	{ id: "results", label: "Results", icon: BarChart3, legacy: true },
	{ id: "parametric", label: "Parametric", icon: GitBranch, legacy: true },
	{ id: "nl2foam", label: "NL2FOAM", icon: BrainCircuit, legacy: true },
	{ id: "pinns", label: "PINNs", icon: Network, legacy: true },
	{ id: "fluidx3d", label: "GPU CFD", icon: Zap },
] as const;

type TabId = (typeof tabs)[number]["id"];

export default function CfdPage() {
	const [activeTab, setActiveTab] = useState<TabId>("status");
	const [status, setStatus] = useState<CfdStatus | null>(null);
	const [cases, setCases] = useState<CaseInfo[]>([]);
	const [loading, setLoading] = useState(false);
	const [result, setResult] = useState<ToolResult | null>(null);
	const [error, setError] = useState<string | null>(null);

	// Form state
	const [caseName, setCaseName] = useState("channel_flow");
	const [domainType, setDomainType] = useState("channel");
	const [lengthM, setLengthM] = useState(1.0);
	const [widthM, setWidthM] = useState(0.1);
	const [heightM, setHeightM] = useState(0.05);
	const [inletRadius, setInletRadius] = useState(0.02);
	const [outletRadius, setOutletRadius] = useState(0.01);
	const [meshCells, setMeshCells] = useState(20000);
	const [stepFile, setStepFile] = useState("");

	const [solver, setSolver] = useState("simpleFoam");
	const [flowType, setFlowType] = useState("laminar");
	const [fluidNu, setFluidNu] = useState(1e-6);
	const [fluidDensity, setFluidDensity] = useState(1000);
	const [inletVelocity, setInletVelocity] = useState(1.0);
	const [endTime, setEndTime] = useState(1000);
	const [deltaT, setDeltaT] = useState(1.0);
	const [writeInterval, setWriteInterval] = useState(100);

	const [bcPatch, setBcPatch] = useState("inlet");
	const [bcField, setBcField] = useState("U");
	const [bcType, setBcType] = useState("fixedValue");
	const [bcValue, setBcValue] = useState("uniform (1 0 0)");

	const [nlDescription, setNlDescription] = useState("");
	const [nlModel, setNlModel] = useState("gemma3:1b");

	const [paramParameter, setParamParameter] = useState("inlet_velocity");
	const [paramValues, setParamValues] = useState("[0.5, 1.0, 2.0, 5.0]");
	const [paramRun, setParamRun] = useState(false);

	const [pinnBoundary, setPinnBoundary] = useState(5000);
	const [pinnInterior, setPinnInterior] = useState(10000);
	const [pinnFormat, setPinnFormat] = useState("csv");

	const [solverSteps, setSolverSteps] = useState(
		"blockMesh,checkMesh,simpleFoam",
	);
	const [parallelRun, setParallelRun] = useState(false);
	const [nCores, setNCores] = useState(4);

	// FluidX3D state
	const [fx3dStatus, setFx3dStatus] = useState<Record<string, unknown> | null>(
		null,
	);
	const [fx3dPreset, setFx3dPreset] = useState("channel");
	const [fx3dStep, setFx3dStep] = useState<
		"idle" | "setup" | "compiling" | "running" | "done"
	>("idle");
	const [fx3dForceData, setFx3dForceData] = useState<Record<string, unknown>[]>(
		[],
	);
	const [fx3dMlups, setFx3dMlups] = useState(0);
	const [fx3dCellCount, setFx3dCellCount] = useState(0);
	const [fx3dRuntime, setFx3dRuntime] = useState(0);
	const [fx3dLog, setFx3dLog] = useState("");

	useEffect(() => {
		fetchStatus();
		fetchCases();
	}, []);

	const fetchStatus = async () => {
		try {
			const r = await fetch(`${API}/control/tool`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ tool: "cfd_status", arguments: {} }),
			});
			const d = await r.json();
			setStatus(d);
		} catch {
			// server not ready
		}
	};

	const fetchCases = async () => {
		try {
			const r = await fetch(`${API}/files`);
			const d = await r.json();
			// Cases are in cfd_cases dir — we approximate from file listing
			setCases([]);
		} catch {
			// ignore
		}
	};

	const callTool = useCallback(
		async (tool: string, args: Record<string, unknown>) => {
			setLoading(true);
			setError(null);
			setResult(null);
			try {
				const r = await fetch(`${API}/control/tool`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ tool, arguments: args }),
				});
				const d = await r.json();
				if (!d.success) {
					setError(d.error || "Tool failed");
				}
				setResult(d);
				return d;
			} catch (e) {
				setError(String(e));
				return null;
			} finally {
				setLoading(false);
			}
		},
		[],
	);

	const field = (label: string, children: React.ReactNode) => (
		<div className="flex flex-col gap-1">
			<label className="text-xs font-medium text-slate-400">{label}</label>
			{children}
		</div>
	);

	const input = (
		value: string | number,
		onChange: (v: string) => void,
		props?: Record<string, unknown>,
	) => (
		<input
			type={typeof value === "number" ? "number" : "text"}
			value={value}
			onChange={(e) => onChange(e.target.value)}
			className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500/50 w-full font-mono"
			{...props}
		/>
	);

	const select = (
		value: string,
		onChange: (v: string) => void,
		options: string[],
	) => (
		<select
			value={value}
			onChange={(e) => onChange(e.target.value)}
			className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500/50 w-full"
		>
			{options.map((o) => (
				<option key={o} value={o}>
					{o}
				</option>
			))}
		</select>
	);

	const btn = (
		label: string,
		onClick: () => void,
		variant: "primary" | "secondary" | "danger" = "primary",
	) => (
		<button
			onClick={onClick}
			disabled={loading}
			className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-50 ${
				variant === "primary"
					? "bg-indigo-600 hover:bg-indigo-500 text-white"
					: variant === "danger"
						? "bg-red-600/20 hover:bg-red-600/40 text-red-400 border border-red-600/30"
						: "bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10"
			}`}
		>
			{loading ? <Loader2 size={14} className="animate-spin" /> : null}
			{label}
		</button>
	);

	return (
		<div className="flex flex-col h-full">
			{/* Tab bar */}
			<div className="flex gap-1 px-4 pt-4 pb-0 border-b border-white/5 overflow-x-auto">
				{tabs.map((tab) => (
					<button
						key={tab.id}
						onClick={() => setActiveTab(tab.id)}
						className={`flex items-center gap-1.5 px-3 py-2 rounded-t-lg text-xs font-medium transition-all whitespace-nowrap ${
							activeTab === tab.id
								? "bg-indigo-600/20 text-indigo-400 border-b-2 border-indigo-500"
								: "text-slate-500 hover:text-slate-300"
						}`}
					>
						<tab.icon size={14} />
						{tab.label}
						{"legacy" in tab && (
							<span className="ml-1 text-[10px] px-1 py-px rounded bg-amber-500/20 text-amber-400 leading-none">
								LEGACY
							</span>
						)}
					</button>
				))}
			</div>

			{/* Content */}
			<div className="flex-1 overflow-y-auto p-4 space-y-4">
				{/* Legacy banner */}
				{tabs.find((t) => t.id === activeTab && "legacy" in t) && (
					<div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
						<AlertTriangle
							size={18}
							className="text-amber-400 shrink-0 mt-0.5"
						/>
						<p className="text-sm text-amber-200">
							OpenFOAM is CPU-only and ~50x slower than FluidX3D GPU CFD. Switch
							to the{" "}
							<button
								onClick={() => setActiveTab("fluidx3d")}
								className="text-indigo-400 underline hover:text-indigo-300"
							>
								GPU CFD tab
							</button>{" "}
							for GPU-accelerated simulations.
						</p>
					</div>
				)}

				{/* Status Tab */}
				{activeTab === "status" && (
					<div className="space-y-4">
						<h2 className="text-lg font-bold text-slate-200">
							CFD Pipeline Status
						</h2>
						<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
							{status ? (
								<>
									<StatusCard
										icon={Cpu}
										label="Bridge Mode"
										value={status.bridge_mode}
										ok={status.bridge_mode !== "none"}
									/>
									<StatusCard
										icon={Box}
										label="Docker"
										value={
											status.docker_available ? status.docker_exe : "Not found"
										}
										ok={status.docker_available}
									/>
									<StatusCard
										icon={Waves}
										label="OpenFOAM Image"
										value={status.openfoam_image ? "Ready" : "Missing"}
										ok={status.openfoam_image}
									/>
									<StatusCard
										icon={CheckCircle2}
										label="Pipeline Ready"
										value={
											status.bridge_mode !== "none" && status.openfoam_image
												? "Yes"
												: "No"
										}
										ok={status.bridge_mode !== "none" && status.openfoam_image}
									/>
								</>
							) : (
								<div className="col-span-4 text-slate-500 text-sm">
									Loading status...
								</div>
							)}
						</div>
						{status?.openfoam_image === false && (
							<div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
								<AlertTriangle
									size={18}
									className="text-amber-400 shrink-0 mt-0.5"
								/>
								<div className="text-sm text-amber-200">
									<p className="font-medium mb-1">
										OpenFOAM Docker image not found
									</p>
									<code className="text-xs bg-black/30 px-2 py-0.5 rounded">
										docker pull openfoam/openfoam10-paraview56
									</code>
								</div>
							</div>
						)}
						{status?.openfoam_image === true && (
							<div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
								<AlertTriangle
									size={18}
									className="text-amber-400 shrink-0 mt-0.5"
								/>
								<div className="text-sm text-amber-200">
									<p className="font-medium mb-1">
										OpenFOAM image available but CPU-only
									</p>
									<p className="text-xs">
										For GPU-accelerated CFD (50x faster), use the{" "}
										<button
											onClick={() => setActiveTab("fluidx3d")}
											className="text-indigo-400 underline hover:text-indigo-300"
										>
											GPU CFD tab
										</button>
										.
									</p>
								</div>
							</div>
						)}
						<button
							onClick={fetchStatus}
							className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm text-slate-400"
						>
							<RefreshCw size={14} /> Refresh
						</button>
					</div>
				)}

				{/* Domain Tab */}
				{activeTab === "create" && (
					<div className="space-y-4 max-w-2xl">
						<h2 className="text-lg font-bold text-slate-200">
							Create Fluid Domain
						</h2>
						<p className="text-xs text-slate-500">
							Generate parametric geometry and blockMeshDict for OpenFOAM
						</p>
						<div className="grid grid-cols-2 gap-3">
							{field("Case Name", input(caseName, setCaseName))}
							{field(
								"Domain Type",
								select(domainType, setDomainType, [
									"channel",
									"pipe",
									"box",
									"nozzle",
									"custom",
								]),
							)}
							{field(
								"Length (m)",
								input(lengthM, setLengthM, { min: 0.001, step: 0.1 }),
							)}
							{field(
								"Width (m)",
								input(widthM, setWidthM, { min: 0.001, step: 0.01 }),
							)}
							{field(
								"Height (m)",
								input(heightM, setHeightM, { min: 0.001, step: 0.01 }),
							)}
							{field(
								"Mesh Cells",
								input(meshCells, setMeshCells, { step: 1000 }),
							)}
							{domainType === "pipe" &&
								field(
									"Inlet Radius (m)",
									input(inletRadius, setInletRadius, { step: 0.001 }),
								)}
							{domainType === "nozzle" && (
								<>
									{field(
										"Inlet Radius (m)",
										input(inletRadius, setInletRadius, { step: 0.001 }),
									)}
									{field(
										"Outlet Radius (m)",
										input(outletRadius, setOutletRadius, { step: 0.001 }),
									)}
								</>
							)}
							{domainType === "custom" &&
								field("STEP File", input(stepFile, setStepFile))}
						</div>
						{btn("Create Domain", () =>
							callTool("cfd_create_domain", {
								case_name: caseName,
								domain_type: domainType,
								length_m: Number(lengthM),
								width_m: Number(widthM),
								height_m: Number(heightM),
								inlet_radius_m: Number(inletRadius),
								outlet_radius_m: Number(outletRadius),
								mesh_cells: Number(meshCells),
								step_file: stepFile,
							}),
						)}
					</div>
				)}

				{/* Physics Tab */}
				{activeTab === "physics" && (
					<div className="space-y-4 max-w-2xl">
						<h2 className="text-lg font-bold text-slate-200">
							Configure Physics
						</h2>
						<p className="text-xs text-slate-500">
							Set solver, flow model, and fluid properties
						</p>
						<div className="grid grid-cols-2 gap-3">
							{field("Case Name", input(caseName, setCaseName))}
							{field(
								"Solver",
								select(solver, setSolver, [
									"simpleFoam",
									"pisoFoam",
									"pimpleFoam",
								]),
							)}
							{field(
								"Flow Model",
								select(flowType, setFlowType, [
									"laminar",
									"kEpsilon",
									"kOmegaSST",
								]),
							)}
							{field(
								"Kinematic Viscosity (m²/s)",
								input(fluidNu, setFluidNu, { step: "1e-7" }),
							)}
							{field(
								"Density (kg/m³)",
								input(fluidDensity, setFluidDensity, { step: 1 }),
							)}
							{field(
								"Inlet Velocity (m/s)",
								input(inletVelocity, setInletVelocity, { step: 0.1 }),
							)}
							{field(
								"End Time / Iterations",
								input(endTime, setEndTime, { step: 100 }),
							)}
							{field("Time Step (s)", input(deltaT, setDeltaT, { step: 0.1 }))}
							{field(
								"Write Interval",
								input(writeInterval, setWriteInterval, { step: 50 }),
							)}
						</div>
						{btn("Configure Physics", () =>
							callTool("cfd_configure_physics", {
								case_name: caseName,
								solver,
								flow_type: flowType,
								fluid_nu: Number(fluidNu),
								fluid_density: Number(fluidDensity),
								inlet_velocity: Number(inletVelocity),
								end_time: Number(endTime),
								delta_t: Number(deltaT),
								write_interval: Number(writeInterval),
							}),
						)}
					</div>
				)}

				{/* Boundary Tab */}
				{activeTab === "boundary" && (
					<div className="space-y-4 max-w-2xl">
						<h2 className="text-lg font-bold text-slate-200">
							Boundary Conditions
						</h2>
						<p className="text-xs text-slate-500">
							Configure per-patch field values
						</p>
						<div className="grid grid-cols-2 gap-3">
							{field("Case Name", input(caseName, setCaseName))}
							{field(
								"Patch",
								select(bcPatch, setBcPatch, ["inlet", "outlet", "walls"]),
							)}
							{field(
								"Field",
								select(bcField, setBcField, ["U", "p", "k", "omega", "nut"]),
							)}
							{field(
								"BC Type",
								select(bcType, setBcType, [
									"fixedValue",
									"zeroGradient",
									"inletOutlet",
									"outletInlet",
									"slip",
									"noSlip",
									"symmetry",
									"empty",
								]),
							)}
							{field("Value", input(bcValue, setBcValue))}
						</div>
						<p className="text-xs text-slate-500">
							Examples: uniform (1 0 0) for velocity, uniform 0 for pressure
						</p>
						{btn("Set Boundary", () =>
							callTool("cfd_set_boundary", {
								case_name: caseName,
								patch_name: bcPatch,
								field_name: bcField,
								bc_type: bcType,
								value: bcValue,
							}),
						)}
					</div>
				)}

				{/* Build Tab */}
				{activeTab === "build" && (
					<div className="space-y-4 max-w-2xl">
						<h2 className="text-lg font-bold text-slate-200">
							Build & Validate Case
						</h2>
						<p className="text-xs text-slate-500">
							Check that all required files are present
						</p>
						{field("Case Name", input(caseName, setCaseName))}
						{btn("Validate Case", () =>
							callTool("cfd_build_case", { case_name: caseName }),
						)}
						{result?.data && (
							<div className="p-4 bg-white/5 rounded-xl border border-white/10 space-y-2">
								<p className="text-sm font-medium text-slate-300">
									Ready:{" "}
									<span
										className={
											result.data.ready ? "text-green-400" : "text-red-400"
										}
									>
										{String(result.data.ready)}
									</span>
								</p>
								{Array.isArray(result.data.files) && (
									<div>
										<p className="text-xs text-slate-500 mb-1">
											Present (
											{Array.isArray(result.data.files)
												? (result.data.files as string[]).length
												: 0}
											):
										</p>
										<div className="flex flex-wrap gap-1">
											{(result.data.files as string[]).map((f: string) => (
												<span
													key={f}
													className="text-xs bg-green-500/10 text-green-400 px-2 py-0.5 rounded"
												>
													{f}
												</span>
											))}
										</div>
									</div>
								)}
								{Array.isArray(result.data.missing) &&
									(result.data.missing as string[]).length > 0 && (
										<div>
											<p className="text-xs text-slate-500 mb-1">Missing:</p>
											<div className="flex flex-wrap gap-1">
												{(result.data.missing as string[]).map((f: string) => (
													<span
														key={f}
														className="text-xs bg-red-500/10 text-red-400 px-2 py-0.5 rounded"
													>
														{f}
													</span>
												))}
											</div>
										</div>
									)}
							</div>
						)}
					</div>
				)}

				{/* Run Tab */}
				{activeTab === "run" && (
					<div className="space-y-4 max-w-2xl">
						<h2 className="text-lg font-bold text-slate-200">Run Solver</h2>
						<p className="text-xs text-slate-500">
							Execute OpenFOAM via Docker
						</p>
						<div className="grid grid-cols-2 gap-3">
							{field("Case Name", input(caseName, setCaseName))}
							{field("Steps", input(solverSteps, setSolverSteps))}
							<div className="flex items-center gap-2">
								<input
									type="checkbox"
									checked={parallelRun}
									onChange={(e) => setParallelRun(e.target.checked)}
									className="accent-indigo-500"
								/>
								<label className="text-xs text-slate-400">Parallel</label>
							</div>
							{parallelRun &&
								field(
									"Cores",
									input(nCores, setNCores, { min: 1, max: 64, step: 1 }),
								)}
						</div>
						{btn("Run Solver", () =>
							callTool("cfd_run_solver", {
								case_name: caseName,
								steps: solverSteps,
								parallel: parallelRun,
								n_cores: Number(nCores),
							}),
						)}
						{result?.data && (
							<div className="p-4 bg-black/20 rounded-xl border border-white/10 space-y-1">
								<p className="text-xs text-slate-500">
									Steps completed:{" "}
									{(result.data.steps_completed as string[])?.join(", ") ||
										"none"}
								</p>
								{result.data.log && (
									<pre className="text-xs text-slate-400 mt-2 max-h-60 overflow-y-auto whitespace-pre-wrap font-mono">
										{String(result.data.log).slice(-5000)}
									</pre>
								)}
							</div>
						)}
					</div>
				)}

				{/* Results Tab */}
				{activeTab === "results" && (
					<div className="space-y-4 max-w-2xl">
						<h2 className="text-lg font-bold text-slate-200">Results</h2>
						{field("Case Name", input(caseName, setCaseName))}
						<div className="flex gap-2">
							{btn("Read Results", () =>
								callTool("cfd_read_results", { case_name: caseName }),
							)}
						</div>
						{result?.data && (
							<div className="space-y-3">
								<div className="p-4 bg-white/5 rounded-xl border border-white/10">
									<p className="text-sm font-medium text-slate-300 mb-2">
										Time Directories
									</p>
									<div className="flex flex-wrap gap-1">
										{(result.data.times as string[])?.map((t: string) => (
											<span
												key={t}
												className="text-xs bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded"
											>
												{t}
											</span>
										))}
									</div>
								</div>
								<div className="p-4 bg-white/5 rounded-xl border border-white/10">
									<p className="text-sm font-medium text-slate-300 mb-2">
										Final Residuals
									</p>
									<div className="grid grid-cols-3 gap-2">
										{result.data.final_residuals &&
											Object.entries(
												result.data.final_residuals as Record<string, number>,
											).map(([k, v]) => (
												<div key={k} className="text-center">
													<p className="text-xs text-slate-500">{k}</p>
													<p
														className={`text-sm font-mono ${v < 1e-4 ? "text-green-400" : "text-amber-400"}`}
													>
														{v.toExponential(2)}
													</p>
												</div>
											))}
									</div>
								</div>
								<div
									className="flex items-center gap-2 p-3 rounded-xl text-sm"
									style={{
										background: result.data.converged
											? "rgb(34 197 94 / 0.1)"
											: "rgb(251 191 36 / 0.1)",
									}}
								>
									{result.data.converged ? (
										<CheckCircle2 size={16} className="text-green-400" />
									) : (
										<AlertTriangle size={16} className="text-amber-400" />
									)}
									<span
										className={
											result.data.converged
												? "text-green-400"
												: "text-amber-400"
										}
									>
										{result.data.converged
											? "Solution converged"
											: "Solution did not fully converge"}
									</span>
								</div>
							</div>
						)}
					</div>
				)}

				{/* Parametric Tab */}
				{activeTab === "parametric" && (
					<div className="space-y-4 max-w-2xl">
						<h2 className="text-lg font-bold text-slate-200">
							Parametric Study
						</h2>
						<p className="text-xs text-slate-500">
							Design optimization via parameter sweep
						</p>
						<div className="grid grid-cols-2 gap-3">
							{field("Base Case", input(caseName, setCaseName))}
							{field(
								"Parameter",
								select(paramParameter, setParamParameter, [
									"inlet_velocity",
									"length",
									"width",
									"height",
									"fluid_nu",
									"angle",
								]),
							)}
							{field("Values (JSON array)", input(paramValues, setParamValues))}
							<div className="flex items-center gap-2">
								<input
									type="checkbox"
									checked={paramRun}
									onChange={(e) => setParamRun(e.target.checked)}
									className="accent-indigo-500"
								/>
								<label className="text-xs text-slate-400">
									Execute each case
								</label>
							</div>
						</div>
						{btn("Run Study", () =>
							callTool("cfd_parametric_study", {
								case_name: caseName,
								parameter: paramParameter,
								values: paramValues,
								run: paramRun,
							}),
						)}
					</div>
				)}

				{/* NL2FOAM Tab */}
				{activeTab === "nl2foam" && (
					<div className="space-y-4 max-w-2xl">
						<h2 className="text-lg font-bold text-slate-200">
							NL2FOAM — Natural Language to OpenFOAM
						</h2>
						<p className="text-xs text-slate-500">
							Describe your CFD problem and let the LLM generate the config
						</p>
						<div className="space-y-3">
							{field("Case Name", input(caseName, setCaseName))}
							{field("Model", input(nlModel, setNlModel))}
							<div className="flex flex-col gap-1">
								<label className="text-xs font-medium text-slate-400">
									Problem Description
								</label>
								<textarea
									value={nlDescription}
									onChange={(e) => setNlDescription(e.target.value)}
									placeholder="e.g. Incompressible laminar flow through a 1m long, 0.1m diameter pipe at Re=500 with water as the working fluid"
									rows={4}
									className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500/50 w-full resize-none font-mono"
								/>
							</div>
						</div>
						{btn("Generate Config", () =>
							callTool("cfd_nl2foam", {
								description: nlDescription,
								case_name: caseName,
								model: nlModel,
							}),
						)}
						{result?.data?.reasoning && (
							<div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
								<p className="text-xs text-indigo-300 mb-1">AI Reasoning</p>
								<p className="text-sm text-slate-300">
									{String(result.data.reasoning)}
								</p>
							</div>
						)}
					</div>
				)}

				{/* PINNs Tab */}
				{activeTab === "pinns" && (
					<div className="space-y-4 max-w-2xl">
						<h2 className="text-lg font-bold text-slate-200">
							PINN Point Cloud Sampling
						</h2>
						<p className="text-xs text-slate-500">
							Export coordinate points for Physics-Informed Neural Network
							training
						</p>
						<div className="grid grid-cols-2 gap-3">
							{field("Case Name", input(caseName, setCaseName))}
							{field(
								"Boundary Points",
								input(pinnBoundary, setPinnBoundary, { step: 1000 }),
							)}
							{field(
								"Interior Points",
								input(pinnInterior, setPinnInterior, { step: 1000 }),
							)}
							{field(
								"Format",
								select(pinnFormat, setPinnFormat, ["csv", "json", "numpy"]),
							)}
						</div>
						{btn("Sample Points", () =>
							callTool("cfd_sample_for_pinns", {
								case_name: caseName,
								n_boundary: Number(pinnBoundary),
								n_interior: Number(pinnInterior),
								output_format: pinnFormat,
							}),
						)}
						{result?.data?.output_file && (
							<div className="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
								<Download size={18} className="text-green-400" />
								<div>
									<p className="text-sm text-green-300">
										{String(result.data.output_file)}
									</p>
									<p className="text-xs text-green-400/70">
										{String(result.data.n_boundary)} boundary +{" "}
										{String(result.data.n_interior)} interior points
									</p>
								</div>
							</div>
						)}
					</div>
				)}

				{/* FluidX3D Tab */}
				{activeTab === "fluidx3d" && (
					<div className="space-y-4">
						<h2 className="text-lg font-bold text-slate-200">
							<Zap size={18} className="inline mr-1.5 text-indigo-400" />
							FluidX3D &mdash; GPU-Accelerated CFD
						</h2>

						{/* Status Grid */}
						<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
							<StatusCard
								icon={Cpu}
								label="FluidX3D Path"
								value={String(fx3dStatus?.path ?? "—")}
								ok={!!fx3dStatus?.path}
							/>
							<StatusCard
								icon={Terminal}
								label="Compiler"
								value={String(fx3dStatus?.compiler ?? "—")}
								ok={!!fx3dStatus?.compiler}
							/>
							<StatusCard
								icon={Box}
								label="GPUs"
								value={String(fx3dStatus?.gpu_count ?? "—")}
								ok={((fx3dStatus?.gpu_count as number) ?? 0) > 0}
							/>
							<StatusCard
								icon={CheckCircle2}
								label="Ready"
								value={fx3dStatus?.ready ? "Yes" : "No"}
								ok={!!fx3dStatus?.ready}
							/>
						</div>

						<button
							onClick={() =>
								callTool("cfd_fluidx3d_status", {}).then(
									(d) => d && setFx3dStatus(d.data ?? null),
								)
							}
							className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm text-slate-400"
						>
							<RefreshCw size={14} /> Check Status
						</button>

						{/* Quick-Start Presets */}
						<div>
							<p className="text-xs font-medium text-slate-400 mb-2">
								Quick-Start Presets
							</p>
							<div className="flex gap-2 flex-wrap">
								{[
									{ label: "Pipe Flow (laminar)", value: "pipe_laminar" },
									{ label: "Channel Flow", value: "channel" },
									{ label: "Airfoil (STL)", value: "airfoil_stl" },
								].map((p) => (
									<button
										key={p.value}
										onClick={() => {
											setFx3dPreset(p.value);
											setFx3dStep("setup");
											setFx3dForceData([]);
											setFx3dLog("");
											callTool("cfd_fluidx3d_setup", { preset: p.value });
										}}
										className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
											fx3dPreset === p.value
												? "bg-indigo-600/20 border-indigo-500/50 text-indigo-400"
												: "bg-white/5 border-white/10 text-slate-300 hover:bg-white/10"
										}`}
									>
										<Zap size={12} />
										{p.label}
									</button>
								))}
							</div>
						</div>

						{/* Workflow */}
						<div className="flex gap-2 flex-wrap">
							{btn(
								"1. Setup",
								() => {
									setFx3dStep("setup");
									callTool("cfd_fluidx3d_setup", { preset: fx3dPreset });
								},
								fx3dStep === "setup" ? "primary" : "secondary",
							)}
							{btn(
								"2. Compile",
								() => {
									setFx3dStep("compiling");
									callTool("cfd_fluidx3d_compile", { preset: fx3dPreset });
								},
								fx3dStep === "compiling" ? "primary" : "secondary",
							)}
							{btn(
								"3. Run",
								() => {
									setFx3dStep("running");
									callTool("cfd_fluidx3d_run", { preset: fx3dPreset }).then(
										(d) => {
											if (d?.success) {
												setFx3dMlups((d.data?.mlups as number) ?? 0);
												setFx3dCellCount((d.data?.cell_count as number) ?? 0);
												setFx3dRuntime((d.data?.runtime as number) ?? 0);
												setFx3dLog((d.data?.log as string) ?? "");
											}
										},
									);
								},
								fx3dStep === "running" ? "primary" : "secondary",
							)}
							{btn(
								"4. Results",
								() => {
									setFx3dStep("done");
									callTool("cfd_fluidx3d_results", { preset: fx3dPreset }).then(
										(d) => {
											if (d?.success) {
												setFx3dForceData(
													(d.data?.force_history as Record<
														string,
														unknown
													>[]) ?? [],
												);
												setFx3dMlups((d.data?.mlups as number) ?? fx3dMlups);
												setFx3dCellCount(
													(d.data?.cell_count as number) ?? fx3dCellCount,
												);
												setFx3dRuntime(
													(d.data?.runtime as number) ?? fx3dRuntime,
												);
											}
										},
									);
								},
								fx3dStep === "done" ? "primary" : "secondary",
							)}
						</div>

						{/* Progress */}
						{fx3dStep !== "idle" && (
							<div className="flex gap-4 text-xs">
								{[
									{ key: "setup" as const, label: "Setup" },
									{ key: "compiling" as const, label: "Compile" },
									{ key: "running" as const, label: "Run" },
									{ key: "done" as const, label: "Results" },
								].map((s) => {
									const order = [
										"idle",
										"setup",
										"compiling",
										"running",
										"done",
									];
									const idx = order.indexOf(fx3dStep);
									const si = order.indexOf(s.key);
									const done = si < idx;
									const active = si === idx;
									return (
										<div
											key={s.key}
											className={`flex items-center gap-1 ${done ? "text-green-400" : active ? "text-indigo-400" : "text-slate-600"}`}
										>
											{done ? (
												<CheckCircle2 size={12} />
											) : active ? (
												<Loader2 size={12} className="animate-spin" />
											) : (
												<div className="w-3 h-3 rounded-full border border-slate-600" />
											)}
											{s.label}
										</div>
									);
								})}
							</div>
						)}

						{/* Force Chart */}
						{fx3dForceData.length > 0 && (
							<div className="p-4 bg-white/5 rounded-xl border border-white/10">
								<p className="text-sm font-medium text-slate-300 mb-3">
									Force History
								</p>
								<ResponsiveContainer width="100%" height={250}>
									<LineChart data={fx3dForceData}>
										<CartesianGrid
											strokeDasharray="3 3"
											stroke="rgba(255,255,255,0.05)"
										/>
										<XAxis dataKey="time" stroke="#64748b" fontSize={11} />
										<YAxis stroke="#64748b" fontSize={11} />
										<Tooltip
											contentStyle={{
												background: "#1e293b",
												border: "1px solid rgba(255,255,255,0.1)",
												borderRadius: "8px",
											}}
										/>
										<Legend />
										<Line
											type="monotone"
											dataKey="drag"
											stroke="#ef4444"
											name="Drag"
											strokeWidth={2}
											dot={false}
										/>
										<Line
											type="monotone"
											dataKey="lift"
											stroke="#3b82f6"
											name="Lift"
											strokeWidth={2}
											dot={false}
										/>
									</LineChart>
								</ResponsiveContainer>
							</div>
						)}

						{/* Performance Metrics */}
						{(fx3dMlups > 0 || fx3dCellCount > 0 || fx3dRuntime > 0) && (
							<div className="grid grid-cols-3 gap-3">
								<div className="p-4 bg-white/5 rounded-xl border border-white/10 text-center">
									<p className="text-xs text-slate-500">MLUPS</p>
									<p className="text-lg font-mono text-indigo-400">
										{fx3dMlups.toFixed(1)}
									</p>
								</div>
								<div className="p-4 bg-white/5 rounded-xl border border-white/10 text-center">
									<p className="text-xs text-slate-500">Cells</p>
									<p className="text-lg font-mono text-indigo-400">
										{fx3dCellCount.toLocaleString()}
									</p>
								</div>
								<div className="p-4 bg-white/5 rounded-xl border border-white/10 text-center">
									<p className="text-xs text-slate-500">Runtime</p>
									<p className="text-lg font-mono text-indigo-400">
										{fx3dRuntime.toFixed(1)}s
									</p>
								</div>
							</div>
						)}

						{/* AI Explain */}
						{fx3dForceData.length > 0 && (
							<div className="space-y-2">
								<button
									onClick={() =>
										callTool("cfd_fluidx3d_explain", { preset: fx3dPreset })
									}
									disabled={loading}
									className="flex items-center gap-2 px-4 py-2 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-sm font-medium transition-all disabled:opacity-50"
								>
									{loading ? (
										<Loader2 size={14} className="animate-spin" />
									) : (
										<Sparkles size={14} />
									)}
									AI Explain
								</button>
								{result?.data?.explanation && (
									<div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
										<p className="text-xs text-indigo-300 mb-1">
											AI Explanation
										</p>
										<p className="text-sm text-slate-300">
											{String(result.data.explanation)}
										</p>
									</div>
								)}
							</div>
						)}

						{/* Log */}
						{fx3dLog && (
							<details className="p-4 bg-black/20 rounded-xl border border-white/10">
								<summary className="text-xs text-slate-400 cursor-pointer">
									Simulation Log
								</summary>
								<pre className="text-xs text-slate-400 mt-2 max-h-60 overflow-y-auto whitespace-pre-wrap font-mono">
									{fx3dLog}
								</pre>
							</details>
						)}
					</div>
				)}

				{/* Error display */}
				{error && (
					<div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
						<AlertTriangle size={18} className="text-red-400 shrink-0 mt-0.5" />
						<p className="text-sm text-red-300">{error}</p>
					</div>
				)}

				{/* Raw result */}
				{result && !result.success && (
					<details className="p-4 bg-red-500/5 border border-red-500/10 rounded-xl">
						<summary className="text-xs text-red-400 cursor-pointer">
							Error Details
						</summary>
						<pre className="text-xs text-slate-400 mt-2 whitespace-pre-wrap overflow-x-auto">
							{JSON.stringify(result, null, 2)}
						</pre>
					</details>
				)}
			</div>
		</div>
	);
}

function StatusCard({
	icon: Icon,
	label,
	value,
	ok,
}: { icon: React.ElementType; label: string; value: string; ok: boolean }) {
	return (
		<div
			className={`p-4 rounded-xl border ${ok ? "bg-green-500/5 border-green-500/20" : "bg-red-500/5 border-red-500/20"}`}
		>
			<div className="flex items-center gap-2 mb-2">
				<Icon size={14} className={ok ? "text-green-400" : "text-red-400"} />
				<span className="text-xs text-slate-500">{label}</span>
			</div>
			<p
				className={`text-sm font-mono ${ok ? "text-green-300" : "text-red-300"}`}
			>
				{value}
			</p>
		</div>
	);
}
