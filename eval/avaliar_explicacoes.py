"""Avaliação das explicações em linguagem simples, em amostra (Tema 9).

A explicação é uma função do SQL (``assistente_sql.explicacao``), sem modelo.
Por isso dá para gerá-la a partir do SQL executado que já está gravado num CSV
de ``eval/avaliar.py``: o texto é o mesmo que a tela mostraria para aquela
consulta. O script não chama o Ollama nem o banco.

Duas etapas:

1. ``gerar``: calcula as métricas automáticas (cobertura e tamanho) para todas
   as consultas executadas e sorteia uma amostra com semente fixa. Grava uma
   ficha CSV com as colunas de avaliação em branco.
2. ``resumir``: lê as fichas preenchidas por pessoas e calcula as métricas.

Quem avalia:

- ``entendeu`` (``sim``, ``parcial`` ou ``nao``): pessoa sem formação em TI,
  que lê só a pergunta e a explicação, sem o SQL. A meta da proposta técnica
  (28/10) é de 20 explicações avaliadas por 2 pessoas não técnicas, com pelo
  menos 75% de "entendeu". Cada pessoa preenche a própria cópia da ficha.
- ``fiel_ao_sql``: integrante do grupo, que confere se a explicação descreve
  o SQL (e não se o SQL está certo).

Uso:
    python eval/avaliar_explicacoes.py gerar [--csv RESULTADOS] [--amostra 20] [--semente 9]
    python eval/avaliar_explicacoes.py resumir FICHA.csv [FICHA2.csv ...]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from assistente_sql.explicacao import explicar

PASTA = Path(__file__).resolve().parent
PASTA_RESULTADOS = PASTA / "resultados"
# rodada completa do conjunto de teste (07/11/2026), já reavaliada
CSV_PADRAO = PASTA_RESULTADOS / "resultados_20261107T193324Z_reavaliado_20261107T204218Z.csv"

COLUNAS_FICHA = [
    "id",
    "pergunta",
    "sql_executado",
    "explicacao",
    "explicacao_completa",
    "avaliador",
    "perfil_avaliador",  # "nao_tecnico" ou "grupo"
    "entendeu",  # sim / parcial / nao (não técnico)
    "fiel_ao_sql",  # sim / nao (grupo)
    "observacao",
]


def carregar_executadas(caminho: Path) -> list[dict[str, Any]]:
    """Linhas do assistente completo com SQL executado, com a explicação gerada."""
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    executadas = []
    for linha in linhas:
        if linha.get("modo") != "completo" or linha.get("situacao") != "ok":
            continue
        explicacao = explicar(linha.get("sql_executado"))
        executadas.append(
            {
                "id": linha["id"],
                "pergunta": linha["pergunta"],
                "sql_executado": linha["sql_executado"],
                "explicacao": explicacao.texto if explicacao else "",
                "explicacao_completa": bool(explicacao and explicacao.completa),
                "passos": len(explicacao.passos) if explicacao else 0,
                "palavras": len(explicacao.texto.split()) if explicacao else 0,
            }
        )
    return executadas


def metricas_automaticas(executadas: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(executadas)
    if not total:
        return {"consultas_executadas": 0}
    com_texto = [e for e in executadas if e["explicacao"]]
    completas = sum(e["explicacao_completa"] for e in executadas)
    return {
        "consultas_executadas": total,
        "com_explicacao": len(com_texto),
        "explicacao_completa": completas,
        "cobertura_completa_pct": round(100 * completas / total, 1),
        "media_passos": round(sum(e["passos"] for e in com_texto) / max(len(com_texto), 1), 1),
        "media_palavras": round(sum(e["palavras"] for e in com_texto) / max(len(com_texto), 1), 1),
        "ids_incompletos": [e["id"] for e in executadas if not e["explicacao_completa"]],
    }


def gerar(caminho_csv: Path, tamanho: int, semente: int) -> tuple[Path, Path, dict[str, Any]]:
    executadas = carregar_executadas(caminho_csv)
    amostra = sorted(
        random.Random(semente).sample(executadas, min(tamanho, len(executadas))),  # noqa: S311
        key=lambda e: e["id"],
    )
    identificador = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    ficha = PASTA_RESULTADOS / f"explicacoes_ficha_{identificador}.csv"
    with ficha.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_FICHA, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(amostra)

    resumo = {
        "csv_origem": caminho_csv.name,
        "data_utc": datetime.now(UTC).isoformat(),
        "semente": semente,
        "tamanho_amostra": len(amostra),
        "ids_amostra": [e["id"] for e in amostra],
        "automaticas": metricas_automaticas(executadas),
        "ficha": ficha.name,
    }
    destino = PASTA_RESULTADOS / f"explicacoes_automaticas_{identificador}.json"
    destino.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return ficha, destino, resumo


def _sim(valor: str | None) -> bool | None:
    texto = (valor or "").strip().lower()
    if texto in ("sim", "s", "1", "true"):
        return True
    if texto in ("nao", "não", "n", "0", "false"):
        return False
    return None


def resumir(fichas: list[Path]) -> tuple[Path, dict[str, Any]]:
    linhas: list[dict[str, str]] = []
    for ficha in fichas:
        with ficha.open(encoding="utf-8-sig", newline="") as arquivo:
            linhas += list(csv.DictReader(arquivo))

    def proporcao(perfil: str, campo: str) -> dict[str, Any]:
        valores = [
            _sim(linha.get(campo))
            for linha in linhas
            if linha.get("perfil_avaliador") == perfil and _sim(linha.get(campo)) is not None
        ]
        sim = sum(valores)
        return {
            "respostas": len(valores),
            "sim": sim,
            "pct": round(100 * sim / len(valores), 1) if valores else None,
        }

    respostas = [
        (linha.get("entendeu") or "").strip().lower().replace("não", "nao")
        for linha in linhas
        if linha.get("perfil_avaliador") == "nao_tecnico"
    ]
    respostas = [r for r in respostas if r in ("sim", "parcial", "nao")]
    resumo = {
        "fichas": [f.name for f in fichas],
        "data_utc": datetime.now(UTC).isoformat(),
        "avaliadores": sorted({linha.get("avaliador", "") for linha in linhas} - {""}),
        "entendeu_nao_tecnico": {
            "respostas": len(respostas),
            **{valor: respostas.count(valor) for valor in ("sim", "parcial", "nao")},
            "pct_sim": round(100 * respostas.count("sim") / len(respostas), 1)
            if respostas
            else None,
            "meta_pct_sim": 75,
        },
        "fiel_ao_sql_grupo": proporcao("grupo", "fiel_ao_sql"),
    }
    identificador = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destino = PASTA_RESULTADOS / f"explicacoes_resumo_{identificador}.json"
    destino.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino, resumo


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia as explicações em amostra.")
    sub = parser.add_subparsers(dest="etapa", required=True)
    p_gerar = sub.add_parser("gerar", help="métricas automáticas e ficha da amostra")
    p_gerar.add_argument("--csv", type=Path, default=CSV_PADRAO)
    p_gerar.add_argument("--amostra", type=int, default=20)
    p_gerar.add_argument("--semente", type=int, default=9)
    p_resumir = sub.add_parser("resumir", help="métricas das fichas preenchidas")
    p_resumir.add_argument("fichas", type=Path, nargs="+")
    args = parser.parse_args()

    if args.etapa == "gerar":
        ficha, destino, resumo = gerar(args.csv, args.amostra, args.semente)
        print(json.dumps(resumo["automaticas"], ensure_ascii=False, indent=2))
        print(f"ficha para preencher: {ficha}\nmétricas: {destino}")
    else:
        destino, resumo = resumir(args.fichas)
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
        print(f"resumo: {destino}")


if __name__ == "__main__":
    main()
