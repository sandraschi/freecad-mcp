import { Box, Eye, Grid, Loader2, RotateCw, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

interface StlViewerProps {
	url: string;
	height?: number;
	showToolbar?: boolean;
}

const COLOR_PRESETS = [
	{ name: "Indigo", hex: 0x6366f1, class: "bg-indigo-500" },
	{ name: "Emerald", hex: 0x10b981, class: "bg-emerald-500" },
	{ name: "Amber", hex: 0xf59e0b, class: "bg-amber-500" },
	{ name: "Rose", hex: 0xf43f5e, class: "bg-rose-500" },
	{ name: "Silver", hex: 0x94a3b8, class: "bg-slate-400" },
];

export default function StlViewer({ url, height = 400, showToolbar = true }: StlViewerProps) {
	const containerRef = useRef<HTMLDivElement>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");

	const [wireframe, setWireframe] = useState(false);
	const [showGrid, setShowGrid] = useState(true);
	const [showBBox, setShowBBox] = useState(false);
	const [autoRotate, setAutoRotate] = useState(false);
	const [meshColor, setMeshColor] = useState(0x6366f1);
	const [bboxInfo, setBboxInfo] = useState<{ x: number; y: number; z: number; vertices: number } | null>(null);

	const meshRef = useRef<THREE.Mesh | null>(null);
	const materialRef = useRef<THREE.MeshPhongMaterial | null>(null);
	const gridRef = useRef<THREE.GridHelper | null>(null);
	const bboxHelperRef = useRef<THREE.BoxHelper | null>(null);
	const controlsRef = useRef<OrbitControls | null>(null);

	// Toggle wireframe dynamically
	useEffect(() => {
		if (materialRef.current) {
			materialRef.current.wireframe = wireframe;
		}
	}, [wireframe]);

	// Toggle grid dynamically
	useEffect(() => {
		if (gridRef.current) {
			gridRef.current.visible = showGrid;
		}
	}, [showGrid]);

	// Toggle bbox helper dynamically
	useEffect(() => {
		if (bboxHelperRef.current) {
			bboxHelperRef.current.visible = showBBox;
		}
	}, [showBBox]);

	// Toggle auto rotate dynamically
	useEffect(() => {
		if (controlsRef.current) {
			controlsRef.current.autoRotate = autoRotate;
		}
	}, [autoRotate]);

	// Update mesh color dynamically
	useEffect(() => {
		if (materialRef.current) {
			materialRef.current.color.setHex(meshColor);
		}
	}, [meshColor]);

	useEffect(() => {
		const container = containerRef.current;
		if (!container) return;

		setLoading(true);
		setError("");
		setBboxInfo(null);

		const scene = new THREE.Scene();
		scene.background = new THREE.Color("#0f0f12");

		const camera = new THREE.PerspectiveCamera(45, container.clientWidth / height, 0.1, 1000);
		camera.position.set(0, 0, 150);

		const renderer = new THREE.WebGLRenderer({ antialias: true });
		renderer.setSize(container.clientWidth, height);
		renderer.setPixelRatio(window.devicePixelRatio);
		container.appendChild(renderer.domElement);

		const controls = new OrbitControls(camera, renderer.domElement);
		controls.enableDamping = true;
		controls.autoRotateSpeed = 2.0;
		controls.autoRotate = autoRotate;
		controlsRef.current = controls;

		const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
		const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
		directionalLight1.position.set(10, 20, 15);
		const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
		directionalLight2.position.set(-10, -10, -15);
		scene.add(ambientLight, directionalLight1, directionalLight2);

		const gridHelper = new THREE.GridHelper(120, 30, 0x4f46e5, 0x1e1b4b);
		gridHelper.visible = showGrid;
		scene.add(gridHelper);
		gridRef.current = gridHelper;

		const loader = new STLLoader();
		let animId: number;

		loader.load(
			url,
			(geometry) => {
				geometry.computeVertexNormals();
				geometry.center();

				const material = new THREE.MeshPhongMaterial({
					color: meshColor,
					specular: 0x222222,
					shininess: 35,
					wireframe: wireframe,
				});
				materialRef.current = material;

				const mesh = new THREE.Mesh(geometry, material);
				scene.add(mesh);
				meshRef.current = mesh;

				const bboxHelper = new THREE.BoxHelper(mesh, 0x38bdf8);
				bboxHelper.visible = showBBox;
				scene.add(bboxHelper);
				bboxHelperRef.current = bboxHelper;

				const box = new THREE.Box3().setFromObject(mesh);
				const center = box.getCenter(new THREE.Vector3());
				const size = box.getSize(new THREE.Vector3());
				const maxDim = Math.max(size.x, size.y, size.z);

				setBboxInfo({
					x: Math.round(size.x * 10) / 10,
					y: Math.round(size.y * 10) / 10,
					z: Math.round(size.z * 10) / 10,
					vertices: geometry.attributes.position ? geometry.attributes.position.count : 0,
				});

				camera.position.set(center.x + maxDim * 1.6, center.y + maxDim * 1.2, center.z + maxDim * 1.6);
				camera.lookAt(center);
				controls.target.copy(center);
				controls.update();
				setLoading(false);
			},
			undefined,
			() => {
				setError("Failed to load STL model");
				setLoading(false);
			},
		);

		const animate = () => {
			animId = requestAnimationFrame(animate);
			controls.update();
			renderer.render(scene, camera);
		};
		animate();

		const handleResize = () => {
			if (!container) return;
			camera.aspect = container.clientWidth / height;
			camera.updateProjectionMatrix();
			renderer.setSize(container.clientWidth, height);
		};
		window.addEventListener("resize", handleResize);

		return () => {
			window.removeEventListener("resize", handleResize);
			cancelAnimationFrame(animId);
			renderer.dispose();
			controls.dispose();
			if (container.contains(renderer.domElement)) {
				container.removeChild(renderer.domElement);
			}
		};
	}, [url, height]);

	return (
		<div
			className="relative rounded-2xl overflow-hidden bg-[#0f0f12] border border-white/10 shadow-xl"
			style={{ height }}
		>
			<div ref={containerRef} className="w-full h-full" />

			{/* Loading Overlay */}
			{loading && (
				<div className="absolute inset-0 flex items-center justify-center bg-[#0f0f12]/80 backdrop-blur-sm z-10">
					<div className="flex flex-col items-center gap-3">
						<Loader2 className="animate-spin text-indigo-400" size={36} />
						<span className="text-slate-300 text-sm font-medium">Rendering 3D Model...</span>
					</div>
				</div>
			)}

			{/* Error Overlay */}
			{error && (
				<div className="absolute inset-0 flex items-center justify-center bg-[#0f0f12]/90 z-10">
					<div className="flex flex-col items-center gap-2 text-rose-400">
						<Box size={36} />
						<span className="text-sm font-semibold">{error}</span>
					</div>
				</div>
			)}

			{/* Interactive Controls Overlay */}
			{!loading && !error && showToolbar && (
				<>
					<div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/60 backdrop-blur-md border border-white/10 p-1.5 rounded-xl text-xs z-10">
						<button
							onClick={() => setWireframe(!wireframe)}
							title="Toggle Wireframe"
							className={`p-1.5 rounded-lg transition ${wireframe ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white hover:bg-white/10"}`}
						>
							<Eye size={14} />
						</button>
						<button
							onClick={() => setShowGrid(!showGrid)}
							title="Toggle Grid"
							className={`p-1.5 rounded-lg transition ${showGrid ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white hover:bg-white/10"}`}
						>
							<Grid size={14} />
						</button>
						<button
							onClick={() => setShowBBox(!showBBox)}
							title="Toggle Bounding Box"
							className={`p-1.5 rounded-lg transition ${showBBox ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white hover:bg-white/10"}`}
						>
							<Square size={14} />
						</button>
						<button
							onClick={() => setAutoRotate(!autoRotate)}
							title="Toggle Auto Rotate"
							className={`p-1.5 rounded-lg transition ${autoRotate ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white hover:bg-white/10"}`}
						>
							<RotateCw size={14} />
						</button>
						<div className="h-4 w-[1px] bg-white/10 mx-1" />
						<div className="flex items-center gap-1">
							{COLOR_PRESETS.map((c) => (
								<button
									key={c.name}
									onClick={() => setMeshColor(c.hex)}
									title={c.name}
									className={`w-3.5 h-3.5 rounded-full ${c.class} transition transform hover:scale-125 ${meshColor === c.hex ? "ring-2 ring-white" : "opacity-70"}`}
								/>
							))}
						</div>
					</div>

					{/* Model Statistics Overlay */}
					{bboxInfo && (
						<div className="absolute bottom-3 right-3 bg-black/60 backdrop-blur-md border border-white/10 px-3 py-1.5 rounded-xl text-[11px] font-mono text-slate-300 z-10 space-y-0.5">
							<div>
								Bounds: {bboxInfo.x} × {bboxInfo.y} × {bboxInfo.z} mm
							</div>
							<div className="text-slate-500">Vertices: {bboxInfo.vertices.toLocaleString()}</div>
						</div>
					)}
				</>
			)}
		</div>
	);
}
