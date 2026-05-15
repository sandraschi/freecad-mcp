import { useState, useEffect, useCallback } from "react";
import { AlertTriangle, BarChart3, Binary, Box, Cpu, FileCode2, Gauge, Info, Loader2, Play, RefreshCw, Rocket, Zap } from "lucide-react";

const API = "/api/v1";

interface F3DStatus {
  success: boolean;
  fluidx3d_path: string | null;
  compiler: string;
  ready: boolean;
  error?: string;
}

interface ToolResult {
  success: boolean;
  error?: string;
  case_name?: string;
  data?: Record<string, unknown>;
}

const tabs = [
  { id: "status", label: "Status", icon: Gauge },
  { id: "setup", label: "Setup", icon: FileCode2 },
  { id: "compile", label: "Compile", icon: Binary },
  { id: "run", label: "Run GPU", icon: Zap },
  { id: "results", label: "Results", icon: BarChart3 },
  { id: "explain", label: "Explain", icon: Info },
] as const;

type TabId = (typeof tabs)[number]["id"];

export default function Fluidx3dPage() {
  const [activeTab, setActiveTab] = useState<TabId>("status");
  const [status, setStatus] = useState<F3DStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ToolResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Setup form
  const [caseName, setCaseName] = useState("f3d_channel");
  const [domainType, setDomainType] = useState("channel");
  const [resX, setResX] = useState(512);
  const [resY, setResY] = useState(128);
  const [resZ, setResZ] = useState(128);
  const [lengthM, setLengthM] = useState(1.0);
  const [velocityMs, setVelocityMs] = useState(0.01);
  const [viscosity, setViscosity] = useState("1e-6");
  const [density, setDensity] = useState(1000);
  const [timeSteps, setTimeSteps] = useState(50000);
  const [writeInterval, setWriteInterval] = useState(1000);
  const [stlFile, setStlFile] = useState("");
  const [openclLib, setOpenclLib] = useState("");
  const [gpuDevice, setGpuDevice] = useState(0);
  const [timeoutS, setTimeoutS] = useState(3600);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const r = await fetch(`${API}/control/tool`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool: "cfd_fluidx3d_status", arguments: {} }),
      });
      setStatus(await r.json());
    } catch {
      // server not ready
    }
  };

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
      if (!d.success) setError(d.error || "Tool returned failure");
      setResult(d);
      return d;
    } catch (e) {
      setError(String(e));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

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
      className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500/50 w-full font-mono"
      {...props}
    />
  );

  const select = (value: string, onChange: (v: string) => void, options: string[]) => (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500/50 w-full"
    >
      {options.map((o) => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  );

  const btn = (label: string, onClick: () => void, icon?: React.ReactNode) => (
    <button
      onClick={onClick}
      disabled={loading}
      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-all disabled:opacity-50"
    >
      {loading ? <Loader2 size={14} className="animate-spin" /> : icon}
      {label}
    </button>
  );

  const StatusBadge = ({ ok, label }: { ok: boolean; label: string }) => (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ok ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
      {ok ? "✓" : "✗"} {label}
    </span>
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex gap-1 px-4 pt-4 pb-0 border-b border-white/5 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-t-lg text-xs font-medium transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? "bg-emerald-600/20 text-emerald-400 border-b-2 border-emerald-500"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            <tab.icon size={14} />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Status */}
        {activeTab === "status" && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-slate-200">FluidX3D GPU Pipeline</h2>
              <span className="text-xs text-slate-500 bg-emerald-500/10 px-2 py-0.5 rounded">OpenCL • All GPUs</span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {status ? (
                <>
                  <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                    <p className="text-xs text-slate-500 mb-1">FluidX3D Path</p>
                    <p className="text-sm font-mono text-slate-300 break-all">{status.fluidx3d_path || "Not found"}</p>
                  </div>
                  <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                    <p className="text-xs text-slate-500 mb-1">Compiler</p>
                    <p className="text-sm font-mono text-slate-300">{status.compiler}</p>
                  </div>
                  <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                    <p className="text-xs text-slate-500 mb-1">Pipeline</p>
                    <StatusBadge ok={status.ready} label={status.ready ? "Ready" : "Missing deps"} />
                  </div>
                </>
              ) : (
                <div className="col-span-3 text-slate-500 text-sm">Checking FluidX3D installation...</div>
              )}
            </div>

            {status?.error && (
              <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
                <div className="text-sm text-amber-200">
                  <p className="font-medium mb-1">{status.error}</p>
                  <code className="text-xs bg-black/30 px-2 py-0.5 rounded block mt-2">git clone https://github.com/ProjectPhysX/FluidX3D.git</code>
                </div>
              </div>
            )}

            <button onClick={fetchStatus} className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm text-slate-400">
              <RefreshCw size={14} /> Refresh
            </button>

            <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
              <p className="text-sm font-medium text-emerald-300 mb-2">Why FluidX3D?</p>
              <ul className="text-xs text-slate-400 space-y-1">
                <li>• GPU-native — runs on NVIDIA, AMD, Intel Arc, Apple Silicon via OpenCL</li>
                <li>• 55 bytes/cell (6× less memory than traditional LBM)</li>
                <li>• 770³ cells on RTX 4090 24GB (≈ 456 million cells)</li>
                <li>• Free for non-commercial use, 5k+ GitHub stars, active maintenance</li>
              </ul>
            </div>
          </div>
        )}

        {/* Setup */}
        {activeTab === "setup" && (
          <div className="space-y-4 max-w-2xl">
            <h2 className="text-lg font-bold text-slate-200">Generate FluidX3D Setup</h2>
            <p className="text-xs text-slate-500">Creates a C++ setup.cpp and defines.hpp for GPU simulation</p>

            <div className="grid grid-cols-2 gap-3">
              {field("Case Name", input(caseName, setCaseName))}
              {field("Domain Type", select(domainType, setDomainType, ["channel", "pipe", "box", "stl"]))}
              {field("Resolution X", input(resX, setResX, { min: 16, step: 64 }))}
              {field("Resolution Y", input(resY, setResY, { min: 16, step: 32 }))}
              {field("Resolution Z", input(resZ, setResZ, { min: 16, step: 32 }))}
              <div className="col-span-2 flex items-center gap-2 text-xs text-slate-500">
                <Cpu size={12} />
                Total cells: {(resX * resY * resZ).toLocaleString()} | ~{((resX * resY * resZ * 55) / 1e9).toFixed(2)} GB VRAM (FP32) | ~{((resX * resY * resZ * 55) / 2 / 1e9).toFixed(2)} GB (FP16)
              </div>
              {field("Length (m)", input(lengthM, setLengthM, { step: 0.1 }))}
              {field("Velocity (m/s)", input(velocityMs, setVelocityMs, { step: 0.001 }))}
              {field("Viscosity (m²/s)", input(viscosity, setViscosity))}
              {field("Density (kg/m³)", input(density, setDensity))}
              {field("Time Steps", input(timeSteps, setTimeSteps, { step: 10000 }))}
              {field("Write Interval", input(writeInterval, setWriteInterval, { step: 100 }))}
              {domainType === "stl" && field("STL File", input(stlFile, setStlFile))}
            </div>

            <div className="flex gap-2">
              {btn("Generate Setup", () =>
                callTool("cfd_fluidx3d_setup", {
                  case_name: caseName,
                  domain_type: domainType,
                  resolution_x: Number(resX), resolution_y: Number(resY), resolution_z: Number(resZ),
                  length_m: Number(lengthM),
                  velocity_ms: Number(velocityMs),
                  viscosity_m2s: Number(viscosity),
                  density_kgm3: Number(density),
                  time_steps: Number(timeSteps),
                  write_interval: Number(writeInterval),
                  stl_file: stlFile,
                }),
                <FileCode2 size={14} />
              )}
            </div>

            {result?.data && (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl space-y-1">
                <p className="text-sm text-emerald-300">Setup generated</p>
                <p className="text-xs text-slate-400">
                  Re ≈ {String(result.data.Re_estimate)} | {String(result.data.resolution)} | {String(result.data.cells)} cells
                </p>
                <p className="text-xs text-slate-500 font-mono">{String(result.data.setup_file)}</p>
              </div>
            )}
          </div>
        )}

        {/* Compile */}
        {activeTab === "compile" && (
          <div className="space-y-4 max-w-2xl">
            <h2 className="text-lg font-bold text-slate-200">Compile to GPU Binary</h2>
            <p className="text-xs text-slate-500">Compiles setup.cpp into an OpenCL GPU executable via g++ or MSVC</p>
            <div className="grid grid-cols-2 gap-3">
              {field("Case Name", input(caseName, setCaseName))}
              {field("OpenCL Lib Hint", input(openclLib, setOpenclLib))}
            </div>
            {btn("Compile", () =>
              callTool("cfd_fluidx3d_compile", { case_name: caseName, opencl_lib: openclLib }),
              <Binary size={14} />
            )}
            {result?.data && (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl space-y-1">
                <p className="text-sm text-emerald-300">Compiled in {String(result.data.compile_time_s)}s</p>
                <p className="text-xs text-slate-400">Compiler: {String(result.data.compiler)}</p>
                <p className="text-xs text-slate-500 font-mono">{String(result.data.binary)}</p>
                {result.data.warnings && <p className="text-xs text-amber-400 mt-1">{String(result.data.warnings).slice(0, 500)}</p>}
              </div>
            )}
          </div>
        )}

        {/* Run */}
        {activeTab === "run" && (
          <div className="space-y-4 max-w-2xl">
            <h2 className="text-lg font-bold text-slate-200">Run GPU Simulation</h2>
            <p className="text-xs text-slate-500">Executes the compiled FluidX3D binary on the GPU via OpenCL</p>
            <div className="grid grid-cols-2 gap-3">
              {field("Case Name", input(caseName, setCaseName))}
              {field("GPU Device Index", input(gpuDevice, setGpuDevice, { min: 0 }))}
              {field("Timeout (s)", input(timeoutS, setTimeoutS, { min: 10, step: 60 }))}
            </div>
            {btn("Run on GPU", () =>
              callTool("cfd_fluidx3d_run", { case_name: caseName, gpu_device: Number(gpuDevice), timeout_s: Number(timeoutS) }),
              <Zap size={14} />
            )}
            {result?.data && (
              <div className="space-y-3">
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl space-y-1">
                  <p className="text-sm text-emerald-300">
                    Exit: {String(result.data.exit_code)} | Runtime: {String(result.data.runtime_s)}s
                  </p>
                  {String(result.data.output).includes("DONE") && (
                    <p className="text-xs text-emerald-400">Simulation completed successfully</p>
                  )}
                </div>
                {result.data.output && (
                  <details className="p-3 bg-black/20 rounded-xl">
                    <summary className="text-xs text-slate-500 cursor-pointer">Console output</summary>
                    <pre className="text-xs text-slate-400 mt-2 max-h-60 overflow-y-auto whitespace-pre-wrap font-mono">{String(result.data.output).slice(-5000)}</pre>
                  </details>
                )}
                {Array.isArray(result.data.vtk_files) && (result.data.vtk_files as string[]).length > 0 && (
                  <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                    <p className="text-xs text-slate-500">VTK output files ({(result.data.vtk_files as string[]).length}):</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Results */}
        {activeTab === "results" && (
          <div className="space-y-4 max-w-2xl">
            <h2 className="text-lg font-bold text-slate-200">Parse Results</h2>
            {field("Case Name", input(caseName, setCaseName))}
            {btn("Parse Results", () => callTool("cfd_fluidx3d_results", { case_name: caseName }), <BarChart3 size={14} />)}
            {result?.data && (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-3 bg-white/5 rounded-xl border border-white/10 text-center">
                    <p className="text-xs text-slate-500">Throughput</p>
                    <p className="text-lg font-mono text-emerald-400">{String(result.data.mlups)}</p>
                    <p className="text-[10px] text-slate-600">MLUPS</p>
                  </div>
                  <div className="p-3 bg-white/5 rounded-xl border border-white/10 text-center">
                    <p className="text-xs text-slate-500">Steps</p>
                    <p className="text-lg font-mono text-slate-200">{String(result.data.time_steps_completed)}</p>
                  </div>
                  <div className="p-3 bg-white/5 rounded-xl border border-white/10 text-center">
                    <p className="text-xs text-slate-500">Wall Time</p>
                    <p className="text-lg font-mono text-slate-200">{String(result.data.runtime_s)}s</p>
                  </div>
                </div>

                {result.data.final_forces && (
                  <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                    <p className="text-sm font-medium text-slate-300 mb-2">Final Forces (N)</p>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      {Object.entries(result.data.final_forces as Record<string, number>).map(([k, v]) => (
                        <div key={k}>
                          <p className="text-xs text-slate-500">{k}</p>
                          <p className="text-sm font-mono text-slate-200">{v.toExponential(3)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {result.data.completed !== undefined && (
                  <div className={`flex items-center gap-2 p-3 rounded-xl text-sm ${
                    result.data.completed ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"
                  }`}>
                    {result.data.completed ? <Rocket size={14} /> : <AlertTriangle size={14} />}
                    {result.data.completed ? "Simulation completed" : "Incomplete — check run log"}
                  </div>
                )}

                {Array.isArray(result.data.forces) && (result.data.forces as Array<{step: number; Fx: number; Fy: number; Fz: number}>).length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs text-slate-500">Force history (last {(result.data.forces as unknown[]).length} points)</p>
                    <div className="max-h-40 overflow-y-auto space-y-0.5">
                      {(result.data.forces as Array<{step: number; Fx: number; Fy: number; Fz: number}>).slice(-20).map((f: {step: number; Fx: number; Fy: number; Fz: number}) => (
                        <div key={f.step} className="flex gap-4 text-xs font-mono text-slate-400">
                          <span className="w-20 text-slate-600">t={f.step}</span>
                          <span>Fx={f.Fx.toExponential(3)}</span>
                          <span>Fy={f.Fy.toExponential(3)}</span>
                          <span>Fz={f.Fz.toExponential(3)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Explain */}
        {activeTab === "explain" && (
          <div className="space-y-4 max-w-2xl">
            <h2 className="text-lg font-bold text-slate-200">Explain Simulation</h2>
            {field("Case Name", input(caseName, setCaseName))}
            {btn("Explain", () => callTool("cfd_fluidx3d_explain", { case_name: caseName }), <Info size={14} />)}
            {result?.data && (
              <div className="space-y-3">
                <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                  <p className="text-sm text-slate-300">{String(result.data.summary)}</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
                    <p className="text-xs text-slate-500">Reynolds Number</p>
                    <p className="text-xl font-mono text-indigo-400">{String(result.data.Re)}</p>
                  </div>
                  <div className="p-3 bg-purple-500/10 rounded-xl border border-purple-500/20">
                    <p className="text-xs text-slate-500">Flow Regime</p>
                    <p className="text-sm text-purple-300">{String(result.data.regime)}</p>
                  </div>
                </div>
                <div className="p-4 bg-black/20 rounded-xl border border-white/10">
                  <p className="text-xs text-slate-500 mb-1">Solver Notes</p>
                  <p className="text-xs text-slate-400">{String(result.data.solver_notes)}</p>
                </div>
              </div>
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
      </div>
    </div>
  );
}
