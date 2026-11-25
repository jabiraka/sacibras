"""O aviso de nota longa do build (Caio, 25/11/2026: textos curtos, sempre)."""

from sacibras.construir import frases


def test_conta_frases() -> None:
    assert frases("") == 0
    assert frases("Cálculo próprio, não previsão.") == 1
    assert frases("Cálculo próprio. Faixa de 90 %.") == 2
    assert frases("Juro de 4,5 % e 1.504 emendas. Outra frase. E mais uma") == 3
