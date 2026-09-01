import { motion } from "framer-motion";
import {
	Bot,
	Box,
	Boxes,
	Car,
	Cog,
	Cpu,
	Database,
	FileText,
	Gauge,
	GitBranch,
	HelpCircle,
	Home,
	LayoutDashboard,
	Logs,
	Settings,
	ShoppingBag,
	Sparkles,
	Waves,
	Wrench,
	Zap,
} from "lucide-react";
import { NavLink } from "react-router-dom";

const navItems = [
	{ path: "/", label: "Dashboard", icon: LayoutDashboard },
	{ path: "/parts", label: "Parts Studio", icon: Cog },
	{ path: "/depot", label: "Depot", icon: Database },

	{ path: "/convert", label: "Convert", icon: Box },
	{ path: "/models", label: "Models", icon: Boxes },
	{ path: "/marketplace", label: "Marketplace", icon: ShoppingBag },
	{ path: "/bim-demo", label: "BIM Demo", icon: Home },
	{ path: "/cfd-demos", label: "CFD Demos", icon: Sparkles },
	{ path: "/toy-car", label: "Toy Car", icon: Car },
	{ path: "/cfd", label: "CFD/OF", icon: Waves },
	{ path: "/fluidx3d", label: "FluidX3D", icon: Zap },
	{ path: "/pipeline", label: "Pipeline", icon: GitBranch },
	{ path: "/chat", label: "CAD Expert", icon: Bot },
	{ path: "/apps", label: "Apps", icon: Wrench },
	{ path: "/logs", label: "Logs", icon: Logs },
	{ path: "/settings", label: "Settings", icon: Settings },
	{ path: "/help", label: "Help", icon: HelpCircle },
];

export default function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
	return (
		<motion.aside
			animate={{ width: collapsed ? 72 : 240 }}
			className="flex flex-col bg-[#0f0f12] border-r border-white/5 h-full shrink-0 overflow-hidden"
		>
			<div className="h-14 flex items-center gap-3 px-4 border-b border-white/5">
				<Cpu className="text-indigo-400 shrink-0" size={22} />
				{!collapsed && <span className="text-sm font-bold text-white whitespace-nowrap">FreeCAD MCP</span>}
			</div>
			<nav className="flex-1 p-3 space-y-1 overflow-y-auto">
				{navItems.map((item) => (
					<NavLink
						key={item.path}
						to={item.path}
						end={item.path === "/"}
						className={({ isActive }) =>
							`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
								isActive
									? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
									: "text-slate-400 hover:text-slate-200 hover:bg-white/5"
							}`
						}
					>
						<item.icon size={18} className="shrink-0" />
						{!collapsed && <span className="whitespace-nowrap">{item.label}</span>}
					</NavLink>
				))}
			</nav>
			<button onClick={onToggle} className="p-3 text-xs text-slate-600 hover:text-slate-400 border-t border-white/5">
				{collapsed ? ">>" : "Collapse"}
			</button>
		</motion.aside>
	);
}
