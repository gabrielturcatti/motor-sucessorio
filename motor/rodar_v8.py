"""Motor v8 (11/set/2026) — agravo no cenário E e grade de caducidade ampliada.

Mudanças em relação ao v7:
  1. CENÁRIO E COM AGRAVO. Até o v7 o cenário declaradamente desfavorável rodava
     em classe Standard, favorecendo o seguro justamente onde deveria castigá-lo.
     Passa a rodar em classe C (+31,8% de prêmio aos 70) e a escada completa
     Standard → A1 → A2 → B → C → D1 entra como eixo de sensibilidade.
     D1 é o TETO de aceitação do vitalício: não existe classe além dela em
     idade alguma para WL10, e WL20/WL30 só aceitam Standard.
  2. GRADE DE CADUCIDADE AMPLIADA para 0/2/5/10/20% ao ano. Os dois valores
     altos não são arbitrários: decorrem da razão entre cancelamentos e prêmios
     emitidos do ramo de vida individual na base SES/SUSEP (~20% a.a. no
     período 2016-2025), lida como cota superior da rotatividade do ramo.
     O piso de 5% dialoga com a taxa de caducidade por inadimplência do mercado
     norte-americano reportada pelo ACLI (4,7% a.a. em 2024).
     A conversão da razão contábil brasileira em hazard por apólice NÃO é
     identificada pelos dados públicos — por isso a grade, e não um ponto.

Uso: python3 rodar_v8.py
"""
import csv
import dataclasses
import motor
import premios
from cenarios import CENARIOS

R_BASE, REGIME_BASE = 0.06, "2026"
SPREAD_SEM_CREDITO = 1.00
LAPSOS = (0.0, 0.02, 0.05, 0.10, 0.20)
ESCADA_AGRAVO = ("Standard", "A1", "A2", "B", "C", "D1")


def principal():
    for regime in ("2026", "pos2027"):
        for lp in LAPSOS:
            res = motor.rodar(regime=regime, lapso_aa=lp, ir_contrafactual=True)
            arq = f"resultados/v8_{regime}_r6ir_lapso{int(lp*100)}.csv"
            motor.salvar_csv(res, arq)
            print("gravado", arq)


def varredura():
    linhas = []

    def coleta(eixo, valor, **kw):
        for res in motor.rodar(regime=REGIME_BASE, lapso_aa=0.0,
                               ir_contrafactual=True, **kw):
            fr = motor.pareto(res)
            for nome, v in res.items():
                if isinstance(v, dict):
                    linhas.append([eixo, valor, res["cenario"], nome,
                                   round(v["E"], 2), round(v["CTE95"], 2),
                                   int(nome in fr)])

    for r in (0.04, 0.05, 0.06, 0.07, 0.08):
        coleta("taxa_desconto", r, r=r)
    for a in (0.15, 0.175, 0.225):
        coleta("aliquota_ir", a, r=R_BASE, aliquota_ir=a)
    for p in (0.0, 0.30, 0.50):
        coleta("plusvalia", p, r=R_BASE, plusvalia=p)
    for p in (0.0, 0.30, 0.50):
        coleta("plusvalia_sem_credito", p, r=R_BASE, plusvalia=p,
               spread_ponte=SPREAD_SEM_CREDITO)

    with open("resultados/v8_sensibilidade.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["eixo", "valor", "cenario", "estrategia",
                    "vp_esperado", "cte95", "na_fronteira"])
        w.writerows(linhas)
    print("gravado resultados/v8_sensibilidade.csv", len(linhas), "linhas")


def escada_agravo():
    """Sensibilidade à classe de risco no cenário E (idade 70)."""
    E = CENARIOS["E"]
    linhas = []
    for classe in ESCADA_AGRAVO:
        CENARIOS["_AG"] = dataclasses.replace(E, codigo="_AG",
                                              classe_risco=classe)
        res = motor.avaliar("_AG", r=R_BASE, regime=REGIME_BASE,
                            ir_contrafactual=True)
        fr = motor.pareto(res)
        ci = res["custo_inventario_nominal"]
        p = premios.premio(E.idade, "WL", 10, E.sexo, ci, classe)
        seg = res["seguro"]
        linhas.append([classe, round(p["fator"], 4), round(p["premio_anual"], 2),
                       round(seg["E"], 2), round(seg["CTE95"], 2),
                       int("seguro" in fr),
                       ", ".join(fr)])
    del CENARIOS["_AG"]
    with open("resultados/v8_escada_agravo.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["classe", "fator", "premio_anual", "vp_esperado", "cte95",
                    "seguro_na_fronteira", "fronteira"])
        w.writerows(linhas)
    print("gravado resultados/v8_escada_agravo.csv", len(linhas), "linhas")


def contratabilidade():
    """Mapa de oferta: quais classes e quais idades cada produto aceita.

    É o insumo do argumento do cenário E: o teto de agravo e o teto de idade
    são opostos entre vitalícios e temporários, e é a conjunção dos dois que
    fecha o mercado para o comprador idoso e agravado.
    """
    CL = ["Standard", "A1", "A2", "B", "C", "D1", "D2", "E1", "E2",
          "F1", "F2", "G", "H1", "H2"]
    linhas = []
    for fam, prz in (("WL", 10), ("WL", 20), ("WL", 30), ("TP", 10), ("TP", 20)):
        for sexo in ("M", "F"):
            for classe in CL:
                idades = [i for i in range(25, 95)
                          if (premios.premio(i, fam, prz, sexo, 1_000_000, classe)
                              or {}).get("fator")]
                if idades:
                    linhas.append([f"{fam}{prz}", sexo, classe,
                                   min(idades), max(idades)])
    with open("resultados/v8_contratabilidade.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["produto", "sexo", "classe", "idade_min", "idade_max"])
        w.writerows(linhas)
    print("gravado resultados/v8_contratabilidade.csv", len(linhas), "linhas")


if __name__ == "__main__":
    principal()
    varredura()
    escada_agravo()
    contratabilidade()
