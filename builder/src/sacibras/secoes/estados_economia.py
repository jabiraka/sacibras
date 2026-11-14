"""Estados: economia, trabalho e crédito (as métricas que não são das contas do governo).

- PIB: Contas Regionais do IBGE (o oficial das 27 UFs, com dois anos de atraso). O crescimento
  sai da série encadeada do volume; o PIB por habitante divide o PIB corrente pela população da
  projeção do IBGE do mesmo ano (1º de julho), o que resolve a mistura de anos que deixava o
  PIB per capita de fora (a tabela 6579 de estimativas não tem todos os anos).
- Prévia do PIB: o IBC-R do Banco Central, mensal, só para os 13 estados que o BC publica.
  Daqui sai o crescimento de 12 meses e o do último ano fechado, que o IBGE ainda não publicou.
- Trabalho: PNAD Contínua trimestral por UF (SIDRA 4099, 8529 e 5436).
- Inflação: o IPCA de 12 meses das 16 áreas que o IBGE pesquisa (SIDRA 7060): cada uma é a
  capital ou a região metropolitana, e só ela representa o estado.
- Crédito: saldo e inadimplência do Sistema Financeiro Nacional por UF (SGS).
- Exportações: Comex Stat, por estado de origem da mercadoria.
- Concentração do PIB: índice de Gini do PIB dos municípios do estado (SIDRA 5939).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from sacibras.catalogo import CREDITO_INADIMPLENCIA_UF, CREDITO_SALDO_UF, IBCR_UF, SGS
from sacibras.fontes import comexstat, ibge_contas_regionais, ibge_projecao, ibge_sidra
from sacibras.schema import MetricaEstados
from sacibras.secoes.base import br, periodo
from sacibras.tipos import Ponto

UFs = list[tuple[int, str, str, str]]
"""(código IBGE, sigla, nome, região), como `estados.UFS`."""

ECONOMIA = "Economia"
TRABALHO = "Trabalho e renda"
CREDITO = "Crédito"


def _por_nome(ufs: UFs) -> dict[str, str]:
    return {nome: sigla for _, sigla, nome, _ in ufs}


# ------------------------------------------------------------------ PIB (Contas Regionais)


def pib(ufs: UFs) -> list[MetricaEstados]:
    """Crescimento no último ano, crescimento médio em dez anos, PIB por habitante e peso no
    PIB do Brasil, todos do mesmo ano das Contas Regionais."""
    edicao, corrente, volume = ibge_contas_regionais.pib()
    por_nome = _por_nome(ufs)
    falta = [n for n in por_nome if n not in corrente or n not in volume]
    if falta:
        raise ibge_contas_regionais.PlanilhaMudouError(f"Contas Regionais sem {falta}")
    ano = max(volume["Brasil"])
    fonte = f"{ibge_contas_regionais.FONTE} (edição {edicao}, FTP do IBGE)"

    def cresc(nome: str, de: int, ate: int) -> float | None:
        v = volume[nome]
        if de not in v or ate not in v:
            return None
        return float(((v[ate] / v[de]) ** (1 / (ate - de)) - 1) * 100)

    metricas = [
        MetricaEstados(
            id="pib_crescimento",
            nome="Crescimento do PIB",
            descricao=(
                f"Quanto a economia do estado cresceu em {ano} sobre {ano - 1}, sem o efeito "
                "dos preços. É o número oficial do IBGE, que sai com quase dois anos de "
                "atraso; para um sinal mais novo, veja a prévia pelo IBC-R."
            ),
            unidade="%",
            casas=1,
            referencia=str(ano),
            maior_e_melhor=True,
            fonte=f"{fonte}, tabela 3 (volume do PIB)",
            valores={s: cresc(n, ano - 1, ano) for n, s in por_nome.items()},
            brasil=cresc("Brasil", ano - 1, ano),
            grupo=ECONOMIA,
        )
    ]
    inicio = ano - 10
    if inicio in volume["Brasil"]:
        metricas.append(
            MetricaEstados(
                id="pib_crescimento_10_anos",
                nome="Crescimento do PIB em 10 anos",
                descricao=(
                    f"Crescimento médio por ano de {inicio} a {ano}, sem o efeito dos preços. "
                    "Pega a recessão de 2015–16 e a pandemia: mostra quem cresce de forma "
                    "duradoura, não um ano bom."
                ),
                unidade="% ao ano",
                casas=1,
                referencia=f"{inicio}–{ano}",
                maior_e_melhor=True,
                fonte=f"{fonte}, tabela 3 (volume do PIB)",
                valores={s: cresc(n, inicio, ano) for n, s in por_nome.items()},
                brasil=cresc("Brasil", inicio, ano),
                grupo=ECONOMIA,
            )
        )

    populacao = ibge_projecao.grupos()
    per_capita: dict[str, float | None] = {}
    for nome, sigla in por_nome.items():
        pop = populacao.get(sigla, {}).get("POP_T", {}).get(ano)
        pib_ano = corrente[nome].get(ano)
        per_capita[sigla] = pib_ano * 1e6 / pop if pop and pib_ano else None
    pop_br = populacao.get("BR", {}).get("POP_T", {}).get(ano)
    pib_br = corrente["Brasil"].get(ano)
    metricas.append(
        MetricaEstados(
            id="pib_per_capita",
            nome="PIB por habitante",
            descricao=(
                f"PIB do estado em {ano}, a preços do próprio ano, dividido pela população "
                "estimada pelo IBGE para 1º de julho. Mede quanto se produz por pessoa, não "
                "quanto cada um ganha: onde há muita mineração, petróleo ou agronegócio de "
                "exportação, o PIB por habitante fica bem acima da renda das famílias."
            ),
            unidade="R$ por pessoa",
            casas=0,
            referencia=str(ano),
            maior_e_melhor=None,
            fonte=f"{fonte}, tabela 1; {ibge_projecao.FONTE} (população em 1º/7/{ano})",
            valores=per_capita,
            brasil=pib_br * 1e6 / pop_br if pib_br and pop_br else None,
            grupo=ECONOMIA,
        )
    )
    if pib_br:
        metricas.append(
            MetricaEstados(
                id="pib_participacao",
                nome="Peso no PIB do Brasil",
                descricao=f"Fatia do estado no PIB do país em {ano}, a preços correntes.",
                unidade="% do PIB do Brasil",
                casas=1,
                referencia=str(ano),
                maior_e_melhor=None,
                fonte=f"{fonte}, tabela 1",
                valores={
                    s: corrente[n][ano] / pib_br * 100 if ano in corrente[n] else None
                    for n, s in por_nome.items()
                },
                grupo=ECONOMIA,
            )
        )
    return metricas


# ------------------------------------------------------------------ IBC-R (Banco Central)


def _media(pontos: list[Ponto], de: date, ate: date) -> float | None:
    """Média dos meses de `de` a `ate` (inclusive), só se estiverem todos."""
    vals = [v for d, v in pontos if de <= d <= ate]
    meses = (ate.year - de.year) * 12 + ate.month - de.month + 1
    return sum(vals) / len(vals) if len(vals) == meses else None


def _menos_meses(d: date, n: int) -> date:
    total = d.year * 12 + d.month - 1 - n
    return date(total // 12, total % 12 + 1, 1)


def crescimento_12_meses(pontos: list[Ponto], fim: date) -> float | None:
    """Os 12 meses até `fim` contra os 12 anteriores, em %."""
    atual = _media(pontos, _menos_meses(fim, 11), fim)
    antes = _media(pontos, _menos_meses(fim, 23), _menos_meses(fim, 12))
    return (atual / antes - 1) * 100 if atual and antes else None


def ibcr(ufs: UFs, sgs: Callable[[str], list[Ponto]]) -> list[MetricaEstados]:
    """Prévia do PIB pelo IBC-R: os 12 meses mais recentes e o último ano fechado."""
    series = {s: sgs(f"IBCR_{s}") for s in IBCR_UF}
    brasil = sgs("IBCBR")
    # O último mês que todos os 13 têm (o BC publica todos juntos, mas por garantia).
    fim = min(p[-1][0] for p in series.values() if p)
    ano = fim.year - 1 if fim.month < 12 else fim.year
    siglas = [s for _, s, _, _ in ufs]
    fora = sorted(s for s in siglas if s not in IBCR_UF)
    nota_fora = (
        f" O Banco Central só publica o IBC-R de {len(IBCR_UF)} estados; "
        f"{', '.join(fora)} ficam sem dado."
    )
    codigos = ", ".join(str(SGS[f"IBCR_{s}"].codigo) for s in sorted(IBCR_UF))
    fonte = f"Banco Central, IBC-R (SGS {codigos}); Brasil: IBC-Br (SGS {SGS['IBCBR'].codigo})"

    def no_ano(p: list[Ponto]) -> float | None:
        atual = _media(p, date(ano, 1, 1), date(ano, 12, 1))
        antes = _media(p, date(ano - 1, 1, 1), date(ano - 1, 12, 1))
        return (atual / antes - 1) * 100 if atual and antes else None

    return [
        MetricaEstados(
            id="ibcr_12_meses",
            nome="Atividade em 12 meses (IBC-R)",
            descricao=(
                "O índice de atividade do Banco Central para o estado, uma prévia mensal do "
                "PIB: a média dos últimos 12 meses contra a dos 12 anteriores. Não é o PIB do "
                "IBGE (usa menos dados e pode errar o tamanho), mas chega quase dois anos "
                "antes." + nota_fora
            ),
            unidade="%",
            casas=1,
            referencia=f"12 meses até {periodo(fim, 'M')}",
            maior_e_melhor=True,
            fonte=fonte,
            valores={
                s: crescimento_12_meses(series[s], fim) if s in series else None for s in siglas
            },
            brasil=crescimento_12_meses(brasil, fim),
            grupo=ECONOMIA,
        ),
        MetricaEstados(
            id="ibcr_ano",
            nome=f"Prévia do PIB de {ano} (IBC-R)",
            descricao=(
                f"Crescimento de {ano} sobre {ano - 1} pela média do IBC-R no ano: o número "
                f"que o IBGE só vai publicar nas Contas Regionais de {ano} (em novembro de "
                f"{ano + 2}). Conta nossa com o índice do Banco Central, não número oficial "
                "do PIB." + nota_fora
            ),
            unidade="%",
            casas=1,
            referencia=str(ano),
            maior_e_melhor=True,
            fonte=fonte,
            valores={s: no_ano(series[s]) if s in series else None for s in siglas},
            brasil=no_ano(brasil),
            grupo=ECONOMIA,
        ),
    ]


# ------------------------------------------------------------------ PNAD por UF


def _pnad(
    ufs: UFs, tabela: int, variavel: int
) -> tuple[date, dict[str, float | None], float | None]:
    por_uf = ibge_sidra.series(
        tabela,
        variavel,
        periodos="last 1",
        nivel="n3/all",
        por="Unidade da Federação",
        trimestral=True,
    )
    sigla = {cod: s for cod, s, _, _ in ufs}
    valores: dict[str, float | None] = {s: None for s in sigla.values()}
    quando: date | None = None
    for cod, pontos in por_uf.items():
        if int(cod) in sigla and pontos:
            quando, valores[sigla[int(cod)]] = pontos[-1]
    if quando is None:
        raise RuntimeError(f"SIDRA {tabela} sem dado por UF")
    pais = ibge_sidra.serie(tabela, variavel, periodos="last 1", nivel="n1/all", trimestral=True)
    return quando, valores, (pais[-1][1] if pais and pais[-1][0] == quando else None)


def trabalho(ufs: UFs) -> list[MetricaEstados]:
    saida: list[MetricaEstados] = []
    quando, valores, brasil = _pnad(ufs, 4099, 4118)
    saida.append(
        MetricaEstados(
            id="subutilizacao",
            nome="Subutilização",
            descricao=(
                "Quem está sem trabalho, quem trabalha menos horas do que gostaria e quem "
                "queria trabalhar mas não procurou, em proporção da força de trabalho "
                "ampliada. Pega o que a desocupação deixa de fora."
            ),
            unidade="%",
            casas=1,
            referencia=periodo(quando, "T"),
            maior_e_melhor=False,
            fonte="IBGE, PNAD Contínua trimestral (SIDRA, tabela 4099, taxa composta)",
            valores=valores,
            brasil=brasil,
            grupo=TRABALHO,
        )
    )
    quando, valores, brasil = _pnad(ufs, 8529, 12466)
    saida.append(
        MetricaEstados(
            id="informalidade",
            nome="Informalidade",
            descricao=(
                "Parcela dos ocupados sem carteira assinada, sem CNPJ ou trabalhando para a "
                "família sem receber: quem fica sem FGTS, férias e, em geral, sem INSS."
            ),
            unidade="% dos ocupados",
            casas=1,
            referencia=periodo(quando, "T"),
            maior_e_melhor=False,
            fonte="IBGE, PNAD Contínua trimestral (SIDRA, tabela 8529)",
            valores=valores,
            brasil=brasil,
            grupo=TRABALHO,
        )
    )
    quando, valores, brasil = _pnad(ufs, 5436, 5933)
    saida.append(
        MetricaEstados(
            id="renda_trabalho",
            nome="Renda média do trabalho",
            descricao=(
                "O que os ocupados costumam receber por mês, somados todos os trabalhos, "
                "em reais do trimestre da pesquisa. Média: puxada para cima por quem ganha muito."
            ),
            unidade="R$ por mês",
            casas=0,
            referencia=periodo(quando, "T"),
            maior_e_melhor=True,
            fonte="IBGE, PNAD Contínua trimestral (SIDRA, tabela 5436, rendimento habitual)",
            valores=valores,
            brasil=brasil,
            grupo=TRABALHO,
        )
    )
    return saida


# ------------------------------------------------------------------ IPCA nas capitais


def inflacao(ufs: UFs) -> MetricaEstados:
    """IPCA de 12 meses de cada área pesquisada, posto no estado dela."""
    siglas = {cod: s for cod, s, _, _ in ufs}
    valores: dict[str, float | None] = {s: None for s in siglas.values()}
    areas: list[str] = []
    quando: date | None = None
    for nivel, por in (("n7/all", "Região Metropolitana"), ("n6/all", "Município")):
        linhas = ibge_sidra.series(
            7060, 2265, periodos="last 1", classificacao="c315/7169", nivel=nivel, por=por
        )
        for cod, pontos in linhas.items():
            uf = siglas.get(int(cod[:2]))
            if uf and pontos:
                quando, valores[uf] = pontos[-1]
                areas.append(uf)
    if quando is None:
        raise RuntimeError("SIDRA 7060 sem as áreas do IPCA")
    pais = ibge_sidra.serie(7060, 2265, periodos="last 1", classificacao="c315/7169")
    fora = sorted(s for s in siglas.values() if s not in areas)
    return MetricaEstados(
        id="inflacao_capital",
        nome="Inflação na capital",
        descricao=(
            "IPCA dos últimos 12 meses na capital ou na região metropolitana que o IBGE "
            f"pesquisa no estado ({len(areas)} áreas). Vale para ela, não para o interior. "
            f"{', '.join(fora)} não têm área pesquisada."
        ),
        unidade="% em 12 meses",
        casas=1,
        referencia=periodo(quando, "M"),
        maior_e_melhor=False,
        fonte="IBGE, IPCA (SIDRA, tabela 7060, por região metropolitana e município)",
        valores=valores,
        brasil=pais[-1][1] if pais and pais[-1][0] == quando else None,
        grupo=ECONOMIA,
    )


# ------------------------------------------------------------------ exportações


def exportacoes(ufs: UFs, populacao: dict[int, float]) -> MetricaEstados:
    fim, por_nome = comexstat.exportacoes_12_meses()
    valores: dict[str, float | None] = {}
    soma = soma_pop = 0.0
    for cod, sigla, nome, _ in ufs:
        pop = populacao.get(cod)
        if nome in por_nome and pop:
            valores[sigla] = por_nome[nome] / pop
            soma += por_nome[nome]
            soma_pop += pop
        else:
            valores[sigla] = None
    ref = f"12 meses até {periodo(fim, 'M')}"
    return MetricaEstados(
        id="exportacoes_per_capita",
        nome="Exportações por habitante",
        descricao=(
            "Quanto o estado vendeu ao exterior em 12 meses, em dólares, dividido pela "
            "população. Conta onde a mercadoria foi produzida, não o porto de saída. O que "
            "sai sem estado declarado fica fora."
        ),
        unidade="US$ por pessoa",
        casas=0,
        referencia=ref,
        maior_e_melhor=None,
        fonte=f"{comexstat.FONTE} (valor FOB, {ref}); população estimada do SICONFI (IBGE)",
        valores=valores,
        brasil=soma / soma_pop if soma_pop else None,
        grupo=ECONOMIA,
    )


# ------------------------------------------------------------------ concentração do PIB


def concentracao(ufs: UFs) -> MetricaEstados:
    por_uf = ibge_sidra.series(
        5939, 529, periodos="last 1", nivel="n3/all", por="Unidade da Federação"
    )
    sigla = {cod: s for cod, s, _, _ in ufs}
    valores: dict[str, float | None] = {s: None for s in sigla.values()}
    quando: date | None = None
    for cod, pontos in por_uf.items():
        if int(cod) in sigla and pontos:
            quando, valores[sigla[int(cod)]] = pontos[-1]
    if quando is None:
        raise RuntimeError("SIDRA 5939 sem dado por UF")
    pais = ibge_sidra.serie(5939, 529, periodos="last 1")
    # O DF é um município só: o índice não se aplica.
    valores["DF"] = None
    return MetricaEstados(
        id="pib_concentracao",
        nome="Concentração do PIB nos municípios",
        descricao=(
            "Índice de Gini do PIB entre os municípios do estado: 0 seria todos com o mesmo "
            "PIB, 1 seria tudo num só. Alto quer dizer que a economia se junta em poucas "
            "cidades. O Distrito Federal é um município só e fica de fora."
        ),
        unidade="índice de 0 a 1",
        casas=2,
        referencia=str(quando.year),
        maior_e_melhor=None,
        fonte="IBGE, PIB dos Municípios (SIDRA, tabela 5939)",
        valores=valores,
        brasil=pais[-1][1] if pais else None,
        grupo=ECONOMIA,
    )


# ------------------------------------------------------------------ crédito


def credito(
    ufs: UFs, sgs: Callable[[str], list[Ponto]], populacao: dict[int, float]
) -> list[MetricaEstados]:
    saldo = {s: sgs(f"CREDITO_SALDO_{s}") for s in CREDITO_SALDO_UF}
    inad = {s: sgs(f"CREDITO_INADIMPLENCIA_{s}") for s in CREDITO_INADIMPLENCIA_UF}
    fim = min(p[-1][0] for p in [*saldo.values(), *inad.values()] if p)

    def em(p: list[Ponto]) -> float | None:
        return next((v for d, v in reversed(p) if d == fim), None)

    por_hab: dict[str, float | None] = {}
    soma = soma_pop = 0.0
    for cod, sigla, _, _ in ufs:
        v, pop = em(saldo.get(sigla, [])), populacao.get(cod)
        if v is not None and pop:
            por_hab[sigla] = v * 1e6 / pop
            soma += v * 1e6
            soma_pop += pop
        else:
            por_hab[sigla] = None
    inadimplencia = {s: em(inad.get(s, [])) for _, s, _, _ in ufs}
    # O Brasil da inadimplência: a média dos estados pesada pelo saldo (a série nacional do
    # BC é de outra família e não fecha com a soma das UFs).
    pares = [(inadimplencia[s], em(saldo[s])) for s in inadimplencia]
    validos = [(i, w) for i, w in pares if i is not None and w]
    peso = sum(w for _, w in validos)
    ref = periodo(fim, "M")
    cods_saldo = f"{min(CREDITO_SALDO_UF.values())} a {max(CREDITO_SALDO_UF.values())}"
    cods_inad = (
        f"{min(CREDITO_INADIMPLENCIA_UF.values())} a {max(CREDITO_INADIMPLENCIA_UF.values())}"
    )
    return [
        MetricaEstados(
            id="credito_per_capita",
            nome="Crédito por habitante",
            descricao=(
                "Saldo de empréstimos e financiamentos de bancos e financeiras a pessoas e "
                "empresas do estado, dividido pela população. O estado é o do cliente."
            ),
            unidade="R$ por pessoa",
            casas=0,
            referencia=ref,
            maior_e_melhor=None,
            fonte=(
                f"Banco Central, saldo das operações de crédito do SFN por UF (SGS {cods_saldo}); "
                "população estimada do SICONFI (IBGE)"
            ),
            valores=por_hab,
            brasil=soma / soma_pop if soma_pop else None,
            grupo=CREDITO,
        ),
        MetricaEstados(
            id="credito_inadimplencia",
            nome="Inadimplência",
            descricao=(
                "Parcela do saldo de crédito com atraso de mais de 90 dias, pessoas e empresas "
                "juntas. O número do Brasil é a média dos estados pesada pelo saldo."
            ),
            unidade="% do saldo",
            casas=1,
            referencia=ref,
            maior_e_melhor=False,
            fonte=(
                "Banco Central, inadimplência das operações de crédito do SFN por UF "
                f"(SGS {cods_inad})"
            ),
            valores=inadimplencia,
            brasil=sum(i * w for i, w in validos) / peso if peso else None,
            grupo=CREDITO,
        ),
    ]


def frase_pib(m: MetricaEstados) -> str:
    v = {u: x for u, x in m.valores.items() if x is not None}
    if not v:
        return ""
    alto, baixo = max(v, key=lambda u: v[u]), min(v, key=lambda u: v[u])
    brasil = f", contra {br(m.brasil)} % no país" if m.brasil is not None else ""
    return (
        f"Em {m.referencia}, o PIB cresceu de {br(v[baixo])} % ({baixo}) a "
        f"{br(v[alto])} % ({alto}){brasil}."
    )
