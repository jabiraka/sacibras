"""Estados sem rede: exportações da ficha e em % do PIB, a pirâmide por UF, o acordo da dívida
(RRF e Propag), as capitais e os dois alertas novos de Riscos."""

from datetime import date
from typing import Any

import pytest

from sacibras import alertas, leis, relatorios
from sacibras.fontes import comexstat, siconfi
from sacibras.secoes import estados, estados_economia, riscos
from sacibras.secoes.base import Contexto

UFS_PEQUENO = [(35, "SP", "São Paulo", "Sudeste"), (33, "RJ", "Rio de Janeiro", "Sudeste")]


# ------------------------------------------------------------------ exportações


def test_exportacoes_no_pib_converte_mes_a_mes_pelo_dolar_do_mes() -> None:
    por_mes = {
        "São Paulo": {m: 1e9 for m in range(1, 13)},  # US$ 12 bi no ano
        "Rio de Janeiro": {1: 6e9},
        "Não Declarada": {1: 1e9},
    }
    # Dólar a R$ 5 em janeiro e R$ 6 no resto do ano.
    dolar = [(date(2024, m, 1), 5.0 if m == 1 else 6.0) for m in range(1, 13)]
    pib = {
        "São Paulo": {2024: 3_000_000.0},  # R$ milhões
        "Rio de Janeiro": {2024: 1_000_000.0},
        "Brasil": {2024: 10_000_000.0},
    }
    m = estados_economia.exportacoes_no_pib(UFS_PEQUENO, por_mes, dolar, pib, 2024, 2024)
    # SP: 1e9 × 5 + 11 × 1e9 × 6 = R$ 71 bi = 71.000 milhões, sobre 3 milhões de milhões.
    assert m.valores["SP"] == pytest.approx(71_000 / 3_000_000 * 100, abs=0.01)
    assert m.valores["RJ"] == pytest.approx(30_000 / 1_000_000 * 100, abs=0.01)
    # O Brasil conta também o que sai sem estado declarado: 71 + 30 + 5 = 106 mil milhões.
    assert m.brasil == pytest.approx(106_000 / 10_000_000 * 100, abs=0.01)
    assert m.referencia == "2024" and m.id == "exportacoes_pib"


def test_exportacoes_no_pib_sem_um_mes_do_dolar_recusa() -> None:
    dolar = [(date(2024, m, 1), 5.0) for m in range(1, 12)]
    with pytest.raises(RuntimeError, match="dólar"):
        estados_economia.exportacoes_no_pib(UFS_PEQUENO, {}, dolar, {}, 2024, 2024)


def _item(codigo: str, nome: str) -> comexstat.Item:
    return comexstat.Item(codigo, nome)


def test_ficha_das_exportacoes_seis_maiores_e_outros() -> None:
    produtos = {
        "São Paulo": {_item(f"{k:04d}", f"Produto {k}") for k in range(8)},
        "Rio de Janeiro": {_item("2709", "Óleos brutos de petróleo")},
    }
    valores_sp = {i: 1e9 * (8 - int(i.codigo)) for i in produtos["São Paulo"]}  # 8, 7… 1 bi
    por_produto = {"São Paulo": valores_sp, "Rio de Janeiro": {_item("2709", "x"): 40e9}}
    paises = {
        "São Paulo": {_item("China", "China"): 20e9, _item("EUA", "Estados Unidos"): 16e9},
        "Rio de Janeiro": {_item("China", "China"): 40e9},
    }
    fichas = estados_economia.exportacoes_da_ficha(
        UFS_PEQUENO, date(2026, 10, 1), por_produto, paises
    )
    sp = fichas["SP"]
    assert sp.numero.valor == pytest.approx(36.0) and sp.numero.unidade == "US$ bilhões"
    # SP tem 36 de 76 bi exportados no total; RJ, com 40, é o maior.
    assert sp.numero.detalhe == "47,4 % do Brasil; 2ª maior de 2"
    assert len(sp.numero.detalhe) <= 60
    blocos = {b.id: b for b in sp.blocos}
    prod = blocos["exportacoes_produtos"]
    assert [f.nome for f in prod.fatias][:2] == ["Produto 0", "Produto 1"]
    assert prod.fatias[-1].nome == "Outros produtos"
    assert prod.fatias[-1].valor == pytest.approx(3000.0)  # 2 + 1 bi, em US$ milhões
    assert len(prod.fatias) == estados_economia.TOP_DA_FICHA + 1
    assert prod.total == pytest.approx(36_000.0) and prod.compara is False
    # O nome curto do petróleo vem de `NOMES_CURTOS`.
    assert fichas["RJ"].blocos[0].fatias[0].nome == "Petróleo bruto"
    assert [f.nome for f in blocos["exportacoes_destinos"].fatias] == ["China", "Estados Unidos"]


# ------------------------------------------------------------------ pirâmide


def test_piramide_de_cada_uf_nos_anos_da_do_brasil() -> None:
    grupos = ["00-04", "05-09", "90+"]
    anos = range(2000, 2071)

    def lado(fator: float) -> dict[str, dict[int, float]]:
        return {g: {a: 1000.0 * fator * (k + 1) for a in anos} for k, g in enumerate(grupos)}

    por_uf = {
        "SP": {"Homens": lado(1), "Mulheres": lado(1.1), "Ambos": lado(2.1)},
        "AC": {"Homens": lado(0.1)},  # sem mulheres: fica de fora
    }
    p = estados.piramides(por_uf, 2026)
    assert set(p) == {"SP"}
    assert p["SP"].grupos == ["0 a 4", "5 a 9", "90 ou mais"]
    assert 2026 in p["SP"].anos and p["SP"].ano_inicial == 2026
    assert p["SP"].homens[0][0] == pytest.approx(1.0)  # mil pessoas


