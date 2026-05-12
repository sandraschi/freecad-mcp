import { useState } from "react";
import { BookOpen, Cpu, Code2, ExternalLink, HelpCircle, Package, Printer, ShoppingBag, Wrench, Layers, History, GitCompare } from "lucide-react";

const sections = [
  { id: "intro", label: "FreeCAD", icon: BookOpen },
  { id: "history", label: "History", icon: History },
  { id: "scripting", label: "Scripting", icon: Code2 },
  { id: "workbenches", label: "Workbenches", icon: Layers },
  { id: "comparison", label: "vs Pro CAD", icon: GitCompare },
  { id: "tools", label: "MCP Tools", icon: Wrench },
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
        {tab === "marketplace" && <MarketplaceHelp />}
        {tab === "printing" && <Printing />}
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
      <p><strong className="text-slate-200">7 MCP tools</strong> registered in the server. Available via MCP SSE and the REST proxy.</p>
      <div className="space-y-2.5">
        {[
          { name: "freecad_status", tag: "READ", desc: "FreeCAD availability + version. Call this first." },
          { name: "step_to_stl", tag: "MUTATE", desc: "Convert STEP/STP assembly → STL mesh. Uses TCP bridge for AP214." },
          { name: "model_info", tag: "READ", desc: "Object count, solids, volume, bounding box. Works on STEP + STL." },
          { name: "create_shape", tag: "MUTATE", desc: "Box, cylinder, sphere, cone → STL. All dimensions in mm." },
          { name: "slicer_status", tag: "READ", desc: "PrusaSlicer availability + version check." },
          { name: "slice_stl", tag: "MUTATE", desc: "Slice STL → G-code. Configurable printer/filament/quality." },
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
      <p className="text-slate-500 italic">Usage via REST: POST /api/v1/control/tool with JSON {"{tool, arguments}"}. Usage via MCP: direct function call.</p>
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
