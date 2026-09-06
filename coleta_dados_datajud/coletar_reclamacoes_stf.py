#!/usr/bin/env python3
"""
Coleta de processos da classe "Reclamação" (Rcl) no STF via API Pública do
DataJud (CNJ), do início da série histórica até a data atual.

CONTEXTO
--------
Este script foi escrito dentro de um ambiente sandbox do Claude Code cujo
proxy de rede bloqueia todo domínio .jus.br e .gov.br (política da
organização, testada e confirmada — não é um bug a ser contornado). Por isso
ele NÃO pôde ser executado nem validado ponta a ponta aqui. Ele deve ser
executado por você, em uma máquina com acesso normal à internet.

O QUE ESTE SCRIPT FAZ
----------------------
1. Descobre dinamicamente o(s) código(s) de classe processual cujo nome
   contém "Reclama" na base do STF (evita "chutar" o código na mão).
2. Faz a varredura paginada (via `search_after`) de TODOS os processos
   dessa(s) classe(s) no STF, do início da série até hoje, salvando os
   resultados brutos em arquivos JSONL (um objeto por linha) — formato
   resiliente a interrupções: se o script cair no meio, é só rodar de novo
   que ele retoma de onde parou (usa um arquivo de checkpoint).
3. Ao final, consolida os JSONL em um único CSV "bruto" (uma linha por
   processo, com os campos principais + a lista de movimentos como JSON),
   pronto para ser filtrado, rotulado e cruzado com o dataset já usado no
   Projeto Parcial (ver ../atividade1_projeto_parcial/).

O QUE ESTE SCRIPT **NÃO** FAZ (e por quê)
------------------------------------------
Ele NÃO extrai sozinho, de forma confiável, se a reclamação foi julgada
"procedente" ou "improcedente". A API pública do DataJud devolve METADADOS
processuais (classe, assuntos, órgão julgador, datas, e a lista de
`movimentos` — os andamentos do processo), mas não um campo pronto
"resultado do julgamento". Para chegar a esse rótulo (o mesmo `decisao` que
usamos no dataset de Lívia Houaiss) é preciso:
  a) mapear, na Tabela Processual Unificada (TPU) do CNJ, quais códigos de
     `movimento` correspondem a "procedência", "improcedência",
     "procedência em parte" etc. (o dicionário abaixo, em
     `CODIGOS_MOVIMENTO_RESULTADO`, é um ponto de partida a CONFERIR e
     completar — os códigos precisam ser validados contra a TPU vigente,
     que também está em domínio bloqueado neste ambiente); e
  b) validar manualmente uma amostra de dezenas de processos (mesma prática
     adotada na tese de Houaiss) para conferir se a extração automática bate
     com a leitura humana da decisão, corrigindo o dicionário até o erro
     ficar pequeno.
Ou seja: a extração da base BRUTA e atualizada (passo que está bloqueado
neste ambiente) é resolvida por este script; a ROTULAGEM do resultado é uma
segunda etapa de engenharia/validação que fizemos juntos depois que você
tiver os dados brutos em mãos.

COMO OBTER A CHAVE DE API
--------------------------
A API Pública do DataJud usa uma chave pública, igual para todos os
usuários, publicada oficialmente pelo CNJ em:
    https://datajud-wiki.cnj.jus.br/api-publica/acesso/
Copie a chave atual dessa página e cole abaixo em API_KEY (a chave abaixo é
a que constava publicamente na documentação até o treinamento deste
assistente — CONFIRA se ainda é a vigente antes de rodar em volume, pois o
CNJ já trocou essa chave no passado).

COMO RODAR
----------
    pip install requests pandas
    python coletar_reclamacoes_stf.py --api-key "APIKey SEU_TOKEN_AQUI"

Por padrão, salva os dados em ./dados_brutos_datajud/.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

TRIBUNAL = "api_publica_stf"
BASE_URL = f"https://api-publica.datajud.cnj.jus.br/{TRIBUNAL}/_search"

# Chave pública documentada pelo CNJ (mesma para todos os usuários).
# CONFIRA em https://datajud-wiki.cnj.jus.br/api-publica/acesso/ antes de
# rodar em volume — o CNJ já revogou/trocou essa chave no passado.
API_KEY_PADRAO = "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRHdw=="

OUT_DIR = Path(__file__).parent / "dados_brutos_datajud"
CHECKPOINT_FILE = OUT_DIR / "_checkpoint.json"
JSONL_FILE = OUT_DIR / "reclamacoes_stf_bruto.jsonl"
PAGE_SIZE = 1000  # máximo recomendado pela documentação do DataJud

# Dicionário de PARTIDA (não definitivo!) para tentar inferir o resultado a
# partir do nome do movimento. Baseado em códigos usuais da TPU/CNJ para
# "Julgamento" — PRECISA SER CONFERIDO contra a TPU vigente e validado numa
# amostra manual antes de qualquer uso analítico.
CODIGOS_MOVIMENTO_RESULTADO = {
    # codigo_movimento: rotulo_candidato
    219: "procedente",        # "Procedência"
    220: "improcedente",      # "Improcedência"
    221: "procedente_em_parte",  # "Procedência em Parte"
    471: "prejudicado",       # "Prejudicado"
    466: "extincao_sem_julgamento_de_merito",
}


def descobrir_codigos_classe(session: requests.Session, api_key: str, termo: str = "Reclama"):
    """Descobre dinamicamente quais classe.codigo têm nome contendo `termo`."""
    body = {
        "size": 50,
        "query": {"match": {"classe.nome": termo}},
        "_source": ["classe"],
    }
    resp = session.post(BASE_URL, headers=_headers(api_key), json=body, timeout=30)
    resp.raise_for_status()
    hits = resp.json().get("hits", {}).get("hits", [])
    codigos = {}
    for h in hits:
        classe = h.get("_source", {}).get("classe", {})
        codigos[classe.get("codigo")] = classe.get("nome")
    return codigos


def _headers(api_key: str):
    return {"Authorization": api_key, "Content-Type": "application/json"}


def _carregar_checkpoint():
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return {"search_after": None, "total_coletado": 0}


def _salvar_checkpoint(cp):
    CHECKPOINT_FILE.write_text(json.dumps(cp))


def coletar(api_key: str, codigo_classe: int, max_paginas: int | None = None):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    cp = _carregar_checkpoint()
    search_after = cp["search_after"]
    total = cp["total_coletado"]

    modo_arquivo = "a" if total > 0 else "w"
    pagina = 0

    with open(JSONL_FILE, modo_arquivo, encoding="utf-8") as f:
        while True:
            body = {
                "size": PAGE_SIZE,
                "query": {"term": {"classe.codigo": codigo_classe}},
                "sort": [{"@timestamp": {"order": "asc"}}, {"_id": {"order": "asc"}}],
            }
            if search_after:
                body["search_after"] = search_after

            resp = session.post(BASE_URL, headers=_headers(api_key), json=body, timeout=60)
            if resp.status_code == 429:
                print("Rate limit atingido, aguardando 10s...", file=sys.stderr)
                time.sleep(10)
                continue
            resp.raise_for_status()

            hits = resp.json().get("hits", {}).get("hits", [])
            if not hits:
                print("Fim da paginação — coleta concluída.")
                break

            for h in hits:
                f.write(json.dumps(h["_source"], ensure_ascii=False) + "\n")
            total += len(hits)
            search_after = hits[-1]["sort"]

            cp = {"search_after": search_after, "total_coletado": total}
            _salvar_checkpoint(cp)

            pagina += 1
            print(f"Página {pagina}: +{len(hits)} processos (total acumulado: {total})")

            if max_paginas and pagina >= max_paginas:
                print(f"Limite de {max_paginas} páginas atingido nesta execução; "
                      f"rode novamente para continuar de onde parou.")
                break

            time.sleep(0.3)  # gentileza com o servidor público

    print(f"Total coletado nesta base: {total} registros em {JSONL_FILE}")


def consolidar_csv():
    """Lê o JSONL bruto e gera um CSV com os campos principais + resultado candidato."""
    import pandas as pd

    linhas = []
    with open(JSONL_FILE, encoding="utf-8") as f:
        for linha in f:
            doc = json.loads(linha)
            movimentos = doc.get("movimentos", []) or []
            resultado_candidato = None
            data_resultado = None
            for mov in movimentos:
                codigo = (mov.get("codigo") or (mov.get("nome") and None))
                if codigo in CODIGOS_MOVIMENTO_RESULTADO:
                    resultado_candidato = CODIGOS_MOVIMENTO_RESULTADO[codigo]
                    data_resultado = mov.get("dataHora")

            linhas.append({
                "numero_processo": doc.get("numeroProcesso"),
                "classe_codigo": doc.get("classe", {}).get("codigo"),
                "classe_nome": doc.get("classe", {}).get("nome"),
                "tribunal": doc.get("tribunal"),
                "grau": doc.get("grau"),
                "orgao_julgador": (doc.get("orgaoJulgador") or {}).get("nome"),
                "data_ajuizamento": doc.get("dataAjuizamento"),
                "data_ultima_atualizacao": doc.get("dataHoraUltimaAtualizacao"),
                "assuntos": json.dumps(doc.get("assuntos"), ensure_ascii=False),
                "n_movimentos": len(movimentos),
                "resultado_candidato": resultado_candidato,
                "data_resultado_candidato": data_resultado,
                "movimentos_json": json.dumps(movimentos, ensure_ascii=False),
            })

    df = pd.DataFrame(linhas)
    out_csv = OUT_DIR / "reclamacoes_stf_bruto_consolidado.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"CSV consolidado: {out_csv} ({len(df)} linhas)")
    print("\nATENÇÃO: a coluna 'resultado_candidato' é PROVISÓRIA — os códigos de "
          "movimento em CODIGOS_MOVIMENTO_RESULTADO ainda precisam ser conferidos "
          "contra a Tabela Processual Unificada (TPU) do CNJ e validados numa "
          "amostra manual antes de qualquer uso analítico.")
    print(f"\n{(df['resultado_candidato'].isna()).mean() * 100:.1f}% das linhas ficaram "
          f"sem resultado_candidato — provavelmente processos sem trânsito em julgado "
          f"ou cujo código de movimento de resultado não está no dicionário acima.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api-key", default=API_KEY_PADRAO,
                     help="Cabeçalho Authorization completo, ex.: 'APIKey xxxxx'. "
                          "Confira a chave vigente em https://datajud-wiki.cnj.jus.br/api-publica/acesso/")
    ap.add_argument("--max-paginas", type=int, default=None,
                     help="Limita o número de páginas nesta execução (útil para testar antes de rodar tudo).")
    ap.add_argument("--so-descobrir-classe", action="store_true",
                     help="Só roda a descoberta do código de classe 'Reclamação' e sai (não coleta).")
    ap.add_argument("--codigo-classe", type=int, default=None,
                     help="Pula a descoberta automática e usa este código de classe diretamente.")
    ap.add_argument("--consolidar", action="store_true",
                     help="Só consolida o JSONL já baixado em CSV (não coleta nada novo).")
    args = ap.parse_args()

    if args.consolidar:
        consolidar_csv()
        return

    session = requests.Session()

    if args.codigo_classe:
        codigo = args.codigo_classe
    else:
        print("Descobrindo código(s) de classe 'Reclamação' no STF...")
        codigos = descobrir_codigos_classe(session, args.api_key)
        if not codigos:
            print("Nenhuma classe encontrada com 'Reclama' no nome. Verifique a chave de API "
                  "e a conectividade.", file=sys.stderr)
            sys.exit(1)
        print("Classes encontradas:")
        for cod, nome in codigos.items():
            print(f"  - código {cod}: {nome}")
        if args.so_descobrir_classe:
            return
        if len(codigos) > 1:
            print("\nMais de um código encontrado — rode novamente com --codigo-classe <N> "
                  "escolhendo o correto (normalmente o que tiver nome exatamente "
                  "'Reclamação').", file=sys.stderr)
            sys.exit(1)
        codigo = next(iter(codigos))

    print(f"\nColetando processos da classe {codigo} no STF (isso pode levar bastante tempo — "
          f"são potencialmente dezenas de milhares de processos)...\n")
    coletar(args.api_key, codigo, max_paginas=args.max_paginas)
    consolidar_csv()


if __name__ == "__main__":
    main()
