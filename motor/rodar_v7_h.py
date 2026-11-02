"""Motor v6 (11/set/2026) — cenário H (haveres) e grid de idade × produto.

Saídas:
  resultados/v7_cenario_h.csv        — cenário H, variantes e produtos
  resultados/v7_grid_idade.csv       — cenários A-F × idade {40,50,60,70} × produto
"""
import csv
import motor, cenario_h as ch
from cenarios import CENARIOS
import dataclasses

R, REGIME = 0.06, "2026"


def roda_h():
    linhas = []

    def add(variante, produto, **kw):
        soc_kw = {k: v for k, v in kw.items() if k in ("idades", "sexos", "parcelas", "valor_firma")}
        av_kw = {k: v for k, v in kw.items() if k in ("spread_ponte", "plusvalia", "r")}
        res = ch.avaliar_h(ch.SociedadeH(produto=produto, **soc_kw), **av_kw)
        if "erro" in res:
            linhas.append([variante, f"{produto[0]}{produto[1]}", "—", "indisponível", "", "", ""])
            return
        b, s = res["baseline_haveres"], res["seguro_buysell"]
        dom_s = int(s["E"] <= b["E"] and s["CTE95"] <= b["CTE95"])
        dom_b = int(b["E"] <= s["E"] and b["CTE95"] <= s["CTE95"])
        for nome, v, na in (("baseline_haveres", b, int(not dom_s)), ("seguro_buysell", s, int(not dom_b))):
            linhas.append([variante, f"{produto[0]}{produto[1]}", nome,
                           round(v["E"], 2), round(v["CTE95"], 2), na,
                           round(res["primeira_morte_esperada"], 1)])

    for prod in (("WL", 10), ("WL", 20), ("WL", 30), ("TP", 10), ("TP", 20)):
        add("base", prod)
    for prod in (("WL", 20), ("TP", 10)):
        add("sem_parcelamento", prod, parcelas=1)
        add("sem_credito_ponte", prod, spread_ponte=1.00, plusvalia=0.50)
        add("sem_parcelamento_sem_credito", prod, parcelas=1, spread_ponte=1.00, plusvalia=0.50)
        add("socios_jovens_35_50", prod, idades=(35, 38, 42, 46, 50))
        add("firma_50mi", prod, valor_firma=50_000_000.0)
        for rr in (0.04, 0.08):
            add(f"r_{int(rr*100)}pct", prod, r=rr)

    with open("resultados/v7_cenario_h.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variante", "produto", "estrategia", "vp_esperado", "cte95",
                    "na_fronteira", "primeira_morte_anos"])
        w.writerows(linhas)
    print("gravado resultados/v7_cenario_h.csv", len(linhas), "linhas")


def roda_grid():
    """Sensibilidade pedida pela banca: idade do segurado 40/50/60/70."""
    linhas = []
    for codigo in ("A", "B", "C", "D", "E", "F"):
        base = CENARIOS[codigo]
        for idade in (40, 50, 60, 70):
            for prod in (("WL", 10), ("WL", 20), ("WL", 30), ("TP", 10), ("TP", 20)):
                CENARIOS[codigo] = dataclasses.replace(base, idade=idade)
                try:
                    res = motor.avaliar(codigo, r=R, regime=REGIME, lapso_aa=0.0,
                                        ir_contrafactual=True, produto=prod)
                except Exception as e:
                    CENARIOS[codigo] = base
                    linhas.append([codigo, idade, f"{prod[0]}{prod[1]}", "erro", "", "", ""])
                    continue
                fr = motor.pareto(res)
                tem_seguro = "seguro" in res
                for nome, v in res.items():
                    if isinstance(v, dict) and "E" in v:
                        linhas.append([codigo, idade, f"{prod[0]}{prod[1]}", nome,
                                       round(v["E"], 2), round(v["CTE95"], 2),
                                       int(nome in fr)])
                if not tem_seguro:
                    linhas.append([codigo, idade, f"{prod[0]}{prod[1]}", "seguro",
                                   "indisponível", "", 0])
                CENARIOS[codigo] = base
    with open("resultados/v7_grid_idade.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "idade", "produto", "estrategia", "vp_esperado",
                    "cte95", "na_fronteira"])
        w.writerows(linhas)
    print("gravado resultados/v7_grid_idade.csv", len(linhas), "linhas")


if __name__ == "__main__":
    roda_h()
    roda_grid()
