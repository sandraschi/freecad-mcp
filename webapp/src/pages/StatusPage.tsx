import { CheckCircle2, Cpu, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

export default function StatusPage() {
	const [status, setStatus] = useState<any>(null);
	useEffect(() => {
		fetch(API_BASE + "/api/v1/status")
			.then((r) => r.json())
			.then(setStatus)
			.catch(() => setStatus({ freecad_ok: false }));
	}, []);
	return (
		<div className="max-w-2xl space-y-6">
			<h1 className="text-2xl font-bold text-white">Server Status</h1>
			<div className="bg-[#0f0f12] border border-white/5 rounded-2xl p-6 space-y-4">
				<div className="flex items-center gap-3">
					{status?.freecad_ok ? (
						<CheckCircle2 className="text-emerald-400" size={24} />
					) : (
						<XCircle className="text-red-400" size={24} />
					)}
					<div>
						<p className="font-bold text-white">{status?.freecad_ok ? "FreeCAD Ready" : "FreeCAD Not Found"}</p>
						<p className="text-sm text-slate-400">FreeCADCmd.exe — {status?.freecad_version || "unavailable"}</p>
					</div>
				</div>
				{status?.freecad_ok && (
					<div className="grid grid-cols-2 gap-3 text-sm">
						<div className="bg-white/5 rounded-xl p-3">
							<Cpu size={16} className="text-indigo-400 mb-1" /> Version{" "}
							<p className="font-mono text-slate-300">{status.freecad_version}</p>
						</div>
						<div className="bg-white/5 rounded-xl p-3">
							<Cpu size={16} className="text-indigo-400 mb-1" /> Work Dir{" "}
							<p className="font-mono text-slate-300 text-xs">$TEMP/freecad_mcp_work</p>
						</div>
					</div>
				)}
			</div>
		</div>
	);
}
