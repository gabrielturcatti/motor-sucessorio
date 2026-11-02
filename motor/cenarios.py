"""Cenários da modelagem — 4 base (A–D) + 3 desfavoráveis (E–G).

Definições fechadas em 26/jun/2026 (ver memória do projeto). Idades default
serão variadas na análise de sensibilidade (40/50/60/70).
"""
from dataclasses import dataclass, field


@dataclass
class Cenario:
    codigo: str
    descricao: str
    patrimonio: float
    uf: str
    n_herdeiros: int
    idade: int = 50
    sexo: str = "M"
    holding_previa: bool = False
    modalidade_inventario: str = "extrajudicial"   # consenso → extrajudicial
    fracao_empresa: float = 0.0    # parte do patrimônio em quotas (afeta base ITCMD)
    vgbl_aplicavel: bool = False   # VGBL entra na comparação neste cenário
    classe_risco: str = "Standard"
    obs: str = ""


CENARIOS: dict[str, Cenario] = {c.codigo: c for c in [
    Cenario("A", "R$ 5 mi, RS, comunhão parcial, 2 filhos, sem holding",
            5_000_000, "RS", 2, fracao_empresa=0.5),
    Cenario("B", "R$ 30 mi, SP, separação total, 3 filhos, holding constituída",
            30_000_000, "SP", 3, holding_previa=True, fracao_empresa=0.6,
            vgbl_aplicavel=True),
    Cenario("C", "R$ 120 mi, SP, divorciado, filhos de uniões diferentes, holding parcial",
            120_000_000, "SP", 4, modalidade_inventario="judicial",
            fracao_empresa=0.7, obs="litígio provável → judicial"),
    Cenario("D", "R$ 350 mi, RS, comunhão universal, 2 filhos, sócio externo, sem holding",
            350_000_000, "RS", 2, fracao_empresa=0.8),
    # AGRAVO IMPLEMENTADO (11/set/2026). Até a v7 este cenário — declarado como
    # DESFAVORÁVEL ao seguro — rodava em classe Standard, o que o favorecia
    # indevidamente. A classe C representa agravo significativo (+31,8% sobre o
    # prêmio Standard aos 70) sem ser o teto de aceitação; a escada completa
    # Standard → D1 entra como sensibilidade. Classes além de D1 NÃO EXISTEM
    # para vitalícios em idade alguma: WL10 vai até D1, e WL20/WL30 só aceitam
    # Standard. A escada completa (até H2) só existe nos temporários, que por
    # sua vez expiram aos 65 (TP10) e aos 55 (TP20) — é a conjunção dos dois
    # limites que define a inacessibilidade que o cenário isola.
    Cenario("E", "Contratabilidade: ~70 anos com agravo, R$ 8–10 mi",
            9_000_000, "RS", 2, idade=70, classe_risco="C",
            fracao_empresa=0.5,
            obs="prêmio agravado (classe C); escada Standard→D1 em sensibilidade"),
    Cenario("F", "Fricção baixa: ~R$ 1 mi financeiro, herdeiros em consenso",
            1_000_000, "RS", 2, fracao_empresa=0.0, vgbl_aplicavel=True,
            obs="fricção existe mas é pequena (Lei 6.858/80 na margem)"),
    Cenario("G", "Sem motivo de legado: casal ~50-55, exit planejado, sem herdeiros",
            20_000_000, "SP", 0, idade=52,
            obs="demanda por seguro = 0 (Yaari); instrumento racional = anuidade"),
]}
