"""Os servidores públicos: quanto custa a folha, quem fica com mais e o contracheque contra o
do setor privado (Caio, 19/11/2026: *"inclua a distribuição dos gastos por servidores
públicos (quem fica com mais) e compare o rendimento e benefícios dos servidores com o setor
privado"*).

Cinco recortes, cada um com a fonte dele dita na tela:
- **por esfera** (União, estados, municípios), na ativa e aposentados: o Government Finance
  Statistics do FMI, que também dá o Brasil contra os outros países;
- **dentro da União, por tipo** (civil e militar, ativo e inativo): o Resultado do Tesouro;
- **dentro da União, por poder**: o Relatório de Gestão Fiscal (Siconfi) dá o gasto, e a
  avaliação atuarial do PLDO, quantos são e quanto ganham em média (`relatorios.py`);
- **o rendimento contra o setor privado**: a PNAD Contínua, por posição na ocupação;
- **a aposentadoria contra a do INSS**: a avaliação atuarial e o boletim da Previdência.

A comparação de rendimento é de médias: o servidor tem, em média, mais escola e mais idade
que o empregado do setor privado, e estes dados não separam o quanto da diferença vem disso.
"""

from __future__ import annotations

from datetime import date

from sacibras import contas, relatorios
from sacibras.fontes import fmi, fmi_pessoal, ibge_sidra, siconfi, tesouro_rtn
from sacibras.schema import Cartao, Grafico, LinhaTabela, Tabela
from sacibras.secoes import gasto
from sacibras.secoes.base import br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto

Pecas = tuple[list[Cartao], list[Grafico], list[Tabela]]

# ------------------------------------------------------------------ PNAD Contínua

TABELA_RENDIMENTO = 6389
"""Rendimento médio real habitual do trabalho principal, por posição na ocupação (variável
5932, trimestre móvel, a preços do último mês). Categorias da classificação 11913 conferidas
em `servicodados.ibge.gov.br/api/v3/agregados/6389/metadados` em 19/11/2026."""
TABELA_PESSOAS = 6320
"""As pessoas ocupadas, pela mesma classificação (variável 4090, mil pessoas)."""
CLASSIFICACAO = "c11913"
ESTATUTARIO = "31730"
PRIVADO_COM_CARTEIRA = "31722"
POSICOES: dict[str, tuple[str, str]] = {
    ESTATUTARIO: ("Servidor estatutário ou militar", "Setor público"),
    "31728": ("Setor público, com carteira", "Setor público"),
    "31729": ("Setor público, sem carteira", "Setor público"),
    PRIVADO_COM_CARTEIRA: ("Setor privado, com carteira", "Setor privado"),
    "31723": ("Setor privado, sem carteira", "Setor privado"),
    "31724": ("Trabalhador doméstico", "Setor privado"),
    "96171": ("Por conta própria", "Por conta própria e empregador"),
    "96170": ("Empregador", "Por conta própria e empregador"),
    "96165": ("Todos os ocupados", "Todos"),
}
NO_GRAFICO = (ESTATUTARIO, "31728", PRIVADO_COM_CARTEIRA, "31723")
TABELA_INSTRUCAO = 5438
"""O mesmo rendimento por nível de instrução (trimestral; classificação 1568, conferida no
mesmo serviço em 19/11/2026): 11632 superior completo, 11630 médio completo."""
INSTRUCAO = {"11632": "Com ensino superior completo", "11630": "Com ensino médio completo"}
FONTE_PNAD = f"IBGE, PNAD Contínua (SIDRA {TABELA_RENDIMENTO} e {TABELA_PESSOAS})"


