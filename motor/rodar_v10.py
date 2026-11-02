"""Motor v10 (02/nov/2026) — sensibilidades que faltavam no texto.

1. Holding x doação: a auditoria de set/2026 registrou como limitação a
   assimetria de parametrização — holding com custos fixos (R$ 25 mil de
   constituição, R$ 18 mil/ano de manutenção) contra doação com honorário de
   estruturação ad valorem (1,5%). Estes parâmetros governam a quarta parcela
   do IES e a pertinência de holding e doação à fronteira. Aqui são varridos
   um a um e em combinação, com os limiares de saída/entrada na fronteira.

2. Sensibilidades complementares prometidas na seção 5 e não reportadas:
   alíquota efetiva de IR do contrafactual, deságio de venda forçada (na
   variante sem crédito-ponte, onde o ramo de venda é ativo), carga do prêmio
   comercial (±30%), tábua de mortalidade (BR-EMS 2021 e IBGE 2024) e
   (A transmissão a valor de mercado do art. 23 da Lei 9.532/1997 foi
   descartada: ver comentário em complementares().)

O caso base é idêntico ao v9 (verificado: CSVs do v9 reproduzidos byte a byte
depois da inclusão dos novos parâmetros no motor).

Uso: python3 rodar_v10.py
"""
import csv

import atuarial
import motor

R, REG = 0.06, "2026"
SEM_CREDITO = float("inf")  # crédito inexistente: só resta a venda forçada.
# (O v9 usava spread de 100% a.a.; com 6 meses de prazo esse crédito ainda
#  saía mais barato que a venda e era tomado — a variante não eliminava o crédito.)
CENS = ("A", "B", "C", "D", "E", "F")


def _rodar(**kw):
    return motor.rodar(r=R, regime=REG, lapso_aa=0.0, ir_contrafactual=True, **kw)


def coleta(linhas, eixo, valor, **kw):
    for res in _rodar(**kw):
        fr = motor.pareto(res)
        for nome, v in res.items():
            if isinstance(v, dict):
                linhas.append([eixo, valor, res["cenario"], nome,
                               round(v["E"], 2), round(v["CTE95"], 2),
                               int(nome in fr)])


def holding_doacao():
    linhas = []
    for c in (10_000, 25_000, 50_000, 100_000, 250_000):
        coleta(linhas, "holding_constituicao", c, holding_constituicao=c)
    for m in (6_000, 18_000, 36_000, 60_000, 120_000):
        coleta(linhas, "holding_manutencao", m, holding_manutencao=m)
    for h in (0.005, 0.015, 0.03, 0.05):
        coleta(linhas, "honor_doacao", h, pct_honor_doacao=h)
    # combinações extremas: assimetria invertida nos dois sentidos
    coleta(linhas, "combinado", "holding_barata_doacao_cara",
           holding_constituicao=10_000, holding_manutencao=6_000,
           pct_honor_doacao=0.05)
    coleta(linhas, "combinado", "holding_cara_doacao_barata",
           holding_constituicao=100_000, holding_manutencao=60_000,
           pct_honor_doacao=0.005)
    with open("resultados/v10_holding_doacao.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["eixo", "valor", "cenario", "estrategia",
                    "vp_esperado", "cte95", "na_fronteira"])
        w.writerows(linhas)
    print("gravado resultados/v10_holding_doacao.csv", len(linhas), "linhas")


def _na_fronteira(cen, estrategia, **kw):
    res = motor.avaliar(cen, r=R, regime=REG, lapso_aa=0.0,
                        ir_contrafactual=True, **kw)
    return estrategia in motor.pareto(res)


def limiar_manutencao(cen, teto=2_000_000, passo=100):
    """Menor manutenção anual (R$) a partir da qual a holding sai da fronteira."""
    if not _na_fronteira(cen, "holding"):
        return None
    lo, hi = 18_000, teto
    if _na_fronteira(cen, "holding", holding_manutencao=hi):
        return float("inf")
    while hi - lo > passo:
        mid = (lo + hi) / 2
        if _na_fronteira(cen, "holding", holding_manutencao=mid):
            lo = mid
        else:
            hi = mid
    return hi


