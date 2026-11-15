// Gera public/og.png (1200×630), a imagem que aparece quando alguém compartilha o site
// (og:image no index.html), a partir de scripts/og.svg, com a fonte Geist do site.
//
//   npm run og
//
// Usa o Chromium do Playwright (`npx playwright install chromium`, se faltar). A imagem vai no
// repositório: rodar de novo só quando a marca ou o lema mudarem.

import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch {
  try {
    // Instalado fora do projeto (global, achado pelo NODE_PATH).
    ({ chromium } = createRequire(import.meta.url)("playwright"));
  } catch {
    console.error('Falta o Playwright: "npm i -g playwright && npx playwright install chromium".');
    process.exit(1);
  }
}

const svg = await readFile(fileURLToPath(new URL("./og.svg", import.meta.url)), "utf8");
// A fonte vai dentro da página (a página em branco do navegador não abre arquivo local).
const woff2 = await readFile(
  fileURLToPath(
    new URL(
      "../node_modules/@fontsource-variable/geist/files/geist-latin-wght-normal.woff2",
      import.meta.url,
    ),
  ),
);
const geist = `data:font/woff2;base64,${woff2.toString("base64")}`;
const saida = fileURLToPath(new URL("../public/og.png", import.meta.url));

const pagina = `<!doctype html><meta charset="utf-8"><style>
@font-face { font-family: "Geist Variable"; src: url("${geist}") format("woff2"); font-weight: 100 900; }
html, body { margin: 0; }
svg { display: block; }
</style>${svg}`;

const navegador = await chromium.launch();
const aba = await navegador.newPage({ viewport: { width: 1200, height: 630 } });
await aba.setContent(pagina, { waitUntil: "load" });
await aba.evaluate(() => document.fonts.ready);
await aba.screenshot({ path: saida, clip: { x: 0, y: 0, width: 1200, height: 630 } });
await navegador.close();
console.log(`Gravado ${saida}`);
