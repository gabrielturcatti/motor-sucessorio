"""Módulo de custos sucessórios (lado "fricção") — regimes 2026 e pós-2027.

Fontes e pendências: ver parametros/parametros_sucessorios.md.
⚠ marca simplificações a validar antes da redação final.
"""
from __future__ import annotations
from dataclasses import dataclass, field

UPF_RS_2026 = 28.3264      # ⚠ confirmar na Receita Estadual RS
UFESP_2026 = 38.42

# ---------------------------------------------------------------- ITCMD

def itcmd_rs(quinhao: float, marginal: bool = True) -> float:
    """RS (Lei 8.821/89), progressivo por quinhão, faixas em UPF-RS.
    ⚠ Implementado como progressividade MARGINAL (por parcela); confirmar se a
    Receita RS aplica por parcela ou alíquota única da faixa sobre o total."""
    faixas = [(0, 2000, 0.00), (2000, 10000, 0.03), (10000, 20000, 0.04),
              (20000, 40000, 0.05), (40000, float("inf"), 0.06)]
    q_upf = quinhao / UPF_RS_2026
    if marginal:
        total = sum((min(q_upf, hi) - lo) * ali for lo, hi, ali in faixas if q_upf > lo)
        return total * UPF_RS_2026
    for lo, hi, ali in faixas:
        if lo <= q_upf < hi:
            return quinhao * ali
    return quinhao * 0.06


def itcmd_sp(base: float, regime: str = "2026") -> float:
    """SP: 4% fixo em 2026. Regime 'pos2027': faixas do PL 7/2024 (2%–8%).
    ⚠ Faixas pós-2027 são PROPOSTA legislativa, não lei — usar só como sensibilidade."""
    if regime == "2026":
        return base * 0.04
    faixas = [(0, 10_000 * UFESP_2026, 0.02),          # ⚠ placeholder das faixas do PL
              (10_000 * UFESP_2026, 85_000 * UFESP_2026, 0.04),
              (85_000 * UFESP_2026, 280_000 * UFESP_2026, 0.06),
              (280_000 * UFESP_2026, float("inf"), 0.08)]
    return sum((min(base, hi) - lo) * ali for lo, hi, ali in faixas if base > lo)


def itcmd(uf: str, base: float, regime: str = "2026", n_herdeiros: int = 1) -> float:
    """ITCMD total. RS tributa por QUINHÃO (divide por herdeiro); SP por base."""
    if uf == "RS":
        q = base / max(n_herdeiros, 1)
        return itcmd_rs(q) * max(n_herdeiros, 1)
    return itcmd_sp(base, regime)


# ------------------------------------------------- demais custos de inventário

def honorarios(monte: float, modalidade: str = "extrajudicial",
               pct_override: float | None = None) -> float:
    """Tabelas OAB (pisos): extrajudicial 6%, judicial 8%, litígio 10%.
    pct_override para sensibilidade (grandes patrimônios negociam abaixo do piso)."""
    pct = pct_override if pct_override is not None else \
        {"extrajudicial": 0.06, "judicial": 0.08, "litigio": 0.10}[modalidade]
    minimo = {"extrajudicial": 5862.39, "judicial": 8207.34, "litigio": 8207.34}[modalidade]
    return max(monte * pct, minimo)


def emolumentos_extrajudicial(uf: str, monte: float) -> float:
    """Escritura de inventário. RS: teto R$ 5.179,40 (TJRS 2026).
    SP: aproximação com teto ⚠ (extrair faixas exatas da tabela CNB/SP)."""
    if uf == "RS":
        return min(210.50 + monte * 0.006, 5179.40)
    return min(1000 + monte * 0.008, 12000.0)  # ⚠ SP aproximado


def taxa_judiciaria(uf: str, monte: float) -> float:
    """Inventário judicial. SP: tabela própria em UFESPs (Lei 17.785/2023).
    RS: ⚠ pendente — aproximado por 0,5% com teto R$ 20 mil."""
    if uf == "SP":
        if monte <= 50_000: return 10 * UFESP_2026
        if monte <= 500_000: return 100 * UFESP_2026
        if monte <= 2_000_000: return 300 * UFESP_2026
        return 1000 * UFESP_2026  # ⚠ faixa superior a confirmar
    return min(monte * 0.005, 20_000.0)  # ⚠ RS aproximado