def rendimento(
    por_posicao: dict[str, list[Ponto]],
    pessoas: dict[str, list[Ponto]],
    por_instrucao: dict[str, list[Ponto]],
    inicio: date,
) -> Pecas:
    """O rendimento do servidor contra o do empregado do setor privado."""
    servidor, privado = por_posicao[ESTATUTARIO], por_posicao[PRIVADO_COM_CARTEIRA]
    quando = servidor[-1][0]
    base = dict(privado)[quando]
    vezes = servidor[-1][1] / base
    cartoes = [
        cartao(
            "servidor-rendimento",
            "Rendimento do servidor estatutário",
            servidor,
            unidade="R$",
            periodicidade="M",
            casas=0,
            detalhe=f"{br(vezes)} vezes o do privado com carteira (R$ {br(base, 0)})",
            fonte=FONTE_PNAD,
            secao="fiscal",
            mini=120,
        )
    ]
    graficos = [
        grafico(
            "rendimento-publico-privado",
            "Quanto ganha o servidor e o empregado privado",
            [
                serie(f"p{codigo}", POSICOES[codigo][0], por_posicao[codigo], desde=inicio, casas=0)
                for codigo in NO_GRAFICO
                if codigo in por_posicao
            ],
            unidade="R$",
            casas=0,
            periodicidade="M",
            janela_anos=10,
            fonte=f"{FONTE_PNAD}, a preços do último mês",
            # Rendimento médio habitual do trabalho principal. Estatutário: o servidor
            # concursado, com estabilidade; inclui os militares e as três esferas.
            nota=(
                "Rendimento médio por mês, sem a inflação. É comparação de médias: o servidor "
                "tem mais escola e idade, e estes dados não separam o peso disso."
            ),
        )
    ]
    linhas: list[LinhaTabela] = []
    for codigo, (nome, grupo) in POSICOES.items():
        if codigo not in por_posicao:
            continue
        valor = dict(por_posicao[codigo]).get(quando)
        gente = dict(pessoas.get(codigo, [])).get(quando)
        linhas.append(
            LinhaTabela(
                rotulo=nome,
                valores=[
                    valor,
                    None if gente is None else round(gente),
                    None if valor is None else round(valor / base * 100),
                ],
                unidade="",
                casas=0,
                grupo=grupo,
            )
        )
    subtitulo = f"Trimestre encerrado em {periodo(quando, 'M')}"
    for codigo, nome in INSTRUCAO.items():
        pontos = por_instrucao.get(codigo)
        if not pontos:
            continue
        d, valor = pontos[-1]
        linhas.append(
            LinhaTabela(
                rotulo=f"{nome} ({periodo(d, 'T')})",
                valores=[valor, None, round(valor / base * 100)],
                unidade="",
                casas=0,
                grupo="Por escolaridade (todos os ocupados)",
            )
        )
    tabela = Tabela(
        id="rendimento-por-posicao",
        titulo="Rendimento do trabalho, por posição",
        subtitulo=subtitulo,
        colunas=[
            "Rendimento médio (R$ por mês)",
            "Pessoas (mil)",
            "Para cada R$ 100 do privado com carteira",
        ],
        linhas=linhas,
        fonte=f"{FONTE_PNAD}; por escolaridade: SIDRA {TABELA_INSTRUCAO}",
        # Boa parte dos servidores tem ensino superior (professores, médicos, juízes). Sem o
        # cruzamento de posição com escolaridade, não dá para dizer quanto o mesmo profissional
        # ganharia a mais ou a menos no governo. O empregado com carteira tem FGTS e
        # seguro-desemprego.
        nota=(
            "Quem tem ensino superior ganha mais em qualquer setor, e o IBGE não cruza posição "
            "com escolaridade. Fora do contracheque, o estatutário tem estabilidade e não tem "
            "FGTS."
        ),
    )
    return cartoes, graficos, [tabela]


def pecas_do_rendimento(inicio: date) -> Pecas:
    codigos = ",".join(POSICOES)
    por_posicao = ibge_sidra.series(
        TABELA_RENDIMENTO, 5932, classificacao=f"{CLASSIFICACAO}/{codigos}", por="Posição"
    )
    pessoas = ibge_sidra.series(
        TABELA_PESSOAS,
        4090,
        periodos="last 4",
        classificacao=f"{CLASSIFICACAO}/{codigos}",
        por="Posição",
    )
    try:
        por_instrucao = ibge_sidra.series(
            TABELA_INSTRUCAO,
            5932,
            periodos="last 4",
            classificacao="c1568/" + ",".join(INSTRUCAO),
            por="Nível",
            trimestral=True,
        )
    except Exception as erro:
        print(f"    o rendimento por escolaridade ficou de fora: {str(erro)[:100]}")
        por_instrucao = {}
    return rendimento(por_posicao, pessoas, por_instrucao, inicio)


