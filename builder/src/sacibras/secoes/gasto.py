"""Onde está o gasto público: o que é obrigatório, o que não é, e o Brasil contra os outros
países por função (Caio, 16/11/2026: *"tem como separar as despesas das obrigatórias? Talvez
fazer uma análise de onde dá pra cortar gastos, se puder também comparar com outros
países"*).

Duas fontes, dois recortes, ditos na tela:
- o Resultado do Tesouro (RTN) separa a despesa do **Governo Central** em obrigatória e
  discricionária, mês a mês;
- o COFOG do FMI dá a despesa do **governo geral** (União, estados e municípios) por função,
  no mesmo conceito para dezenas de países. Os grupos são a mediana dos países de cada um,
  cada país no ano mais novo que tem, até o ano do Brasil e no máximo três anos antes.
"""

from __future__ import annotations

from datetime import date
from statistics import median

from sacibras import contas
from sacibras.fontes import fmi, fmi_cofog
from sacibras.schema import Cartao, Grafico, LinhaTabela, Tabela
from sacibras.secoes.base import br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto

GRUPOS = {"G200": "Emergentes", "G205": "América Latina", "G110": "Avançados"}
"""Os grupos do FMI com que o Brasil se compara, na ordem das colunas."""
PRINCIPAIS = {f for f in fmi_cofog.FUNCOES if len(f) == len("GF10_T")}
"""As dez funções; as outras são subfunções (juros, velhice, pensão por morte)."""
ANOS_DE_FOLGA = 3
"""Um país entra no grupo com o dado mais novo dele, se for de até três anos antes do Brasil."""


def _somar(*series: list[Ponto]) -> list[Ponto]:
    por_mes = [dict(s) for s in series]
    meses = set.intersection(*(set(s) for s in por_mes))
    return [(d, sum(s[d] for s in por_mes)) for d in sorted(meses)]


def _em_12_meses(mensal: list[Ponto]) -> list[Ponto]:
    return [(d, v) for d, v in contas.soma_movel(mensal, 12)]


