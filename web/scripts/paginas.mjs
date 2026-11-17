// As páginas que o buscador acha (aprendido no finjabs, M131 de 10/11/2026): o site abre tudo
// por "#pergunta/juro-alto", e o Google não indexa o que vem depois do "#" — para ele, o site é
// uma página só, com o título "status da economia brasileira". Como o gancho é a pergunta que
// as pessoas buscam (Caio, 16/11/2026), cada pergunta e cada assunto ganham um endereço de
// verdade, com título, descrição, canônico e a prévia do link:
//
//   dist/pergunta/<id>/index.html   "Por que o juro é tão alto? · sacibras"
//   dist/<assunto>/index.html       "Inflação · sacibras"
//   dist/sitemap.xml, dist/robots.txt
//
// Cada página é o mesmo index.html do site, com a cabeça trocada e um `<base>` que aponta para a
// raiz (os arquivos e o `data/` são relativos). Ao abrir, ela põe o "#pergunta/<id>" e o site
// desenha a pergunta como sempre. Os elos de dentro ("#inflacao") seguem na mesma página, sem
// recarregar (o `<base>` os mandaria à raiz).
//
// Roda depois do `vite build` (`npm run build`), lendo o `dist/data/` que o builder gerou. Sem os
// JSONs (o build só da tela, sem rodar o builder), sai só o sitemap da raiz, com um aviso.

import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { ENDERECO } from "./endereco.mjs";

const DIST = fileURLToPath(new URL("../dist/", import.meta.url));
const MARCA = "sacibras";

const escapar = (s) =>
  s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

/** Até `n` letras, cortando na palavra (o Google mostra uns 155). */
export function resumir(texto, n = 158) {
  const limpo = texto.replace(/\s+/g, " ").trim();
  if (limpo.length <= n) return limpo;
  const corte = limpo.slice(0, n - 1);
  return `${corte.slice(0, corte.lastIndexOf(" ")).replace(/[,;:.]$/, "")}…`;
}

/** O index.html com a cabeça de uma página. */
export function pagina(html, { caminho, titulo, descricao, texto = descricao, hash, profundidade }) {
  const url = ENDERECO + caminho;
  const t = escapar(`${titulo} · ${MARCA}`);
  const d = escapar(descricao);
  const base = "../".repeat(profundidade);
  const trocar = (re, novo) => {
    if (!re.test(html)) throw new Error(`index.html sem ${re}: a página de ${caminho} sairia errada`);
    html = html.replace(re, novo);
  };
  trocar(/<title>[^<]*<\/title>/, `<title>${t}</title>`);
  trocar(/(<meta\s+name="description"\s+content=")[^"]*(")/, `$1${d}$2`);
  trocar(/(<meta\s+property="og:title"\s+content=")[^"]*(")/, `$1${t}$2`);
  trocar(/(<meta\s+property="og:description"\s+content=")[^"]*(")/, `$1${d}$2`);
  trocar(/(<meta\s+property="og:url"\s+content=")[^"]*(")/, `$1${url}$2`);
  // O <base> vem antes de qualquer arquivo relativo; o roteiro roda antes do site.
  const cabeca = [
    `<base href="${base}" />`,
    `<link rel="canonical" href="${url}" />`,
    "<script>",
    `if (!location.hash) history.replaceState(null, "", location.pathname + location.search + "#${hash}");`,
    "document.addEventListener(\"click\", (e) => {",
    "  const a = e.target instanceof Element ? e.target.closest(\"a[href^='#']\") : null;",
    "  if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;",
    "  e.preventDefault();",
    "  location.hash = a.getAttribute(\"href\");",
    "}, true);",
    "</script>",
  ].join("\n    ");
  trocar(/<meta charset="utf-8" \/>/, `<meta charset="utf-8" />\n    ${cabeca}`);
  // Quem lê sem JavaScript (e o buscador, antes de rodar o site) vê a pergunta e a resposta.
  trocar(
    /<body>/,
    `<body>\n    <noscript><h1>${escapar(titulo)}</h1><p>${escapar(texto)}</p></noscript>`,
  );
  return html;
}

export function sitemap(urls, data) {
  const linhas = urls.map(
    (u) => `  <url><loc>${escapar(ENDERECO + u)}</loc>${data ? `<lastmod>${data}</lastmod>` : ""}</url>`,
  );
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...linhas,
    "</urlset>",
    "",
  ].join("\n");
}

async function lerJson(nome) {
  const arquivo = `${DIST}data/${nome}`;
  return existsSync(arquivo) ? JSON.parse(await readFile(arquivo, "utf8")) : null;
}

async function main() {
  const html = await readFile(`${DIST}index.html`, "utf8");
  const painel = await lerJson("painel.json");
  const perguntas = await lerJson("perguntas.json");
  const urls = [""];
  const data = painel?.gerado_em?.slice(0, 10);

  if (!painel || !perguntas) {
    console.warn("páginas: sem dist/data/painel.json ou perguntas.json (rode o builder); só o sitemap da raiz");
  } else {
    for (const p of perguntas.perguntas) {
      const caminho = `pergunta/${p.id}/`;
      await mkdir(`${DIST}${caminho}`, { recursive: true });
      const texto = pagina(html, {
        caminho,
        titulo: p.titulo,
        descricao: resumir(p.resposta),
        texto: p.resposta,
        hash: `pergunta/${p.id}`,
        profundidade: 2,
      });
      await writeFile(`${DIST}${caminho}index.html`, texto);
      urls.push(caminho);
    }
    const ocupados = new Set(["assets", "data", "pergunta"]);
    for (const s of painel.secoes) {
      if (s.id === "resumo" || !s.ok || ocupados.has(s.id) || !/^[a-z0-9-]+$/.test(s.id)) continue;
      const caminho = `${s.id}/`;
      await mkdir(`${DIST}${caminho}`, { recursive: true });
      const texto = pagina(html, {
        caminho,
        titulo: s.titulo,
        descricao: resumir(s.resumo || `${s.titulo} do Brasil, com fonte oficial e data.`),
        hash: s.id,
        profundidade: 1,
      });
      await writeFile(`${DIST}${caminho}index.html`, texto);
      urls.push(caminho);
    }
  }

  await writeFile(`${DIST}sitemap.xml`, sitemap(urls, data));
  await writeFile(`${DIST}robots.txt`, `User-agent: *\nAllow: /\n\nSitemap: ${ENDERECO}sitemap.xml\n`);
  console.log(`páginas: ${urls.length - 1} com endereço próprio, mais a raiz, no sitemap.xml`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await main();
