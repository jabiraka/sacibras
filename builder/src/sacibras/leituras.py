"""Os prazos para reler o que foi lido à mão (`leis.py` e `relatorios.py`).

Número de norma ou de relatório sem API só muda quando alguém lê a fonte de novo. Cada
leitura tem aqui a data em que foi feita, até quando ela vale e onde procurar a nova. O
`sacibras leituras` lista o que venceu ou vence logo; o build avisa; e o workflow "Prazos de
releitura" abre uma issue no GitHub (Caio, 14/11/2026: fazer o aviso, "o 1 e o 2").

Ao reler: atualize o número e o comentário no arquivo de origem e aqui a `lida_em` e o
`reler_ate` (o próximo prazo). `onde` aponta o nome no código; o teste confere que ele existe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

AVISO_DIAS = 7
"""Quantos dias antes do prazo a leitura já aparece como "vence logo"."""


@dataclass(frozen=True)
class Leitura:
    o_que: str
    onde: str
    """`modulo.NOME` do número no código (o teste confere que existe)."""
    lida_em: date
    reler_ate: date
    como: str
    """Onde procurar a leitura nova e de quanto em quanto tempo ela sai."""
    do_pc: bool = False
    """A fonte recusa quem está fora do Brasil (o Planalto): só se lê do PC do Caio."""


LEITURAS: list[Leitura] = [
    # ------------------------------------------------------------- leis e normas
    Leitura(
        "Meta de primário da LDO (o ano que vem pede a LDO nova)",
        "leis.META_PRIMARIA_2026",
        date(2026, 11, 14),
        date(2027, 1, 15),
        "Planalto, lei da LDO 2027, art. 2º (sancionada em dezembro ou janeiro). Trocar a meta "
        "do ano ao virar o ano.",
        do_pc=True,
    ),
    Leitura(
        "Avaliação bimestral do primário (o desconto da meta)",
        "leis.AVALIACOES_2026",
        date(2026, 11, 14),
        date(2026, 11, 24),
        "Relatório de Avaliação de Receitas e Despesas Primárias do 5º bimestre (sai até 22/11) "
        "ou a nota da Conorf no site do Senado. A cada bimestre.",
    ),
    Leitura(
        "Meta de inflação (CMN)",
        "leis.META_CONTINUA",
        date(2026, 11, 14),
        date(2027, 7, 15),
        "API de normativos do BCB: conferir se o CMN mudou a meta na reunião de junho.",
    ),
    Leitura(
        "Limites de pessoal da LRF",
        "leis.PESSOAL_EXECUTIVO_ESTADUAL",
        date(2026, 11, 14),
        date(2027, 11, 14),
        "Planalto, LC 101/2000, arts. 19, 20, 22 e 59 (texto compilado). Uma vez por ano.",
        do_pc=True,
    ),
    Leitura(
        "Limite da dívida dos estados (Senado)",
        "leis.DIVIDA_ESTADUAL",
        date(2026, 11, 14),
        date(2027, 11, 14),
        "legis.senado.leg.br/norma/562458 (Resolução 40/2001, texto atualizado). Uma vez por ano.",
    ),
    # ------------------------------------------------------------- relatórios
    Leitura(
        "Elasticidades da dívida (nota fiscal do BC)",
        "relatorios.ELASTICIDADES",
        date(2026, 11, 14),
        date(2026, 12, 3),
        "Nota 'Estatísticas fiscais' do BC, seção 3 (sai no fim de cada mês). Todo mês.",
    ),
    Leitura(
        "Nota de crédito do país",
        "relatorios.NOTAS",
        date(2026, 11, 14),
        date(2026, 12, 14),
        "sisweb.tesouro.gov.br/apex/f?p=2810:2 (fora do ar em 14/11/2026) e os comunicados do "
        "Tesouro. Sem calendário: conferir uma vez por mês.",
    ),
    Leitura(
        "Teste de estresse dos bancos (REF)",
        "relatorios.ESTRESSE_DOS_BANCOS",
        date(2026, 11, 14),
        date(2027, 5, 31),
        "Relatório de Estabilidade Financeira do BC (maio e outubro).",
    ),
    Leitura(
        "Efeito da Selic na inflação e no dólar (modelos do BC)",
        "relatorios.EFEITO_SELIC_EM",
        date(2026, 11, 14),
        date(2026, 12, 31),
        "Relatório de Política Monetária de dezembro: procurar nova atualização dos modelos "
        "semiestruturais. A cada relatório (mar, jun, set, dez).",
    ),
    Leitura(
        "Faixa de erro do efeito da Selic no IPCA",
        "relatorios.IPCA_FAIXA_90_MENOR",
        date(2026, 11, 14),
        date(2026, 12, 31),
        "Mesmo relatório: conferir se o BC voltou a publicar o intervalo de 90 %.",
    ),
    Leitura(
        "Repasse do dólar para os preços",
        "relatorios.IPCA_POR_10_DE_DOLAR_12M",
        date(2026, 11, 14),
        date(2027, 3, 31),
        "Relatório de Política Monetária: novo boxe de repasse cambial. Uma vez por ano.",
    ),
    Leitura(
        "Proposta de Lara Resende no simulador da Selic",
        "relatorios.LARA_RESENDE_SELIC",
        date(2026, 11, 14),
        date(2027, 3, 25),
        "Substack do autor: conferir se a proposta mudou ou envelheceu (seis meses da publicação).",
    ),
    Leitura(
        "Multiplicadores de imposto",
        "relatorios.EFEITOS_DE_IMPOSTO",
        date(2026, 11, 14),
        date(2027, 5, 14),
        "SPE, Boletim Impulso Estrutural do Gasto: conferir se saiu a nota metodológica com o "
        "multiplicador de receita. A cada seis meses.",
    ),
]


def situacao(leitura: Leitura, hoje: date) -> str:
    """'vencida', 'vence logo' ou 'em dia'."""
    if hoje > leitura.reler_ate:
        return "vencida"
    if (leitura.reler_ate - hoje).days <= AVISO_DIAS:
        return "vence logo"
    return "em dia"


def pendentes(hoje: date) -> list[Leitura]:
    """As vencidas e as que vencem logo, da mais atrasada à mais folgada."""
    return sorted((x for x in LEITURAS if situacao(x, hoje) != "em dia"), key=lambda x: x.reler_ate)


def tabela(hoje: date, todas: bool = False) -> str:
    """Tabela em Markdown (vai na issue e no resumo do Actions)."""
    linhas = LEITURAS if todas else pendentes(hoje)
    if not linhas:
        return "Nenhuma releitura vencida nem vencendo nos próximos dias."
    saida = [
        "| Situação | O quê | Prazo | Lida em | Onde | Como |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for x in sorted(linhas, key=lambda x: x.reler_ate):
        como = x.como
        if x.do_pc:
            como += " **Só do PC** (a fonte recusa quem está fora do Brasil)."
        saida.append(
            f"| {situacao(x, hoje)} | {x.o_que} | {x.reler_ate:%d/%m/%Y} | "
            f"{x.lida_em:%d/%m/%Y} | `{x.onde}` | {como} |"
        )
    return "\n".join(saida)
