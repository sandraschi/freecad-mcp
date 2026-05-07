import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 10945,
    strictPort: true,
    host: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:10944", changeOrigin: true },
    },
  },
});
