"""O endereço exato de cada fonte (Caio, 25/11/2026: *"Em todas as fontes, coloque o site de
onde estamos tirando a informação, o site exato"*).

O texto da `fonte` de cada peça é escrito à mão em muitos lugares; em vez de mudar cada um, o
site procura nele os padrões daqui e põe os endereços ao lado. Os padrões vão para
`fontes.json` (`gravar`) e valem em JavaScript e em Python (sem flags; a caixa conta).

Duas formas de regra:
- fixa: a regra casa e entra o endereço da página da fonte;
- por número (`por_numero`): o grupo 1 tem uma lista de códigos ("SGS 4189, 4390 e 13521";
  "SIDRA 6381 e 6392") e cada código vira um endereço próprio, com `{n}` no lugar dele.

Endereço novo só entra aberto e conferido na fonte (data no comentário). Fonte que não casa
com nenhuma regra aparece sem endereço: o `sem_endereco` serve ao teste e ao aviso do build.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel

from sacibras.fontes import sest


class Regra(BaseModel):
    padrao: str
    """Expressão regular (sintaxe comum a Python e JavaScript, sem flags)."""
    nome: str
    url: str
    por_numero: bool = False


# As leis das LDOs (`leis.METAS_DAS_LDOS`), no Senado: o id vem de
# legis.senado.leg.br/dadosabertos/legislacao/lista?tipo=LEI&numero=N&ano=A (25/11/2026).
LEIS_NO_SENADO: dict[str, int] = {
    "Lei nº 10.266/2001": 552142,
    "Lei nº 10.524/2002": 552400,
    "Lei nº 10.707/2003": 552583,
    "Lei nº 10.934/2004": 552810,
    "Lei nº 11.178/2005": 572717,
    "Lei nº 11.439/2006": 572591,
    "Lei nº 11.514/2007": 572666,
    "Lei nº 11.768/2008": 582190,
    "Lei nº 12.017/2009": 580240,
    "Lei nº 12.309/2010": 575951,
    "Lei nº 12.465/2011": 584321,
    "Lei nº 12.708/2012": 588084,
    "Lei nº 12.919/2013": 591367,
    "Lei nº 13.080/2015": 584892,
    "Lei nº 13.242/2015": 602467,
    "Lei nº 13.408/2016": 602632,
    "Lei nº 13.473/2017": 17745360,
    "Lei nº 13.707/2018": 27457218,
    "Lei nº 13.898/2019": 31666914,
    "Lei nº 14.116/2020": 33040572,
    "Lei nº 14.194/2021": 34722181,
    "Lei nº 14.436/2022": 36225432,
    "Lei nº 14.791/2023": 38065853,
    "Lei nº 15.080/2024": 40035025,
    "Lei nº 15.321/2025": 41912067,
    "Lei nº 14.520/2023": 36753460,
}


_NUMEROS = r"(\d{1,6}(?:(?:,\s*|\s+e\s+)\d{1,6})*)"

REGRAS: list[Regra] = [
    # Séries do Banco Central: cada código tem o seu endereço (o mesmo que o builder chama).
    Regra(
        padrao=r"SGS\s+" + _NUMEROS,
        nome="SGS {n}",
        url="https://api.bcb.gov.br/dados/serie/bcdata.sgs.{n}/dados?formato=json",
        por_numero=True,
    ),
    # Tabelas do IBGE: a página da tabela no SIDRA.
    Regra(
        padrao=r"SIDRA,?\s*(?:tabelas?\s+)?" + _NUMEROS,
        nome="SIDRA {n}",
        url="https://sidra.ibge.gov.br/tabela/{n}",
        por_numero=True,
    ),
    Regra(
        padrao=r"SGS(?!\s+\d)",
        nome="Banco Central, SGS",
        url="https://www3.bcb.gov.br/sgspub/",
    ),
    Regra(
        padrao=r"SIDRA(?!,?\s*(?:tabelas?\s+)?\d)",
        nome="IBGE, SIDRA",
        url="https://sidra.ibge.gov.br",
    ),
    # Séries do Ipeadata citadas pelo código, "(PNADCA_TXPNUF)": os valores da própria série.
    Regra(
        padrao=r"\((PNAD\w+(?:(?:,\s*|\s+e\s+)PNAD\w+)*)\)",
        nome="Ipeadata {n}",
        url="https://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{n}')",
        por_numero=True,
    ),
    Regra(
        padrao=r"Focus",
        nome="Focus",
        url="https://www.bcb.gov.br/publicacoes/focus",
    ),
    Regra(
        padrao=r"Tesouro Direto",
        nome="Tesouro Direto",
        url="https://www.tesourotransparente.gov.br/ckan/dataset/taxas-dos-titulos-ofertados-pelo-tesouro-direto",
    ),
    Regra(
        padrao=r"\bRTN\b|Resultado do Tesouro",
        nome="RTN",
        url="https://www.tesourotransparente.gov.br/ckan/dataset/resultado-do-tesouro-nacional",
    ),
    Regra(
        padrao=r"SICONFI|Siconfi|\bRGF\b|\bRREO\b|\bDCA\b",
        nome="SICONFI",
        url="https://siconfi.tesouro.gov.br/siconfi/index.jsf",
    ),
    Regra(
        padrao=r"CAPAG",
        nome="CAPAG",
        url="https://www.tesourotransparente.gov.br/temas/estados-e-municipios/capacidade-de-pagamento-capag",
    ),
    Regra(
        padrao=r"\bBIS\b",
        nome="BIS",
        url="https://data.bis.org",
    ),
    Regra(
        padrao=r"\bFMI\b|\bWEO\b",
        nome="FMI",
        url="https://data.imf.org",
    ),
    Regra(
        padrao=r"Banco Mundial|World Bank",
        nome="Banco Mundial",
        url="https://data.worldbank.org",
    ),
    Regra(
        padrao=r"\bOCDE\b",
        nome="OCDE",
        url="https://data-explorer.oecd.org",
    ),
    Regra(
        padrao=r"Federal Reserve|\bFRED\b|\bH\.10\b",
        nome="Federal Reserve (FRED)",
        url="https://fred.stlouisfed.org",
    ),
    Regra(
        padrao=r"\bONU\b|\bWPP\b|World Population Prospects",
        nome="ONU, World Population Prospects",
        url="https://population.un.org/wpp/",
    ),
    Regra(
        padrao=r"Penn World Table|\bPWT\b",
        nome="Penn World Table",
        url="https://www.rug.nl/ggdc/productivity/pwt/",
    ),
    Regra(
        padrao=r"Projeções da População|Projeção da População",
        nome="IBGE, Projeções da População",
        url="https://www.ibge.gov.br/estatisticas/sociais/populacao/9109-projecao-da-populacao.html",
    ),
    Regra(
        padrao=r"Contas Regionais",
        nome="IBGE, Contas Regionais",
        url="https://www.ibge.gov.br/estatisticas/economicas/contas-nacionais/9054-contas-regionais-do-brasil.html",
    ),
    Regra(
        padrao=r"Ipeadata|IPEADATA",
        nome="Ipeadata",
        url="http://www.ipeadata.gov.br",
    ),
    Regra(
        padrao=r"Comex Stat|ComexStat|MDIC",
        nome="Comex Stat",
        url="https://comexstat.mdic.gov.br",
    ),
    # Abertas em 25/11/2026: o painel do ONS e a página do Novo Caged (leva ao mês mais novo).
    Regra(
        padrao=r"ONS, energia armazenada",
        nome="ONS, energia armazenada",
        url="https://www.ons.org.br/Paginas/resultados-da-operacao/historico-da-operacao/energia_armazenada.aspx",
    ),
    Regra(
        padrao=r"Novo Caged",
        nome="Novo Caged (MTE)",
        url="https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho/novo-caged",
    ),
    # O Relatório Agregado das Estatais (Sest): a página dele, a planilha do anexo I (de onde
    # vêm as fichas de cada estatal e a conta do ano) e o PDF (as páginas citadas). Os três
    # abertos em 25/11/2026. A planilha e o PDF mudam de nome a cada edição, em junho: o
    # build avisa quando a página aponta para uma planilha nova (`sest.endereco`).
    Regra(
        padrao=r"Relatório Agregado das Empresas Estatais Federais",
        nome="Relatório Agregado (Sest)",
        url=sest.PAGINA,
    ),
    Regra(
        padrao=r"Relatório Agregado das Empresas Estatais Federais[^;]*anexo I\b",
        nome="planilha do anexo I",
        url=sest.RESERVA,
    ),
    Regra(
        padrao=r"Relatório Agregado das Empresas Estatais Federais[^;]*, p\. \d+",
        nome="relatório em PDF",
        url=sest.PDF,
    ),
    Regra(
        padrao=r"\bONS\b",
        nome="ONS",
        url="https://dados.ons.org.br",
    ),
    Regra(
        padrao=r"Receita Federal",
        nome="Receita Federal",
        url="https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos",
    ),
    Regra(
        padrao=r"SINISA",
        nome="SINISA",
        url="https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa",
    ),
    Regra(
        padrao=r"\bFAO\b",
        nome="FAO",
        url="https://www.fao.org/publications/home/fao-flagship-publications/the-state-of-food-security-and-nutrition-in-the-world",
    ),
    # A lista das LDOs por ano (todas as leis de `leis.METAS_DAS_LDOS` estão nela e, uma a uma,
    # em `LEIS_NO_SENADO`).
    Regra(
        padrao=r"LDO de cada ano",
        nome="Câmara, LDOs de cada ano",
        url="https://www2.camara.leg.br/orcamento-da-uniao/leis-orcamentarias/ldo",
    ),
    Regra(
        padrao=r"Relatório de Acompanhamento Fiscal",
        nome="IFI, Relatório de Acompanhamento Fiscal",
        url="https://www12.senado.leg.br/ifi/publicacoes-1/relatorio-de-acompanhamento-fiscal",
    ),
    Regra(
        # Onde o Relatório Agregado é citado, os três endereços exatos acima bastam.
        padrao=r"Sest\b(?!\), Relatório Agregado)|SEST\b|Empresas Estatais(?! Federais)",
        nome="Ministério da Gestão, estatais (Sest)",
        url="https://www.gov.br/gestao/pt-br/assuntos/estatais",
    ),
    Regra(
        padrao=r"Ministério da Previdência|Boletim Estatístico da Previdência|\bINSS\b",
        nome="Ministério da Previdência, dados abertos",
        url="https://www.gov.br/previdencia/pt-br/acesso-a-informacao/dados-abertos",
    ),
    Regra(
        padrao=r"Tribunal de Contas da União",
        nome="TCU",
        url="https://portal.tcu.gov.br",
    ),
    Regra(
        padrao=r"\bIFI\b|Instituição Fiscal Independente",
        nome="IFI",
        url="https://www12.senado.leg.br/ifi",
    ),
    # O projeto da LDO 2027 (matéria 173677 no Senado, a mesma de `tramitacao.PROJETOS`); a
    # página abre na ficha do Congresso Nacional (conferida em 25/11/2026).
    Regra(
        padrao=r"PLN nº 2/2026|Projeto da LDO 2027|PLDO 2027",
        nome="PLN 2/2026 (LDO 2027)",
        url="https://www.congressonacional.leg.br/materias/materias-bicamerais/-/ver/pln-2-2026",
    ),
    # Abertas em 25/11/2026: a página dos boletins (lista a planilha da edição do mês) e a do
    # Relatório de Estabilidade Financeira.
    Regra(
        padrao=r"Boletim Estatístico da Previdência",
        nome="Boletim Estatístico da Previdência Social",
        url="https://www.gov.br/previdencia/pt-br/assuntos/previdencia-social/Dados-estatisticos-previdencia-social-e-inss/boletins-da-previdencia-social",
    ),
    # Abertas em 25/11/2026: a página que lista a planilha "quadros de apoio" de cada
    # bimestre, e o PDF do Acórdão 2933/2026-Plenário (relatório, voto e acórdão; o endereço
    # vem do campo urlArquivoPdf da API de dados abertos do TCU).
    Regra(
        padrao=r"Relatório de Avaliação de Receitas e Despesas Primárias",
        nome="Relatórios de avaliação fiscal (MPO)",
        url="https://www.gov.br/planejamento/pt-br/assuntos/orcamento/relatorios-de-avaliacao-fiscal",
    ),
    Regra(
        padrao=r"Acórdão 2933/2026",
        nome="TCU, Acórdão 2933/2026-Plenário",
        url="https://contas.tcu.gov.br/sagas/SvlVisualizarRelVotoAc?codFiltro=SAGAS-SESSAO-ENCERRADA&seOcultaPagina=S&item0=920740",
    ),
    Regra(
        padrao=r"Relatório de Estabilidade Financeira",
        nome="Banco Central, Relatório de Estabilidade Financeira",
        url="https://www.bcb.gov.br/publicacoes/ref",
    ),
    Regra(
        padrao=r"Relatório de Inflação",
        nome="Banco Central, Relatório de Inflação",
        url="https://www.bcb.gov.br/publicacoes/ri",
    ),
    Regra(
        padrao=r"Relatório de Política Monetária",
        nome="Banco Central, Relatório de Política Monetária",
        url="https://www.bcb.gov.br/publicacoes/rpm",
    ),
    Regra(
        padrao=r"Tabelas especiais",
        nome="Banco Central, Tabelas especiais",
        url="https://www.bcb.gov.br/estatisticas/tabelasespeciais",
    ),
    Regra(
        padrao=r"Estatísticas fiscais",
        nome="Banco Central, Estatísticas fiscais",
        url="https://www.bcb.gov.br/estatisticas/estatisticasfiscais",
    ),
    Regra(
        padrao=r"Classificação para a Dívida de Longo Prazo|Classificação de Risco",
        nome="Tesouro, classificação de risco",
        url="https://sisweb.tesouro.gov.br/apex/f?p=2810:2",
    ),
    Regra(
        padrao=r"(?:Emenda Constitucional|\bEC) (?:nº )?132\b",
        nome="EC 132/2023",
        url="https://legis.senado.leg.br/norma/37959796",
    ),
    Regra(
        padrao=r"(?:Lei Complementar|\bLC) (?:nº )?214\b",
        nome="LC 214/2025",
        url="https://legis.senado.leg.br/norma/40180341",
    ),
    Regra(
        padrao=r"(?:Lei Complementar|\bLC) (?:nº )?200\b",
        nome="LC 200/2023",
        url="https://legis.senado.leg.br/norma/37553820",
    ),
    Regra(
        padrao=r"(?:Lei Complementar|\bLC) (?:nº )?101\b|\bLRF\b",
        nome="LRF (LC 101/2000)",
        url="https://legis.senado.leg.br/norma/572856",
    ),
    Regra(
        padrao=r"(?:Lei Complementar|\bLC) (?:nº )?227\b",
        nome="LC 227/2026",
        url="https://legis.senado.leg.br/norma/42042119",
    ),
    Regra(
        padrao=r"(?:Lei Complementar|\bLC) (?:nº )?206\b",
        nome="LC 206/2024",
        url="https://legis.senado.leg.br/norma/38506116",
    ),
    Regra(
        padrao=r"Resolução do Senado nº 40/2001",
        nome="Resolução do Senado 40/2001",
        url="https://legis.senado.leg.br/norma/562458",
    ),
    Regra(
        padrao=r"Decreto nº 12\.797",
        nome="Decreto 12.797/2025",
        url="https://legis.senado.leg.br/norma/41882097",
    ),
    Regra(
        padrao=r"Resolução CMN nº 5\.141",
        nome="Resolução CMN 5.141/2024",
        url="https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=5141",
    ),
    Regra(
        padrao=r"\bADCT\b",
        nome="Constituição (ADCT)",
        url="https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
    ),
]

REGRAS += [
    Regra(
        padrao=re.escape(nome),
        nome=nome,
        url=f"https://legis.senado.leg.br/norma/{id_}",
    )
    for nome, id_ in LEIS_NO_SENADO.items()
]

# Quem fala de "Banco Central" sem série ou relatório próprio cai na página de dados abertos
# (o catálogo de todas as séries); entra só se nenhuma outra regra do BC casou.
_GERAIS: list[Regra] = [
    Regra(
        padrao=r"Banco Central",
        nome="Banco Central, dados abertos",
        url="https://dadosabertos.bcb.gov.br",
    ),
    Regra(
        padrao=r"IBGE",
        nome="IBGE",
        url="https://www.ibge.gov.br/estatisticas/todos-os-temas.html",
    ),
    Regra(
        padrao=r"Tesouro Nacional",
        nome="Tesouro Transparente",
        url="https://www.tesourotransparente.gov.br",
    ),
]

# Instituição citada sem que nenhuma regra mais específica tenha dado link dela: entra a página
# geral (padrão, pedaço do endereço que já a cobre).
_INSTITUICOES: list[tuple[Regra, str]] = [
    (_GERAIS[0], "bcb.gov"),
    (_GERAIS[1], "ibge.gov"),
    (_GERAIS[2], "tesouro"),
    (
        Regra(padrao=r"\bIpea\b", nome="Ipea", url="http://www.ipeadata.gov.br"),
        "ipeadata",
    ),
    (
        Regra(padrao=r"\bSenado\b", nome="Senado Federal", url="https://www.senado.leg.br"),
        "senado.leg",
    ),
    (
        Regra(
            padrao=r"Câmara dos Deputados",
            nome="Câmara dos Deputados",
            url="https://www.camara.leg.br",
        ),
        "camara.leg",
    ),
]


class Endereco(BaseModel):
    nome: str
    url: str


def _numeros(lista: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"[A-Z][A-Z0-9_]*[0-9_][A-Z0-9_]*|\d+", lista)))


def enderecos(fonte: str) -> list[Endereco]:
    """Os endereços da fonte, sem repetir. Espelha `enderecosDaFonte` em `web/src/fontes.ts`."""
    achados: dict[str, Endereco] = {}

    def somar(regras: list[Regra]) -> None:
        for r in regras:
            for m in re.finditer(r.padrao, fonte):
                if r.por_numero:
                    for n in _numeros(m.group(1)):
                        url = r.url.replace("{n}", n)
                        achados.setdefault(url, Endereco(nome=r.nome.replace("{n}", n), url=url))
                else:
                    achados.setdefault(r.url, Endereco(nome=r.nome, url=r.url))

    somar(REGRAS)
    for regra, dominio in _INSTITUICOES:
        if not any(dominio in url for url in achados) and re.search(regra.padrao, fonte):
            somar([regra])
    return list(achados.values())


def sem_endereco(fonte: str) -> bool:
    return bool(fonte.strip()) and not enderecos(fonte)


def _textos_de_fonte(no: object) -> list[str]:
    achados: list[str] = []
    if isinstance(no, dict):
        for chave, valor in no.items():
            if chave in ("fonte", "fonte_piramide") and isinstance(valor, str):
                achados.append(valor)
            else:
                achados += _textos_de_fonte(valor)
    elif isinstance(no, list):
        for x in no:
            achados += _textos_de_fonte(x)
    return achados


def auditar(pasta: Path) -> tuple[list[str], list[str]]:
    """As fontes dos JSONs gerados sem endereço nenhum e as que só caíram na página geral da
    instituição (`_INSTITUICOES`). O build avisa as duas listas (Caio, 25/11/2026: toda fonte
    oficial
    tem de estar linkada)."""
    sem: set[str] = set()
    gerais: set[str] = set()
    paginas = {r.url for r, _ in _INSTITUICOES}
    for arquivo in sorted(
        pasta.glob("*.json")
    ):  # o painel de alerta é conta nossa sobre linhas já citadas
        if arquivo.name in ("busca.json", "glossario.json", "fontes.json"):
            continue
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for texto in _textos_de_fonte(dados):
            achados = enderecos(texto)
            if not texto.strip() or texto.startswith("Painel de alerta"):
                continue
            if not achados:
                sem.add(texto)
            elif all(e.url in paginas for e in achados):
                gerais.add(texto)
    return sorted(sem), sorted(gerais)


def gravar(saida: Path) -> int:
    regras = REGRAS + [r for r, _ in _INSTITUICOES]
    texto = json.dumps(
        {
            "regras": [r.model_dump(exclude_defaults=True) for r in REGRAS],
            "instituicoes": [
                {**r.model_dump(exclude_defaults=True), "dominio": dominio}
                for r, dominio in _INSTITUICOES
            ],
        },
        ensure_ascii=False,
    )
    (saida / "fontes.json").write_text(texto, encoding="utf-8")
    return len(regras)
