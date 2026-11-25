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


class Regra(BaseModel):
    padrao: str
    """Expressão regular (sintaxe comum a Python e JavaScript, sem flags)."""
    nome: str
    url: str
    por_numero: bool = False


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
        padrao=r"Ipeadata",
        nome="Ipeadata",
        url="http://www.ipeadata.gov.br",
    ),
    Regra(
        padrao=r"Comex Stat|ComexStat|MDIC",
        nome="Comex Stat",
        url="https://comexstat.mdic.gov.br",
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
        padrao=r"\bB3\b",
        nome="B3",
        url="https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/ibovespa.htm",
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
    Regra(
        padrao=r"\bIFI\b|Instituição Fiscal Independente",
        nome="IFI",
        url="https://www12.senado.leg.br/ifi",
    ),
    Regra(
        padrao=r"Emenda Constitucional nº 132",
        nome="EC 132/2023",
        url="https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc132.htm",
    ),
    Regra(
        padrao=r"Lei Complementar nº 214|\bLC 214\b",
        nome="LC 214/2025",
        url="https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm",
    ),
    Regra(
        padrao=r"Lei Complementar nº 200|\bLC 200\b",
        nome="LC 200/2023",
        url="https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp200.htm",
    ),
    Regra(
        padrao=r"Lei Complementar nº 101|\bLRF\b",
        nome="LRF",
        url="https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp101.htm",
    ),
    Regra(
        padrao=r"\bADCT\b",
        nome="Constituição (ADCT)",
        url="https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
    ),
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


class Endereco(BaseModel):
    nome: str
    url: str


def _numeros(lista: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\d+", lista)))


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
    if not achados:
        somar(_GERAIS)
    return list(achados.values())


def sem_endereco(fonte: str) -> bool:
    return bool(fonte.strip()) and not enderecos(fonte)


def gravar(saida: Path) -> int:
    regras = REGRAS + _GERAIS
    texto = json.dumps(
        {
            "regras": [r.model_dump(exclude_defaults=True) for r in REGRAS],
            "gerais": [r.model_dump(exclude_defaults=True) for r in _GERAIS],
        },
        ensure_ascii=False,
    )
    (saida / "fontes.json").write_text(texto, encoding="utf-8")
    return len(regras)