# ------------------------------------------------------------------ a folha da União (RTN)

TIPOS = {
    "ativo_civil": "Civis na ativa",
    "inativo_civil": "Aposentadorias e pensões civis",
    "ativo_militar": "Militares na ativa",
    "inativo_militar": "Reformas e pensões militares",
}


def folha_da_uniao(
    det: dict[str, list[Ponto]], pib: list[Ponto], fonte: str, inicio: date
) -> Pecas:
    """A folha do Governo Central por tipo de servidor (RTN, aba 1.5, valor pago)."""
    em_12 = {nome: dict(contas.soma_movel(det[nome], 12)) for nome in (*TIPOS, "pessoal_pago")}
    quando = max(em_12["pessoal_pago"])
    total = em_12["pessoal_pago"][quando] / 1000
    pib_q = dict(pib)[quando] / 1000
    inativos = [
        (d, (em_12["inativo_civil"][d] + em_12["inativo_militar"][d]) / v * 100)
        for d, v in sorted(em_12["pessoal_pago"].items())
        if v and d in em_12["inativo_civil"] and d in em_12["inativo_militar"]
    ]
    cartoes = [
        cartao(
            "folha-inativos",
            "Aposentados e pensionistas na folha da União",
            inativos,
            unidade="% da folha",
            periodicidade="M",
            casas=1,
            detalhe=f"folha em 12 meses: R$ {br(total, 0)} bi ({br(total / pib_q * 100)} % do PIB)",
            fonte=fonte,
            procedencia="calculado",
            secao="fiscal",
            mini=120,
        )
    ]
    graficos = [
        grafico(
            "folha-uniao",
            "A folha da União: ativos e aposentados",
            [
                serie(nome, rotulo, contas.em_pct_do_pib(det[nome], pib), desde=inicio)
                for nome, rotulo in TIPOS.items()
            ],
            unidade="% do PIB, em 12 meses",
            casas=2,
            periodicidade="M",
            janela_anos=15,
            fonte=fonte,
            nota=(
                "Governo Central, pelo valor pago. Militares: Forças Armadas (reformas são as "
                "aposentadorias deles). Ficam fora do desenho os precatórios de pessoal."
            ),
        )
    ]
    itens = [(rotulo, em_12[nome][quando] / 1000) for nome, rotulo in TIPOS.items()]
    itens.append(("Sentenças judiciais e outros", total - sum(v for _, v in itens)))
    tabela = Tabela(
        id="folha-uniao",
        titulo="A folha da União, por tipo de servidor",
        subtitulo=f"12 meses até {periodo(quando, 'M')}",
        colunas=["R$ bilhões", "% da folha", "% do PIB"],
        linhas=[
            LinhaTabela(
                rotulo=nome,
                valores=[round(v, 1), round(v / total * 100, 1), round(v / pib_q * 100, 2)],
                unidade="",
                casas=1,
            )
            for nome, v in itens
        ],
        fonte=fonte,
        nota=(
            "Conta nossa sobre a tabela 1.5 do Tesouro: as linhas somam a despesa de pessoal e "
            "encargos sociais. As contribuições que os servidores e os militares pagam para a "
            "própria aposentadoria entram como receita, não aqui."
        ),
    )
    return cartoes, graficos, [tabela]


# ------------------------------------------------------------------ por poder (Siconfi + PLDO)


