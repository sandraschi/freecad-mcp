import { Box, CheckCircle2, Cog, Download, FileText, Layers, Loader2, Sparkles, Wrench } from "lucide-react";
import { useState } from "react";
import StlViewer from "../components/StlViewer";
import { API_BASE } from "../lib/api";

type PartCategory = "gear" | "fastener" | "sketch" | "techdraw" | "generative" | "primitive";

export default function PartsPage() {
	const [category, setCategory] = useState<PartCategory>("gear");

	// Gear State
	const [gearType, setGearType] = useState("spur");
	const [numTeeth, setNumTeeth] = useState(20);
	const [moduleVal, setModuleVal] = useState(2.0);
	const [faceWidth, setFaceWidth] = useState(10.0);
	const [boreDia, setBoreDia] = useState(8.0);

	// Fastener State
	const [fastenerType, setFastenerType] = useState("bolt");
	const [fastenerSize, setFastenerSize] = useState("M6");
	const [fastenerLength, setFastenerLength] = useState(20.0);

	// Sketcher State
	const [sketchType, setSketchType] = useState("rectangle_with_hole");
	const [sketchWidth, setSketchWidth] = useState(60.0);
	const [sketchHeight, setSketchHeight] = useState(40.0);
	const [sketchHoleDia, setSketchHoleDia] = useState(12.0);
	const [sketchExtrude, setSketchExtrude] = useState(15.0);

	// TechDraw State
	const [techdrawScale, setTechdrawScale] = useState(1.0);
	const [techdrawFile, setTechdrawFile] = useState("box_part.stl");

	// Generative State
	const [genReductionPct, setGenReductionPct] = useState(35.0);
	const [genWallThickness, setGenWallThickness] = useState(3.0);
	const [genPocketPattern, setGenPocketPattern] = useState("honeycomb");

	// Primitive State
	const [primitiveType, setPrimitiveType] = useState("box");
	const [primWidth, setPrimWidth] = useState(40.0);
	const [primHeight, setPrimHeight] = useState(20.0);
	const [primDepth, setPrimDepth] = useState(30.0);
	const [primRadius, setPrimRadius] = useState(15.0);

	// Status & Output
	const [loading, setLoading] = useState(false);
	const [stlUrl, setStlUrl] = useState<string | null>(null);
	const [outputName, setOutputName] = useState<string | null>(null);
	const [resultData, setResultData] = useState<any>(null);
	const [error, setError] = useState<string | null>(null);
	const [savedToDepot, setSavedToDepot] = useState(false);

	const handleGenerate = async () => {
		setLoading(true);
		setError(null);
		setStlUrl(null);
		setResultData(null);
		setSavedToDepot(false);

		let payload: any = { execution_mode: "hands_off" };
		let fileName = "model.stl";

		if (category === "gear") {
			fileName = `${gearType}_gear_m${moduleVal}_t${numTeeth}.stl`;
			payload = {
				tool: "freecad_model",
				arguments: {
					operation: "gear",
					gear_type: gearType,
					num_teeth: numTeeth,
					module: moduleVal,
					face_width_mm: faceWidth,
					bore_diameter_mm: boreDia,
					output_name: fileName,
				},
			};
		} else if (category === "fastener") {
			fileName = `${fastenerSize}_${fastenerType}_${fastenerLength}mm.stl`;
			payload = {
				tool: "freecad_model",
				arguments: {
					operation: "fastener",
					fastener_type: fastenerType,
					size: fastenerSize,
					length_mm: fastenerLength,
					output_name: fileName,
				},
			};
		} else if (category === "sketch") {
			fileName = `sketch_${sketchType}_${sketchWidth}x${sketchHeight}.stl`;
			payload = {
				tool: "freecad_model",
				arguments: {
					operation: "sketch",
					sketch_type: sketchType,
					width_mm: sketchWidth,
					height_mm: sketchHeight,
					hole_diameter_mm: sketchHoleDia,
					extrude_height_mm: sketchExtrude,
					output_name: fileName,
				},
			};
		} else if (category === "techdraw") {
			fileName = "blueprint.svg";
			payload = {
				tool: "freecad_model",
				arguments: {
					operation: "techdraw",
					file_name: techdrawFile || "box_part.stl",
					scale: techdrawScale,
					output_name: fileName,
				},
			};
		} else if (category === "generative") {
			fileName = `opt_weight_${genReductionPct}pct.stl`;
			payload = {
				tool: "freecad_model",
				arguments: {
					operation: "generative",
					file_name: techdrawFile || "box_part.stl",
					target_reduction_pct: genReductionPct,
					wall_thickness_mm: genWallThickness,
					pocket_pattern: genPocketPattern,
					output_name: fileName,
				},
			};
		} else {
			fileName = `${primitiveType}_part.stl`;
			const p: any = {};
			if (primitiveType === "box") {
				p.width = primWidth;
				p.height = primHeight;
				p.depth = primDepth;
			} else {
				p.radius = primRadius;
				p.height = primHeight;
			}
			payload = {
				tool: "freecad_model",
				arguments: {
					operation: "create_primitive",
					primitive_type: primitiveType,
					params: p,
					output_name: fileName,
				},
			};
		}

		try {
			const res = await fetch(API_BASE + "/api/v1/control/tool", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(payload),
			});
			const data = await res.json();

			if (data.success && data.result?.data) {
				setResultData(data.result.data);
				const outName = data.result.output || fileName;
				setOutputName(outName);
				setStlUrl(`${API_BASE}/api/v1/files/output/${outName}?t=${Date.now()}`);
			} else {
				setError(data.error || data.result?.error || "Failed to generate parametric model");
			}
		} catch (err: any) {
			setError(err.message || "Network error generating model");
		} finally {
			setLoading(false);
		}
	};

	const handleSaveToDepot = async () => {
		if (!outputName) return;
		try {
			const res = await fetch(API_BASE + "/api/v1/control/tool", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					tool: "depot_add_file",
					arguments: {
						source_path: outputName,
						title: outputName.replace(".stl", "").replace(/_/g, " "),
						category: category,
						tags: [category, "parametric", "3d-print"],
					},
				}),
			});
			const d = await res.json();
			if (d.success || d.result?.success) {
				setSavedToDepot(true);
			}
		} catch {
			// ignore
		}
	};

	return (
		<div className="space-y-6 animate-in fade-in pb-12">
			{/* Header */}
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-bold text-white flex items-center gap-2">
						<Cog className="text-indigo-400" size={26} /> Parts & Fasteners Studio
					</h1>
					<p className="text-slate-400 text-sm">
						Generate 3D parametric gears, metric ISO fasteners, and primitives in real-time with mass properties.
					</p>
				</div>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
				{/* Parametric Controls Column */}
				<div className="lg:col-span-5 space-y-5">
					{/* Category Tabs */}
					<div className="flex bg-[#0f0f12] border border-white/10 p-1.5 rounded-2xl gap-1">
						<button
							type="button"
							onClick={() => setCategory("gear")}
							className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
								category === "gear"
									? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
									: "text-slate-400 hover:text-white"
							}`}
						>
							<Cog size={14} /> Gears
						</button>
						<button
							type="button"
							onClick={() => setCategory("fastener")}
							className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
								category === "fastener"
									? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
									: "text-slate-400 hover:text-white"
							}`}
						>
							<Wrench size={14} /> Fasteners
						</button>
						<button
							type="button"
							onClick={() => setCategory("sketch")}
							className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
								category === "sketch"
									? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
									: "text-slate-400 hover:text-white"
							}`}
						>
							<Layers size={14} /> 2D Sketch
						</button>
						<button
							type="button"
							onClick={() => setCategory("techdraw")}
							className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
								category === "techdraw"
									? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
									: "text-slate-400 hover:text-white"
							}`}
						>
							<FileText size={14} /> Blueprint
						</button>
						<button
							type="button"
							onClick={() => setCategory("generative")}
							className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
								category === "generative"
									? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
									: "text-slate-400 hover:text-white"
							}`}
						>
							<Sparkles size={14} /> Generative
						</button>
						<button
							type="button"
							onClick={() => setCategory("primitive")}
							className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
								category === "primitive"
									? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
									: "text-slate-400 hover:text-white"
							}`}
						>
							<Box size={14} /> Primitives
						</button>
					</div>

					{/* Form Parameters Box */}
					<div className="bg-[#0f0f12] border border-white/10 rounded-2xl p-5 space-y-4">
						{category === "sketch" && (
							<>
								<h3 className="text-sm font-semibold text-white border-b border-white/5 pb-2">
									Parametric 2D Sketch Extruder
								</h3>
								<div className="grid grid-cols-2 gap-3">
									<div>
										<label className="text-xs text-slate-400 block mb-1">Sketch Type</label>
										<select
											value={sketchType}
											onChange={(e) => setSketchType(e.target.value)}
											className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
										>
											<option value="rectangle_with_hole">Rectangle with Hole</option>
											<option value="flange">Flange Plate</option>
											<option value="slot">Slotted Plate</option>
										</select>
									</div>
									<div>
										<label className="text-xs text-slate-400 block mb-1">Width: {sketchWidth}mm</label>
										<input
											type="range"
											min={20}
											max={200}
											value={sketchWidth}
											onChange={(e) => setSketchWidth(parseFloat(e.target.value))}
											className="w-full accent-indigo-500"
										/>
									</div>
									<div>
										<label className="text-xs text-slate-400 block mb-1">Height: {sketchHeight}mm</label>
										<input
											type="range"
											min={15}
											max={150}
											value={sketchHeight}
											onChange={(e) => setSketchHeight(parseFloat(e.target.value))}
											className="w-full accent-indigo-500"
										/>
									</div>
									<div>
										<label className="text-xs text-slate-400 block mb-1">Extrude Height: {sketchExtrude}mm</label>
										<input
											type="range"
											min={2}
											max={100}
											value={sketchExtrude}
											onChange={(e) => setSketchExtrude(parseFloat(e.target.value))}
											className="w-full accent-indigo-500"
										/>
									</div>
								</div>
							</>
						)}

						{category === "techdraw" && (
							<>
								<h3 className="text-sm font-semibold text-white border-b border-white/5 pb-2">
									TechDraw 2D Engineering Blueprint
								</h3>
								<div className="space-y-3">
									<div>
										<label className="text-xs text-slate-400 block mb-1">Target Part File</label>
										<input
											type="text"
											value={techdrawFile}
											onChange={(e) => setTechdrawFile(e.target.value)}
											placeholder="box_part.stl or bracket.step"
											className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white font-mono"
										/>
									</div>
									<div>
										<label className="text-xs text-slate-400 block mb-1">Drawing View Scale: {techdrawScale}x</label>
										<input
											type="range"
											min={0.25}
											max={3.0}
											step={0.25}
											value={techdrawScale}
											onChange={(e) => setTechdrawScale(parseFloat(e.target.value))}
											className="w-full accent-indigo-500"
										/>
									</div>
								</div>
							</>
						)}

						{category === "generative" && (
							<>
								<h3 className="text-sm font-semibold text-white border-b border-white/5 pb-2">
									Generative Weight Optimization
								</h3>
								<div className="space-y-3">
									<div>
										<label className="text-xs text-slate-400 block mb-1">
											Target Weight Reduction: {genReductionPct}%
										</label>
										<input
											type="range"
											min={10}
											max={60}
											step={5}
											value={genReductionPct}
											onChange={(e) => setGenReductionPct(parseFloat(e.target.value))}
											className="w-full accent-indigo-500"
										/>
									</div>
									<div>
										<label className="text-xs text-slate-400 block mb-1">Wall Thickness: {genWallThickness}mm</label>
										<input
											type="range"
											min={1.0}
											max={10.0}
											step={0.5}
											value={genWallThickness}
											onChange={(e) => setGenWallThickness(parseFloat(e.target.value))}
											className="w-full accent-indigo-500"
										/>
									</div>
									<div>
										<label className="text-xs text-slate-400 block mb-1">Pocketing Pattern</label>
										<select
											value={genPocketPattern}
											onChange={(e) => setGenPocketPattern(e.target.value)}
											className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
										>
											<option value="honeycomb">Honeycomb Lattice</option>
											<option value="grid">Grid Ribs</option>
											<option value="hollow">Hollow Shell</option>
										</select>
									</div>
								</div>
							</>
						)}
						{category === "gear" && (
							<>
								<h3 className="text-sm font-semibold text-white border-b border-white/5 pb-2">Gear Parameters</h3>
								<div className="grid grid-cols-2 gap-3">
									<div>
										<label className="text-xs text-slate-400 block mb-1">Gear Type</label>
										<select
											value={gearType}
											onChange={(e) => setGearType(e.target.value)}
											className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
										>
											<option value="spur">Spur Gear</option>
											<option value="helical">Helical Gear</option>
										</select>
									</div>
									<div>
										<label className="text-xs text-slate-400 block mb-1">Tooth Count ({numTeeth})</label>
										<input
											type="range"
											min={6}
											max={60}
											value={numTeeth}
											onChange={(e) => setNumTeeth(parseInt(e.target.value))}
											className="w-full accent-indigo-500"
										/>
									</div>
									<div>
										<label className="text-xs text-slate-400 block mb-1">Module (mm)</label>
										<input
											type="number"
											step="0.5"
											min="0.5"
											max="10"
											value={moduleVal}
											onChange={(e) => setModuleVal(parseFloat(e.target.value) || 1.0)}
											className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
										/>
									</div>
									<div>
										<label className="text-xs text-slate-400 block mb-1">Face Width (mm)</label>
										<input
											type="number"
											min="2"
											max="100"
											value={faceWidth}
											onChange={(e) => setFaceWidth(parseFloat(e.target.value) || 5.0)}
											className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
										/>
									</div>
								</div>
								<div>
									<label className="text-xs text-slate-400 block mb-1">Center Bore Diameter (mm)</label>
									<input
										type="number"
										min="0"
										max="50"
										value={boreDia}
										onChange={(e) => setBoreDia(parseFloat(e.target.value) || 0)}
										className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
									/>
								</div>
								<div className="text-[11px] text-indigo-400/80 bg-indigo-500/10 p-2.5 rounded-xl">
									Pitch Diameter: <span className="font-bold text-white">{(numTeeth * moduleVal).toFixed(1)} mm</span>
								</div>
							</>
						)}

						{category === "fastener" && (
							<>
								<h3 className="text-sm font-semibold text-white border-b border-white/5 pb-2">
									ISO Fastener Specifications
								</h3>
								<div className="grid grid-cols-2 gap-3">
									<div>
										<label className="text-xs text-slate-400 block mb-1">Fastener Type</label>
										<select
											value={fastenerType}
											onChange={(e) => setFastenerType(e.target.value)}
											className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
										>
											<option value="bolt">Hex Bolt</option>
											<option value="nut">Hex Nut</option>
											<option value="washer">Washer</option>
										</select>
									</div>
									<div>
										<label className="text-xs text-slate-400 block mb-1">Metric Size</label>
										<select
											value={fastenerSize}
											onChange={(e) => setFastenerSize(e.target.value)}
											className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
										>
											{["M3", "M4", "M5", "M6", "M8", "M10", "M12"].map((s) => (
												<option key={s} value={s}>
													{s}
												</option>
											))}
										</select>
									</div>
								</div>
								{fastenerType === "bolt" && (
									<div>
										<label className="text-xs text-slate-400 block mb-1">Thread Length (mm)</label>
										<input
											type="number"
											min="5"
											max="150"
											value={fastenerLength}
											onChange={(e) => setFastenerLength(parseFloat(e.target.value) || 10)}
											className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
										/>
									</div>
								)}
							</>
						)}

						{category === "primitive" && (
							<>
								<h3 className="text-sm font-semibold text-white border-b border-white/5 pb-2">Primitive Geometry</h3>
								<div>
									<label className="text-xs text-slate-400 block mb-1">Primitive Type</label>
									<select
										value={primitiveType}
										onChange={(e) => setPrimitiveType(e.target.value)}
										className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
									>
										<option value="box">Box</option>
										<option value="cylinder">Cylinder</option>
										<option value="sphere">Sphere</option>
										<option value="cone">Cone</option>
									</select>
								</div>
								{primitiveType === "box" ? (
									<div className="grid grid-cols-3 gap-2">
										<div>
											<label className="text-xs text-slate-400 block mb-1">Width (X)</label>
											<input
												type="number"
												value={primWidth}
												onChange={(e) => setPrimWidth(parseFloat(e.target.value) || 10)}
												className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none"
											/>
										</div>
										<div>
											<label className="text-xs text-slate-400 block mb-1">Height (Y)</label>
											<input
												type="number"
												value={primHeight}
												onChange={(e) => setPrimHeight(parseFloat(e.target.value) || 10)}
												className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none"
											/>
										</div>
										<div>
											<label className="text-xs text-slate-400 block mb-1">Depth (Z)</label>
											<input
												type="number"
												value={primDepth}
												onChange={(e) => setPrimDepth(parseFloat(e.target.value) || 10)}
												className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none"
											/>
										</div>
									</div>
								) : (
									<div className="grid grid-cols-2 gap-3">
										<div>
											<label className="text-xs text-slate-400 block mb-1">Radius (mm)</label>
											<input
												type="number"
												value={primRadius}
												onChange={(e) => setPrimRadius(parseFloat(e.target.value) || 10)}
												className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none"
											/>
										</div>
										{primitiveType !== "sphere" && (
											<div>
												<label className="text-xs text-slate-400 block mb-1">Height (mm)</label>
												<input
													type="number"
													value={primHeight}
													onChange={(e) => setPrimHeight(parseFloat(e.target.value) || 10)}
													className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none"
												/>
											</div>
										)}
									</div>
								)}
							</>
						)}

						{/* Action Button */}
						<button
							type="button"
							onClick={handleGenerate}
							disabled={loading}
							className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2 transition disabled:opacity-50"
						>
							{loading ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
							{loading ? "Generating Geometry..." : "Generate 3D Part"}
						</button>
					</div>
				</div>

				{/* 3D Viewport Column */}
				<div className="lg:col-span-7 space-y-4">
					{error && (
						<div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-2xl text-sm font-medium">
							{error}
						</div>
					)}

					{stlUrl ? (
						<div className="space-y-4">
							<StlViewer url={stlUrl} height={420} />

							{/* Download & Depot Action Bar */}
							<div className="flex items-center justify-between bg-[#0f0f12] border border-white/10 p-3 rounded-2xl">
								<div className="text-xs text-slate-300 font-mono truncate max-w-[240px]">{outputName}</div>
								<div className="flex items-center gap-2">
									<button
										type="button"
										onClick={handleSaveToDepot}
										disabled={savedToDepot}
										className={`px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition ${
											savedToDepot
												? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
												: "bg-white/5 hover:bg-white/10 text-white"
										}`}
									>
										{savedToDepot ? <CheckCircle2 size={14} /> : <Box size={14} />}
										{savedToDepot ? "Saved to Depot" : "Add to Depot"}
									</button>
									<a
										href={stlUrl}
										download={outputName || "part.stl"}
										className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 transition shadow-md shadow-indigo-600/20"
									>
										<Download size={14} /> Download STL
									</a>
								</div>
							</div>

							{/* Mass Properties Card */}
							{resultData?.volume_mm3 && (
								<div className="bg-[#0f0f12] border border-white/10 rounded-2xl p-4 grid grid-cols-3 gap-3 text-xs">
									<div className="bg-black/30 p-3 rounded-xl">
										<span className="text-slate-400 block text-[10px]">Volume</span>
										<span className="text-white font-bold font-mono text-sm">
											{resultData.volume_mm3.toLocaleString()} mm³
										</span>
									</div>
									<div className="bg-black/30 p-3 rounded-xl">
										<span className="text-slate-400 block text-[10px]">Mass (Steel 7.85g/cm³)</span>
										<span className="text-emerald-400 font-bold font-mono text-sm">
											{((resultData.volume_mm3 * 7.85) / 1000).toFixed(1)} g
										</span>
									</div>
									<div className="bg-black/30 p-3 rounded-xl">
										<span className="text-slate-400 block text-[10px]">Mass (PLA 1.24g/cm³)</span>
										<span className="text-amber-400 font-bold font-mono text-sm">
											{((resultData.volume_mm3 * 1.24) / 1000).toFixed(1)} g
										</span>
									</div>
								</div>
							)}
						</div>
					) : (
						<div className="h-[420px] rounded-2xl bg-[#0f0f12] border border-white/5 flex flex-col items-center justify-center text-slate-500 gap-3">
							<Cog size={48} className="text-slate-700 animate-spin-slow" />
							<span className="text-sm font-medium">Select parameters and click "Generate 3D Part"</span>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
