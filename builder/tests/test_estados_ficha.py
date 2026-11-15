"""A ficha de cada estado sem rede: CAPAG, previdência (RREO Anexo 04), as contas no fim de
cada ano, a economia por atividade (Contas Regionais) e os estados perto dos limites."""

from datetime import UTC, date, datetime
from typing import Any

import pytest

from sacibras import leis
from sacibras.fontes import ibge_contas_regionais, siconfi, tesouro_capag
from sacibras.schema import MetricaEstados
from sacibras.secoes import estados
from sacibras.secoes.base import Contexto

SIGLAS = [s for _, s, _, _ in estados.UFS]
CODIGOS = [c for c, *_ in estados.UFS]


# ---------------------------------------------------------------- CAPAG

# O começo do CSV de 2025 (consultado em 15/11/2026), com o BOM que a revisão de 2024 tem.
CSV_CAPAG = (
    "﻿UF;Indicador 1;Nota 1;Indicador 2;Nota 2;Indicador 3;Nota 3;"
    "Classificação da CAPAG;Qualidade da informação contábil e fiscal;Observação\r\n"
    "AC;34,95%;A;92,29%;B;-1,03%;C;C;Bicf;\r\n"
    "MG;181,78%;C;95,21%;C;-19,53%;C;D;Aicf;\r\n"
    "ES;31,88%;A;77,75%;A;7,48%;A;A+;Aicf;\r\n"
    "SP;147,35%;C;89,75%;B;1,97%;B;B;Bicf;\r\n"
) + "".join(f"{s};1%;A;1%;A;1%;A;B+;Aicf;\r\n" for s in SIGLAS if s not in "AC MG ES SP")


def test_capag_le_o_csv_com_bom_e_as_tres_notas() -> None:
    notas = tesouro_capag.ler_csv(CSV_CAPAG.encode("utf-8"))
    assert len(notas) == 27
    assert notas["MG"] == tesouro_capag.NotaCapag("D", "C", "C", "C")
    assert notas["ES"].nota == "A+" and notas["SP"].poupanca == "B"


def test_capag_recusa_csv_sem_as_colunas() -> None:
    with pytest.raises(tesouro_capag.PlanilhaMudouError):
        tesouro_capag.ler_csv(b"UF;Nota\nAC;C\n")


def test_capag_escolhe_o_ano_mais_novo_e_a_revisao_do_mesmo_ano() -> None:
    def r(nome: str, fmt: str = "CSV") -> dict[str, Any]:
        return {"name": nome, "format": fmt, "url": f"https://x/{nome}"}

    recursos = [r("Capag Estados 2023"), r("Capag Estados 2024 - Revisão"), r("Capag Estados 2024")]
    assert tesouro_capag.escolher(recursos) == (
        2024,
        True,
        "https://x/Capag Estados 2024 - Revisão",
    )
    recursos += [r("CAPAG Estados 2025"), r("Metadados", "PDF")]
    assert tesouro_capag.escolher(recursos) == (2025, False, "https://x/CAPAG Estados 2025")
    assert tesouro_capag.escolher([r("Metadados", "PDF")]) is None


def _capag() -> tesouro_capag.Capag:
    return tesouro_capag.Capag(2025, False, tesouro_capag.ler_csv(CSV_CAPAG.encode("utf-8")))


def test_capag_vira_metrica_com_o_nome_no_lugar_do_numero() -> None:
    m = estados._capag(_capag())
    assert m.valores["MG"] == 1.0 and m.valores["ES"] == 6.0 and m.valores["SP"] == 3.0
    assert {x.rotulo: x.valor for x in m.marcas} == {
        "D": 1,
        "C": 2,
        "B": 3,
        "B+": 4,
        "A": 5,
        "A+": 6,
    }
    assert m.maior_e_melhor is True and m.referencia == "2025, contas de 2024"
    cartao = estados._cartao_capag("AC", _capag())
    assert cartao is not None and cartao.texto == "C"
    assert cartao.detalhe == "Dívida A · poupança B · caixa C" and len(cartao.detalhe) <= 60


# ---------------------------------------------------------------- RREO Anexo 04 e Anexo 06


def _l(conta: str, coluna: str, valor: float) -> dict[str, Any]:
    return {"cod_conta": conta, "coluna": coluna, "valor": valor}


