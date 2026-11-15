import { defineConfig } from "vite";

// O endereço do site no ar, num lugar só: a imagem de compartilhamento (og:image e og:url no
// index.html) pede o endereço completo. Quando o domínio próprio sair (depende do Caio), muda
// aqui e em `anterior.SITE`, no builder.
const ENDERECO = "https://jabiraka.github.io/sacibras/";

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