def por_poder(ano: int, gasto_do_poder: dict[str, tuple[float, int]]) -> list[Tabela]:
    """Quanto da folha da União vai para cada poder, e quanto ganha em média o servidor civil
    de cada um."""
    total = sum(v for v, _ in gasto_do_poder.values())
    fonte_rgf = (
        f"Tesouro Nacional, Siconfi, Relatório de Gestão Fiscal da União (anexo 1, {ano}); "
        "soma dos órgãos: conta nossa"
    )
    gasto_tabela = Tabela(
        id="folha-por-poder",
        titulo="A folha da União, por poder",
        subtitulo=f"Despesa bruta com pessoal em {ano}, ativos e inativos",
        colunas=["R$ bilhões", "% do total"],
        linhas=[
            LinhaTabela(
                rotulo=siconfi.PODERES_DA_UNIAO[poder],
                valores=[round(v / 1e9, 1), round(v / total * 100, 1)],
                unidade="",
                casas=1,
            )
            for poder, (v, _) in sorted(gasto_do_poder.items(), key=lambda x: -x[1][0])
        ],
        fonte=fonte_rgf,
        # No Executivo entram os militares e o pessoal que a União paga do Distrito Federal,
        # do Amapá e de Roraima. A Defensoria informa só a despesa líquida.
        nota=(
            "Relatórios de Gestão Fiscal dos órgãos, somados por poder. Conceito da LRF (por "
            "competência), um pouco diferente do valor pago que o Tesouro publica."
        ),
    )
    civis = relatorios.SERVIDORES_POR_PODER
    ativos = sum(p.ativos for p in civis)
    media = sum(p.ativos * p.remuneracao for p in civis) / ativos
    aposentados = sum(p.aposentados for p in civis)
    media_apos = sum(p.aposentados * p.provento for p in civis) / aposentados
    linhas = [
        LinhaTabela(
            rotulo=p.poder,
            valores=[
                round(p.ativos / 1000, 1),
                round(p.remuneracao),
                round(p.aposentados / 1000, 1),
                round(p.provento),
                round(p.pensao),
            ],
            unidade="",
            casas=0,
            grupo="Servidores civis",
        )
        for p in sorted(civis, key=lambda p: -p.remuneracao)
    ]
    linhas.append(
        LinhaTabela(
            rotulo="Todos os civis (média ponderada, conta nossa)",
            valores=[
                round(ativos / 1000, 1),
                round(media),
                round(aposentados / 1000, 1),
                round(media_apos),
                None,
            ],
            unidade="",
            casas=0,
            grupo="Servidores civis",
        )
    )
    inativos = dict((nome, (n, v)) for nome, n, v in relatorios.MILITARES_INATIVOS)
    for nome, n, v in relatorios.MILITARES_ATIVOS:
        if not nome.endswith("de carreira") or nome.startswith("Praças especiais"):
            continue
        tipo = nome.split()[0]
        n_inativo, v_inativo = inativos.get(tipo, (None, None))
        linhas.append(
            LinhaTabela(
                rotulo=nome,
                valores=[
                    round(n / 1000, 1),
                    round(v),
                    None if n_inativo is None else round(n_inativo / 1000, 1),
                    None if v_inativo is None else round(v_inativo),
                    None,
                ],
                unidade="",
                casas=0,
                grupo="Militares das Forças Armadas",
            )
        )
    remuneracao_tabela = Tabela(
        id="remuneracao-por-poder",
        titulo="Ganho médio do servidor da União, por poder",
        subtitulo=(
            f"R$ por mês; civis em {periodo(relatorios.SERVIDORES_EM, 'M')}, militares em 2025"
        ),
        colunas=[
            "Na ativa (mil pessoas)",
            "Remuneração média",
            "Aposentados (mil)",
            "Aposentadoria média",
            "Pensão média",
        ],
        linhas=linhas,
        fonte=f"{relatorios.FONTE_SERVIDORES}; {relatorios.FONTE_MILITARES}",
        # Lido nas avaliações atuariais do PLDO, uma vez por ano. Num mesmo poder há carreiras
        # de salário muito diferente (no Judiciário, o juiz e o técnico). Os temporários são a
        # maioria (recrutas); a aposentadoria dos militares junta todos os oficiais e praças.
        nota=(
            "Média de todos os cargos de cada poder, que esconde a distância entre carreiras. "
            "Dos militares, só os de carreira; os temporários ganham bem menos."
        ),
    )
    return [gasto_tabela, remuneracao_tabela]


