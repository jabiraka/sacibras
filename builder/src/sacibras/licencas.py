"""As licenças de dado das fontes que não são do governo, lidas no site de cada uma.

Pedido do Caio (15/11/2026): *"não deixe exportar oq for de fontes privadas, grave a licença
de dados desses sites para não infringirmos nenhuma cláusula"*. Dado do governo brasileiro
(IBGE, BC, Tesouro…) é público; o que vem de instituição privada só vai à tela com a fonte, e
sem CSV nem PNG quando os termos não deixam reproduzir. Quem decide é a fonte de cada
gráfico: se ela cita uma origem daqui com `exporta=False`, o `Grafico` sai com
`sem_download` preenchido (`schema.py`) e o site esconde os dois botões.

Repassar não muda a licença: o SGS do Banco Central serve o IGP-M (189) e a utilização da
capacidade (28561), mas não os põe no catálogo de dados abertos dele, que é o que sai sob
ODbL (`dadosabertos.bcb.gov.br`, busca por título em 15/11/2026: nenhum conjunto da FGV).
Vale o termo de quem fez o número.

Reler os termos uma vez por ano (`leituras.py`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Licenca:
    dono: str
    licenca: str
    termos: str
    """Onde o termo foi lido."""
    trecho: str
    """O que o termo diz, copiado como estava (ou resumido, quando é longo)."""
    lida_em: date
    exporta: bool
    """False: o site não oferece CSV nem PNG dos gráficos com este dado."""
    marca: str
    """Expressão regular que acha a origem no texto da fonte do gráfico."""
    motivo: str = ""
    """O que o site escreve no lugar dos botões (curto)."""
    citacao: str = ""
    """O que a licença pede que se escreva ao usar."""


PWT = Licenca(
    dono="Groningen Growth and Development Centre (Universidade de Groningen)",
    licenca="Creative Commons Atribuição 4.0 Internacional (CC BY 4.0)",
    termos=(
        "rug.nl/ggdc/productivity/pwt/ e o registro no DataverseNL (doi:10.34894/FABVLR, "
        'campo "license": CC-BY-4.0)'
    ),
    trecho=(
        '"Penn World Table 11.0 by Robert C. Feenstra, Robert Inklaar and Marcel P. Timmer is '
        'licensed under a Creative Commons Attribution 4.0 International License." A CC BY '
        "4.0 deixa copiar e redistribuir, inclusive para uso comercial, com o crédito, o elo "
        "da licença e o aviso de que houve mudança."
    ),
    lida_em=date(2026, 11, 15),
    exporta=True,
    marca=r"Penn World Table",
    citacao=(
        'Feenstra, Robert C., Robert Inklaar e Marcel P. Timmer (2015), "The Next Generation '
        'of the Penn World Table", American Economic Review, 105(10), 3150-3182'
    ),
)

FGV_IBRE = Licenca(
    dono="Fundação Getulio Vargas, Instituto Brasileiro de Economia (FGV IBRE)",
    licenca="Todos os direitos reservados; reproduzir pede autorização do FGV IBRE",
    termos="portalibre.fgv.br/termos-de-uso e portalibre.fgv.br/fgv-dados",
    trecho=(
        '"É expressamente proibida a reprodução de qualquer item citado anteriormente, assim '
        "como de qualquer forma de conteúdo aqui disponibilizado, sem a autorização do FGV "
        'IBRE." "[...] não utilizar o conteúdo aqui encontrado para finalidades comerciais, '
        "publicitárias ou qualquer outro propósito que seja ilegal ou proibido, como "
        "reprodução, distribuição e divulgação, total ou parcial, dos textos, figuras, "
        'gráficos que compõem o Portal, sem prévia autorização do FGV IBRE." No FGV Dados: '
        '"Os índices do IGP e seus componentes (IPA, IPC e INCC) são divulgados gratuitamente '
        "nas suas formas mais agregadas e são oferecidos por assinatura nas suas formas mais "
        'desagregadas (grupos, subgrupos e itens)." Rodapé: "© Copyright 2020 IBRE. Todos os '
        'direitos reservados."'
    ),
    lida_em=date(2026, 11, 15),
    exporta=False,
    marca=r"\bFGV\b",
    motivo="dado da FGV IBRE, cujos termos de uso vedam reproduzir sem autorização",
    citacao="FGV IBRE",
)

FECOMERCIO = Licenca(
    dono="Federação do Comércio de Bens, Serviços e Turismo do Estado de São Paulo",
    licenca="Sem termo de uso de dados publicado (procurado no site em 15/11/2026)",
    termos=(
        "fecomercio.com.br (só o aviso de privacidade); o catálogo do BC lista a série 4393 "
        'com ODbL e "Fonte: Federação do Comércio..."'
    ),
    trecho=(
        "O Banco Central publica o Índice de Confiança do Consumidor (SGS 4393) no catálogo de "
        "dados abertos sob ODbL, mas o índice é da Fecomercio-SP, que não diz o que deixa "
        "fazer com ele. Por cautela, fica como dado privado."
    ),
    lida_em=date(2026, 11, 15),
    exporta=False,
    marca=r"Fecomercio",
    motivo="índice da Fecomercio-SP, entidade privada que não publica licença de uso",
    citacao="Fecomercio-SP",
)

B3 = Licenca(
    dono="B3 S.A. - Brasil, Bolsa, Balcão",
    licenca="Dado de mercado da B3: uso fora do site pede licença (B3 Market Data)",
    termos="b3.com.br (ver docs/FONTES.md, leitura de 14/11/2026)",
    trecho=(
        "A B3 veda a coleta automatizada no site e licencia a redistribuição de cotações e "
        "índices. O Ibovespa chega pelo IPEADATA, mas o índice continua da B3."
    ),
    lida_em=date(2026, 11, 15),
    exporta=False,
    marca=r"\bB3\b",
    motivo="índice ou preço da B3, que licencia a redistribuição dos dados dela",
    citacao="B3",
)

LICENCAS: list[Licenca] = [PWT, FGV_IBRE, FECOMERCIO, B3]


def sem_download(fonte: str) -> str:
    """Por que o gráfico com esta fonte não tem CSV nem PNG ("" quando pode ter)."""
    motivos = [x.motivo for x in LICENCAS if not x.exporta and re.search(x.marca, fonte)]
    if not motivos:
        return ""
    return "Sem download: " + "; ".join(motivos) + "."
