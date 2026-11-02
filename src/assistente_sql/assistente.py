"""Fluxo ponta a ponta: pergunta -> SQL gerado -> validação -> custo -> execução.

A conexão recebida deve ser do usuário ``leitor``. Mesmo assim, cada pergunta
roda numa transação marcada como somente leitura e sempre desfeita no final.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import psycopg

from assistente_sql.esquema import TABELAS_CONSULTAVEIS
from assistente_sql.gerador import Modelo, extrair_sql, montar_mensagens
from assistente_sql.validador import (
    CUSTO_MAXIMO_PADRAO,
    LIMITE_PADRAO,
    validar,
    verificar_custo,
)

log = logging.getLogger("assistente_sql")


@dataclass(frozen=True)
class Configuracao:
    ollama_url: str = "http://localhost:11434"
    ollama_modelo: str = "qwen2.5-coder:7b"
    database_url_leitor: str | None = None
    limite_linhas: int = LIMITE_PADRAO
    custo_maximo: float = CUSTO_MAXIMO_PADRAO

    @classmethod
    def do_ambiente(cls) -> Configuracao:
        return cls(
            ollama_url=os.environ.get("OLLAMA_URL", cls.ollama_url),
            ollama_modelo=os.environ.get("OLLAMA_MODELO", cls.ollama_modelo),
            database_url_leitor=os.environ.get("DATABASE_URL_LEITOR"),
            limite_linhas=int(os.environ.get("LIMITE_LINHAS", LIMITE_PADRAO)),
            custo_maximo=float(os.environ.get("CUSTO_MAXIMO", CUSTO_MAXIMO_PADRAO)),
        )


@dataclass
class Resposta:
    """Resultado de uma pergunta. ``situacao`` diz onde o fluxo terminou."""

    pergunta: str
    situacao: str = "ok"  # ok | bloqueada | erro_execucao | erro_modelo
    texto_modelo: str | None = None
    sql_gerado: str | None = None
    sql_executado: str | None = None
    motivo: str | None = None
    custo_estimado: float | None = None
    colunas: list[str] = field(default_factory=list)
    linhas: list[tuple[Any, ...]] = field(default_factory=list)
    tempos: dict[str, float] = field(default_factory=dict)
    tokens_entrada: int = 0
    tokens_saida: int = 0


def responder(
    pergunta: str,
    modelo: Modelo,
    conexao: psycopg.Connection,
    esquema: str,
    limite_linhas: int = LIMITE_PADRAO,
    custo_maximo: float = CUSTO_MAXIMO_PADRAO,
) -> Resposta:
    resposta = Resposta(pergunta=pergunta)

    try:
        gerada = modelo.gerar(montar_mensagens(pergunta, esquema))
    except Exception as erro:  # rede, timeout, modelo não baixado
        log.exception("falha ao chamar o modelo")
        resposta.situacao, resposta.motivo = "erro_modelo", f"O modelo não respondeu: {erro}"
        return resposta
    resposta.texto_modelo = gerada.texto
    resposta.sql_gerado = extrair_sql(gerada.texto)
    resposta.tokens_entrada, resposta.tokens_saida = gerada.tokens_entrada, gerada.tokens_saida
    resposta.tempos["modelo"] = gerada.segundos

    validacao = validar(resposta.sql_gerado, TABELAS_CONSULTAVEIS, limite_linhas)
    if not validacao.aprovada:
        resposta.situacao, resposta.motivo = "bloqueada", validacao.motivo
        _registrar(resposta)
        return resposta

    conexao.read_only = True
    try:
        with conexao.cursor() as cursor:
            inicio = time.perf_counter()
            custo = verificar_custo(cursor, validacao, custo_maximo)
            resposta.tempos["custo"] = time.perf_counter() - inicio
            resposta.custo_estimado = custo.custo_estimado
            if not custo.aprovada:
                resposta.situacao, resposta.motivo = "bloqueada", custo.motivo
                return resposta

            resposta.sql_executado = custo.sql
            inicio = time.perf_counter()
            cursor.execute(custo.sql)
            resposta.colunas = [d.name for d in cursor.description or []]
            resposta.linhas = cursor.fetchall()
            resposta.tempos["execucao"] = time.perf_counter() - inicio
    except psycopg.Error as erro:
        resposta.situacao = "erro_execucao"
        resposta.motivo = f"O banco recusou a consulta: {erro.diag.message_primary or erro}"
    finally:
        conexao.rollback()
        _registrar(resposta)
    return resposta


def main(argv: list[str] | None = None) -> None:
    """Uso: python -m assistente_sql.assistente "Quanto o Ministério da Saúde pagou em 2025?" """
    import argparse

    from assistente_sql.gerador import ModeloOllama, formatar_esquema, ler_esquema

    parser = argparse.ArgumentParser(description="Responde perguntas pela linha de comando.")
    parser.add_argument("perguntas", nargs="+")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    config = Configuracao.do_ambiente()
    if not config.database_url_leitor:
        raise SystemExit("Defina DATABASE_URL_LEITOR.")
    modelo = ModeloOllama(config.ollama_url, config.ollama_modelo)
    with psycopg.connect(config.database_url_leitor) as conexao:
        with conexao.cursor() as cursor:
            esquema = formatar_esquema(ler_esquema(cursor))
        conexao.rollback()
        for pergunta in args.perguntas:
            r = responder(
                pergunta, modelo, conexao, esquema, config.limite_linhas, config.custo_maximo
            )
            print(f"\n## {pergunta}\nsituação: {r.situacao}  tempos: {r.tempos}")
            print(f"SQL: {r.sql_executado or r.sql_gerado}")
            if r.motivo:
                print(f"motivo: {r.motivo}")
            for linha in r.linhas[:10]:
                print("  ", linha)


def _registrar(resposta: Resposta) -> None:
    log.info(
        "pergunta=%r situacao=%s linhas=%d custo=%s tempos=%s sql=%r motivo=%r",
        resposta.pergunta,
        resposta.situacao,
        len(resposta.linhas),
        resposta.custo_estimado,
        {k: round(v, 2) for k, v in resposta.tempos.items()},
        resposta.sql_executado or resposta.sql_gerado,
        resposta.motivo,
    )


if __name__ == "__main__":
    main()
