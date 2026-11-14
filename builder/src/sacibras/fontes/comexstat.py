"""Comércio exterior detalhado: a API do Comex Stat (MDIC), em US$ FOB.

`POST api-comexstat.mdic.gov.br/general` com JSON: fluxo (`export`/`import`), período,
detalhe (setor, produto, país…) e a métrica `metricFOB`. Conferido em 14/11/2026, com dado até
out/2026 (`/general/dates/updated`). O que se viu e o leitor trata:

- **O período é recortado mês a mês dentro de cada ano**: `2025-01` a `2026-10` traz
  janeiro a outubro de 2025 *e* de 2026, e `2025-11` a `2026-10` não traz nada. Daí os dois
  pedidos: o ano fechado (`AAAA-01` a `AAAA-12`) e o acumulado do ano (`jan` ao último mês,
  do ano passado e deste, que é a comparação no mesmo período).
- Sem `monthDetail`, uma linha por ano e item; o valor vem como texto, em dólares.
- O código do grupo da CUCI (Classificação Uniforme para o Comércio Internacional, a SITC da
  ONU) pode ter letra no fim (`222a1`, soja; `281b`, minério de ferro): os três primeiros
  dígitos são o grupo da ONU.
- O GET com cabeçalho `Origin` dá HTTP 451 de fora do Brasil; o POST sem ele responde.
- Os países vêm só pelo nome, sem código.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from sacibras.rede import FonteForaDoArError, baixar_json

URL = "https://api-comexstat.mdic.gov.br/general"
FONTE = "Ministério do Desenvolvimento, Indústria, Comércio e Serviços (MDIC), Comex Stat"
PRIMEIRO_ANO = 1997

Fluxo = Literal["export", "import"]

# O campo do código e o do nome em cada detalhe pedido.
CAMPOS: dict[str, tuple[str, str]] = {
    "ISICDivision": ("coIsicDivision", "ISICDivision"),
    "heading": ("headingCode", "heading"),
    "SITCGroup": ("coSITCGroup", "SITCGroup"),
    "country": ("country", "country"),
    "economicBlock": ("economicBlock", "economicBlock"),
}


@dataclass(frozen=True)
class Item:
    codigo: str
    nome: str


Valores = dict[Item, dict[int, float]]
"""Item → ano → US$."""


def ultimo_mes() -> date:
    """O último mês com dado publicado."""
    dados = baixar_json(f"{URL}/dates/updated")
    d = dados["data"]
    return date(int(d["year"]), int(d["monthNumber"]), 1)


def consultar(fluxo: Fluxo, detalhe: str, ano_de: int, ano_ate: int, mes_ate: int = 12) -> Valores:
    """Os valores de cada item, ano a ano, de janeiro a `mes_ate` de cada ano."""
    codigo, nome = CAMPOS[detalhe]
    corpo = {
        "flow": fluxo,
        "monthDetail": False,
        "period": {"from": f"{ano_de}-01", "to": f"{ano_ate}-{mes_ate:02d}"},
        "filters": [],
        "details": [detalhe],
        "metrics": ["metricFOB"],
    }
    resposta: Any = baixar_json(URL, metodo="POST", corpo_json=corpo, tempo_limite=120)
    linhas = (resposta.get("data") or {}).get("list") if isinstance(resposta, dict) else None
    if not linhas:
        raise FonteForaDoArError(f"Comex Stat sem linhas para {fluxo} {detalhe} {ano_de}-{ano_ate}")
    saida: Valores = {}
    for linha in linhas:
        item = Item(str(linha[codigo]), str(linha[nome]).strip())
        ano = int(linha["year"])
        saida.setdefault(item, {})[ano] = saida.get(item, {}).get(ano, 0.0) + float(
            linha["metricFOB"]
        )
    return saida


def no_ano(valores: Valores, ano: int) -> dict[Item, float]:
    """O valor de cada item num ano (sem os itens que não aparecem nele)."""
    return {item: anos[ano] for item, anos in valores.items() if ano in anos}


# ---- grupos de produtos da UNCTAD
# "UNCTAD product groupings and composition (SITC Rev. 3)", UNCTADstat, lido em 14/11/2026
# (`unctadstat.unctad.org/EN/Classifications/`, o PDF
# `DimSitcRev3Products_DsibSpecialGroupings_Hierarchy.pdf`,
# gerado em 09/09/2026): A20 "Primary commodities (SITC 0 + 1 + 2 + 3 + 4 + 68)", que se divide
# em A01 "All food items (SITC 0 + 1 + 22 + 4)", A02 "Agricultural raw materials (SITC 2 less
# 22, 27 and 28)", A03 "Ores and metals (SITC 27 + 28 + 68)" e A04 "Fuels (SITC 3)"; A12
# "Manufactured goods (SITC 5 to 8 less 667 and 68)"; A19 "Pearls, precious stones and
# non-monetary gold (SITC 667 + 971)". O resto da seção 9 (moedas, não classificados) vai em
# "outros". O Comex Stat publica a CUCI do Brasil; os grupos se leem pelos dígitos da ONU.
GRUPOS_UNCTAD: list[tuple[str, str]] = [
    ("alimentos", "Alimentos"),
    ("combustiveis", "Combustíveis"),
    ("minerios", "Minérios e metais"),
    ("agricolas", "Matérias-primas agrícolas"),
    ("manufaturados", "Manufaturados"),
    ("ouro", "Ouro, pedras e outros"),
]
COMMODITIES = ("alimentos", "combustiveis", "minerios", "agricolas")


def grupo_unctad(codigo_cuci: str) -> str:
    """O grupo da UNCTAD de um grupo da CUCI (`222a1` → alimentos)."""
    secao, divisao, grupo = codigo_cuci[:1], codigo_cuci[:2], codigo_cuci[:3]
    if secao == "3":
        return "combustiveis"
    if divisao in ("27", "28", "68"):
        return "minerios"
    if secao in ("0", "1", "4") or divisao == "22":
        return "alimentos"
    if secao == "2":
        return "agricolas"
    if grupo == "667":
        return "ouro"
    if secao in ("5", "6", "7", "8"):
        return "manufaturados"
    return "ouro"  # 971 (ouro não monetário) e o resto da seção 9


# ---- nomes curtos de setor (divisão da ISIC). Os oficiais falam "Fabricação de…" e "n.c".
SETORES_CURTOS: dict[str, str] = {
    "01": "Agropecuária (lavoura e criação)",
    "02": "Produção florestal",
    "03": "Pesca",
    "05": "Carvão mineral",
    "06": "Petróleo e gás",
    "07": "Minérios metálicos",
    "08": "Outros minerais (pedras, sal, adubos)",
    "10": "Alimentos industrializados",
    "11": "Bebidas",
    "12": "Fumo",
    "13": "Têxteis",
    "14": "Roupas",
    "15": "Couro e calçados",
    "16": "Madeira",
    "17": "Papel e celulose",
    "19": "Derivados de petróleo (refino)",
    "20": "Químicos (adubos, defensivos e outros)",
    "21": "Farmacêuticos",
    "22": "Borracha e plástico",
    "23": "Vidro, cimento e cerâmica",
    "24": "Metalurgia (aço, alumínio, ouro)",
    "25": "Produtos de metal",
    "26": "Eletrônicos e informática",
    "27": "Equipamentos elétricos",
    "28": "Máquinas e equipamentos",
    "29": "Veículos e peças",
    "30": "Aviões, navios e trens",
    "31": "Móveis",
    "32": "Outras indústrias",
}


def setor_curto(item: Item) -> str:
    """O nome de todo dia do setor, ou o oficial sem o "Fabricação de"."""
    if item.codigo in SETORES_CURTOS:
        return SETORES_CURTOS[item.codigo]
    nome = item.nome.removeprefix("Fabricação de ").removesuffix(" n.c").strip()
    return nome[:1].upper() + nome[1:]


# ---- nomes curtos de produto (posição SH4). O nome oficial passa de cem letras ("Óleos de
# petróleo ou de minerais betuminosos, exceto óleos brutos; preparações não especificadas…");
# os mais vendidos e comprados de 2023 a 2026 ganham nome de todo dia. O resto se corta.
NOMES_CURTOS: dict[str, str] = {
    "0202": "Carne bovina congelada",
    "0207": "Carne de frango",
    "0901": "Café",
    "1005": "Milho",
    "1201": "Soja em grão",
    "1701": "Açúcar",
    "2304": "Farelo de soja",
    "2601": "Minério de ferro",
    "2603": "Minério de cobre",
    "2701": "Carvão mineral",
    "2709": "Petróleo bruto",
    "2710": "Derivados de petróleo (diesel, gasolina)",
    "2711": "Gás natural e de cozinha",
    "2933": "Compostos químicos com nitrogênio",
    "3002": "Vacinas, soros e derivados do sangue",
    "3004": "Medicamentos",
    "3102": "Adubos nitrogenados",
    "3104": "Adubos de potássio",
    "3105": "Adubos mistos (NPK)",
    "3808": "Defensivos agrícolas",
    "4703": "Celulose",
    "5201": "Algodão",
    "7108": "Ouro",
    "7202": "Ferroligas",
    "7207": "Aço semiacabado",
    "8411": "Turbinas de avião e a gás",
    "8471": "Computadores",
    "8517": "Celulares e aparelhos de rede",
    "8541": "Semicondutores e placas solares",
    "8542": "Chips (circuitos integrados)",
    "8703": "Automóveis",
    "8704": "Caminhões e picapes",
    "8708": "Peças de veículos",
    "8802": "Aviões",
    "8905": "Plataformas e navios especiais",
}


def nome_curto(item: Item, limite: int = 48) -> str:
    """O nome de todo dia do produto, ou o oficial cortado no primeiro ponto e vírgula."""
    if item.codigo in NOMES_CURTOS:
        return NOMES_CURTOS[item.codigo]
    nome = item.nome.split(";")[0].strip()
    if len(nome) <= limite:
        return nome
    corte = nome[:limite].rsplit(" ", 1)[0].rstrip(",")
    return f"{corte}…"
