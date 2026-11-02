"""Figuras 1 a 3 redesenhadas (v24).

Figura 1: fronteiras de eficiência em pequenos múltiplos com escala comum. Cada
  cenário é normalizado pelo custo esperado do inventário direto (= 1), o que
  preserva a geometria de cada painel e torna os seis comparáveis entre si.
  Pontos fora da escala comum são indicados na borda com seta e coordenadas.
Figura 2: decomposição do Índice de Eficiência Sucessória no cenário A, em
  barras horizontais empilhadas, com total rotulado e o preço do instrumento em
  cinza com hachura, para separá-lo visualmente das três fricções.
Figura 3: árvore de decisão (Graphviz), com as folhas em que o seguro integra a
  fronteira destacadas.

Paleta categórica validada (dataviz/validate_palette.js): laranja #eb6834,
azul #2a78d6 e água #1baf7a passam em todos os pares (ΔE CVD 9,2; visão normal
24,0); o cinza do preço do instrumento é neutro proposital, com hachura.
Tipografia: Liberation Serif, métrica do Times New Roman do corpo do texto.
Largura de 6,0 polegadas = largura de inserção no documento (15,2 cm), de modo
que os tamanhos de fonte são os tamanhos impressos.
"""
import os, subprocess
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import pandas as pd
import gerar_tabelas as G

for f in font_manager.findSystemFonts():
    if "LiberationSerif" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({
    "font.family": "Liberation Serif", "font.size": 9.5,
    "axes.edgecolor": "#8a8984", "axes.linewidth": 0.6,
    "xtick.color": "#3d3c39", "ytick.color": "#3d3c39",
    "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "axes.labelcolor": "#1d1d1b", "text.color": "#1d1d1b",
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.04,
})
AZUL, LARANJA, AGUA, CINZA = "#2a78d6", "#eb6834", "#1baf7a", "#cfcdc6"
TINTA, MUDO, GRADE = "#1d1d1b", "#8a8984", "#e6e5e1"

D = G.ler(G.BASE)
ROT = {"baseline_venda": "Inventário", "baseline_reserva": "Reserva prévia",
       "seguro": "Seguro", "holding": "Holding", "doacao": "Doação", "vgbl": "VGBL"}
TIT = {"A": "A · Patrimônio médio, sem VGBL",
       "B": "B · Holding prévia, com VGBL",
       "C": "C · Grande patrimônio, conflito",
       "D": "D · Grande patrimônio, sócio externo",
       "E": "E · Idade avançada e agravo",
       "F": "F · Patrimônio pequeno, com VGBL"}


def br(v, casas=2):
    return f"{v:.{casas}f}".replace(".", ",")


# posições fixadas onde a busca automática produz leitura ambígua
FIXO = {("B", "baseline_venda"): (-6, 0, "right", "center"), ("B", "doacao"): (6, 3, "left", "bottom"),
        ("B", "holding"): (-6, 0, "right", "center")}


def _sobrepoe(a, b, folga=1.5):
    return not (a.x1 + folga < b.x0 or b.x1 + folga < a.x0 or
                a.y1 + folga < b.y0 or b.y1 + folga < a.y0)


