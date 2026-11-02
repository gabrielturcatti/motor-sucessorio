# Arquivos de precificação não distribuídos

O motor espera, nesta pasta, os arquivos abaixo, extraídos da tabela de precificação de uma
seguradora de vida individual. Eles não acompanham o repositório.

| Arquivo | Usado por | Esquema |
|---|---|---|
| `fatores_2024.csv` | `premios.py` | primeira coluna = idade de emissão; demais colunas = uma por chave de produto (`FAMILIA + PRAZO + SEXO [+ "+" banda de capital] [+ CLASSE] [+ "F" fumante]`, por exemplo `WL10M`, `WL10M+C`, `TP10MST`); valor = fator de prêmio anual por mil de capital. Célula vazia, `-` ou zero = produto indisponível na idade |
| `regras_tarifarias.json` | `premios.py` | `{"banda_preferencial_min": float, "familias_com_banda": [str], "fator_modal": {"decrescentes", "wl5", "tp", "capital_alto", "demais", "limite_capital"}}` |
| `resgate.csv` | `resgate.py` | valor de resgate como fração do capital segurado, por produto, sexo, idade de emissão e ano de vigência |

Prêmio anual = fator × capital / 1.000 × (1 + IOF). Prêmio mensal = prêmio anual × fator modal.
