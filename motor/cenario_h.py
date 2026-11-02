"""Cenário H — acordo de sócios e apuração de haveres (perspectiva da EMPRESA).

Diferentemente de A–G, construídos da perspectiva da família, aqui o agente é a
sociedade. Falecendo um sócio, seus herdeiros em regra não ingressam no quadro
societário (CC, arts. 1.028 a 1.031) e a sociedade deve liquidar-lhes em dinheiro
a participação do falecido — os haveres.

ESTRUTURA DA COMPARAÇÃO
Nos dois arranjos os sócios remanescentes terminam com a MESMA participação
adquirida; o que difere é o desembolso que a produz:
  baseline : a sociedade paga os haveres H com recursos próprios, acrescidos da
             cunha de iliquidez de levantar caixa na data incerta do óbito;
  seguro   : apólices sobre a vida de cada sócio (entity purchase) custeiam H, e
             o desembolso resume-se aos prêmios.
Como a participação adquirida é idêntica nos dois casos, ela se cancela e
confrontar (H + Λ) contra o valor presente dos prêmios é a comparação correta.

HORIZONTE — por que NÃO se modela apenas a primeira morte
Uma versão anterior truncava a análise no primeiro óbito. Isso cobrava prêmios
de N apólices contra um único pagamento e superestimava o custo do seguro em
cerca de N vezes — artefato do recorte, não característica do instrumento. O
arranjo, na prática, permanece em vigor e todas as apólices acabam pagando. Aqui
o custo é somado sobre TODOS os sócios: para cada um, a sociedade deve H no ano
de seu óbito e paga prêmios sobre a respectiva apólice. Como as vidas são
independentes e os custos aditivos, o valor esperado é exato (soma das
esperanças individuais). Apenas a métrica de CAUDA exige a distribuição
conjunta, obtida por simulação de Monte Carlo com semente fixa — recurso
numérico para integrar uma distribuição discreta de N dimensões, não estimação
estatística.

PARCELAMENTO CONTRATUAL
O contrato social costuma prever pagamento dos haveres em parcelas. Não reduz o
principal, mas reduz o CHOQUE de caixa: a cunha incide sobre a primeira parcela.
É mitigação barata disponível SEM seguro, e incluí-la evita viés pró-seguro.

PRODUTOS TEMPORÁRIOS
Cobrem apenas o prazo contratado: se o óbito ocorre depois da expiração, os
prêmios foram pagos e a sociedade volta a suportar os haveres integralmente —
o risco de sobreviver à cobertura, o mesmo mecanismo isolado no cenário E.

⚠ LIMITAÇÕES: o litígio sobre o critério de avaliação dos haveres não é
monetizado (cunha processual = 0), embora seja fonte reconhecida de disputa;
participações iguais; não se modela a reposição de apólices após cada óbito.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import random
import atuarial, custos, premios, resgate

SEMENTE = 20260911
N_SIM = 40_000


@dataclass
class SociedadeH:
    idades: tuple = (45, 48, 52, 56, 60)
    sexos: tuple = ("M", "M", "M", "F", "M")
    valor_firma: float = 10_000_000.0
    uf: str = "RS"
    parcelas: int = 4
    produto: tuple = ("WL", 20)
    n_socios: int = field(init=False)
    haveres: float = field(init=False)

    def __post_init__(self):
        self.n_socios = len(self.idades)
        self.haveres = self.valor_firma / self.n_socios


def _dist_individual(idade: int, sexo: str) -> list[tuple[float, int]]:
    return [(atuarial.prob_morte_no_ano(idade, sexo, t), t)
            for t in range(121 - idade)
            if atuarial.prob_morte_no_ano(idade, sexo, t) > 0]


def dist_primeira_morte(soc: SociedadeH) -> list[tuple[float, int]]:
    """Distribuição do PRIMEIRO óbito — estatística descritiva do choque inicial,
    não a base do cálculo de custo."""
    q = atuarial.tabua()
    horizonte = 121 - min(soc.idades)
    dist, s_ant = [], 1.0
    for t in range(horizonte):
        s = 1.0
        for idade, sexo in zip(soc.idades, soc.sexos):
            p = 1.0
            for k in range(t):
                p *= 1 - q[sexo].get(idade + k, 1.0)
            s *= p
        if t > 0:
            dist.append((s_ant - s, t - 1))
        s_ant = s
    if s_ant > 1e-12:
        dist.append((s_ant, horizonte - 1))
    return [(p, t) for p, t in dist if p > 0]


def avaliar_h(soc: SociedadeH | None = None, r: float = 0.06,
              ir_contrafactual: bool = True, spread_ponte: float = 0.06,
              desagio_venda: float = 0.25, plusvalia: float = 0.0,
              n_sim: int = N_SIM) -> dict:
    soc = soc or SociedadeH()
    r_bruto = r
    if ir_contrafactual:
        r = custos.taxa_real_liquida(r_bruto)
    H = soc.haveres
    fam, prz = soc.produto
    vitalicio = fam in ("WL", "WV", "WS", "WD", "MO")

    choque = H / max(soc.parcelas, 1)
    cunha = custos.cunha_iliquidez(choque, 6, r_bruto, spread_ponte,
                                   desagio_venda, plusvalia=plusvalia)
    desc = lambda v, t: v / (1 + r) ** (t + 0.5)

    apolices = []
    for idade, sexo in zip(soc.idades, soc.sexos):
        p = premios.premio(idade, fam, prz, sexo, H, "Standard")
        if p is None or p["premio_anual"] <= 0:
            return {"erro": f"produto {fam}{prz} indisponível para {sexo}{idade}"}
        apolices.append(p)

    def custo_base(t):
        return desc(H + cunha["cunha"], t)

    def custo_seg(i, idade, sexo, t):
        pagos = premios.vp_premios(apolices[i], r, min(t + 1, prz), mensal=True)
        if vitalicio:
            return pagos            # capital isento cobre H integralmente
        return pagos + (custo_base(t) if t >= prz else 0.0)

    # ---- valor esperado: exato, por aditividade
    e_base = e_seg = 0.0
    dists = []
    for i, (idade, sexo) in enumerate(zip(soc.idades, soc.sexos)):
        d = _dist_individual(idade, sexo)
        dists.append(d)
        e_base += sum(p * custo_base(t) for p, t in d)
        e_seg += sum(p * custo_seg(i, idade, sexo, t) for p, t in d)

    # ---- cauda: Monte Carlo sobre a distribuição conjunta
    rng = random.Random(SEMENTE)
    acum = []
    for d in dists:
        c, tot = [], 0.0
        for p, t in d:
            tot += p; c.append((tot, t))
        acum.append(c)

    def sorteia(c):
        u = rng.random()
        for tot, t in c:
            if u <= tot: return t
        return c[-1][1]

    sim_b, sim_s = [], []
    for _ in range(n_sim):
        tb = ts = 0.0
        for i, (idade, sexo) in enumerate(zip(soc.idades, soc.sexos)):
            t = sorteia(acum[i])
            tb += custo_base(t); ts += custo_seg(i, idade, sexo, t)
        sim_b.append(tb); sim_s.append(ts)
    def cte(v, nivel=0.95):
        v = sorted(v, reverse=True); k = max(1, int(round((1 - nivel) * len(v))))
        return sum(v[:k]) / k

    d1 = dist_primeira_morte(soc)
    return {"cenario": "H", "haveres": H, "n_socios": soc.n_socios,
            "primeira_morte_esperada": sum(p * t for p, t in d1),
            "baseline_haveres": {"E": e_base, "CTE95": cte(sim_b), "REC": 0.0},
            "seguro_buysell": {"E": e_seg, "CTE95": cte(sim_s), "REC": 0.0}}
