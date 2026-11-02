"""Valor de resgate (reserva matemática resgatável) dos produtos vitalícios.

Fonte: motor/parametros/resgate.csv — extraído da planilha de cotação da
seguradora (ver parametros/README.md; NÃO citar a seguradora na dissertação).
Cobertura: WL5/10/20/30/60/65/70/75/80/100 e WV10/20/30, M e F, por idade de
emissão, para os anos 1..120 de vigência.

UNIDADE: fração do capital segurado. VR(t) = 1,0 significa que a apólice
atingiu o valor de dotação (WL matura aos 100 anos: VR = capital).
Zeros à direita = apólice já encerrada; tratados como indisponíveis, não como
resgate nulo.

USO NA MODELAGEM — cuidado com dupla contagem:
O valor de resgate NÃO deve ser subtraído do custo do seguro quando o contrato
é mantido até a morte. Nesse caso a reserva é absorvida no pagamento do capital
e não é recuperada pelo titular. O resgate só se realiza se o contrato for
ABANDONADO em vida. É por isso que ele entra aqui por dois canais distintos:

  (a) LAPSO (contra o seguro): a apólice caduca com hazard lambda; o titular
      recupera VR(tau) mas a família volta ao inventário integral.
  (b) REVERSIBILIDADE (a favor do seguro): mede quanto do custo já incorrido é
      recuperável — dimensão em que a doação em vida vale exatamente zero.
"""
from __future__ import annotations
import csv
from pathlib import Path
from functools import lru_cache

DIR_PARAMS = Path(__file__).parent / "parametros"
ARQ = DIR_PARAMS / "resgate.csv"

IDADE_MATURIDADE = 100  # WL/WV dotam aos 100; após isso a tabela zera


@lru_cache(maxsize=1)
def _tabela() -> dict:
    """{(familia, prazo, sexo, idade_emissao): [vr_ano1, ..., vr_ano120]}"""
    tab = {}
    if not ARQ.exists():
        return tab
    with open(ARQ, newline="") as f:
        for row in csv.DictReader(f):
            chave = (row["familia"], int(row["prazo"]), row["sexo"],
                     int(row["idade_emissao"]))
            serie = []
            for i in range(1, 121):
                v = row.get(f"a{i}", "")
                serie.append(float(v) if v not in ("", None) else None)
            tab[chave] = serie
    return tab


def disponivel(familia: str, prazo, sexo: str, idade_emissao: int) -> bool:
    return (familia, int(prazo), sexo, int(idade_emissao)) in _tabela()


def vr(familia: str, prazo, sexo: str, idade_emissao: int, t: int) -> float | None:
    """Valor de resgate no ANIVERSÁRIO t (t=1 é o fim do 1º ano), como fração do
    capital segurado. None se o produto/idade não existe ou a apólice já encerrou.

    Os dois primeiros anos são tipicamente zero (período de carência de resgate)
    — isso é dado da tabela, não premissa nossa.
    """
    serie = _tabela().get((familia, int(prazo), sexo, int(idade_emissao)))
    if serie is None:
        return None
    if t < 1 or t > 120:
        return None
    if idade_emissao + t > IDADE_MATURIDADE:
        return None            # apólice já dotada/encerrada: zeros da tabela
    return serie[t - 1]


def curva(familia: str, prazo, sexo: str, idade_emissao: int) -> list[float]:
    """VR por ano de vigência, truncada na maturidade (idade 100)."""
    serie = _tabela().get((familia, int(prazo), sexo, int(idade_emissao)))
    if serie is None:
        return []
    n = min(120, IDADE_MATURIDADE - int(idade_emissao))
    return [(serie[i] or 0.0) for i in range(n)]


def valor_resgate(capital: float, familia: str, prazo, sexo: str,
                  idade_emissao: int, t: int) -> float:
    """Valor de resgate em R$ (0,0 se indisponível).

    Após a DOTAÇÃO — o vitalício matura aos 100 anos e paga o capital — a série
    da planilha volta a zero, pois não há mais apólice. Ler esse zero como
    "nada recuperável" subestimaria a reversibilidade: o titular já recebeu o
    capital. A partir da maturação, portanto, carrega-se o último valor da
    série. O efeito é pequeno (≈0,07% do índice de reversibilidade aos 50 anos,
    verificado em 11/set/2026), mas a correção é gratuita e elimina um viés
    conhecido contra o instrumento.
    """
    f = vr(familia, prazo, sexo, idade_emissao, t)
    if f:
        return f * capital
    anterior = 0.0
    for k in range(t - 1, -1, -1):
        g = vr(familia, prazo, sexo, idade_emissao, k)
        if g:
            anterior = g
            break
    return anterior * capital


# --------------------------------------------------------------- diagnóstico

def taxa_recuperacao(capital: float, premio_anual: float, familia: str, prazo,
                     sexo: str, idade_emissao: int, t: int,
                     max_anos_pagto: int | None = None) -> float | None:
    """VR(t) / (prêmios NOMINAIS pagos até t). Mede quanto do desembolso é
    recuperável. Não desconta — é razão de caixa, para leitura direta."""
    v = valor_resgate(capital, familia, prazo, sexo, idade_emissao, t)
    n_pagtos = min(t, max_anos_pagto or t)
    pago = premio_anual * n_pagtos
    return v / pago if pago > 0 else None