def figura1():
    XMAX, YMAX = 2.3, 3.5
    fig, axes = plt.subplots(3, 2, figsize=(6.0, 7.9), sharex=True, sharey=True)
    for ax, cen in zip(axes.ravel(), "ABCDEF"):
        sub = D[D.cenario == cen].copy()
        base = sub[sub.estrategia == "baseline_venda"].vp_esperado.iloc[0]
        sub["x"] = sub.vp_esperado / base
        sub["y"] = sub.cte95 / base
        ax.set_xlim(0, XMAX); ax.set_ylim(0, YMAX)
        ax.grid(color=GRADE, lw=0.5); ax.set_axisbelow(True)
        ax.axvline(1, color=MUDO, lw=0.7, ls=(0, (3, 2)), zorder=1)
        fr = sub[sub.pareto_2d == 1].sort_values("x")
        ax.plot(fr.x.clip(upper=XMAX), fr.y.clip(upper=YMAX), color=TINTA, lw=1.0, zorder=2)
        fig.canvas.draw()
        rend = fig.canvas.get_renderer()
        caixas = []
        # pontos primeiro (para os rótulos evitarem os marcadores)
        for _, r in sub.iterrows():
            fora = r.x > XMAX or r.y > YMAX
            if fora:
                continue
            seg = r.estrategia == "seguro"
            na = r.pareto_2d == 1
            cor = AZUL if seg else TINTA
            ax.scatter(r.x, r.y, s=34 if na else 30, zorder=4,
                       facecolor=cor if na else "white",
                       edgecolor=cor if (na or seg) else MUDO, linewidth=1.1)
            px, py = ax.transData.transform((r.x, r.y))
            caixas.append(matplotlib.transforms.Bbox([[px - 4, py - 4], [px + 4, py + 4]]))
        for _, r in sub[(sub.x > XMAX) | (sub.y > YMAX)].iterrows():
            ax.annotate("", xy=(XMAX - 0.02, YMAX - 0.03), xytext=(XMAX - 0.2, YMAX - 0.33),
                        arrowprops=dict(arrowstyle="-|>", color=MUDO, lw=0.8, mutation_scale=7))
            t = ax.text(0.98, 0.03, f"{ROT[r.estrategia]} fora da escala: ({br(r.x)}; {br(r.y)})",
                        transform=ax.transAxes, ha="right", va="bottom", fontsize=7.6,
                        color="#5f5d58", style="italic")
            caixas.append(t.get_window_extent(rend))
            px, py = ax.transData.transform((XMAX - 0.1, YMAX - 0.18))
            caixas.append(matplotlib.transforms.Bbox([[px - 14, py - 14], [px + 14, py + 14]]))
        ordem = sub.sort_values("y", ascending=False)
        for _, r in ordem.iterrows():
            seg = r.estrategia == "seguro"
            cor = AZUL if seg else (TINTA if r.pareto_2d == 1 else "#5f5d58")
            peso = "bold" if seg else "normal"
            if r.x > XMAX or r.y > YMAX:
                continue
            fixo = FIXO.get((cen, r.estrategia))
            if fixo:
                t = ax.annotate(ROT[r.estrategia], (r.x, r.y), xytext=fixo[:2],
                                textcoords="offset points", ha=fixo[2], va=fixo[3],
                                fontsize=8.2, color=cor, fontweight=peso, zorder=5)
                caixas.append(t.get_window_extent(rend))
                continue
            for dx, dy, ha, va in ((6, 3, "left", "bottom"), (6, -3, "left", "top"),
                                   (-6, 3, "right", "bottom"), (-6, -3, "right", "top"),
                                   (0, 7, "center", "bottom"), (0, -7, "center", "top"),
                                   (10, 10, "left", "bottom"), (-10, -10, "right", "top"),
                                   (12, -12, "left", "top"), (-12, 12, "right", "bottom")):
                t = ax.annotate(ROT[r.estrategia], (r.x, r.y), xytext=(dx, dy),
                                textcoords="offset points", ha=ha, va=va, fontsize=8.2,
                                color=cor, fontweight=peso, zorder=5)
                bb = t.get_window_extent(rend)
                axbb = ax.get_window_extent(rend)
                dentro = (bb.x0 >= axbb.x0 + 1 and bb.x1 <= axbb.x1 - 1 and
                          bb.y0 >= axbb.y0 + 1 and bb.y1 <= axbb.y1 - 1)
                if dentro and not any(_sobrepoe(bb, c) for c in caixas):
                    caixas.append(bb); break
                t.remove()
            else:
                t = ax.annotate(ROT[r.estrategia], (r.x, r.y), xytext=(6, 3),
                                textcoords="offset points", fontsize=8.2, color=cor,
                                fontweight=peso, zorder=5)
                caixas.append(t.get_window_extent(rend))
        ax.set_title(TIT[cen], fontsize=9.5, loc="left", pad=4, color=TINTA)
        ax.tick_params(labelsize=8.2)
        ax.xaxis.set_major_formatter(lambda v, _: br(v, 1) if v % 1 else f"{v:.0f}")
        ax.yaxis.set_major_formatter(lambda v, _: br(v, 1) if v % 1 else f"{v:.0f}")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.supxlabel("Custo esperado (custo esperado do inventário direto = 1)", fontsize=9.5, y=0.03)
    fig.supylabel("Custo nos 5% piores desfechos (mesma escala)", fontsize=9.5, x=0.015)
    leg = [Line2D([], [], marker="o", ls="-", color=TINTA, mfc=TINTA, ms=5, lw=1.0,
                  label="Na fronteira de eficiência"),
           Line2D([], [], marker="o", ls="", mec=MUDO, mfc="white", ms=5, label="Dominada"),
           Line2D([], [], marker="o", ls="", mec=AZUL, mfc=AZUL, ms=5, label="Seguro de vida")]
    fig.legend(handles=leg, loc="upper center", ncol=3, frameon=False, fontsize=8.6,
               bbox_to_anchor=(0.5, 1.0), handletextpad=0.4, columnspacing=1.6)
    fig.tight_layout(rect=(0.02, 0.035, 1, 0.97), h_pad=1.2, w_pad=1.0)
    fig.savefig(os.path.join(G.FIG, "F1_fronteiras.png"))
    plt.close(fig)


