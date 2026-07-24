import { useState, useEffect, useCallback, useRef } from "react";
import { Activity, AlertTriangle, BarChart3, Binary, Box, Cpu, FileCode2, Film, Gauge, Info, Loader2, Play, RefreshCw, Rocket, Zap } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import StlViewer from "../components/StlViewer";

import { API } from "../lib/api";

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
  { id: "live", label: "Live", icon: Activity },
  { id: "results", label: "Results", icon: BarChart3 },
  { id: "video", label: "Video", icon: Film },
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
  const [fps, setFps] = useState(10);

  // Live monitor state
  const [liveLog, setLiveLog] = useState("");
  const [liveConnected, setLiveConnected] = useState(false);
  const [forceHistory, setForceHistory] = useState<Array<{step: number; Fx: number; Fy: number; Fz: number}>>([]);
  const [mlups, setMlups] = useState(0);
  const [stepsCompleted, setStepsCompleted] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);

  const connectWS = useCallback(() => {
    if (wsRef.current) { wsRef.current.close(); }
    const ws = new WebSocket(`ws://127.0.0.1:10944/api/v1/fluidx3d/ws/${encodeURIComponent(caseName)}`);
    ws.onopen = () => setLiveConnected(true);
    ws.onmessage = (e) => {
      const text = e.data;
      if (text === "__SIMULATION_COMPLETE__") { setLiveConnected(false); return; }
      setLiveLog((prev) => (prev + text).slice(-50000));
      const lines = text.split("\n");
      for (const line of lines) {
        const m = line.match(/STEP\s+(\d+)\s+F\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)/);
        if (m) {
          setForceHistory((prev) => [...prev.slice(-500), { step: parseInt(m[1]), Fx: parseFloat(m[2]), Fy: parseFloat(m[3]), Fz: parseFloat(m[4]) }]);
        }
        const d = line.match(/DONE\s+steps:(\d+)\s+time:[\d.]+\s+mlups:([\d.]+)/);
        if (d) {
          setStepsCompleted(parseInt(d[1]));
          setMlups(parseFloat(d[2]));
        }
      }
    };
    ws.onclose = () => setLiveConnected(false);
    ws.onerror = () => setLiveConnected(false);
    wsRef.current = ws;
  }, [caseName]);

  useEffect(() => {
    fetchStatus();
    return () => { if (wsRef.current) wsRef.current.close(); };
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

            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
              <p className="text-sm font-medium text-amber-300 mb-2">OpenFOAM vs FluidX3D — When to Use Which?</p>
              <p className="text-xs text-slate-400 mb-2">Both are available in this server. OpenFOAM runs on CPU inside Docker (GPU is idle). FluidX3D runs on GPU via OpenCL.</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2 bg-black/20 rounded-lg">
                  <p className="text-amber-400 font-bold mb-1">Pick OpenFOAM when:</p>
                  <ul className="text-slate-500 space-y-0.5">
                    <li>• Complex geometry (not a simple channel/pipe)</li>
                    <li>• Need kEpsilon, kOmegaSST, LES turbulence models</li>
                    <li>• Multiphase (VOF) or heat transfer</li>
                    <li>• Industry-standard validation required</li>
                    <li>• You already have Docker set up</li>
                  </ul>
                </div>
                <div className="p-2 bg-black/20 rounded-lg">
                  <p className="text-emerald-400 font-bold mb-1">Pick FluidX3D when:</p>
                  <ul className="text-slate-500 space-y-0.5">
                    <li>• Geometry fits a Cartesian grid</li>
                    <li>• Fast iteration / design exploration</li>
                    <li>• You have a GPU (RTX 4090, AMD, Apple Silicon)</li>
                    <li>• Millisecond-per-timestep throughput</li>
                    <li>• Want automatic video/streamline output</li>
                  </ul>
                </div>
              </div>
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
              {field("Resolution X", input(resX, (v) => setResX(Number(v)), { min: 16, step: 64 }))}
              {field("Resolution Y", input(resY, (v) => setResY(Number(v)), { min: 16, step: 32 }))}
              {field("Resolution Z", input(resZ, (v) => setResZ(Number(v)), { min: 16, step: 32 }))}
              <div className="col-span-2 flex items-center gap-2 text-xs text-slate-500">
                <Cpu size={12} />
                Total cells: {(resX * resY * resZ).toLocaleString()} | ~{((resX * resY * resZ * 55) / 1e9).toFixed(2)} GB VRAM (FP32) | ~{((resX * resY * resZ * 55) / 2 / 1e9).toFixed(2)} GB (FP16)
              </div>
              {field("Length (m)", input(lengthM, (v) => setLengthM(Number(v)), { step: 0.1 }))}
              {field("Velocity (m/s)", input(velocityMs, (v) => setVelocityMs(Number(v)), { step: 0.001 }))}
              {field("Viscosity (m²/s)", input(viscosity, setViscosity))}
              {field("Density (kg/m³)", input(density, (v) => setDensity(Number(v))))}
              {field("Time Steps", input(timeSteps, (v) => setTimeSteps(Number(v)), { step: 10000 }))}
              {field("Write Interval", input(writeInterval, (v) => setWriteInterval(Number(v)), { step: 100 }))}
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
              <div className="space-y-4">
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl space-y-1">
                  <p className="text-sm text-emerald-300">Setup generated</p>
                  <p className="text-xs text-slate-400">
                    Re ≈ {String(result.data.Re_estimate)} | {String(result.data.resolution)} | {String(result.data.cells)} cells
                  </p>
                  <p className="text-xs text-slate-500 font-mono">{String(result.data.setup_file)}</p>
                </div>
                {!!result.data.stl_file_name && (
                  <StlViewer
                    url={`/api/v1/case-files/${caseName}/${result.data.stl_file_name}`}
                    height={400}
                  />
                )}
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
                {!!result.data.warnings && <p className="text-xs text-amber-400 mt-1">{String(result.data.warnings).slice(0, 500)}</p>}
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
              {field("GPU Device Index", input(gpuDevice, (v) => setGpuDevice(Number(v)), { min: 0 }))}
              {field("Timeout (s)", input(timeoutS, (v) => setTimeoutS(Number(v)), { min: 10, step: 60 }))}
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
                {!!result.data.output && (
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

        {/* Live Monitor */}
        {activeTab === "live" && (
          <div className="space-y-4 max-w-4xl">
            <h2 className="text-lg font-bold text-slate-200">Live Monitor</h2>
            <div className="flex items-end gap-3">
              {field("Case Name", input(caseName, (v) => setCaseName(v)))}
              {field("GPU Device", input(gpuDevice, (v) => setGpuDevice(Number(v)), { min: 0 }))}
              {field("Timeout (s)", input(timeoutS, (v) => setTimeoutS(Number(v)), { min: 10, step: 60 }))}
            </div>
            <div className="flex gap-2">
              {btn("Start & Connect", async () => {
                callTool("cfd_fluidx3d_run", { case_name: caseName, gpu_device: Number(gpuDevice), timeout_s: Number(timeoutS) });
                connectWS();
              }, <Play size={14} />)}
              {btn("Connect Only", connectWS, <RefreshCw size={14} />)}
            </div>
            {liveConnected && <span className="text-xs text-emerald-400">Connected</span>}
            <div className="grid grid-cols-2 gap-4">
              {forceHistory.length > 0 && (
                <div className="bg-white/5 rounded-xl p-4 border border-white/10" style={{ height: 250 }}>
                  <p className="text-xs text-slate-500 mb-2">Force History</p>
                  <ResponsiveContainer width="100%" height="85%">
                    <LineChart data={forceHistory.map((f: {step: number; Fx: number; Fy: number; Fz: number}, i: number) => ({...f, idx: i}))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                      <XAxis dataKey="step" stroke="#ffffff40" tick={{fontSize: 10}} />
                      <YAxis stroke="#ffffff40" tick={{fontSize: 10}} />
                      <Tooltip contentStyle={{backgroundColor: '#1e1e2e', border: '1px solid #ffffff20', borderRadius: 8, fontSize: 12}} />
                      <Line type="monotone" dataKey="Fx" stroke="#10b981" dot={false} name="Fx" />
                      <Line type="monotone" dataKey="Fy" stroke="#f59e0b" dot={false} name="Fy" />
                      <Line type="monotone" dataKey="Fz" stroke="#6366f1" dot={false} name="Fz" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
              <div className="space-y-2">
                {mlups > 0 && (
                  <div className="p-3 bg-emerald-500/10 rounded-xl border border-emerald-500/20 text-center">
                    <p className="text-xs text-slate-500">MLUPS</p>
                    <p className="text-2xl font-bold text-emerald-400">{mlups.toFixed(1)}</p>
                  </div>
                )}
                {stepsCompleted > 0 && (
                  <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20 text-center">
                    <p className="text-xs text-slate-500">Steps</p>
                    <p className="text-2xl font-bold text-indigo-400">{stepsCompleted.toLocaleString()}</p>
                  </div>
                )}
              </div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/5">
              <p className="text-xs text-slate-500 mb-2">Simulation Log</p>
              <pre className="text-xs font-mono text-slate-400 max-h-60 overflow-y-auto whitespace-pre-wrap">{liveLog}</pre>
            </div>
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

                {!!result.data.final_forces && (
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

        {/* Video */}
        {activeTab === "video" && (
          <div className="space-y-4 max-w-3xl">
            <h2 className="text-lg font-bold text-slate-200">Simulation Video</h2>
            {field("Case Name", input(caseName, (v) => setCaseName(v)))}
            {field("FPS", input(fps, (v) => setFps(Number(v)), { min: 1, max: 30, step: 1 }))}
            {btn("Render Video", () => callTool("cfd_fluidx3d_render", { case_name: caseName, fps: Number(fps) }), <Film size={14} />)}
            {loading && <Loader2 className="animate-spin text-amber-400" size={24} />}
            {result?.data && (
              <div className="space-y-4">
                {!!result.data.video_path && (
                  <video controls autoPlay loop className="w-full rounded-xl border border-white/10 bg-black/40" style={{ maxHeight: "500px" }}>
                    <source src={`/api/v1/case-files/${encodeURIComponent(caseName)}/${encodeURIComponent(caseName)}_simulation.webm`} type="video/webm" />
                  </video>
                )}
                {!result.data.video_path && !!result.data.png_path && (
                  <img
                    src={`/api/v1/case-files/${encodeURIComponent(caseName)}/${encodeURIComponent(caseName)}_result.png`}
                    alt="Simulation result"
                    className="w-full rounded-xl border border-white/10"
                  />
                )}
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-3 bg-slate-800/50 rounded-xl text-center">
                    <p className="text-xs text-slate-500">Frames</p>
                    <p className="text-lg font-mono text-cyan-400">{String(result.data.frame_count)}</p>
                  </div>
                  <div className="p-3 bg-slate-800/50 rounded-xl text-center">
                    <p className="text-xs text-slate-500">Duration</p>
                    <p className="text-lg font-mono text-cyan-400">{String(result.data.duration_s)}s</p>
                  </div>
                  <div className="p-3 bg-slate-800/50 rounded-xl text-center">
                    <p className="text-xs text-slate-500">VTK Files</p>
                    <p className="text-lg font-mono text-cyan-400">{String(result.data.vtk_files)}</p>
                  </div>
                </div>
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
