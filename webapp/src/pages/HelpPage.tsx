import { useState } from "react";
import { BookOpen, Cpu, Code2, ExternalLink, HelpCircle, Package, Printer, ShoppingBag, Wrench, Layers, History, GitCompare, Waves, Film } from "lucide-react";

const sections = [
  { id: "intro", label: "FreeCAD", icon: BookOpen },
  { id: "history", label: "History", icon: History },
  { id: "scripting", label: "Scripting", icon: Code2 },
  { id: "workbenches", label: "Workbenches", icon: Layers },
  { id: "comparison", label: "vs Pro CAD", icon: GitCompare },
  { id: "tools", label: "MCP Tools", icon: Wrench },
  { id: "cfd", label: "CFD", icon: Waves },
  { id: "openfoam", label: "OpenFOAM", icon: Cpu },
  { id: "visualization", label: "Visualization", icon: Film },
  { id: "marketplace", label: "Marketplace", icon: ShoppingBag },
  { id: "printing", label: "3D Printing", icon: Printer },
  { id: "links", label: "Links", icon: ExternalLink },
];

export default function HelpPage() {
  const [tab, setTab] = useState("intro");
  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3"><HelpCircle className="text-indigo-400" /> Help &amp; Reference</h1>

      <div className="flex flex-wrap gap-1.5 p-1 bg-white/5 rounded-2xl">
        {sections.map((s) => (
          <button key={s.id} onClick={() => setTab(s.id)} className={`px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition-all ${tab === s.id ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20" : "text-slate-500 hover:text-slate-300"}`}>
            <s.icon size={13} className="inline mr-1.5" />{s.label}
          </button>
        ))}
      </div>

      <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-6 text-sm text-slate-400 leading-relaxed space-y-4">

        {tab === "intro" && <Intro />}
        {tab === "history" && <HistorySection />}
        {tab === "scripting" && <Scripting />}
        {tab === "workbenches" && <Workbenches />}
        {tab === "comparison" && <Comparison />}
        {tab === "tools" && <Tools />}
        {tab === "cfd" && <CfdHelp />}
        {tab === "openfoam" && <OpenfoamHelp />}
        {tab === "marketplace" && <MarketplaceHelp />}
        {tab === "printing" && <Printing />}
        {tab === "visualization" && <Visualization />}
        {tab === "links" && <Links />}
      </div>
    </div>
  );
}

function Intro() {
  return (
    <>
      <p><strong className="text-slate-200">FreeCAD</strong> is a free, open-source parametric 3D CAD modeler (LGPL). It uses the <strong className="text-slate-200">OpenCASCADE (OCCT)</strong> geometry kernel — the same technology behind CATIA and Salome.</p>
      <p>FreeCAD is <strong className="text-slate-200">not</strong> a mesh modeler like Blender. It creates precise solid models (B-Rep) with a parametric feature tree. Changes to early features propagate through the entire model. Think of it as "programmable SolidWorks."</p>
      <p>The fleet runs <strong className="text-slate-200">FreeCAD 1.1.1</strong> as the backend for freecad-mcp. All CAD operations — STEP conversion, model inspection, geometry creation — go through FreeCAD's Python API via a TCP bridge or subprocess.</p>
      <p className="text-slate-500 italic">FreeCAD 1.0 (2024) was the "production ready" milestone. 1.1 added improved STEP AP214 support and the Ondsel merger.</p>
    </>
  );
}

function HistorySection() {
  return (
    <>
      <div className="space-y-2">
        {[
          ["2002", "Jürgen Riegel starts FreeCAD as a Qt/OpenCASCADE project"],
          ["2007", "First public release (0.1)"],
          ["2012", "Part Design workbench, Sketcher constraint solver"],
          ["2015", "Assembly2 workbench, Path/CAM workbench debut"],
          ["2018", "Qt5 port, TechDraw technical drawing workbench"],
          ["2022", "Topological naming fix pioneered (realthunder's LinkStage3 fork)"],
          ["2024", "FreeCAD 1.0 — declared 'production ready'"],
          ["2025", "FreeCAD 1.1 — improved AP214 STEP, Ondsel merger"],
        ].map(([year, text]) => (
          <div key={year} className="flex gap-3">
            <span className="text-indigo-400 font-bold text-xs shrink-0 w-12">{year}</span>
            <span>{text}</span>
          </div>
        ))}
      </div>
      <p>Community: <strong className="text-slate-200">150+ core contributors</strong>, 70k+ GitHub stars, ~2M downloads per release. The <a href="https://forum.freecad.org" target="_blank" className="text-indigo-400 hover:underline">forum</a> has 300k+ posts.</p>
    </>
  );
}