def figura2():
    """Decomposição do IES nos seis cenários, em pequenos múltiplos com escala
    comum: custo de cada estratégia em relação ao custo esperado do inventário
    direto do próprio cenário (= 100)."""
    ordem = ["baseline_venda", "baseline_reserva", "seguro", "holding", "doacao", "vgbl"]
    nomes = {"baseline_venda": "Inventário direto", "baseline_reserva": "Inventário c/ reserva",
             "seguro": "Seguro de vida", "holding": "Holding familiar",
             "doacao": "Doação em vida", "vgbl": "VGBL"}
    parc = [("ies_e_tributaria", "Fricção tributária", LARANJA, None),
            ("ies_e_processual", "Fricção processual", AZUL, None),
            ("ies_e_iliquidez", "Fricção de liquidez", AGUA, None),
            ("ies_e_instrumento", "Preço do instrumento", CINZA, "////")]
    plt.rcParams["hatch.color"] = "#8f8d87"
    plt.rcParams["hatch.linewidth"] = 0.6
    XMIN, XMAX = -185, 340
    fig, axes = plt.subplots(3, 2, figsize=(6.0, 7.6), sharex=True, sharey=True)
    ys = list(range(len(ordem)))[::-1]
    for ax, cen in zip(axes.ravel(), "ABCDEF"):
        sub = D[D.cenario == cen].set_index("estrategia")
        base = sub.loc["baseline_venda", "vp_esperado"] / 100
        ax.set_xlim(XMIN, XMAX)
        ax.grid(axis="x", color=GRADE, lw=0.5); ax.set_axisbelow(True)
        ax.axvline(0, color="#8a8984", lw=0.6, zorder=1)
        ax.axvline(100, color=MUDO, lw=0.7, ls=(0, (3, 2)), zorder=1)
        for y, e in zip(ys, ordem):
            if e not in sub.index:
                ax.text(4, y, "não se aplica", va="center", fontsize=7.2, color="#9a9893",
                        style="italic")
                continue
            pos, neg = 0.0, 0.0
            for col, lab, cor, hach in parc:
                v = sub.loc[e, col] / base
                if abs(v) < 1e-9:
                    continue
                if v < 0:
                    ax.barh(y, v, left=neg, height=0.66, color=cor, edgecolor="white",
                            linewidth=0.8, hatch=hach, zorder=3)
                    neg += v
                    continue
                larg = min(v, XMAX - pos) if pos < XMAX else 0
                ax.barh(y, larg, left=pos, height=0.66, color=cor, edgecolor="white",
                        linewidth=0.8, hatch=hach, zorder=3)
                pos += v
            total = sub.loc[e, "vp_esperado"] / base
            if pos > XMAX:
                ax.text(XMAX - 4, y, f"{G.br(total)} →", va="center", ha="right",
                        fontsize=7.8, color=TINTA, zorder=5,
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
                continue
            if neg < 0:
                ax.plot([total, total], [y - 0.42, y + 0.42], color=TINTA, lw=1.3, zorder=5)
            ax.text(pos + 6, y, G.br(total), va="center", fontsize=7.8, color=TINTA)
        ax.set_title(TIT[cen], fontsize=9.3, loc="left", pad=3, color=TINTA)
        ax.set_yticks(ys, [nomes[e] for e in ordem], fontsize=8.2)
        ax.tick_params(axis="y", length=0)
        ax.tick_params(axis="x", labelsize=8)
        for s_ in ("top", "right", "left"):
            ax.spines[s_].set_visible(False)
    hand = [Patch(facecolor=c, edgecolor="white", hatch=h, label=l) for _, l, c, h in parc]
    fig.legend(handles=hand, loc="upper center", ncol=4, frameon=False, fontsize=8.4,
               bbox_to_anchor=(0.55, 1.0), handlelength=1.3, columnspacing=1.1)
    fig.supxlabel("Custo esperado (custo esperado do inventário direto = 100)", fontsize=9.3,
                  x=0.6, y=0.035)
    fig.tight_layout(rect=(0, 0.04, 1, 0.965), h_pad=1.0, w_pad=0.8)
    fig.savefig(os.path.join(G.FIG, "F2_ies.png"))
    plt.close(fig)


def figura3():
    q = 'shape=box, style="rounded", color="#5f5d58", fillcolor="white"'
    folha = 'shape=box, style="rounded,filled", color="#b9b7b0", fillcolor="#f3f2ef"'
    seg = 'shape=box, style="rounded,filled", color="#2a78d6", penwidth=1.6, fillcolor="#e8f1fb"'
    dot = f"""digraph G {{
  graph [rankdir=TB, nodesep=0.30, ranksep=0.26, fontname="Liberation Serif", dpi=300,
         newrank=true, pad=0.05];
  node  [fontname="Liberation Serif", fontsize=11, penwidth=0.9, margin="0.14,0.07",
         width=2.35, fontcolor="#1d1d1b"];
  edge  [fontname="Liberation Serif", fontsize=10, arrowsize=0.55, penwidth=0.8,
         color="#5f5d58", fontcolor="#3d3c39"];
  q1 [{q}, label="O titular tem\\nmotivo de legado?"];
  g  [{folha}, label=<<B>Caso-limite G</B><BR/>Instrumento racional: renda vitalícia.<BR/>Seguro sem função sucessória.>];
  q2 [{q}, label="Quem suporta a obrigação\\nno óbito?"];
  h  [{seg}, label=<<B>Cenário H · haveres</B><BR/>Na fronteira: pagamento direto<BR/>e <B>seguro temporário</B>.<BR/>Vitalício dominado, salvo sem<BR/>parcelamento e sem crédito.>];
  q3 [{q}, label="O VGBL é aplicável\\nao perfil?"];
  bf [{folha}, label=<<B>Cenários B e F</B><BR/>VGBL domina (taxa de<BR/>administração até 2,9% a.a.).>];
  q4 [{q}, label="O titular é contratável\\nem condição padrão?"];
  e  [{folha}, label=<<B>Cenário E · idade e agravo</B><BR/>Na fronteira: holding e doação.<BR/>Seguro fora em todas as classes.>];
  q5 [{q}, label="Patrimônio empresarial\\nde grande porte?"];
  cd [{folha}, label=<<B>Cenários C e D</B><BR/>Na fronteira: holding (regime 2026).<BR/>Seguro entra em C sem crédito-ponte<BR/>ou no regime pós-2027.>];
  a  [{seg}, label=<<B>Cenário A</B><BR/>Na fronteira: inventário,<BR/><B>seguro</B> e doação. Escolha pela<BR/>aversão ao risco de cauda.>];
  ca [shape=note, style="filled", fillcolor="white", color="#b9b7b0", fontsize=10, width=1.7,
      label="Condição para o seguro:\\npersistência do contrato\\n(sai da fronteira com\\nabandono de 2% a.a.)"];
  {{rank=same; q1; g;}}  {{rank=same; q2; h;}}  {{rank=same; q3; bf;}}
  {{rank=same; q4; e;}}  {{rank=same; q5; cd;}} {{rank=same; a; ca;}}
  q1 -> g  [label="  Não  "];
  q1 -> q2 [label="  Sim"];
  q2 -> h  [label="  Sociedade  "];
  q2 -> q3 [label="  Família"];
  q3 -> bf [label="  Sim  "];
  q3 -> q4 [label="  Não"];
  q4 -> e  [label="  Não  "];
  q4 -> q5 [label="  Sim"];
  q5 -> cd [label="  Sim  "];
  q5 -> a  [label="  Não"];
  a -> ca  [style=dashed, arrowhead=none, color="#b9b7b0"];
}}"""
    caminho = os.path.join(G.FIG, "F3_arvore.dot")
    open(caminho, "w", encoding="utf-8").write(dot)
    subprocess.run(["dot", "-Tpng", caminho, "-o", os.path.join(G.FIG, "F3_arvore.png")], check=True)


if __name__ == "__main__":
    figura1(); figura2(); figura3()
    print("ok")