def multa_atraso(valor_itcmd: float, meses_atraso: float = 0) -> float:
    """10% do ITCMD (>60 dias), 20% (>180 dias). SP e RS."""
    if meses_atraso <= 2: return 0.0
    return valor_itcmd * (0.20 if meses_atraso > 6 else 0.10)


@dataclass
class CustoInventario:
    itcmd: float
    honorarios: float
    emolumentos_ou_custas: float
    multa: float = 0.0
    total: float = field(init=False)
    def __post_init__(self):
        self.total = self.itcmd + self.honorarios + self.emolumentos_ou_custas + self.multa


def custo_inventario(uf: str, monte_mor: float, n_herdeiros: int,
                     modalidade: str = "extrajudicial", regime: str = "2026",
                     meses_atraso: float = 0, pct_honorarios: float | None = None,
                     base_itcmd: float | None = None) -> CustoInventario:
    """Custo total do inventário. base_itcmd permite base ≠ monte-mor
    (ex.: quotas a valor contábil no regime 2026 vs. mercado no pós-2027)."""
    base = base_itcmd if base_itcmd is not None else monte_mor
    v_itcmd = itcmd(uf, base, regime, n_herdeiros)
    h = honorarios(monte_mor, modalidade, pct_honorarios)
    e = (emolumentos_extrajudicial(uf, monte_mor) if modalidade == "extrajudicial"
         else taxa_judiciaria(uf, monte_mor))
    m = multa_atraso(v_itcmd, meses_atraso)
    return CustoInventario(v_itcmd, h, e, m)


# ------------------------------------------------------------------ holding

def custo_holding(uf: str, valor_patrimonio: float, anos_ate_obito: float,
                  regime: str = "2026",
                  constituicao: float = 25_000.0,       # ⚠ validar com prática
                  manutencao_anual: float = 18_000.0,   # ⚠ contabilidade+obrigações
                  desagio_contabil: float = 0.40) -> dict:
    """Estratégia holding: doação de quotas com reserva de usufruto em vida.
    Regime 2026: base = valor patrimonial CONTÁBIL (deságio vs. mercado).
    Pós-2027 (LC 227/26): base = PL ajustado a valor de MERCADO (deságio morre).
    ⚠ Extinção de usufruto sem novo ITCMD assumida (verificar por estado)."""
    base = valor_patrimonio * (1 - (desagio_contabil if regime == "2026" else 0.0))
    # CORREÇÃO (11/set/2026, auditoria): a transferência de quotas à holding é
    # DOAÇÃO, e deve usar a tabela de doação — a mesma aplicada à estratégia de
    # doação em vida. A versão anterior usava a tabela causa mortis com um único
    # quinhão, o que cobrava ~1,5x mais da holding pelo mesmo ato jurídico e a
    # penalizava por escolha de função, não por economia.
    v_itcmd = itcmd_doacao(uf, base, regime)
    return {"itcmd_doacao": v_itcmd, "constituicao": constituicao,
            "manutencao_anual": manutencao_anual,
            "custo_inicial": v_itcmd + constituicao}


# ------------------------------------------------------------ doação em vida

def itcmd_doacao(uf: str, valor: float, regime: str = "2026") -> float:
    """RS: 3% até 10.000 UPF, 4% acima (⚠ confirmar faixas); SP: 4% com isenção
    anual de R$ 96.050 por par doador-donatário."""
    if uf == "RS":
        lim = 10_000 * UPF_RS_2026
        return valor * 0.03 if valor <= lim else lim * 0.03 + (valor - lim) * 0.04
    if regime == "2026":
        return max(valor - 96_050, 0) * 0.04
    return itcmd_sp(valor, "pos2027")   # pós-2027: progressivo + consolidação


FRACAO_DOADA_PADRAO = 0.50      # reserva de subsistência (art. 548 CC)
PCT_HONORARIOS_DOACAO = 0.015   # ⚠ estruturação/escrituras; NÃO é ad valorem 6%


