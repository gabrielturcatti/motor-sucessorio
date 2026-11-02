# Motor de cálculo do custo sucessório

Código, parâmetros públicos e resultados da dissertação *O seguro de vida como instrumento
de planejamento sucessório em empresas familiares brasileiras* (Gabriel Turcatti Lorandi,
Programa de Pós-Graduação Profissional em Economia, UFRGS, 2026).

O motor compara, em valor presente, o custo de seis estratégias sucessórias — inventário com
crédito-ponte ou venda forçada, inventário com reserva prévia, seguro de vida, holding
familiar, doação em vida e VGBL — ponderando todos os anos possíveis de óbito por uma tábua
de mortalidade. Reporta o custo esperado, o custo médio nos 5% piores desfechos (CTE-95), a
decomposição do custo pelo Índice de Eficiência Sucessória e a fronteira de eficiência por
dominância de Pareto. A formalização está no Apêndice A da dissertação.

## O que está e o que não está aqui

A tabela de precificação da seguradora (prêmios, valores de resgate, catálogo de produtos e
regras tarifárias) **não é distribuída**: sua cessão foi condicionada à não redistribuição.
Sem ela o motor não executa; os resultados, porém, estão todos em `motor/resultados/`, e as
tabelas e figuras da dissertação podem ser regeneradas a partir deles. O esquema dos
arquivos ausentes está em `motor/parametros/DADOS_NAO_DISTRIBUIDOS.md`, para quem quiser
rodar o motor com outra tabela de precificação.

| Pasta | Conteúdo |
|---|---|
| `motor/*.py` | módulos do motor, rotinas de execução (`rodar_v*.py`), suíte de verificação e gerador de tabelas e figuras |
| `motor/parametros/` | tábuas de mortalidade (BR-EMS mt 2026 e 2021, IBGE 2024) e levantamento dos parâmetros tributários e de custos |
| `motor/resultados/` | saídas do motor em CSV, usadas pelas tabelas da dissertação |
| `motor/tabelas/` | Tabelas 1 a 15 da dissertação em CSV, geradas por `gerar_tabelas.py` (1 a 13) e `gerar_tabelas_v12.py` (14 e 15) |
| `motor/figuras/` | Figuras 1 a 3 |

## Reprodução

Python 3.10 ou superior, com `pandas` e `matplotlib`; Graphviz (`dot`) para a Figura 3.

```bash
cd motor
python3 gerar_tabelas.py      # regenera tabelas/ e figuras/ a partir de resultados/
python3 gerar_tabelas_v12.py  # Tabelas 14 e 15 (matriz de preços de equilíbrio)
```

Com a tabela de precificação em `motor/parametros/`:

```bash
python3 verificar.py          # 46 testes de consistência interna
python3 rodar_v9.py           # caso base, caducidade, regime pós-2027, juro, VGBL
python3 rodar_v8.py           # escada de agravo e contratabilidade
python3 rodar_v7_h.py         # grid de idade × produto (e cenário H na versão antiga)
python3 rodar_v10_h.py        # cenário H (versão usada na dissertação)
python3 rodar_v10.py          # holding × doação, sem crédito-ponte, sensibilidades complementares
python3 rodar_v12_matriz.py   # matriz de preços de equilíbrio e prêmio puro
python3 gerar_tabelas.py
```

Correspondência entre arquivos e tabelas: T1–T5 = Tabelas 1–5; T10 = 6; T9 = 7; T6 = 8;
T7 = 9; T8 = 10; T11 = 11; T12 = 12; T13 = 13; T14 = 14; T15 = 15.

Nota: o eixo `plusvalia_sem_credito` de `v9_sensibilidade.csv` usa crédito-ponte com spread
de 100% a.a., que ainda era tomado pela família em inventários extrajudiciais de 6 meses; a
variante sem crédito da dissertação (Tabela 9) usa `v10_sem_credito.csv`, em que o crédito é
de fato inexistente.

## Dados de mercado (seção 4)

`dados_mercado_v12.py` refaz, a partir de fontes públicas, os números de mercado da seção 4:
prêmio direto e despesas de comercialização do seguro de vida individual (SES/SUSEP, ramo
1391) e aportes e resgates de VGBL, deflacionados pelo IPCA (IBGE, SIDRA, tabela 1737). Os
arquivos de origem não são versionados por tamanho; a forma de obtê-los está no cabeçalho do
script. As saídas estão em `motor/resultados/v12_susep_*.csv`.

```bash
python3 dados_mercado_v12.py <pasta com os CSVs da SES> <ipca.json>
```

## Citação

LORANDI, Gabriel Turcatti. *Motor de cálculo do custo sucessório*: código, parâmetros e
resultados da dissertação. [S. l.]: GitHub, 2026.

Código sob licença MIT (ver `LICENSE`). Os resultados e figuras podem ser reutilizados com
citação da dissertação.
