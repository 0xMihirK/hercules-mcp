import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

import path from "node:path";
export default defineConfig({
  base: "./",
  plugins: [react()],
  optimizeDeps: { entries: ["index.html"] },
  server: { watch: { ignored: ["**/test-results/**", "**/capture/fonts/**", "**/*.pending"] } },
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  build: { target: "es2022", sourcemap: false },
});
