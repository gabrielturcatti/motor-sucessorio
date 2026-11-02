"""Módulo atuarial — VP esperado ponderado por probabilidades de morte.

Tábua: motor/parametros/tabua_mortalidade.csv com colunas idade,qx_m,qx_f
(IBGE 2024 ou BR-EMS 2021; ver task pendente). Enquanto o arquivo não existir,
o módulo opera só em modo determinístico (idade de óbito fixada).
Fluxos em R$ CONSTANTES; taxa de desconto REAL.
"""
from __future__ import annotations
import csv
from pathlib import Path
from functools import lru_cache

DIR_PARAMS = Path(__file__).parent / "parametros"
ARQ_TABUA = DIR_PARAMS / "tabua_mortalidade.csv"


@lru_cache(maxsize=1)
def tabua() -> dict[str, dict[int, float]] | None:
    if not ARQ_TABUA.exists():
        return None
    qx = {"M": {}, "F": {}}
    with open(ARQ_TABUA, newline="") as f:
        for row in csv.DictReader(f):
            i = int(row["idade"])
            qx["M"][i] = float(row["qx_m"])
            qx["F"][i] = float(row["qx_f"])
    return qx


def prob_morte_no_ano(idade: int, sexo: str, t: int) -> float:
    """P(morrer entre t e t+1 | vivo em idade). Requer tábua."""
    q = tabua()[sexo]
    p_sobrev = 1.0
    for k in range(t):
        p_sobrev *= 1 - q.get(idade + k, 1.0)
    return p_sobrev * q.get(idade + t, 1.0)


def expectativa_vida(idade: int, sexo: str) -> float:
    q = tabua()[sexo]
    e, p = 0.0, 1.0
    for k in range(idade, 121):
        p *= 1 - q.get(k, 1.0)
        e += p
    return e


def vp_fluxo_ate_morte(fluxo_anual: float, idade: int, sexo: str, r: float,
                       max_anos: int | None = None) -> float:
    """VP atuarial de um fluxo anual pago enquanto vivo (anuidade antecipada).
    max_anos limita o pagamento (ex.: WL10 paga 10 anos; temporário até idade X)."""
    q = tabua()[sexo]
    vp, p = 0.0, 1.0
    horizonte = min(121 - idade, max_anos or 999)
    for t in range(horizonte):
        vp += fluxo_anual * p / (1 + r) ** t
        p *= 1 - q.get(idade + t, 1.0)
        if p <= 0:
            break
    return vp


def vp_custo_na_morte(custo, idade: int, sexo: str, r: float) -> float:
    """VP esperado de um custo incorrido na morte.
    custo: valor fixo ou função custo(t) — permite custo que varia com o ano do óbito."""
    vp = 0.0
    for t in range(121 - idade):
        pm = prob_morte_no_ano(idade, sexo, t)
        if pm <= 0:
            continue
        c = custo(t) if callable(custo) else custo
        vp += c * pm / (1 + r) ** (t + 0.5)
    return vp


def prob_sobreviver_alem(idade: int, sexo: str, idade_limite: int) -> float:
    """P(sobreviver além de idade_limite) — mede o risco de 'sobreviver à cobertura'
    de um temporário (mecanismo do cenário E)."""
    q = tabua()[sexo]
    p = 1.0
    for k in range(idade, idade_limite):
        p *= 1 - q.get(k, 1.0)
    return p


def distribuicao_custo(custo_por_ano_obito, idade: int, sexo: str, r: float) -> list:
    """[(prob, vp_custo)] por ano possível de óbito. custo_por_ano_obito(t) → custo
    total (nominal) da estratégia se a morte ocorre no ano t (inclui prêmios pagos
    até t, custos na morte etc., já em VP)."""
    dist = []
    for t in range(121 - idade):
        pm = prob_morte_no_ano(idade, sexo, t)
        if pm > 0:
            dist.append((pm, custo_por_ano_obito(t)))
    return dist


def cte(dist: list, nivel: float = 0.95) -> float:
    """Conditional Tail Expectation: custo médio nos (1-nivel) piores desfechos."""
    ordenado = sorted(dist, key=lambda x: x[1], reverse=True)
    alvo = (1 - nivel) * sum(p for p, _ in dist)
    acum, soma = 0.0, 0.0
    for p, c in ordenado:
        usa = min(p, alvo - acum)
        soma += usa * c
        acum += usa
        if acum >= alvo:
            break
    return soma / alvo if alvo > 0 else 0.0


def esperanca(dist: list) -> float:
    tot = sum(p for p, _ in dist)
    return sum(p * c for p, c in dist) / tot if tot else 0.0


# ----------------------------------------------------- modo determinístico

def vp_fluxo_deterministico(fluxo_anual: float, anos: float, r: float) -> float:
    n = int(anos)
    return sum(fluxo_anual / (1 + r) ** t for t in range(n))


def vp_custo_deterministico(custo: float, anos_ate_obito: float, r: float) -> float:
    return custo / (1 + r) ** anos_ate_obito
