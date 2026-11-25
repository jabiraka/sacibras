"""Setor externo e crédito sem rede: o balanço de pagamentos em partes e a casa própria."""

from datetime import date

import pytest

from sacibras.secoes import credito, externo
from sacibras.secoes.base import Contexto
from sacibras.tipos import Ponto


def _meses(n: int, valor: float, inicio: date = date(2010, 1, 1)) -> list[Ponto]:
    saida: list[Ponto] = []
    ano, mes = inicio.year, inicio.month
    for i in range(n):
        saida.append((date(ano, mes, 1), valor + i * 0.01))
        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1
    return saida


def _contexto(valores: dict[str, float], anos: dict[str, int] | None = None) -> Contexto:
    ctx = Contexto(hoje=date(2026, 11, 14))
    for chave, v in valores.items():
        ctx._sgs[(chave, (anos or {}).get(chave, 16))] = _meses(201, v)  # jan/2010 a set/2026
    return ctx


def test_pib_em_dolares_sai_da_conta_corrente_e_do_percentual() -> None:
    d1, d2 = date(2026, 9, 1), date(2007, 1, 1)
    tc_12m = [(d2, 100.0), (d1, -59986.1)]
    tc_pib = [(d2, 0.05), (d1, -2.33)]
    pib = externo.pib_dolares_12m(tc_12m, tc_pib)
    # Perto de zero o percentual com duas casas não serve de denominador: a data sai.
    assert [d for d, _ in pib] == [d1]
    assert pib[0][1] == pytest.approx(2574.5, abs=0.1)


def test_tabela_do_balanco_mostra_agora_e_um_ano_antes() -> None:
    agora, antes = date(2026, 9, 1), date(2025, 9, 1)
    linhas = [("Bens", [(antes, 50.0), (agora, 75.0)], "22707")]
    pib = [(antes, 2000.0), (agora, 2500.0)]
    tabela = externo.tabela_balanco(linhas, pib, fonte="Banco Central, SGS 22707")
    assert tabela.colunas[0] == "Até set/2026 (US$ bi)"
    assert tabela.colunas[3] == "Até set/2025 (% do PIB)"
    assert tabela.linhas[0].valores == [75.0, 50.0, 3.0, 2.5]
    assert tabela.linhas[0].fonte == "SGS 22707"


def test_tabela_sem_pib_deixa_o_percentual_vazio() -> None:
    agora = date(2026, 9, 1)
    tabela = externo.tabela_balanco([("Bens", [(agora, 75.0)], "22707")], [], fonte="x")
    assert tabela.linhas[0].valores == [75.0, None, None, None]


def test_real_em_12m_desconta_o_ipca() -> None:
    d = date(2026, 9, 1)
    real = credito.real_em_12m([(d, 6.06)], [(d, 4.58)])
    assert real[0][1] == pytest.approx((1.0606 / 1.0458 - 1) * 100)
    assert credito.real_em_12m([(d, 6.0)], []) == []


EXTERNO = {
    "BALANCA_COMERCIAL": 6000.0,
    "BP_SERVICOS": -5000.0,
    "BP_RENDA_PRIMARIA": -7000.0,
    "BP_RENDA_SECUNDARIA": 500.0,
    "TRANSACOES_CORRENTES": -5500.0,
    "IDP": 7000.0,
    "BP_IDE": 3000.0,
    "BP_CARTEIRA": 500.0,
    "BP_DERIVATIVOS": 100.0,
    "BP_OUTROS_INVESTIMENTOS": -3000.0,
    "BP_ATIVOS_RESERVA": 1000.0,
    "BP_CONTA_FINANCEIRA": -5400.0,
    "TC_12M": -66000.0,
    "TC_12M_PIB": -4.5,  # sobe 0,01 por mês: termina em -2,5
    "IDP_12M_PIB": 3.4,
    "RESERVAS": 360000.0,
    "CAMBIO_REAL_EFETIVO": 120.0,
    "ICBR": 400.0,
    "ICBR_AGRO": 400.0,
    "ICBR_METAL": 600.0,
    "ICBR_ENERGIA": 200.0,
    # Os serviços em partes: somam -5000 por mês, como o total acima.
    "BP_SERV_TRANSPORTES": -1500.0,
    "BP_SERV_ALUGUEL": -1500.0,
    "BP_SERV_TELECOM": -800.0,
    "BP_SERV_VIAGENS": -1000.0,
    "BP_SERV_PROPRIEDADE": -900.0,
    "BP_SERV_NEGOCIOS": 700.0,
    "BP_SERV_FINANCEIROS": 100.0,
    "BP_SERV_SEGUROS": -100.0,
    "BP_SERV_GOVERNO": -100.0,
    "BP_SERV_CULTURAIS": 50.0,
    "BP_SERV_MANUTENCAO": 50.0,
    "BP_SERV_CONSTRUCAO": 0.0,
    "BP_SERV_MANUFATURA": 0.0,
}


