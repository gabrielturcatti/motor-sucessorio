"""Tabelas 14 e 15 (v12): matriz de preços de equilíbrio e prêmio puro.

Lê resultados/v12_matriz_precos.csv (rodar_v12_matriz.py) e grava T14/T15 em
tabelas/ (.csv para conferência e .xml pronto para o documento).
"""
import os
import pandas as pd
import gerar_tabelas as G

M = pd.read_csv(os.path.join(G.RES, "v12_matriz_precos.csv"), dtype={"cenario": str})
PROD = {"WL10": "vitalício 10 pag.", "WL20": "vitalício 20 pag.",
        "TP10": "temporário 10 anos", "TP20": "temporário 20 anos"}


def pct(k):
    if pd.isna(k) or k == "":
        return "nunca"
    k = float(k)
    if k <= 0:
        return "nunca"
    return f"{k * 100:.0f}%"


def linha(cen, prod):
    a = M[(M.regime == "2026") & (M.cenario == cen) & (M.produto == prod)].iloc[0]
    b = M[(M.regime == "pos2027") & (M.cenario == cen) & (M.produto == prod)].iloc[0]
    if pd.isna(a.razao_E_k1):
        return None
    return [f"{cen} · {PROD[prod]}", G.br(a.razao_E_k1, 2),
            pct(a.k_fronteira), pct(b.k_fronteira), pct(a.k_inventario),
            pct(a.k_minimo), pct(b.k_minimo)]


def t14():
    linhas = []
    for cen in ("A", "B", "C", "D", "E", "F"):
        for prod in ("WL10", "WL20", "TP10", "TP20"):
            l = linha(cen, prod)
            if l:
                linhas.append(l)
    return G.gravar(
        "T14",
        "Tabela 14 – Matriz de preços de equilíbrio: prêmio máximo, em proporção do "
        "prêmio de tabela, em que o seguro atinge cada limiar, por cenário e produto",
        ["Cenário · produto", "Razão E (tabela)", "Fronteira 2026",
         "Fronteira pós-2027", "Iguala o inventário", "Menor custo 2026",
         "Menor custo pós-2027"],
        linhas, [2350, 1050, 1050, 1100, 1100, 1050, 1100],
        "Fonte: elaboração própria (2026). Taxa real bruta de 6% a.a., sem abandono da "
        "apólice, titular de 50 anos (70 anos e classe C no cenário E, em que só o "
        "vitalício de 10 pagamentos é oferecido). Cada célula é o maior prêmio, em "
        "proporção do prêmio de tabela (100%), com o qual o seguro: integra a fronteira "
        "de eficiência (Fronteira); tem custo esperado igual ou inferior ao do "
        "inventário direto (Iguala o inventário, limiar que não depende do regime); tem "
        "o menor custo esperado entre todas as estratégias do cenário (Menor custo). "
        "“Nunca” indica que o limiar não é atingido nem com prêmio zero. A razão E é a "
        "razão entre o custo esperado do seguro e o do inventário direto com o prêmio "
        "de tabela, no regime 2026.")


def t15():
    linhas = []
    casos = [("A", "WL10", "Vitalício 10 pagamentos, 50 anos"),
             ("A", "WL20", "Vitalício 20 pagamentos, 50 anos"),
             ("A", "TP10", "Temporário 10 anos, 50 anos"),
             ("A", "TP20", "Temporário 20 anos, 50 anos"),
             ("E", "WL10", "Vitalício 10 pagamentos, 70 anos, classe C")]
    for cen, prod, rot in casos:
        r = M[(M.regime == "2026") & (M.cenario == cen) & (M.produto == prod)].iloc[0]
        cA = M[(M.regime == "2026") & (M.cenario == "A") & (M.produto == prod)]
        cC = M[(M.regime == "2026") & (M.cenario == "C") & (M.produto == prod)]
        folga_ext = r.k_inventario / r.k_puro_liq - 1
        linhas.append([rot, pct(r.k_puro_liq), pct(r.k_puro_6),
                       G.br((1 / r.k_puro_liq - 1) * 100, 0) + "%",
                       G.br(folga_ext * 100, 1) + "%"])
    return G.gravar(
        "T15",
        "Tabela 15 – Prêmio puro em proporção do prêmio de tabela e margem máxima "
        "compatível com custo esperado igual ao do inventário",
        ["Produto", "Prêmio puro (taxa da família)", "Prêmio puro (6% a.a.)",
         "Diferença da tabela sobre o puro", "Margem máxima sobre o puro"],
        linhas, [3350, 1250, 1150, 1350, 1200],
        "Fonte: elaboração própria (2026). Prêmio puro é o prêmio que iguala o valor "
        "presente atuarial dos pagamentos ao do capital segurado, sem carregamento, com "
        "a tábua BR-EMS mt 2026 e a mesma mecânica de pagamento do modelo (mensal, "
        "enquanto vivo, até a quitação). A taxa da família é a taxa real líquida de "
        "imposto de renda que desconta todos os fluxos do modelo (4,5% a.a.). A margem "
        "máxima é a margem sobre o prêmio puro com a qual o custo esperado do seguro "
        "iguala o do inventário direto em inventário extrajudicial; em inventário "
        "judicial (cenário C), ela é de 10,1%. No vitalício agravado, o prêmio puro "
        "usa a mortalidade padrão da tábua, como todo o modelo, e por isso subestima o "
        "prêmio justo de um titular agravado.")


if __name__ == "__main__":
    print(t14())
    print(t15())
    print(open(os.path.join(G.TAB, "T14.csv")).read())
    print(open(os.path.join(G.TAB, "T15.csv")).read())
