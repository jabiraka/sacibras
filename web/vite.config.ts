import { defineConfig } from "vite";

// O endereço do site no ar mora em scripts/endereco.mjs (também o usa o paginas.mjs).
import { ENDERECO } from "./scripts/endereco.mjs";

// base relativa: o mesmo build serve no GitHub Pages (/sacibras/) e num domínio próprio.
export default defineConfig({
  base: "./",
  build: { target: "es2022", chunkSizeWarningLimit: 900 },
  server: { port: 5173 },
  plugins: [
    {
      name: "endereco-do-site",
      transformIndexHtml: (html) => html.replaceAll("%ENDERECO%", ENDERECO),
    },
  ],
});
