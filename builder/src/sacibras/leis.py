"""Números que vêm de norma. Cada um com a referência da norma lida.

Regra do projeto: número de lei só entra daqui, e só depois de a norma ter sido lida na fonte
oficial (a data da leitura fica ao lado).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MetaDeInflacao:
    centro: float
    intervalo: float
    desde: date
    referencia: str


META_CONTINUA = MetaDeInflacao(
    centro=3.0,
    intervalo=1.5,
    desde=date(2025, 1, 1),
    # Lida em 14/11/2026 na API de normativos do BCB (exibenormativo?p1=Resolução CMN&p2=5141):
    # "Art. 2º A meta para a variação acumulada em doze meses do índice de preços indicado no
    # art. 1º, apurada mês a mês, a ser aplicada no período que se inicia em 1º de janeiro de
    # 2025, é fixada em 3,00% (três inteiros por cento), com intervalo de tolerância de menos
    # 1,50 p.p. (um e meio ponto percentual) e de mais 1,50 p.p." O art. 1º indica o IPCA.
    referencia="Resolução CMN nº 5.141, de 26/6/2024, art. 2º",
)


@dataclass(frozen=True)
class LimiteLegal:
    """Um limite em % da receita corrente líquida, com a norma de onde ele sai."""

    valor: float
    referencia: str


# ---- Pessoal do Poder Executivo estadual (o RGF que o SICONFI traz é o do Executivo).
# Lidos em 14/11/2026 no Planalto (ccivil_03/leis/lcp/lcp101.htm):
# art. 19, II: "Estados: 60% (sessenta por cento)" da RCL;
# art. 20, II, c: "49% (quarenta e nove por cento) para o Executivo" (marcado "Vide ADI 6533");
# art. 22, parágrafo único: "Se a despesa total com pessoal exceder a 95% (noventa e cinco por
# cento) do limite, são vedados [...]" (o limite prudencial);
# art. 59, § 1º, II: o Tribunal de Contas alerta quando a despesa com pessoal passa de "90%
# (noventa por cento) do limite" (o limite de alerta).
PESSOAL_EXECUTIVO_ESTADUAL = LimiteLegal(49.0, "LRF, art. 20, II, c")
PESSOAL_PRUDENCIAL = LimiteLegal(round(0.95 * 49.0, 2), "LRF, art. 22, parágrafo único")
PESSOAL_ALERTA = LimiteLegal(round(0.90 * 49.0, 2), "LRF, art. 59, § 1º, II")

# ---- Dívida consolidada líquida dos estados.
# Lida em 14/11/2026 no Senado (legis.senado.leg.br/norma/562458, texto atualizado):
# Resolução do Senado Federal nº 40/2001, art. 3º, I: a dívida consolidada líquida "não poderá
# exceder [...] no caso dos Estados e do Distrito Federal: 2 (duas) vezes a receita corrente
# líquida". O alerta é o mesmo art. 59, § 1º, III, da LRF: "acima de 90% (noventa por cento)".
DIVIDA_ESTADUAL = LimiteLegal(200.0, "Resolução do Senado nº 40/2001, art. 3º, I")
DIVIDA_ALERTA = LimiteLegal(180.0, "LRF, art. 59, § 1º, III")


@dataclass(frozen=True)
class MetaPrimaria:
    """A meta de resultado primário do Governo Central para um ano, em R$ milhões correntes."""

    ano: int
    centro: float
    inferior: float
    superior: float
    referencia: str


# Lida em 14/11/2026 no Planalto (ccivil_03/_ato2023-2026/2025/lei/L15321.htm), Lei nº 15.321,
# de 31/12/2025 (LDO 2026), art. 2º: "meta de superávit primário de R$ 34.264.603.518,00 [...]
# para o Governo Central"; § 1º: intervalo de tolerância com "limite superior equivalente a
# superávit primário de R$ 68.529.207.037,00" e "limite inferior equivalente ao resultado
# primário de R$ 0,00". A banda vem da LC 101/2000, art. 4º, § 5º, IV (incluído pela LC
# 200/2023): "menos 0,25 p.p. [...] e de mais 0,25 p.p. [...] do PIB previsto".
# A LC 200/2023, art. 2º, § 4º, diz que a apuração é do Banco Central.
# AINDA FORA DA TELA (decisão do Caio pendente): o relatório bimestral do governo desconta da
# meta despesas que outras normas excluem (EC 136/2025, LCs 221, 223 e 235; R$ 67,3 bi no 4º
# bimestre de 2026, segundo a nota da Consultoria de Orçamento do Senado). O número cru do BC
# contra a meta diria "abaixo do piso" num ano em que a apuração oficial pode dizer "dentro".
META_PRIMARIA_2026 = MetaPrimaria(
    ano=2026,
    centro=34_264.603518,
    inferior=0.0,
    superior=68_529.207037,
    referencia="Lei nº 15.321/2025 (LDO 2026), art. 2º",
)

# Lidos em 14/11/2026, ainda sem uso na tela (pedem o RREO Anexo 12 e o Anexo 08 de cada
# estado, que trazem a base de cálculo): saúde, no mínimo 12 % da arrecadação de impostos
# estaduais e transferências (LC 141/2012, art. 6º; Constituição, art. 198, § 2º, II);
# educação, no mínimo 25 % da receita de impostos, incluídas as transferências
# (Constituição, art. 212).
