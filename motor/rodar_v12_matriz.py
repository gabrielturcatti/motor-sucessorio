"""Motor v12 (02/nov/2026) — matriz de preços de equilíbrio do seguro.

Para cada cenário × produto × regime, encontra o multiplicador k do prêmio de
tabela (k = 1,0 é a tabela; k = 0,7 é prêmio 30% menor) em três limiares:

  k_fronteira  maior k em que o seguro ainda integra a fronteira de eficiência
               (não é dominado por nenhuma estratégia em E e CTE-95);
  k_inventario k em que o custo esperado do seguro iguala o do inventário direto
               (abaixo dele o seguro domina o inventário, pois já é melhor na cauda);
  k_minimo     k em que o seguro passa a ter o menor custo esperado entre todas
               as estratégias do cenário.

E compara esses limiares com o prêmio puro: o multiplicador k_puro em que o
prêmio cobre exatamente o valor presente atuarial do benefício, sem
carregamento, calculado com a mesma tábua (BR-EMS mt 2026) e a mesma mecânica
de pagamento do motor (mensal, enquanto vivo, até a quitação), à taxa real de
mercado de 6% a.a. (rendimento bruto das reservas da seguradora) e à taxa
líquida da família.

O custo esperado do seguro é linear em k (prêmios entram somando), por isso
k_inventario e k_minimo têm forma fechada; a CTE-95 não é necessariamente
linear (o conjunto da cauda pode mudar), e k_fronteira é obtido por bisseção.
Caso base: taxa real bruta de 6%, IR no contrafactual, sem abandono.
"""
import csv
import atuarial
import motor
from cenarios import CENARIOS

R = 0.06
PRODUTOS = (("WL", 10), ("WL", 20), ("TP", 10), ("TP", 20))
CENS = ("A", "B", "C", "D", "E", "F")


def aval(cen, regime, prod, k):
    return motor.avaliar(cen, r=R, regime=regime, lapso_aa=0.0,
                         ir_contrafactual=True, produto=prod, carga_premio=k)


def na_fronteira(cen, regime, prod, k):
    res = aval(cen, regime, prod, k)
    return "seguro" in res and "seguro" in motor.pareto(res)


def k_fronteira(cen, regime, prod, teto=10.0):
    if na_fronteira(cen, regime, prod, teto):
        return float("inf")
    lo, hi = 0.0, teto
    if not na_fronteira(cen, regime, prod, lo):
        return None
    for _ in range(40):
        mid = (lo + hi) / 2
        if na_fronteira(cen, regime, prod, mid):
            lo = mid
        else:
            hi = mid
    return lo


def k_puro(cen, regime, prod, i):
    """Multiplicador em que o VP atuarial dos prêmios (à taxa i) iguala o VP
    atuarial do benefício (à mesma taxa). Usa o capital e o prêmio do motor."""
    c = CENARIOS[cen]
    ests, _, ci, meta, _ = motor.estrategias(c, R, regime, produto=prod,
                                             ir_contrafactual=True)
    if "seguro" not in meta:
        return None
    m = meta["seguro"]
    p, cap, max_anos = m["p"], m["capital"], m["max_anos"]
    fam, prz = prod
    vit = fam == "WL"
    import premios
    vp_ben, vp_prem = 0.0, 0.0
    for t in range(121 - c.idade):
        pm = atuarial.prob_morte_no_ano(c.idade, c.sexo, t)
        if pm <= 0:
            continue
        # prêmios pagos até o óbito (inclusive o ano do óbito) ou a quitação
        vp_prem += pm * premios.vp_premios(p, i, min(t + 1, max_anos), mensal=True)
        if vit or t < prz:
            vp_ben += pm * cap / (1 + i) ** (t + 0.5)
    return vp_ben / vp_prem


def main():
    linhas = []
    for regime in ("2026", "pos2027"):
        for cen in CENS:
            for prod in PRODUTOS:
                r1 = aval(cen, regime, prod, 1.0)
                if "seguro" not in r1:
                    linhas.append([regime, cen, f"{prod[0]}{prod[1]}"] + [""] * 9)
                    continue
                r0 = aval(cen, regime, prod, 0.0)
                e1, e0 = r1["seguro"]["E"], r0["seguro"]["E"]
                inv = r1["baseline_venda"]["E"]
                outros = min(v["E"] for n, v in r1.items()
                             if isinstance(v, dict) and n != "seguro")
                k_inv = (inv - e0) / (e1 - e0)
                k_min = (outros - e0) / (e1 - e0)
                kf = k_fronteira(cen, regime, prod)
                kp6 = k_puro(cen, regime, prod, R)
                kpl = k_puro(cen, regime, prod, r1.get("_r", None) or
                             motor.estrategias(CENARIOS[cen], R, regime, produto=prod,
                                               ir_contrafactual=True)[3]["r_desconto"])
                fr1 = int("seguro" in motor.pareto(r1))
                linhas.append([regime, cen, f"{prod[0]}{prod[1]}", fr1,
                               round(e1 / inv, 4), round(kf, 4) if kf is not None else "",
                               round(k_inv, 4), round(k_min, 4), round(kp6, 4),
                               round(kpl, 4), round(e1, 2), round(inv, 2)])
                print(linhas[-1])
    with open("resultados/v12_matriz_precos.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["regime", "cenario", "produto", "fronteira_k1", "razao_E_k1",
                    "k_fronteira", "k_inventario", "k_minimo", "k_puro_6",
                    "k_puro_liq", "E_seguro_k1", "E_inventario"])
        w.writerows(linhas)
    print("gravado resultados/v12_matriz_precos.csv")


if __name__ == "__main__":
    main()