def test_externo_guarda_o_balanco_no_fim(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sem o Comex Stat (aqui, sem rede), a seção sai com o resto.
    def fora_do_ar(ctx: Contexto) -> None:
        raise RuntimeError("Comex Stat fora do ar")

    monkeypatch.setattr(externo, "comercio_detalhado", fora_do_ar)
    secao = externo.montar(_contexto(EXTERNO, {"CAMBIO_REAL_EFETIVO": 25}))
    assert [c.id for c in secao.cartoes][:4] == [
        "transacoes-correntes",
        "balanca",
        "reservas",
        "cambio-real",
    ]
    assert secao.graficos[0].id == "conta-corrente"
    assert [g.id for g in secao.graficos][-2:] == ["conta-corrente-partes", "servicos-partes"]
    partes = secao.graficos[-2]
    assert partes.tipo == "empilhado"
    assert [s.id for s in partes.series] == ["bens", "servicos", "renda1", "renda2"]
    tabela = secao.tabelas[0]
    assert tabela.id == "balanco-pagamentos"
    rotulos = [linha.rotulo for linha in tabela.linhas]
    assert "Conta corrente" in rotulos
    assert "Investimento direto no país" in rotulos
    # O IDP entra como veio (entrada); o IDE e os ativos de reserva, com o sinal trocado.
    por_rotulo = {linha.rotulo: linha.valores for linha in tabela.linhas}
    assert por_rotulo["Investimento direto no país"][0] > 0
    assert por_rotulo["Investimento direto de brasileiros no exterior"][0] < 0
    # Com o PIB em dólares de mentira (~66 bi / 2,5 %), o % do PIB sai preenchido.
    assert por_rotulo["Conta corrente"][2] is not None
    # Os serviços: seis linhas no gráfico; na tabela, todas, da que mais tira dólares à que
    # mais traz, e o total, que é a soma.
    assert len(secao.graficos[-1].series) == externo.SERVICOS_NO_GRAFICO
    servicos = next(t for t in secao.tabelas if t.id == "servicos-partes")
    assert servicos.colunas == ["Até set/2026 (US$ bi)", "Até set/2025 (US$ bi)"]
    rotulos = [linha.rotulo for linha in servicos.linhas]
    assert rotulos[0] in ("Transportes (fretes e passagens)", "Aluguel de equipamentos")
    assert rotulos[-2:] == ["Serviços técnicos e de negócios", "Serviços, total"]
    # (cada série de mentira cresce 0,01 por mês: a soma das partes se afasta um pouco do total)
    partes_12m = [linha.valores[0] or 0.0 for linha in servicos.linhas[:-1]]
    assert sum(partes_12m) == pytest.approx(servicos.linhas[-1].valores[0], abs=0.5)


CREDITO = {
    "CREDITO_PIB": 55.0,
    "CREDITO_SALDO": 6_000_000.0,
    "CREDITO_TAXA": 32.0,
    "CREDITO_SPREAD": 21.0,
    "CREDITO_INADIMPLENCIA": 5.0,
    "FAMILIAS_ENDIVIDAMENTO": 50.0,
    "FAMILIAS_COMPROMETIMENTO": 29.0,
    "FAMILIAS_COMPROMETIMENTO_JUROS": 11.0,
    "FAMILIAS_ENDIVIDAMENTO_SEM_HABITACAO": 31.0,
    "IMOB_TAXA_MERCADO": 14.2,
    "IMOB_TAXA_REGULADA": 10.9,
    "IMOB_CONCESSOES": 20000.0,
    "IVGR": 800.0,
    "IPCA_12M": 4.6,
    "PF_CARTAO_ROTATIVO": 450.0,
    "PF_CARTAO_PARCELADO": 190.0,
    "PF_CHEQUE_ESPECIAL": 139.0,
    "PF_PESSOAL": 110.0,
    "PF_CONSIGNADO": 28.0,
}


def test_credito_poe_a_casa_propria_depois_dos_numeros_de_antes() -> None:
    secao = credito.montar(_contexto(CREDITO))
    ids = [c.id for c in secao.cartoes]
    assert ids[:4] == ["credito-pib", "credito-taxa", "credito-spread", "inadimplencia"]
    novos = [
        "imobiliario-taxa",
        "imobiliario-concessoes",
        "ivgr",
        "comprometimento-juros",
        "endividamento-sem-casa",
    ]
    assert ids[-5:] == novos
    graficos = [g.id for g in secao.graficos]
    assert graficos[:4] == ["credito-pib", "credito-custo", "inadimplencia", "familias"]
    assert graficos[4:] == [
        "imobiliario-taxa",
        "imobiliario-concessoes",
        "ivgr",
        "familias-juros",
        "familias-sem-casa",
        "juros-modalidades",
    ]
    # Revisão das telas (15/11/2026): "juros do cartão" e "cheque especial" não achavam nada.
    cartao = next(c for c in secao.cartoes if c.id == "juro-cartao")
    assert cartao.unidade == "% a.a."
    assert cartao.detalhe.startswith("cheque especial: 141,0 % a.a.")
    modalidades = next(g for g in secao.graficos if g.id == "juros-modalidades")
    assert [s.nome for s in modalidades.series] == [
        "Cartão rotativo",
        "Cartão parcelado",
        "Cheque especial",
        "Crédito pessoal",
        "Consignado",
    ]
    concessoes = next(c for c in secao.cartoes if c.id == "imobiliario-concessoes")
    assert concessoes.unidade == "R$ bilhões"
    assert concessoes.procedencia == "oficial"
    ivgr = next(c for c in secao.cartoes if c.id == "ivgr")
    assert "IPCA no mesmo período" in ivgr.detalhe