LIQ = siconfi.COL_LIQUIDADA_BIMESTRE
# Trecho real do RREO-Anexo 04 do RJ, 6º bimestre de 2025 (consultado em 15/11/2026).
A4_RJ = [
    _l("RREO4ResultadoRPPSPrevidenciario", LIQ, 1169010627.29),
    _l("RREO4ResultadoRPPSFinanceiro", "DOTAÇÃO ATUALIZADA (c)", -12646974447.48),
    _l("RREO4ResultadoRPPSFinanceiro", LIQ, -11181705876.83),
    _l("ResultadoDaAdministracaoRPPS", LIQ, -574427908.41),
    _l("ResultadoDosBeneficiosMantidosPeloTesouro", LIQ, -1626398977.12),
    _l("ResultadoAssociadoAInativosEPensionistasMilirares", LIQ, -6932338482.22),
]


def test_previdencia_soma_reparticao_tesouro_e_militares_sem_a_capitalizacao() -> None:
    p = siconfi.parse_previdencia(A4_RJ)
    assert p is not None
    assert p.capitalizacao == pytest.approx(1169010627.29)
    assert p.resultado == pytest.approx(-11181705876.83 - 1626398977.12 - 6932338482.22)
    # O RS não tem a linha dos militares: conta zero.
    rs = siconfi.parse_previdencia(A4_RJ[:3])
    assert rs is not None and rs.militares == 0 and rs.tesouro == 0
    assert siconfi.parse_previdencia([]) is None


def test_primario_com_rpps_pela_conta_de_cada_edicao() -> None:
    assert siconfi.parse_primario_com_rpps(
        [
            _l("ResultadoPrimarioSemRPPSAcimaDaLinha", "VALOR", 24918028585.69),
            _l("ResultadoPrimarioComRPPSAcimaDaLinha", "VALOR", 1739828418.36),
        ]
    ) == pytest.approx(1739828418.36)
    antigo = [_l("RREO6ResultadoPrimarioEstadosMunicipios", "VALOR", 4609989591.57)]
    assert siconfi.parse_primario_com_rpps(antigo) == pytest.approx(4609989591.57)
    de_2019 = [_l("RREO6ResultadoPrimarioEstadosMunicipios", "VALOR INCORRIDO", 2367009713.0)]
    assert siconfi.parse_primario_com_rpps(de_2019) == pytest.approx(2367009713.0)


def test_pessoal_anual_calcula_o_percentual_quando_a_coluna_falta() -> None:
    p = siconfi.parse_pessoal_anual(
        [
            _l("ReceitaCorrenteLiquidaAjustada", "Valor", 200.0),
            _l("DespesaComPessoalTotal", "Valor", 90.0),
        ]
    )
    assert p is not None and p.percentual == pytest.approx(45.0) and p.base == 200.0
    assert siconfi.parse_pessoal_anual([]) is None


def test_ultimo_ano_fechado_espera_o_fim_de_janeiro() -> None:
    assert siconfi.ultimo_ano_fechado(date(2026, 11, 15)) == 2025
    assert siconfi.ultimo_ano_fechado(date(2026, 1, 20)) == 2024


