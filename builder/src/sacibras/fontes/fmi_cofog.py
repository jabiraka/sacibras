"""A despesa do governo por função (COFOG), país a país, no Government Finance Statistics do
FMI (IMF.STA, GFS_COFOG). Conferido em 17/11/2026: setor S13 (governo geral: União, estados
e municípios), grupo G2MF (despesa por função), em % do PIB (POGDP_PT), anual; 79 países com
dado, 73 com algum ano de 2022 em diante, o Brasil até 2024.

As dez funções são as da classificação da ONU (COFOG). "Serviços públicos gerais" (GF01)
inclui os juros da dívida (GF0170, "operações da dívida pública"), que vêm à parte para não
somar juro com gasto de funcionamento. Da proteção social vêm à parte a velhice (GF1020, as
aposentadorias) e a pensão por morte (GF1030, "sobreviventes"). Os códigos de subfunção têm
quatro algarismos no FMI (GF0170, não GF017), conferido em 17/11/2026.
"""

from __future__ import annotations

from typing import Any

from sacibras.rede import baixar_json

BASE = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,GFS_COFOG"
FONTE = "FMI, Government Finance Statistics (COFOG), governo geral"

FUNCOES: dict[str, str] = {
    "GF10_T": "Proteção social",
    "GF1020_T": "  dos quais: velhice (aposentadorias)",
    "GF1030_T": "  dos quais: pensão por morte",
    "GF01_T": "Serviços públicos gerais",
    "GF0170_T": "  dos quais: juros da dívida",
    "GF07_T": "Saúde",
    "GF09_T": "Educação",
    "GF04_T": "Assuntos econômicos (transporte, energia, agricultura)",
    "GF03_T": "Segurança pública e Justiça",
    "GF02_T": "Defesa",
    "GF06_T": "Moradia e serviços urbanos",
    "GF05_T": "Meio ambiente",
    "GF08_T": "Cultura, esporte e religião",
}
"""Os códigos do FMI, na ordem da tabela, com o nome na tela."""

PorPais = dict[str, dict[str, dict[int, float]]]
"""{ISO3: {função: {ano: % do PIB}}}."""


def ler(bruto: dict[str, Any]) -> PorPais:
    """A resposta SDMX-JSON (país, setor, grupo, indicador, unidade, frequência) em dicionário."""
    estrutura, dados = bruto["structure"], bruto["dataSets"][0]
    dims = estrutura["dimensions"]["series"]
    anos = [int(v["id"][:4]) for v in estrutura["dimensions"]["observation"][0]["values"]]
    saida: PorPais = {}
    for chave, serie in dados["series"].items():
        i = [int(x) for x in chave.split(":")]
        pais = dims[0]["values"][i[0]]["id"]
        funcao = dims[3]["values"][i[3]]["id"]
        valores = {
            anos[int(t)]: float(obs[0])
            for t, obs in serie["observations"].items()
            if obs and obs[0] not in (None, "")
        }
        if valores:
            saida.setdefault(pais, {})[funcao] = valores
    return saida


def por_funcao(desde: int) -> PorPais:
    """Todos os países com a despesa do governo geral por função, em % do PIB."""
    indicadores = "+".join(FUNCOES)
    bruto = baixar_json(
        f"{BASE}/.S13.G2MF.{indicadores}.POGDP_PT.A",
        params={"startPeriod": str(desde)},
        cabecalhos={"Accept": "application/json"},
        validade=7 * 86400,
        tempo_limite=240,
    )
    return ler(bruto)
