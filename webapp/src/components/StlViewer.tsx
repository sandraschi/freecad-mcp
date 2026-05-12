import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { Box, Loader2 } from "lucide-react";

interface StlViewerProps {
  url: string;
  height?: number;
}

export default function StlViewer({ url, height = 400 }: StlViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    setLoading(true);
    setError("");

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

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 20, 15);
    scene.add(ambientLight, directionalLight);

    const gridHelper = new THREE.GridHelper(80, 20, 0x333333, 0x1a1a1a);
    scene.add(gridHelper);

    const loader = new STLLoader();
    loader.load(
      url,
      (geometry) => {
        geometry.computeVertexNormals();
        geometry.center();

        const material = new THREE.MeshPhongMaterial({ color: 0x6366f1, specular: 0x111111, shininess: 30 });
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);

        const box = new THREE.Box3().setFromObject(mesh);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        camera.position.set(center.x + maxDim * 1.5, center.y + maxDim, center.z + maxDim * 1.5);
        camera.lookAt(center);
        controls.target.copy(center);
        controls.update();
        setLoading(false);
      },
      undefined,
      () => {
        setError("Failed to load STL");
        setLoading(false);
      },
    );

    const animate = () => {
      requestAnimationFrame(animate);
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
      renderer.dispose();
      controls.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [url, height]);

  return (
    <div className="relative rounded-xl overflow-hidden bg-[#0f0f12] border border-white/5" style={{ height }}>
      <div ref={containerRef} className="w-full h-full" />
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0f0f12]/80">
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="animate-spin text-indigo-400" size={32} />
            <span className="text-slate-400 text-sm">Loading model...</span>
          </div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0f0f12]/80">
          <div className="flex flex-col items-center gap-2 text-red-400">
            <Box size={32} />
            <span className="text-sm">{error}</span>
          </div>
        </div>
      )}
    </div>
  );
}
