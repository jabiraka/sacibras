"""Quantas empresas estão no Simples Nacional e no MEI: as Estatísticas do Simples Nacional
da Receita Federal (o "Sinac" e o "Simei"), por UF, na posição do dia.

A página é um formulário antigo (ASP.NET): abre-se a consulta, troca-se o tipo para "Por UF"
(uma volta ao servidor) e pede-se "Exibir Dados" com o dia da posição, sempre com os campos
escondidos que a página devolve (`__VIEWSTATE` e os outros).
Lido em 26/11/2026, com a posição consolidada até 21/11/2026: 26.391.253 optantes do Simples
e 17.881.969 MEI. O total do Simples inclui o MEI, que é uma forma de estar no Simples (LC
123/2006, art. 18-A: o MEI é "optante pelo Simples Nacional"). Só o ano corrente abre
direto; os anteriores pedem outra volta e ficam de fora.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date

from sacibras.rede import FonteForaDoArError, baixar

BASE = "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATBHE/estatisticasSinac.app/"
PAGINA = BASE + "Default.aspx"
FONTE = "Receita Federal, Estatísticas do Simples Nacional"
CONSULTAS = {
    "simples": "EstatisticasOptantesPorDataMunicipio.aspx?tipoConsulta=1&anoConsulta=",
    "mei": "EstatisticasOptantesPorDataMunicipio.aspx?tipoConsulta=2&optanteSimei=&anoConsulta=",
}
_P = "ctl00$ctl00$Conteudo$"
_ESCONDIDO = re.compile(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"')
_POSICAO = re.compile(r"Posição Consolidada até (\d{2})/(\d{2})/(\d{4})")
_LINHA = re.compile(r"\b([A-Z]{2}|TOTAL) ([\d.]+)\b")


@dataclass(frozen=True)
class Optantes:
    posicao: date
    total: int
    por_uf: dict[str, int]


def _texto(pagina: str) -> str:
    sem_script = re.sub(r"<script.*?</script>", "", pagina, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", sem_script)))


def ler(pagina: str) -> Optantes:
    """A tabela "UF Total" da página de resposta."""
    texto = _texto(pagina)
    achada = _POSICAO.search(texto)
    if not achada:
        raise FonteForaDoArError("Simples: sem a data da posição")
    dia, mes, ano = (int(x) for x in achada.groups())
    inicio = texto.find("UF Total")
    if inicio < 0:
        raise FonteForaDoArError("Simples: sem a tabela por UF")
    por_uf: dict[str, int] = {}
    total = 0
    for sigla, numero in _LINHA.findall(texto[inicio:]):
        valor = int(numero.replace(".", ""))
        if sigla == "TOTAL":
            total = valor
            break
        por_uf[sigla] = valor
    if not total or len(por_uf) != 27 or sum(por_uf.values()) != total:
        raise FonteForaDoArError(f"Simples: tabela por UF incompleta ({len(por_uf)} UFs)")
    return Optantes(posicao=date(ano, mes, dia), total=total, por_uf=por_uf)


def _campos(pagina: str) -> dict[str, str]:
    return {nome: html.unescape(valor) for nome, valor in _ESCONDIDO.findall(pagina)}


def optantes(qual: str) -> Optantes:
    """ "simples" (todos, MEI inclusive) ou "mei"."""
    url = BASE + CONSULTAS[qual]
    pagina = baixar(url, validade=0).decode("utf-8", "replace")
    campos = _campos(pagina) | {
        "__EVENTTARGET": _P + "AntesTabela$droplistOpcao",
        _P + "AntesTabela$droplistOpcao": "Por UF",
        _P + "AposTabela$ddlUf": "UFNS",
    }
    pagina = baixar(url, metodo="POST", dados=campos, validade=0).decode("utf-8", "replace")
    # A consulta "Por UF" pede o dia: o da posição consolidada, que a própria página diz.
    achada = _POSICAO.search(_texto(pagina))
    if not achada:
        raise FonteForaDoArError("Simples: sem a data da posição")
    campos = _campos(pagina) | {
        _P + "AntesTabela$droplistOpcao": "Por UF",
        _P + "AntesTabela$txtDtIni": "/".join(achada.groups()),
        _P + "AntesTabela$btnExibir": "Exibir Dados",
        _P + "AposTabela$ddlUf": "UFNS",
    }
    pagina = baixar(url, metodo="POST", dados=campos, validade=0).decode("utf-8", "replace")
    return ler(pagina)
