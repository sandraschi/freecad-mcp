import {
	AlertTriangle,
	Box,
	Circle,
	Database,
	Download,
	EyeOff,
	FileText,
	Grid3X3,
	Layers,
	List,
	Loader2,
	Pencil,
	Plus,
	RefreshCw,
	Ruler,
	Save,
	Search,
	Square,
	Trash2,
	Upload,
	X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

type CadFile = {
	name: string;
	size_kb: number;
	size_bytes: number;
	modified: string;
	meta: {
		created?: string;
		description?: string;
		tags?: string[];
		shape_type?: string;
	};
};

function formatDate(iso: string) {
	try {
		return new Date(iso).toLocaleString();
	} catch {
		return iso;
	}
}

function timeAgo(iso: string) {
	try {
		const diff = Date.now() - new Date(iso).getTime();
		const mins = Math.floor(diff / 60000);
		if (mins < 1) return "just now";
		if (mins < 60) return `${mins}m ago`;
		const hrs = Math.floor(mins / 60);
		if (hrs < 24) return `${hrs}h ago`;
		const days = Math.floor(hrs / 24);
		return `${days}d ago`;
	} catch {
		return "";
	}
}

export default function DepotPage() {
	const [files, setFiles] = useState<CadFile[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [search, setSearch] = useState("");
	const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
	const [selectedFile, setSelectedFile] = useState<string | null>(null);
	const [fileInfo, setFileInfo] = useState<any>(null);

	// Dialogs
	const [showCreate, setShowCreate] = useState(false);
	const [renameTarget, setRenameTarget] = useState<string | null>(null);
	const [renameValue, setRenameValue] = useState("");
	const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

	// Create form
	const [createShapeType, setCreateShapeType] = useState("box");
	const [createDesc, setCreateDesc] = useState("");
	const [createParams, setCreateParams] = useState<Record<string, number>>({ width: 50, height: 30, depth: 20 });
	const [creating, setCreating] = useState(false);

	// Upload
	const [uploading, setUploading] = useState(false);

	const loadFiles = useCallback(async () => {
		setLoading(true);
		try {
			const r = await fetch(API_BASE + "/api/v1/depot");
			const j = await r.json();
			setFiles(j.files || []);
		} catch {
			setError("Failed to load depot");
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		loadFiles();
	}, [loadFiles]);

	const shapeParamDefs: Record<string, { label: string; key: string; default: number }[]> = {
		box: [
			{ label: "Width", key: "width", default: 50 },
			{ label: "Height", key: "height", default: 30 },
			{ label: "Depth", key: "depth", default: 20 },
		],
		cylinder: [
			{ label: "Radius", key: "radius", default: 20 },
			{ label: "Height", key: "height", default: 40 },
		],
		sphere: [{ label: "Radius", key: "radius", default: 25 }],
		cone: [
			{ label: "Radius", key: "radius", default: 15 },
			{ label: "Height", key: "height", default: 30 },
		],
	};

	const filtered = files.filter(
		(f) =>
			f.name.toLowerCase().includes(search.toLowerCase()) ||
			(f.meta.description || "").toLowerCase().includes(search.toLowerCase()),
	);

	const selectFile = async (name: string) => {
		setSelectedFile(name);
		setFileInfo(null);
		try {
			const infoR = await fetch(API_BASE + "/api/v1/control/tool", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ tool: "model_info", arguments: { file_name: name } }),
			});
			const infoJ = await infoR.json();
			if (infoJ.success) setFileInfo(infoJ.data);
		} catch {}
	};

	const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (!file) return;
		setUploading(true);
		setError("");
		try {
			const fd = new FormData();
			fd.append("file", file);
			const r = await fetch(API_BASE + "/api/v1/depot/upload", { method: "POST", body: fd });
			const j = await r.json();
			if (!j.success) throw new Error(j.detail || "Upload failed");
			await loadFiles();
		} catch (err: any) {
			setError(err.message || "Upload failed");
		} finally {
			setUploading(false);
			e.target.value = "";
		}
	};

	const handleCreate = async () => {
		setCreating(true);
		setError("");
		try {
			const params = { ...createParams };
			const r = await fetch(API_BASE + "/api/v1/depot/create", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ shape_type: createShapeType, params, description: createDesc }),
			});
			const j = await r.json();
			if (!j.success) throw new Error(j.error || "Creation failed");
			setShowCreate(false);
			setCreateDesc("");
			await loadFiles();
		} catch (err: any) {
			setError(err.message);
		} finally {
			setCreating(false);
		}
	};

	const handleRename = async () => {
		if (!renameTarget || !renameValue) return;
		try {
			const r = await fetch(API_BASE + `/api/v1/depot/${encodeURIComponent(renameTarget)}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ name: renameValue }),
			});
			if (!r.ok) {
				const j = await r.json();
				throw new Error(j.detail || "Rename failed");
			}
			setRenameTarget(null);
			if (selectedFile === renameTarget) setSelectedFile(null);
			await loadFiles();
		} catch (err: any) {
			setError(err.message);
		}
	};

	const handleDelete = async () => {
		if (!deleteTarget) return;
		try {
			const r = await fetch(API_BASE + `/api/v1/depot/${encodeURIComponent(deleteTarget)}`, { method: "DELETE" });
			if (!r.ok) {
				const j = await r.json();
				throw new Error(j.detail || "Delete failed");
			}
			setDeleteTarget(null);
			if (selectedFile === deleteTarget) setSelectedFile(null);
			await loadFiles();
		} catch (err: any) {
			setError(err.message);
		}
	};

	const shapeTypeChanged = (st: string) => {
		setCreateShapeType(st);
		const defaults = shapeParamDefs[st] || [];
		const params: Record<string, number> = {};
		defaults.forEach((d) => {
			params[d.key] = d.default;
		});
		setCreateParams(params);
	};

	const fileIcon = (name: string) => {
		const ext = name.split(".").pop()?.toLowerCase();
		if (ext === "stl") return <Box size={16} className="text-emerald-400" />;
		if (ext === "step" || ext === "stp") return <FileText size={16} className="text-indigo-400" />;
		if (ext === "ifc" || ext === "ifcxml") return <FileText size={16} className="text-amber-400" />;
		if (ext === "fcstd") return <FileText size={16} className="text-sky-400" />;
		return <FileText size={16} className="text-slate-400" />;
	};

	return (
		<div className="space-y-4 max-w-7xl mx-auto">
			{/* Header */}
			<div className="flex items-center justify-between flex-wrap gap-3">
				<h1 className="text-2xl font-bold text-white flex items-center gap-3">
					<Database className="text-indigo-400" /> CAD Depot
				</h1>
				<div className="flex items-center gap-2">
					<button
						onClick={loadFiles}
						className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-white/10 text-xs text-slate-400 hover:text-white hover:bg-white/5"
					>
						<RefreshCw size={14} /> Refresh
					</button>
					<label className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold cursor-pointer">
						<Upload size={14} /> {uploading ? "Uploading..." : "Upload"}
						<input
							type="file"
							accept=".step,.stp,.stl,.ifc,.fcstd,.iges,.obj,.dxf"
							className="hidden"
							onChange={handleUpload}
							disabled={uploading}
						/>
					</label>
					<button
						onClick={() => setShowCreate(true)}
						className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold"
					>
						<Plus size={14} /> New Shape
					</button>
				</div>
			</div>

			{error && (
				<div className="p-3 rounded-xl bg-red-950/40 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
					<AlertTriangle size={14} /> {error}
					<button onClick={() => setError("")} className="ml-auto text-red-400 hover:text-red-300">
						<X size={14} />
					</button>
				</div>
			)}

			{/* Search + view toggle */}
			<div className="flex items-center gap-3">
				<div className="flex items-center gap-2 px-3 py-2 rounded-xl border border-white/10 bg-[#0f0f12] flex-1 max-w-md">
					<Search size={14} className="text-slate-500 shrink-0" />
					<input
						type="text"
						placeholder="Search files..."
						value={search}
						onChange={(e) => setSearch(e.target.value)}
						className="bg-transparent text-sm text-slate-200 placeholder-slate-600 outline-none w-full"
					/>
				</div>
				<div className="flex gap-1 p-1 bg-white/5 rounded-xl">
					<button
						onClick={() => setViewMode("grid")}
						className={`p-1.5 rounded-lg ${viewMode === "grid" ? "bg-indigo-600 text-white" : "text-slate-500 hover:text-slate-300"}`}
					>
						<Grid3X3 size={14} />
					</button>
					<button
						onClick={() => setViewMode("list")}
						className={`p-1.5 rounded-lg ${viewMode === "list" ? "bg-indigo-600 text-white" : "text-slate-500 hover:text-slate-300"}`}
					>
						<List size={14} />
					</button>
				</div>
				<span className="text-xs text-slate-600">
					{files.length} file{files.length !== 1 ? "s" : ""}
				</span>
			</div>

			{/* Loading */}
			{loading ? (
				<div className="flex items-center justify-center py-20">
					<Loader2 className="animate-spin text-indigo-400" size={32} />
				</div>
			) : filtered.length === 0 ? (
				<div className="text-center py-20 text-slate-600 space-y-3">
					<Database size={48} className="mx-auto opacity-30" />
					<p className="text-lg">{files.length === 0 ? "Depot is empty" : "No files match your search"}</p>
					<p className="text-sm">
						{files.length === 0
							? "Upload a CAD file or create a new shape to get started."
							: "Try a different search term."}
					</p>
					{files.length === 0 && (
						<div className="flex gap-3 justify-center mt-4">
							<label className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold cursor-pointer">
								<Upload size={14} /> Upload
								<input type="file" accept=".step,.stp,.stl,.ifc,.fcstd" className="hidden" onChange={handleUpload} />
							</label>
							<button
								onClick={() => setShowCreate(true)}
								className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold"
							>
								<Plus size={14} /> New Shape
							</button>
						</div>
					)}
				</div>
			) : viewMode === "grid" ? (
				<div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
					{filtered.map((f) => (
						<div
							key={f.name}
							onClick={() => selectFile(f.name)}
							className={`bg-[#0f0f12] border rounded-2xl p-4 cursor-pointer transition-all hover:border-indigo-500/30 space-y-2 ${
								selectedFile === f.name ? "border-indigo-500/50 bg-indigo-500/5" : "border-white/5"
							}`}
						>
							<div className="flex items-start justify-between">
								{fileIcon(f.name)}
								<div className="flex gap-1">
									<button
										onClick={(e) => {
											e.stopPropagation();
											setRenameTarget(f.name);
											setRenameValue(f.name);
										}}
										className="text-slate-600 hover:text-slate-300 p-0.5"
									>
										<Pencil size={12} />
									</button>
									<button
										onClick={(e) => {
											e.stopPropagation();
											setDeleteTarget(f.name);
										}}
										className="text-slate-600 hover:text-red-400 p-0.5"
									>
										<Trash2 size={12} />
									</button>
								</div>
							</div>
							<p className="text-sm font-medium text-slate-200 truncate">{f.name}</p>
							<div className="flex items-center justify-between text-xs text-slate-600">
								<span>{f.size_kb} KB</span>
								<span>{timeAgo(f.modified)}</span>
							</div>
							{f.meta.shape_type && (
								<div className="flex items-center gap-1 text-xs text-slate-500">
									<Square size={10} /> {f.meta.shape_type}
								</div>
							)}
						</div>
					))}
				</div>
			) : (
				<div className="bg-[#0f0f12] border border-white/5 rounded-2xl overflow-hidden">
					<table className="w-full text-sm">
						<thead>
							<tr className="text-left text-slate-500 border-b border-white/5">
								<th className="py-3 px-4 font-medium">Name</th>
								<th className="py-3 px-4 font-medium">Size</th>
								<th className="py-3 px-4 font-medium">Modified</th>
								<th className="py-3 px-4 font-medium">Type</th>
								<th className="py-3 px-4 font-medium">Actions</th>
							</tr>
						</thead>
						<tbody>
							{filtered.map((f) => (
								<tr
									key={f.name}
									onClick={() => selectFile(f.name)}
									className={`border-b border-white/[0.02] cursor-pointer hover:bg-white/[0.02] ${
										selectedFile === f.name ? "bg-indigo-500/5" : ""
									}`}
								>
									<td className="py-3 px-4">
										<span className="flex items-center gap-2 text-slate-300">
											{fileIcon(f.name)} {f.name}
										</span>
									</td>
									<td className="py-3 px-4 text-slate-500">{f.size_kb} KB</td>
									<td className="py-3 px-4 text-slate-500">{formatDate(f.modified)}</td>
									<td className="py-3 px-4 text-slate-500">
										{f.meta.shape_type || f.name.split(".").pop()?.toUpperCase() || "—"}
									</td>
									<td className="py-3 px-4">
										<div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
											<button
												onClick={() => {
													setRenameTarget(f.name);
													setRenameValue(f.name);
												}}
												className="p-1 text-slate-600 hover:text-slate-300 rounded"
											>
												<Pencil size={13} />
											</button>
											<button
												onClick={() => setDeleteTarget(f.name)}
												className="p-1 text-slate-600 hover:text-red-400 rounded"
											>
												<Trash2 size={13} />
											</button>
											<a
												href={`/api/v1/depot/${encodeURIComponent(f.name)}`}
												download
												className="p-1 text-slate-600 hover:text-emerald-400 rounded"
											>
												<Download size={13} />
											</a>
										</div>
									</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			)}

			{/* Detail panel */}
			{selectedFile && (
				<div className="bg-[#0f0f12] border border-white/5 rounded-2xl overflow-hidden">
					<div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
						<h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
							{fileIcon(selectedFile)} {selectedFile}
						</h3>
						<div className="flex items-center gap-2">
							<a
								href={`/api/v1/depot/${encodeURIComponent(selectedFile)}`}
								download
								className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold"
							>
								<Download size={12} /> Download
							</a>
							<button onClick={() => setSelectedFile(null)} className="text-slate-600 hover:text-slate-300 p-1">
								<X size={14} />
							</button>
						</div>
					</div>
					<div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-4">
						{/* Preview — Three.js STL viewer if STL, otherwise info */}
						<div
							className="lg:col-span-2 bg-[#0a0a0c] border border-white/5 rounded-xl overflow-auto"
							style={{ maxHeight: "50vh" }}
						>
							{selectedFile.toLowerCase().endsWith(".stl") ? (
								<div className="flex items-center justify-center h-64 text-slate-500 text-sm">
									STL file —{" "}
									<a
										href={`/api/v1/depot/${encodeURIComponent(selectedFile)}`}
										download
										className="text-indigo-400 hover:underline ml-1"
									>
										download to view in 3D
									</a>
								</div>
							) : (
								<div className="flex items-center justify-center h-64 text-slate-500 text-sm">
									Preview not available for this format
								</div>
							)}
						</div>

						{/* Metadata */}
						<div className="space-y-3">
							<div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-3 space-y-2">
								<h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Info</h4>
								{(() => {
									const f = files.find((x) => x.name === selectedFile);
									if (!f) return null;
									return (
										<>
											<div className="flex justify-between text-xs">
												<span className="text-slate-500">Size</span>
												<span className="text-slate-300">{f.size_kb} KB</span>
											</div>
											<div className="flex justify-between text-xs">
												<span className="text-slate-500">Created</span>
												<span className="text-slate-300">{f.meta.created ? formatDate(f.meta.created) : "—"}</span>
											</div>
											<div className="flex justify-between text-xs">
												<span className="text-slate-500">Modified</span>
												<span className="text-slate-300">{formatDate(f.modified)}</span>
											</div>
											{f.meta.shape_type && (
												<div className="flex justify-between text-xs">
													<span className="text-slate-500">Type</span>
													<span className="text-slate-300">{f.meta.shape_type}</span>
												</div>
											)}
											{f.meta.description && (
												<div className="text-xs text-slate-400 pt-1 border-t border-white/5">{f.meta.description}</div>
											)}
										</>
									);
								})()}
							</div>

							{fileInfo && (
								<div className="bg-[#0a0a0c] border border-white/5 rounded-xl p-3 space-y-2">
									<h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Details</h4>
									{fileInfo.objects && (
										<div className="flex justify-between text-xs">
											<span className="text-slate-500">Objects</span>
											<span className="text-slate-300">{fileInfo.total || fileInfo.objects.length}</span>
										</div>
									)}
									{fileInfo.vertices && (
										<div className="flex justify-between text-xs">
											<span className="text-slate-500">Vertices</span>
											<span className="text-slate-300">{fileInfo.vertices}</span>
										</div>
									)}
									{fileInfo.facets && (
										<div className="flex justify-between text-xs">
											<span className="text-slate-500">Facets</span>
											<span className="text-slate-300">{fileInfo.facets}</span>
										</div>
									)}
								</div>
							)}

							<div className="flex gap-2">
								<button
									onClick={() => {
										setRenameTarget(selectedFile);
										setRenameValue(selectedFile);
									}}
									className="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-xl border border-white/10 text-xs text-slate-400 hover:text-white"
								>
									<Pencil size={12} /> Rename
								</button>
								<button
									onClick={() => setDeleteTarget(selectedFile)}
									className="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-xl border border-red-500/20 text-xs text-red-400 hover:bg-red-500/10"
								>
									<Trash2 size={12} /> Delete
								</button>
							</div>
						</div>
					</div>
				</div>
			)}

			{/* Create Shape Dialog */}
			{showCreate && (
				<div
					className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
					onClick={() => setShowCreate(false)}
				>
					<div
						className="bg-[#0f0f12] border border-white/10 rounded-2xl p-6 max-w-md w-full mx-4"
						onClick={(e) => e.stopPropagation()}
					>
						<div className="flex items-center justify-between mb-4">
							<h2 className="text-lg font-bold text-white flex items-center gap-2">
								<Circle size={18} className="text-indigo-400" /> Create Shape
							</h2>
							<button onClick={() => setShowCreate(false)} className="text-slate-600 hover:text-slate-300">
								<X size={18} />
							</button>
						</div>

						<div className="space-y-3">
							<label className="block text-xs text-slate-500">Shape Type</label>
							<div className="flex gap-2">
								{Object.keys(shapeParamDefs).map((st) => (
									<button
										key={st}
										onClick={() => shapeTypeChanged(st)}
										className={`flex-1 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wider ${
											createShapeType === st
												? "bg-indigo-600 text-white"
												: "bg-white/5 text-slate-400 hover:text-slate-200"
										}`}
									>
										{st === "box" && <Square size={14} className="inline mr-1" />}
										{st === "cylinder" && <Circle size={14} className="inline mr-1" />}
										{st === "sphere" && <Circle size={14} className="inline mr-1" />}
										{st === "cone" && <Box size={14} className="inline mr-1" />}
										{st}
									</button>
								))}
							</div>

							<label className="block text-xs text-slate-500 mt-3">Parameters</label>
							<div className="grid grid-cols-2 gap-2">
								{(shapeParamDefs[createShapeType] || []).map((pd) => (
									<label key={pd.key} className="block">
										<span className="text-xs text-slate-500">{pd.label}</span>
										<input
											type="number"
											value={createParams[pd.key] ?? pd.default}
											onChange={(e) =>
												setCreateParams({ ...createParams, [pd.key]: parseFloat(e.target.value) || pd.default })
											}
											className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500/30"
										/>
									</label>
								))}
							</div>

							<label className="block text-xs text-slate-500">Description (optional)</label>
							<input
								value={createDesc}
								onChange={(e) => setCreateDesc(e.target.value)}
								placeholder="Test bracket"
								className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500/30"
							/>
						</div>

						<div className="flex gap-3 mt-4">
							<button
								onClick={() => setShowCreate(false)}
								className="flex-1 py-2.5 rounded-xl border border-white/10 text-sm text-slate-400 hover:text-white"
							>
								Cancel
							</button>
							<button
								onClick={handleCreate}
								disabled={creating}
								className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-bold flex items-center justify-center gap-2"
							>
								{creating ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
								{creating ? "Creating..." : "Create"}
							</button>
						</div>
					</div>
				</div>
			)}

			{/* Rename Dialog */}
			{renameTarget && (
				<div
					className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
					onClick={() => setRenameTarget(null)}
				>
					<div
						className="bg-[#0f0f12] border border-white/10 rounded-2xl p-6 max-w-sm w-full mx-4"
						onClick={(e) => e.stopPropagation()}
					>
						<h2 className="text-lg font-bold text-white mb-4">Rename File</h2>
						<input
							value={renameValue}
							onChange={(e) => setRenameValue(e.target.value)}
							placeholder="New filename"
							className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500/30 mb-4"
						/>
						<div className="flex gap-3">
							<button
								onClick={() => setRenameTarget(null)}
								className="flex-1 py-2.5 rounded-xl border border-white/10 text-sm text-slate-400 hover:text-white"
							>
								Cancel
							</button>
							<button
								onClick={handleRename}
								disabled={!renameValue}
								className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-bold"
							>
								Rename
							</button>
						</div>
					</div>
				</div>
			)}

			{/* Delete Confirmation */}
			{deleteTarget && (
				<div
					className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
					onClick={() => setDeleteTarget(null)}
				>
					<div
						className="bg-[#0f0f12] border border-white/10 rounded-2xl p-6 max-w-sm w-full mx-4"
						onClick={(e) => e.stopPropagation()}
					>
						<div className="flex items-center gap-3 mb-4">
							<div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
								<AlertTriangle size={20} className="text-red-400" />
							</div>
							<div>
								<h2 className="text-lg font-bold text-white">Delete File</h2>
								<p className="text-sm text-slate-400">This action cannot be undone.</p>
							</div>
						</div>
						<p className="text-sm text-slate-300 mb-4">
							Are you sure you want to delete <strong className="text-white">{deleteTarget}</strong>?
						</p>
						<div className="flex gap-3">
							<button
								onClick={() => setDeleteTarget(null)}
								className="flex-1 py-2.5 rounded-xl border border-white/10 text-sm text-slate-400 hover:text-white"
							>
								Cancel
							</button>
							<button
								onClick={handleDelete}
								className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-sm font-bold flex items-center justify-center gap-2"
							>
								<Trash2 size={14} /> Delete
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