function Scripting() {
  return (
    <>
      <p><strong className="text-slate-200">FreeCAD's entire API is Python.</strong> The console is a live REPL into the OCCT kernel. Every GUI operation has a Python equivalent.</p>
      <div className="bg-black/30 rounded-xl p-4 font-mono text-xs space-y-1 overflow-x-auto">
        <div><span className="text-slate-500">import</span> <span className="text-emerald-400">Part</span>, <span className="text-emerald-400">Mesh</span></div>
        <div className="text-slate-600"># Create base plate + mounting boss + hole</div>
        <div>base = Part.makeBox(<span className="text-amber-400">50</span>, <span className="text-amber-400">40</span>, <span className="text-amber-400">5</span>)</div>
        <div>boss = Part.makeCylinder(<span className="text-amber-400">5</span>, <span className="text-amber-400">15</span>, Part.Vector(<span className="text-amber-400">10</span>, <span className="text-amber-400">10</span>, <span className="text-amber-400">5</span>))</div>
        <div>hole = Part.makeCylinder(<span className="text-amber-400">3</span>, <span className="text-amber-400">15</span>, Part.Vector(<span className="text-amber-400">10</span>, <span className="text-amber-400">10</span>, <span className="text-amber-400">5</span>))</div>
        <div>bracket = base.fuse(boss).cut(hole)</div>
        <div>Mesh.Mesh(bracket).write(<span className="text-green-400">"bracket.stl"</span>)</div>
      </div>
      <p><strong className="text-slate-200">Core modules:</strong> <code className="text-indigo-400">FreeCAD</code> (app), <code className="text-indigo-400">Part</code> (topology), <code className="text-indigo-400">Mesh</code> (STL), <code className="text-indigo-400">Sketcher</code> (2D constraints), <code className="text-indigo-400">Fem</code> (FEA), <code className="text-indigo-400">Path</code> (CAM), <code className="text-indigo-400">TechDraw</code> (drawings), <code className="text-indigo-400">Import</code> (STEP/IGES).</p>
      <p>FreeCAD can run <strong className="text-slate-200">headless</strong> via <code className="text-indigo-400">FreeCADCmd.exe</code> — that's how the MCP server's subprocess fallback works. It pipes Python scripts to stdin and parses JSON from stdout.</p>
    </>
  );
}

function Workbenches() {
  return (
    <>
      <p>Workbenches are FreeCAD's plugin system — <strong className="text-slate-200">300+ available</strong> in the Addon Manager. Each adds domain-specific tools and UI.</p>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Built-in (shipped with FreeCAD)</h3>
      <div className="grid grid-cols-2 gap-2">
        {[
          ["Part", "CSG primitives, booleans, sweeps, lofts"],
          ["Part Design", "Parametric feature tree: pad, pocket, fillet"],
          ["Sketcher", "2D constraint solver with 20+ constraint types"],
          ["Draft", "2D CAD with snap-to-grid and dimensions"],
          ["Mesh", "STL/OBJ import, repair, analysis, decimation"],
          ["TechDraw", "Engineering drawing sheets with GD&amp;T"],
          ["FEM", "Finite element analysis (CalculiX solver)"],
          ["Path", "CAM/CNC toolpaths for milling, drilling, lathe"],
          ["BIM", "Building Information Modeling (IFC, walls, slabs)"],
          ["Spreadsheet", "Parametric tables driving model dimensions"],
          ["Robot", "6-axis robot kinematics (KUKA, ABB)"],
          ["Assembly", "Joint-based assembly constraints (new in 1.0)"],
        ].map(([name, desc]) => (
          <div key={name} className="bg-white/5 rounded-lg p-2.5">
            <span className="text-indigo-400 font-bold text-xs">{name}</span>
            <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
          </div>
        ))}
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Popular Community Workbenches</h3>
      <div className="grid grid-cols-2 gap-2">
        {[
          ["Fasteners", "ISO/DIN screws, nuts, washers, threaded inserts"],
          ["SheetMetal", "Sheet metal unfolding with bend tables"],
          ["Gears", "Involute gears, sprockets, timing belt pulleys"],
          ["A2plus", "Assembly with kinematic constraint solver"],
          ["Curves", "Freeform NURBS curves and surfaces"],
          ["Assembly4", "LCS-based parametric assembly with variables"],
          ["Rocket", "Model rocket design with CP/CG stability analysis"],
          ["CfdOF", "OpenFOAM CFD integration for fluid simulation"],
          ["KiCadStepUp", "PCB ↔ FreeCAD bridge for enclosure design"],
          ["LCInterlocking", "Laser-cut interlocking part generator"],
        ].map(([name, desc]) => (
          <div key={name} className="bg-white/5 rounded-lg p-2.5">
            <span className="text-emerald-400 font-bold text-xs">{name}</span>
            <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
          </div>
        ))}
      </div>
    </>
  );
}