def rigidez(
    rtn: dict[str, list[Ponto]], pib: list[Ponto], fonte: str, inicio: date
) -> tuple[list[Cartao], list[Grafico], list[Tabela]]:
    """A despesa do Governo Central em obrigatória e discricionária (RTN, aba 1.1)."""
    obrigatoria = _somar(
        rtn["rgps"], rtn["pessoal"], rtn["outras_obrigatorias"], rtn["obrigatorias_fluxo"]
    )
    discricionaria = rtn["discricionarias"]
    # A tabela só abre a discricionária a partir de 2009 (antes a linha vem zerada): os
    # gráficos começam no primeiro mês com 12 meses dela.
    primeiro = next(d for d, v in discricionaria if v)
    desde = max(inicio, date(primeiro.year + 1, primeiro.month, 1))
    obrig_pib = [p for p in contas.em_pct_do_pib(obrigatoria, pib) if p[0] >= desde]
    discr_pib = [p for p in contas.em_pct_do_pib(discricionaria, pib) if p[0] >= desde]
    total_12 = dict(_em_12_meses(rtn["despesa_total"]))
    discr_12 = _em_12_meses(discricionaria)
    parte = [(d, v / total_12[d] * 100) for d, v in discr_12 if total_12.get(d)]
    quando = parte[-1][0]
    em_bi = dict(discr_12)[quando] / 1000
    cartoes = [
        cartao(
            "discricionaria-parte",
            "Parte discricionária da despesa",
            parte,
            unidade="% da despesa",
            periodicidade="M",
            casas=1,
            detalhe=f"discricionária, 12 meses: R$ {br(em_bi, 0)} bi",
            fonte=fonte,
            procedencia="calculado",
            secao="fiscal",
            mini=120,
        ),
        cartao(
            "obrigatoria-pib",
            "Despesa obrigatória, 12 meses",
            obrig_pib,
            unidade="% do PIB",
            periodicidade="M",
            casas=1,
            detalhe=f"discricionária: {br(discr_pib[-1][1])} % do PIB",
            fonte=fonte,
            procedencia="calculado",
            secao="fiscal",
            mini=120,
        ),
    ]
    graficos = [
        grafico(
            "despesa-rigidez",
            "Despesa obrigatória e discricionária",
            [
                serie("obrigatoria", "Obrigatória", obrig_pib),
                serie("discricionaria", "Discricionária", discr_pib),
            ],
            unidade="% do PIB, em 12 meses",
            casas=1,
            periodicidade="M",
            janela_anos=15,
            fonte=fonte,
            nota=(
                "Governo Central. Obrigatória: a que a Constituição ou a lei manda pagar "
                "(benefícios do INSS, pessoal, BPC, abono e seguro-desemprego, os mínimos de "
                "saúde e educação e as demais da tabela 1.1 do Tesouro). Discricionária: a que "
                "o governo decide no ano, como investimento e custeio da máquina."
            ),
        )
    ]

    # A tabela dos últimos 12 meses, por tipo de despesa.
    def ultimo(mensal: list[Ponto]) -> float:
        return dict(_em_12_meses(mensal))[quando] / 1000

    total = total_12[quando] / 1000
    pib_q = dict(pib)[quando] / 1000
    demais = ultimo(rtn["outras_obrigatorias"]) - ultimo(rtn["bpc"]) - ultimo(rtn["abono_seguro"])
    itens = [
        ("Benefícios do INSS", ultimo(rtn["rgps"]), "Obrigatória"),
        ("Pessoal e encargos", ultimo(rtn["pessoal"]), "Obrigatória"),
        (
            "BPC (idosos e pessoas com deficiência de baixa renda)",
            ultimo(rtn["bpc"]),
            "Obrigatória",
        ),
        ("Abono salarial e seguro-desemprego", ultimo(rtn["abono_seguro"]), "Obrigatória"),
        ("Demais obrigatórias (Fundeb, precatórios, subsídios…)", demais, "Obrigatória"),
        (
            "Obrigatórias com controle de fluxo (saúde, Bolsa Família…)",
            ultimo(rtn["obrigatorias_fluxo"]),
            "Obrigatória",
        ),
        ("Discricionárias (investimento e custeio)", ultimo(discricionaria), "Discricionária"),
    ]
    tabela = Tabela(
        id="despesa-obrigatoria",
        titulo="A despesa do Governo Central, do que é obrigatório ao que não é",
        subtitulo=f"12 meses até {periodo(quando, 'M')}",
        colunas=["R$ bilhões", "% da despesa", "% do PIB"],
        linhas=[
            LinhaTabela(
                rotulo=nome,
                valores=[round(v, 1), round(v / total * 100, 1), round(v / pib_q * 100, 2)],
                unidade="",
                casas=1,
                grupo=grupo,
            )
            for nome, v, grupo in itens
        ],
        fonte=fonte,
        nota=(
            "Conta nossa sobre a tabela 1.1 do Tesouro: as linhas somam a despesa total. "
            '"Obrigatórias com controle de fluxo" são obrigatórias cujo ritmo de pagamento o '
            "governo controla ao longo do ano (o Bolsa Família e boa parte da saúde, por "
            "exemplo), não o valor do ano. Cortar a despesa obrigatória pede mudar a lei ou a "
            "Constituição que a criou; a discricionária se corta no orçamento, mas também tem "
            "piso: parte dela conta para os mínimos de saúde e educação."
        ),
    )
    return cartoes, graficos, [tabela]


def _arredondar(v: float | None) -> float | None:
    return None if v is None else round(v, 1)


def _mediana_do_grupo(
    dados: fmi_cofog.PorPais, paises: list[str], funcao: str, ano: int
) -> tuple[float | None, int]:
    valores: list[float] = []
    for iso in paises:
        if iso == "BRA" or iso not in dados or funcao not in dados[iso]:
            continue
        anos = [a for a in dados[iso][funcao] if ano - ANOS_DE_FOLGA <= a <= ano]
        if not anos:
            continue
        valor = dados[iso][funcao][max(anos)]
        # Na subfunção (código de quatro algarismos), zero é quase sempre "não abriu o total",
        # não "não gasta": fica de fora da mediana.
        if valor == 0 and funcao not in PRINCIPAIS:
            continue
        valores.append(valor)
    return (median(valores) if valores else None), len(valores)


