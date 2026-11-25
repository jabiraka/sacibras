from __future__ import annotations

from sacibras import relatorios, tramitacao


def _corpo(situacao: str, informes: list[tuple[str, str]]) -> dict[str, object]:
    return {
        "MovimentacaoMateria": {
            "Materia": {
                "Autuacoes": {
                    "Autuacao": [
                        {
                            "SituacoesAtuais": {"SituacaoAtual": [{"DescricaoSituacao": situacao}]},
                            "InformesLegislativos": {
                                "InformeLegislativo": [
                                    {"Data": d, "Descricao": t} for d, t in informes
                                ]
                            },
                        }
                    ]
                }
            }
        }
    }


def test_estado_pega_o_informe_mais_recente() -> None:
    corpo = _corpo(
        "MATÉRIA COM A RELATORIA",
        [("2026-11-19 17:33:12", "cronograma"), ("2026-11-24 22:57:42", "1.504  emendas")],
    )
    assert tramitacao.estado(corpo) == (
        "MATÉRIA COM A RELATORIA",
        "2026-11-24 22:57:42",
        "1.504 emendas",
    )


def test_so_avisa_o_que_mudou() -> None:
    p = tramitacao.PROJETOS[0]
    assert tramitacao.mudancas(p, p.situacao, p.informe, "") == []
    novo = tramitacao.mudancas(p, "AGUARDANDO SANÇÃO", "2026-12-18 10:00:00", "aprovado")
    assert len(novo) == 2
    assert "AGUARDANDO SANÇÃO" in novo[0]
    assert "2026-12-18" in novo[1]


def test_o_projeto_da_ldo_fecha_com_o_que_foi_lido() -> None:
    proj = relatorios.PLDO_2027
    # a meta de 2027 é 0,50 % do PIB, e a tolerância, 0,25 pp para cada lado
    baixo, alto = relatorios.PLDO_2027_FAIXA_BI
    meta = relatorios.PLDO_2027_META_BI
    assert abs((meta - baixo) - (alto - meta)) < 0.01
    assert abs(baixo / meta - 0.5) < 0.01
    # as metas sobem e o primário antes dos descontos fica abaixo delas
    metas = [x.meta for x in proj.values() if x.meta is not None]
    assert metas == sorted(metas)
    assert all(x.primario < x.meta for x in proj.values() if x.meta is not None)
    # o que estabilizaria em 2027 é bem mais que a meta
    assert (proj[2027].meta or 0) < relatorios.PLDO_2027_ESTABILIZA
    assert sorted(proj) == list(range(2026, 2037))
