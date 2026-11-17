"""Avaliação experimental do assistente Text-to-SQL.

Compara o assistente com esquema dinâmico e um baseline sem esquema
 dinâmico, usando as mesmas perguntas, modelo e proteções de segurança.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import psycopg

from assistente_sql.assistente import Configuracao, responder
from assistente_sql.esquema import TABELAS_CONSULTAVEIS
from assistente_sql.gerador import ModeloOllama, formatar_esquema, ler_esquema
from assistente_sql.validador import validar, verificar_custo

PASTA = Path(__file__).resolve().parent
ARQUIVO_PERGUNTAS = PASTA / "perguntas.jsonl"
PASTA_RESULTADOS = PASTA / "resultados"

COLUNAS_CSV = [
    "modo",
    "id",
    "categoria",
    "dificuldade",
    "pergunta",
    "situacao",
    "acertou",
    "sql_referencia",
    "sql_gerado",
    "sql_executado",
    "resultado_esperado",
    "resultado_obtido",
    "motivo",
    "custo_estimado",
    "tempo_modelo_s",
    "tempo_custo_s",
    "tempo_execucao_s",
    "tokens_entrada",
    "tokens_saida",
]


def carregar_perguntas() -> list[dict[str, Any]]:
    perguntas: list[dict[str, Any]] = []

    with ARQUIVO_PERGUNTAS.open(encoding="utf-8") as arquivo:
        for numero, linha in enumerate(arquivo, start=1):
            if not linha.strip():
                continue
            try:
                pergunta = json.loads(linha)
            except json.JSONDecodeError as erro:
                raise ValueError(f"JSON inválido na linha {numero}: {erro}") from erro
            perguntas.append(pergunta)

    if len(perguntas) != 50:
        raise ValueError(f"Esperadas 50 perguntas, mas foram encontradas {len(perguntas)}.")

    ids = [p["id"] for p in perguntas]
    if len(set(ids)) != len(ids):
        raise ValueError("Existem IDs duplicados no arquivo JSONL.")

    return perguntas


def _decimal_centavos(valor: Any) -> Decimal:
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def valor_igual(real: Any, esperado: Any) -> bool:
    """Compara números com precisão de centavos e textos exatamente.

    No fluxo ao vivo, psycopg entrega valores numéricos como Decimal e o
    JSONL guarda os resultados esperados como strings. Para reavaliar CSVs
    históricos, ambos podem estar serializados como strings; nesse caso,
    strings numéricas com parte decimal também são comparadas em centavos.
    Códigos e contagens inteiros continuam sendo comparados textualmente.
    """
    if real is None or esperado is None:
        return real is None and esperado is None

    if isinstance(real, bool) or isinstance(esperado, bool):
        return real == esperado

    tipos_numericos = (int, float, Decimal)
    algum_numerico = isinstance(real, tipos_numericos) or isinstance(esperado, tipos_numericos)

    if algum_numerico:
        try:
            return _decimal_centavos(real) == _decimal_centavos(esperado)
        except (InvalidOperation, ValueError, TypeError):
            return False

    # Nos CSVs antigos, valores decimais foram serializados como strings.
    # Exigimos ponto decimal ou notação científica para não converter códigos
    # inteiros como "00123" em números e perder zeros à esquerda.
    if isinstance(real, str) and isinstance(esperado, str):
        if real.strip() == esperado.strip():
            return True
        strings_decimais = (
            "." in real or "e" in real.lower() or "." in esperado or "e" in esperado.lower()
        )
        if strings_decimais:
            try:
                return _decimal_centavos(real) == _decimal_centavos(esperado)
            except (InvalidOperation, ValueError, TypeError):
                return False

    return str(real).strip() == str(esperado).strip()


def _linhas_iguais(
    linha_real: list[Any],
    linha_esperada: list[Any],
) -> bool:
    if len(linha_real) != len(linha_esperada):
        return False
    return all(
        valor_igual(real, esperado)
        for real, esperado in zip(linha_real, linha_esperada, strict=True)
    )


def resultados_iguais(
    reais: list[list[Any]],
    esperados: list[list[Any]],
    comparar_ordem: bool = True,
) -> bool:
    """Compara resultados; ignora ordem de linhas quando a pergunta permitir."""
    if len(reais) != len(esperados):
        return False

    if comparar_ordem:
        return all(
            _linhas_iguais(real, esperado) for real, esperado in zip(reais, esperados, strict=True)
        )

    # Comparação como multiconjunto: ignora a ordem, mas preserva duplicatas.
    pendentes = list(esperados)
    for linha_real in reais:
        encontrada = None
        for indice, linha_esperada in enumerate(pendentes):
            if _linhas_iguais(linha_real, linha_esperada):
                encontrada = indice
                break
        if encontrada is None:
            return False
        pendentes.pop(encontrada)

    return not pendentes


def serializar(valor: Any) -> Any:
    """Converte tipos do PostgreSQL em valores compatíveis com JSON."""
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, (list, tuple)):
        return [serializar(item) for item in valor]
    return valor


def executar_referencia(
    pergunta: dict[str, Any],
    conexao: psycopg.Connection,
    config: Configuracao,
) -> list[list[Any]]:
    """Executa referência após validar SQL, custo e somente leitura."""
    conexao.read_only = True
    try:
        with conexao.cursor() as cursor:
            validacao = validar(
                pergunta["sql_referencia"],
                TABELAS_CONSULTAVEIS,
                config.limite_linhas,
            )
            if not validacao.aprovada:
                raise RuntimeError(f"SQL de referência bloqueado: {validacao.motivo}")

            custo = verificar_custo(cursor, validacao, config.custo_maximo)
            if not custo.aprovada:
                raise RuntimeError(f"SQL de referência excedeu o custo: {custo.motivo}")

            cursor.execute(custo.sql)
            return [list(linha) for linha in cursor.fetchall()]
    finally:
        conexao.rollback()


def conferir_referencias(
    perguntas: list[dict[str, Any]],
    conexao: psycopg.Connection,
    config: Configuracao,
) -> None:
    """Confere todas as referências; mantém a ordem declarada pelo SQL de referência."""
    problemas = []
    print("\n=== CONFERÊNCIA DAS REFERÊNCIAS ===", flush=True)

    for pergunta in perguntas:
        try:
            resultado = executar_referencia(pergunta, conexao, config)
            esperado = pergunta["resultado_esperado"]
            if resultados_iguais(resultado, esperado, comparar_ordem=True):
                print(f"[OK] {pergunta['id']}", flush=True)
            else:
                problemas.append(
                    {
                        "id": pergunta["id"],
                        "esperado": esperado,
                        "obtido": serializar(resultado),
                    }
                )
                print(
                    f"[DIVERGÊNCIA] {pergunta['id']}: resultado armazenado diferente do banco",
                    flush=True,
                )
        except Exception as erro:
            problemas.append({"id": pergunta["id"], "erro": str(erro)})
            print(f"[ERRO] {pergunta['id']}: {erro}", flush=True)

    if problemas:
        print("\nForam encontrados problemas nas referências:")
        print(json.dumps(problemas, ensure_ascii=False, indent=2))
        raise SystemExit("Avaliação interrompida. Corrija as referências antes de continuar.")

    print(
        f"\nTodas as {len(perguntas)} referências foram conferidas.",
        flush=True,
    )


def avaliar_condicao(
    modo: str,
    perguntas: list[dict[str, Any]],
    modelo: ModeloOllama,
    conexao: psycopg.Connection,
    esquema: str,
    config: Configuracao,
    escritor: csv.DictWriter,
    arquivo_csv: Any,
) -> list[dict[str, Any]]:
    """Executa uma condição experimental para todas as perguntas."""
    resultados = []
    esquema_usado = esquema if modo == "completo" else ""
    print(f"\n=== INÍCIO: {modo.upper()} ===", flush=True)

    for indice, pergunta in enumerate(perguntas, start=1):
        try:
            resposta = responder(
                pergunta["pergunta"],
                modelo,
                conexao,
                esquema_usado,
                config.limite_linhas,
                config.custo_maximo,
            )
            linhas = [list(linha) for linha in resposta.linhas]
            acertou = resposta.situacao == "ok" and resultados_iguais(
                linhas,
                pergunta["resultado_esperado"],
                comparar_ordem=pergunta.get("comparar_ordem", False),
            )

            registro = {
                "modo": modo,
                "id": pergunta["id"],
                "categoria": pergunta["categoria"],
                "dificuldade": pergunta["dificuldade"],
                "pergunta": pergunta["pergunta"],
                "situacao": resposta.situacao,
                "acertou": acertou,
                "sql_referencia": pergunta["sql_referencia"],
                "sql_gerado": resposta.sql_gerado,
                "sql_executado": resposta.sql_executado,
                "resultado_esperado": json.dumps(
                    pergunta["resultado_esperado"], ensure_ascii=False
                ),
                "resultado_obtido": json.dumps(serializar(linhas), ensure_ascii=False),
                "motivo": resposta.motivo,
                "custo_estimado": resposta.custo_estimado,
                "tempo_modelo_s": resposta.tempos.get("modelo"),
                "tempo_custo_s": resposta.tempos.get("custo"),
                "tempo_execucao_s": resposta.tempos.get("execucao"),
                "tokens_entrada": resposta.tokens_entrada,
                "tokens_saida": resposta.tokens_saida,
            }
        except Exception as erro:
            registro = {
                "modo": modo,
                "id": pergunta["id"],
                "categoria": pergunta["categoria"],
                "dificuldade": pergunta["dificuldade"],
                "pergunta": pergunta["pergunta"],
                "situacao": "erro_avaliador",
                "acertou": False,
                "sql_referencia": pergunta["sql_referencia"],
                "resultado_esperado": json.dumps(
                    pergunta["resultado_esperado"], ensure_ascii=False
                ),
                "resultado_obtido": "[]",
                "motivo": str(erro),
            }

        escritor.writerow(registro)
        arquivo_csv.flush()
        resultados.append(registro)
        status = "ACERTO" if registro["acertou"] else "ERRO"
        tempo = registro.get("tempo_modelo_s")
        print(
            f"[{modo}] {indice}/{len(perguntas)} {pergunta['id']}: "
            f"{status} | situação={registro['situacao']} | "
            f"tempo_modelo={tempo}",
            flush=True,
        )

    return resultados


def calcular_metricas(resultados: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(resultados)
    if total == 0:
        return {"total": 0, "acertos": 0, "acuracia_execucao": 0}

    acertos = sum(bool(r["acertou"]) for r in resultados)
    executadas = sum(r["situacao"] == "ok" for r in resultados)

    def media(campo: str) -> float | None:
        valores = [float(r[campo]) for r in resultados if r.get(campo) not in (None, "")]
        return round(sum(valores) / len(valores), 3) if valores else None

    return {
        "total": total,
        "acertos": acertos,
        "acuracia_execucao": round(100 * acertos / total, 2),
        "consultas_executadas": executadas,
        "taxa_execucao": round(100 * executadas / total, 2),
        "bloqueadas": sum(r["situacao"] == "bloqueada" for r in resultados),
        "erros_execucao": sum(r["situacao"] == "erro_execucao" for r in resultados),
        "erros_modelo": sum(r["situacao"] == "erro_modelo" for r in resultados),
        "erros_avaliador": sum(r["situacao"] == "erro_avaliador" for r in resultados),
        "tempo_medio_modelo_s": media("tempo_modelo_s"),
        "tempo_medio_custo_s": media("tempo_custo_s"),
        "tempo_medio_execucao_s": media("tempo_execucao_s"),
    }


def calcular_resumo(resultados: list[dict[str, Any]]) -> dict[str, Any]:
    resumo = calcular_metricas(resultados)
    for campo, destino in (
        ("categoria", "por_categoria"),
        ("dificuldade", "por_dificuldade"),
    ):
        grupos: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for resultado in resultados:
            grupos[resultado[campo]].append(resultado)
        resumo[destino] = {nome: calcular_metricas(itens) for nome, itens in sorted(grupos.items())}
    return resumo


def reavaliar_csv_historico(
    caminho_csv: Path,
    perguntas: list[dict[str, Any]],
) -> tuple[Path, Path, dict[str, Any]]:
    """Recalcula a métrica de um CSV já gerado, sem chamar o modelo ou o banco."""
    perguntas_por_id = {p["id"]: p for p in perguntas}
    with caminho_csv.open("r", newline="", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)
        linhas = list(leitor)
        campos = list(leitor.fieldnames or [])

    resultados_por_modo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    linhas_atualizadas = []

    for linha in linhas:
        pergunta = perguntas_por_id.get(linha.get("id", ""))
        if pergunta is None:
            raise ValueError(f"O CSV contém ID ausente no JSONL: {linha.get('id')}")

        acertou = False
        if linha.get("situacao") == "ok":
            try:
                obtido = json.loads(linha.get("resultado_obtido") or "[]")
                acertou = resultados_iguais(
                    obtido,
                    pergunta["resultado_esperado"],
                    comparar_ordem=pergunta.get("comparar_ordem", False),
                )
            except (json.JSONDecodeError, TypeError):
                acertou = False

        linha["acertou"] = acertou
        linhas_atualizadas.append(linha)

        registro_metricas = dict(linha)
        registro_metricas["acertou"] = acertou
        resultados_por_modo[linha.get("modo", "desconhecido")].append(registro_metricas)

    identificador = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destino_csv = caminho_csv.with_name(f"{caminho_csv.stem}_reavaliado_{identificador}.csv")
    destino_json = destino_csv.with_suffix(".json")

    if "acertou" not in campos:
        campos.append("acertou")

    with destino_csv.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(linhas_atualizadas)

    resumo = {
        "csv_origem": caminho_csv.name,
        "data_reavaliacao_utc": datetime.now(UTC).isoformat(),
        "criterio_numerico": "arredondamento decimal a duas casas (ROUND_HALF_UP)",
        "criterio_ordem": (
            "ordem ignorada por padrão; preservada somente quando comparar_ordem=true no JSONL"
        ),
        "condicoes": {
            modo: calcular_resumo(registros) for modo, registros in resultados_por_modo.items()
        },
        "arquivo_resultados": destino_csv.name,
    }
    destino_json.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino_csv, destino_json, resumo


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia o assistente Text-to-SQL.")
    parser.add_argument(
        "--modo",
        choices=["completo", "baseline", "ambos"],
        default="ambos",
        help="Condição experimental a executar.",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Executa somente as primeiras N perguntas (teste preliminar).",
    )
    parser.add_argument(
        "--reavaliar-csv",
        type=Path,
        default=None,
        help="Recalcula um CSV anterior sem chamar o modelo nem o banco.",
    )
    args = parser.parse_args()

    perguntas = carregar_perguntas()

    if args.reavaliar_csv is not None:
        caminho = args.reavaliar_csv
        if not caminho.is_absolute():
            caminho = Path.cwd() / caminho
        if not caminho.is_file():
            raise SystemExit(f"CSV não encontrado: {caminho}")
        novo_csv, novo_json, resumo = reavaliar_csv_historico(caminho, perguntas)
        print("=== REAVALIAÇÃO HISTÓRICA CONCLUÍDA ===")
        for modo, metricas in resumo["condicoes"].items():
            print(
                f"{modo}: {metricas['acertos']}/{metricas['total']} acertos | "
                f"acurácia={metricas['acuracia_execucao']}%"
            )
        print(f"CSV reavaliado: {novo_csv}")
        print(f"Resumo: {novo_json}")
        return

    if args.limite is not None and args.limite <= 0:
        raise SystemExit("--limite precisa ser maior que zero.")

    config = Configuracao.do_ambiente()
    if not config.database_url_leitor:
        raise SystemExit("DATABASE_URL_LEITOR não está configurada.")

    perguntas_execucao = perguntas[: args.limite] if args.limite else perguntas
    modos = ["completo", "baseline"] if args.modo == "ambos" else [args.modo]

    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    identificador = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    caminho_csv = PASTA_RESULTADOS / f"resultados_{identificador}.csv"
    caminho_json = PASTA_RESULTADOS / f"resumo_{identificador}.json"

    print(f"Modelo: {config.ollama_modelo}")
    print(f"Perguntas no arquivo: {len(perguntas)}")
    print(f"Perguntas nesta execução: {len(perguntas_execucao)}")
    print(f"Modos: {', '.join(modos)}")
    print(f"Limite de linhas: {config.limite_linhas}")
    print(f"Custo máximo: {config.custo_maximo}")
    print(f"CSV: {caminho_csv}", flush=True)

    todos_resultados: dict[str, list[dict[str, Any]]] = {}

    with psycopg.connect(config.database_url_leitor) as conexao:
        conexao.read_only = True
        print("\nObtendo esquema do PostgreSQL...", flush=True)
        with conexao.cursor() as cursor:
            esquema = formatar_esquema(ler_esquema(cursor))
        conexao.rollback()
        print("Esquema obtido.", flush=True)

        conferir_referencias(perguntas_execucao, conexao, config)
        modelo = ModeloOllama(config.ollama_url, config.ollama_modelo)

        with caminho_csv.open("w", newline="", encoding="utf-8-sig") as arquivo_csv:
            escritor = csv.DictWriter(
                arquivo_csv,
                fieldnames=COLUNAS_CSV,
                extrasaction="ignore",
            )
            escritor.writeheader()
            arquivo_csv.flush()

            for modo in modos:
                resultados = avaliar_condicao(
                    modo,
                    perguntas_execucao,
                    modelo,
                    conexao,
                    esquema,
                    config,
                    escritor,
                    arquivo_csv,
                )
                todos_resultados[modo] = resultados

    resumo = {
        "data_utc": datetime.now(UTC).isoformat(),
        "modelo": config.ollama_modelo,
        "quantidade_perguntas_arquivo": len(perguntas),
        "quantidade_perguntas_executadas": len(perguntas_execucao),
        "execucao_completa": len(perguntas_execucao) == len(perguntas),
        "modo": modos,
        "limite_linhas": config.limite_linhas,
        "custo_maximo": config.custo_maximo,
        "referencias_conferidas": True,
        "condicoes": {
            modo: calcular_resumo(resultados) for modo, resultados in todos_resultados.items()
        },
        "arquivo_resultados": caminho_csv.name,
    }
    caminho_json.write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== RESUMO DA AVALIAÇÃO ===")
    for modo, metricas in resumo["condicoes"].items():
        print(
            f"{modo}: {metricas['acertos']}/{metricas['total']} acertos | "
            f"acurácia={metricas['acuracia_execucao']}% | "
            f"tempo médio do modelo={metricas['tempo_medio_modelo_s']} s"
        )
    print(f"\nCSV salvo em: {caminho_csv}")
    print(f"Resumo salvo em: {caminho_json}")


if __name__ == "__main__":
    main()