def test_historico_pede_rgf_desde_2019_e_rreo_desde_2021_sem_rede(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pedidos: list[tuple[str, int, int]] = []

    def demonstrativo(
        tipo: str, per: str, ano: int, periodo: int, anexo: int, ente: int, validade: float
    ) -> list[dict[str, Any]]:
        pedidos.append((f"{tipo}{anexo}", ano, ente))
        if ente == 12 and ano == 2025:
            raise siconfi.FonteForaDoArError("fora")
        if tipo == "RGF" and anexo == 1:
            return [_l("DespesaComPessoalTotal", siconfi.COL_PCT, 40.0)]
        if tipo == "RGF":
            col = "Até o 3º Quadrimestre"
            return [
                _l("PercentualDaDCLSobreARCL", col, 100.0),
                _l("RGF2ReceitaCorrenteLiquida", col, 10.0),
            ]
        if anexo == 6:
            return [_l("ResultadoPrimarioComRPPSAcimaDaLinha", "VALOR", 1.0)]
        return A4_RJ

    monkeypatch.setattr(siconfi, "_demonstrativo", demonstrativo)
    h = siconfi.coletar_historico([12, 35], date(2026, 11, 15), trabalhadores=2)
    assert sorted(h) == list(range(2019, 2026))
    assert h[2019][35].primario is None and h[2019][35].pessoal is not None
    assert h[2024][35].previdencia is not None and h[2024][35].primario == 1.0
    assert 12 not in h[2025] and h[2025][35].divida is not None
    rreo_antes = [p for p in pedidos if p[0].startswith("RREO") and p[1] < 2021]
    assert not rreo_antes


# ---------------------------------------------------------------- anos fechados


def _ano(pessoal: float, divida: float, prim: float, prev: float) -> siconfi.AnoFechado:
    return siconfi.AnoFechado(
        pessoal=siconfi.PessoalAnual(pessoal, pessoal, 100.0),
        divida=siconfi.DividaAnual(divida, divida, 100.0, 100.0),
        primario=prim,
        previdencia=siconfi.Previdencia(prev, 0.0, 0.0, 5.0),
    )


def _historico(poucos_em: int | None = None) -> dict[int, dict[int, siconfi.AnoFechado]]:
    hist: dict[int, dict[int, siconfi.AnoFechado]] = {}
    for ano in (2023, 2024, 2025):
        cods = CODIGOS[:10] if ano == poucos_em else CODIGOS
        hist[ano] = {c: _ano(40.0 + c % 5, 50.0, 2.0, -10.0 - c % 3) for c in cods}
    hist[2025][33] = _ano(47.0, 210.0, 1.0, -20.0)  # RJ
    return hist


def test_historicos_por_estado_e_a_soma_dos_estados_so_com_24() -> None:
    por_uf, brasil = estados._historicos(_historico(poucos_em=2023))
    rj = {h.id: h for h in por_uf["RJ"]}
    assert set(rj) == {"pessoal", "divida", "primario", "previdencia"}
    assert rj["divida"].pontos[2025] == 210.0 and rj["previdencia"].pontos[2025] == -20.0
    assert [x.valor for x in rj["pessoal"].linhas] == [
        leis.PESSOAL_EXECUTIVO_ESTADUAL.valor,
        leis.PESSOAL_PRUDENCIAL.valor,
    ]
    assert rj["primario"].linhas == []
    # 2023 só com 10 estados: sem a soma; 2025 é soma sobre soma, não média dos percentuais.
    assert 2023 not in brasil["pessoal"]
    assert brasil["divida"][2025] == pytest.approx((50.0 * 26 + 210.0) / 27, abs=0.01)


def test_previdencia_do_ano_mais_novo_com_cartao_e_posicao_no_deficit() -> None:
    achado = estados._previdencia(_historico())
    assert achado is not None
    metrica, ano, em_reais = achado
    assert ano == 2025 and metrica.referencia == "2025" and metrica.maior_e_melhor is True
    assert metrica.valores["RJ"] == -20.0 and em_reais["RJ"] == -20.0
    assert "capitalização" in metrica.descricao
    cartao = estados._cartao_previdencia("RJ", metrica, ano, em_reais)
    assert cartao is not None and "1º maior déficit de 27" in cartao.detalhe
    assert len(cartao.detalhe) <= 60


def test_enriquecer_cria_a_ficha_mesmo_sem_a_dca() -> None:
    x = estados.Extras()
    x.historicos, x.brasil = estados._historicos(_historico())
    x.numeros["RJ"] = [c for c in [estados._cartao_capag("MG", _capag())] if c]
    contas = estados._enriquecer(None, x, datetime(2026, 11, 15, tzinfo=UTC))
    assert contas is not None and len(contas.contas) == 27
    assert contas.contas["RJ"].numeros[0].texto == "D"
    assert contas.historico_brasil["pessoal"]
    assert estados._enriquecer(None, estados.Extras(), datetime.now(UTC)) is None


# ---------------------------------------------------------------- a economia por atividade

ANOS_DA_PLANILHA = [""] + [float(a) for a in range(2020, 2025)]


def test_aba_da_tab07_le_o_local_e_as_atividades() -> None:
    linhas: list[list[Any]] = [
        ["Tabela 7.27 Participação ... de Santa Catarina - 2010-2024", "", "", "", "", ""],
        ["Atividades econômicas", "Participação no valor adicionado bruto (%)", "", "", "", ""],
        ANOS_DA_PLANILHA,
        ["Santa catarina", "", "", "", "", ""],
        ["Total das Atividades", 100.0, 100.0, 100.0, 100.0, 100.0],
        ["Agropecuária", 6.0, 6.0, 6.0, 6.0, 7.0],
        ["Fonte: IBGE", "", "", "", "", ""],
    ]
    local, por_ano = ibge_contas_regionais.ler_folha_de_participacao(linhas)
    assert local == "Santa catarina" and por_ano[2024]["Agropecuária"] == 7.0
    assert ibge_contas_regionais.ler_folha_de_participacao([["Sumário"], ["Tabela 7"]]) == ("", {})


def test_bloco_da_economia_divide_o_valor_adicionado_e_fecha_no_total() -> None:
    atividades = {
        "Total das Atividades": 100.0,
        "Agropecuária": 10.0,
        "Indústria": 30.0,
        "Indústrias extrativas": 5.0,
        "Indústrias de transformação": 15.0,
        "Eletricidade e gás, água, esgoto, atividades de gestão de resíduos": 3.0,
        "Construção": 7.0,
        "Serviços": 60.0,
        "Comércio e reparação de veículos automotores e motocicletas": 12.0,
        "Administração, defesa, educação e saúde públicas e seguridade social": 18.0,
        "Atividades imobiliárias": 30.0,
    }
    vab = {"Santa Catarina": {2024: 1000.0}}
    participacao = {"Santa catarina": {2024: atividades}}
    blocos = estados._blocos_setores(2024, vab, participacao)
    assert set(blocos) == {"SC"}
    b = blocos["SC"]
    assert b.id == "pib_setor" and b.referencia == "2024" and b.total == 1000.0
    fatias = {f.nome: f.valor for f in b.fatias}
    assert fatias["Construção, luz e água"] == pytest.approx(100.0)  # 7 % + 3 % de R$ 1 bi
    assert fatias["Agropecuária"] == pytest.approx(100.0)
    assert fatias["Outras"] == pytest.approx(300.0)  # os demais serviços
    assert sum(fatias.values()) == pytest.approx(1000.0)


# ---------------------------------------------------------------- perto dos limites


def _metrica(id_: str, valores: dict[str, float | None]) -> MetricaEstados:
    return MetricaEstados(
        id=id_,
        nome=id_,
        unidade="% da RCL",
        referencia="2º quadrimestre de 2026",
        fonte=f"fonte de {id_}",
        valores={s: valores.get(s, 30.0) for s in SIGLAS},
    )


def test_perto_dos_limites_ordena_pela_gravidade_e_conta_quem_passou() -> None:
    pessoal = _metrica("pessoal", {"RN": 56.4, "MG": 48.0, "AC": 45.0, "AP": None})
    divida = _metrica("divida", {"RJ": 217.2, "RS": 185.0})
    achado = estados.perto_dos_limites([pessoal, divida, estados._capag(_capag())])
    assert achado is not None
    cartao, tabela = achado
    nomes = [linha.rotulo for linha in tabela.linhas]
    # RN e RJ passaram de um máximo; MG (prudencial e nota D); RS e AC (alertas); SP (nota B)
    # não entra.
    assert nomes[:2] == ["Rio Grande do Norte", "Rio de Janeiro"]
    assert nomes[2] == "Minas Gerais"
    assert set(nomes) == {
        "Rio Grande do Norte",
        "Rio de Janeiro",
        "Minas Gerais",
        "Rio Grande do Sul",
        "Acre",
    }
    rn = tabela.linhas[0]
    assert rn.textos[0] == "56,4 %, acima do máximo" and rn.textos[1] == "30,0 %"
    assert tabela.linhas[2].textos == ["48,0 %, acima do prudencial", "30,0 %", "D"]
    assert tabela.colunas == ["Pessoal (% da RCL)", "Dívida (% da RCL)", "CAPAG"]
    assert cartao.valor == 5.0 and cartao.unidade == "de 27"
    assert cartao.detalhe == "2 com nota CAPAG C ou D"  # AC (C) e MG (D)
    assert cartao.referencia == date(2026, 8, 1)


def test_perto_dos_limites_sem_capag_e_sem_rgf() -> None:
    pessoal, divida = _metrica("pessoal", {"RN": 56.4}), _metrica("divida", {})
    achado = estados.perto_dos_limites([pessoal, divida])
    assert achado is not None
    _, tabela = achado
    assert tabela.colunas == ["Pessoal (% da RCL)", "Dívida (% da RCL)"]
    assert estados.perto_dos_limites([pessoal]) is None


def test_riscos_usa_o_que_estados_deixou_no_memo(monkeypatch: pytest.MonkeyPatch) -> None:
    def nao_chame(*a: Any, **k: Any) -> Any:
        raise AssertionError("não devia ir à fonte")

    monkeypatch.setattr(estados.siconfi, "coletar", nao_chame)
    ctx = Contexto(hoje=date(2026, 11, 15))
    guardadas = [_metrica("pessoal", {}), _metrica("divida", {})]
    ctx.memo["estados_limites"] = guardadas
    assert estados.metricas_dos_limites(ctx) is guardadas
