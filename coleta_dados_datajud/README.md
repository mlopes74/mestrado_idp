# Coleta atualizada de Reclamações no STF (DataJud/CNJ)

## Por que isto está aqui e não já rodado

Testei exaustivamente, neste ambiente (sandbox do Claude Code), o acesso a todo domínio que
poderia dar dados reais e atuais de reclamações no STF:

| Domínio testado | Resultado |
|---|---|
| `transparencia.stf.jus.br`, `portal.stf.jus.br`, `redir.stf.jus.br`, `jurisprudencia.stf.jus.br` | Bloqueado (403 política de rede) |
| `www.cnj.jus.br`, `api-publica.datajud.cnj.jus.br` (API pública do DataJud) | Bloqueado |
| `dados.gov.br` | Bloqueado |
| `www.stj.jus.br`, `dadosabertos.web.stj.jus.br`, `www.trf2.jus.br` | Bloqueado |
| `bibliotecadigital.fgv.br`, `direitorio.fgv.br` | Bloqueado |
| `conjur.com.br`, `jota.info`, `migalhas.com.br`, `escavador.com`, `jusbrasil.com.br` | Bloqueado |
| `brasil.io` | Bloqueado |
| `github.com`, `raw.githubusercontent.com` | **Liberado** |

Ou seja: **todo domínio `.jus.br`, `.gov.br` e a maior parte de sites de notícias/legal-tech estão
bloqueados pela política de rede da organização neste ambiente** — não é uma falha pontual, é uma
política deliberada, testada em mais de 15 domínios diferentes. A única via de acesso externo que
funciona aqui é a hospedagem de código (GitHub) e os registros de pacotes (PyPI/npm). Também
verifiquei o repositório GitHub, buscando algum espelho já pronto e atualizado (2019 em diante) da
mesma base de reclamações do STF — não encontrei nenhum.

**Conclusão prática: esta sessão não consegue, por si só, baixar dados atualizados do STF.** Isso
precisa ser feito em um ambiente com internet normal (seu computador, ou uma sessão do Claude Code
com política de rede menos restritiva).

## O que preparei para resolver isso

O script `coletar_reclamacoes_stf.py` faz a coleta completa via **API Pública do DataJud (CNJ)** —
a base nacional oficial de metadados processuais, que cobre todos os tribunais (STF incluso), é
atualizada continuamente e é gratuita/sem cadastro pessoal (usa uma chave pública, igual para
todo mundo). Ele:

1. Descobre automaticamente o código da classe processual "Reclamação" no STF (não usa um código
   "chutado" de memória).
2. Faz a coleta paginada de **todos** os processos dessa classe, do início da série até hoje,
   salvando em JSONL de forma retomável (se cair no meio, roda de novo e continua de onde parou).
3. Consolida tudo num CSV com os campos principais de cada processo.

### O que ele NÃO resolve sozinho: o rótulo de resultado

A API do DataJud devolve metadados e a lista de andamentos (`movimentos`) de cada processo, mas
**não** um campo pronto "procedente/improcedente" como o dataset da tese de Houaiss tinha. Para
chegar nesse rótulo, o script já inclui uma tentativa (`CODIGOS_MOVIMENTO_RESULTADO`), mas ela
**precisa ser conferida** contra a Tabela Processual Unificada (TPU) do CNJ — que também está
bloqueada aqui — e validada numa amostra manual de dezenas de processos (mesma prática que a
Lívia Houaiss descreve na tese dela). Isso é trabalho real de engenharia de dados, não um
one-liner; é a próxima etapa depois que tivermos os dados brutos em mãos.

## Como seguir a partir daqui — três caminhos possíveis

**A) Você roda o script na sua máquina e me manda o CSV de volta (mais rápido).**
```bash
pip install requests pandas
python coletar_reclamacoes_stf.py --so-descobrir-classe   # primeiro, só para conferir o código da classe
python coletar_reclamacoes_stf.py --codigo-classe <N>     # depois, a coleta completa
```
Confira antes a chave de API vigente em
<https://datajud-wiki.cnj.jus.br/api-publica/acesso/> (o script já vem com a última que eu
tinha registrada, mas o CNJ já trocou essa chave no passado). Quando terminar, me envie o arquivo
`dados_brutos_datajud/reclamacoes_stf_bruto_consolidado.csv` (pode levar bastante tempo — são
potencialmente dezenas de milhares de processos; use `--max-paginas` para testar com um pedaço
pequeno primeiro).

**B) Você abre uma sessão do Claude Code no seu computador (ou outro ambiente com internet normal)
e eu rodo o script diretamente lá.**

**C) Seguimos com dados agregados/estatísticas já publicadas (menos ideal).** Encontrei, por
busca, números públicos de 2025 (ex.: taxa de sucesso geral e por área do direito, citados em
matéria do ConJur/JOTA) mas não em nível de processo — serviriam apenas para uma comparação de
contexto, não para treinar um classificador por caso.

Meu recomendo a opção A ou B. Qual prefere?
