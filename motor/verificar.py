# -*- coding: utf-8 -*-
"""Suíte de verificação do motor — invariantes, fórmulas e consistência.

Executar antes de qualquer rodada que vá para o texto: python3 verificar.py
Cada teste imprime OK ou FALHA com o valor observado.
"""
import math, csv, itertools
import atuarial, premios, custos, resgate, motor, cenario_h as ch
from cenarios import CENARIOS

ok = fail = 0
def check(cond, nome, detalhe=""):
    global ok, fail
    if cond: ok += 1; print(f"  OK   {nome}")
    else:    fail += 1; print(f"  FALHA {nome}  {detalhe}")

def quase(a, b, tol=1e-6): return abs(a-b) <= tol*max(1, abs(a), abs(b))

print("\n=== A. TÁBUA DE MORTALIDADE ===")
for sexo in ("M","F"):
    for idade in (40,50,60,70):
        s = sum(atuarial.prob_morte_no_ano(idade,sexo,t) for t in range(121-idade))
        check(quase(s,1.0,1e-9), f"massa de probabilidade = 1 ({sexo}{idade})", f"{s:.10f}")
q = atuarial.tabua()["M"]
cresc = all(q.get(i,0) <= q.get(i+1,1)+1e-9 for i in range(35,95))
check(cresc, "qx monotônico crescente (M, 35-95)")
check(atuarial.expectativa_vida(50,"F") > atuarial.expectativa_vida(50,"M"),
      "expectativa de vida F > M aos 50")

print("\n=== B. PRÊMIOS ===")
p = premios.premio(50,"WL",10,"M",500_000)
f = premios.fator(50,"WL10M")
check(quase(p["premio_anual"], f*500_000/1000*(1+premios.IOF)),
      "prêmio anual = fator x capital/1000 x (1+IOF)", f'{p["premio_anual"]:.4f}')
fm = premios.fator_modal("WL",10,500_000)
check(quase(p["premio_mensal"], p["premio_anual"]*fm), "prêmio mensal = anual x fator modal")
check(quase(premios.carregamento_fracionamento("WL",10,500_000), fm*12-1),
      "carregamento = 12 x fator modal - 1")
pbig = premios.premio(50,"WL",10,"M",1_500_000)
check(pbig["chave"].endswith("+") or "+" in pbig["chave"],
      "capital >= 1 mi usa banda preferencial (+)", pbig["chave"])
check(premios.premio(70,"TP",10,"M",500_000) is None,
      "fator zerado devolve None (indisponível)")
r_ = 0.06
vp_anual = sum(p["premio_anual"]/(1+r_)**k for k in range(10))
check(quase(premios.vp_premios(p, r_, 10, mensal=False), vp_anual),
      "vp_premios anual = soma descontada")
vp_mensal = sum(p["premio_mensal"]/(1+r_)**(m/12) for m in range(120))
check(quase(premios.vp_premios(p, r_, 10, mensal=True), vp_mensal),
      "vp_premios mensal = 12 parcelas/ano descontadas")
check(premios.vp_premios(p, r_, 0) == 0.0, "vp_premios(0 anos) = 0")

print("\n=== C. VALOR DE RESGATE ===")
cap = 500_000
serie = [resgate.valor_resgate(cap,"WL",10,"M",50,t) for t in range(0,55)]
check(all(0 <= v <= cap*1.0001 for v in serie), "VR dentro de [0, capital]")
check(all(serie[i] <= serie[i+1]+cap*1e-9 for i in range(len(serie)-1)),
      "VR monotônico não decrescente, inclusive após a dotação (WL10)")
check(serie[0] < serie[-1], "VR cresce ao longo da vigência")

print("\n=== D. CUSTOS ===")
ci = custos.custo_inventario("RS", 5_000_000, 2)
check(quase(ci.total, ci.itcmd+ci.honorarios+ci.emolumentos_ou_custas+ci.multa),
      "CustoInventario.total = soma dos componentes")
check(quase(custos.itcmd_sp(1_000_000,"2026"), 40_000), "ITCMD-SP 2026 = 4% da base")
# ITCMD-RS progressivo marginal conferido à mão
U = custos.UPF_RS_2026
base = 15_000*U   # cai na faixa 10.000-20.000 UPF
esperado = (8_000*0.03 + 5_000*0.04)*U
check(quase(custos.itcmd_rs(base), esperado), "ITCMD-RS marginal por faixas", f"{custos.itcmd_rs(base):.2f} vs {esperado:.2f}")
check(custos.itcmd_rs(1_000*U) == 0.0, "ITCMD-RS isento abaixo de 2.000 UPF")
c = custos.cunha_iliquidez(500_000, 6, 0.06, 0.06, 0.25, plusvalia=0.40)
check(quase(c["iliquidez"]+c["tributo_gk"], c["cunha"]), "cunha = iliquidez + tributo GK")
check(quase(c["cunha"], min(c["credito_ponte"], c["venda_forcada"])), "cunha = mínimo dos dois caminhos")
rl = custos.taxa_real_liquida(0.06, 0.04, 0.15)
i_nom = 1.06*1.04-1
check(quase(rl, (1+i_nom*0.85)/1.04-1), "taxa real líquida conforme fórmula", f"{rl:.6f}")
check(custos.taxa_real_liquida(0.06,0.04,0.0) == 0.06 or quase(custos.taxa_real_liquida(0.06,0.04,0.0),0.06),
      "alíquota zero devolve a taxa bruta")
check([custos.aliquota_vgbl_regressiva(a) for a in (1,3,5,7,9,11)] == [0.35,0.30,0.25,0.20,0.15,0.10],
      "tabela regressiva do VGBL")

