"""A Selic e o que vem depois: os ciclos de corte e de alta, e a conta do efeito.

Duas coisas diferentes, que a tela mostra separadas:

- `ciclos` e `depois_do_ciclo` contam o que aconteceu de fato depois de cada ciclo. Não é o
  efeito da Selic: o Copom corta quando espera inflação em queda, e junto vieram safra, dólar
  e crise de fora.
- `efeito` é a estimativa do Banco Central para o efeito isolado (`relatorios.py`), posta na
  escala da mudança escolhida. O navegador refaz a mesma conta (`web/src/simulador-selic.ts`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from typing import Literal

from sacibras.tipos import Ponto

PAUSA_QUE_SEPARA = 365
"""Dias sem mexer na Selic que separam dois ciclos no mesmo sentido (2018 e 2019)."""


@dataclass(frozen=True)
class Ciclo:
    sentido: Literal["corte", "alta"]
    inicio: date
    """O dia em que a primeira mudança passou a valer."""
    fim: date
    """O dia da última mudança."""
    selic_antes: float
    selic_depois: float

    @property
    def rotulo(self) -> str:
        if self.inicio.year == self.fim.year:
            return str(self.inicio.year)
        return f"{self.inicio.year}–{self.fim.year % 100:02d}"


def ciclos(diaria: list[Ponto]) -> list[Ciclo]:
    """Os ciclos da Selic meta: mudanças seguidas no mesmo sentido.

    Uma pausa não encerra o ciclo; a virada de sentido encerra, e também um ano parado."""
    saida: list[Ciclo] = []
    aberto: Ciclo | None = None
    for (_, antes), (dia, depois) in pairwise(diaria):
        if depois == antes:
            continue
        sentido: Literal["corte", "alta"] = "corte" if depois < antes else "alta"
        continua = (
            aberto is not None
            and aberto.sentido == sentido
            and (dia - aberto.fim).days <= PAUSA_QUE_SEPARA
        )
        if aberto is not None and continua:
            aberto = Ciclo(sentido, aberto.inicio, dia, aberto.selic_antes, depois)
        else:
            if aberto is not None:
                saida.append(aberto)
            aberto = Ciclo(sentido, dia, dia, antes, depois)
    if aberto is not None:
        saida.append(aberto)
    return saida


def _meses_depois(d: date, meses: int) -> date:
    total = d.year * 12 + d.month - 1 + meses
    return date(total // 12, total % 12 + 1, 1)


def no_mes(mensal: list[Ponto], inicio: date, meses: int = 0) -> float | None:
    """O valor da série mensal no mês de `inicio` mais `meses`; None se a série não chega lá."""
    alvo = _meses_depois(inicio, meses)
    return next((v for d, v in mensal if d.year == alvo.year and d.month == alvo.month), None)


def ate_o_dia(diaria: list[Ponto], dia: date) -> float | None:
    """O último valor da série diária até `dia`; None se a série começa depois ou acaba antes."""
    if not diaria or dia < diaria[0][0] or dia > diaria[-1][0]:
        return None
    return [v for d, v in diaria if d <= dia][-1]


def mes_relativo(k: int) -> date:
    """O mês `k` contado de uma marca, escrito como data para o gráfico de eixo "meses".

    O mês 0 é jan/2000, o 1 é fev/2000, o −1 é dez/1999: o site lê de volta e escreve "mês k"
    (`eixo="meses"` em `schema.Grafico`)."""
    return _meses_depois(date(2000, 1, 1), k)


def alinhado(mensal: list[Ponto], inicio: date, antes: int, depois: int) -> list[Ponto]:
    """A série mensal de `antes` meses antes do mês de `inicio` a `depois` meses depois, com o
    mês de `inicio` no 0 (datas de `mes_relativo`). Mês que a série não tem fica de fora."""
    saida: list[Ponto] = []
    for k in range(-antes, depois + 1):
        v = no_mes(mensal, inicio, k)
        if v is not None:
            saida.append((mes_relativo(k), v))
    return saida


def fim_do_mes(diaria: list[Ponto]) -> list[Ponto]:
    """O último valor de cada mês, datado no dia 1 (para `no_mes`)."""
    por_mes: dict[date, float] = {}
    for d, v in diaria:
        por_mes[date(d.year, d.month, 1)] = v
    return sorted(por_mes.items())


@dataclass(frozen=True)
class DepoisDoCiclo:
    ipca_no_comeco: float | None
    ipca_um_ano: float | None
    ipca_dois_anos: float | None
    dolar_um_ano: float | None
    """Variação do dólar, em %, do primeiro dia do ciclo a um ano depois."""
    divida_dois_anos: float | None
    """Mudança da dívida bruta, em pp do PIB, do mês do começo a dois anos depois."""


def depois_do_ciclo(
    c: Ciclo, ipca12: list[Ponto], dolar: list[Ponto], divida: list[Ponto]
) -> DepoisDoCiclo:
    um_ano = date(c.inicio.year + 1, c.inicio.month, min(c.inicio.day, 28))
    d0, d1 = ate_o_dia(dolar, c.inicio), ate_o_dia(dolar, um_ano)
    b0, b2 = no_mes(divida, c.inicio), no_mes(divida, c.inicio, 24)
    return DepoisDoCiclo(
        ipca_no_comeco=no_mes(ipca12, c.inicio),
        ipca_um_ano=no_mes(ipca12, c.inicio, 12),
        ipca_dois_anos=no_mes(ipca12, c.inicio, 24),
        dolar_um_ano=(d1 / d0 - 1) * 100 if d0 and d1 else None,
        divida_dois_anos=b2 - b0 if b0 is not None and b2 is not None else None,
    )


@dataclass(frozen=True)
class Efeito:
    """O que muda um ano depois, com a Selic `pp` diferente durante quatro trimestres."""

    ipca: float
    """pp no IPCA acumulado em quatro trimestres (modelo agregado do BC)."""
    ipca_outro_modelo: float
    ipca_faixa: tuple[float, float]
    """A faixa de 90 % do BC para o IPCA, da menor ponta à maior."""
    dolar: float
    """% no dólar."""
    dolar_faixa: tuple[float, float]
    divida_pelos_juros: float
    divida_pelo_dolar: float
    divida_pela_inflacao: float

    divida_faixa: tuple[float, float]
    """Os juros (conta de estoque, sem faixa) mais as pontas do dólar e da inflação."""

    @property
    def divida(self) -> float:
        """pp do PIB na dívida bruta, as três partes somadas."""
        return self.divida_pelos_juros + self.divida_pelo_dolar + self.divida_pela_inflacao


def efeito(
    pp: float,
    *,
    ipca_por_pp: float,
    ipca_por_pp_outro: float,
    ipca_por_pp_faixa: tuple[float, float],
    dolar_por_pp: float,
    dolar_por_pp_faixa: tuple[float, float],
    divida_por_pp_de_selic: float,
    divida_por_1_de_dolar: float,
    divida_por_pp_de_precos: float,
) -> Efeito:
    """As estimativas do BC na escala de `pp` (os modelos são lineares e simétricos).

    A dívida soma três contas do BC: os juros da parte atrelada à Selic, o dólar que a Selic
    move e a inflação que ela move (a soma é nossa; cada parcela é dele). As faixas são as de
    90 % que o BC publica; a da dívida soma as pontas do dólar e da inflação."""
    dolar = dolar_por_pp * pp
    ipca = ipca_por_pp * pp
    do_dolar = sorted(k * pp for k in dolar_por_pp_faixa)
    do_ipca = sorted(k * pp for k in ipca_por_pp_faixa)
    juros = divida_por_pp_de_selic * pp
    return Efeito(
        ipca=ipca,
        ipca_outro_modelo=ipca_por_pp_outro * pp,
        ipca_faixa=(do_ipca[0], do_ipca[1]),
        dolar=dolar,
        dolar_faixa=(do_dolar[0], do_dolar[1]),
        divida_pelos_juros=juros,
        divida_pelo_dolar=divida_por_1_de_dolar * dolar,
        divida_pela_inflacao=divida_por_pp_de_precos * ipca,
        divida_faixa=(
            juros + divida_por_1_de_dolar * do_dolar[0] + divida_por_pp_de_precos * do_ipca[0],
            juros + divida_por_1_de_dolar * do_dolar[1] + divida_por_pp_de_precos * do_ipca[1],
        ),
    )
