import { useState } from "react";
import { ArrowLeftRight, Building2, Columns, DoorOpen, Home, LandPlot, Loader2, Wand2 } from "lucide-react";
import { API_BASE } from "../lib/api";

interface FieldDef {
  key: string;
  label: string;
  type: "number" | "select" | "text";
  defaultValue: string | number;
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
  hint?: string;
}

interface ToolDef {
  tool: string;
  label: string;
  icon: typeof Home;
  fields: FieldDef[];
}

const tools: ToolDef[] = [
  {
    tool: "bim_create_wall",
    label: "Wall",
    icon: Home,
    fields: [
      { key: "length_mm", label: "Length (mm)", type: "number", defaultValue: 5000, min: 1 },
      { key: "width_mm", label: "Thickness (mm)", type: "number", defaultValue: 200, min: 10 },
      { key: "height_mm", label: "Height (mm)", type: "number", defaultValue: 2800, min: 10 },
      { key: "placement_x", label: "X (mm)", type: "number", defaultValue: 0 },
      { key: "placement_y", label: "Y (mm)", type: "number", defaultValue: 0 },
      { key: "placement_z", label: "Z (mm)", type: "number", defaultValue: 0 },
      { key: "rotation_z", label: "Rotation Z (°)", type: "number", defaultValue: 0 },
      { key: "output_name", label: "Filename", type: "text", defaultValue: "wall.fcstd" },
    ],
  },
  {
    tool: "bim_create_slab",
    label: "Slab",
    icon: LandPlot,
    fields: [
      { key: "width_mm", label: "Width (mm)", type: "number", defaultValue: 6000, min: 100 },
      { key: "length_mm", label: "Length (mm)", type: "number", defaultValue: 8000, min: 100 },
      { key: "thickness_mm", label: "Thickness (mm)", type: "number", defaultValue: 200, min: 20 },
      { key: "placement_x", label: "X (mm)", type: "number", defaultValue: 0 },
      { key: "placement_y", label: "Y (mm)", type: "number", defaultValue: 0 },
      { key: "placement_z", label: "Z (mm)", type: "number", defaultValue: 0 },
      { key: "output_name", label: "Filename", type: "text", defaultValue: "slab.fcstd" },
    ],
  },
  {
    tool: "bim_create_column",
    label: "Column",
    icon: Columns,
    fields: [
      { key: "profile_type", label: "Profile", type: "select", defaultValue: "rectangular", options: ["rectangular", "circular", "h_section"] },
      { key: "width_mm", label: "Width (mm)", type: "number", defaultValue: 300, min: 10 },
      { key: "depth_mm", label: "Depth (mm)", type: "number", defaultValue: 300, min: 10 },
      { key: "height_mm", label: "Height (mm)", type: "number", defaultValue: 3000, min: 10 },
      { key: "placement_x", label: "X (mm)", type: "number", defaultValue: 0 },
      { key: "placement_y", label: "Y (mm)", type: "number", defaultValue: 0 },
      { key: "placement_z", label: "Z (mm)", type: "number", defaultValue: 0 },
      { key: "output_name", label: "Filename", type: "text", defaultValue: "column.fcstd" },
    ],
  },
  {
    tool: "bim_create_window",
    label: "Window",
    icon: Wand2,
    fields: [
      { key: "window_type", label: "Type", type: "select", defaultValue: "fixed", options: ["fixed", "casement", "sliding", "awning"] },
      { key: "width_mm", label: "Width (mm)", type: "number", defaultValue: 1000, min: 200 },
      { key: "height_mm", label: "Height (mm)", type: "number", defaultValue: 1200, min: 200 },
      { key: "sill_height_mm", label: "Sill Height (mm)", type: "number", defaultValue: 900, min: 0 },
      { key: "placement_x", label: "X (mm)", type: "number", defaultValue: 0 },
      { key: "placement_y", label: "Y (mm)", type: "number", defaultValue: 0 },
      { key: "placement_z", label: "Z (mm)", type: "number", defaultValue: 0 },
      { key: "rotation_z", label: "Rotation Z (°)", type: "number", defaultValue: 0 },
      { key: "output_name", label: "Filename", type: "text", defaultValue: "window.fcstd" },
    ],
  },
  {
    tool: "bim_create_door",
    label: "Door",
    icon: DoorOpen,
    fields: [
      { key: "door_type", label: "Type", type: "select", defaultValue: "simple", options: ["simple", "glass", "sliding_glass"] },
      { key: "width_mm", label: "Width (mm)", type: "number", defaultValue: 900, min: 400 },
      { key: "height_mm", label: "Height (mm)", type: "number", defaultValue: 2100, min: 1500 },
      { key: "placement_x", label: "X (mm)", type: "number", defaultValue: 0 },
      { key: "placement_y", label: "Y (mm)", type: "number", defaultValue: 0 },
      { key: "placement_z", label: "Z (mm)", type: "number", defaultValue: 0 },
      { key: "rotation_z", label: "Rotation Z (°)", type: "number", defaultValue: 0 },
      { key: "output_name", label: "Filename", type: "text", defaultValue: "door.fcstd" },
    ],
  },
  {
    tool: "bim_create_roof",
    label: "Roof",
    icon: Building2,
    fields: [
      { key: "width_mm", label: "Width (mm)", type: "number", defaultValue: 8000, min: 100 },
      { key: "length_mm", label: "Length (mm)", type: "number", defaultValue: 10000, min: 100 },
      { key: "angle_deg", label: "Pitch Angle (°)", type: "number", defaultValue: 30, min: 0, max: 75 },
      { key: "thickness_mm", label: "Thickness (mm)", type: "number", defaultValue: 100, min: 10 },
      { key: "placement_x", label: "X (mm)", type: "number", defaultValue: 0 },
      { key: "placement_y", label: "Y (mm)", type: "number", defaultValue: 0 },
      { key: "placement_z", label: "Z (mm)", type: "number", defaultValue: 2800 },
      { key: "output_name", label: "Filename", type: "text", defaultValue: "roof.fcstd" },
    ],
  },
  {
    tool: "bim_export_ifc",
    label: "Export IFC",
    icon: ArrowLeftRight,
    fields: [
      { key: "file_name", label: "Source .fcstd", type: "text", defaultValue: "wall.fcstd", hint: "Must exist in uploads or outputs" },
      { key: "output_name", label: "Output .ifc", type: "text", defaultValue: "building.ifc" },
    ],
  },
  {
    tool: "bim_import_ifc",
    label: "Import IFC",
    icon: ArrowLeftRight,
    fields: [
      { key: "file_name", label: "Source .ifc", type: "text", defaultValue: "building.ifc", hint: "Must exist in uploads" },
      { key: "output_name", label: "Output .fcstd", type: "text", defaultValue: "", hint: "Auto from stem if empty" },
    ],
  },
];

