"""Módulo de prêmios de seguro de vida.

Consome motor/parametros/fatores_2024.csv (fonte primária anonimizada — ver README).
Mecânica validada contra a tabela de precificação de origem:
    prêmio_anual  = fator(idade, chave) × capital / 1.000   (família FI: ÷ 10)
    prêmio_mensal = prêmio_anual × fator_modal
Chave = FAMILIA + PRAZO + SEXO [+ "+" se capital >= 1 mi e família em WL/WV/WS]
        [+ classe de risco] [+ "F" fumante, temporários] [+ "ST" p/ TP standard]
"""
from __future__ import annotations
import csv
from pathlib import Path
from functools import lru_cache

DIR_PARAMS = Path(__file__).parent / "parametros"

IOF = 0.0038   # Decreto nº 6.306/2007 (seguro de vida): 0,38%

# Regras tarifárias da seguradora (banda de capital e fatores de fracionamento)
# ficam em parametros/regras_tarifarias.json, que NÃO é redistribuído junto com
# o código (cessão condicionada à não redistribuição). Ver
# parametros/DADOS_NAO_DISTRIBUIDOS.md para o esquema esperado.
ARQ_REGRAS = DIR_PARAMS / "regras_tarifarias.json"


@lru_cache(maxsize=1)
def _regras() -> dict:
    import json
    if not ARQ_REGRAS.exists():
        raise FileNotFoundError(
            "parametros/regras_tarifarias.json ausente: a tabela de precificação da "
            "seguradora não é distribuída. Ver parametros/DADOS_NAO_DISTRIBUIDOS.md.")
    return json.loads(ARQ_REGRAS.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _tabela() -> tuple[dict, list]:
    """Retorna ({(idade, chave): fator}, [chaves])."""
    tab, chaves = {}, []
    with open(DIR_PARAMS / "fatores_2024.csv", newline="") as f:
        rows = list(csv.reader(f))
    chaves = rows[0]  # header; col 0 ('WL') é a coluna de idade
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        idade = int(float(r[0]))
        for j, v in enumerate(r[1:], start=1):
            if v not in ("", "-"):
                try:
                    tab[(idade, chaves[j])] = float(v)
                except ValueError:
                    pass
    return tab, chaves


def montar_chave(familia: str, prazo, sexo: str, capital: float,
                 classe: str = "Standard", fumante: bool = False) -> str:
    """Chave de produto: família + prazo + sexo [+ banda] [+ classe] [+ fumante]."""
    rg = _regras()
    chave = f"{familia}{prazo}{sexo}"
    if (capital >= rg["banda_preferencial_min"] and familia in rg["familias_com_banda"]
            and str(prazo) != "5"):
        chave += "+"
    if classe == "Standard":
        if familia == "TP":
            chave += "ST"
    else:
        chave += classe
    if fumante and familia == "TP":
        chave += "F"
    return chave


def fator(idade: int, chave: str) -> float | None:
    return _tabela()[0].get((idade, chave))


def fator_modal(familia: str, prazo, capital: float) -> float:
    """Fator de fracionamento mensal, conforme as regras da seguradora."""
    fm = _regras()["fator_modal"]
    if familia.startswith("D"):
        return fm["decrescentes"]
    if familia == "WL" and str(prazo) == "5":
        return fm["wl5"]
    if familia == "TP":
        return fm["tp"]
    return fm["capital_alto"] if capital >= fm["limite_capital"] else fm["demais"]


def premio(idade: int, familia: str, prazo, sexo: str, capital: float,
           classe: str = "Standard", fumante: bool = False,
           com_iof: bool = True) -> dict | None:
    """Prêmio anual e mensal. None se produto indisponível na idade (contratabilidade)."""
    chave = montar_chave(familia, prazo, sexo, capital, classe, fumante)
    f = fator(idade, chave)
    # fator ausente OU zerado = produto indisponível nessa idade (contratabilidade).
    # A planilha-fonte grava 0 em algumas células; tratá-las como prêmio zero
    # produziria "seguro grátis" — erro detectado no grid de idade em 11/set/2026.
    if f is None or f <= 0:
        return None
    divisor = 10 if familia == "FI" else 1000
    anual = f * capital / divisor
    mensal = anual * fator_modal(familia, prazo, capital)
    if com_iof:
        anual, mensal = anual * (1 + IOF), mensal * (1 + IOF)
    return {"chave": chave, "fator": f, "premio_anual": anual,
            "premio_mensal": mensal, "premio_mensalizado_ano": mensal * 12}


def vp_premios(p: dict, r: float, anos: int, mensal: bool = True) -> float:
    """VP do fluxo de prêmios ao longo de `anos` anos de pagamento.

    mensal=True reproduz a prática de mercado (12 pagamentos por ano). Dois
    efeitos OPOSTOS entram aqui e não devem ser confundidos:

      (+) CARREGAMENTO DE FRACIONAMENTO — 12 x fator_modal > 1, isto é, pagar
          mensalmente custa nominalmente mais que pagar à vista no início do
          ano. É o juro embutido que a seguradora cobra pelo parcelamento.
      (-) ADIAMENTO — os pagamentos se distribuem ao longo do ano em vez de
          saírem todos no dia 1º, o que reduz o valor presente.

    O efeito líquido depende do fator modal do produto e da taxa real. Reportar
    os dois separadamente na dissertação: o carregamento é preço, o adiamento é
    financeiro.

    Fluxos em R$ CONSTANTES: pressupõe prêmio corrigido por índice de preços,
    que é a prática do produto (a planilha-fonte mantém série IPCA justamente
    para isso). Se o prêmio fosse nominalmente fixo, o custo real CAIRIA ao
    longo do tempo e o seguro ficaria mais barato — sensibilidade a testar.
    """
    if anos <= 0:
        return 0.0
    if not mensal:
        return sum(p["premio_anual"] / (1 + r) ** k for k in range(anos))
    pm = p["premio_mensal"]
    return sum(pm / (1 + r) ** (m / 12) for m in range(12 * anos))


def carregamento_fracionamento(familia: str, prazo, capital: float) -> float:
    """Quanto o pagamento mensal custa a mais, em termos NOMINAIS, que o anual.
    Ex.: 0,0596 = pagar em 12 vezes sai 5,96% mais caro no ano."""
    return fator_modal(familia, prazo, capital) * 12 - 1


def disponibilidade(idade: int) -> int:
    """Nº de chaves de produto com fator na idade (proxy de contratabilidade)."""
    tab, _ = _tabela()
    return sum(1 for (i, _c) in tab if i == idade)