def aposentadoria() -> tuple[list[Cartao], list[Tabela]]:
    """A aposentadoria média do servidor civil da União contra a do INSS (leituras)."""
    civis = relatorios.SERVIDORES_POR_PODER
    aposentados = sum(p.aposentados for p in civis)
    media = sum(p.aposentados * p.provento for p in civis) / aposentados
    inss = relatorios.INSS_APOSENTADORIA_MEDIA
    fonte = (
        f"{relatorios.FONTE_SERVIDORES}; {relatorios.FONTE_INSS} "
        f"({periodo(relatorios.INSS_EM, 'M')}, quadro 15); {relatorios.FONTE_TETOS}"
    )
    card = Cartao(
        id="aposentadoria-servidor",
        rotulo="Aposentadoria média do servidor civil da União",
        valor=round(media, 2),
        unidade="R$",
        casas=0,
        referencia=relatorios.SERVIDORES_EM,
        periodicidade="M",
        detalhe=f"INSS: R$ {br(inss, 0)} em média ({br(media / inss)} vezes menos)",
        fonte=fonte,
        procedencia="calculado",
        secao="fiscal",
    )

    def linha(nome: str, valor: float, grupo: str, gente: float | None = None) -> LinhaTabela:
        return LinhaTabela(
            rotulo=nome,
            valores=[round(valor), None if gente is None else round(gente / 1000)],
            unidade="",
            casas=0,
            grupo=grupo,
        )

    linhas = [
        linha(f"Servidor civil: {p.poder}", p.provento, "Servidores da União", p.aposentados)
        for p in sorted(civis, key=lambda p: -p.provento)
    ]
    linhas.append(
        linha("Servidor civil: todos (conta nossa)", media, "Servidores da União", aposentados)
    )
    linhas += [
        linha(f"Militar: {nome.lower()}", v, "Servidores da União", n)
        for nome, n, v in relatorios.MILITARES_INATIVOS
    ]
    linhas += [
        linha(
            "INSS: todas as aposentadorias",
            inss,
            "Setor privado (INSS)",
            relatorios.INSS_APOSENTADORIAS,
        ),
        linha(
            "INSS: por tempo de contribuição",
            relatorios.INSS_APOSENTADORIA_TEMPO,
            "Setor privado (INSS)",
        ),
        linha("INSS: por idade", relatorios.INSS_APOSENTADORIA_IDADE, "Setor privado (INSS)"),
        linha(f"Teto do INSS em {relatorios.TETO_INSS_ANO}", relatorios.TETO_INSS, "Os tetos"),
        linha(
            "Teto do serviço público (subsídio de ministro do STF)",
            relatorios.TETO_SERVICO_PUBLICO,
            "Os tetos",
        ),
    ]
    tabela = Tabela(
        id="aposentadoria-publico-privado",
        titulo="A aposentadoria do servidor e a do INSS",
        subtitulo=(
            f"Valor médio, R$ por mês; servidores em {periodo(relatorios.SERVIDORES_EM, 'M')}, "
            f"INSS em {periodo(relatorios.INSS_EM, 'M')}"
        ),
        colunas=["Valor médio (R$ por mês)", "Aposentados (mil)"],
        linhas=linhas,
        fonte=fonte,
        # Mais da metade das aposentadorias do INSS é por idade, com valor médio perto do
        # salário mínimo.
        nota=(
            "Regras diferentes: o servidor ganha mais na ativa e os mais antigos contribuíram "
            "sobre o salário inteiro; no INSS, tudo para no teto. Estados e municípios têm "
            "regimes próprios, fora daqui."
        ),
    )
    return [card], [tabela]


# ------------------------------------------------------------------ por esfera e por país (FMI)

INDICADORES = {
    fmi_pessoal.ATIVOS: "Servidores na ativa (salários e encargos)",
    fmi_pessoal.INATIVOS: "Aposentadorias e pensões de servidores",
}