function Comparison() {
  return (
    <>
      <p className="text-slate-500 italic">How FreeCAD stacks up against the commercial CAD giants.</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-200 border-b border-white/10">
              <th className="text-left py-2 pr-4">Aspect</th>
              <th className="text-left py-2 px-3 bg-indigo-500/10 rounded-t-lg">FreeCAD</th>
              <th className="text-left py-2 px-3">SolidWorks</th>
              <th className="text-left py-2 px-3">Fusion 360</th>
              <th className="text-left py-2 px-3">AutoCAD</th>
            </tr>
          </thead>
          <tbody className="text-slate-400">
            {[
              ["License", "Free (LGPL)", "$4,000+/yr", "$680/yr", "$2,000+/yr"],
              ["Parametric", "Full (Sketcher)", "Full", "Full", "Limited"],
              ["Assembly", "New in 1.0", "Mature", "Mature", "N/A"],
              ["FEM", "Built-in (CalculiX)", "Simulation add-on", "Cloud-based", "None"],
              ["CAM", "Built-in (Path)", "CAMWorks add-on", "Built-in", "None"],
              ["Python API", "Full — everything", "VBA macros only", "Limited add-in", "AutoLISP"],
              ["STEP Support", "Good (AP214 in 1.1)", "Excellent", "Good", "Limited"],
              ["File Format", "FCStd (open ZIP+B-Rep)", "SLDPRT (proprietary)", "F3D (proprietary)", "DWG (proprietary)"],
              ["Cloud", "Self-hosted", "3DEXPERIENCE", "Forced cloud", "BIM 360"],
              ["Learning Curve", "Moderate", "Steep", "Gentle", "Steep"],
            ].map(([aspect, fc, sw, fusion, autocad]) => (
              <tr key={aspect} className="border-b border-white/5 hover:bg-white/[0.02]">
                <td className="py-2 pr-4 font-bold text-slate-300">{aspect}</td>
                <td className="py-2 px-3 bg-indigo-500/5 text-indigo-300">{fc}</td>
                <td className="py-2 px-3">{sw}</td>
                <td className="py-2 px-3">{fusion}</td>
                <td className="py-2 px-3">{autocad}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p><strong className="text-indigo-400">FreeCAD wins</strong> when you need scriptable CAD pipelines (that's why this MCP server exists), zero budget, no vendor lock-in, or built-in FEM/CAM without add-ons.</p>
      <p><strong className="text-slate-500">Pro CAD wins</strong> for 1000+ part assemblies, certified simulation, PLM integration, or collaborative multi-user editing.</p>
    </>
  );
}

function Tools() {
  return (
    <>
      <p><strong className="text-slate-200">32 MCP tools</strong> registered in the server. Available via MCP SSE and the REST proxy. All files are stored in a persistent depot at <code className="text-indigo-400">%LOCALAPPDATA%\freecad-mcp\depot</code> with full CRUD via the Depot page and REST API.</p>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">CAD Depot</h3>
      <div className="space-y-2">
        {[
          { name: "cad_depot", tag: "READ", desc: "List all files in the persistent CAD file depot with metadata (size, created date, description, tags, shape type). Supports STEP, STL, IFC, FCStd, IGES, OBJ, and DXF." },
          { name: "cad_create", tag: "MUTATE", desc: "Create a box/cylinder/sphere/cone shape, save the resulting STL directly to the depot with metadata. All dimensions in mm." },
        ].map((t) => (
          <div key={t.name} className="bg-white/5 rounded-xl p-3 flex items-start gap-3">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${t.tag === "READ" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"}`}>{t.tag}</span>
            <div>
              <code className="text-indigo-400 font-bold">{t.name}()</code>
              <p className="text-xs text-slate-500 mt-0.5">{t.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <p className="text-slate-500 text-xs mt-2">Depot CRUD via REST: <code className="text-indigo-400">GET/PUT/DELETE /api/v1/depot/{'{name}'}</code>, <code className="text-indigo-400">POST /api/v1/depot/create</code>, <code className="text-indigo-400">POST /api/v1/depot/upload</code></p>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Core CAD</h3>
      <div className="space-y-2">
        {[
          { name: "freecad_status", tag: "READ", desc: "FreeCAD availability + version. Call this first." },
          { name: "step_to_stl", tag: "MUTATE", desc: "Convert STEP/STP assembly → STL mesh. Uses TCP bridge for AP214." },
          { name: "model_info", tag: "READ", desc: "Object count, solids, volume, bounding box. Works on STEP + STL." },
          { name: "create_shape", tag: "MUTATE", desc: "Box, cylinder, sphere, cone → STL. All dimensions in mm." },
          { name: "freecad_gui", tag: "MUTATE", desc: "Launch FreeCAD desktop app, optionally opening a file." },
        ].map((t) => (
          <div key={t.name} className="bg-white/5 rounded-xl p-3 flex items-start gap-3">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${t.tag === "READ" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"}`}>{t.tag}</span>
            <div>
              <code className="text-indigo-400 font-bold">{t.name}()</code>
              <p className="text-xs text-slate-500 mt-0.5">{t.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Slicing (3D Printing)</h3>
      <div className="space-y-2">
        {[
          { name: "slicer_status", tag: "READ", desc: "PrusaSlicer availability + version check." },
          { name: "slice_stl", tag: "MUTATE", desc: "Slice STL → G-code. Configurable printer/filament/quality." },
        ].map((t) => (
          <div key={t.name} className="bg-white/5 rounded-xl p-3 flex items-start gap-3">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${t.tag === "READ" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"}`}>{t.tag}</span>
            <div>
              <code className="text-indigo-400 font-bold">{t.name}()</code>
              <p className="text-xs text-slate-500 mt-0.5">{t.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">BIM / Architecture (Arch workbench)</h3>
      <div className="space-y-2">
        {[
          { name: "bim_status", tag: "READ", desc: "BIM/Arch workbench availability check." },
          { name: "bim_create_wall", tag: "MUTATE", desc: "Parametric architectural wall → .fcstd document." },
          { name: "bim_create_slab", tag: "MUTATE", desc: "Floor slab (structural element) → .fcstd document." },
          { name: "bim_create_column", tag: "MUTATE", desc: "Column (rectangular, circular, H-section) → .fcstd." },
          { name: "bim_create_window", tag: "MUTATE", desc: "Window hosted in auto-generated wall → .fcstd." },
          { name: "bim_create_door", tag: "MUTATE", desc: "Door hosted in auto-generated wall → .fcstd." },
          { name: "bim_create_roof", tag: "MUTATE", desc: "Sloped or flat roof → .fcstd document." },
          { name: "bim_export_ifc", tag: "MUTATE", desc: "Export .fcstd → .ifc (Industry Foundation Classes, open BIM standard)." },
          { name: "bim_import_ifc", tag: "MUTATE", desc: "Import .ifc file from architects → .fcstd document." },
        ].map((t) => (
          <div key={t.name} className="bg-white/5 rounded-xl p-3 flex items-start gap-3">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${t.tag === "READ" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"}`}>{t.tag}</span>
            <div>
              <code className="text-indigo-400 font-bold">{t.name}()</code>
              <p className="text-xs text-slate-500 mt-0.5">{t.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">CFD / OpenFOAM</h3>
      <div className="space-y-2">
        {[
          { name: "cfd_status", tag: "READ", desc: "Check Docker, OpenFOAM image, and FreeCAD bridge availability." },
          { name: "cfd_create_domain", tag: "MUTATE", desc: "Parametric fluid domain (channel, pipe, nozzle) → STEP + OpenFOAM blockMeshDict." },
          { name: "cfd_configure_physics", tag: "MUTATE", desc: "Generate all OpenFOAM dictionaries: solver, turbulence model, fluid properties." },
          { name: "cfd_set_boundary", tag: "MUTATE", desc: "Configure per-patch BC files (U, p, k, omega, nut) with 14 BC types." },
          { name: "cfd_build_case", tag: "READ", desc: "Validate OpenFOAM case completeness. Lists missing files." },
          { name: "cfd_run_solver", tag: "MUTATE", desc: "Execute OpenFOAM via Docker: blockMesh, checkMesh, simpleFoam/pisoFoam. Supports MPI parallel." },
          { name: "cfd_read_results", tag: "READ", desc: "Parse forces, residuals, time directories, convergence status." },
          { name: "cfd_parametric_study", tag: "MUTATE", desc: "Parameter sweeps for design optimization and ML dataset generation." },
          { name: "cfd_nl2foam", tag: "MUTATE", desc: "Natural language → executable OpenFOAM case via Ollama LLM." },
          { name: "cfd_sample_for_pinns", tag: "MUTATE", desc: "Export point clouds for PINN/GNN training (CSV, JSON, NumPy)." },
        ].map((t) => (
          <div key={t.name} className="bg-white/5 rounded-xl p-3 flex items-start gap-3">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${t.tag === "READ" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"}`}>{t.tag}</span>
            <div>
              <code className="text-indigo-400 font-bold">{t.name}()</code>
              <p className="text-xs text-slate-500 mt-0.5">{t.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Marketplace</h3>
      <div className="space-y-2">
        {[
          { name: "marketplace_search", tag: "READ", desc: "Search Printables, Thingiverse, GrabCAD for CAD models." },
          { name: "marketplace_download", tag: "MUTATE", desc: "Download a model → uploads directory. Auto-extracts ZIPs." },
          { name: "marketplace_categories", tag: "READ", desc: "List available categories per marketplace source." },
          { name: "show_marketplace_card", tag: "PREFAB", desc: "Rich Prefab UI card with search results in MCP clients." },
        ].map((t) => (
          <div key={t.name} className="bg-white/5 rounded-xl p-3 flex items-start gap-3">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${t.tag === "READ" ? "bg-emerald-500/20 text-emerald-400" : t.tag === "PREFAB" ? "bg-purple-500/20 text-purple-400" : "bg-amber-500/20 text-amber-400"}`}>{t.tag}</span>
            <div>
              <code className="text-indigo-400 font-bold">{t.name}()</code>
              <p className="text-xs text-slate-500 mt-0.5">{t.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <p className="text-slate-500 italic mt-4">Usage via REST: POST /api/v1/control/tool with JSON {"{tool, arguments}"}. Usage via MCP: direct function call.</p>
    </>
  );
}

function MarketplaceHelp() {
  return (
    <>
      <p>Search and import CAD models directly from three community repositories — no browser needed.</p>
      <div className="space-y-3">
        {[
          { name: "Printables", color: "text-orange-400", api: "GraphQL", auth: "None", desc: "Prusa's 3D printing community. Direct STL/STEP downloads. Largest active user base." },
          { name: "Thingiverse", color: "text-cyan-400", api: "REST", auth: "None", desc: "The original 3D model repository. ZIP downloads auto-extracted by the server." },
          { name: "GrabCAD", color: "text-blue-400", api: "REST", auth: "None", desc: "Engineering-focused CAD community. More STEP assemblies and mechanical parts." },
        ].map((s) => (
          <div key={s.name} className="bg-white/5 rounded-xl p-3">
            <h3 className={`font-bold text-sm ${s.color}`}>{s.name}</h3>
            <p className="text-xs text-slate-500 mt-1">{s.desc}</p>
            <div className="flex gap-3 mt-2 text-[10px] text-slate-600">
              <span>API: {s.api}</span>
              <span>Auth: {s.auth}</span>
            </div>
          </div>
        ))}
      </div>
      <p><strong className="text-slate-200">Flow:</strong> Search → Browse results (thumbnails, stats) → Import (downloads to uploads/) → View in Models page (3D viewer) → Slice with PrusaSlicer.</p>
    </>
  );
}

function Printing() {
  return (
    <>
      <p>FreeCAD MCP includes <strong className="text-slate-200">PrusaSlicer 2.8+</strong> integration for end-to-end 3D printing workflows.</p>
      <div className="bg-black/30 rounded-xl p-4 font-mono text-xs space-y-1">
        <div className="text-slate-600"># 1. Convert CAD to mesh</div>
        <div>step_to_stl(<span className="text-green-400">"part.step"</span>, <span className="text-green-400">"part.stl"</span>)</div>
        <div className="text-slate-600"># 2. Inspect before printing</div>
        <div>model_info(<span className="text-green-400">"part.stl"</span>)</div>
        <div className="text-slate-600"># 3. Slice for your printer</div>
        <div>slice_stl(<span className="text-green-400">"part.stl"</span>, printer_profile=<span className="text-green-400">"Prusa MK4"</span>, filament_profile=<span className="text-green-400">"PETG"</span>)</div>
        <div className="text-slate-600"># 4. Download G-code → print</div>
      </div>
      <p><strong className="text-slate-200">Configurable:</strong> printer profile, filament profile, layer height (0.10mm DETAIL to 0.30mm DRAFT). Defaults to Prusa MK4 + PLA + 0.20mm SPEED.</p>
      <p>Set <code className="text-indigo-400">PRUSA_SLICER_PATH</code> env var if PrusaSlicer is not at the default portable location.</p>
    </>
  );
}

function CfdHelp() {
  return (
    <>
      <p><strong className="text-slate-200">Computational Fluid Dynamics</strong> pipeline — FreeCAD geometry → OpenFOAM solver → AI-driven analysis. Requires Docker with <code className="text-indigo-400">openfoam/openfoam10-paraview56</code> image for solver execution. Case generation works without Docker.</p>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Installation</h3>
      <div className="bg-black/30 rounded-xl p-4 font-mono text-xs space-y-1">
        <div className="text-slate-600"># 1. Install Docker Desktop for Windows</div>
        <div className="text-slate-600"># 2. Pull the OpenFOAM image (one-time, ~2 GB)</div>
        <div>docker pull <span className="text-green-400">openfoam/openfoam10-paraview56</span></div>
        <div className="text-slate-600"># 3. (Optional) Install Ollama for NL2FOAM</div>
        <div className="text-slate-600"># 4. Start the freecad-mcp server</div>
        <div>just bootstrap &amp;&amp; start.ps1</div>
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Pipeline Architecture</h3>
      <div className="space-y-1.5 text-xs">
        <div className="flex items-center gap-2"><span className="text-indigo-400 font-mono">1. Geometry</span> <span className="text-slate-600">─</span> <span>FreeCAD parametric domain (channel, pipe, nozzle, custom STEP)</span></div>
        <div className="flex items-center gap-2"><span className="text-indigo-400 font-mono">2. Mesh</span> <span className="text-slate-600">─</span> <span>blockMeshDict → structured hex mesh (blockMesh)</span></div>
        <div className="flex items-center gap-2"><span className="text-indigo-400 font-mono">3. Physics</span> <span className="text-slate-600">─</span> <span>Laminar / kEpsilon / kOmegaSST turbulence models</span></div>
        <div className="flex items-center gap-2"><span className="text-indigo-400 font-mono">4. BCs</span> <span className="text-slate-600">─</span> <span>14 boundary condition types (fixedValue, zeroGradient, noSlip...)</span></div>
        <div className="flex items-center gap-2"><span className="text-indigo-400 font-mono">5. Solve</span> <span className="text-slate-600">─</span> <span>simpleFoam/pisoFoam/pimpleFoam via Docker (serial or MPI parallel)</span></div>
        <div className="flex items-center gap-2"><span className="text-indigo-400 font-mono">6. Analyze</span> <span className="text-slate-600">─</span> <span>Forces, residuals, convergence, time series</span></div>
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Quick Start: Laminar Channel Flow</h3>
      <div className="bg-black/30 rounded-xl p-4 font-mono text-xs space-y-1 overflow-x-auto">
        <div className="text-slate-600"># 1. Create 1m × 0.1m × 0.05m channel</div>
        <div>cfd_create_domain(<span className="text-green-400">"channel"</span>, length_m=<span className="text-amber-400">1.0</span>, width_m=<span className="text-amber-400">0.1</span>, height_m=<span className="text-amber-400">0.05</span>, mesh_cells=<span className="text-amber-400">80000</span>, case_name=<span className="text-green-400">"demo"</span>)</div>
        <div className="text-slate-600"># 2. Configure water at Re=100</div>
        <div>cfd_configure_physics(<span className="text-green-400">"demo"</span>, flow_type=<span className="text-green-400">"laminar"</span>, fluid_nu=<span className="text-amber-400">1e-6</span>, inlet_velocity=<span className="text-amber-400">0.002</span>)</div>
        <div className="text-slate-600"># 3. Set boundary conditions</div>
        <div>cfd_set_boundary(<span className="text-green-400">"demo"</span>, <span className="text-green-400">"inlet"</span>, <span className="text-green-400">"U"</span>, <span className="text-green-400">"fixedValue"</span>, <span className="text-green-400">"uniform (0.002 0 0)"</span>)</div>
        <div>cfd_set_boundary(<span className="text-green-400">"demo"</span>, <span className="text-green-400">"outlet"</span>, <span className="text-green-400">"p"</span>, <span className="text-green-400">"fixedValue"</span>, <span className="text-green-400">"uniform 0"</span>)</div>
        <div className="text-slate-600"># 4. Validate and run</div>
        <div>cfd_build_case(<span className="text-green-400">"demo"</span>)</div>
        <div>cfd_run_solver(<span className="text-green-400">"demo"</span>, steps=<span className="text-green-400">"blockMesh,checkMesh,simpleFoam"</span>)</div>
        <div className="text-slate-600"># 5. Read results</div>
        <div>cfd_read_results(<span className="text-green-400">"demo"</span>)</div>
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Fluid Property Reference</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-200 border-b border-white/10">
              <th className="text-left py-1 pr-3">Fluid</th>
              <th className="text-left py-1 px-2">ν (m²/s)</th>
              <th className="text-left py-1 px-2">ρ (kg/m³)</th>
              <th className="text-left py-1 px-2">Notes</th>
            </tr>
          </thead>
          <tbody className="text-slate-400">
            {[
              ["Water @ 20°C", "1.004e-6", "998", "Default"],
              ["Air @ 20°C", "1.516e-5", "1.204", "Standard atmosphere"],
              ["SAE 10W-30", "6.5e-5", "865", "Hydraulic oil"],
              ["Glycerin", "1.18e-3", "1260", "High-viscosity benchmark"],
              ["Mercury", "1.15e-7", "13546", "Liquid metal"],
            ].map(([name, nu, rho, note]) => (
              <tr key={name} className="border-b border-white/5">
                <td className="py-1 pr-3 text-slate-300">{name}</td>
                <td className="py-1 px-2 font-mono text-indigo-400">{nu}</td>
                <td className="py-1 px-2 font-mono">{rho}</td>
                <td className="py-1 px-2 text-slate-500">{note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">AI &amp; ML Features</h3>
      <div className="space-y-2">
        <div className="bg-white/5 rounded-xl p-3">
          <span className="text-purple-400 font-bold text-xs">NL2FOAM</span>
          <p className="text-xs text-slate-500 mt-1">Describe a CFD problem in plain language — the LLM generates the complete OpenFOAM case (solver, mesh, BCs) automatically. "Laminar pipe flow, Re=500, D=0.1m, water, calculate pressure drop"</p>
        </div>
        <div className="bg-white/5 rounded-xl p-3">
          <span className="text-purple-400 font-bold text-xs">Parametric Sweeps</span>
          <p className="text-xs text-slate-500 mt-1">Run design optimization by sweeping parameters (velocity, geometry, viscosity). Generate 100s of cases for training ML surrogate models.</p>
        </div>
        <div className="bg-white/5 rounded-xl p-3">
          <span className="text-purple-400 font-bold text-xs">PINN Sampling</span>
          <p className="text-xs text-slate-500 mt-1">Export coordinate point clouds for Physics-Informed Neural Networks (NVIDIA Modulus, DeepXDE). CSV, JSON, and NumPy (.npz) formats.</p>
        </div>
      </div>

      <p className="text-slate-500 italic mt-4">Full guide: <code className="text-indigo-400">docs/cfd-guide.md</code> — architecture, complete parameter reference, troubleshooting, performance benchmarks, and bridge extension instructions.</p>
    </>
  );
}

function OpenfoamHelp() {
  return (
    <>
      <p><strong className="text-slate-200">OpenFOAM</strong> is the industry-standard CPU CFD toolkit (finite-volume, MPI-parallel). For GPU-accelerated CFD, the free solver of choice is <a href="https://github.com/ProjectPhysX/FluidX3D" target="_blank" className="text-indigo-400 hover:underline">FluidX3D</a> (5k stars, OpenCL — runs on NVIDIA, AMD, Intel Arc, and Apple Silicon). The MCP server runs OpenFOAM via Docker; FluidX3D integration is planned.</p>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">GPU: Real Options (2026)</h3>
      <div className="space-y-2">
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
          <p className="text-emerald-400 font-bold text-sm">FluidX3D</p>
          <p className="text-xs text-slate-400 mt-1">OpenCL — all GPUs (NVIDIA, AMD, Intel Arc, Apple Silicon). FP16 memory: 770³ cells on 24GB 4090 (~456M cells). Free surfaces, moving boundaries, thermal convection, STL import, interactive 3D viz, video export.</p>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
          <p className="text-emerald-400 font-bold text-sm">Lethe</p>
          <p className="text-xs text-slate-400 mt-1">CUDA-accelerated FEM Navier-Stokes solver. Validated against OpenFOAM benchmarks. Supports incompressible flow with complex geometry.</p>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
          <p className="text-amber-400 font-bold text-sm">Standard OpenFOAM</p>
          <p className="text-xs text-slate-400 mt-1">CPU-only MPI. The <code className="text-indigo-400">openfoam/openfoam10-paraview56</code> image does NOT use GPU. RTX 4090 is idle during cfd_run_solver.</p>
        </div>
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Mac with 128GB RAM?</h3>
      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
        <p className="text-emerald-400 font-bold text-sm">Yes — excellent for this pipeline.</p>
        <p className="text-xs text-slate-400 mt-1">Apple Silicon unified memory means 128GB shared between CPU and GPU. FluidX3D runs on Mac GPU via OpenCL — up to ~1500³ grid (~3.4 BILLION cells) vs ~770³ on 4090. PyTorch MPS backend uses GPU for PINN/GNN training. The 4090 is ~3x faster for training throughput, but the Mac fits problems the 4090 can't hold in VRAM at all. <strong className="text-slate-300">For large parametric studies + big neural surrogates, the Mac is the better single-machine choice.</strong></p>
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Solver Reference</h3>
      <div className="space-y-1.5 text-xs">
        {[
          ["simpleFoam", "Steady incompressible. Most common engineering solver."],
          ["pisoFoam", "Transient incompressible. Vortex shedding, startup transients."],
          ["pimpleFoam", "Transient, large timesteps. Pseudo-transient for complex geometry."],
          ["icoFoam", "Transient laminar only. Educational/validation."],
          ["interFoam", "Multiphase (VOF). Free surfaces, sloshing, waves."],
          ["rhoSimpleFoam", "Steady compressible. High-speed aerodynamics."],
        ].map(([name, desc]) => (
          <div key={name} className="flex items-start gap-2">
            <code className="text-indigo-400 font-mono shrink-0 w-44">{name}</code>
            <span className="text-slate-500">{desc}</span>
          </div>
        ))}
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Case Directory Structure</h3>
      <div className="bg-black/30 rounded-xl p-4 font-mono text-xs space-y-1">
        <div className="text-indigo-400 font-bold">case_name/</div>
        <div>├── <span className="text-slate-500">0/                  Initial/boundary fields</span></div>
        <div>│   ├── <span className="text-slate-500">U                   Velocity</span></div>
        <div>│   ├── <span className="text-slate-500">p                   Pressure</span></div>
        <div>│   └── <span className="text-slate-500">k, omega            Turbulence fields</span></div>
        <div>├── <span className="text-slate-500">constant/           Time-invariant data</span></div>
        <div>│   ├── <span className="text-slate-500">polyMesh/blockMeshDict</span></div>
        <div>│   ├── <span className="text-slate-500">transportProperties</span></div>
        <div>│   └── <span className="text-slate-500">turbulenceProperties</span></div>
        <div>└── <span className="text-slate-500">system/             Solver control</span></div>
        <div>    ├── <span className="text-slate-500">controlDict        Time, write, forces</span></div>
        <div>    ├── <span className="text-slate-500">fvSchemes          Discretisation</span></div>
        <div>    └── <span className="text-slate-500">fvSolution         Linear solvers</span></div>
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">Turbulence Models</h3>
      <div className="space-y-2">
        {[
          { model: "laminar", when: "No model. Re below critical (~2300 pipe, ~5e5 plate).", color: "text-emerald-400" },
          { model: "kEpsilon", when: "High-Re industrial. Wall functions (y+ > 30). 2 extra fields.", color: "text-amber-400" },
          { model: "kOmegaSST", when: "Wall-bounded, separation. Resolves to wall (y+ ≈ 1). 2 extra fields.", color: "text-amber-400" },
          { model: "Spalart-Allmaras", when: "External aero, airfoils. Simple 1-equation. 1 extra field.", color: "text-amber-400" },
        ].map(({ model, when, color }) => (
          <div key={model} className="bg-white/5 rounded-xl p-3">
            <span className={`font-bold text-xs font-mono ${color}`}>{model}</span>
            <p className="text-xs text-slate-500 mt-1">{when}</p>
          </div>
        ))}
      </div>

      <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mt-4">FluidX3D vs OpenFOAM — Quick Pick</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-200 border-b border-white/10">
              <th className="text-left py-1 pr-3">Criterion</th>
              <th className="text-left py-1 px-2 text-emerald-400">FluidX3D</th>
              <th className="text-left py-1 px-2 text-amber-400">OpenFOAM</th>
            </tr>
          </thead>
          <tbody className="text-slate-400">
            {[
              ["GPU", "Yes (OpenCL, all GPUs)", "No (CPU MPI only)"],
              ["Max cells on 4090", "456M (770³)", "~5M (CPU RAM limited)"],
              ["Turbulence", "Smagorinsky-Lilly", "kEpsilon, kOmegaSST, LES, DES"],
              ["Mesh type", "Cartesian voxelized", "Structured + unstructured"],
              ["Maturity", "4 years, 5k stars", "30+ years, industry standard"],
              ["Multiphase", "Free surface", "VOF, Euler-Euler, reacting"],
            ].map(([criterion, f3d, of]) => (
              <tr key={criterion} className="border-b border-white/5">
                <td className="py-1 pr-3 text-slate-300">{criterion}</td>
                <td className="py-1 px-2">{f3d}</td>
                <td className="py-1 px-2">{of}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-slate-500 italic mt-4">Full reference: <code className="text-indigo-400">docs/openfoam.md</code> — GPU solvers, Mac vs 4090 analysis, FluidX3D integration plan, solver reference, mesh quality targets.</p>
    </>
  );
}

function Visualization() {
  return (
    <>
      <p><strong className="text-slate-200">FluidX3D simulation results</strong> can be visualized as video, 3D streamlines, or imported into game engines.</p>

      <h3 className="text-white font-bold mt-6">Output Formats</h3>
      <div className="grid grid-cols-2 gap-3 mt-2">
        {[
          ["VTK (.vtk)", "Raw velocity + density field data. Needs ParaView or our render pipeline to view. Not human-readable directly."],
          ["OBJ (.obj)", "3D streamlines — curves that follow the flow path. Importable into Unity, Godot, Blender, Resonite. Standard format since the 80s."],
          ["WebM (.webm)", "Heatmap video of velocity magnitude. Plays in any browser. Produced by cfd_fluidx3d_render."],
          ["PNG (.png)", "Single heatmap frame. Good for reports, documentation, quick inspection."],
          ["CSV (.csv)", "Velocity point cloud with coordinates. Import into Python, Excel, or ML training pipelines."],
          ["JSON (.json)", "Structured force history, MLUPS throughput, simulation config."],
        ].map(([fmt, desc]) => (
          <div key={String(fmt)} className="p-3 bg-white/5 rounded-xl border border-white/10">
            <p className="text-amber-400 font-bold text-xs uppercase mb-1">{String(fmt)}</p>
            <p className="text-xs text-slate-400">{String(desc)}</p>
          </div>
        ))}
      </div>

      <h3 className="text-white font-bold mt-6">Automatic Video (WebM)</h3>
      <p>Run <code className="text-indigo-400">cfd_fluidx3d_render(case_name="pipe_gpu")</code> — the server reads VTK velocity fields, renders each time step as a colored heatmap, and stitches them into a WebM video via ffmpeg. No manual steps. View in the FluidX3D page <strong className="text-slate-200">Video</strong> tab.</p>

      <h3 className="text-white font-bold mt-6">Game Engine Pipeline (OBJ streamlines)</h3>
      <p>Run <code className="text-indigo-400">cfd_fluidx3d_export_for_render(case_name="pipe_gpu")</code> to generate OBJ streamlines. These are 3D curves you can import anywhere:</p>
      <div className="grid grid-cols-3 gap-3 mt-2">
        {[
          ["Unity3D", "Import .obj → Line Renderer with velocity gradient. VR: place in scene at 1:1 scale."],
          ["Godot 4", "Import .obj as Mesh → MeshInstance3D → Emission shader. Animate with script."],
          ["Resonite", "Import .obj as MeshRenderer → PBS_Metallic material. Walk through flow in VR."],
          ["Blender", "Import .obj → Bevel modifier for thickness → Emission shader. Render for production video."],
          ["Unreal Engine", "Import .obj as Static Mesh → Niagara particles along spline for animated flow."],
          ["Three.js (web)", "Load .obj with THREE/OBJLoader → animate line opacity/color in browser."],
        ].map(([engine, desc]) => (
          <div key={String(engine)} className="p-3 bg-indigo-500/5 rounded-xl border border-indigo-500/20">
            <p className="text-indigo-400 font-bold text-xs mb-1">{String(engine)}</p>
            <p className="text-xs text-slate-500">{String(desc)}</p>
          </div>
        ))}
      </div>

      <h3 className="text-white font-bold mt-6">Professional Post-Processing (ParaView)</h3>
      <p>For publication-quality rendering: download VTK files from <code className="text-indigo-400">GET /api/v1/case-files/{'{case_name}'}/{'{filename}'}</code> and open in <a href="https://www.paraview.org" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">ParaView</a>. Supports slices, contours, streamlines, volume rendering, and animation export.</p>
      <p className="text-xs text-slate-500 mt-2">See <code className="text-indigo-400">docs/flow-visualization.md</code> for the full reference.</p>
    </>
  );
}

function Links() {
  return (
    <div className="space-y-2">
      {[
        ["freecad.org", "Official website", "https://www.freecad.org"],
        ["github.com/FreeCAD/FreeCAD", "Source code (C++/Python, 16k stars)", "https://github.com/FreeCAD/FreeCAD"],
        ["forum.freecad.org", "Community forum — 300k+ posts", "https://forum.freecad.org"],
        ["wiki.freecad.org", "Comprehensive documentation", "https://wiki.freecad.org"],
        ["printables.com", "3D model marketplace (Prusa)", "https://www.printables.com"],
        ["thingiverse.com", "3D model marketplace (UltiMaker)", "https://www.thingiverse.com"],
        ["grabcad.com", "Engineering CAD library (Stratasys)", "https://grabcad.com"],
        ["PrusaSlicer", "Slicer for 3D printing", "https://github.com/prusa3d/PrusaSlicer"],
        ["OpenCASCADE", "The OCCT geometry kernel", "https://dev.opencascade.org"],
        ["OpenFOAM", "Open-source CFD toolkit", "https://www.openfoam.com"],
        ["NVIDIA Modulus", "Physics-ML framework (PINNs)", "https://developer.nvidia.com/modulus"],
        ["DeepXDE", "Lightweight PINN library", "https://deepxde.readthedocs.io"],
        ["FluidX3D", "Free GPU CFD (OpenCL, all GPUs)", "https://github.com/ProjectPhysX/FluidX3D"],
        ["Lethe", "GPU-accelerated FEM CFD", "https://github.com/lethe-cfd/lethe"],
        ["FluidX3D Docs", "Setup, extensions, video rendering", "https://github.com/ProjectPhysX/FluidX3D/blob/master/DOCUMENTATION.md"],
      ].map(([label, desc, url]) => (
        <a key={url} href={url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all group">
          <div>
            <span className="text-indigo-400 font-bold text-sm group-hover:text-indigo-300">{label}</span>
            <p className="text-xs text-slate-500">{desc}</p>
          </div>
          <ExternalLink size={14} className="text-slate-600 group-hover:text-slate-400" />
        </a>
      ))}
    </div>
  );
}
