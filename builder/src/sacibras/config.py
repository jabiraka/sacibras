"""Escolhas de ambiente do builder."""

from __future__ import annotations

import os


def usar_b3() -> bool:
    """Liga as fontes que leem o SITE da B3 (índices setoriais, futuros). Desligado por padrão.

    O site da B3 diz, na página do Boletim Diário (lido em 14/11/2026): "é expressamente
    vedada a coleta automatizada, inclusive por meio de ferramentas de inteligência
    artificial, para quaisquer finalidades, comerciais ou não". Enquanto o Caio não decidir,
    o padrão é não coletar: o Ibovespa vem do IPEADATA, o câmbio do Banco Central e a curva de
    juros do Tesouro Direto (dado aberto). `SB_B3=1` liga, por conta de quem roda.
    """
    return os.environ.get("SB_B3", "").strip().lower() in ("1", "true", "sim")