def por_esfera(valores: fmi_pessoal.Valores) -> tuple[list[Grafico], list[Tabela]]:
    """Quem fica com a folha: União, estados e municípios, na ativa e aposentados."""
    geral = valores[("BRA", fmi_pessoal.GERAL, fmi_pessoal.ATIVOS, "POGDP_PT")]
    ano = max(geral)
    fonte = f"{fmi_pessoal.FONTE}; partes do total: conta nossa"

    def reais(setor: str, indicador: str) -> float:
        return valores.get(("BRA", setor, indicador, "XDC"), {}).get(ano, 0.0) / 1e9

    def pib(setor: str, indicador: str) -> float:
        return valores.get(("BRA", setor, indicador, "POGDP_PT"), {}).get(ano, 0.0)

    total = sum(reais(fmi_pessoal.GERAL, i) for i in INDICADORES)
    linhas = [
        LinhaTabela(
            rotulo=nome,
            valores=[
                round(reais(setor, indicador), 1),
                round(reais(setor, indicador) / total * 100, 1),
                round(pib(setor, indicador), 2),
            ],
            unidade="",
            casas=1,
            grupo=grupo,
        )
        for indicador, grupo in INDICADORES.items()
        for setor, nome in fmi_pessoal.ESFERAS.items()
    ]
    linhas.append(
        LinhaTabela(
            rotulo="As três esferas, ativos e aposentados",
            valores=[
                round(total, 1),
                100.0,
                round(sum(pib(fmi_pessoal.GERAL, i) for i in INDICADORES), 2),
            ],
            unidade="",
            casas=1,
            grupo="Total",
        )
    )
    tabela = Tabela(
        id="folha-quem-fica",
        titulo="Gasto com servidores: União, estados e municípios",
        subtitulo=f"{ano}, governo geral",
        colunas=["R$ bilhões", "% do total", "% do PIB"],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Na ativa, com a contribuição patronal; aposentadorias sem descontar o que o "
            "servidor contribui. Estados e municípios têm a maior parte dos professores, "
            "policiais e médicos."
        ),
    )

    def serie_da_esfera(setor: str) -> list[Ponto]:
        ativos = valores.get(("BRA", setor, fmi_pessoal.ATIVOS, "POGDP_PT"), {})
        inativos = valores.get(("BRA", setor, fmi_pessoal.INATIVOS, "POGDP_PT"), {})
        return [(date(a, 1, 1), ativos[a] + inativos[a]) for a in sorted(ativos) if a in inativos]

    desenho = grafico(
        "folha-por-esfera",
        "O gasto com servidores, por esfera de governo",
        [serie(setor, nome, serie_da_esfera(setor)) for setor, nome in fmi_pessoal.ESFERAS.items()],
        unidade="% do PIB",
        casas=2,
        periodicidade="A",
        fonte=fonte,
        nota="Servidores na ativa mais aposentadorias e pensões de servidores, em cada esfera.",
    )
    return [desenho], [tabela]


