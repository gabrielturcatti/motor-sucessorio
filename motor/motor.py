"""Motor v1 — custo sucessório em duas dimensões: VP esperado × CTE-95.

Estratégias avaliadas (custo em VP real, por ano possível de óbito t):
  baseline_venda   inventário pago com venda forçada de ativos (deságio DLOM)
  baseline_reserva reserva líquida pré-constituída (sofre gross-up: a própria
                   reserva integra o espólio) + crédito-ponte no bloqueio
  seguro           prêmios até a morte; capital isento e imediato cobre o custo
  holding          custo inicial (ITCMD doação de quotas + constituição) +
                   manutenção anual + inventário residual dos bens de fora
  doacao           doação em vida com usufruto na data zero (100% aos herdeiros)
  vgbl             aporte = custo-alvo; IOF (>600k/ano) + taxa de adm até a morte

Decisões (Gabriel, 08/jul/2026): duas variantes de baseline + doação em vida;
CTE-95 como métrica de cauda; VP atuarial (BR-EMS mt 2026).
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import premios, custos, atuarial, resgate
from cenarios import CENARIOS

DESAGIO_CONTABIL = 0.40   # ⚠ validar (quotas a valor contábil, regime 2026)
CTE_NIVEL = 0.95
LAPSO_AA = 0.0            # hazard anual de caducidade da apólice (0 = v1)


def base_itcmd(cen, regime):
    if regime == "2026":
        return cen.patrimonio * (1 - DESAGIO_CONTABIL * cen.fracao_empresa)
    return cen.patrimonio


def estrategias(cen, r: float, regime: str, produto=("WL", 10),
                pct_honorarios=None, spread_ponte=0.06, desagio_venda=0.25,
                pagamento_mensal=True, fracao_doada=None, pct_honor_doacao=None,
                ir_contrafactual=False, plusvalia=None, aliquota_gk=None,
                aliquota_ir=None, taxa_adm_vgbl=None,
                holding_constituicao=None, holding_manutencao=None,
                carga_premio=1.0, gk_transmissao_gratuita=0.0):
    """Retorna (E, REC, ci, meta, COMP).

    COMP[estrategia](t) → dict com a decomposição do MESMO custo que E devolve,
    em quatro parcelas (o Índice de Eficiência Sucessória):

      tributaria  ITCMD (causa mortis ou doação), IOF, IR sobre ganho de capital
                  na venda forçada e efeito tributário líquido do VGBL;
      processual  honorários de inventário, emolumentos, custas e multa;
      iliquidez   cunha Λ — deságio de venda forçada ou juro do crédito-ponte;
      instrumento preço pago voluntariamente a um provedor privado para
                  reestruturar a transmissão: prêmios de seguro, constituição e
                  manutenção de holding, honorários de estruturação da doação,
                  taxa de administração do VGBL.

    O critério de classificação é a natureza do dispêndio, não quem o recebe:
    as três primeiras parcelas são o que a transmissão perde para o Estado e
    para o processo (as cunhas que o benchmark de irrelevância zera), e a quarta
    é o que se paga para reduzi-las. É essa troca — cunha por preço — que o
    índice mede. Por construção, sum(COMP[s](t).values()) == E[s](t).
    

    E[estrategia](t)   → custo em VP se o óbito ocorre no ano t
    REC[estrategia](t) → valor em R$ (nominal, no ano t) que o TITULAR recupera
                         se abandonar a estratégia em vida no ano t. Mede
                         reversibilidade: a doação em vida vale zero aqui por
                         construção, e é essa dimensão que (E, CTE-95) não vê.
    meta               → parâmetros do seguro, p/ o modelo de lapso

    Parâmetros de sensibilidade acrescentados no v10 (02/nov/2026), todos com
    default que reproduz o v9 exatamente:
      holding_constituicao / holding_manutencao  custos fixos da holding (R$);
      carga_premio        multiplicador do prêmio comercial (1,0 = tabela);
      gk_transmissao_gratuita  fração do valor transmitido em vida (quotas da
                          holding e bens doados) que é ganho de capital latente,
                          tributado a 15% quando a transmissão se faz a VALOR DE
                          MERCADO (art. 23 da Lei 9.532/1997). 0,0 = transmissão
                          pelo valor declarado, sem IR no ato (caso base).
    """
    ci = custos.custo_inventario(cen.uf, cen.patrimonio, cen.n_herdeiros,
                                 cen.modalidade_inventario, regime,
                                 base_itcmd=base_itcmd(cen, regime),
                                 pct_honorarios=pct_honorarios)
    prazo = custos.PRAZO_INVENTARIO_MESES[cen.modalidade_inventario]
    # v4 (29/ago/2026): com ir_contrafactual=True, o dinheiro da família
    # rende LÍQUIDO de IR (taxa_real_liquida) — e é essa taxa que desconta
    # todos os fluxos. O crédito-ponte, porém, é tomado à taxa BRUTA de
    # mercado (juro pago pela família não é dedutível).
    r_bruto = r
    t_ir_param = custos.ALIQUOTA_IR_RF if aliquota_ir is None else aliquota_ir
    if ir_contrafactual:
        r = custos.taxa_real_liquida(r_bruto, aliquota_ir=t_ir_param)
    kw_gk = {}
    if plusvalia is not None:
        kw_gk["plusvalia"] = plusvalia
    if aliquota_gk is not None:
        kw_gk["aliquota_gk"] = aliquota_gk
    cunha = custos.cunha_iliquidez(ci.total, prazo, r_bruto, spread_ponte,
                                   desagio_venda, **kw_gk)
    desc = lambda v, t: v / (1 + r) ** (t + 0.5)
    E, REC, meta, COMP = {}, {}, {}, {}
    Z = {"tributaria": 0.0, "processual": 0.0, "iliquidez": 0.0, "instrumento": 0.0}
    meta["r_desconto"], meta["r_bruto"] = r, r_bruto

    # baseline: venda forçada (usa o mínimo entre ponte e venda — família racional)
    E["baseline_venda"] = lambda t: desc(ci.total + cunha["cunha"], t)
    COMP["baseline_venda"] = lambda t: {
        "tributaria": desc(ci.itcmd + cunha["tributo_gk"], t),
        "processual": desc(ci.honorarios + ci.emolumentos_ou_custas + ci.multa, t),
        "iliquidez": desc(cunha["iliquidez"], t),
        "instrumento": 0.0}
    REC["baseline_venda"] = lambda t: 0.0   # nada foi desembolsado em vida

    # baseline: reserva líquida — gross-up (reserva integra o espólio) + ponte
    ci_com_reserva = custos.custo_inventario(
        cen.uf, cen.patrimonio + ci.total, cen.n_herdeiros,
        cen.modalidade_inventario, regime,
        base_itcmd=base_itcmd(cen, regime) + ci.total, pct_honorarios=pct_honorarios)
    grossup = ci_com_reserva.total - ci.total
    gu_trib = ci_com_reserva.itcmd - ci.itcmd
    gu_proc = grossup - gu_trib
    ponte = custos.cunha_iliquidez(ci.total, prazo, r_bruto, spread_ponte, 1e-9)["credito_ponte"]
    E["baseline_reserva"] = lambda t: desc(ci.total + grossup + ponte, t)
    COMP["baseline_reserva"] = lambda t: {
        "tributaria": desc(ci.itcmd + gu_trib, t),
        "processual": desc(ci.honorarios + ci.emolumentos_ou_custas + ci.multa + gu_proc, t),
        "iliquidez": desc(ponte, t),
        "instrumento": 0.0}
    # a reserva permanece patrimônio do titular: recuperável integralmente
    REC["baseline_reserva"] = lambda t: ci.total

    # seguro: prêmios (antecipados) até QUITAR a apólice ou morrer, o que vier antes.
    # WL5/10/20/30: quita em N anos; WL60...WL100: quita na idade X; cobertura
    # vitalícia continua após a quitação com custo zero.
    fam, prz = produto
    p = premios.premio(cen.idade, fam, prz, cen.sexo, ci.total, cen.classe_risco)
    if p is not None and carga_premio != 1.0:
        p = {**p, "premio_anual": p["premio_anual"] * carga_premio,
             "premio_mensal": p["premio_mensal"] * carga_premio,
             "premio_mensalizado_ano": p["premio_mensalizado_ano"] * carga_premio}
    if p is not None:
        vitalicio = fam in ("WL", "WV", "WS", "WD", "MO")
        if vitalicio and prz in (5, 10, 20, 30):
            max_anos = prz
        elif vitalicio:             # WL60..WL100: quita na idade indicada
            max_anos = max(prz - cen.idade, 1)
        else:
            # TEMPORÁRIOS (TP/TM/TR): confirmado com a fonte em 11/set/2026 —
            # o número do produto é AO MESMO TEMPO o prazo de pagamento do
            # prêmio e o prazo de COBERTURA. Sobrevivendo o titular ao prazo,
            # os prêmios foram pagos e a família volta ao inventário integral:
            # é o risco de sobreviver à cobertura, mecanismo do cenário E.
            max_anos = prz
        pa = p["premio_anual"]
        # prêmio pago MENSALMENTE (prática de mercado): 12 parcelas/ano, cada
        # uma = premio_anual x fator_modal. Ver premios.vp_premios.
        def _e_seguro(t, p=p, max_anos=max_anos, vit=vitalicio, prz=prz):
            pagos = premios.vp_premios(p, r, min(t + 1, max_anos),
                                       mensal=pagamento_mensal)
            if vit or t < prz:      # cobertura vigente na data do óbito
                return pagos
            return pagos + E["baseline_venda"](t)   # cobertura expirada
        E["seguro"] = _e_seguro
        E["seguro"].info = p["chave"]
        # Cobertura vigente: o capital chega isento (CC 794) e imediato, zera as
        # três cunhas e converte-as no preço do instrumento. Cobertura expirada:
        # o titular pagou os prêmios E a família suporta as cunhas do inventário.
        def _c_seguro(t, vit=vitalicio, prz=prz):
            pagos = premios.vp_premios(p, r, min(t + 1, max_anos),
                                       mensal=pagamento_mensal)
            if vit or t < prz:
                return {**Z, "instrumento": pagos}
            base = COMP["baseline_venda"](t)
            return {**base, "instrumento": pagos}
        COMP["seguro"] = _c_seguro
        # valor de resgate: fração do capital segurado (= custo do inventário)
        REC["seguro"] = lambda t: resgate.valor_resgate(
            ci.total, fam, prz, cen.sexo, cen.idade, t)
        meta["seguro"] = {"familia": fam, "prazo": prz, "premio_anual": pa,
                          "premio_mensal": p["premio_mensal"], "p": p,
                          "max_anos": max_anos, "capital": ci.total,
                          "chave": p["chave"], "mensal": pagamento_mensal,
                          "carregamento": premios.carregamento_fracionamento(
                              fam, prz, ci.total)}

    # holding
    # CORREÇÃO (11/set/2026, auditoria): `or 1.0` colapsava fracao_empresa=0.0 em
    # 1.0, fazendo a holding ser constituída sobre 100% do patrimônio enquanto a
    # linha seguinte mandava os MESMOS 100% ao inventário — dupla contagem no
    # cenário F. Sem parcela empresarial, a holding é constituída sobre todo o
    # patrimônio apenas se não houver nada fora dela.
    frac_holding = cen.fracao_empresa if cen.fracao_empresa > 0 else 1.0
    kw_h = {}
    if holding_constituicao is not None:
        kw_h["constituicao"] = holding_constituicao
    if holding_manutencao is not None:
        kw_h["manutencao_anual"] = holding_manutencao
    h = custos.custo_holding(cen.uf, cen.patrimonio * frac_holding, 30, regime, **kw_h)
    gk_h = custos.ALIQUOTA_GK * gk_transmissao_gratuita * cen.patrimonio * frac_holding
    fora = cen.patrimonio * (1 - frac_holding)
    ci_fora = (custos.custo_inventario(cen.uf, fora, cen.n_herdeiros,
                                       cen.modalidade_inventario, regime)
               if fora > 0 else None)
    cunha_fora = (custos.cunha_iliquidez(ci_fora.total, prazo, r_bruto, spread_ponte,
                                         desagio_venda, **kw_gk)["cunha"] if ci_fora else 0)
    cunha_fora_d = (custos.cunha_iliquidez(ci_fora.total, prazo, r_bruto, spread_ponte,
                                           desagio_venda, **kw_gk) if ci_fora else None)
    E["holding"] = lambda t: (h["custo_inicial"] + gk_h
                              + sum(h["manutencao_anual"] / (1 + r) ** k for k in range(t + 1))
                              + (desc(ci_fora.total + cunha_fora, t) if ci_fora else 0))
    COMP["holding"] = lambda t: {
        "tributaria": h["itcmd_doacao"] + gk_h + (desc(ci_fora.itcmd + cunha_fora_d["tributo_gk"], t)
                                           if ci_fora else 0.0),
        "processual": (desc(ci_fora.honorarios + ci_fora.emolumentos_ou_custas + ci_fora.multa, t)
                       if ci_fora else 0.0),
        "iliquidez": (desc(cunha_fora_d["iliquidez"], t) if ci_fora else 0.0),
        "instrumento": h["constituicao"] + sum(h["manutencao_anual"] / (1 + r) ** k
                                               for k in range(t + 1))}
    REC["holding"] = lambda t: 0.0   # custo de constituição é afundado

    # doação em vida PARCIAL com reserva de usufruto. O doador NÃO pode doar
    # tudo (art. 548 CC), logo retém um resíduo que passa por inventário no
    # óbito — com ITCMD, honorários E cunha de iliquidez, como qualquer espólio.
    kw_d = {}
    if fracao_doada is not None:
        kw_d["fracao_doada"] = fracao_doada
    if pct_honor_doacao is not None:
        kw_d["pct_honorarios"] = pct_honor_doacao
    # base do ITCMD da doação com o MESMO deságio contábil aplicado ao
    # inventário e à holding no regime 2026 (correção do v5).
    frac_d = kw_d.get("fracao_doada", custos.FRACAO_DOADA_PADRAO)
    kw_d["base_itcmd"] = base_itcmd(cen, regime) * frac_d
    d = custos.custo_doacao_em_vida(cen.uf, cen.patrimonio, regime, **kw_d)
    if gk_transmissao_gratuita:
        gk_d = custos.ALIQUOTA_GK * gk_transmissao_gratuita * d["valor_doado"]
        d = {**d, "itcmd_doacao": d["itcmd_doacao"] + gk_d,
             "total_data_zero": d["total_data_zero"] + gk_d, "ir_gk_doacao": gk_d}
    residuo = d["residuo_retido"]
    if residuo > 0:
        # doação assumida PROPORCIONAL à composição do patrimônio ⚠ (o resíduo
        # mantém a mesma fração em quotas, logo o mesmo deságio de base)
        prop = residuo / cen.patrimonio
        ci_res = custos.custo_inventario(
            cen.uf, residuo, cen.n_herdeiros, cen.modalidade_inventario, regime,
            base_itcmd=base_itcmd(cen, regime) * prop, pct_honorarios=pct_honorarios)
        cunha_res_d = custos.cunha_iliquidez(ci_res.total, prazo, r_bruto, spread_ponte,
                                             desagio_venda, **kw_gk)
        cunha_res = cunha_res_d["cunha"]
        E["doacao"] = lambda t: (d["total_data_zero"]
                                 + desc(ci_res.total + cunha_res, t))
        COMP["doacao"] = lambda t: {
            "tributaria": d["itcmd_doacao"] + desc(ci_res.itcmd + cunha_res_d["tributo_gk"], t),
            "processual": d["emolumentos"] + desc(ci_res.honorarios
                                                  + ci_res.emolumentos_ou_custas
                                                  + ci_res.multa, t),
            "iliquidez": desc(cunha_res_d["iliquidez"], t),
            "instrumento": d["honorarios"]}
    else:
        E["doacao"] = lambda t: d["total_data_zero"]
        COMP["doacao"] = lambda t: {
            "tributaria": d["itcmd_doacao"], "processual": d["emolumentos"],
            "iliquidez": 0.0, "instrumento": d["honorarios"]}
    REC["doacao"] = lambda t: 0.0    # irreversível por construção jurídica
    meta["doacao"] = d

    # vgbl seletivo
    if cen.vgbl_aplicavel:
        # taxa de administração do VGBL: parâmetro de sensibilidade.
        # Baseline 1,32% a.a. — média oficial do segmento aberto (RGPC,
        # 4T2025, tab. 7.1), estável entre 1,27% e 1,37% desde 2016.
        kw_v = {} if taxa_adm_vgbl is None else {'taxa_adm_aa': taxa_adm_vgbl}
        v = custos.custo_vgbl(ci.total, 30, **kw_v)
        adm = ci.total * v["taxa_adm_aa"]
        if ir_contrafactual:
            # v4 — mundo COM impostos: o aporte capitaliza DENTRO do VGBL à
            # taxa nominal bruta menos adm, com IR regressivo só sobre o
            # rendimento e só na morte; o benchmark tributável rende líquido
            # de IR ano a ano. Custo = IOF - diferencial de acumulação: o
            # diferimento pode tornar o custo NEGATIVO (alfa tributário).
            A, pi, t_ir = ci.total, custos.INFLACAO_AA, t_ir_param
            g_nom = (1 + r_bruto) * (1 + pi) - 1
            def _e_vgbl(t, A=A, g=g_nom, pi=pi, t_ir=t_ir, v=v, rl=r):
                h = t + 0.5
                v_nom = A * (1 + g - v["taxa_adm_aa"]) ** h
                ir_morte = custos.aliquota_vgbl_regressiva(h) * max(v_nom - A, 0)
                w_nom = A * (1 + g * (1 - t_ir)) ** h
                dif_real = (v_nom - ir_morte - w_nom) / (1 + pi) ** h
                return v["iof_aportes"] - dif_real / (1 + rl) ** h
            E["vgbl"] = _e_vgbl
            def _c_vgbl(t, A=A, g=g_nom, pi=pi, t_ir=t_ir, v=v, rl=r):
                """Separa o custo do VGBL em preço do produto e efeito tributário.
                v_sem_adm = acumulação bruta sem taxa; a diferença para v_nom é o
                custo de administração (instrumento); o restante é o diferencial
                tributário do diferimento (tributária). As duas somam _e_vgbl."""
                h = t + 0.5
                disc = (1 + pi) ** h * (1 + rl) ** h
                v_sem = A * (1 + g) ** h
                v_nom = A * (1 + g - v["taxa_adm_aa"]) ** h
                ir_morte = custos.aliquota_vgbl_regressiva(h) * max(v_nom - A, 0)
                w_nom = A * (1 + g * (1 - t_ir)) ** h
                instr = (v_sem - v_nom) / disc
                trib = v["iof_aportes"] - (v_sem - ir_morte - w_nom) / disc
                return {"tributaria": trib, "processual": 0.0,
                        "iliquidez": 0.0, "instrumento": instr}
            COMP["vgbl"] = _c_vgbl
        else:
            E["vgbl"] = lambda t: v["iof_aportes"] + sum(adm / (1 + r) ** k for k in range(t + 1))
            COMP["vgbl"] = lambda t: {
                "tributaria": v["iof_aportes"], "processual": 0.0, "iliquidez": 0.0,
                "instrumento": sum(adm / (1 + r) ** k for k in range(t + 1))}
        # resgate a qualquer tempo; em termos REAIS o principal volta ~integral
        # ⚠ resgate em vida também sofreria IR sobre o rendimento (REC otimista)
        REC["vgbl"] = lambda t: ci.total
    return E, REC, ci, meta, COMP


def indice_reversibilidade(rec_fn, idade: int, sexo: str, r: float) -> float:
    """VP esperado do valor recuperável, se a necessidade de saída em vida surgir
    em um momento aleatório (uniforme) do período em que o titular está vivo.

    R = E_t[ REC(t) / (1+r)^t | vivo em t ], com t uniforme sobre a vida restante
    e ponderado pela probabilidade de sobrevivência.

    Interpretação: quanto do valor imobilizado na estratégia o titular consegue
    reaver se mudar de ideia. Dimensão em que a doação em vida vale ZERO.
    """
    q = atuarial.tabua()[sexo]
    p, num, den = 1.0, 0.0, 0.0
    for t in range(0, 121 - idade):
        num += p * rec_fn(t) / (1 + r) ** t
        den += p
        p *= 1 - q.get(idade + t, 1.0)
        if p <= 0:
            break
    return num / den if den else 0.0


def dist_seguro_com_lapso(cen, r, meta, fc_seguro, fc_baseline, lapso_aa):
    """Distribuição de custo do seguro sob caducidade com hazard constante.

    O lapso só pode ocorrer enquanto há prêmio a pagar (após a quitação não há
    incentivo a caducar). Se a apólice caduca no ano tau, o titular recupera
    VR(tau) e a FAMÍLIA volta ao inventário integral com venda forçada.

    A distribuição é construída sobre os pares (tau, t) — não sobre a média
    condicional — para que a CTE-95 enxergue o desfecho ruim (caducar e morrer
    depois sem cobertura) em vez de diluí-lo.
    """
    m = meta["seguro"]
    max_anos, cap = m["max_anos"], m["capital"]
    dist = []
    for t in range(121 - cen.idade):
        pm = atuarial.prob_morte_no_ano(cen.idade, cen.sexo, t)
        if pm <= 0:
            continue
        janela = min(t, max_anos)          # anos em que o lapso pode ocorrer
        p_sem_lapso = (1 - lapso_aa) ** janela
        for tau in range(1, janela + 1):
            p_tau = (1 - lapso_aa) ** (tau - 1) * lapso_aa
            premios_pagos = premios.vp_premios(m["p"], r, tau, mensal=m["mensal"])
            vr_t = resgate.valor_resgate(cap, m["familia"], m["prazo"],
                                         cen.sexo, cen.idade, tau)
            custo = premios_pagos - vr_t / (1 + r) ** tau + fc_baseline(t)
            dist.append((pm * p_tau, custo))
        dist.append((pm * p_sem_lapso, fc_seguro(t)))
    return dist


def avaliar(codigo: str, r=0.06, regime="2026", lapso_aa=None, **kw):
    cen = CENARIOS[codigo]
    lapso_aa = LAPSO_AA if lapso_aa is None else lapso_aa
    ests, recs, ci, meta, comps = estrategias(cen, r, regime, **kw)
    out_meta = meta
    r_d = meta.get("r_desconto", r)   # taxa líquida quando ir_contrafactual
    out = {"cenario": codigo, "custo_inventario_nominal": ci.total}
    for nome, fc in ests.items():
        com_lapso = (nome == "seguro" and lapso_aa > 0 and "seguro" in meta)
        if com_lapso:
            dist = dist_seguro_com_lapso(cen, r_d, meta, fc,
                                         ests["baseline_venda"], lapso_aa)
        else:
            dist = atuarial.distribuicao_custo(fc, cen.idade, cen.sexo, r_d)
        rec = (indice_reversibilidade(recs[nome], cen.idade, cen.sexo, r_d)
               if nome in recs else 0.0)
        ies_e, ies_cte = ies(comps.get(nome), cen, r_d, dist if com_lapso else None,
                             comps.get("baseline_venda") if com_lapso else None,
                             meta if com_lapso else None, lapso_aa)
        out[nome] = {"E": atuarial.esperanca(dist),
                     "CTE95": atuarial.cte(dist, CTE_NIVEL),
                     "REC": rec, "IES_E": ies_e, "IES_CTE": ies_cte}
    return out


PARCELAS = ("tributaria", "processual", "iliquidez", "instrumento")


def ies(comp_fn, cen, r, dist_lapso=None, comp_baseline=None, meta=None, lapso_aa=0.0):
    """Índice de Eficiência Sucessória: decompõe o custo da estratégia nas três
    cunhas de fricção e no preço do instrumento, no valor esperado e na cauda.

    Retorna (parcelas_E, parcelas_CTE), ambos dicts em R$ de valor presente.
    Por construção sum(parcelas_E.values()) == E[VP] e o mesmo vale na cauda —
    a decomposição da CTE é aditiva porque a cauda é definida pelo custo TOTAL e
    cada parcela é promediada sobre esse MESMO conjunto de desfechos.
    """
    if comp_fn is None:
        return {p: 0.0 for p in PARCELAS}, {p: 0.0 for p in PARCELAS}
    if dist_lapso is not None:                      # seguro com caducidade
        pares = _pares_lapso(cen, r, meta, comp_fn, comp_baseline, lapso_aa)
    else:
        pares = [(atuarial.prob_morte_no_ano(cen.idade, cen.sexo, t), comp_fn(t))
                 for t in range(121 - cen.idade)
                 if atuarial.prob_morte_no_ano(cen.idade, cen.sexo, t) > 0]
    tot = sum(p for p, _ in pares)
    esp = {k: sum(p * c[k] for p, c in pares) / tot for k in PARCELAS}
    # cauda: ordena pelo custo TOTAL e promedia cada parcela no mesmo conjunto
    ordenado = sorted(pares, key=lambda x: sum(x[1].values()), reverse=True)
    alvo, acum = (1 - CTE_NIVEL) * tot, 0.0
    soma = {k: 0.0 for k in PARCELAS}
    for p, c in ordenado:
        usa = min(p, alvo - acum)
        for k in PARCELAS:
            soma[k] += usa * c[k]
        acum += usa
        if acum >= alvo:
            break
    cauda = {k: (v / alvo if alvo > 0 else 0.0) for k, v in soma.items()}
    return esp, cauda


def _pares_lapso(cen, r, meta, comp_seg, comp_base, lapso_aa):
    """Pares (prob, parcelas) do seguro sob caducidade. Caducando em tau, o que
    foi pago em prêmios menos o resgate segue sendo preço do instrumento, e a
    família volta a suportar as cunhas do inventário."""
    m = meta["seguro"]
    max_anos, cap = m["max_anos"], m["capital"]
    pares = []
    for t in range(121 - cen.idade):
        pm = atuarial.prob_morte_no_ano(cen.idade, cen.sexo, t)
        if pm <= 0:
            continue
        janela = min(t, max_anos)
        pares.append((pm * (1 - lapso_aa) ** janela, comp_seg(t)))
        for tau in range(1, janela + 1):
            p_tau = (1 - lapso_aa) ** (tau - 1) * lapso_aa
            pagos = premios.vp_premios(m["p"], r, tau, mensal=m["mensal"])
            vr = resgate.valor_resgate(cap, m["familia"], m["prazo"],
                                       cen.sexo, cen.idade, tau)
            base = comp_base(t)
            c = dict(base)
            c["instrumento"] = base["instrumento"] + pagos - vr / (1 + r) ** tau
            pares.append((pm * p_tau, c))
    return pares


def pareto(res: dict, com_reversibilidade: bool = False) -> list[str]:
    """Estratégias não dominadas. Custos (E, CTE95) minimizam; REC maximiza.

    com_reversibilidade=False reproduz o critério do v1 (2 dimensões).
    """
    ests = {k: v for k, v in res.items() if isinstance(v, dict)}
    def vetor(v):
        return ((v["E"], v["CTE95"], -v.get("REC", 0.0)) if com_reversibilidade
                else (v["E"], v["CTE95"]))
    nd = []
    for a, va in ests.items():
        A = vetor(va)
        dominada = any(
            all(x <= y for x, y in zip(vetor(vb), A))
            and any(x < y for x, y in zip(vetor(vb), A))
            for b, vb in ests.items() if b != a)
        if not dominada:
            nd.append(a)
    return nd


def rodar(r=0.06, regime="2026", **kw):
    return [avaliar(c, r, regime, **kw) for c in CENARIOS if c != "G"]


def salvar_csv(resultados, caminho):
    with open(caminho, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "estrategia", "vp_esperado", "cte95", "reversibilidade"]
                   + [f"ies_e_{p}" for p in PARCELAS]
                   + [f"ies_cte_{p}" for p in PARCELAS]
                   + ["pareto_2d", "pareto_3d"])
        for res in resultados:
            p2, p3 = pareto(res), pareto(res, com_reversibilidade=True)
            for nome, v in res.items():
                if isinstance(v, dict):
                    e_i = v.get("IES_E", {p: 0.0 for p in PARCELAS})
                    c_i = v.get("IES_CTE", {p: 0.0 for p in PARCELAS})
                    w.writerow([res["cenario"], nome, round(v["E"], 2),
                                round(v["CTE95"], 2), round(v.get("REC", 0.0), 2)]
                               + [round(e_i[p], 2) for p in PARCELAS]
                               + [round(c_i[p], 2) for p in PARCELAS]
                               + [int(nome in p2), int(nome in p3)])


if __name__ == "__main__":
    import sys as _s
    lapso = float(_s.argv[1]) if len(_s.argv) > 1 else LAPSO_AA
    for regime in ("2026", "pos2027"):
        print(f"\n===== Regime {regime} | r = 6% real | BR-EMS mt 2026 "
              f"| lapso {lapso:.1%} a.a. =====")
        for res in rodar(regime=regime, lapso_aa=lapso):
            print(f"\nCenário {res['cenario']} (inventário nominal "
                  f"R$ {res['custo_inventario_nominal']:,.0f})")
            print(f"  {'estratégia':18} {'E[VP]':>13} {'CTE-95':>13} {'REVERSÍVEL':>13}")
            for nome, v in res.items():
                if isinstance(v, dict):
                    print(f"  {nome:18} {v['E']:>13,.0f} {v['CTE95']:>13,.0f} "
                          f"{v.get('REC', 0):>13,.0f}")
            print(f"  → Pareto 2D (E, CTE):        {', '.join(pareto(res))}")
            print(f"  → Pareto 3D (+ reversibil.): "
                  f"{', '.join(pareto(res, com_reversibilidade=True))}")
