# -*- coding: utf-8 -*-
"""Gera as tabelas e figuras da dissertação a partir dos CSVs do motor.

Único ponto de verdade entre o motor e o texto: toda tabela da seção 6 e
toda figura saem daqui. Rodar após qualquer reexecução do motor.

Saídas:
  tabelas/T{n}.csv   — conteúdo já formatado (conferência humana)
  tabelas/T{n}.xml   — bloco <w:tbl> pronto para o documento
  tabelas/manifesto.json
  figuras/F1_fronteiras.png, figuras/F2_ies.png
"""
from __future__ import annotations
import json, os, re
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(AQUI, "resultados")

# Única fonte de verdade das tabelas: mudar a versão aqui propaga para todas.
VERSAO = "v9"
BASE = f"{VERSAO}_2026_r6ir_lapso0.csv"
POS = f"{VERSAO}_pos2027_r6ir_lapso0.csv"
SENS = f"{VERSAO}_sensibilidade.csv"
LAPSOS = (0, 2, 5, 10, 20)
GRID = "v7_grid_idade.csv"          # grade idade x produto (rodar_v7_h.py)
CEN_H = "v10_cenario_h.csv"         # v10: variante sem crédito corrigida
ESCADA = "v8_escada_agravo.csv"      # independe da taxa do VGBL
TAXA_VGBL = f"{VERSAO}_taxa_vgbl.csv"
LIMIARES = f"{VERSAO}_limiares_vgbl.csv"
CONTRAT = "v8_contratabilidade.csv"
SEM_CRED = "v10_sem_credito.csv"     # v10: crédito de fato inexistente (spread infinito)
HOLD = "v10_holding_doacao.csv"
HOLD_LIM = "v10_limiares_holding_doacao.csv"
COMPL = "v10_complementares.csv"
TAB = os.path.join(AQUI, "tabelas")
FIG = os.path.join(AQUI, "figuras")
os.makedirs(TAB, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

NOME = {
    "baseline_venda": "Inventário (crédito-ponte/venda)",
    "baseline_reserva": "Inventário (reserva prévia)",
    "seguro": "Seguro de vida",
    "holding": "Holding familiar",
    "doacao": "Doação em vida",
    "vgbl": "VGBL",
}

ORDEM = ("baseline_venda", "baseline_reserva", "seguro",
         "holding", "doacao", "vgbl")

# rótulo curto para figuras (o nome longo colide nos painéis)
CURTO = {
    "baseline_venda": "Inventário (venda)",
    "baseline_reserva": "Inventário (reserva)",
    "seguro": "Seguro",
    "holding": "Holding",
    "doacao": "Doação",
    "vgbl": "VGBL",
}


def br(v, casas=0):
    """Formata número no padrão brasileiro."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    s = f"{v:,.{casas}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def ler(nome):
    """Lê um CSV de resultados convertendo para número só o que é número.

    A versão anterior mantinha uma lista de colunas de texto a preservar, o que
    silenciosamente destruía qualquer coluna textual nova (classe de risco, sexo)
    transformando-a em NaN. Aqui a conversão só é aceita se produzir algum valor
    válido — coluna de texto puro fica como está.
    """
    d = pd.read_csv(os.path.join(RES, nome))
    for c in d.columns:
        conv = pd.to_numeric(d[c], errors="coerce")
        if conv.notna().any():
            d[c] = conv
    return d


# ------------------------------------------------------------------ OOXML
def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _cel(texto, larg, negrito, alinha, realce, bordas="", recuo=0, span=1):
    """Célula no estilo IBGE/ABNT: sem fios verticais; fios só onde pedidos."""
    rpr = "<w:rPr>"
    if negrito:
        rpr += "<w:b/>"
    rpr += '<w:sz w:val="20"/>'
    if realce:
        rpr += '<w:highlight w:val="yellow"/>'
    rpr += "</w:rPr>"
    tcb = f"<w:tcBorders>{bordas}</w:tcBorders>" if bordas else ""
    ind = f'<w:ind w:left="{recuo}"/>' if recuo else ""
    kn = "<w:keepNext/>" if span > 1 else ""
    t = f'<w:r>{rpr}<w:t xml:space="preserve">{esc(texto)}</w:t></w:r>' if texto != "" else ""
    gs = f'<w:gridSpan w:val="{span}"/>' if span > 1 else ""
    return (f'<w:tc><w:tcPr><w:tcW w:w="{larg}" w:type="dxa"/>{gs}{tcb}<w:vAlign w:val="bottom"/></w:tcPr>'
            f'<w:p><w:pPr>{kn}<w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/>'
            f'{ind}<w:jc w:val="{alinha}"/></w:pPr>{t}</w:p></w:tc>')


def _fio(lado, sz, cor="000000"):
    return f'<w:{lado} w:val="single" w:sz="{sz}" w:space="0" w:color="{cor}"/>'


def _grupos(col):
    """Detecta agrupamento na primeira coluna ("A  x", "A · x", "grupo · x").
    Devolve [(chave, resto)] ou None quando não há agrupamento útil."""
    import re as _re
    if all(_re.match(r"^[A-H]  \S", c) for c in col):
        g = [("Cenário " + c[0], c[3:]) for c in col]
    elif all(" · " in c for c in col):
        g = []
        for c in col:
            k, r = c.rsplit(" · ", 1)
            g.append((("Cenário " + k) if _re.fullmatch(r"[A-H]", k) else k, r))
    else:
        return None
    chaves = [k for k, _ in g]
    return g if len(set(chaves)) < len(chaves) else None


def _alinha(c):
    import re as _re
    c = str(c).strip()
    if _re.fullmatch(r"[−+\-]?(R\$ )?[\d.,]+(%|\*)?( mil)?", c):
        return "right"
    if c in ("sim", "—", "n/d", "nunca", "não") or len(c) <= 4:
        return "center"
    return "left"


def tabela_xml(cabecalho, linhas, larguras, realce=True):
    """Tabela aberta (IBGE, Normas de apresentação tabular, adotadas pela ABNT):
    fio grosso no topo e na base, fio simples sob o cabeçalho, sem fios
    verticais; grupos da primeira coluna viram linhas de seção com fio claro."""
    total = sum(larguras)
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/>'
           '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/>'
           '<w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
           '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="85" w:type="dxa"/>'
           '<w:right w:w="85" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>']
    out += [f'<w:gridCol w:w="{w}"/>' for w in larguras]
    out.append("</w:tblGrid>")
    cab_b = _fio("top", 12) + _fio("bottom", 6)
    out.append('<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>' + "".join(
        _cel(c, larguras[i], True, "left" if i == 0 else "center", realce, cab_b)
        for i, c in enumerate(cabecalho)) + "</w:tr>")
    grupos = _grupos([str(l[0]) for l in linhas])
    import re as _re
    num = lambda c: _re.fullmatch(r"[−+\-]?(R\$ )?[\d.,]+(%|\*)?( mil)?", str(c).strip()) is not None
    vazio = lambda c: str(c).strip() in ("n/d", "—", "nunca", "")
    col_curta = [all(len(str(l[i]).strip()) <= 4 for l in linhas) for i in range(len(cabecalho))]
    col_num = [any(num(l[i]) for l in linhas) and all(num(l[i]) or vazio(l[i]) for l in linhas)
               for i in range(len(cabecalho))]
    corpo = []
    ultimo = None
    for n, ln in enumerate(linhas):
        primeira = list(ln)
        recuo = 0
        if grupos:
            chave, resto = grupos[n]
            if chave != ultimo:
                corpo.append(("grupo", [chave] + [""] * (len(ln) - 1), ultimo is not None))
                ultimo = chave
            primeira[0] = resto
            recuo = 170
        corpo.append(("linha", primeira, recuo))
    for k, (tipo, ln, extra) in enumerate(corpo):
        fim = k == len(corpo) - 1
        cels = []
        for i, c in enumerate(ln):
            b = ""
            if tipo == "grupo" and extra:
                b += _fio("top", 4, "A6A6A6")
            if fim:
                b += _fio("bottom", 12)
            if tipo == "grupo":
                if i == 0:
                    cels.append(_cel(c, sum(larguras), True, "left", realce, b, span=len(ln)))
                continue
            al = "left" if i == 0 else ("right" if col_num[i] else ("center" if col_curta[i] else "left"))
            cels.append(_cel(c, larguras[i], False, al,
                             realce, b, extra if i == 0 else 0))
        out.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' + "".join(cels) + "</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def titulo_xml(texto, realce=True):
    hl = '<w:highlight w:val="yellow"/>' if realce else ""
    return ('<w:p><w:pPr><w:keepNext/><w:spacing w:after="120"/><w:jc w:val="left"/></w:pPr>'
            f'<w:r><w:rPr><w:b/><w:sz w:val="20"/>{hl}</w:rPr>'
            f'<w:t xml:space="preserve">{esc(texto)}</w:t></w:r></w:p>')


def fonte_xml(texto, realce=True):
    hl = '<w:highlight w:val="yellow"/>' if realce else ""
    return ('<w:p><w:pPr><w:spacing w:before="60" w:after="240"/>'
            '<w:jc w:val="left"/></w:pPr>'
            f'<w:r><w:rPr><w:sz w:val="18"/>{hl}</w:rPr>'
            f'<w:t xml:space="preserve">{esc(texto)}</w:t></w:r></w:p>')


def gravar(nome, titulo, cabecalho, linhas, larguras, fonte, realce=True):
    pd.DataFrame(linhas, columns=cabecalho).to_csv(
        os.path.join(TAB, f"{nome}.csv"), index=False)
    tb = tabela_xml(cabecalho, linhas, larguras, realce)
    if nome in ("T12", "T13"):   # muitas colunas de texto: corpo 9 pt
        tb = tb.replace('<w:sz w:val="20"/>', '<w:sz w:val="18"/>')
    xml = titulo_xml(titulo, realce) + tb + fonte_xml(fonte, realce)
    open(os.path.join(TAB, f"{nome}.xml"), "w", encoding="utf-8").write(xml)
    return {"nome": nome, "titulo": titulo, "linhas": len(linhas),
            "colunas": len(cabecalho)}


# Os nomes de arquivo T1..T10 seguem a ordem de criação; o NÚMERO exibido em
# cada título segue a ordem de aparição no texto, que é outra. A correspondência
# está registrada em NUMERO_NO_TEXTO para quem for conferir.
NUMERO_NO_TEXTO = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5,
                   "T10": 6, "T9": 7, "T6": 8, "T7": 9, "T8": 10,
                   "T11": 11, "T12": 12, "T13": 13}


# =============================================================== T1
def t1_principal():
    """Custo por cenário e estratégia — a tabela principal da seção 6."""
    d = ler(BASE)
    linhas = []
    for cen in sorted(d.cenario.unique()):
        for e in ORDEM:
            r = d[(d.cenario == cen) & (d.estrategia == e)]
            if r.empty:
                continue
            r = r.iloc[0]
            linhas.append([f"{cen}  {NOME[e]}", br(r.vp_esperado),
                           br(r.cte95), br(r.reversibilidade),
                           "sim" if r.pareto_2d == 1 else "—"])
    return gravar(
        "T1",
        "Tabela 1 – Custo sucessório por cenário e estratégia (regime 2026, taxa "
        "real bruta de 6% a.a., sem abandono da apólice), em R$ de valor presente",
        ["Cenário / estratégia", "E[VP]", "CTE-95", "Reversibilidade", "Fronteira"],
        linhas, [3200, 1450, 1450, 1800, 1150],
        "Fonte: elaboração própria (2026). A coluna Fronteira indica se a estratégia "
        "pertence ao conjunto não dominado em (E[VP], CTE-95) dentro do cenário. A "
        "coluna Reversibilidade é o valor presente esperado do montante recuperável "
        "pelo titular em caso de abandono da estratégia em vida (Apêndice A, seção "
        "A.6), reportado de forma descritiva, sem integrar o critério de dominância. O "
        "cenário E roda com prêmio agravado de classe C, conforme a seção 5.")


# =============================================================== T2
def t2_ies():
    """Decomposição do IES em todos os cenários (v25; até a v24, só o cenário A)."""
    d = ler(BASE)
    menos = lambda v: br(v).replace("-", "−")
    linhas = []
    for cen in sorted(d.cenario.unique()):
        sub = d[d.cenario == cen]
        for e in ORDEM:
            r = sub[sub.estrategia == e]
            if r.empty:
                continue
            r = r.iloc[0]
            linhas.append([f"{cen}  {NOME[e]}", menos(r.ies_e_tributaria),
                           menos(r.ies_e_processual), menos(r.ies_e_iliquidez),
                           menos(r.ies_e_instrumento), menos(r.vp_esperado)])
    return gravar(
        "T2",
        "Tabela 2 – Índice de Eficiência Sucessória: decomposição do custo esperado "
        "por cenário e estratégia (regime 2026, taxa real bruta de 6% a.a., sem "
        "abandono da apólice), em R$ de valor presente",
        ["Cenário / estratégia", "Fricção tributária", "Fricção processual",
         "Fricção de liquidez", "Preço do instrumento", "Total"],
        linhas, [3100, 1200, 1200, 1100, 1250, 1150],
        "Fonte: elaboração própria (2026). A soma das quatro parcelas reproduz o "
        "total por construção; a demonstração está no Apêndice A, seção A.8. No VGBL, "
        "a fricção tributária é negativa porque o ganho do diferimento do imposto de "
        "renda supera os tributos que incidem sobre o veículo. O cenário E roda com "
        "prêmio agravado de classe C, conforme a seção 5.")


# =============================================================== T3
def t3_juro():
    """Sensibilidade à taxa real de desconto, cenário A."""
    s = ler(SENS)
    t = s[(s.eixo == "taxa_desconto") & (s.cenario == "A")]
    linhas = []
    for v in sorted(t.valor.unique()):
        x = t[t.valor == v]
        seg = x[x.estrategia == "seguro"].iloc[0]
        inv = x[x.estrategia == "baseline_venda"].iloc[0]
        fr = ", ".join(NOME[e] for e in x[x.na_fronteira == 1].estrategia)
        linhas.append([f"{v*100:.0f}%".replace(".", ","), br(seg.vp_esperado),
                       br(inv.vp_esperado),
                       f"{seg.vp_esperado/inv.vp_esperado:.2f}".replace(".", ","),
                       fr])
    return gravar(
        "T3",
        "Tabela 3 – Sensibilidade à taxa real de desconto: custo esperado no "
        "cenário A e composição da fronteira",
        ["Taxa real", "Seguro", "Inventário", "Razão", "Fronteira de eficiência"],
        linhas, [1000, 1500, 1500, 900, 4000],
        "Fonte: elaboração própria (2026). Regime 2026, produto WL10, sem abandono da apólice.")


# =============================================================== T4
def t4_caducidade():
    """CTE-95 do seguro sob a grade ampliada de caducidade."""
    dados = {lp: ler(f"{VERSAO}_2026_r6ir_lapso{lp}.csv") for lp in LAPSOS}
    cens = sorted(dados[0].cenario.unique())
    linhas = []
    for cen in cens:
        vals = []
        for lp in LAPSOS:
            r = dados[lp][(dados[lp].cenario == cen) &
                          (dados[lp].estrategia == "seguro")].iloc[0]
            vals.append(r.cte95)
        var = (vals[-1] / vals[0] - 1) * 100
        linhas.append([cen] + [br(v) for v in vals] +
                      [f"+{var:.0f}%"])
    cab = ["Cenário"] + [("λ = 0" if lp == 0 else f"λ = {lp}% a.a.")
                         for lp in LAPSOS] + ["Variação"]
    return gravar(
        "T4",
        "Tabela 4 – Efeito do abandono da apólice sobre o custo de cauda do seguro (CTE-95), "
        "por cenário, em R$ de valor presente",
        cab, linhas, [900, 1350, 1350, 1350, 1350, 1350, 1050],
        "Fonte: elaboração própria (2026). A coluna de variação compara λ = 20% a.a. "
        "com a ausência de abandono. Sobre a calibração de λ e a razão de a grade "
        "ir até 20% ao ano, ver a discussão de fontes nesta seção.")


# =============================================================== T5
def t5_grid():
    """Razão entre o custo esperado do seguro e o do inventário direto,
    por idade e produto, nos cenários A, C e E."""
    g = ler(GRID)
    linhas = []
    for cen in ("A", "C", "E"):
        for prod in ("WL10", "WL20", "WL30", "TP10", "TP20"):
            cels = []
            for idade in (40, 50, 60, 70):
                sub = g[(g.cenario == cen) & (g.idade == idade) &
                        (g.produto == prod)]
                seg = sub[sub.estrategia == "seguro"]
                inv = sub[sub.estrategia == "baseline_venda"]
                if seg.empty or inv.empty or pd.isna(seg.iloc[0].vp_esperado):
                    cels.append("n/d")
                    continue
                razao = seg.iloc[0].vp_esperado / inv.iloc[0].vp_esperado
                marca = "*" if seg.iloc[0].na_fronteira == 1 else ""
                cels.append(f"{razao:.2f}".replace(".", ",") + marca)
            linhas.append([f"{cen} · {prod}"] + cels)
    return gravar(
        "T5",
        "Tabela 5 – Razão entre o custo esperado do seguro e o do inventário direto, "
        "por idade de contratação e produto",
        ["Cenário · produto", "40 anos", "50 anos", "60 anos", "70 anos"],
        linhas, [1800, 1700, 1700, 1700, 1700],
        "Fonte: elaboração própria (2026). Regime 2026, taxa real bruta de 6% a.a. O "
        "asterisco indica que o seguro integra a fronteira de eficiência; “n/d” indica "
        "produto indisponível para a idade — resultado de contratabilidade. O cenário "
        "E carrega prêmio agravado de classe C em todas as idades, por ser o perfil "
        "que isola a restrição de aceitação.")


# =============================================================== T6
def t6_cenario_h():
    """Cenário societário: apuração de haveres."""
    d = ler(CEN_H)
    rot = {"base": "Base (4 parcelas, crédito disponível)",
           "sem_parcelamento": "Sem parcelamento contratual",
           "sem_credito_ponte": "Sem crédito-ponte",
           "sem_parcelamento_sem_credito": "Sem parcelamento e sem crédito",
           "socios_jovens_35_50": "Sócios mais jovens (35–50)",
           "firma_50mi": "Firma de R$ 50 milhões",
           "r_4pct": "Taxa real de 4%", "r_8pct": "Taxa real de 8%"}
    linhas = []
    for (var, prod), sub in d.groupby(["variante", "produto"], sort=False):
        hav = sub[sub.estrategia == "baseline_haveres"]
        seg = sub[sub.estrategia == "seguro_buysell"]
        if hav.empty or seg.empty or pd.isna(seg.iloc[0].vp_esperado):
            continue
        h, g_ = hav.iloc[0], seg.iloc[0]
        fr = []
        if h.na_fronteira == 1:
            fr.append("Haveres")
        if g_.na_fronteira == 1:
            fr.append("Seguro")
        linhas.append([f"{rot.get(var, var)} · {prod}",
                       br(h.vp_esperado), br(g_.vp_esperado),
                       br(h.cte95), br(g_.cte95), ", ".join(fr) or "—"])
    return gravar(
        "T6",
        "Tabela 8 – Cenário societário: pagamento de haveres com recursos próprios "
        "e com seguro (entity purchase), em R$ de valor presente",
        ["Variante · produto", "Haveres E[VP]", "Seguro E[VP]",
         "Haveres CTE-95", "Seguro CTE-95", "Fronteira"],
        linhas, [1500, 1300, 1300, 1300, 1300, 2300],
        "Fonte: elaboração própria (2026). Cinco sócios, firma de R$ 10 milhões, "
        "haveres de R$ 2 milhões por sócio. Valor esperado exato por aditividade; "
        "cauda por simulação de Monte Carlo com semente fixa.")


# =============================================================== T9
def t9_escada_agravo():
    """Sensibilidade à classe de risco no cenário E."""
    d = ler(ESCADA)
    base = d.iloc[0].vp_esperado
    linhas = []
    for _, r in d.iterrows():
        linhas.append([r.classe, br(r.fator, 2), br(r.premio_anual),
                       br(r.vp_esperado), br(r.cte95),
                       f"+{(r.vp_esperado/base-1)*100:.1f}%".replace(".", ","),
                       "sim" if r.seguro_na_fronteira == 1 else "—"])
    return gravar(
        "T9",
        "Tabela 7 – Sensibilidade ao agravo de risco no cenário E: prêmio e custo "
        "do seguro por classe de aceitação, produto WL10 aos 70 anos",
        ["Classe", "Fator", "Prêmio anual", "E[VP]", "CTE-95",
         "Sobre Standard", "Fronteira"],
        linhas, [1050, 1050, 1400, 1400, 1400, 1300, 1100],
        "Fonte: elaboração própria (2026) a partir da tabela de precificação da "
        "seguradora. D1 é o teto de aceitação do produto: não há classe além dela "
        "em idade alguma. O caso base do cenário E adota a classe C.")


# Os nomes de arquivo T1..T10 seguem a ordem de criação; o NÚMERO exibido em
# cada título segue a ordem de aparição no texto, que é outra. A correspondência
# está registrada em NUMERO_NO_TEXTO para quem for conferir.
NUMERO_NO_TEXTO = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5,
                   "T10": 6, "T9": 7, "T6": 8, "T7": 9, "T8": 10,
                   "T11": 11, "T12": 12, "T13": 13}


# =============================================================== T10
def t10_contratabilidade():
    """Mapa de oferta: idade máxima e teto de agravo por produto."""
    d = ler(CONTRAT)
    d = d[d.sexo == "M"]
    ordem_cl = ["Standard", "A1", "A2", "B", "C", "D1", "D2", "E1", "E2",
                "F1", "F2", "G", "H1", "H2"]
    linhas = []
    for prod in ("WL10", "WL20", "WL30", "TP10", "TP20"):
        sub = d[d.produto == prod]
        if sub.empty:
            continue
        cls = [c for c in ordem_cl if c in set(sub.classe)]
        linhas.append([prod,
                       f"{int(sub.idade_min.min())}–{int(sub.idade_max.max())}",
                       str(len(cls)), cls[-1],
                       "sim" if len(cls) > 1 else "não"])
    return gravar(
        "T10",
        "Tabela 6 – Contratabilidade por produto: faixa etária de oferta e teto de "
        "agravo aceito",
        ["Produto", "Idades ofertadas", "Classes", "Teto de agravo",
         "Aceita agravo"],
        linhas, [1400, 1900, 1300, 1700, 1600],
        "Fonte: elaboração própria (2026) a partir da tabela de precificação da "
        "seguradora, perfil masculino. Os vitalícios vão até os 70 anos mas aceitam "
        "no máximo a classe D1 — e apenas o WL10, já que WL20 e WL30 só aceitam "
        "Standard. Os temporários aceitam a escada completa até H2, mas expiram aos "
        "65 (TP10) e aos 55 (TP20). É a conjunção dos dois tetos que fecha o mercado "
        "para o comprador idoso e agravado.")


# =============================================================== T7
def t7_sem_credito():
    """Variante de indisponibilidade de crédito-ponte, cenários A–F.

    Prometida na seção 5.4 e até então reportada apenas para o cenário H.
    O eixo 'plusvalia_sem_credito' força spread proibitivo no crédito-ponte,
    de modo que a família só dispõe da venda forçada.
    """
    s = ler(SEM_CRED)
    base = ler(BASE)
    sc = s[(s.eixo == "plusvalia_sem_credito") & (s.valor == 0.30)]
    linhas = []
    for cen in sorted(sc.cenario.unique()):
        b = base[base.cenario == cen]
        v = sc[sc.cenario == cen]
        fr_base = ", ".join(CURTO[e] for e in b[b.pareto_2d == 1].estrategia)
        fr_var = ", ".join(CURTO[e] for e in v[v.na_fronteira == 1].estrategia)
        seg_b = b[b.estrategia == "seguro"].iloc[0]
        seg_v = v[v.estrategia == "seguro"].iloc[0]
        inv_b = b[b.estrategia == "baseline_venda"].iloc[0]
        inv_v = v[v.estrategia == "baseline_venda"].iloc[0]
        linhas.append([
            cen,
            br(inv_b.vp_esperado), br(inv_v.vp_esperado),
            br(seg_b.vp_esperado), br(seg_v.vp_esperado),
            fr_base or "—", fr_var or "—",
        ])
    return gravar(
        "T7",
        "Tabela 9 – Efeito da indisponibilidade de crédito-ponte sobre o custo "
        "e sobre a fronteira de eficiência, por cenário (regime 2026, taxa real "
        "bruta de 6% a.a., sem abandono da apólice), em R$ de valor presente",
        ["Cenário", "Inventário base", "Inventário s/ crédito",
         "Seguro base", "Seguro s/ crédito", "Fronteira base",
         "Fronteira s/ crédito"],
        linhas,
        [900, 1100, 1150, 1100, 1150, 1800, 1800],
        "Fonte: elaboração própria (2026). Na variante sem crédito-ponte a família "
        "dispõe apenas da venda forçada de ativos, com deságio de liquidez de 25% e "
        "ganho de capital tributável (fração de ganho acumulado de 30%). O custo do seguro "
        "não se altera entre as colunas porque o instrumento não recorre a nenhuma "
        "das duas saídas.")


# =============================================================== T8
def t8_pos2027():
    """Sensibilidade regulatória: regime 2026 × pós-2027 (LC 227/2026)."""
    a = ler(BASE)
    b = ler(POS)
    linhas = []
    for cen in sorted(a.cenario.unique()):
        xa, xb = a[a.cenario == cen], b[b.cenario == cen]
        ia = xa[xa.estrategia == "baseline_venda"].iloc[0].vp_esperado
        ib = xb[xb.estrategia == "baseline_venda"].iloc[0].vp_esperado
        ha = xa[xa.estrategia == "holding"].iloc[0].vp_esperado
        hb = xb[xb.estrategia == "holding"].iloc[0].vp_esperado
        fa = ", ".join(CURTO[e] for e in xa[xa.pareto_2d == 1].estrategia)
        fb = ", ".join(CURTO[e] for e in xb[xb.pareto_2d == 1].estrategia)
        linhas.append([cen, br(ia), br(ib), br(ha), br(hb), fa, fb])
    return gravar(
        "T8",
        "Tabela 10 – Sensibilidade regulatória: regime de 2026 e regime pós-2027 "
        "(LC nº 227/2026), por cenário (taxa real bruta de 6% a.a., sem "
        "abandono da apólice), em R$ de valor presente",
        ["Cenário", "Inventário 2026", "Inventário pós-2027",
         "Holding 2026", "Holding pós-2027", "Fronteira 2026",
         "Fronteira pós-2027"],
        linhas,
        [900, 1100, 1150, 1100, 1150, 1800, 1800],
        "Fonte: elaboração própria (2026). O regime pós-2027 substitui a base "
        "contábil das quotas pelo valor de mercado e consolida doações sucessivas, "
        "extinguindo o deságio que hoje favorece holding e doação em vida. As "
        "faixas progressivas de São Paulo seguem proposta legislativa e devem ser "
        "lidas como sensibilidade, não como direito vigente.")


# =============================================================== figuras
def figuras():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = ler(BASE)
    cens = sorted(d.cenario.unique())
    # 3 linhas x 2 colunas: em retrato cada painel fica ~7,6 cm na página,
    # contra ~5 cm no arranjo 2x3 — diferença entre legível e ilegível impresso.
    fig, axes = plt.subplots(3, 2, figsize=(8.0, 10.2))
    for ax, cen in zip(axes.ravel(), cens):
        sub = d[d.cenario == cen]
        fr = sub[sub.pareto_2d == 1].sort_values("vp_esperado")
        ax.plot(fr.vp_esperado / 1000, fr.cte95 / 1000, "-",
                color="0.55", lw=1.4, zorder=1)
        xs = sub.vp_esperado / 1000
        meio = (xs.min() + xs.max()) / 2
        for _, r in sub.iterrows():
            na = r.pareto_2d == 1
            x, y = r.vp_esperado / 1000, r.cte95 / 1000
            ax.scatter(x, y, s=70 if na else 42,
                       facecolor="black" if na else "white",
                       edgecolor="black", linewidth=1.1, zorder=3)
            # rótulo à esquerda do ponto quando ele está na metade direita,
            # para que o texto não vaze para fora da moldura dos eixos
            direita = x > meio
            ax.annotate(CURTO[r.estrategia], (x, y),
                        textcoords="offset points",
                        xytext=(-7, 6) if direita else (7, 6),
                        ha="right" if direita else "left", fontsize=8.5)
        ax.margins(x=0.18, y=0.16)
        ax.set_title(f"Cenário {cen}", fontsize=12)
        ax.set_xlabel("E[VP]  (R$ mil)", fontsize=10)
        ax.set_ylabel("CTE-95  (R$ mil)", fontsize=10)
        ax.tick_params(labelsize=9)
        ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout(h_pad=2.0, w_pad=1.6)
    fig.savefig(os.path.join(FIG, "F1_fronteiras.png"), dpi=200)
    plt.close(fig)

    # F2 — decomposição do IES, cenário A
    sub = d[d.cenario == "A"]
    parcelas = [("ies_e_tributaria", "Fricção tributária", "0.25"),
                ("ies_e_processual", "Fricção processual", "0.50"),
                ("ies_e_iliquidez", "Fricção de liquidez", "0.72"),
                ("ies_e_instrumento", "Preço do instrumento", "0.90")]
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    rot = [CURTO[e].replace(" (", "\n(") for e in sub.estrategia]
    baixo = [0.0] * len(sub)
    for col, lab, cor in parcelas:
        vals = (sub[col] / 1000).tolist()
        ax.bar(rot, vals, bottom=baixo, label=lab, color=cor,
               edgecolor="black", linewidth=0.6)
        baixo = [b + v for b, v in zip(baixo, vals)]
    ax.set_ylabel("E[VP]  (R$ mil)", fontsize=10)
    ax.legend(fontsize=9.5, frameon=False)
    ax.tick_params(labelsize=9.5)
    ax.grid(axis="y", alpha=0.25, lw=0.5)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "F2_ies.png"), dpi=200)
    plt.close(fig)
    return ["F1_fronteiras.png", "F2_ies.png"]



# =============================================================== T11
def t11_taxa_vgbl():
    """Sensibilidade à taxa de administração do VGBL, cenários B e F."""
    g = ler(TAXA_VGBL)
    lim = ler(LIMIARES)
    linhas = []
    for cen in ("B", "F"):
        sub = g[g.cenario == cen].sort_values("taxa_adm")
        for _, r in sub.iterrows():
            tx = f"{r.taxa_adm*100:.2f}".replace(".", ",") + "%"
            linhas.append([f"{cen} · {tx}", br(r.vgbl_e), br(r.vgbl_cte),
                           br(r.inventario_e),
                           "sim" if r.vgbl_na_fronteira == 1 else "—"])
    nota = []
    for _, r in lim.iterrows():
        nota.append(
            f"No cenário {r.cenario} o custo esperado cruza zero em "
            f"{r.taxa_custo_zero*100:.2f}".replace(".", ",") + "%, supera o do "
            f"inventário direto em {r.taxa_supera_inventario*100:.2f}".replace(".", ",")
            + "% e o veículo deixa a fronteira em "
            f"{r.taxa_sai_fronteira*100:.2f}".replace(".", ",") + "%")
    return gravar(
        "T11",
        "Tabela 11 – Sensibilidade à taxa de administração do VGBL: custo do "
        "veículo e composição da fronteira nos cenários em que ele é aplicável",
        ["Cenário · taxa", "VGBL E[VP]", "VGBL CTE-95", "Inventário E[VP]",
         "VGBL na fronteira"],
        linhas, [2100, 1700, 1700, 1700, 1500],
        "Fonte: elaboração própria (2026). Regime 2026, taxa real bruta de 6% a.a., "
        "sem abandono da apólice. A grade é ancorada em fonte: 1,32% é a média oficial do "
        "segmento aberto e 1,75% a média amostral de Soares e Campani (2020); os "
        "extremos delimitam a faixa em que se situa a quase totalidade dos fundos "
        "de previdência em operação. " + ". ".join(nota) + ".")



# =============================================================== v10: T12, T13, F3
ABREV = {"baseline_venda": "Inv.", "baseline_reserva": "Res.", "seguro": "Seg.",
         "holding": "Hol.", "doacao": "Doa.", "vgbl": "VGBL"}
NOTA_ABREV = ("Inv. = inventário com crédito-ponte ou venda forçada; Res. = "
              "inventário com reserva prévia; Seg. = seguro de vida; Hol. = holding "
              "familiar; Doa. = doação em vida.")


def _fronteiras(sub):
    return [", ".join(ABREV[e] for e in sub[(sub.cenario == c) & (sub.na_fronteira == 1)]
                      .estrategia) or "—" for c in "ABCDEF"]


def _brl(v):
    return "R$ " + br(v)


def t12_holding_doacao():
    """Sensibilidade aos custos fixos da holding e ao honorário da doação."""
    d = pd.read_csv(os.path.join(RES, HOLD), dtype={"valor": str})
    lim = ler(HOLD_LIM).set_index("cenario")
    base = ler(BASE).rename(columns={"pareto_2d": "na_fronteira"})
    rot = {"holding_constituicao": "Constituição da holding",
           "holding_manutencao": "Manutenção anual da holding",
           "honor_doacao": "Honorário de estruturação da doação"}
    linhas = [["Caso base"] + _fronteiras(base)]
    for eixo in ("holding_constituicao", "holding_manutencao", "honor_doacao"):
        sub = d[d.eixo == eixo]
        for v in sub.valor.unique():
            if (eixo == "holding_constituicao" and float(v) == 25000) or \
               (eixo == "holding_manutencao" and float(v) == 18000) or \
               (eixo == "honor_doacao" and abs(float(v) - 0.015) < 1e-9):
                continue
            val = (f"{float(v)*100:.1f}".replace(".", ",") + "%") if eixo == "honor_doacao" \
                else _brl(float(v))
            linhas.append([f"{rot[eixo]}: {val}"] + _fronteiras(sub[sub.valor == v]))
    comb = {"holding_barata_doacao_cara":
            "Holding barata (R$ 10 mil + R$ 6 mil/ano), doação a 5%",
            "holding_cara_doacao_barata":
            "Holding cara (R$ 100 mil + R$ 60 mil/ano), doação a 0,5%"}
    sub = d[d.eixo == "combinado"]
    for k, r in comb.items():
        linhas.append([r] + _fronteiras(sub[sub.valor == k]))
    m = lim.manutencao_sai_fronteira
    h = lim.honor_doacao_sai_fronteira
    nota = (f"Fonte: elaboração própria (2026). Regime 2026, taxa real bruta de 6% a.a., "
            f"sem abandono da apólice. Caso base: constituição de R$ 25 mil, manutenção de R$ 18 mil "
            f"anuais e honorário de 1,5% do valor doado. Cada linha altera um parâmetro, "
            f"exceto as duas últimas. Limiares: a holding deixa a fronteira com manutenção "
            f"anual a partir de cerca de R$ {m['E']/1000:.0f} mil no cenário E, "
            f"R$ {m['C']/1000:.0f} mil no C e R$ {m['D']/1000:.0f} mil no D; a doação deixa a fronteira com honorário a partir de "
            + f"{h['A']*100:.1f}".replace(".", ",") + "% no cenário A e "
            + f"{h['E']*100:.1f}".replace(".", ",") + "% no E. " + NOTA_ABREV)
    return gravar(
        "T12",
        "Tabela 12 – Sensibilidade aos custos da holding e da doação em vida: "
        "estratégias na fronteira de eficiência, por cenário",
        ["Parâmetro alterado", "A", "B", "C", "D", "E", "F"],
        linhas, [3000, 1350, 700, 1000, 1000, 1150, 700], nota)


def t13_complementares():
    """Sensibilidades complementares prometidas na seção 5."""
    d = pd.read_csv(os.path.join(RES, COMPL), dtype={"valor": str})
    rot = [("base", "base", "Caso base"),
           ("aliquota_ir", 0.175, "Alíquota de IR do contrafactual: 17,5%"),
           ("aliquota_ir", 0.225, "Alíquota de IR do contrafactual: 22,5%"),
           ("carga_premio", 0.7, "Carga do prêmio: −30%"),
           ("carga_premio", 1.3, "Carga do prêmio: +30%"),
           ("tabua", "brems_mt_2021", "Tábua BR-EMS mt 2021"),
           ("tabua", "ibge_2024", "Tábua IBGE 2024 (população geral)"),
           ("desagio_sem_credito", 0.15, "Sem crédito-ponte, deságio de 15%"),
           ("desagio_sem_credito", 0.25, "Sem crédito-ponte, deságio de 25%"),
           ("desagio_sem_credito", 0.35, "Sem crédito-ponte, deságio de 35%"),
           ("consumo", "com_credito", "Custo de vida no bloqueio, com crédito-ponte"),
           ("consumo", "sem_credito", "Custo de vida no bloqueio, sem crédito-ponte"),
           ("consumo", "com_credito_seguro_cobre",
            "Idem, com crédito e seguro dimensionado também para o custo de vida"),
           ("consumo", "sem_credito_seguro_cobre",
            "Idem, sem crédito e seguro dimensionado também para o custo de vida")]
    linhas = []
    for eixo, val, nome in rot:
        sub = d[(d.eixo == eixo) & (d.valor == str(val))]
        a = sub[sub.cenario == "A"].set_index("estrategia").vp_esperado
        razao = f"{a['seguro'] / a['baseline_venda']:.2f}".replace(".", ",")
        linhas.append([nome, razao] + _fronteiras(sub))
    return gravar(
        "T13",
        "Tabela 13 – Sensibilidades complementares: razão entre o custo esperado do "
        "seguro e o do inventário direto no cenário A e estratégias na fronteira de "
        "eficiência, por cenário",
        ["Parâmetro alterado", "Razão", "A", "B", "C", "D", "E", "F"],
        linhas, [2450, 650, 1350, 700, 1000, 1000, 1150, 700],
        "Fonte: elaboração própria (2026). Regime 2026, taxa real bruta de 6% a.a., "
        "sem abandono da apólice, produto WL10. Caso base: alíquota de 15%, prêmio da "
        "tabela da seguradora, tábua BR-EMS mt 2026, crédito-ponte disponível e custo de "
        "vida da família durante o bloqueio omitido. Nas linhas sem crédito-ponte a "
        "família realiza ganho de capital sobre 30% do valor vendido. Nas linhas de "
        "custo de vida, a família despende 4% do patrimônio ao ano, financiados durante "
        "o prazo do inventário na proporção dos bens que permanecem no espólio. "
        + NOTA_ABREV)


def figura_arvore():
    """Árvore de decisão — síntese esquemática dos resultados (Figura 3)."""
    import subprocess
    dot = r"""digraph G {
  graph [rankdir=TB, nodesep=0.35, ranksep=0.30, fontname="DejaVu Sans", dpi=220,
         newrank=true];
  node  [fontname="DejaVu Sans", fontsize=10.5, shape=box, style="rounded",
         penwidth=1.1, margin="0.12,0.07", width=2.3];
  edge  [fontname="DejaVu Sans", fontsize=9.5, arrowsize=0.6, penwidth=0.9];
  q1 [label="O titular tem\nmotivo de legado?"];
  g  [label="Caso-limite G\nInstrumento racional: renda vitalícia.\nSeguro sem função sucessória.",
      style="rounded,filled", fillcolor="gray92"];
  q2 [label="Quem suporta a obrigação\nno óbito?"];
  h  [label="Cenário H — haveres\nNa fronteira: pagamento direto e\nseguro temporário. Vitalício dominado,\nsalvo sem parcelamento e sem crédito.",
      style="rounded,filled", fillcolor="gray92"];
  q3 [label="O VGBL é aplicável\nao perfil?"];
  bf [label="Cenários B e F\nVGBL domina (taxa de\nadministração até 2,9% a.a.).",
      style="rounded,filled", fillcolor="gray92"];
  q4 [label="O titular é contratável\nem condição padrão?"];
  e  [label="Cenário E — idade avançada e agravo\nNa fronteira: holding e doação.\nSeguro fora em todas as classes.",
      style="rounded,filled", fillcolor="gray92"];
  q5 [label="Patrimônio empresarial\nde grande porte?"];
  cd [label="Cenários C e D\nNa fronteira: holding (regime 2026).\nSeguro entra em C sem crédito-ponte\nou no regime pós-2027.",
      style="rounded,filled", fillcolor="gray92"];
  a  [label="Cenário A\nNa fronteira: inventário, seguro\ne doação. Escolha pela aversão\nao risco de cauda.",
      style="rounded,filled", fillcolor="gray92"];
  ca [label="Condição para o seguro:\npersistência do contrato\n(sai da fronteira com\nabandono de 2% a.a.)",
      shape=note, style="", fontsize=9.5, width=1.6];
  {rank=same; q1; g;}  {rank=same; q2; h;}  {rank=same; q3; bf;}
  {rank=same; q4; e;}  {rank=same; q5; cd;} {rank=same; a; ca;}
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
  a -> ca  [style=dashed, arrowhead=none];
}"""

    caminho = os.path.join(FIG, "F3_arvore.dot")
    open(caminho, "w", encoding="utf-8").write(dot)
    subprocess.run(["dot", "-Tpng", caminho, "-o", os.path.join(FIG, "F3_arvore.png")],
                   check=True)
    return "F3_arvore.png"

if __name__ == "__main__":
    man = {"tabelas": [t1_principal(), t2_ies(), t3_juro(), t4_caducidade(),
                       t5_grid(), t6_cenario_h(), t7_sem_credito(),
                       t8_pos2027(), t9_escada_agravo(), t10_contratabilidade(),
                       t11_taxa_vgbl(), t12_holding_doacao(), t13_complementares()],
           "figuras": []}
    json.dump(man, open(os.path.join(TAB, "manifesto.json"), "w"),
              ensure_ascii=False, indent=2)
    for t in man["tabelas"]:
        print(f"  {t['nome']}: {t['linhas']} linhas × {t['colunas']} colunas")
    for f in man["figuras"]:
        print(f"  figura {f}")
    print("OK")
