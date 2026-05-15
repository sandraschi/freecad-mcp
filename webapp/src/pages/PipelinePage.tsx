import { useState, useCallback } from "react";
import {
  AlertTriangle, ArrowRight, BarChart3, Box, CheckCircle2,
  Cpu, Download, FileText, FlaskConical, Layers, Loader2, Play,
  Server, Upload, Waves, Zap
} from "lucide-react";

const API = "/api/v1";

interface ToolResult {
  success: boolean;
  error?: string;
  case_name?: string;
  case_dir?: string;
  data?: Record<string, unknown>;
}

const steps = [
  { id: "geometry", label: "Geometry", icon: Box, num: 1 },
  { id: "solver", label: "Solver", icon: Cpu, num: 2 },
  { id: "physics", label: "Physics", icon: FlaskConical, num: 3 },
  { id: "boundaries", label: "Boundaries", icon: Layers, num: 4 },
  { id: "run", label: "Run", icon: Play, num: 5 },
  { id: "results", label: "Results", icon: BarChart3, num: 6 },
] as const;

type StepId = (typeof steps)[number]["id"];

export default function PipelinePage() {
  const [activeStep, setActiveStep] = useState<StepId>("geometry");
  const [completedSteps, setCompletedSteps] = useState<Set<StepId>>(new Set());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ToolResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [geometrySource, setGeometrySource] = useState<"new" | "stl">("new");
  const [caseName, setCaseName] = useState("pipeline_case");
  const [domainType, setDomainType] = useState("channel");
  const [lengthM, setLengthM] = useState(1.0);
  const [widthM, setWidthM] = useState(0.1);
  const [heightM, setHeightM] = useState(0.05);
  const [inletRadius, setInletRadius] = useState(0.02);
  const [outletRadius, setOutletRadius] = useState(0.01);
  const [meshCells, setMeshCells] = useState(20000);
  const [stlFile, setStlFile] = useState("");

  const [solver, setSolver] = useState<"openfoam" | "fluidx3d">("openfoam");

  const [flowType, setFlowType] = useState("laminar");
  const [fluidNu, setFluidNu] = useState(1e-6);
  const [fluidDensity, setFluidDensity] = useState(1000);
  const [inletVelocity, setInletVelocity] = useState(1.0);
  const [endTime, setEndTime] = useState(1000);
  const [deltaT, setDeltaT] = useState(1.0);
  const [writeInterval, setWriteInterval] = useState(100);

  const [resX, setResX] = useState(512);
  const [resY, setResY] = useState(128);
  const [resZ, setResZ] = useState(128);
  const [timeSteps, setTimeSteps] = useState(50000);

  const [bcInletVelocity, setBcInletVelocity] = useState("uniform (1 0 0)");
  const [bcOutletPressure, setBcOutletPressure] = useState("uniform 0");
  const [bcWallType, setBcWallType] = useState("noSlip");

  const [parallelRun, setParallelRun] = useState(false);
  const [nCores, setNCores] = useState(4);
  const [gpuDevice, setGpuDevice] = useState(0);
  const [timeoutS, setTimeoutS] = useState(3600);

  const openfoamTools = ["cfd_create_domain", "cfd_configure_physics", "cfd_set_boundary", "cfd_build_case", "cfd_run_solver", "cfd_read_results"];
  const fluidx3dTools = ["cfd_fluidx3d_setup", "cfd_fluidx3d_compile", "cfd_fluidx3d_run", "cfd_fluidx3d_results"];

  const callTool = useCallback(async (tool: string, args: Record<string, unknown>) => {
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
      if (!d.success) setError(d.error || "Tool failed");
      setResult(d);
      return d;
    } catch (e) {
      setError(String(e));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const markStepComplete = (step: StepId) => {
    setCompletedSteps((prev) => new Set(prev).add(step));
  };

  const goToStep = (step: StepId) => {
    const currentIdx = steps.findIndex((s) => s.id === activeStep);
    const targetIdx = steps.findIndex((s) => s.id === step);
    if (targetIdx <= currentIdx + 1 || completedSteps.has(step)) {
      setActiveStep(step);
    }
  };

  const goNext = () => {
    const idx = steps.findIndex((s) => s.id === activeStep);
    if (idx < steps.length - 1) setActiveStep(steps[idx + 1].id);
  };

  const field = (label: string, children: React.ReactNode) => (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-slate-400">{label}</label>
      {children}
    </div>
  );

  const input = (value: string | number, onChange: (v: string) => void, props?: Record<string, unknown>) => (
    <input
      type={typeof value === "number" ? "number" : "text"}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500/50 w-full font-mono"
      {...props}
    />
  );

  const select = (value: string, onChange: (v: string) => void, options: string[]) => (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500/50 w-full"
    >
      {options.map((o) => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  );

  const btn = (label: string, onClick: () => void, variant: "primary" | "secondary" | "danger" = "primary") => (
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

  const handleGeometrySubmit = async () => {
    if (geometrySource === "new") {
      if (solver === "openfoam") {
        await callTool("cfd_create_domain", {
          case_name: caseName,
          domain_type: domainType,
          length_m: Number(lengthM),
          width_m: Number(widthM),
          height_m: Number(heightM),
          inlet_radius_m: Number(inletRadius),
          outlet_radius_m: Number(outletRadius),
          mesh_cells: Number(meshCells),
        });
      } else {
        await callTool("cfd_fluidx3d_setup", {
          case_name: caseName,
          domain_type: domainType,
          resolution_x: Number(resX), resolution_y: Number(resY), resolution_z: Number(resZ),
          length_m: Number(lengthM),
          velocity_ms: Number(inletVelocity),
          viscosity_m2s: Number(fluidNu),
          density_kgm3: Number(fluidDensity),
          time_steps: Number(timeSteps),
          write_interval: Number(writeInterval),
        });
      }
    } else {
      if (solver === "openfoam") {
        await callTool("cfd_create_domain", {
          case_name: caseName,
          domain_type: "custom",
          step_file: stlFile,
          mesh_cells: Number(meshCells),
        });
      } else {
        await callTool("cfd_fluidx3d_setup", {
          case_name: caseName,
          domain_type: "stl",
          stl_file: stlFile,
          resolution_x: Number(resX), resolution_y: Number(resY), resolution_z: Number(resZ),
          velocity_ms: Number(inletVelocity),
          viscosity_m2s: Number(fluidNu),
          density_kgm3: Number(fluidDensity),
          time_steps: Number(timeSteps),
          write_interval: Number(writeInterval),
        });
      }
    }
    markStepComplete("geometry");
    goNext();
  };

  const handleSolverConfirm = () => {
    markStepComplete("solver");
    goNext();
  };

  const handlePhysicsSubmit = async () => {
    if (solver === "openfoam") {
      await callTool("cfd_configure_physics", {
        case_name: caseName,
        solver: "simpleFoam",
        flow_type: flowType,
        fluid_nu: Number(fluidNu),
        fluid_density: Number(fluidDensity),
        inlet_velocity: Number(inletVelocity),
        end_time: Number(endTime),
        delta_t: Number(deltaT),
        write_interval: Number(writeInterval),
      });
    } else {
      await callTool("cfd_fluidx3d_setup", {
        case_name: caseName,
        domain_type: domainType,
        resolution_x: Number(resX), resolution_y: Number(resY), resolution_z: Number(resZ),
        length_m: Number(lengthM),
        velocity_ms: Number(inletVelocity),
        viscosity_m2s: Number(fluidNu),
        density_kgm3: Number(fluidDensity),
        time_steps: Number(timeSteps),
        write_interval: Number(writeInterval),
      });
    }
    markStepComplete("physics");
    goNext();
  };

  const handleBoundarySubmit = async () => {
    await callTool("cfd_set_boundary", {
      case_name: caseName,
      patch_name: "inlet",
      field_name: "U",
      bc_type: "fixedValue",
      value: bcInletVelocity,
    });
    await callTool("cfd_set_boundary", {
      case_name: caseName,
      patch_name: "outlet",
      field_name: "p",
      bc_type: "fixedValue",
      value: bcOutletPressure,
    });
    await callTool("cfd_set_boundary", {
      case_name: caseName,
      patch_name: "walls",
      field_name: "U",
      bc_type: bcWallType,
      value: "uniform (0 0 0)",
    });
    markStepComplete("boundaries");
    goNext();
  };

  const handleRun = async () => {
    if (solver === "openfoam") {
      await callTool("cfd_run_solver", {
        case_name: caseName,
        steps: "blockMesh,checkMesh,simpleFoam",
        parallel: parallelRun,
        n_cores: Number(nCores),
      });
    } else {
      await callTool("cfd_fluidx3d_compile", { case_name: caseName });
      await callTool("cfd_fluidx3d_run", {
        case_name: caseName,
        gpu_device: Number(gpuDevice),
        timeout_s: Number(timeoutS),
      });
    }
    markStepComplete("run");
    goNext();
  };

  const handleReadResults = async () => {
    if (solver === "openfoam") {
      await callTool("cfd_read_results", { case_name: caseName });
    } else {
      await callTool("cfd_fluidx3d_results", { case_name: caseName });
    }
  };

  const isStepComplete = (id: StepId) => completedSteps.has(id);
  const activeIdx = steps.findIndex((s) => s.id === activeStep);

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-4 pb-2">
        <h1 className="text-lg font-bold text-slate-200 flex items-center gap-2">
          <Waves size={20} className="text-indigo-400" />
          CFD Pipeline Wizard
        </h1>
        <p className="text-xs text-slate-500 mt-1">Step-by-step setup for CFD simulation</p>
      </div>

      {/* Stepper */}
      <div className="px-4 py-3 border-b border-white/5">
        <div className="flex items-center">
          {steps.map((step, idx) => (
            <div key={step.id} className="flex items-center flex-1 last:flex-none">
              <button
                onClick={() => goToStep(step.id)}
                className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                  step.id === activeStep
                    ? "bg-indigo-600/20 text-indigo-400 ring-1 ring-indigo-500/30"
                    : isStepComplete(step.id)
                      ? "text-emerald-400 hover:text-emerald-300"
                      : "text-slate-600"
                }`}
              >
                {isStepComplete(step.id) ? (
                  <CheckCircle2 size={14} className="text-emerald-400" />
                ) : (
                  <span
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      step.id === activeStep ? "bg-indigo-600 text-white" : "bg-white/5 text-slate-600"
                    }`}
                  >
                    {step.num}
                  </span>
                )}
                <span className="hidden sm:inline">{step.label}</span>
              </button>
              {idx < steps.length - 1 && (
                <div
                  className={`flex-1 h-px mx-0.5 ${
                    isStepComplete(step.id) ? "bg-emerald-500/30" : "bg-white/5"
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {steps.map((step) => {
          const isActive = step.id === activeStep;
          const isComplete = isStepComplete(step.id);
          const StepIcon = step.icon;

          return (
            <div
              key={step.id}
              className={`rounded-xl border transition-all ${
                isActive
                  ? "bg-white/5 border-indigo-500/30"
                  : isComplete
                    ? "bg-white/[0.02] border-emerald-500/10"
                    : "bg-white/[0.01] border-white/5 opacity-40"
              }`}
            >
              <button
                onClick={() => goToStep(step.id)}
                className="w-full flex items-center gap-3 px-4 py-3 text-left"
              >
                <div
                  className={`p-1.5 rounded-lg ${
                    isActive
                      ? "bg-indigo-600/20 text-indigo-400"
                      : isComplete
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-white/5 text-slate-600"
                  }`}
                >
                  <StepIcon size={16} />
                </div>
                <div className="flex-1">
                  <p
                    className={`text-sm font-medium ${
                      isActive ? "text-slate-200" : isComplete ? "text-slate-300" : "text-slate-600"
                    }`}
                  >
                    Step {step.num}: {step.label}
                  </p>
                </div>
                {isComplete && <CheckCircle2 size={14} className="text-emerald-400" />}
              </button>

              {isActive && (
                <div className="px-4 pb-4 space-y-3 border-t border-white/5 pt-3">
                  {/* Geometry */}
                  {step.id === "geometry" && (
                    <>
                      <p className="text-xs text-slate-500">Choose how to define your fluid domain</p>

                      <div className="flex gap-2">
                        <button
                          onClick={() => setGeometrySource("new")}
                          className={`flex-1 p-3 rounded-lg border text-left transition-all ${
                            geometrySource === "new"
                              ? "bg-indigo-600/10 border-indigo-500/30 text-slate-200"
                              : "bg-white/5 border-white/10 text-slate-500 hover:text-slate-300"
                          }`}
                        >
                          <Box size={16} className="mb-1 text-indigo-400" />
                          <p className="text-xs font-medium">Create new domain</p>
                          <p className="text-[10px] text-slate-500">Parametric channel/pipe/box/nozzle</p>
                        </button>
                        <button
                          onClick={() => setGeometrySource("stl")}
                          className={`flex-1 p-3 rounded-lg border text-left transition-all ${
                            geometrySource === "stl"
                              ? "bg-indigo-600/10 border-indigo-500/30 text-slate-200"
                              : "bg-white/5 border-white/10 text-slate-500 hover:text-slate-300"
                          }`}
                        >
                          <Upload size={16} className="mb-1 text-indigo-400" />
                          <p className="text-xs font-medium">Use existing STL</p>
                          <p className="text-[10px] text-slate-500">Upload or select from files</p>
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        {field("Case Name", input(caseName, setCaseName))}
                        {geometrySource === "new" ? (
                          <>
                            {field("Domain Type", select(domainType, setDomainType, ["channel", "pipe", "box", "nozzle"]))}
                            {field("Length (m)", input(lengthM, setLengthM, { min: 0.001, step: 0.1 }))}
                            {field("Width (m)", input(widthM, setWidthM, { min: 0.001, step: 0.01 }))}
                            {field("Height (m)", input(heightM, setHeightM, { min: 0.001, step: 0.01 }))}
                            {field("Mesh Cells", input(meshCells, setMeshCells, { step: 1000 }))}
                            {domainType === "pipe" && field("Inlet Radius (m)", input(inletRadius, setInletRadius, { step: 0.001 }))}
                            {domainType === "nozzle" && (
                              <>
                                {field("Inlet Radius (m)", input(inletRadius, setInletRadius, { step: 0.001 }))}
                                {field("Outlet Radius (m)", input(outletRadius, setOutletRadius, { step: 0.001 }))}
                              </>
                            )}
                          </>
                        ) : (
                          <>
                            {field("STL File Path", input(stlFile, setStlFile))}
                            {field("Mesh Cells", input(meshCells, setMeshCells, { step: 1000 }))}
                          </>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <FileText size={12} />
                        Will call: {solver === "openfoam" ? "cfd_create_domain" : "cfd_fluidx3d_setup"}
                      </div>

                      <div className="flex gap-2">
                        {btn("Create Domain", handleGeometrySubmit)}
                      </div>
                    </>
                  )}

                  {/* Solver */}
                  {step.id === "solver" && (
                    <>
                      <p className="text-xs text-slate-500">Select your CFD solver engine</p>

                      <div className="flex gap-3">
                        <button
                          onClick={() => setSolver("openfoam")}
                          className={`flex-1 p-4 rounded-lg border text-left transition-all ${
                            solver === "openfoam"
                              ? "bg-indigo-600/10 border-indigo-500/30"
                              : "bg-white/5 border-white/10 hover:border-white/20"
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <Server size={16} className="text-blue-400" />
                            <span className={`text-sm font-medium ${solver === "openfoam" ? "text-slate-200" : "text-slate-400"}`}>
                              OpenFOAM
                            </span>
                          </div>
                          <p className="text-[10px] text-slate-500 mb-2">CPU · Docker container</p>
                          <div className="flex flex-wrap gap-1">
                            {openfoamTools.map((t) => (
                              <span key={t} className="text-[10px] bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded">
                                {t}
                              </span>
                            ))}
                          </div>
                        </button>

                        <button
                          onClick={() => setSolver("fluidx3d")}
                          className={`flex-1 p-4 rounded-lg border text-left transition-all ${
                            solver === "fluidx3d"
                              ? "bg-indigo-600/10 border-indigo-500/30"
                              : "bg-white/5 border-white/10 hover:border-white/20"
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <Zap size={16} className="text-emerald-400" />
                            <span className={`text-sm font-medium ${solver === "fluidx3d" ? "text-slate-200" : "text-slate-400"}`}>
                              FluidX3D
                            </span>
                          </div>
                          <p className="text-[10px] text-slate-500 mb-2">GPU · OpenCL</p>
                          <div className="flex flex-wrap gap-1">
                            {fluidx3dTools.map((t) => (
                              <span key={t} className="text-[10px] bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded">
                                {t}
                              </span>
                            ))}
                          </div>
                        </button>
                      </div>

                      {btn("Confirm Solver", handleSolverConfirm)}
                    </>
                  )}

                  {/* Physics */}
                  {step.id === "physics" && (
                    <>
                      <p className="text-xs text-slate-500">Configure fluid properties and flow conditions</p>

                      <div className="grid grid-cols-2 gap-3">
                        {field("Case Name", input(caseName, setCaseName))}
                        {solver === "openfoam" ? (
                          <>
                            {field("Flow Model", select(flowType, setFlowType, ["laminar", "kEpsilon", "kOmegaSST"]))}
                            {field("Kinematic Viscosity (m²/s)", input(fluidNu, setFluidNu, { step: "1e-7" }))}
                            {field("Density (kg/m³)", input(fluidDensity, setFluidDensity, { step: 1 }))}
                            {field("Inlet Velocity (m/s)", input(inletVelocity, setInletVelocity, { step: 0.1 }))}
                            {field("End Time / Iterations", input(endTime, setEndTime, { step: 100 }))}
                            {field("Time Step (s)", input(deltaT, setDeltaT, { step: 0.1 }))}
                            {field("Write Interval", input(writeInterval, setWriteInterval, { step: 50 }))}
                          </>
                        ) : (
                          <>
                            {field("Velocity (m/s)", input(inletVelocity, setInletVelocity, { step: 0.001 }))}
                            {field("Viscosity (m²/s)", input(fluidNu, setFluidNu))}
                            {field("Density (kg/m³)", input(fluidDensity, setFluidDensity))}
                            {field("Resolution X", input(resX, setResX, { min: 16, step: 64 }))}
                            {field("Resolution Y", input(resY, setResY, { min: 16, step: 32 }))}
                            {field("Resolution Z", input(resZ, setResZ, { min: 16, step: 32 }))}
                            {field("Time Steps", input(timeSteps, setTimeSteps, { step: 10000 }))}
                            {field("Write Interval", input(writeInterval, setWriteInterval, { step: 100 }))}
                            <div className="col-span-2 flex items-center gap-2 text-xs text-slate-500">
                              <Cpu size={12} />
                              Total cells: {(resX * resY * resZ).toLocaleString()} | ~{((resX * resY * resZ * 55) / 1e9).toFixed(2)} GB VRAM
                            </div>
                          </>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <FileText size={12} />
                        Will call: {solver === "openfoam" ? "cfd_configure_physics" : "cfd_fluidx3d_setup"}
                      </div>

                      {btn("Configure Physics", handlePhysicsSubmit)}
                    </>
                  )}

                  {/* Boundaries */}
                  {step.id === "boundaries" && (
                    <>
                      {solver === "openfoam" ? (
                        <>
                          <p className="text-xs text-slate-500">Configure boundary conditions for inlet, outlet, and walls</p>

                          <div className="grid grid-cols-2 gap-3">
                            {field("Case Name", input(caseName, setCaseName))}
                            <div className="flex flex-col gap-1">
                              <label className="text-xs font-medium text-slate-400">Inlet Velocity (U)</label>
                              <input
                                value={bcInletVelocity}
                                onChange={(e) => setBcInletVelocity(e.target.value)}
                                className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500/50 w-full font-mono"
                              />
                            </div>
                            <div className="flex flex-col gap-1">
                              <label className="text-xs font-medium text-slate-400">Outlet Pressure (p)</label>
                              <input
                                value={bcOutletPressure}
                                onChange={(e) => setBcOutletPressure(e.target.value)}
                                className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500/50 w-full font-mono"
                              />
                            </div>
                            {field("Wall Type", select(bcWallType, setBcWallType, ["noSlip", "slip", "symmetry"]))}
                          </div>

                          <div className="flex items-center gap-2 text-xs text-slate-500">
                            <FileText size={12} />
                            Will call: cfd_set_boundary (inlet, outlet, walls)
                          </div>

                          {btn("Set Boundaries", handleBoundarySubmit)}
                        </>
                      ) : (
                        <div className="space-y-3">
                          <p className="text-xs text-slate-500">
                            FluidX3D boundary conditions are embedded in the setup file. No separate BC configuration needed.
                          </p>
                          <p className="text-xs text-emerald-400">
                            Boundaries defined via: domain_type = "{domainType}" with automatic BCs
                          </p>
                          {btn("Continue", () => {
                            markStepComplete("boundaries");
                            goNext();
                          })}
                        </div>
                      )}
                    </>
                  )}

                  {/* Run */}
                  {step.id === "run" && (
                    <>
                      <p className="text-xs text-slate-500">Execute the simulation</p>

                      {solver === "openfoam" ? (
                        <div className="grid grid-cols-2 gap-3">
                          {field("Case Name", input(caseName, setCaseName))}
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={parallelRun}
                              onChange={(e) => setParallelRun(e.target.checked)}
                              className="accent-indigo-500"
                            />
                            <label className="text-xs text-slate-400">Parallel run</label>
                          </div>
                          {parallelRun && field("Cores", input(nCores, setNCores, { min: 1, max: 64, step: 1 }))}
                          <div className="col-span-2 flex items-center gap-2 text-xs text-slate-500">
                            <FileText size={12} />
                            Steps: blockMesh → checkMesh → simpleFoam
                          </div>
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 gap-3">
                          {field("Case Name", input(caseName, setCaseName))}
                          {field("GPU Device Index", input(gpuDevice, setGpuDevice, { min: 0 }))}
                          {field("Timeout (s)", input(timeoutS, setTimeoutS, { min: 10, step: 60 }))}
                          <div className="col-span-2 flex items-center gap-2 text-xs text-slate-500">
                            <FileText size={12} />
                            Steps: cfd_fluidx3d_compile → cfd_fluidx3d_run
                          </div>
                        </div>
                      )}

                      {btn(solver === "openfoam" ? "Run OpenFOAM Solver" : "Run on GPU", handleRun)}

                      {result?.data && (
                        <div className="p-4 bg-black/20 rounded-xl border border-white/10 space-y-1">
                          {result.data.runtime_s && (
                            <p className="text-sm text-emerald-300">Runtime: {String(result.data.runtime_s)}s</p>
                          )}
                          {result.data.steps_completed && (
                            <p className="text-xs text-slate-400">
                              Completed: {(result.data.steps_completed as string[])?.join(", ")}
                            </p>
                          )}
                          {result.data.log && (
                            <pre className="text-xs text-slate-500 mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap font-mono">
                              {String(result.data.log).slice(-3000)}
                            </pre>
                          )}
                          {result.data.output &&
                            typeof result.data.output === "string" &&
                            result.data.output.includes("DONE") && (
                              <p className="text-xs text-emerald-400">Simulation completed successfully</p>
                            )}
                        </div>
                      )}
                    </>
                  )}

                  {/* Results */}
                  {step.id === "results" && (
                    <>
                      <p className="text-xs text-slate-500">View simulation results and download output files</p>

                      <div className="flex gap-2">
                        {btn("Read Results", handleReadResults)}
                      </div>

                      {result?.data && (
                        <div className="space-y-3">
                          {result.data.mlups && (
                            <div className="grid grid-cols-3 gap-2">
                              <div className="p-3 bg-white/5 rounded-xl border border-white/10 text-center">
                                <p className="text-xs text-slate-500">Throughput</p>
                                <p className="text-lg font-mono text-emerald-400">{String(result.data.mlups)}</p>
                                <p className="text-[10px] text-slate-600">MLUPS</p>
                              </div>
                              <div className="p-3 bg-white/5 rounded-xl border border-white/10 text-center">
                                <p className="text-xs text-slate-500">Steps</p>
                                <p className="text-lg font-mono text-slate-200">
                                  {String(result.data.time_steps_completed ?? "\u2014")}
                                </p>
                              </div>
                              <div className="p-3 bg-white/5 rounded-xl border border-white/10 text-center">
                                <p className="text-xs text-slate-500">Wall Time</p>
                                <p className="text-lg font-mono text-slate-200">
                                  {String(result.data.runtime_s ?? "\u2014")}s
                                </p>
                              </div>
                            </div>
                          )}

                          {result.data.final_residuals && (
                            <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                              <p className="text-sm font-medium text-slate-300 mb-2">Final Residuals</p>
                              <div className="grid grid-cols-3 gap-2">
                                {Object.entries(result.data.final_residuals as Record<string, number>).map(
                                  ([k, v]) => (
                                    <div key={k} className="text-center">
                                      <p className="text-xs text-slate-500">{k}</p>
                                      <p
                                        className={`text-sm font-mono ${
                                          typeof v === "number" && v < 1e-4
                                            ? "text-green-400"
                                            : "text-amber-400"
                                        }`}
                                      >
                                        {typeof v === "number" ? v.toExponential(2) : String(v)}
                                      </p>
                                    </div>
                                  )
                                )}
                              </div>
                            </div>
                          )}

                          {result.data.final_forces && (
                            <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                              <p className="text-sm font-medium text-slate-300 mb-2">Final Forces (N)</p>
                              <div className="grid grid-cols-3 gap-2 text-center">
                                {Object.entries(result.data.final_forces as Record<string, number>).map(
                                  ([k, v]) => (
                                    <div key={k}>
                                      <p className="text-xs text-slate-500">{k}</p>
                                      <p className="text-sm font-mono text-slate-200">
                                        {typeof v === "number" ? v.toExponential(3) : String(v)}
                                      </p>
                                    </div>
                                  )
                                )}
                              </div>
                            </div>
                          )}

                          {result.data.converged !== undefined && (
                            <div
                              className={`flex items-center gap-2 p-3 rounded-xl text-sm ${
                                result.data.converged
                                  ? "bg-emerald-500/10 text-emerald-400"
                                  : "bg-amber-500/10 text-amber-400"
                              }`}
                            >
                              {result.data.converged ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                              {result.data.converged
                                ? "Solution converged"
                                : "Solution did not fully converge"}
                            </div>
                          )}

                          {result.data.completed !== undefined && (
                            <div
                              className={`flex items-center gap-2 p-3 rounded-xl text-sm ${
                                result.data.completed
                                  ? "bg-emerald-500/10 text-emerald-400"
                                  : "bg-amber-500/10 text-amber-400"
                              }`}
                            >
                              {result.data.completed ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                              {result.data.completed
                                ? "Simulation completed"
                                : "Incomplete — check run log"}
                            </div>
                          )}

                          {Array.isArray(result.data.vtk_files) &&
                            (result.data.vtk_files as string[]).length > 0 && (
                              <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                                <p className="text-sm font-medium text-slate-300 mb-2">VTK Output Files</p>
                                <div className="flex flex-wrap gap-1">
                                  {(result.data.vtk_files as string[]).map((f: string) => (
                                    <span
                                      key={f}
                                      className="flex items-center gap-1 text-xs bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded"
                                    >
                                      <Download size={10} />
                                      {f}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {error && (
          <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
            <AlertTriangle size={18} className="text-red-400 shrink-0 mt-0.5" />
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {result && !result.success && (
          <details className="p-4 bg-red-500/5 border border-red-500/10 rounded-xl">
            <summary className="text-xs text-red-400 cursor-pointer">Error Details</summary>
            <pre className="text-xs text-slate-400 mt-2 whitespace-pre-wrap overflow-x-auto">
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}