def custo_doacao_em_vida(uf: str, valor_patrimonio: float, regime: str = "2026",
                         fracao_doada: float = FRACAO_DOADA_PADRAO,
                         pct_honorarios: float = PCT_HONORARIOS_DOACAO,
                         n_parcelas_anuais: int = 1,
                         base_tributavel_usufruto: float = 1.0,
                         base_itcmd: float | None = None) -> dict:
    """Doação em vida com reserva de usufruto, na data zero.

    LIMITE JURÍDICO (art. 548 do Código Civil): é NULA a doação de todos os bens
    sem reserva de parte, ou de renda suficiente para a subsistência do doador.
    Por isso `fracao_doada` < 1 não é conservadorismo — é condição de validade.
    O v1/v2 do motor doava 100% na data zero, o que superestimava a estratégia e
    modelava um ato juridicamente inexistente.

    `pct_honorarios`: a doação NÃO escapa de custo advocatício, mas também não
    paga o piso ad valorem de 6% da tabela da OAB aplicável ao inventário — é
    honorário de estruturação, contratado. Parâmetro de sensibilidade.

    `base_tributavel_usufruto`: fração do valor doado tributada JÁ na doação.
    1,0 = tudo na doação (conservador). Estados que tributam a nua-propriedade
    e diferem o restante para a extinção do usufruto pedem valor menor.
    ⚠ Verificar o tratamento por estado antes da redação final.

    O resíduo retido pelo doador (1 − fracao_doada) NÃO é tratado aqui: ele
    passa por inventário no óbito e é somado pelo motor.

    Regime 2026: parcelas anuais tratadas isoladamente (isenção/faixa renova).
    Pós-2027 (LC 227/26): doações sucessivas CONSOLIDADAS → parcelar não ajuda.
    """
    doado = valor_patrimonio * fracao_doada
    # `base_itcmd`: base de cálculo do ITCMD sobre o valor DOADO. No regime 2026
    # as quotas entram por valor contábil (deságio), exatamente como no
    # inventário e na holding — a v4 não aplicava esse deságio à doação, o que a
    # sobretributava em relação às demais estratégias. Corrigido no v5.
    # No pós-2027 (LC 227/2026) a base é o valor de mercado e os dois coincidem.
    base_bruta = doado if base_itcmd is None else base_itcmd
    base = base_bruta * base_tributavel_usufruto
    if regime == "2026" and n_parcelas_anuais > 1:
        parcela = base / n_parcelas_anuais
        tributo = sum(itcmd_doacao(uf, parcela, regime) for _ in range(n_parcelas_anuais))
    else:
        tributo = itcmd_doacao(uf, base, regime)
    # escritura de doação ~ mesma tabela de emolumentos ⚠; sem doação, sem escritura
    emol = emolumentos_extrajudicial(uf, doado) if doado > 0 else 0.0
    honor = doado * pct_honorarios
    return {"itcmd_doacao": tributo, "emolumentos": emol, "honorarios": honor,
            "valor_doado": doado, "residuo_retido": valor_patrimonio - doado,
            "total_data_zero": tributo + emol + honor}


# ------------------------------------------------------------ cunha de iliquidez

ALIQUOTA_GK = 0.15          # ganho de capital, pessoa física (regra geral)
PLUSVALIA_LATENTE = 0.0     # fração do valor do ativo que é ganho acumulado.
                            # 0 = comportamento do v4 (sem GK). v5 usa 0,30-0,50
                            # como sensibilidade; ver rodar_v5.py.


