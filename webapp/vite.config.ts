import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [react()],
	define: {
		"import.meta.env.VITE_API_BASE": JSON.stringify(process.env.VITE_API_BASE || ""),
	},
	build: {
		chunkSizeWarningLimit: 600,
		rollupOptions: {
			output: {
				manualChunks: {
					react: ["react", "react-dom", "react-router-dom"],
					vendor: ["framer-motion", "recharts", "three", "zustand", "lucide-react"],
				},
			},
		},
	},
	server: {
		allowedHosts: ["goliath"],
		port: 10945,
		strictPort: true,
		host: "127.0.0.1",
		proxy: {
			"/api": { target: "http://127.0.0.1:10944", changeOrigin: true },
		},
	},
});