def limiar_honor_doacao(cen, teto=0.30):
    """Menor honorário de estruturação a partir do qual a doação sai da fronteira."""
    if not _na_fronteira(cen, "doacao"):
        return None
    lo, hi = 0.015, teto
    if _na_fronteira(cen, "doacao", pct_honor_doacao=hi):
        return float("inf")
    for _ in range(40):
        mid = (lo + hi) / 2
        if _na_fronteira(cen, "doacao", pct_honor_doacao=mid):
            lo = mid
        else:
            hi = mid
    return hi


def limiares():
    linhas = []
    for cen in CENS:
        m = limiar_manutencao(cen)
        h = limiar_honor_doacao(cen)
        linhas.append([cen, "" if m is None else m, "" if h is None else round(h, 5)])
        print(f"  {cen}: holding sai com manutenção ≥ {m}; doação sai com honorário ≥ {h}")
    with open("resultados/v10_limiares_holding_doacao.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "manutencao_sai_fronteira", "honor_doacao_sai_fronteira"])
        w.writerows(linhas)
    print("gravado resultados/v10_limiares_holding_doacao.csv")


def sem_credito():
    """Variante sem crédito-ponte (Tabela 9), agora com crédito de fato inexistente."""
    linhas = []
    for p in (0.0, 0.30, 0.50):
        coleta(linhas, "plusvalia_sem_credito", p, plusvalia=p, spread_ponte=SEM_CREDITO)
    with open("resultados/v10_sem_credito.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["eixo", "valor", "cenario", "estrategia",
                    "vp_esperado", "cte95", "na_fronteira"])
        w.writerows(linhas)
    print("gravado resultados/v10_sem_credito.csv", len(linhas), "linhas")


def complementares():
    linhas = []
    coleta(linhas, "base", "base")
    for a in (0.15, 0.175, 0.225):
        coleta(linhas, "aliquota_ir", a, aliquota_ir=a)
    for c in (0.7, 1.3):
        coleta(linhas, "carga_premio", c, carga_premio=c)
    for d in (0.15, 0.25, 0.35):
        coleta(linhas, "desagio_sem_credito", d, desagio_venda=d,
               spread_ponte=SEM_CREDITO, plusvalia=0.30)
    # Transmissão gratuita a valor de mercado (art. 23 da Lei 9.532/1997) NÃO é
    # varrida: a faculdade do valor declarado alcança igualmente herança e
    # doação, e o ganho latente fica com os herdeiros em todas as estratégias.
    # Aplicá-la só às transmissões em vida enviesaria contra holding e doação.
    # tábua: troca o arquivo e limpa o cache
    # v11: custo de vida da família durante o bloqueio do inventário — despesa
    # anual de 4% do patrimônio financiada na proporção dos bens presos no espólio.
    CONS = 0.04
    coleta(linhas, "consumo", "com_credito", consumo_aa=CONS)
    coleta(linhas, "consumo", "sem_credito", consumo_aa=CONS,
           spread_ponte=SEM_CREDITO, plusvalia=0.30)
    coleta(linhas, "consumo", "com_credito_seguro_cobre", consumo_aa=CONS,
           seguro_cobre_consumo=True)
    coleta(linhas, "consumo", "sem_credito_seguro_cobre", consumo_aa=CONS,
           seguro_cobre_consumo=True, spread_ponte=SEM_CREDITO, plusvalia=0.30)
    original = atuarial.ARQ_TABUA
    for nome in ("tabua_brems_mt_2021.csv", "tabua_ibge_2024.csv"):
        atuarial.ARQ_TABUA = atuarial.DIR_PARAMS / nome
        atuarial.tabua.cache_clear()
        coleta(linhas, "tabua", nome.replace("tabua_", "").replace(".csv", ""))
    atuarial.ARQ_TABUA = original
    atuarial.tabua.cache_clear()
    with open("resultados/v10_complementares.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["eixo", "valor", "cenario", "estrategia",
                    "vp_esperado", "cte95", "na_fronteira"])
        w.writerows(linhas)
    print("gravado resultados/v10_complementares.csv", len(linhas), "linhas")


if __name__ == "__main__":
    holding_doacao()
    limiares()
    sem_credito()
    complementares()
