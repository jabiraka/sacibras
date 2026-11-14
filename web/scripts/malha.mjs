// Gera src/mapa/ufs.json: a malha das 27 UFs, simplificada, em TopoJSON.
//
// Fonte: IBGE, Malha Territorial 2024 (shapefile das UFs, geoftp). A API de malhas do IBGE
// (servicodados) derruba a conexão de quem está fora do Brasil, e o build roda no GitHub
// Actions, nos EUA; por isso a malha é gerada aqui, uma vez, e vai no repositório (~50 KB).
// Fronteira de estado quase nunca muda: rodar de novo só quando o IBGE publicar malha nova.
//
//   npm run malha
//
// Tiradas: as ilhas oceânicas menores que 400 km² (Trindade e Martim Vaz, a 1.100 km da costa
// do ES, esticariam o mapa; Fernando de Noronha some na escala do mapa). Simplificação de
// 0,6 % dos vértices, preservando a topologia (as fronteiras vizinhas continuam encostadas).

import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import mapshaper from "mapshaper";

const URL =
  "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/" +
  "municipio_2024/Brasil/BR_UF_2024.zip";
const SAIDA = new globalThis.URL("../src/mapa/ufs.json", import.meta.url).pathname;

const pasta = await mkdtemp(join(tmpdir(), "malha-"));
const zip = join(pasta, "BR_UF_2024.zip");
console.log(`Baixando ${URL}`);
const resposta = await fetch(URL);
if (!resposta.ok) throw new Error(`IBGE respondeu HTTP ${resposta.status}`);
await writeFile(zip, Buffer.from(await resposta.arrayBuffer()));

await mapshaper.runCommands(
  [
    `-i "${zip}"`,
    "-filter-fields SIGLA_UF,AREA_KM2",
    "-rename-fields uf=SIGLA_UF,area=AREA_KM2",
    "-each 'area=Math.round(area)'",
    "-filter-islands min-area=400km2 remove-empty",
    "-simplify 0.6% keep-shapes",
    "-clean",
    "-rename-layers ufs",
    `-o "${SAIDA}" format=topojson quantization=10000`,
  ].join(" "),
);
console.log(`Gravado ${SAIDA}`);
