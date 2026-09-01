import { ArrowLeftRight, Box, Building2, Columns, Cpu, FileText, Home, Wrench } from "lucide-react";

const apps = [
	{
		name: "STEP ⟶ STL",
		desc: "Upload a STEP assembly and download the converted STL mesh.",
		icon: Box,
		path: "/convert",
	},
	{
		name: "Model Info",
		desc: "Inspect CAD files: object count, solids, volume, bounding box.",
		icon: FileText,
		path: "/models",
	},
	{
		name: "Create Shape",
		desc: "Generate basic geometry (box, cylinder, sphere, cone) and export as STL.",
		icon: Cpu,
		path: "/convert",
	},
	{
		name: "BIM — Walls",
		desc: "Parametric architectural walls with placement, rotation, thickness.",
		icon: Home,
		path: "/convert",
	},
	{
		name: "BIM — Slabs & Columns",
		desc: "Floor slabs and structural columns (rectangular, circular, H-section).",
		icon: Building2,
		path: "/convert",
	},
	{
		name: "BIM — Windows & Doors",
		desc: "Windows and doors hosted in auto-generated walls with sill height.",
		icon: Columns,
		path: "/convert",
	},
	{
		name: "BIM — IFC Exchange",
		desc: "Export .fcstd → .ifc and import architectural .ifc files.",
		icon: ArrowLeftRight,
		path: "/convert",
	},
	{
		name: "CAD Expert Chat",
		desc: "Ask FreeCAD, BIM and CAD modelling questions to the AI expert.",
		icon: Cpu,
		path: "/chat",
	},
];

export default function AppsPage() {
	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-white flex items-center gap-3">
				<Wrench className="text-indigo-400" /> Apps
			</h1>
			<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
				{apps.map((app) => (
					<a
						key={app.name}
						href={app.path}
						className="bg-[#0f0f12] border border-white/5 rounded-2xl p-5 hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all group"
					>
						<div className="flex items-center gap-3 mb-2">
							<app.icon size={20} className="text-indigo-400" />
							<h3 className="text-sm font-bold text-white group-hover:text-indigo-300">{app.name}</h3>
						</div>
						<p className="text-xs text-slate-500">{app.desc}</p>
					</a>
				))}
			</div>
		</div>
	);
}