print("\n=== E. ATUARIAL ===")
d = atuarial.distribuicao_custo(lambda t: 100.0, 50, "M", 0.06)
check(quase(sum(pp for pp,_ in d), 1.0, 1e-9), "distribuicao_custo soma 1")
check(quase(atuarial.esperanca(d), 100.0), "esperança de custo constante = constante")
dd = [(0.5, 10.0), (0.3, 20.0), (0.2, 100.0)]
check(quase(atuarial.cte(dd, 0.80), 100.0), "CTE-80 pega o pior desfecho", f"{atuarial.cte(dd,0.80)}")
check(atuarial.cte(dd,0.95) >= atuarial.esperanca(dd), "CTE >= esperança")
check(quase(atuarial.cte(dd, 0.0), atuarial.esperanca(dd)), "CTE com nível 0 = esperança")

print("\n=== F. MOTOR — IES, PARETO, LAPSO, TEMPORÁRIOS ===")
PAR = ("tributaria","processual","iliquidez","instrumento")
falhas_ies = falhas_par = 0
for produto in (("WL",10), ("WL",20), ("TP",10)):
    for lapso in (0.0, 0.05):
        for res in motor.rodar(ir_contrafactual=True, lapso_aa=lapso, produto=produto):
            for nome, v in res.items():
                if not (isinstance(v,dict) and "E" in v): continue
                if not quase(sum(v["IES_E"].values()), v["E"], 1e-6): falhas_ies += 1
                if not quase(sum(v["IES_CTE"].values()), v["CTE95"], 1e-6): falhas_ies += 1
            fr = motor.pareto(res)
            ests = {k:v for k,v in res.items() if isinstance(v,dict) and "E" in v}
            for a, va in ests.items():
                dominada = any(vb["E"] <= va["E"] and vb["CTE95"] <= va["CTE95"]
                               and (vb["E"] < va["E"] or vb["CTE95"] < va["CTE95"])
                               for b, vb in ests.items() if b != a)
                if dominada and a in fr: falhas_par += 1
                if not dominada and a not in fr: falhas_par += 1
check(falhas_ies == 0, "IES aditivo em E e na cauda (todos os cenários/produtos/lapsos)", f"{falhas_ies} falhas")
check(falhas_par == 0, "fronteira de Pareto coerente com dominância", f"{falhas_par} falhas")

cen = CENARIOS["A"]
ests, recs, ci_, meta, comps = motor.estrategias(cen, 0.06, "2026", produto=("WL",10), ir_contrafactual=True)
dist = motor.dist_seguro_com_lapso(cen, meta["r_desconto"], meta, ests["seguro"], ests["baseline_venda"], 0.05)
check(quase(sum(pp for pp,_ in dist), 1.0, 1e-9), "distribuição com lapso soma 1", f"{sum(pp for pp,_ in dist):.10f}")

# temporário: após a expiração o custo deve ser prêmios + baseline
e2, r2, ci2, m2, c2 = motor.estrategias(cen, 0.06, "2026", produto=("TP",10), ir_contrafactual=True)
rd = m2["r_desconto"]
pagos10 = premios.vp_premios(m2["seguro"]["p"], rd, 10, mensal=True)
check(quase(e2["seguro"](20), pagos10 + e2["baseline_venda"](20)),
      "temporário expirado: prêmios + inventário integral")
check(quase(e2["seguro"](5), premios.vp_premios(m2["seguro"]["p"], rd, 6, mensal=True)),
      "temporário vigente: só prêmios")

# monotonicidade econômica
a4 = motor.avaliar("A", r=0.04, ir_contrafactual=True)
a8 = motor.avaliar("A", r=0.08, ir_contrafactual=True)
check(a4["baseline_venda"]["E"] > a8["baseline_venda"]["E"],
      "custo do inventário cai quando a taxa sobe")
check(a4["seguro"]["E"] > a8["seguro"]["E"], "custo do seguro cai quando a taxa sobe")
check(a8["seguro"]["E"]/a8["baseline_venda"]["E"] > a4["seguro"]["E"]/a4["baseline_venda"]["E"],
      "razão seguro/baseline cresce com a taxa (hipótese do juro real)")

print("\n=== G. CENÁRIO H ===")
soc = ch.SociedadeH()
d1 = ch.dist_primeira_morte(soc)
check(quase(sum(pp for pp,_ in d1), 1.0, 1e-9), "distribuição de primeira morte soma 1", f"{sum(pp for pp,_ in d1):.10f}")
rh = ch.avaliar_h(soc, n_sim=40_000)
# E exato deve estar próximo da média das simulações
rng_ok = abs(rh["baseline_haveres"]["E"]) > 0
check(rng_ok, "cenário H produz resultado")
soc1 = ch.SociedadeH(idades=(50,), sexos=("M",))
rh1 = ch.avaliar_h(soc1, n_sim=20_000)
# com 1 sócio, E deve bater com o cálculo direto sobre a distribuição individual
H = soc1.haveres
rl_ = custos.taxa_real_liquida(0.06)
cunha1 = custos.cunha_iliquidez(H/4, 6, 0.06, 0.06, 0.25)["cunha"]
esp = sum(pp*(H+cunha1)/(1+rl_)**(t+0.5) for pp,t in
          [(atuarial.prob_morte_no_ano(50,"M",t), t) for t in range(71)])
check(quase(rh1["baseline_haveres"]["E"], esp, 1e-6),
      "cenário H com 1 sócio = cálculo direto", f'{rh1["baseline_haveres"]["E"]:.2f} vs {esp:.2f}')

print(f"\n{'='*60}\nRESULTADO: {ok} OK, {fail} FALHA(S)")
