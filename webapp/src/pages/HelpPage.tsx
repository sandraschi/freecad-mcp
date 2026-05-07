import { HelpCircle, ExternalLink, BookOpen, Cpu, FileText } from "lucide-react";
import { useState } from "react";

const sections = [
  { id: "intro", label: "FreeCAD", icon: BookOpen },
  { id: "workbenches", label: "Workbenches", icon: Cpu },
  { id: "formats", label: "File Formats", icon: FileText },
  { id: "links", label: "Links", icon: ExternalLink },
];

export default function HelpPage() {
  const [tab, setTab] = useState("intro");
  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3"><HelpCircle className="text-indigo-400" /> Help</h1>
      <div className="flex gap-2 p-1 bg-white/5 rounded-2xl w-fit">
        {sections.map((s) => (
          <button key={s.id} onClick={() => setTab(s.id)} className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider ${tab === s.id ? "bg-indigo-600 text-white" : "text-slate-500 hover:text-slate-300"}`}>
            <s.icon size={13} className="inline mr-1.5" />{s.label}
          </button>
        ))}
      </div>
      <div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-6 text-sm text-slate-400 leading-relaxed space-y-3">
        {tab === "intro" && <>
          <p><strong className="text-slate-200">FreeCAD</strong> is a free, open-source parametric 3D CAD modeller (LGPL). It uses the OpenCASCADE (OCCT) CAD kernel — the same technology behind CATIA.</p>
          <p>It is <strong className="text-slate-200">not</strong> a mesh modeller like Blender. It creates precise solid models with a parametric feature tree. Changes to early features propagate through the entire model.</p>
          <p>The fleet runs FreeCAD 1.1.1 as the backend for the freecad-mcp server, handling STEP→STL conversion, model metadata extraction, and basic geometry creation.</p>
        </>}
        {tab === "workbenches" && <>
          <p><strong className="text-slate-200">Part</strong> — primitives (box, cylinder, sphere) and boolean operations (fuse, cut, intersect).</p>
          <p><strong className="text-slate-200">Part Design</strong> — parametric feature tree: pads, pockets, revolutions, fillets, chamfers.</p>
          <p><strong className="text-slate-200">Sketcher</strong> — 2D constraint-based sketching, foundation for Part Design.</p>
          <p><strong className="text-slate-200">Assembly</strong> — constrain parts together (new in 1.0).</p>
          <p><strong className="text-slate-200">Mesh</strong> — STL/OBJ import/export, repair.</p>
          <p><strong className="text-slate-200">TechDraw</strong> — engineering drawings from 3D models.</p>
          <p><strong className="text-slate-200">BIM</strong> — building information modelling (FreeCAD's "AutoCAD killer").</p>
          <p><strong className="text-slate-200">CAM</strong> — CNC toolpath generation.</p>
        </>}
        {tab === "formats" && <>
          <p><strong className="text-slate-200">STEP (.step, .stp)</strong> — industry standard for 3D CAD exchange. AP203 (basic) and AP214 (automotive assembly). The fleet uses AP214.</p>
          <p><strong className="text-slate-200">STL (.stl)</strong> — triangle mesh format for 3D printing and web visualization. Converted from STEP.</p>
          <p><strong className="text-slate-200">FCStd (.FCStd)</strong> — FreeCAD's native parametric format (ZIP containing XML geometry + BREP).</p>
          <p><strong className="text-slate-200">IGES (.iges, .igs)</strong> — older CAD exchange format, supported for import.</p>
          <p><strong className="text-slate-200">OBJ (.obj)</strong> — mesh format with optional material/colour.</p>
          <p><strong className="text-slate-200">DXF (.dxf)</strong> — 2D drawing exchange.</p>
        </>}
        {tab === "links" && <>
          <p><a href="https://www.freecad.org" target="_blank" className="text-indigo-400 hover:underline">freecad.org</a> — official website</p>
          <p><a href="https://github.com/FreeCAD/FreeCAD" target="_blank" className="text-indigo-400 hover:underline">github.com/FreeCAD/FreeCAD</a> — source code</p>
          <p><a href="https://forum.freecad.org" target="_blank" className="text-indigo-400 hover:underline">forum.freecad.org</a> — community forum</p>
          <p><a href="https://wiki.freecad.org" target="_blank" className="text-indigo-400 hover:underline">wiki.freecad.org</a> — documentation</p>
        </>}
      </div>
    </div>
  );
}