# ------------------------------------------------------------------ RRF e Propag


def test_acordos_cobrem_as_27_ufs_com_o_que_foi_lido() -> None:
    assert set(relatorios.ACORDOS) == {s for _, s, _, _ in estados.UFS}
    m = estados.acordos()
    contagem: dict[float, int] = {}
    for v in m.valores.values():
        assert v is not None
        contagem[v] = contagem.get(v, 0) + 1
    # IFI, RAF de jul/2026: 22 aderiram ao Propag; o RS, que ainda não assinou, segue no RRF.
    assert contagem == {0.0: 5, 1.0: 21, 2.0: 1}
    assert m.valores["RS"] == estados.REGIMES["RRF"]
    assert {x.rotulo for x in m.marcas} == {"Nenhum", "Propag", "RRF"}
    for a in relatorios.ACORDOS.values():
        assert len(a.detalhe) <= 60


def test_cartao_do_acordo_vem_depois_da_capag() -> None:
    c = estados._cartao_acordo("RJ")
    assert c is not None and c.texto == "Propag" and "RRF" in c.detalhe


# ------------------------------------------------------------------ capitais


def test_contas_das_capitais_com_os_limites_dos_municipios() -> None:
    caps = {"SP": (3550308, "São Paulo"), "RJ": (3304557, "Rio de Janeiro")}
    coleta = siconfi.ColetaCapitais(
        2026,
        2,
        pessoal={3550308: siconfi.Pessoal(26.08, 54, 51.3, 48.6), 3304557: None},
        divida={3550308: siconfi.Divida(14.73, 107e9, 120, 108), 3304557: None},
        bimestre=(2026, 4),
        primario={3550308: 1.5e9, 3304557: -2e9},
        rcl={3550308: 100e9, 3304557: None},
    )
    c = estados.contas_das_capitais(coleta, caps)
    assert c.nomes == {"SP": "São Paulo", "RJ": "Rio de Janeiro"}
    por_id = {m.id: m for m in c.metricas}
    assert por_id["pessoal"].valores == {"SP": 26.08, "RJ": None}
    assert [x.valor for x in por_id["pessoal"].limites] == [54.0, 51.3, 48.6]
    assert [x.valor for x in por_id["divida"].limites] == [
        leis.DIVIDA_MUNICIPAL.valor,
        leis.DIVIDA_ALERTA_MUNICIPAL.valor,
    ]
    assert por_id["primario"].valores == {"SP": 1.5, "RJ": None}
    assert por_id["primario"].referencia == "jan–ago/2026"


def test_coletar_capitais_pega_o_quadrimestre_com_quase_todas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cods = [3550308, 3304557, 3106200]
    pct = "% sobre a RCL Ajustada"

    def rgf(ano: int, q: int, anexo: int, ente: int, esfera: str = "E") -> list[dict[str, Any]]:
        assert esfera == "M"
        if (ano, q) != (2026, 2):  # o 3º quadrimestre ainda não saiu
            return []
        if anexo == 1:
            return [{"cod_conta": "DespesaComPessoalTotal", "coluna": pct, "valor": 30.0}]
        coluna = "Até o 2º Quadrimestre"
        return [{"cod_conta": "PercentualDaDCLSobreARCL", "coluna": coluna, "valor": 10.0}]

    def rreo(
        ano: int, b: int, anexo: int, ente: int, validade: float = 0, esfera: str = "E"
    ) -> list[dict[str, Any]]:
        if (ano, b) != (2026, 4):
            return []
        if anexo == 3:
            col = siconfi.COL_12M
            return [{"cod_conta": "RREO3ReceitaCorrenteLiquida", "coluna": col, "valor": 100.0}]
        conta = "ResultadoPrimarioSemRPPSAcimaDaLinha"
        return [{"cod_conta": conta, "coluna": siconfi.COL_PRIMARIO, "valor": 5.0}]

    monkeypatch.setattr(siconfi, "rgf", rgf)
    monkeypatch.setattr(siconfi, "rreo", rreo)
    c = siconfi.coletar_capitais(cods, date(2026, 11, 15), minimo=3)
    assert c is not None and (c.ano, c.quadrimestre, c.bimestre) == (2026, 2, (2026, 4))
    assert all(p is not None and p.percentual == 30.0 for p in c.pessoal.values())
    assert c.primario == {e: 5.0 for e in cods} and c.rcl == {e: 100.0 for e in cods}


# ------------------------------------------------------------------ os dois alertas novos


def test_alertas_novos_tem_explicacao_e_lado_ruim_alto(monkeypatch: pytest.MonkeyPatch) -> None:
    meses = [date(2007 + m // 12, m % 12 + 1, 1) for m in range(19 * 12)]
    total = [(d, 100.0) for d in meses]
    # A parte que vence em 12 meses sobe com o tempo: o último ponto é o pior da história.
    curta = {"até 1 ano": [(d, 10.0 + i * 0.05) for i, d in enumerate(meses)]}
    monkeypatch.setattr(riscos.bcb_fiscal, "cronograma_dbgg", lambda: (total, curta))
    ctx = Contexto(hoje=date(2026, 11, 15))
    monkeypatch.setattr(ctx, "sgs", lambda chave, anos=16: [(d, 1000.0) for d in meses])
    bloco = riscos._vencimento(ctx)
    [a] = bloco.alertas
    assert a.id == "vence-em-12-meses" and a.pior_quando == "alto"
    assert a.grupo == riscos.FISCAL and a.pior_que >= 99.0
    assert a.significa == alertas.EXPLICACOES["vence-em-12-meses"].significa
    assert "juros-sobre-receita" in alertas.EXPLICACOES
