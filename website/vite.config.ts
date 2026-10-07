import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  optimizeDeps: { entries: ["index.html"] },
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  build: { target: "es2022", sourcemap: false },
});