const inputCls =
  "w-full bg-[#0a0a0c] border border-white/5 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-indigo-500/30 font-mono";

export default function BimDemoPage() {
  const [tabIdx, setTabIdx] = useState(0);
  const [values, setValues] = useState<Record<string, Record<string, string>>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const active = tools[tabIdx];

  function getVal(key: string): string {
    const field = active.fields.find((f) => f.key === key);
    const stored = values[active.tool]?.[key];
    if (stored !== undefined) return stored;
    return String(field?.defaultValue ?? "");
  }

  function setVal(key: string, v: string) {
    setValues((prev) => ({
      ...prev,
      [active.tool]: { ...(prev[active.tool] || {}), [key]: v },
    }));
  }

  async function handleCreate() {
    setLoading(true);
    setResult(null);
    setError("");

    const args: Record<string, unknown> = {};
    for (const f of active.fields) {
      const raw = getVal(f.key);
      if (f.type === "number") {
        const n = parseFloat(raw);
        args[f.key] = Number.isNaN(n) ? f.defaultValue : n;
      } else {
        args[f.key] = raw || String(f.defaultValue);
      }
    }

    try {
      const r = await fetch(API_BASE + "/api/v1/control/tool", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool: active.tool, arguments: args }),
      });
      const j = await r.json();
      if (!r.ok || !j.success) {
        setError(j.error || j.detail || `HTTP ${r.status}`);
      } else {
        setResult(j);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  const outputName = result ? (result.output as string) || "" : "";

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Wand2 className="text-indigo-400" /> BIM Demo
        </h1>
        <span className="text-xs text-slate-500">FreeCAD Arch workbench</span>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-1 p-1 bg-white/5 rounded-xl">
        {tools.map((t, i) => (
          <button
            key={t.tool}
            onClick={() => {
              setTabIdx(i);
              setResult(null);
              setError("");
            }}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${
              i === tabIdx ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            <t.icon size={13} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Form */}
      <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-6 space-y-4">
        <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
          <active.icon size={16} className="text-indigo-400" />
          {active.label} Parameters
        </h2>

        <div className="grid grid-cols-2 gap-3">
          {active.fields.map((f) => (
            <div key={f.key} className={f.key === "output_name" || f.key === "file_name" ? "col-span-2" : ""}>
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                {f.label}
                {f.hint && <span className="text-slate-600 ml-1 font-normal normal-case">— {f.hint}</span>}
              </label>
              {f.type === "select" ? (
                <select value={getVal(f.key)} onChange={(e) => setVal(f.key, e.target.value)} className={inputCls}>
                  {f.options?.map((o) => (
                    <option key={o} value={o}>
                      {o.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={f.type}
                  value={getVal(f.key)}
                  onChange={(e) => setVal(f.key, e.target.value)}
                  min={f.min}
                  max={f.max}
                  step={f.step ?? (f.type === "number" ? 10 : undefined)}
                  className={inputCls}
                />
              )}
            </div>
          ))}
        </div>

        <button
          onClick={handleCreate}
          disabled={loading}
          className="w-full px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-bold text-sm flex items-center justify-center gap-2 transition-all"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
          {loading ? "Creating..." : `Create ${active.label}`}
        </button>

        {error && (
          <div className="bg-red-950/40 border border-red-500/20 rounded-xl p-4">
            <p className="text-red-400 text-sm font-bold">Error</p>
            <p className="text-red-300/80 text-xs mt-1 font-mono">{error}</p>
          </div>
        )}

        {result && (
          <div className="bg-emerald-950/30 border border-emerald-500/20 rounded-xl p-4 space-y-3">
            <p className="text-emerald-400 text-sm font-bold">Created Successfully</p>

            <div className="grid grid-cols-2 gap-2 text-xs">
              {result.data && typeof result.data === "object"
                ? Object.entries(result.data as Record<string, unknown>)
                    .filter(([k]) => k !== "path")
                    .map(([k, v]) => (
                      <div key={k} className="bg-white/5 rounded-lg p-2">
                        <span className="text-slate-500">{k}</span>
                        <span className="text-slate-200 ml-2 font-mono">{typeof v === "number" ? v.toLocaleString() : typeof v === "string" ? v : JSON.stringify(v)}</span>
                      </div>
                    ))
                : null}
            </div>

            {outputName && (
              <a
                href={`/api/v1/download/${outputName}`}
                className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-bold"
              >
                Download {outputName} &#8599;
              </a>
            )}

            <details className="text-xs">
              <summary className="text-slate-500 cursor-pointer hover:text-slate-400">Raw response</summary>
              <pre className="mt-2 bg-black/30 rounded-lg p-3 text-slate-400 overflow-x-auto font-mono text-[11px]">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>

      {/* Quick start */}
      <div className="bg-indigo-500/5 border border-indigo-500/10 rounded-2xl p-6">
        <h3 className="text-sm font-bold text-indigo-300 mb-2">Quick Start</h3>
        <div className="text-xs text-slate-500 space-y-1">
          <p>1. Pick an element type from the tabs above</p>
          <p>2. Adjust parameters or keep the defaults</p>
          <p>3. Click Create — the resulting .fcstd saves to the outputs directory</p>
          <p>4. Chain tools: create walls, then export the whole document to IFC</p>
          <p className="mt-2 text-indigo-400/70">
            Tip: Use <strong>bim_export_ifc</strong> to export any .fcstd to .ifc for sharing with architects.
          </p>
        </div>
      </div>
    </div>
  );
}
