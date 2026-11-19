"""Quanto o governo gasta com quem trabalha para ele, país a país e, no Brasil, por esfera:
o Government Finance Statistics do FMI (IMF.STA, GFS_SOO, a demonstração de operações).

Conferido em 19/11/2026 (Caio: *"inclua a distribuição dos gastos por servidores públicos
(quem fica com mais)"*): anual, em % do PIB (POGDP_PT) e em moeda do país (XDC, em unidades),
105 países com a remuneração de empregados do governo geral, o Brasil até 2025.

- `G21_T`, remuneração de empregados: salários (`G211_T`) e a contribuição do governo como
  patrão (`G212_T`). É a folha de quem está na ativa.
- `G273_T`, benefícios sociais do empregador: no Brasil, as aposentadorias e pensões dos
  servidores (os regimes próprios), que o FMI conta como benefício social, não como folha.

Setores: `S13` governo geral; no Brasil, `S1311B` governo central (a União), `S1312MIXED`
estados e `S1313MIXED` municípios. As três esferas somam o governo geral (conferido em
19/11/2026: 2,12 + 4,33 + 4,62 = 11,07 % do PIB em 2025).
"""

from __future__ import annotations

from typing import Any

from sacibras.rede import baixar_json

BASE = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,GFS_SOO"
FONTE = "FMI, Government Finance Statistics (demonstração de operações)"
ATIVOS = "G21_T"
INATIVOS = "G273_T"
GERAL = "S13"
ESFERAS = {"S1311B": "União", "S1312MIXED": "Estados", "S1313MIXED": "Municípios"}

Valores = dict[tuple[str, str, str, str], dict[int, float]]
"""{(país, setor, indicador, unidade): {ano: valor}}."""


def ler(bruto: dict[str, Any]) -> Valores:
    """A resposta SDMX-JSON (país, setor, grupo, indicador, unidade, frequência)."""
    estrutura, dados = bruto["structure"], bruto["dataSets"][0]
    dims = estrutura["dimensions"]["series"]
    anos = [int(v["id"][:4]) for v in estrutura["dimensions"]["observation"][0]["values"]]
    saida: Valores = {}
    for chave, serie in dados["series"].items():
        i = [int(x) for x in chave.split(":")]
        nome = (
            dims[0]["values"][i[0]]["id"],
            dims[1]["values"][i[1]]["id"],
            dims[3]["values"][i[3]]["id"],
            dims[4]["values"][i[4]]["id"],
        )
        valores = {
            anos[int(t)]: float(obs[0])
            for t, obs in serie["observations"].items()
            if obs and obs[0] not in (None, "")
        }
        if valores:
            saida[nome] = valores
    return saida


def _baixar(chave: str, desde: int) -> Valores:
    bruto = baixar_json(
        f"{BASE}/{chave}",
        params={"startPeriod": str(desde)},
        cabecalhos={"Accept": "application/json"},
        validade=7 * 86400,
        tempo_limite=240,
    )
    return ler(bruto)


def paises(desde: int) -> dict[str, dict[str, dict[int, float]]]:
    """{ISO3: {indicador: {ano: % do PIB}}} do governo geral, todos os países."""
    saida: dict[str, dict[str, dict[int, float]]] = {}
    for (pais, _, indicador, _), v in _baixar(
        f".{GERAL}..{ATIVOS}+{INATIVOS}.POGDP_PT.A", desde
    ).items():
        saida.setdefault(pais, {})[indicador] = v
    return saida


def brasil_por_esfera(desde: int) -> Valores:
    """O Brasil, governo geral e as três esferas, em % do PIB e em reais."""
    setores = "+".join([GERAL, *ESFERAS])
    return _baixar(f"BRA.{setores}..{ATIVOS}+{INATIVOS}.POGDP_PT+XDC.A", desde)