def contra_os_paises(
    paises: dict[str, dict[str, dict[int, float]]], grupos: dict[str, list[str]]
) -> tuple[list[Cartao], list[Tabela]]:
    """A folha do governo geral, o Brasil contra a mediana de cada grupo de países."""
    brasil = paises["BRA"]
    ano = max(brasil[fmi_pessoal.ATIVOS])
    colunas = ["Brasil"]
    medianas: dict[str, dict[str, float | None]] = {}
    quantos: dict[str, int] = {}
    for codigo, nome in gasto.GRUPOS.items():
        membros = grupos.get(codigo, [])
        medianas[codigo] = {}
        for indicador in INDICADORES:
            medianas[codigo][indicador], n = gasto._mediana_do_grupo(
                paises, membros, indicador, ano
            )
            if indicador == fmi_pessoal.ATIVOS:
                quantos[codigo] = n
        colunas.append(f"{nome} ({quantos[codigo]})")
    fonte = f"{fmi_pessoal.FONTE}; grupos do FMI (World Economic Outlook); medianas: conta nossa"

    def arredondar(v: float | None) -> float | None:
        return None if v is None else round(v, 1)

    tabela = Tabela(
        id="folha-paises",
        titulo="O gasto com servidores: o Brasil e os outros países",
        subtitulo=(
            f"% do PIB, governo geral; Brasil em {ano}, os outros entre "
            f"{ano - gasto.ANOS_DE_FOLGA} e {ano}"
        ),
        colunas=colunas,
        linhas=[
            LinhaTabela(
                rotulo=nome,
                valores=[
                    arredondar(brasil.get(indicador, {}).get(ano)),
                    *(arredondar(medianas[g][indicador]) for g in gasto.GRUPOS),
                ],
                unidade="% do PIB",
                casas=1,
            )
            for indicador, nome in INDICADORES.items()
        ],
        fonte=fonte,
        # Nas aposentadorias, menos países informam, e quem informa zero fica fora: em muitos
        # o servidor se aposenta pelo regime geral, e a despesa aparece em outra linha.
        nota=(
            "Mediana dos países de cada grupo do FMI (entre parênteses, quantos). Gastar mais "
            "pode vir de mais servidores, salário maior ou mais serviço público: estes dados "
            "não separam."
        ),
    )
    emergentes = medianas["G200"][fmi_pessoal.ATIVOS]
    b = brasil[fmi_pessoal.ATIVOS][ano]
    cartoes = [
        Cartao(
            id="folha-ativos-pib",
            rotulo="Servidores na ativa, as três esferas",
            valor=round(b, 2),
            unidade="% do PIB",
            casas=1,
            referencia=date(ano, 1, 1),
            periodicidade="A",
            detalhe=(
                ""
                if emergentes is None
                else f"emergentes: {br(emergentes)} % (mediana de {quantos['G200']} países)"
            ),
            fonte=fonte,
            procedencia="oficial",
            secao="fiscal",
            mini=[
                (date(a, 1, 1), round(v, 2)) for a, v in sorted(brasil[fmi_pessoal.ATIVOS].items())
            ],
        )
    ]
    return cartoes, [tabela]


# ------------------------------------------------------------------ tudo junto


def pecas(pib: list[Ponto], inicio: date, hoje: date) -> Pecas:
    """Todas as peças dos servidores; a fonte que falhar deixa só o pedaço dela de fora."""
    cartoes: list[Cartao] = []
    graficos: list[Grafico] = []
    tabelas: list[Tabela] = []

    def juntar(nome: str, montar: object) -> None:
        try:
            c, g, t = montar()  # type: ignore[operator]
        except Exception as erro:
            print(f"    servidores: {nome} ficou de fora: {str(erro)[:120]}")
            return
        cartoes.extend(c)
        graficos.extend(g)
        tabelas.extend(t)

    def do_fmi() -> Pecas:
        g, t = por_esfera(fmi_pessoal.brasil_por_esfera(2010))
        c, t2 = contra_os_paises(fmi_pessoal.paises(2015), fmi.grupos())
        return c, g, t + t2

    def do_rtn() -> Pecas:
        fonte = "Tesouro Nacional, Resultado do Tesouro Nacional (série histórica, tabela 1.5)"
        return folha_da_uniao(tesouro_rtn.detalhes(), pib, fonte, inicio)

    def do_siconfi() -> Pecas:
        achado = siconfi.pessoal_da_uniao_por_poder(hoje)
        if achado is None:
            raise RuntimeError("o RGF da União por poder não veio")
        return [], [], por_poder(*achado)

    def das_leituras() -> Pecas:
        c, t = aposentadoria()
        return c, [], t

    juntar("o FMI", do_fmi)
    juntar("a PNAD", lambda: pecas_do_rendimento(inicio))
    juntar("o RTN", do_rtn)
    juntar("o RGF por poder", do_siconfi)
    juntar("a aposentadoria", das_leituras)
    return cartoes, graficos, tabelas
