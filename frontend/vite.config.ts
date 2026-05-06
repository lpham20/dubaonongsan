import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8010",
      "/health": "http://127.0.0.1:8010"
    }
  },
  build: {
    target: "es2022",
    sourcemap: false,
    minify: "esbuild",
    cssMinify: "esbuild",
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/react") || id.includes("node_modules/react-dom")) {
            return "react-vendor";
          }
          if (id.includes("node_modules/recharts")) {
            return "recharts";
          }
          if (id.includes("node_modules/@phosphor-icons")) {
            return "icons";
          }
        }
      }
    }
  }
});
