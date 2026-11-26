import io

import openpyxl
import pytest

from sacibras.fontes import osu
from sacibras.rede import FonteForaDoArError


def _anexo(com_total: bool = True) -> bytes:
    livro = openpyxl.Workbook()
    for aba in ("Tab_1", "Tab_4"):
        ws = livro.active if aba == "Tab_1" else livro.create_sheet(aba)
        ws.title = aba
        ws.append([None, "Tabela"])
        ws.append([])
        ws.append([None, "Discriminação", "Tipologia", 2023, 2024, 2025])
        ws.append([None, "Benefícios Financeiros", "Explícito", 5.0, 6.0, 7.0])
        ws.append([None, "PRONAF (Equalização)", "Explícito", 5.0, 6.0, 7.0])
        ws.append([None, "Benefícios Creditícios", "Implícito", 1.0, 2.0, 3.0])
        ws.append(
            [
                None,
                "Fundo de Financiamento ao Estudante do Ensino Superior - FIES",
                "Implícito",
                1.0,
                2.0,
                3.0,
            ]
        )
        ws.append([None, "Benefícios Tributários", "Implícito", 10.0, 10.0, 10.0])
        ws.append([None, "Benefícios do Trabalhador", "Implícito", 10.0, 10.0, 10.0])
        if com_total:
            ws.append([None, "TOTAL", None, 16.0, 18.0, 20.0])
        ws.append([None, "Fontes: ..."])
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def test_le_os_tipos_os_programas_e_o_total() -> None:
    s = osu.ler_anexo(_anexo(), 2026)
    assert s.ultimo_ano == 2025
    assert s.nominal.totais["TOTAL"] == {2023: 16.0, 2024: 18.0, 2025: 20.0}
    assert s.nominal.totais[osu.CREDITICIOS][2025] == 3.0
    # "Benefícios do Trabalhador" é programa tributário, não um tipo.
    assert [(p.nome, p.tipo) for p in s.nominal.programas] == [
        ("PRONAF (Equalização)", osu.FINANCEIROS),
        ("Fundo de Financiamento ao Estudante do Ensino Superior - FIES", osu.CREDITICIOS),
        ("Benefícios do Trabalhador", osu.TRIBUTARIOS),
    ]


def test_recusa_anexo_sem_total_ou_sem_abas() -> None:
    with pytest.raises(FonteForaDoArError):
        osu.ler_anexo(_anexo(com_total=False), 2026)
    livro = openpyxl.Workbook()
    saida = io.BytesIO()
    livro.save(saida)
    with pytest.raises(FonteForaDoArError):
        osu.ler_anexo(saida.getvalue(), 2026)


def test_acha_a_edicao_mais_nova_na_pagina() -> None:
    base = "/planejamento/x/orcamento-de-subsidios-da-uniao"
    html = (
        f'<a href="{base}/osu_2025-anexos-publicacao.xlsx/@@download/file">'
        f'<a href="{base}/osu_2026-anexos-publicacao_enviado.xlsx/@@download/file">'
        f'<a href="{base}/relatorioosu_2025.pdf/@@display-file/file">'
    )
    achadas = osu.edicoes_na_pagina(html)
    assert sorted(achadas) == [2025, 2026]
    assert achadas[2026].startswith("https://www.gov.br/planejamento/")
    assert achadas[2026].endswith("_enviado.xlsx/@@download/file")


def test_area_do_programa() -> None:
    assert osu.area_do_programa("PRONAF (Equalização)") == "Agropecuária"
    assert osu.area_do_programa("Minha Casa Minha Vida - MCMV") == "Habitação"
    assert osu.area_do_programa("Fundos Constitucionais de Financiamento - FNE, FNO e FCO") == (
        "Desenvolvimento regional"
    )
    assert osu.area_do_programa("Fundo de Amparo ao Trabalhador - FAT") == "Trabalho e emprego"
    assert osu.area_do_programa("Programa qualquer") == osu.OUTROS
