import { defineConfig } from "vite";

// base relativa: o mesmo build serve no GitHub Pages (/sacibras/) e num domínio próprio.
export default defineConfig({
  base: "./",
  build: { target: "es2022", chunkSizeWarningLimit: 900 },
  server: { port: 5173 },
});
