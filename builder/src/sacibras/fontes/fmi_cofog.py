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


# ------------------------------------------------------------------ por esfera, só o Brasil
#
# O mesmo conjunto abre o Brasil em três esferas (conferido em 19/11/2026, BRA até 2024):
# `S1311` (governo central: a União), `S1312MIXED` (os estados e o DF) e `S1313MIXED` (os
# municípios). Cada esfera conta o que ela paga, os repasses a outra esfera inclusive: o
# FPE, o FPM e a cota do ICMS ficam na função "transferências gerais entre esferas"
# (GF0180, dentro de serviços públicos gerais), e o repasse com destino certo (o SUS, o
# complemento do Fundeb) fica na função dele. Por isso a soma das três passa do governo
# geral (`S13`), que tira o que uma esfera passa à outra. Em 2024, a União repassou R$ 548
# bi em GF0180 e os estados, R$ 197 bi. A unidade `POTO_PT` é a parte da despesa da própria
# esfera; `POGDP_PT`, % do PIB.

ESFERAS: dict[str, str] = {
    "S1311": "União",
    "S1312MIXED": "Estados",
    "S1313MIXED": "Municípios",
}
REPASSES = "GF0180_T"
"""Transferências gerais entre esferas (FPE, FPM, cota do ICMS): sem destino amarrado."""

PorEsfera = dict[str, dict[str, dict[str, dict[int, float]]]]
"""{esfera: {função: {unidade: {ano: valor}}}}."""


def ler_esferas(bruto: dict[str, Any]) -> PorEsfera:
    """A resposta SDMX-JSON (país, setor, grupo, função, unidade, frequência) por esfera."""
    estrutura, dados = bruto["structure"], bruto["dataSets"][0]
    dims = estrutura["dimensions"]["series"]
    anos = [int(v["id"][:4]) for v in estrutura["dimensions"]["observation"][0]["values"]]
    saida: PorEsfera = {}
    for chave, serie in dados["series"].items():
        i = [int(x) for x in chave.split(":")]
        esfera = dims[1]["values"][i[1]]["id"]
        funcao = dims[3]["values"][i[3]]["id"]
        unidade = dims[4]["values"][i[4]]["id"]
        valores = {
            anos[int(t)]: float(obs[0])
            for t, obs in serie["observations"].items()
            if obs and obs[0] not in (None, "")
        }
        if valores:
            saida.setdefault(esfera, {}).setdefault(funcao, {})[unidade] = valores
    return saida


def por_esfera(desde: int) -> PorEsfera:
    """A despesa da União, dos estados e dos municípios por função, em % do PIB e em % da
    despesa da própria esfera."""
    funcoes = "+".join([*FUNCOES, REPASSES])
    bruto = baixar_json(
        f"{BASE}/BRA.{'+'.join(ESFERAS)}.G2MF.{funcoes}.POGDP_PT+POTO_PT.A",
        params={"startPeriod": str(desde)},
        cabecalhos={"Accept": "application/json"},
        validade=7 * 86400,
        tempo_limite=240,
    )
    return ler_esferas(bruto)
