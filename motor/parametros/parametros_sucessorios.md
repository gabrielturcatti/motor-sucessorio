# Parâmetros públicos do custo sucessório — levantamento 08/jul/2026

Insumos do motor de cálculo (lado "custo do inventário/instrumentos"). Cada bloco traz valor,
base legal e fonte. Itens marcados ⚠ exigem verificação na fonte primária antes da redação final.

## 1. ITCMD

### Rio Grande do Sul (Lei estadual 8.821/89) — progressivo por quinhão
| Faixa (UPF-RS) | Faixa (R$, 2026) | Alíquota |
|---|---|---|
| até 2.000 | até 56.652,80 | isento |
| 2.000 – 10.000 | 56.652,80 – 283.264 | 3% |
| 10.000 – 20.000 | 283.264 – 566.528 | 4% |
| 20.000 – 40.000 | 566.528 – 1.133.056 | 5% |
| acima de 40.000 | acima de 1.133.056 | 6% |

UPF-RS 2026 ≈ R$ 28,3264 (implícita nos limites divulgados). Doações: 3–4%.
⚠ Confirmar valor exato da UPF-RS 2026 na Receita Estadual RS.

### São Paulo (Lei 10.705/2000)
- **2026: alíquota fixa de 4%** sobre o valor venal.
- Progressividade pendente: PL 7/2024 (parecer favorável na CCJ) e PL 409/2025 não votados.
  Faixas propostas: 2% a 8%. Lei publicada em 2026 só produz efeitos a partir de 01/01/2027
  (anterioridade anual + nonagesimal).
- Isenção anual de doação (mesmo doador/donatário): R$ 96.050 (2026).

### LC 227/2026 (publicada 13–14/jan/2026) — regulamentação nacional do ITCMD
Mudanças com impacto direto na modelagem:
1. **Progressividade obrigatória** em todos os estados (teto de 8% — Res. Senado 9/92).
2. **Base de cálculo de quotas/ações fora de bolsa: no mínimo o patrimônio líquido AJUSTADO
   a valor de mercado de ativos e passivos**, podendo incluir fundo de comércio; FCD citado
   como metodologia. → Corrói a vantagem clássica da holding (transmissão de quotas por
   valor contábil/histórico). Central para a comparação seguro × holding.
3. **Doações sucessivas consolidadas** entre mesmas partes para aplicação da progressividade
   (prazo a definir por lei estadual). → Atinge a estratégia de doações graduais.
4. **Não incidência expressa** de ITCMD sobre benefícios de previdência complementar e
   seguros, "ainda que o beneficiário seja terceiro".
5. Trusts: fato gerador na reversão gratuita ao beneficiário.
6. Não autoaplicável: depende de lei estadual + anterioridade → efeitos práticos ≥ 2027.
7. Contexto de fiscalização: arrecadação ITCMD SP: R$ 4,4 bi (2023) → 6,3 bi (2024) → 6,9 bi (2025).
8. STJ Tema 1.371: fisco pode contestar valor declarado, mas por procedimento formal motivado.

**Implicação para os cenários:** rodar em dois regimes — (i) regras 2026 (SP 4% fixo, quotas
por valor patrimonial contábil ainda defensável) e (ii) regime pós-2027 (SP progressivo até 8%,
quotas a valor de mercado). O regime (ii) tende a favorecer o seguro; registrar como cenário
de sensibilidade regulatória, não como certeza.

## 2. Multa por atraso na abertura do inventário (prazo: 60 dias do óbito, CPC art. 611)
- SP (Lei 10.705/00, art. 21, I): 10% do ITCMD; 20% se atraso > 180 dias.
- RS: mesma estrutura 10%/20%.
- ⚠ Nuance: TJSP tem decisões afastando a multa em inventários extrajudiciais.

## 3. Seguro de vida e previdência — tratamento na sucessão
- **Seguro de vida:** capital não integra o espólio (CC art. 794); sem ITCMD, sem inventário.
  Não-incidência agora expressa também na LC 227/26.
- **VGBL/PGBL:** STF Tema 1214 (RE 1.363.013): inconstitucional ITCMD sobre valores
  transmitidos a beneficiários na morte do titular. Resgate independe de inventário.
- **Custo novo da previdência:** IOF de 5% sobre aportes em VGBL acima de R$ 600 mil/ano
  por CPF (Decreto 12.499/2025). → Cunha de custo relevante nos cenários B/C/D se a
  previdência entrar na comparação.

## 4. Custas e emolumentos
### Inventário extrajudicial (escritura pública)
- **RS (tabela TJRS 2026, reajuste 5,86%):** emolumentos com TETO ≈ R$ 5.179,40.
- **SP (tabela TJSP/Anoreg 2026, vigente desde 08/jan):** escala progressiva com teto;
  referência: escritura de ~R$ 500 mil ≈ R$ 5,5 mil. ⚠ Extrair faixas exatas da tabela CNB/SP.
- **Consequência para o motor:** emolumentos são custo quase FIXO — desprezíveis nos
  cenários C (R$ 120 mi) e D (R$ 350 mi); relevantes apenas no F (~R$ 1 mi).

