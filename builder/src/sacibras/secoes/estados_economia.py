"""Estados: economia, trabalho e crédito (as métricas que não são das contas do governo).

- PIB: Contas Regionais do IBGE (o oficial das 27 UFs, com dois anos de atraso). O crescimento
  sai da série encadeada do volume; o PIB por habitante divide o PIB corrente pela população da
  projeção do IBGE do mesmo ano (1º de julho), o que resolve a mistura de anos que deixava o
  PIB per capita de fora (a tabela 6579 de estimativas não tem todos os anos).
- Prévia do PIB: o IBC-R do Banco Central, mensal, só para os 17 estados que o BC publica
  (MT desde 2013; MA, MS e RN desde 2023).
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
from dataclasses import dataclass
from datetime import date

from sacibras import relatorios
from sacibras.catalogo import (
    CREDITO_INADIMPLENCIA_UF,
    CREDITO_SALDO_UF,
    IBCR_REGIAO,
    IBCR_UF,
    SGS,
)
from sacibras.fontes import comexstat, ibge_contas_regionais, ibge_projecao, ibge_sidra
from sacibras.modelos import pib_estados
from sacibras.schema import BlocoDeConta, Cartao, Fatia, MetricaEstados, PeriodoDaMetrica
from sacibras.secoes.base import br, periodo
from sacibras.tipos import Ponto

UFs = list[tuple[int, str, str, str]]
"""(código IBGE, sigla, nome, região), como `estados.UFS`."""

ECONOMIA = "Economia"
TRABALHO = "Trabalho e renda"
CREDITO = "Crédito"
REGIOES = {"Norte": "N", "Nordeste": "NE", "Sudeste": "SE", "Sul": "S", "Centro-Oeste": "CO"}
"""Nome da região em `UFs` → a sigla dela no IBC-R (`catalogo.IBCR_REGIAO`)."""
assert set(REGIOES.values()) == set(IBCR_REGIAO)


def _por_nome(ufs: UFs) -> dict[str, str]:
    return {nome: sigla for _, sigla, nome, _ in ufs}


# ------------------------------------------------------------------ PIB (Contas Regionais)


def pib(ufs: UFs) -> list[MetricaEstados]:
    """Crescimento do PIB (o último ano; a série vai junto, para a tela escolher a janela),
    PIB por habitante e peso no PIB do Brasil, todos do mesmo ano das Contas Regionais."""
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
            anuais={
                ("BR" if n == "Brasil" else por_nome[n]): {a: round(x, 6) for a, x in v.items()}
                for n, v in volume.items()
                if n == "Brasil" or n in por_nome
            },
        )
    ]
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


def crescimento_anual(pontos: list[Ponto]) -> dict[int, float]:
    """{ano: crescimento da média do ano sobre a do anterior, em %}, só com anos inteiros."""
    por_ano: dict[int, list[float]] = {}
    for d, v in pontos:
        por_ano.setdefault(d.year, []).append(v)
    media = {a: sum(v) / 12 for a, v in por_ano.items() if len(v) == 12}
    return {a: (media[a] / media[a - 1] - 1) * 100 for a in media if a - 1 in media}


def _quantil(valores: list[float], p: float) -> float:
    ordenados = sorted(valores)
    i = p * (len(ordenados) - 1)
    baixo = int(i)
    alto = min(baixo + 1, len(ordenados) - 1)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (i - baixo)


MINIMO_DE_ERROS = 40
"""Com menos pares (previsão, oficial) que isso, a faixa de erro não se publica."""


def erros_da_previa(
    ufs: UFs,
    por_uf: dict[str, dict[int, float]],
    por_regiao: dict[str, dict[int, float]],
    volume: dict[str, dict[int, float]],
) -> tuple[list[float], list[float], int, int]:
    """O teste da prévia contra o PIB oficial, ano a ano: (oficial − IBC-R do próprio estado,
    oficial − IBC-R da região para quem não tem índice, primeiro ano, último ano)."""
    proprio: list[float] = []
    pela_regiao: list[float] = []
    anos: list[int] = []
    for _, sigla, nome, regiao in ufs:
        v = volume.get(nome, {})
        previa = por_uf.get(sigla) or por_regiao.get(regiao, {})
        for ano in sorted(v):
            if ano - 1 not in v or ano not in previa:
                continue
            erro = (v[ano] / v[ano - 1] - 1) * 100 - previa[ano]
            (proprio if sigla in por_uf else pela_regiao).append(erro)
            anos.append(ano)
    return proprio, pela_regiao, min(anos, default=0), max(anos, default=0)


def ibcr(
    ufs: UFs, sgs: Callable[[str], list[Ponto]], volume: dict[str, dict[int, float]] | None = None
) -> list[MetricaEstados]:
    """Prévia do PIB pelo IBC-R: os 12 meses mais recentes e o último ano fechado.

    A prévia do ano é previsão do PIB oficial e sai para os 27 estados por uma regra só:
    quem tem IBC-R usa o próprio índice; quem não tem cresce como a região dele (o IBC-R da
    região). Testada contra as Contas Regionais de 2011 a 2024 (14/11/2026), a regra da região
    errou menos que as duas alternativas: descontar da região os estados que têm índice
    (erro médio de 2,2 pp contra 2,0) e somar a folga histórica do estado sobre a região
    (igual, com faixa mais larga). A faixa de erro sai do mesmo teste, refeito a cada rodada
    com `volume` (a série encadeada das Contas Regionais): onde ficaram 8 de cada 10 erros.
    Sem `volume` não há faixa, e a previsão dos estados sem índice não se publica.
    """
    series = {s: sgs(f"IBCR_{s}") for s in IBCR_UF}
    brasil = sgs("IBCBR")
    # O último mês que todos têm (o BC publica todos juntos, mas por garantia).
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

    doze = MetricaEstados(
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
        valores={s: crescimento_12_meses(series[s], fim) if s in series else None for s in siglas},
        brasil=crescimento_12_meses(brasil, fim),
        grupo=ECONOMIA,
    )

    por_uf = {s: crescimento_anual(p) for s, p in series.items()}
    por_regiao = {r: crescimento_anual(sgs(f"IBCR_REGIAO_{c}")) for r, c in REGIOES.items()}
    proprio, pela_regiao, de, ate = erros_da_previa(ufs, por_uf, por_regiao, volume or {})
    valores: dict[str, float | None] = {
        s: por_uf[s].get(ano) if s in por_uf else None for s in siglas
    }
    intervalos: dict[str, tuple[float, float]] = {}
    estimados: list[str] = []
    como_ler = ""
    if len(proprio) >= MINIMO_DE_ERROS:
        baixo, alto = _quantil(proprio, 0.1), _quantil(proprio, 0.9)
        for s in por_uf:
            v = valores[s]
            if v is not None:
                intervalos[s] = (v + baixo, v + alto)
        como_ler = (
            f"O traço é a faixa de erro: de {de} a {ate}, em 8 de cada 10 vezes o PIB oficial "
            f"ficou entre {br(abs(baixo))} ponto abaixo e {br(alto)} acima do IBC-R do estado"
        )
    if len(pela_regiao) >= MINIMO_DE_ERROS:
        baixo, alto = _quantil(pela_regiao, 0.1), _quantil(pela_regiao, 0.9)
        for _, s, _, regiao in ufs:
            v = por_regiao.get(regiao, {}).get(ano)
            if s not in por_uf and v is not None:
                valores[s] = v
                intervalos[s] = (v + baixo, v + alto)
                estimados.append(s)
        como_ler += (
            f"; nos estados sem índice (ponto vazado), entre {br(abs(baixo))} abaixo e "
            f"{br(alto)} acima do número da região. A faixa é mais larga para cima porque "
            "esses estados costumam crescer mais que a região."
        )
    elif como_ler:
        como_ler += "."
    if estimados:
        regra = (
            f" Para os {len(estimados)} estados sem IBC-R ({', '.join(sorted(estimados))}), "
            "a regra é simples: o estado cresce como a região dele (o IBC-R da região). "
            "É previsão: erra bastante, e a faixa mostra quanto."
        )
        cods = ", ".join(str(SGS[f"IBCR_REGIAO_{c}"].codigo) for c in REGIOES.values())
        fonte_ano = f"{fonte}; IBC-R das regiões (SGS {cods}); teste: IBGE, Contas Regionais"
    else:
        regra, fonte_ano = nota_fora, fonte
    previa = MetricaEstados(
        id="ibcr_ano",
        nome=f"Prévia do PIB de {ano}",
        descricao=(
            f"Previsão nossa para o crescimento de {ano}, que o IBGE só publica nas Contas "
            f"Regionais de {ano} (em novembro de {ano + 2}). Para os estados com IBC-R, é o "
            f"crescimento da média do índice no ano. Não é número oficial do PIB." + regra
        ),
        unidade="%",
        casas=1,
        referencia=str(ano),
        maior_e_melhor=True,
        fonte=fonte_ano,
        valores=valores,
        brasil=crescimento_anual(brasil).get(ano),
        grupo=ECONOMIA,
        intervalos=intervalos,
        estimados=sorted(estimados),
        como_ler=como_ler,
    )
    return [doze, previa]


# ------------------------------------------------------------------ PIB trimestral (estimativa)

PIB_TRIMESTRAL = (1620, 583, "c11255/90707")
"""SIDRA 1620, variável 583: série encadeada do índice de volume trimestral do PIB do Brasil
(média de 1995 = 100, sem ajuste sazonal), a mesma de `demografia.PIB_VOLUME`."""
FONTE_PIB_TRIMESTRAL = "IBGE, Contas Nacionais Trimestrais (SIDRA 1620)"


def pib_trimestral(
    ufs: UFs,
    sgs: Callable[[str], list[Ponto]],
    pib_brasil: list[Ponto],
    edicao: int,
    corrente: dict[str, dict[int, float]],
    volume: dict[str, dict[int, float]],
) -> list[MetricaEstados]:
    """PIB trimestral de cada estado, estimativa nossa (`modelos/pib_estados.py`): o
    crescimento contra o mesmo trimestre do ano anterior e a contribuição de cada estado para
    o crescimento do Brasil, em cada trimestre desde 2011.

    `pib_brasil` é o índice de volume trimestral do país; `corrente` e `volume` são as
    Contas Regionais (por nome do local, com "Brasil"). A faixa de erro só existe nos
    trimestres depois do último ano oficial: nos anteriores, o ano já fecha com o IBGE.
    """
    por_nome = _por_nome(ufs)
    siglas = [s for _, s, _, _ in ufs]
    regiao = {s: REGIOES[r] for _, s, _, r in ufs}
    proprio = {s: pib_estados.trimestral(sgs(f"IBCR_{s}")) for s in IBCR_UF}
    da_regiao = {r: pib_estados.trimestral(sgs(f"IBCR_REGIAO_{r}")) for r in IBCR_REGIAO}
    brasil = dict(pib_brasil)
    primeiro = min(volume["Brasil"])
    # Até o último trimestre que o PIB do Brasil, as regiões e todos os índices próprios têm.
    fim = min(max(p) for p in [brasil, *da_regiao.values(), *proprio.values()] if p)
    trimestres = sorted(
        t
        for t in brasil
        if t.year >= primeiro and t <= fim and all(t in p for p in da_regiao.values())
    )
    if len(trimestres) < 12 or (trimestres[0].month, len(set(trimestres))) != (1, len(trimestres)):
        raise ValueError("PIB trimestral dos estados: série curta ou sem o 1º trimestre")
    indicador: dict[str, list[float]] = {}
    for s in siglas:
        referencia = [da_regiao[regiao[s]][t] for t in trimestres]
        # Sem índice: a região. Índice que começa tarde: emendado para trás pela região.
        indicador[s] = (
            pib_estados.emendar(proprio[s], referencia, trimestres) if s in proprio else referencia
        )

    def com_indice(s: str, tri: date) -> bool:
        """O crescimento do estado no trimestre sai do IBC-R dele (e não do da região)?"""
        return s in proprio and tri in proprio[s] and date(tri.year - 1, tri.month, 1) in proprio[s]

    pib = [brasil[t] for t in trimestres]
    vol = {s: volume[n] for n, s in por_nome.items()}
    cor = {s: corrente[n] for n, s in por_nome.items()}
    e = pib_estados.estimar(trimestres, indicador, vol, cor, pib, corrente["Brasil"])
    cresc = {s: pib_estados.crescimento(e.indice[s]) for s in siglas}
    contrib = pib_estados.contribuicoes(e, pib)
    cresc_br = pib_estados.crescimento(pib)

    # A faixa: quanto o número do trimestre mudou quando saiu o PIB oficial do ano, separando
    # os trimestres em que o estado tinha índice próprio dos que saíram pela região.
    revisoes = pib_estados.revisoes(trimestres, indicador, vol, cor, pib, corrente["Brasil"], e)
    sem_indice = sorted(s for s in siglas if s not in IBCR_UF)
    com = [x for s in siglas for tri, x in revisoes[s] if com_indice(s, tri)]
    sem = [x for s in siglas for tri, x in revisoes[s] if not com_indice(s, tri)]
    f_com = f_sem = None
    como_ler = ""
    if len(com) >= MINIMO_DE_ERROS and len(sem) >= MINIMO_DE_ERROS:
        f_com = (_quantil(com, 0.1), _quantil(com, 0.9))
        f_sem = (_quantil(sem, 0.1), _quantil(sem, 0.9))
        como_ler = (
            "O traço é a faixa de erro. Refizemos a conta como se o IBGE ainda não tivesse "
            "publicado o PIB do ano: em 8 de cada 10 trimestres, o número refeito depois do "
            f"oficial ficou entre {br(abs(f_com[0]))} ponto abaixo e {br(f_com[1])} acima do "
            "estimado antes; nos estados sem IBC-R (ponto vazado), entre "
            f"{br(abs(f_sem[0]))} abaixo e {br(f_sem[1])} acima. O teste não vê o erro de "
            "repartir o ano entre os trimestres: seca ou safra forte num estado pode cair no "
            "trimestre errado."
        )

    def faixa(s: str, tri: date) -> tuple[float, float] | None:
        return f_com if com_indice(s, tri) else f_sem

    # Quem ganhou índice depois: até que ano o crescimento dele ainda sai pela região.
    tardios: dict[int, list[str]] = {}
    for s in sorted(proprio):
        comeco = min(proprio[s])
        if comeco > trimestres[0]:
            tardios.setdefault(comeco.year, []).append(s)
    tambem = " e ".join(
        f"{', '.join(quem[:-1])} e {quem[-1]} até {ano}"
        if len(quem) > 1
        else f"{quem[0]} até {ano}"
        for ano, quem in sorted(tardios.items())
    )

    def periodos(
        valores: dict[str, list[float | None]],
        casas: int,
        largura: Callable[[str, int], float],
        brasil_no_ranking: bool,
    ) -> list[PeriodoDaMetrica]:
        """Do trimestre mais novo ao mais antigo. `largura` multiplica a faixa de erro (1 no
        crescimento; a fatia do estado na contribuição)."""
        saida = []
        for t in range(len(trimestres) - 1, 3, -1):
            tri = trimestres[t]
            estimado = tri.year > e.ultimo_oficial
            vals = {s: valores[s][t] for s in siglas}
            do_brasil = cresc_br[t]
            nota = ""
            if do_brasil is not None and not brasil_no_ranking:
                nota = (
                    f"No {periodo(tri, 'T')}, o PIB do Brasil "
                    f"{'cresceu' if do_brasil >= 0 else 'caiu'} {br(abs(do_brasil))} % contra o "
                    f"mesmo trimestre de {tri.year - 1} (IBGE): é a soma dos 27 estados."
                )
            saida.append(
                PeriodoDaMetrica(
                    referencia=periodo(tri, "T") + (" (estimativa)" if estimado else ""),
                    valores={s: None if v is None else round(v, casas) for s, v in vals.items()},
                    brasil=round(do_brasil, casas)
                    if brasil_no_ranking and do_brasil is not None
                    else None,
                    intervalos={
                        s: (
                            round(v + f[0] * largura(s, t), casas),
                            round(v + f[1] * largura(s, t), casas),
                        )
                        for s, v in vals.items()
                        if estimado and v is not None and (f := faixa(s, tri)) is not None
                    },
                    nota=nota,
                    estimados=sorted(s for s in siglas if not com_indice(s, tri)),
                )
            )
        return saida

    codigos = ", ".join(str(SGS[f"IBCR_{s}"].codigo) for s in sorted(IBCR_UF))
    cods_reg = ", ".join(str(SGS[f"IBCR_REGIAO_{c}"].codigo) for c in REGIOES.values())
    fonte = (
        f"Conta nossa sobre {ibge_contas_regionais.FONTE} (edição {edicao}), "
        f"{FONTE_PIB_TRIMESTRAL} e Banco Central, IBC-R (SGS {codigos}; regiões: {cods_reg})"
    )
    metodo = (
        "O IBGE não publica PIB trimestral por estado: só o do Brasil, a cada trimestre, e o "
        f"dos estados uma vez por ano (o último é {e.ultimo_oficial}). A conta reparte o PIB "
        "trimestral do Brasil entre os estados pelo IBC-R do Banco Central, fechando com o "
        f"PIB oficial de cada estado até {e.ultimo_oficial}. Estado sem IBC-R (ponto vazado) "
        f"anda como a região: são {len(sem_indice)} hoje"
        + (f", e também {tambem}, antes de terem índice" if tambem else "")
        + ". Não é número oficial."
    )
    c = relatorios.CONFERENCIA_PIB_ESTADOS
    conferencia = (
        f"Conferência: contra o PIB trimestral que {len(c.estados)} estados publicam "
        f"({', '.join(c.estados[:-1])} e {c.estados[-1]}), a nossa conta ficou, em média, a "
        f"{br(c.diferenca_media)} ponto do número deles em {c.trimestres} trimestres desde "
        f"{c.desde}; em 8 de cada 10, entre {br(abs(c.faixa[0]))} abaixo e {br(c.faixa[1])} "
        f"acima (conferido em {c.lida_em:%d/%m/%Y})."
    )
    p_cresc = periodos(cresc, 2, lambda s, t: 1.0, True)
    p_contrib = periodos(contrib, 3, lambda s, t: e.pesos[s][t], False)
    return [
        MetricaEstados(
            id="pib_trimestre",
            nome="PIB no trimestre (estimativa)",
            descricao=(
                "Estimativa nossa de quanto a economia do estado cresceu no trimestre contra "
                f"o mesmo trimestre do ano anterior. {metodo}"
            ),
            unidade="%",
            casas=1,
            referencia=p_cresc[0].referencia,
            maior_e_melhor=True,
            fonte=fonte,
            valores=p_cresc[0].valores,
            brasil=p_cresc[0].brasil,
            grupo=ECONOMIA,
            intervalos=p_cresc[0].intervalos,
            estimados=p_cresc[0].estimados,
            como_ler=como_ler,
            conferencia=conferencia,
            periodos=p_cresc,
        ),
        MetricaEstados(
            id="pib_trimestre_contribuicao",
            nome="Contribuição para o PIB do Brasil (estimativa)",
            descricao=(
                "Quantos pontos do crescimento do PIB do Brasil vieram de cada estado: o peso "
                f"do estado na economia vezes o quanto ele cresceu. {metodo}"
            ),
            unidade="ponto percentual",
            casas=2,
            referencia=p_contrib[0].referencia,
            maior_e_melhor=None,
            fonte=fonte,
            valores=p_contrib[0].valores,
            grupo=ECONOMIA,
            intervalos=p_contrib[0].intervalos,
            estimados=p_contrib[0].estimados,
            como_ler=como_ler
            and (
                "O traço é a faixa de erro: a do crescimento do estado (veja a métrica "
                '"PIB no trimestre") vezes o peso dele na economia do país. Estado grande '
                "pesa mais, e por isso o traço dele é mais largo."
            ),
            periodos=p_contrib,
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


def exportacoes_no_pib(
    ufs: UFs,
    por_mes: dict[str, dict[int, float]],
    dolar: list[Ponto],
    pib_corrente: dict[str, dict[int, float]],
    ano: int,
    edicao: int,
) -> MetricaEstados:
    """Exportações do ano em % do PIB do estado no mesmo ano: cada mês em dólares vira reais
    pelo dólar médio do mês, e a soma vai sobre o PIB corrente das Contas Regionais."""
    cambio = {(d.year, d.month): v for d, v in dolar}
    faltam = [m for m in range(1, 13) if (ano, m) not in cambio]
    if faltam:
        raise RuntimeError(f"sem o dólar médio de {faltam} de {ano}")

    def em_reais(meses: dict[int, float]) -> float:
        return sum(v * cambio[(ano, m)] for m, v in meses.items())

    valores: dict[str, float | None] = {}
    soma_x = soma_pib = 0.0
    for _, sigla, nome, _ in ufs:
        pib_ano = pib_corrente.get(nome, {}).get(ano)
        if nome in por_mes and pib_ano:
            x = em_reais(por_mes[nome]) / 1e6  # R$ milhões, como o PIB
            valores[sigla] = round(x / pib_ano * 100, 2)
            soma_x += x
            soma_pib += pib_ano
        else:
            valores[sigla] = None
    pib_br = pib_corrente.get("Brasil", {}).get(ano)
    # O Brasil: todas as exportações do ano (com as sem estado declarado) sobre o PIB do país.
    total = sum(em_reais(m) for m in por_mes.values()) / 1e6
    return MetricaEstados(
        id="exportacoes_pib",
        nome="Exportações em % do PIB",
        descricao=(
            f"Quanto o estado vendeu ao exterior em {ano}, em reais, sobre tudo o que produziu "
            "no mesmo ano. Conta onde a mercadoria foi produzida, não o porto. Mostra o quanto "
            "a economia do estado depende de vender para fora."
        ),
        unidade="% do PIB do estado",
        casas=1,
        referencia=str(ano),
        maior_e_melhor=None,
        fonte=(
            f"{comexstat.FONTE} (valor FOB de {ano}, mês a mês, em reais pelo dólar médio do "
            f"mês do Banco Central, SGS 3698); {ibge_contas_regionais.FONTE} (edição {edicao}, "
            "PIB a preços correntes); cálculo próprio"
        ),
        valores=valores,
        brasil=round(total / pib_br * 100, 2) if pib_br else None,
        grupo=ECONOMIA,
    )


TOP_DA_FICHA = 6
"""Quantos produtos e países a ficha mostra; o resto vai em "Outros"."""


def _fatias_do_comercio(
    itens: dict[comexstat.Item, float], nome: Callable[[comexstat.Item], str], outros: str
) -> tuple[list[Fatia], float]:
    total = sum(v for v in itens.values() if v > 0)
    maiores = sorted(((i, v) for i, v in itens.items() if v > 0), key=lambda p: -p[1])
    fatias = [Fatia(nome=nome(i), valor=round(v / 1e6, 1)) for i, v in maiores[:TOP_DA_FICHA]]
    resto = total - sum(v for _, v in maiores[:TOP_DA_FICHA])
    if resto > 0:
        fatias.append(Fatia(nome=outros, valor=round(resto / 1e6, 1)))
    return fatias, total


@dataclass
class FichaDoComercio:
    numero: Cartao
    blocos: list[BlocoDeConta]


def exportacoes_da_ficha(
    ufs: UFs, fim: date, produtos: comexstat.PorEstado, paises: comexstat.PorEstado
) -> dict[str, FichaDoComercio]:
    """Por UF: o cartão com o total de 12 meses (a fatia do Brasil e a posição) e os dois
    blocos, o que vende e para onde."""
    ref = f"12 meses até {periodo(fim, 'M')}"
    fonte = f"{comexstat.FONTE}, exportações pelo estado de origem, valor FOB, {ref}"
    totais = {
        sigla: sum(v for v in produtos.get(nome, {}).values() if v > 0) for _, sigla, nome, _ in ufs
    }
    brasil = sum(sum(v for v in itens.values() if v > 0) for itens in produtos.values())
    com_dado = {s: v for s, v in totais.items() if v > 0}
    saida: dict[str, FichaDoComercio] = {}
    for _, sigla, nome, _ in ufs:
        if sigla not in com_dado:
            continue
        fat_prod, total = _fatias_do_comercio(
            produtos.get(nome, {}), comexstat.nome_curto, "Outros produtos"
        )
        fat_paises, _ = _fatias_do_comercio(paises.get(nome, {}), lambda i: i.nome, "Outros países")
        pos = 1 + sum(1 for v in com_dado.values() if v > com_dado[sigla])
        bilhoes = total / 1e9
        casas = 1 if bilhoes >= 1 else 2
        saida[sigla] = FichaDoComercio(
            numero=Cartao(
                id=f"{sigla.lower()}_exportacoes",
                rotulo="Exportações em 12 meses",
                valor=round(bilhoes, casas),
                unidade="US$ bilhões",
                casas=casas,
                referencia=fim,
                periodicidade="M",
                detalhe=(
                    f"{br(total / brasil * 100)} % do Brasil; {pos}ª maior de {len(com_dado)}"
                    if brasil
                    else f"{pos}ª maior de {len(com_dado)}"
                ),
                fonte=fonte,
            ),
            blocos=[
                BlocoDeConta(
                    id="exportacoes_produtos",
                    titulo="O que o estado vende ao exterior",
                    descricao="Os produtos mais vendidos, pelo estado onde foram produzidos.",
                    unidade="US$ milhões",
                    referencia=ref,
                    fonte=f"{fonte}, por posição do Sistema Harmonizado (SH4)",
                    fatias=fat_prod,
                    total=round(total / 1e6, 1),
                    compara=False,
                ),
                BlocoDeConta(
                    id="exportacoes_destinos",
                    titulo="Para onde vende",
                    descricao="Os países que mais compram do estado.",
                    unidade="US$ milhões",
                    referencia=ref,
                    fonte=f"{fonte}, por país de destino",
                    fatias=fat_paises,
                    total=round(sum(v for v in paises.get(nome, {}).values() if v > 0) / 1e6, 1),
                    compara=False,
                ),
            ],
        )
    return saida


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


def encadear_previa(pib: MetricaEstados, previa: MetricaEstados) -> None:
    """Põe o ano da prévia (IBC-R) na série do PIB, quando é o ano seguinte ao último do IBGE:
    assim a janela escolhida na tela pode ir até ele, marcada como previsão."""
    if not pib.anuais or not previa.referencia.isdigit():
        return
    ano = int(previa.referencia)
    if ano != max(pib.anuais.get("BR", {0: 0.0})) + 1:
        return
    pares = [*previa.valores.items(), ("BR", previa.brasil)]
    for sigla, cresc in pares:
        serie = pib.anuais.get(sigla)
        if cresc is None or not serie or ano - 1 not in serie:
            continue
        serie[ano] = round(serie[ano - 1] * (1 + cresc / 100), 6)
    pib.ano_previsto = ano


def frase_pib(m: MetricaEstados) -> str:
    v = {u: x for u, x in m.valores.items() if x is not None}
    if not v:
        return ""
    alto, baixo = max(v, key=lambda u: v[u]), min(v, key=lambda u: v[u])
    brasil = f", contra {br(m.brasil)} % no país" if m.brasil is not None else ""
    # "cresceu de -4,4 %" não se lê: com estado em queda, a frase diz queda e alta.
    if v[baixo] < 0:
        return (
            f"Em {m.referencia}, o PIB foi de uma queda de {br(-v[baixo])} % ({baixo}) a "
            f"uma alta de {br(v[alto])} % ({alto}){brasil}."
        )
    return (
        f"Em {m.referencia}, o PIB cresceu de {br(v[baixo])} % ({baixo}) a "
        f"{br(v[alto])} % ({alto}){brasil}."
    )
