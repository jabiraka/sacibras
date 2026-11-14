"""O índice da busca do site (`busca.json`): cada assunto, número, gráfico e tabela, as métricas
de estados e de países, e os nomes dos estados, com os sinônimos de cada um.

Lido dos JSONs já gravados (os da rodada e os que sobraram da anterior), para que a busca
ache tudo o que o site mostra. Os sinônimos ficam aqui, num dicionário só: quem procura
"desemprego" acha a desocupação; "carestia", o IPCA; "calote", a inadimplência.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from pydantic import BaseModel

# termo que aparece no título → palavras que alguém usaria para procurá-lo
SINONIMOS: dict[str, list[str]] = {
    "ipca": ["inflacao", "precos", "custo de vida", "carestia", "inflação oficial"],
    "inflacao": ["ipca", "precos", "custo de vida", "carestia", "alta dos precos"],
    "nucleo": ["inflacao subjacente", "nucleos"],
    "selic": ["juros", "taxa basica", "copom", "banco central", "taxa de juros"],
    "juro": ["juros", "selic", "taxa", "rendimento"],
    "copom": ["selic", "juros", "banco central", "reuniao"],
    "cdi": ["di", "renda fixa", "rendimento", "aplicacao"],
    "prefixad": ["tesouro prefixado", "ltn", "titulos publicos", "curva de juros", "di futuro"],
    "ipca+": ["tesouro ipca", "ntn-b", "juro real", "titulos publicos"],
    "implicita": ["inflacao implicita", "breakeven", "expectativa de inflacao", "titulos"],
    "curva": ["curva de juros", "estrutura a termo", "titulos publicos", "vencimento"],
    "dolar": ["cambio", "moeda", "us$", "real", "taxa de cambio", "moeda americana"],
    "euro": ["cambio", "moeda", "europa"],
    "cambio": ["dolar", "euro", "moeda", "real"],
    "ibovespa": ["bolsa", "acoes", "b3", "mercado de acoes", "ibov"],
    "poupanca": ["caderneta", "rendimento", "aplicacao"],
    "rendeu": [
        "retorno",
        "rentabilidade",
        "investimento",
        "aplicacao",
        "rendimento",
        "quanto rende",
    ],
    "pib": ["crescimento", "atividade", "economia", "produto interno bruto", "recessao"],
    "ibc-br": ["previa do pib", "atividade", "pib mensal"],
    "atividade": ["pib", "crescimento", "producao", "economia"],
    "industria": ["producao industrial", "fabricas", "pim"],
    "varejo": ["comercio", "vendas", "consumo", "lojas", "pmc"],
    "servicos": ["pms", "setor de servicos"],
    "desocupacao": ["desemprego", "emprego", "pnad", "taxa de desemprego", "mercado de trabalho"],
    "ocupad": ["emprego", "trabalho", "empregados"],
    "subutiliz": ["u-6", "subocupacao", "desemprego ampliado", "subemprego"],
    "informal": ["sem carteira", "bico", "trabalho informal", "conta propria"],
    "desalent": ["desistiu de procurar", "desalento"],
    "nivel de ocupacao": ["epop", "emprego sobre a populacao", "taxa de emprego"],
    "forca de trabalho": ["participacao", "pea", "populacao ativa"],
    "juro real": ["ipca+", "ntn-b", "tesouro ipca"],
    "a termo": ["5y5y", "forward", "longo prazo"],
    "imobiliari": ["casa propria", "financiamento habitacional", "hipoteca", "imoveis", "sfh"],
    "ivg-r": ["preco dos imoveis", "valor dos imoveis", "casas", "apartamentos"],
    "imoveis": ["casa propria", "preco das casas", "ivg-r"],
    "balanco de pagamentos": ["bpm6", "contas externas", "conta financeira", "renda primaria"],
    "renda primaria": ["juros e lucros remetidos", "remessa de lucros"],
    "caged": ["emprego formal", "carteira assinada", "vagas", "empregos"],
    "rendimento": ["salario", "renda", "ganho", "massa salarial"],
    "salario": ["renda", "rendimento", "salario minimo"],
    "credito": ["emprestimo", "financiamento", "banco", "concessoes"],
    "inadimplencia": ["calote", "atraso", "dividas atrasadas", "inadimplentes"],
    "spread": ["juros do banco", "custo do credito"],
    "endividamento": ["dividas das familias", "familias endividadas"],
    "divida": ["endividamento", "divida publica", "dbgg", "debito", "deve"],
    "dbgg": ["divida bruta", "divida publica", "divida do governo"],
    "primario": ["deficit", "superavit", "rombo", "resultado fiscal", "contas do governo"],
    "nominal": ["deficit nominal", "juros da divida"],
    "fiscal": ["contas publicas", "governo", "gastos publicos", "orcamento"],
    "receita": ["arrecadacao", "impostos", "tributos"],
    "despesa": ["gastos", "gasto publico", "custeio"],
    "pessoal": ["folha", "servidores", "funcionalismo", "salarios do governo"],
    "icms": ["imposto estadual", "arrecadacao dos estados", "imposto"],
    "rcl": ["receita corrente liquida"],
    "estado": ["estados", "uf", "unidade da federacao", "governo estadual", "regioes"],
    "exporta": ["exportacoes", "vendas ao exterior", "comercio exterior", "balanca comercial"],
    "importa": ["importacoes", "compras do exterior", "comercio exterior", "balanca comercial"],
    "balanca": ["comercio exterior", "exportacoes", "importacoes", "saldo comercial"],
    "transac": ["transacoes correntes", "conta corrente", "deficit externo", "setor externo"],
    "reservas": ["reservas internacionais", "dolares do banco central", "colchao"],
    "investimento direto": ["idp", "ied", "investimento estrangeiro", "capital estrangeiro"],
    "focus": ["previsao", "projecao", "expectativa", "mercado espera", "consenso", "boletim focus"],
    "previs": ["projecao", "expectativa", "futuro", "focus", "o que vem"],
    "simul": ["simulador", "cenario", "e se"],
    "mundo": ["paises", "exterior", "internacional", "comparacao internacional", "fmi"],
    "pais": ["paises", "mundo", "exterior", "internacional"],
    "emergentes": ["paises emergentes", "brics"],
    "per capita": ["por habitante", "por pessoa"],
}


class Item(BaseModel):
    t: str
    """O que aparece no resultado (título do gráfico, rótulo do número...)."""
    o: str
    """Onde está: o nome do assunto, e o tipo."""
    h: str
    """O endereço: `#assunto` ou `#assunto/alvo` (o id do elemento na página)."""
    p: str = ""
    """As palavras a mais da busca (sinônimos, sem acento, em minúsculas)."""


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sem_acento if unicodedata.category(c) != "Mn").lower()


def sinonimos_de(texto: str) -> str:
    base = normalizar(texto)
    extras: list[str] = []
    for termo, palavras in SINONIMOS.items():
        if termo in base:
            extras.extend(p for p in palavras if p not in base and p not in extras)
    return " ".join(extras)


def _item(t: str, o: str, h: str, extra: str = "") -> Item:
    return Item(t=t, o=o, h=h, p=sinonimos_de(f"{t} {extra}"))


def montar(saida: Path) -> list[Item]:
    painel = json.loads((saida / "painel.json").read_text(encoding="utf-8"))
    itens: list[Item] = []
    for s in painel["secoes"]:
        if s["id"] == "resumo" or not (saida / s["arquivo"]).exists():
            continue
        dados = json.loads((saida / s["arquivo"]).read_text(encoding="utf-8"))
        nome, h = s["titulo"], f"#{s['id']}"
        itens.append(_item(nome, "Assunto", h, s.get("resumo", "")))
        for c in dados.get("cartoes", []):
            itens.append(_item(c["rotulo"], f"{nome} · número", f"{h}/c-{c['id']}", c["detalhe"]))
        for g in dados.get("graficos", []):
            itens.append(_item(g["titulo"], f"{nome} · gráfico", f"{h}/g-{g['id']}"))
        for t in dados.get("tabelas", []):
            itens.append(_item(t["titulo"], f"{nome} · tabela", f"{h}/t-{t['id']}"))
        for m in dados.get("metricas", []):
            itens.append(_item(m["nome"], f"{nome} · comparação", f"{h}/m-{m['id']}"))
        for pais in dados.get("paises", []):
            itens.append(_item(pais["nome"], f"{nome} · país", f"{h}/p-{pais['iso3']}"))
        for uf in dados.get("ufs", []):
            itens.append(_item(uf["nome"], f"{nome} · {uf['sigla']}", f"{h}/uf-{uf['sigla']}"))
    return itens


def gravar(saida: Path) -> int:
    itens = montar(saida)
    texto = json.dumps([i.model_dump(exclude_defaults=True) for i in itens], ensure_ascii=False)
    (saida / "busca.json").write_text(texto, encoding="utf-8")
    return len(itens)