### Inventário judicial — taxa judiciária SP (tabela progressiva específica de inventário)
| Monte-mor | Taxa |
|---|---|
| até R$ 50 mil | 10 UFESPs (R$ 384) |
| R$ 50 mil – 500 mil | 100 UFESPs (R$ 3.842) |
| R$ 500 mil – 2 mi | 300 UFESPs (R$ 11.526) |
| acima de R$ 2 mi | ⚠ confirmar faixas superiores |

UFESP 2026 = R$ 38,42. ⚠ Levantar taxa judiciária equivalente no RS (Regimento de Custas TJRS).

## 5. Honorários advocatícios (tabelas OAB — pisos referenciais)
| Modalidade | % sobre monte-mor | Mínimo RS (2024) | Mínimo SP |
|---|---|---|---|
| Extrajudicial | 6% | R$ 5.862,39 | R$ 3.969,48 |
| Judicial sem litígio | 8% | R$ 8.207,34 | R$ 5.557,28 |
| Judicial com litígio | 10% | — | — |

**Decisão de modelagem:** tabela OAB é piso referencial; em patrimônios grandes negocia-se
abaixo. Tratar honorários como parâmetro de sensibilidade (ex.: 2% a 8%), usando 6%/8%
como cenário-base conservador com fonte citável. Honorários são o MAIOR custo não
tributário do inventário — dominam emolumentos e custas por ordem de grandeza.

## 6. Parâmetros financeiros e atuariais
- Selic: 14,25% a.a. (Copom, 17/jun/2026; ciclo de corte em curso).
- Juro real (NTN-B longa): ≈ 8% a.a. (jul/2026 — máxima histórica).
- Taxa de desconto do motor: REAL (fluxos em R$ constantes). Sensibilidade: 4% / 6% / 8%.
  Nota: 8% real é pico de estresse; usar como limite superior, não como base.
- Tábua de mortalidade: BR-EMS (Susep) para o VP atuarial. ⚠ Baixar versão mais recente
  (BR-EMS 2021 mt/sb, M/F) no site da Susep.
- IPCA: apólices corrigem capital pelo IPCA (confirmado na planilha-fonte); trabalhar em
  termos reais neutraliza a correção.

## 7. Parâmetros da cunha de iliquidez (levantados 08/jul/2026)
- **Prazo do inventário:** extrajudicial 2–6 meses; judicial média ~1 ano e 9 meses
  (distribuição→encerramento), intervalo 1–5 anos em casos litigiosos. Base: 6 meses
  (extrajudicial) / 21 meses (judicial); sensibilidade até 60 meses no cenário C.
- **Capital-ponte:** taxa de crédito livre PJ (capital de giro >365d) ~13–20% a.a. nominal
  (BCB, jan/2026); em termos reais ≈ r + spread de 4–8 p.p. Base: spread 6 p.p. reais.
- **Deságio de venda forçada (DLOM):** literatura de restricted stocks e valuation de
  empresas fechadas: 20%–35%. Base: 25%; sensibilidade 15%–35%.
  Referências acadêmicas a citar: Shleifer & Vishny (1992, fire sales); estudos de
  restricted stock (Silber 1991); surveys de DLOM. ⚠ Fechar citações formais na redação.
- **Estrutura da cunha no motor:** a família cobre o custo exigível (ITCMD em 60 dias +
  custas) pelo mais barato entre (a) crédito-ponte pelo prazo do inventário e
  (b) venda forçada com deságio sobre o valor líquido necessário.

## 8. Doação em vida (4º instrumento — decisão de 08/jul/2026)
- ITCMD doação: RS 3% até 10.000 UPF e 4% acima ⚠ confirmar faixas; SP 4% (isenção
  R$ 96.050/ano por par doador-donatário).
- Custos: escritura de doação (emolumentos com teto), eventual reserva de usufruto.
- Pós-2027 (LC 227/26): consolidação de doações sucessivas entre as mesmas partes —
  o parcelamento anual para fugir da progressividade/isenção morre. Resultado
  potencialmente interessante: a reforma atinge a doação parcelada mais que a holding.
- Custo de oportunidade não monetário (perda de controle do patrimônio em vida):
  tratar qualitativamente; usufruto mitiga.

## Fontes principais
- LC 227/26: Planalto (lcp227.htm); análise Machado Meyer (03/mar/2026)
- ITCMD RS: Receita Estadual RS (atendimento.receita.rs.gov.br)
- ITCMD SP: Lei 10.705/2000; PL 7/2024 e PL 409/2025 (Alesp); Tersi Advocacia; Sávio Advocacia
- Tema 1214: STF (RE 1.363.013), notícia oficial STF
- IOF/VGBL: Decreto 12.499/2025
- Emolumentos RS: TJRS Tabela_de_Emolumentos_2026.pdf; Anoreg-RS
- Emolumentos SP: Anoreg-SP / CNB-SP tabelas 2026
- Taxa judiciária SP: TJSP (Índices e Taxas Judiciárias); UFESP 2026 = R$ 38,42
- Honorários: tabelas OAB-SP e OAB-RS
- Selic: Copom jun/2026 (Agência Brasil); NTN-B: Tesouro Direto (jul/2026)
