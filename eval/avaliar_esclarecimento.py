"""Avaliação do pedido de esclarecimento (Tema 9: "perguntar quando o esquema for ambíguo").

Mede as duas metas ligadas ao esclarecimento, sem o Ollama e sem o banco,
porque a verificação (``assistente_sql.esclarecimento``) roda antes do modelo:

- Tratamento de ambiguidade (meta da proposta técnica, 28/10): entre as
  perguntas marcadas como ambíguas em ``perguntas_ambiguas.jsonl``, quantas
  fazem o sistema pedir esclarecimento. Meta: pelo menos 60%.
- Esclarecimentos desnecessários: entre as perguntas claras (as 50 de teste,
  as 10 de desenvolvimento e as marcadas como claras no arquivo de ambíguas),
  quantas fazem o sistema perguntar sem precisar.

O arquivo ``perguntas_ambiguas.jsonl`` deve ser escrito por quem não leu as
regras de ``esclarecimento.py``; senão a medida fica a favor do sistema. Cada
linha: ``{"id": "A01", "pergunta": "...", "ambigua": true, "motivo": "..."}``.

Uso: python eval/avaliar_esclarecimento.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from assistente_sql.esclarecimento import verificar

PASTA = Path(__file__).resolve().parent
ARQUIVO_AMBIGUAS = PASTA / "perguntas_ambiguas.jsonl"
ARQUIVOS_CLAROS = (PASTA / "perguntas.jsonl", PASTA / "perguntas_dev.jsonl")
PASTA_RESULTADOS = PASTA / "resultados"
META_AMBIGUIDADE_PCT = 60


def _ler(arquivo: Path) -> list[dict[str, Any]]:
    with arquivo.open(encoding="utf-8") as entrada:
        return [json.loads(linha) for linha in entrada if linha.strip()]


def avaliar() -> dict[str, Any]:
    claras = [p for arquivo in ARQUIVOS_CLAROS for p in _ler(arquivo)]
    ambiguas: list[dict[str, Any]] = []
    if ARQUIVO_AMBIGUAS.exists():
        marcadas = _ler(ARQUIVO_AMBIGUAS)
        ambiguas = [p for p in marcadas if p.get("ambigua")]
        claras += [p for p in marcadas if not p.get("ambigua")]

    def registro(p: dict[str, Any]) -> dict[str, Any]:
        esclarecimento = verificar(p["pergunta"])
        return {
            "id": p["id"],
            "pergunta": p["pergunta"],
            "pediu_esclarecimento": esclarecimento is not None,
            "regra": esclarecimento.regra if esclarecimento else None,
        }

    resultado_ambiguas = [registro(p) for p in ambiguas]
    resultado_claras = [registro(p) for p in claras]
    detectadas = sum(r["pediu_esclarecimento"] for r in resultado_ambiguas)
    desnecessarios = [r for r in resultado_claras if r["pediu_esclarecimento"]]
    return {
        "data_utc": datetime.now(UTC).isoformat(),
        "ambiguas": {
            "arquivo": ARQUIVO_AMBIGUAS.name if ARQUIVO_AMBIGUAS.exists() else None,
            "total": len(ambiguas),
            "pediu_esclarecimento": detectadas,
            "pct": round(100 * detectadas / len(ambiguas), 1) if ambiguas else None,
            "meta_pct": META_AMBIGUIDADE_PCT,
            "nao_detectadas": [r for r in resultado_ambiguas if not r["pediu_esclarecimento"]],
        },
        "claras": {
            "total": len(claras),
            "esclarecimento_desnecessario": len(desnecessarios),
            "pct": round(100 * len(desnecessarios) / len(claras), 1) if claras else None,
            "casos": desnecessarios,
        },
        "detalhes": resultado_ambiguas,
    }


def main() -> None:
    resumo = avaliar()
    identificador = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destino = PASTA_RESULTADOS / f"esclarecimento_{identificador}.json"
    destino.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    ambiguas, claras = resumo["ambiguas"], resumo["claras"]
    if ambiguas["arquivo"] is None:
        print(f"Falta {ARQUIVO_AMBIGUAS.name}: só as perguntas claras foram medidas.")
    else:
        print(
            f"Ambíguas: {ambiguas['pediu_esclarecimento']}/{ambiguas['total']} "
            f"({ambiguas['pct']}%, meta ≥ {META_AMBIGUIDADE_PCT}%)"
        )
    print(
        f"Claras com esclarecimento desnecessário: "
        f"{claras['esclarecimento_desnecessario']}/{claras['total']} ({claras['pct']}%)"
    )
    print(f"resultado: {destino}")


if __name__ == "__main__":
    main()
