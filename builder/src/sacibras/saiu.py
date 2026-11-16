"""O que saiu por último, contra o que o Focus esperava (Caio, 16/11/2026: *"pode incluir"*).

Para cada divulgação (o IPCA do mês, a desocupação, o PIB do trimestre, a decisão do Copom):
o número que saiu, a última mediana do Focus antes dele e a diferença. Ao lado, quanto o
Focus costuma errar nesse número: a média do erro absoluto nas divulgações anteriores, para
a pessoa saber se a diferença é do tamanho de sempre ou não. Nada aqui é previsão nossa.

Limite declarado: o que saiu é o dado de hoje (o PIB e a desocupação são revisados), não o
da hora da divulgação.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from sacibras.fontes import bcb_copom, bcb_focus, ibge_sidra
from sacibras.schema import Divulgado
from sacibras.secoes.base import Contexto, periodo
from sacibras.tipos import Periodicidade, Ponto

MINIMO_PARA_O_ERRO = 6
"""Com menos divulgações que isto, o erro de costume não é dito."""

Esperado = dict[date, tuple[date, float]]
"""{referência: (dia da coleta, mediana)}: a última coleta do Focus para cada referência."""


def _mes(texto: str) -> date:
    mes, ano = texto.split("/")
    return date(int(ano), int(mes), 1)


def _trimestre(texto: str) -> date:
    tri, ano = texto.split("/")
    return date(int(ano), 3 * int(tri) - 2, 1)


def ultimas(linhas: list[tuple[str, date, float]], ler: Callable[[str], date]) -> Esperado:
    """De [(referência, coleta, mediana)] da mais nova à mais antiga, a mais nova de cada uma."""
    saida: Esperado = {}
    for referencia, coleta, mediana in linhas:
        saida.setdefault(ler(referencia), (coleta, mediana))
    return saida


def medir(
    id: str,
    nome: str,
    secao: str,
    realizado: list[Ponto],
    esperado: Esperado,
    *,
    unidade: str,
    casas: int,
    periodicidade: Periodicidade,
    fonte: str,
    nota: str = "",
    rotulo: Callable[[date], str] | None = None,
    dias: dict[date, date] | None = None,
) -> Divulgado | None:
    """A última divulgação de `realizado` contra o Focus. `dias`: o dia em que cada número
    saiu, quando se sabe (o Copom); sem ele, vale a coleta do Focus, que é da véspera."""
    if not realizado:
        return None
    quando, valor = realizado[-1]
    erros = [abs(v - esperado[d][1]) for d, v in realizado[:-1] if d in esperado and v is not None]
    tem = quando in esperado
    coleta, mediana = esperado[quando] if tem else (None, None)
    return Divulgado(
        id=id,
        nome=nome,
        secao=secao,
        referencia=quando,
        periodo=rotulo(quando) if rotulo else periodo(quando, periodicidade),
        nota=nota,
        valor=round(valor, casas + 2),
        unidade=unidade,
        casas=casas,
        esperado=mediana,
        esperado_em=coleta,
        surpresa=round(round(valor, casas) - round(mediana, casas), casas)
        if mediana is not None
        else None,
        erro_de_costume=round(sum(erros) / len(erros), casas + 1)
        if len(erros) >= MINIMO_PARA_O_ERRO
        else None,
        divulgacoes=len(erros),
        saiu_em=(dias or {}).get(quando) or coleta,
        fonte=fonte,
    )


def _ipca(ctx: Contexto) -> Divulgado | None:
    linhas = bcb_focus.medianas_no_tempo(
        "ExpectativaMercadoMensais", "IPCA", ctx.hoje - timedelta(days=400)
    )
    return medir(
        "ipca",
        "IPCA",
        "inflacao",
        ctx.sgs("IPCA"),
        ultimas(linhas, _mes),
        unidade="%",
        casas=2,
        periodicidade="M",
        nota="no mês",
        fonte=f"{ctx.fonte_sgs('IPCA')} (IBGE) e Focus",
    )


def _desocupacao(ctx: Contexto) -> Divulgado | None:
    linhas = bcb_focus.medianas_no_tempo(
        "ExpectativaMercadoMensais", "Taxa de desocupação", ctx.hoje - timedelta(days=500)
    )
    return medir(
        "desocupacao",
        "Desocupação",
        "trabalho",
        ctx.sgs("DESOCUPACAO"),
        ultimas(linhas, _mes),
        unidade="%",
        casas=1,
        periodicidade="M",
        nota="trimestre até o mês",
        fonte=f"{ctx.fonte_sgs('DESOCUPACAO')} (IBGE) e Focus",
    )


def _pib(ctx: Contexto) -> Divulgado | None:
    realizado: list[Ponto] = ctx.memo.get("pib_aa") or ibge_sidra.series(
        5932, 6561, classificacao="c11255/90707", por="Setores", trimestral=True
    ).get("90707", [])
    linhas = bcb_focus.medianas_no_tempo(
        "ExpectativasMercadoTrimestrais", "PIB Total", ctx.hoje - timedelta(days=900)
    )
    return medir(
        "pib",
        "PIB",
        "atividade",
        realizado,
        ultimas(linhas, _trimestre),
        unidade="%",
        casas=1,
        periodicidade="T",
        nota="contra um ano antes",
        fonte="IBGE (SIDRA 5932) e Focus",
    )


def _selic(ctx: Contexto) -> Divulgado | None:
    feitas = [r for r in bcb_copom.reunioes() if r.meta is not None and r.data <= ctx.hoje]
    if not feitas:
        return None
    linhas = bcb_focus.medianas_no_tempo(
        "ExpectativasMercadoSelic", "Selic", ctx.hoje - timedelta(days=420), campo="Reuniao"
    )
    # A reunião "R7/2026" é a 7ª ordinária do ano; vale a última coleta antes do dia dela.
    ordem: dict[str, date] = {}
    do_ano: dict[int, int] = {}
    for r in feitas:
        do_ano[r.data.year] = do_ano.get(r.data.year, 0) + 1
        ordem[f"R{do_ano[r.data.year]}/{r.data.year}"] = r.data
    esperado: Esperado = {}
    for reuniao, coleta, mediana in linhas:
        dia = ordem.get(reuniao)
        if dia and coleta < dia:
            esperado.setdefault(dia, (coleta, mediana))
    return medir(
        "selic",
        "Selic",
        "juros",
        [(r.data, float(r.meta)) for r in feitas if r.meta is not None],
        esperado,
        unidade="% a.a.",
        casas=2,
        periodicidade="D",
        fonte="Banco Central (Copom e Focus)",
        rotulo=lambda d: f"reunião de {d.strftime('%d/%m/%Y')}",
        dias={r.data: r.data for r in feitas},
    )


def montar(ctx: Contexto, anteriores: list[Divulgado]) -> list[Divulgado]:
    """As divulgações, da mais nova à mais antiga. A que falhar fica com a da rodada anterior
    (`anteriores`): valor nunca em branco."""
    de_antes = {d.id: d for d in anteriores}
    saida: list[Divulgado] = []
    for id, conta in (
        ("ipca", _ipca),
        ("desocupacao", _desocupacao),
        ("pib", _pib),
        ("selic", _selic),
    ):
        try:
            novo = conta(ctx)
        except Exception as erro:
            print(f"    saiu: {id} ficou com o da rodada anterior ({str(erro)[:120]})")
            novo = None
        item = novo or de_antes.get(id)
        if item:
            saida.append(item)
    return sorted(saida, key=lambda d: d.saiu_em or d.referencia, reverse=True)