def cunha_iliquidez(custo_exigivel: float, prazo_meses: float, r_real: float,
                    spread_ponte: float = 0.06, desagio_venda: float = 0.25,
                    plusvalia: float = PLUSVALIA_LATENTE,
                    aliquota_gk: float = ALIQUOTA_GK) -> dict:
    """Custo de FINANCIAR o custo sucessório com ativos bloqueados.

    (a) crédito-ponte: juros (r+spread) sobre o exigível pelo prazo do inventário;
    (b) venda forçada: é preciso vender um bruto G que cubra o exigível DEPOIS do
        deságio de liquidez d E do imposto sobre o ganho realizado:
            G*(1-d) - G*plusvalia*aliq = custo   →   G = custo / (1 - d - p*a)
        A perda total é G - custo, separável em deságio e tributo — separação
        necessária para o IES, que classifica o deságio como cunha de iliquidez
        e o imposto sobre o ganho como cunha tributária.

    O capital de seguro não passa por nenhum dos dois caminhos (chega líquido e
    isento, CC art. 794), e por isso zera esta cunha na estratégia segurada.
    A família escolhe o caminho mais barato; retorna os componentes e o mínimo.
    """
    t = prazo_meses / 12
    # CORREÇÃO (11/set/2026, auditoria): o crédito-ponte não custa a taxa cheia.
    # Tomando o empréstimo, a família paga CI*(1+r+spread)^t em t+prazo em vez de
    # CI na data do óbito — e, nesse intervalo, o próprio dinheiro dela rende r.
    # O custo econômico é, portanto, o EXCESSO sobre o custo de oportunidade:
    #     CI * [ ((1+r+spread)/(1+r))^t - 1 ]  ≈  CI * spread * t
    # A fórmula anterior cobrava CI*((1+r+spread)^t - 1), superestimando a cunha
    # em ~2,1x nas premissas do caso base — viés PRÓ-seguro, pois a cunha é a
    # única fricção que o capital segurado neutraliza e que os instrumentos
    # concorrentes suportam.
    ponte = custo_exigivel * (((1 + r_real + spread_ponte) / (1 + r_real)) ** t - 1)
    denom = 1 - desagio_venda - plusvalia * aliquota_gk
    if denom <= 0:                      # deságio + tributo inviabilizam a venda
        venda_total, venda_desagio, venda_gk = float("inf"), float("inf"), 0.0
    else:
        bruto = custo_exigivel / denom
        venda_total = bruto - custo_exigivel
        venda_gk = bruto * plusvalia * aliquota_gk
        venda_desagio = venda_total - venda_gk
    usa_venda = venda_total < ponte
    return {"credito_ponte": ponte,
            "venda_forcada": venda_total,
            "venda_desagio": venda_desagio if usa_venda else 0.0,
            "venda_gk": venda_gk if usa_venda else 0.0,
            "cunha": min(ponte, venda_total),
            # decomposição do MÍNIMO escolhido, para o IES:
            "iliquidez": (venda_desagio if usa_venda else ponte),
            "tributo_gk": (venda_gk if usa_venda else 0.0)}


PRAZO_INVENTARIO_MESES = {"extrajudicial": 6, "judicial": 21}   # CNJ/estimativas 2026


# ------------------------------------ tributação do contrafactual (v4, 29/ago)

ALIQUOTA_IR_RF = 0.15   # ⚠ renda fixa >720 dias (tabela regressiva); confirmar
                        #   legislação vigente em 2026 antes da redação final
INFLACAO_AA = 0.04      # ⚠ expectativa de inflação; parâmetro de sensibilidade


def taxa_real_liquida(r_real_bruto: float, inflacao: float = INFLACAO_AA,
                      aliquota_ir: float = ALIQUOTA_IR_RF) -> float:
    """Taxa real LÍQUIDA de IR do investimento contrafactual (renda fixa
    tributável). O IR incide sobre o rendimento NOMINAL — a inflação é
    tributada junto:
        i_nom = (1+r)(1+pi) - 1
        r_liq = (1 + i_nom*(1-t)) / (1+pi) - 1
    Com r=6% real, pi=4% e t=15%: r_liq ~ 4,5% a.a. O contrafactual da
    família rende bem menos que a taxa bruta de referência (NTN-B).
    Aproximação: tributação anual do rendimento ⚠ (títulos levados ao
    vencimento diferem o IR; o contrafactual verdadeiro fica entre os dois)."""
    i_nom = (1 + r_real_bruto) * (1 + inflacao) - 1
    return (1 + i_nom * (1 - aliquota_ir)) / (1 + inflacao) - 1


def aliquota_vgbl_regressiva(anos: float) -> float:
    """Tabela regressiva do VGBL — IR só sobre o RENDIMENTO, no resgate ou na
    morte: 35% até 2 anos, caindo 5 p.p. a cada 2, piso de 10% acima de 10."""
    for lim, a in ((2, 0.35), (4, 0.30), (6, 0.25), (8, 0.20), (10, 0.15)):
        if anos <= lim:
            return a
    return 0.10


# --------------------------------------------------------------------- VGBL

def custo_vgbl(aporte_total: float, anos_ate_obito: float,
               taxa_adm_aa: float = 0.0132,      # média oficial EAPC: RGPC 4T2025, tab. 7.1
               aporte_por_ano: float | None = None) -> dict:
    """VGBL como veículo sucessório (Tema 1214: sem ITCMD, sem inventário).
    Custo = IOF 5% sobre aportes > R$ 600 mil/ano (Dec. 12.499/2025) + taxa de adm."""
    aporte_ano = aporte_por_ano or aporte_total
    excesso = max(aporte_ano - 600_000, 0)
    iof = excesso * 0.05 * (aporte_total / aporte_ano if aporte_ano else 1)
    return {"iof_aportes": iof, "taxa_adm_aa": taxa_adm_aa,
            "custo_adm_aprox_total": aporte_total * taxa_adm_aa * anos_ate_obito}
