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
        "Projeto da LDO 2027: meta, dívida projetada e parâmetros (ainda não é lei)",
        "relatorios.PLDO_2027",
        date(2026, 11, 25),
        date(2026, 12, 23),
        "Senado, matéria 173677 (dadosabertos/materia/textos/173677): o parecer final da CMO, "
        "o autógrafo e a lei sancionada. O `sacibras tramitacao` avisa quando ela anda (issue "
        "`tramitação`). Sancionada, a meta de 2027 vai para leis.METAS_DAS_LDOS.",
    ),
    Leitura(
        "Faixa do crescimento real do limite da despesa (arcabouço fiscal)",
        "leis.FAIXA_DA_DESPESA",
        date(2026, 11, 20),
        date(2027, 11, 20),
        "Senado, LC 200/2023 (legis.senado.leg.br/norma/37553820), art. 5º, § 1º: ver se lei "
        "complementar nova mudou o piso de 0,6 % ou o teto de 2,5 %. Uma vez por ano.",
    ),
    Leitura(
        "Avaliação bimestral do primário (o desconto da meta)",
        "leis.AVALIACOES_2026",
        date(2026, 11, 25),
        date(2027, 1, 22),
        "O builder lê sozinho a planilha quadros de apoio do bimestre mais novo "
        "(fontes/avaliacao_bimestral.py, aba Tabela 1) e diz o bimestre na tela. Conferir que "
        "a tela mostra o último (sai até o dia 22 do mês seguinte ao bimestre) e passar os "
        "números para a reserva. Com o 1º bimestre de 2027 (março), o build avisa que a "
        "planilha é de outro ano: trocar a meta e o ano (META_PRIMARIA_2026).",
    ),
    Leitura(
        "Salário mínimo do ano (o decreto de 2027 sai em dezembro)",
        "leis.SALARIO_MINIMO_NORMAS",
        date(2026, 11, 15),
        date(2027, 1, 10),
        "Senado, lista de decretos (dadosabertos/legislacao/lista?tipo=DEC&ano=2026), o que "
        "'dispõe sobre o valor do salário mínimo'; ler o art. 1º, conferir que o SGS 1619 dá o "
        "mesmo valor e pôr o ano novo no dicionário. Uma vez por ano.",
    ),
    Leitura(
        "Meta do Marco do Saneamento (99 % água, 90 % esgoto até 2033)",
        "leis.META_SANEAMENTO",
        date(2026, 11, 14),
        date(2027, 11, 14),
        "Câmara, Lei 11.445/2007 em texto atualizado (legin, normaatualizada), art. 11-B; ou o "
        "Planalto, do PC. Conferir se lei nova mudou a meta ou o prazo. Uma vez por ano.",
    ),
    Leitura(
        "As respostas e conclusões das perguntas (falam do momento: 'ainda não', 'do jeito "
        "que está, não')",
        "perguntas.LIDAS_EM",
        date(2026, 11, 19),
        date(2027, 2, 19),
        "Abrir as perguntas no site e conferir cada frase contra o número ao lado: a "
        "inflação contra o teto, o ritmo dos núcleos, a desocupação contra o mínimo da série, "
        "o primário que estabiliza contra o maior já feito, a implícita contra o Focus, e, na "
        "da crise, as reservas contra a dívida externa curta e o investimento direto contra o "
        "déficit externo. A "
        "cada três meses, e antes disso se o IPCA voltar à meta ou a Selic mudar de direção.",
    ),
    Leitura(
        "Meta de primário no texto original de cada LDO (o prometido contra o que veio)",
        "leis.METAS_DAS_LDOS",
        date(2026, 11, 19),
        date(2027, 1, 15),
        "Senado, publicação original da LDO 2027 (dadosabertos/legislacao/lista?tipo=LEI), "
        "art. 2º: pôr o ano novo no dicionário. Uma vez por ano, quando a LDO é sancionada.",
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
        "Limites de pessoal e de dívida das capitais (LRF e Senado)",
        "leis.PESSOAL_EXECUTIVO_MUNICIPAL",
        date(2026, 11, 15),
        date(2027, 11, 15),
        "Senado, LC 101/2000 em texto atualizado (norma 572856), art. 20, III; e a Resolução nº "
        "40/2001 (norma 562458), art. 3º, II. Uma vez por ano.",
    ),
    Leitura(
        "Estados no RRF e no Propag",
        "relatorios.ACORDOS",
        date(2026, 11, 25),
        date(2026, 12, 23),
        "Tesouro Nacional, Relatório Mensal de Garantias Honradas (tesourotransparente.gov.br/"
        "publicacoes/relatorio-mensal-de-garantias-honradas-rmgh, sai por volta do dia 15; diz "
        "quem está no RRF), e o Relatório de Acompanhamento Fiscal da IFI (Senado) que trouxer "
        "o Propag. Conferir se o RS e o RN assinaram o termo do Propag. Todo mês.",
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
        date(2026, 11, 25),
        date(2027, 5, 25),
        "O builder lê sozinho o CSV da consulta do Tesouro (fontes/tesouro_notas.py) e "
        "acrescenta os atos de S&P, Fitch e Moody's depois de ULTIMO_ATO_LIDO. Conferir que a "
        "nota da tela diz o ato mais novo (sisweb.tesouro.gov.br/apex/f?p=2810:2); passar os "
        "atos novos para NOTAS, PERSPECTIVA e ULTIMO_ATO_LIDO. A cada seis meses.",
    ),
    Leitura(
        "Teste de estresse dos bancos (REF)",
        "relatorios.ESTRESSE_DOS_BANCOS",
        date(2026, 11, 25),
        date(2027, 6, 15),
        "O builder lê sozinho o anexo estatístico da edição mais nova do Relatório de "
        "Estabilidade Financeira (fontes/bcb_ref.py, gráficos 1.2.5.6 e 1.2.5.7). Depois da "
        "edição de maio, conferir que a tela a mostra e que a planilha bate com o texto do "
        "relatório; se bater, passar a frase e ESTRESSE_EDICAO para ela. Duas vezes por ano.",
    ),
    Leitura(
        "Efeito da Selic na inflação e no dólar (modelos do BC)",
        "relatorios.EFEITO_SELIC_EM",
        date(2026, 11, 14),
        date(2026, 12, 31),
        "Relatório de Política Monetária de dezembro: procurar nova atualização dos modelos "
        "semiestruturais; os números saem da planilha anexa (rpmAAAAMManp.xlsx), não do "
        "gráfico. A cada relatório (mar, jun, set, dez).",
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
    # ------------------------------------------------------------- licenças de dado
    Leitura(
        "Licença da Penn World Table (CC BY 4.0) e versão nova",
        "licencas.PWT",
        date(2026, 11, 15),
        date(2027, 11, 15),
        "rug.nl/ggdc/productivity/pwt/: conferir a licença e se saiu versão nova (a 12.0 virá "
        "com outro DOI: trocar `pwt.DOI` e `pwt.VERSAO`). Uma vez por ano.",
    ),
    Leitura(
        "Termos de uso da FGV IBRE (IGP-M e capacidade instalada fora da tela)",
        "licencas.FGV_IBRE",
        date(2026, 11, 15),
        date(2027, 11, 15),
        "portalibre.fgv.br/termos-de-uso e /fgv-dados: se passarem a deixar divulgar com a "
        "fonte, trocar `mostra` (e `exporta`, se deixarem reproduzir). Uma vez por ano.",
    ),
    Leitura(
        "Licença do Índice de Confiança do Consumidor (Fecomercio-SP)",
        "licencas.FECOMERCIO",
        date(2026, 11, 15),
        date(2027, 11, 15),
        "fecomercio.com.br e o catálogo do BC (série 4393): ver se a Fecomercio publicou "
        "termo de uso dos dados. Uma vez por ano.",
    ),
    # ------------------------------------------------------------- impostos
    Leitura(
        "Reforma do consumo, ano a ano (EC 132 e LC 214)",
        "leis.REFORMA_DO_CONSUMO",
        date(2026, 11, 15),
        date(2027, 11, 15),
        "Câmara, Constituição em texto atualizado (legin, constituicao-1988-…-normaatualizada), "
        "arts. 124 a 137 do ADCT, e a LC 214/2025 também em texto atualizado (arts. 343 a "
        "349): ver se emenda ou lei nova mexeu. O Planalto, do PC, serve de conferência. Uma "
        "vez por ano.",
    ),
    Leitura(
        "IBS pelo destino: quanto se reparte pela receita de antes (2029 a 2077)",
        "leis.IBS_PELA_RECEITA_ANTIGA",
        date(2026, 11, 15),
        date(2027, 11, 15),
        "Câmara, Constituição em texto atualizado, ADCT, arts. 131 e 132; e a lei complementar "
        "que reparte o IBS (LC 214/2025). Uma vez por ano.",
    ),
    Leitura(
        "Imposto Seletivo e Simples Nacional na reforma (LC 214)",
        "leis.SELETIVO_E_SIMPLES",
        date(2026, 11, 15),
        date(2027, 2, 15),
        "Câmara, LC 214/2025 em texto atualizado (arts. 41, 47, 409 a 438) e a LC 123/2006 "
        "(art. 13). Procurar a lei ordinária com as alíquotas do Seletivo, que a LC deixa para "
        "ela, e trocar a linha das alíquotas quando sair. A cada três meses até 2027.",
    ),
    Leitura(
        "Regimes específicos da reforma: combustíveis, bancos, saúde, imóveis (LC 214)",
        "leis.REGIMES_PROPRIOS",
        date(2026, 11, 15),
        date(2027, 2, 15),
        "Câmara, LC 214/2025 em texto atualizado (arts. 157, 164, 168, 172 a 176, 181, 192, "
        "233 a 238, 244 a 246, 251 a 261, 271, 273 a 289 e 293): ver se lei complementar nova "
        "mexeu, como a LC 227/2026 fez nos bancos, no aluguel e na SAF. Depois, uma vez por ano.",
    ),
    Leitura(
        "CBS de 2027: o cálculo do TCU e a resolução do Senado",
        "relatorios.CBS_REFERENCIA_2027",
        date(2026, 11, 25),
        date(2026, 12, 23),
        "Resolução do Senado que fixa a alíquota de referência da CBS de 2027 (prazo: 15 ou "
        '22/12; sem ela, vale o cálculo do TCU). Trocar o número e o texto "o Senado ainda '
        'fixa" em impostos.py. O acórdão do TCU (2933/2026-Plenário) foi lido; o `sacibras '
        "tramitacao` olha a API de acórdãos do TCU e avisa (issue `tramitação`) quando sai o "
        "cálculo de outro ano. Depois, todo ano, a alíquota do ano seguinte.",
    ),
    Leitura(
        "Alíquota cheia do IBS e da CBS: a conta do Comitê Gestor",
        "relatorios.ALIQUOTA_COMITE_GESTOR",
        date(2026, 11, 14),
        date(2027, 8, 15),
        "Comitê Gestor do IBS (cgibs.gov.br), a resolução de julho com a estimativa de "
        "arrecadação do ano seguinte e o anexo metodológico. Uma vez por ano.",
    ),
    Leitura(
        "Descontos, devolução e teto de 26,5 % da reforma (LC 214)",
        "leis.TETO_IBS_CBS",
        date(2026, 11, 14),
        date(2027, 2, 15),
        "Câmara, texto atualizado da LC 214/2025 (arts. 12, 118, 123, 125, 127, 128 e 475): "
        "ver se lei complementar nova mexeu, como a LC 227/2026 fez. Depois, uma vez por ano.",
    ),
    Leitura(
        "Receita prevista para o ano (LOA e avaliação bimestral)",
        "relatorios.RECEITA_PREVISTA",
        date(2026, 11, 25),
        date(2027, 1, 22),
        "O builder lê sozinho a mesma planilha de leis.AVALIACOES_2026 (LOA e avaliação mais "
        "nova da receita administrada e do RGPS). Com o 1º bimestre de 2027, trocar "
        "ANO_DA_RECEITA_PREVISTA e a reserva; até lá, conferir de vez em quando.",
    ),
    Leitura(
        "Dívida ativa da União: estoque",
        "relatorios.DIVIDA_ATIVA_ESTOQUE",
        date(2026, 11, 14),
        date(2027, 4, 30),
        "Anexo de Riscos Fiscais do PLDO (gov.br/planejamento, orçamentos anuais), enviado "
        "até 15 de abril. Uma vez por ano.",
    ),
    Leitura(
        "Ações na Justiça contra a União e sentenças pagas (Anexo de Riscos Fiscais)",
        "relatorios.ACOES_JUDICIAIS",
        date(2026, 11, 15),
        date(2027, 4, 30),
        "Anexo V (Riscos Fiscais) do PLDO, tabelas de demandas judiciais (possível e provável) "
        "e de despesas judiciais (gov.br/planejamento, orçamentos anuais, enviado até 15 de "
        "abril). Atualizar também SENTENCAS_PAGAS e RISCOS_FISCAIS (a tabela-resumo). Uma vez "
        "por ano.",
    ),
    Leitura(
        "Projeção atuarial do INSS até 2100",
        "relatorios.RGPS_PROJECAO",
        date(2026, 11, 15),
        date(2027, 4, 30),
        "Anexo IV.10 do PLDO (Projeções Atuariais do RGPS), tabela da receita, despesa e "
        "necessidade de financiamento em % do PIB (gov.br/planejamento, abril). Uma vez por "
        "ano.",
    ),
    Leitura(
        "PIB trimestral por estado contra os cinco estados que publicam o seu",
        "relatorios.CONFERENCIA_PIB_ESTADOS",
        date(2026, 11, 15),
        date(2027, 11, 30),
        "Rodar scripts/conferir_pib_estados.py: ele acha e baixa sozinho a planilha mais nova "
        "de RS (DEE), PR (IPARDES), BA (SEI) e ES (IJSN); a de MG (FJP) se baixa à mão e vai "
        "com --mg (o IPARDES às vezes pede verificação de robô: --pr). Não roda no build. Uma "
        "vez por ano, depois das Contas Regionais (novembro).",
    ),
    Leitura(
        "Dívida ativa da União: recuperado no ano",
        "relatorios.DIVIDA_ATIVA_RECUPERADO",
        date(2026, 11, 14),
        date(2027, 3, 31),
        "PGFN em Números (gov.br/pgfn, institucional), que sai em março. Uma vez por ano.",
    ),
    # ------------------------------------------------------------- servidores e estatais
    Leitura(
        "Servidores civis da União por poder: quantos são e a remuneração média",
        "relatorios.SERVIDORES_POR_PODER",
        date(2026, 11, 19),
        date(2027, 5, 15),
        "PLDO 2028 (sai até 15/4/2027), anexo de metas fiscais, 'Avaliação Atuarial do RPPS "
        "dos servidores civis', tabelas por poder (são imagem no PDF: ler na página). Trocar "
        "também SERVIDORES_EM. Uma vez por ano.",
    ),
    Leitura(
        "Militares das Forças Armadas: quantos são e a remuneração média",
        "relatorios.MILITARES_ATIVOS",
        date(2026, 11, 19),
        date(2027, 5, 15),
        "PLDO 2028, 'Avaliação Atuarial do Sistema de Pensões Militares das Forças Armadas', "
        "volume 1, seções 3.1.1 e 3.1.2; atualizar também MILITARES_INATIVOS. Uma vez por ano.",
    ),
    Leitura(
        "Valor médio das aposentadorias do INSS",
        "relatorios.INSS_APOSENTADORIA_MEDIA",
        date(2026, 11, 25),
        date(2027, 5, 25),
        "O builder lê sozinho a planilha do Boletim Estatístico da Previdência Social mais "
        "nova sem o 13º (fontes/beps.py, quadros 15 e 27). Conferir que a tabela dos "
        "servidores mostra um mês recente; se não, ver se a página dos boletins mudou o nome "
        "do arquivo. Atualizar a reserva (INSS_*, INSS_EM, TETO_INSS). A cada seis meses.",
    ),
    Leitura(
        "Teto do INSS e teto do serviço público",
        "relatorios.TETO_INSS",
        date(2026, 11, 19),
        date(2027, 3, 31),
        "O do INSS vem sozinho do boletim da Previdência (quadro 27); em março, quando sai o "
        "boletim de janeiro, conferir que a tela mostra o do ano. O do serviço público é à "
        "mão: a lista de leis do Senado, para ver se há lei nova do subsídio de ministro do "
        "STF. Uma vez por ano.",
    ),
    Leitura(
        "Estatais federais: lucro, dividendos à União, subvenção e aporte, por ano",
        "relatorios.ESTATAIS_POR_ANO",
        date(2026, 11, 19),
        date(2027, 7, 15),
        "O builder lê sozinho a planilha do anexo I da edição mais nova (fontes/sest.py). "
        "Em julho, conferir que a tela mostra a edição 2027 (ano-base 2026); se não, ver se "
        "a página da Sest mudou o nome do arquivo. Atualizar os números de reserva "
        "(ESTATAIS_POR_ANO, SUBVENCOES_2025, LUCRO_DOS_MAIORES) e a frase da pergunta das "
        "estatais ('o menor em cinco anos').",
    ),
    Leitura(
        "Polo Industrial de Manaus: faturamento, folha e empregos por ano (Suframa)",
        "relatorios.PIM_EMPREGOS",
        date(2026, 11, 26),
        date(2027, 3, 15),
        "Suframa, gov.br/suframa/pt-br/centrais-de-conteudo/indicadores: o caderno de "
        "dezembro de 2026 (sai em fevereiro), quadros 'Principais custos de produção x "
        "faturamento' e 'Evolução da mão-de-obra do PIM'. Trocar os dicionários "
        "(PIM_*, inclusive PIM_SUBSETORES) e PIM_EM, e conferir os números fixos da "
        "pergunta da Zona Franca (R$ 27 bi, R$ 242 mil por emprego, três vezes a folha, "
        "43 % de eletrônicos, 31 % do Amazonas). O custo vem do DGT da Receita (abril). "
        "Uma vez por ano.",
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
