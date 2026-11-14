"""Números que vêm de norma. Cada um com a referência da norma lida.

Regra do projeto: número de lei só entra daqui, e só depois de a norma ter sido lida na fonte
oficial (a data da leitura fica ao lado).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MetaDeInflacao:
    centro: float
    intervalo: float
    desde: date
    referencia: str


META_CONTINUA = MetaDeInflacao(
    centro=3.0,
    intervalo=1.5,
    desde=date(2025, 1, 1),
    # Lida em 14/11/2026 na API de normativos do BCB (exibenormativo?p1=Resolução CMN&p2=5141):
    # "Art. 2º A meta para a variação acumulada em doze meses do índice de preços indicado no
    # art. 1º, apurada mês a mês, a ser aplicada no período que se inicia em 1º de janeiro de
    # 2025, é fixada em 3,00% (três inteiros por cento), com intervalo de tolerância de menos
    # 1,50 p.p. (um e meio ponto percentual) e de mais 1,50 p.p." O art. 1º indica o IPCA.
    referencia="Resolução CMN nº 5.141, de 26/6/2024, art. 2º",
)

# Ainda NÃO lidos na fonte oficial (o Planalto redireciona de fora do Brasil), e por isso
# fora da tela: a meta de resultado primário e a banda do arcabouço (LC 200/2023 e LDO),
# os limites de pessoal da LRF (LC 101/2000, arts. 19 e 20) e o limite da dívida dos estados
# (Resolução do Senado 40/2001).
