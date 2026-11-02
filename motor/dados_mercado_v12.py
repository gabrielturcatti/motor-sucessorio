"""Dados de mercado da seção 4 (v12): VGBL e seguro de vida individual.

Fontes públicas, baixadas à parte (não versionadas por tamanho):
  - SUSEP, Sistema de Estatísticas (SES), base completa (BaseCompleta.zip):
    https://www2.susep.gov.br/menuestatistica/SES/principal.aspx
    arquivos usados: Ses_seguros.csv, Ses_Contrib_Benef.csv, Ses_vgbl_resgates.csv
  - IBGE, SIDRA, tabela 1737 (IPCA, número-índice), em JSON:
    https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/all?formato=json

Uso: python3 dados_mercado_v12.py <pasta com os CSVs da SES> <ipca.json>
Grava resultados/v12_susep_vida_individual.csv e resultados/v12_susep_vgbl.csv.

Definições: vida individual = ramo 1391 (grupo 13, Pessoas Individual; ramo 91, Vida),
prêmio direto e despesas de comercialização; vida em grupo = ramo 0993 (comparação).
VGBL = contribuições (tipoProd == "VGBL") e resgates totais, parciais e pagamentos
programados. Valores reais em R$ de 2025, deflacionados pela média anual do IPCA.
"""
import json, os, sys
import pandas as pd

SES, IPCA = sys.argv[1], sys.argv[2]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")

j = json.load(open(IPCA))[1:]
ipca = pd.Series({int(x["D3C"]): float(x["V"]) for x in j if x["V"] not in ("...", "-")})
media = ipca.groupby(ipca.index // 100).mean()

s = pd.read_csv(os.path.join(SES, "Ses_seguros.csv"), sep=";", decimal=",",
                dtype={"coramo": str, "coenti": str},
                usecols=["damesano", "coenti", "coramo", "premio_direto", "desp_com"])
s["ano"] = s.damesano // 100
v = s[s.coramo == "1391"]
vi = v.groupby("ano")[["premio_direto", "desp_com"]].sum().loc[2015:2025]
f = media.loc[2025] / media.loc[2015:2025]
vi["premio_real25"] = vi.premio_direto * f
vi["desp_real25"] = vi.desp_com * f
vi["razao_desp_premio"] = vi.desp_com / vi.premio_direto
cia = v.groupby(["ano", "coenti"]).premio_direto.sum()
vi["n_cias"] = (cia > 0).groupby(level=0).sum().loc[2015:2025]
g = s[s.coramo == "0993"].groupby("ano")[["premio_direto", "desp_com"]].sum()
vi["razao_desp_premio_vida_grupo"] = (g.desp_com / g.premio_direto).loc[2015:2025]
vi.to_csv(os.path.join(OUT, "v12_susep_vida_individual.csv"))

ja = lambda y: ipca[[y * 100 + m for m in range(1, 9)]].mean()
jv = v[v.damesano % 100 <= 8].groupby("ano").premio_direto.sum()
print("vida individual jan-ago 2026/2025: nominal",
      round(jv[2026] / jv[2025] - 1, 4), "real", round(jv[2026] / jv[2025] / (ja(2026) / ja(2025)) - 1, 4))

c = pd.read_csv(os.path.join(SES, "Ses_Contrib_Benef.csv"), sep=";", decimal=",", dtype={"coenti": str})
c = c[c.tipoProd == "VGBL"]
r = pd.read_csv(os.path.join(SES, "Ses_vgbl_resgates.csv"), sep=";", decimal=",", dtype={"coenti": str})
r["tot"] = r.resg_total + r.resg_parcial + r.Resg_Pag_programado
t = pd.DataFrame({"contrib": c.groupby(c.damesano // 100).contrib.sum(),
                  "resg": r.groupby(r.damesano // 100).tot.sum()}).loc[2019:] / 1e9
t["liq"] = t.contrib - t.resg
t.to_csv(os.path.join(OUT, "v12_susep_vgbl.csv"))
mensal = c[c.damesano >= 202501].groupby("damesano").contrib.sum() / 1e9
print("VGBL, aportes mensais (R$ bi):")
print(mensal.round(1).to_string())
print(vi.round(3).to_string())
print(t.round(1).to_string())
