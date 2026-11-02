"""Motor v9 (11/set/2026) — taxa de administração do VGBL com fonte e grade.

Mudança em relação ao v8: a taxa de administração do VGBL deixa de ser o
palpite de 1% a.a. e passa a 1,32% a.a., média oficial das entidades abertas de
previdência complementar (Relatório Gerencial de Previdência Complementar,
4º trimestre de 2025, tabela 7.1, Total Geral), estável entre 1,27% e 1,37%
desde 2016.

Consequência: o custo esperado do VGBL nos cenários B e F DEIXA DE SER NEGATIVO.
O resultado anterior era artefato do palpite — o limiar de custo zero fica em
1,08% (B) e 1,21% (F), logo acima do 1% adotado até aqui.

A grade de sensibilidade e os limiares mostram que a conclusão qualitativa
sobrevive: o VGBL só perde para o inventário direto acima de 2,2% a.a. e só
deixa a fronteira acima de 3% a.a., faixa em que vive menos de 1% do mercado.

Uso: python3 rodar_v9.py
"""
import csv
import motor

R_BASE, REGIME_BASE = 0.06, "2026"
CEN_VGBL = ("B", "F")

# Grade ancorada em fonte:
#   0,50%  piso do mercado competitivo (44% dos fundos entre 0,5% e 1,0%)
#   1,00%  mediana aproximada; RF não indexados no RGPC = 1,00%
#   1,32%  BASE — média oficial do segmento aberto (RGPC 4T2025, tab. 7.1)
#   1,75%  média amostral de Soares e Campani (2020)
#   2,00%  teto do varejo; Ações Ativo no RGPC = 2,00%
GRADE = (0.005, 0.010, 0.0132, 0.0175, 0.020)
BASE = 0.0132


def _av(cen, tx):
    return motor.avaliar(cen, r=R_BASE, regime=REGIME_BASE,
                         ir_contrafactual=True, taxa_adm_vgbl=tx)


def limiar(cen, alvo, lo=0.0, hi=0.10, iters=45):
    """Bissecção na taxa de administração até o cruzamento de `alvo`."""
    for _ in range(iters):
        mid = (lo + hi) / 2
        if alvo(_av(cen, mid)) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def limiar_fronteira(cen, passo=0.0005, teto=0.10):
    """Menor taxa em que o VGBL deixa a fronteira de eficiência."""
    tx = 0.0
    while tx <= teto:
        if "vgbl" not in motor.pareto(_av(cen, tx)):
            return tx
        tx += passo
    return None


def varredura():
    """Mesmas varreduras do v8, reexecutadas com a taxa oficial do VGBL."""
    SPREAD_SEM_CREDITO = 1.00
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

    with open("resultados/v9_sensibilidade.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["eixo", "valor", "cenario", "estrategia",
                    "vp_esperado", "cte95", "na_fronteira"])
        w.writerows(linhas)
    print("gravado resultados/v9_sensibilidade.csv", len(linhas), "linhas")


def grade():
    linhas = []
    for cen in CEN_VGBL:
        for tx in GRADE:
            r = _av(cen, tx)
            fr = motor.pareto(r)
            v, inv = r["vgbl"], r["baseline_venda"]
            linhas.append([cen, round(tx, 4), round(v["E"], 2),
                           round(v["CTE95"], 2), round(inv["E"], 2),
                           int("vgbl" in fr), ", ".join(fr)])
    with open("resultados/v9_taxa_vgbl.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "taxa_adm", "vgbl_e", "vgbl_cte",
                    "inventario_e", "vgbl_na_fronteira", "fronteira"])
        w.writerows(linhas)
    print("gravado resultados/v9_taxa_vgbl.csv", len(linhas), "linhas")


def limiares():
    linhas = []
    for cen in CEN_VGBL:
        inv = _av(cen, BASE)["baseline_venda"]["E"]
        zero = limiar(cen, lambda r: r["vgbl"]["E"])
        supera = limiar(cen, lambda r, b=inv: r["vgbl"]["E"] - b)
        sai = limiar_fronteira(cen)
        linhas.append([cen, round(zero, 5), round(supera, 5),
                       round(sai, 5) if sai else "", round(inv, 2)])
        print(f"  {cen}: custo zero em {zero*100:.2f}%, supera o inventário em "
              f"{supera*100:.2f}%, sai da fronteira em "
              f"{sai*100:.1f}%" if sai else f"  {cen}: não sai da fronteira")
    with open("resultados/v9_limiares_vgbl.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "taxa_custo_zero", "taxa_supera_inventario",
                    "taxa_sai_fronteira", "inventario_e"])
        w.writerows(linhas)
    print("gravado resultados/v9_limiares_vgbl.csv")


def principal():
    """Reexecuta a base com a taxa oficial, mantendo a grade de caducidade."""
    for regime in ("2026", "pos2027"):
        for lp in (0.0, 0.02, 0.05, 0.10, 0.20):
            res = motor.rodar(regime=regime, lapso_aa=lp, ir_contrafactual=True)
            arq = f"resultados/v9_{regime}_r6ir_lapso{int(lp*100)}.csv"
            motor.salvar_csv(res, arq)
            print("gravado", arq)


if __name__ == "__main__":
    principal()
    varredura()
    grade()
    limiares()
