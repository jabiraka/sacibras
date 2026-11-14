"""Global Revenue Statistics da OCDE (`sdmx.oecd.org`), CSV, sem chave.

A carga tributária de ~145 países no mesmo método (o "Revenue Statistics" da OCDE, com a
classificação de tributos dela), por base de incidência, para o governo geral e cada esfera.
Conferido em 14/11/2026: o Brasil vai até 2024 (33,7 % do PIB no governo geral); a maioria
dos países, até 2023. Agregados: OECD_REP (média dos países da OCDE), A9 (América Latina e
Caribe), F (África), SO (Ásia e Pacífico).

Dimensões da chave: REF_AREA.MEASURE.SECTOR.STANDARD_REVENUE.CTRY_SPECIFIC_REVENUE.
UNIT_MEASURE.FREQ.
"""

from __future__ import annotations

import csv
import io

from sacibras.rede import baixar

BASE = "https://sdmx.oecd.org/public/rest/data/OECD.CTP.TPS,DSD_REV_COMP_GLOBAL@DF_RSGLOBAL,"
FONTE = "OCDE, Global Revenue Statistics"

# Código da OCDE -> nome curto. As bases somam o total (_T); 6000 é quase zero no Brasil.
BASES = {
    "T_1000": "Renda e lucro",
    "T_2000": "Contribuições sociais",
    "T_3000": "Folha de pagamento",
    "T_4000": "Patrimônio",
    "T_5000": "Bens e serviços",
    "T_6000": "Outros",
}
ESFERAS = {
    "S1311": "União",
    "S1312": "Estados",
    "S1313": "Municípios",
    "S1314": "Previdência",
}
"""Na OCDE, as contribuições ao INSS ficam em "fundos de seguridade social" (S1314)."""

PorAno = dict[int, float]
Tabela = dict[tuple[str, str, str], PorAno]
"""{(país, setor, categoria): {ano: % do PIB}}."""


def ler_csv(texto: str) -> Tabela:
    saida: Tabela = {}
    for linha in csv.DictReader(io.StringIO(texto)):
        valor = linha.get("OBS_VALUE") or ""
        if valor in ("", "NaN"):
            continue
        chave = (linha["REF_AREA"], linha["SECTOR"], linha["STANDARD_REVENUE"])
        saida.setdefault(chave, {})[int(linha["TIME_PERIOD"])] = float(valor)
    return saida


def carga(
    paises: list[str] | None = None,
    setores: list[str] | None = None,
    categorias: list[str] | None = None,
    inicio: int = 2000,
) -> Tabela:
    """Receita tributária em % do PIB. Lista vazia ou `None` traz todos (a chave vazia)."""
    chave = ".".join(
        [
            "+".join(paises or []),
            "TAX_REV",
            "+".join(setores or ["S13"]),
            "+".join(categorias or ["_T", *BASES]),
            "_T",
            "PT_B1GQ",
            "A",
        ]
    )
    corpo = baixar(
        BASE + "/" + chave,
        params={"startPeriod": str(inicio), "format": "csvfile"},
        validade=24 * 3600,
        tempo_limite=180,
    )
    return ler_csv(corpo.decode("utf-8-sig"))
