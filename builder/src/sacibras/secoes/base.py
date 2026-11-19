"""O que toda seção usa: ler do catálogo, montar série, gráfico e cartão."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sacibras import contas, licencas
from sacibras.catalogo import SGS
from sacibras.fontes import bcb_sgs
from sacibras.schema import Cartao, Grafico, Procedencia, Serie, VarianteGrafico
from sacibras.tipos import Periodicidade, Ponto

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


@dataclass
class Contexto:
    hoje: date = field(default_factory=date.today)
    _sgs: dict[tuple[str, int], list[Ponto]] = field(default_factory=dict)
    memo: dict[str, Any] = field(default_factory=dict)
    """Resultados que mais de uma seção usa (o Focus de hoje, a curva de juros)."""

    def sgs(self, chave: str, anos: int = 16) -> list[Ponto]:
        """A série do catálogo, dos últimos `anos` até hoje."""
        if SGS[chave].origem and (motivo := licencas.nao_mostra(SGS[chave].origem)):
            raise ValueError(f"{chave} não pode ir à tela: {motivo} (licencas.py)")
        if (chave, anos) not in self._sgs:
            inicio = date(self.hoje.year - anos, 1, 1)
            self._sgs[(chave, anos)] = bcb_sgs.ler(SGS[chave], inicio, self.hoje)
        return self._sgs[(chave, anos)]

    def fonte_sgs(self, *chaves: str) -> str:
        codigos = ", ".join(str(SGS[c].codigo) for c in chaves)
        origens = "".join(f"; {SGS[c].origem}" for c in chaves if SGS[c].origem)
        return f"Banco Central, SGS {codigos}{origens}"

    def agora(self) -> datetime:
        return datetime.now(UTC)


def periodo(d: date, p: Periodicidade) -> str:
    """'out/2026', '3º tri/2026', '13/11/2026', '2026' — para frases escritas pelo builder."""
    if p == "A":
        return str(d.year)
    if p == "T":
        return f"{(d.month - 1) // 3 + 1}º tri/{d.year}"
    if p == "M":
        return f"{MESES[d.month - 1]}/{d.year}"
    return d.strftime("%d/%m/%Y")


def br(valor: float, casas: int = 1) -> str:
    """Número no formato brasileiro, para frases: 4,5 · 1.234,5."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def serie(
    id: str,
    nome: str,
    pontos: list[Ponto],
    *,
    papel: str = "realizado",
    casas: int = 2,
    desde: date | None = None,
    tracejado_desde: date | None = None,
) -> Serie:
    if desde:
        pontos = [p for p in pontos if p[0] >= desde]
    return Serie(
        id=id,
        nome=nome,
        pontos=[(d, round(v, casas)) for d, v in pontos],
        papel=papel,  # type: ignore[arg-type]
        tracejado_desde=tracejado_desde,
    )


def grafico(
    id: str,
    titulo: str,
    series: list[Serie],
    *,
    unidade: str,
    periodicidade: Periodicidade,
    fonte: str,
    **extra: Any,
) -> Grafico:
    return Grafico(
        id=id,
        titulo=titulo,
        series=series,
        unidade=unidade,
        periodicidade=periodicidade,
        fonte=fonte,
        **extra,
    )


def cartao(
    id: str,
    rotulo: str,
    pontos: list[Ponto],
    *,
    unidade: str,
    periodicidade: Periodicidade,
    fonte: str,
    casas: int = 1,
    detalhe: str = "",
    secao: str = "",
    procedencia: Procedencia = "oficial",
    mini: int = 36,
    referencia: date | None = None,
) -> Cartao:
    """O cartão do último ponto de `pontos`, com a miniatura dos `mini` últimos."""
    quando, valor = pontos[-1]
    cauda = pontos[-mini:]
    # Miniatura leve: no máximo ~60 pontos.
    passo = max(1, len(cauda) // 60)
    reduzida = cauda[::-1][::passo][::-1]
    return Cartao(
        id=id,
        rotulo=rotulo,
        valor=round(valor, casas + 2),
        unidade=unidade,
        casas=casas,
        referencia=referencia or quando,
        periodicidade=periodicidade,
        detalhe=detalhe,
        fonte=fonte,
        procedencia=procedencia,
        mini=[(d, round(v, casas + 2)) for d, v in reduzida],
        secao=secao,
    )


def ha_um_ano(pontos: list[Ponto]) -> float | None:
    """O valor de 12 meses antes do último ponto (ou o mais próximo anterior)."""
    if not pontos:
        return None
    alvo = pontos[-1][0] - timedelta(days=365)
    antes = [v for d, v in pontos if d <= alvo]
    return antes[-1] if antes else None


def em_reais_de_hoje(mensal_milhoes: list[Ponto], ipca: list[Ponto]) -> tuple[list[Ponto], date]:
    """A soma de 12 meses de um fluxo mensal em R$ milhões, em R$ bilhões a preços do
    último mês do dado (ou do último com IPCA, se o IPCA ainda não chegou nele), e esse mês.
    Mês sem IPCA fica de fora."""
    indice = contas.indice_de_precos(ipca)
    ultimo = max(d for d, _ in mensal_milhoes)
    base = max(d for d in indice if d <= ultimo)
    reais = contas.a_precos_de(mensal_milhoes, indice, base)
    return [(d, v / 1000) for d, v in contas.soma_movel(reais)], base


def variante(
    id: str,
    rotulo: str,
    titulo: str,
    series: list[Serie],
    *,
    unidade: str,
    periodicidade: Periodicidade,
    casas: int = 1,
    nota: str = "",
    fonte: str = "",
) -> VarianteGrafico:
    return VarianteGrafico(
        id=id,
        rotulo=rotulo,
        titulo=titulo,
        series=series,
        unidade=unidade,
        casas=casas,
        periodicidade=periodicidade,
        nota=nota,
        fonte=fonte,
    )


def com_variantes(
    g: Grafico, rotulo: str, *outras: VarianteGrafico, nome_da_lista: str = "Ver em"
) -> Grafico:
    """O gráfico com a lista que troca a unidade (Caio, 19/11/2026: *"coloque um parâmetro
    pra mudar o gráfico em % do PIB"*): ele mesmo é a primeira opção, com o nome `rotulo`."""
    primeira = VarianteGrafico(
        id="principal",
        rotulo=rotulo,
        titulo=g.titulo,
        unidade=g.unidade,
        casas=g.casas,
        periodicidade=g.periodicidade,
        series=g.series,
        linhas=g.linhas,
        nota=g.nota,
        fonte=g.fonte,
    )
    return g.model_copy(
        update={"variantes": [primeira, *outras], "rotulo_variantes": nome_da_lista}
    )
