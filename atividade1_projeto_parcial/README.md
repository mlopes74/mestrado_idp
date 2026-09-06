# Atividade 1 — Projeto Parcial

**Tema:** Chances de sucesso de uma Reclamação no STF antes de ajuizá-la (análise jurimétrica preliminar)
**Mestrando (representante do grupo):** Marcos Meira
**Entrega:** 28/09

## Arquivos entregues

| Arquivo | Conteúdo |
|---|---|
| `marcos_meira.ipynb` | Notebook Jupyter com: descrição do problema, descrição da base, referência ao dicionário de dados, análises descritivas (medidas de posição/dispersão e gráficos) e discussão preliminar (relações entre variáveis e qualidade dos dados). Já executado, com saídas e gráficos gerados. |
| `dicionario_marcos_meira.xlsx` | Dicionário de dados das 18 variáveis da base (nome, nome descritivo, tipo, unidade, domínio, significado, observações), mais aba com a citação completa da fonte dos dados. |
| `base_marcos_meira.csv` | Base de dados bruta (6.370 decisões do STF em reclamações constitucionais, 2011–2018), sem qualquer tratamento/limpeza. |
| `relatorio_parcial_marcos_meira.docx` | Relatório parcial (Introdução, Objetivos, Referencial Teórico, Referências Bibliográficas), fonte Times New Roman 12, alinhamento justificado. |

## Fonte dos dados

Os dados são reutilização, com citação explícita, de uma base pública de pesquisa acadêmica:

- HOUAISS (PITELLI), Lívia Pitelli Zamarian. *Reclamação constitucional e recalcitrância judicial
  na medida das decisões do Supremo Tribunal Federal*. Tese de Doutorado — Universidade Federal
  Fluminense (UFF), 2019.
- JESUS FILHO, José de. `repotese`: código e base de dados da tese de Lívia Houaiss. GitHub, 2019.
  Disponível em: <https://github.com/jjesusfilho/repotese>.

**Por que uma base de terceiros?** O ambiente usado para preparar esta entrega não tem acesso aos
portais de dados abertos do STF/DataJud (bloqueio de rede do ambiente de execução). Diante do
prazo, optou-se por reutilizar — com citação clara — uma base real, pública e documentada,
construída para uma tese sobre exatamente o mesmo fenômeno (reclamação constitucional no STF).
O repositório de origem não traz uma licença explícita; o uso aqui é estritamente acadêmico e
didático (atividade de disciplina), com atribuição integral ao autor e à pesquisa original.

**Pendências para as próximas etapas (a validar com o orientador):**
- Confirmar formalmente com o autor/repositório eventuais condições de reuso dos dados.
- Avaliar estender a coleta para anos posteriores a 2018 via API pública do DataJud/CNJ, caso o
  acesso à rede esteja disponível no ambiente de trabalho do aluno.
- Tratar os problemas de qualidade de dados listados na seção 5 do notebook antes da modelagem
  preditiva (ausências em `assunto`/`area`, padronização de categorias, duplicidade de
  `incidente`, datas inconsistentes, colinearidade entre variáveis de paradigma).

## Como reexecutar o notebook

```bash
pip install pandas numpy matplotlib seaborn scipy openpyxl
jupyter nbconvert --to notebook --execute --inplace marcos_meira.ipynb
```

O notebook espera `base_marcos_meira.csv` no mesmo diretório.