def contra_os_paises(
    dados: fmi_cofog.PorPais, grupos: dict[str, list[str]]
) -> tuple[list[Cartao], list[Tabela]]:
    """O gasto do governo geral por função, o Brasil contra a mediana de cada grupo."""
    brasil = dados["BRA"]
    ano = max(brasil["GF10_T"])
    colunas: list[str] = ["Brasil"]
    medianas: dict[str, dict[str, float | None]] = {}
    for codigo, nome in GRUPOS.items():
        membros = grupos.get(codigo, [])
        _, n = _mediana_do_grupo(dados, membros, "GF10_T", ano)
        colunas.append(f"{nome} ({n})")
        medianas[codigo] = {
            f: _mediana_do_grupo(dados, membros, f, ano)[0] for f in fmi_cofog.FUNCOES
        }
    colunas.append("Brasil menos emergentes")
    linhas: list[LinhaTabela] = []
    acima: list[tuple[float, str, float, float]] = []
    for f, nome in fmi_cofog.FUNCOES.items():
        b = brasil.get(f, {}).get(ano)
        emerg = medianas["G200"][f]
        diferenca = b - emerg if b is not None and emerg is not None else None
        linhas.append(
            LinhaTabela(
                rotulo=nome,
                valores=[
                    None if b is None else round(b, 1),
                    *(_arredondar(medianas[g][f]) for g in GRUPOS),
                    None if diferenca is None else round(diferenca, 1),
                ],
                unidade="% do PIB",
                casas=1,
            )
        )
        if diferenca is not None and not nome.startswith(" "):
            acima.append((diferenca, nome, b or 0.0, emerg or 0.0))
    fonte = f"{fmi_cofog.FONTE}; grupos do FMI (World Economic Outlook); medianas: conta nossa"
    tabela = Tabela(
        id="gasto-por-funcao",
        titulo="Onde o governo gasta: o Brasil e os outros países",
        subtitulo=(
            f"% do PIB, governo geral (União, estados e municípios); Brasil em {ano}; os outros, "
            f"o ano mais novo de cada um entre {ano - ANOS_DE_FOLGA} e {ano}"
        ),
        colunas=colunas,
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Grupos: a mediana dos países de cada grupo do FMI que publicam o gasto por função "
            "(entre parênteses, quantos). A classificação é a da ONU (COFOG), a mesma para "
            'todos. Os juros da dívida estão dentro de "Serviços públicos gerais", e a '
            'velhice e a pensão por morte dentro de "Proteção social"; vêm à parte porque '
            "pesam muito no Brasil; nelas, quem informa zero fica fora da mediana (quase "
            "sempre é quem não abre o total). Gastar mais que os outros numa função não diz, "
            "sozinho, "
            "que dá para cortar: pode ser escolha (a população envelhecida, a rede de "
            "proteção) ou ineficiência, e esses dados não separam as duas."
        ),
    )
    acima.sort(reverse=True)
    cartoes: list[Cartao] = []
    if acima:
        dif, nome, b, e = acima[0]
        cartoes.append(
            Cartao(
                id="gasto-acima-pares",
                rotulo="Onde o Brasil mais gasta acima dos emergentes",
                valor=round(dif, 2),
                unidade="pp do PIB",
                casas=1,
                referencia=date(ano, 1, 1),
                periodicidade="A",
                detalhe=f"{nome.lower()}: {br(b)} % contra {br(e)} %"[:60],
                fonte=fonte,
                procedencia="calculado",
                secao="fiscal",
            )
        )
    return cartoes, [tabela]


def pecas_dos_paises() -> tuple[list[Cartao], list[Tabela]]:
    dados = fmi_cofog.por_funcao(2015)
    if "BRA" not in dados or "GF10_T" not in dados["BRA"]:
        raise RuntimeError("o COFOG do FMI veio sem o Brasil")
    return contra_os_paises(dados, fmi.grupos())
