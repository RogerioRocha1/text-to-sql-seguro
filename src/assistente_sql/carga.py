"""Baixa os CSV de despesas do Portal da Transparência e carrega no PostgreSQL.

Uso:
    python -m assistente_sql.carga                # baixa (se preciso) e carrega 2025
    python -m assistente_sql.carga --so-baixar    # só baixa os ZIPs para DADOS_DIR

Variáveis de ambiente:
    DATABASE_URL  conexão com permissão de escrita (usuário dono do banco)
    DADOS_DIR     pasta onde os ZIPs ficam guardados (padrão: data/raw)

A carga roda numa única transação: ou o banco fica com a foto nova completa,
ou continua com a anterior.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import IO

import psycopg

from assistente_sql import esquema
from assistente_sql.fontes import (
    EXECUCAO,
    ORCAMENTO,
    Fonte,
    arquivos_do_ano,
    conferir_cabecalho,
    ler_cabecalho,
)

log = logging.getLogger("assistente_sql.carga")

ANO_PADRAO = 2025
TENTATIVAS = 3
BLOCO = 1 << 20


def baixar(url: str, destino: Path) -> None:
    """Baixa ``url`` para ``destino``, sem refazer se o ZIP já existe e é válido."""
    if destino.exists() and zipfile.is_zipfile(destino):
        log.info("já baixado: %s", destino.name)
        return

    parcial = destino.with_suffix(destino.suffix + ".part")
    pedido = urllib.request.Request(url, headers={"User-Agent": "assistente-sql/0.1"})  # noqa: S310
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            log.info("baixando %s (tentativa %d)", url, tentativa)
            with urllib.request.urlopen(pedido, timeout=120) as resposta, parcial.open("wb") as f:  # noqa: S310
                shutil.copyfileobj(resposta, f, BLOCO)
            if not zipfile.is_zipfile(parcial):
                raise ValueError(f"{url} não devolveu um arquivo ZIP")
            parcial.replace(destino)
            return
        except Exception:
            if tentativa == TENTATIVAS:
                raise
            log.warning("falha ao baixar %s, tentando de novo", url, exc_info=True)
            time.sleep(5 * tentativa)


def abrir_csv(caminho_zip: Path) -> tuple[zipfile.ZipFile, IO[bytes]]:
    """Abre o único CSV de dentro do ZIP da CGU, sem extrair para o disco."""
    arquivo = zipfile.ZipFile(caminho_zip)
    csvs = [n for n in arquivo.namelist() if n.lower().endswith(".csv")]
    if len(csvs) != 1:
        arquivo.close()
        raise ValueError(f"{caminho_zip.name}: esperado 1 CSV, encontrados {len(csvs)}")
    return arquivo, arquivo.open(csvs[0])


def copiar_para_staging(cursor, fonte: Fonte, caminho_zip: Path) -> None:
    """Confere o cabeçalho e envia o restante do CSV para o staging via COPY."""
    arquivo, csv = abrir_csv(caminho_zip)
    with arquivo, csv:
        conferir_cabecalho(fonte, ler_cabecalho(csv.readline()))
        colunas = ", ".join(fonte.colunas_staging)
        comando = (
            f"COPY carga.{fonte.tabela_staging} ({colunas}) FROM STDIN "
            "(FORMAT csv, DELIMITER ';', QUOTE '\"', ENCODING 'WIN1252')"
        )
        with cursor.copy(comando) as copia:
            while bloco := csv.read(BLOCO):
                copia.write(bloco)


def carregar(database_url: str, arquivos: list[tuple[Fonte, Path]]) -> dict[str, int]:
    # search_path fixo: o padrão "$user", public mandaria as tabelas para o schema
    # "carga" quando o usuário dono também se chama carga.
    with (
        psycopg.connect(database_url, options="-c search_path=public") as conexao,
        conexao.cursor() as cursor,
    ):
        cursor.execute(esquema.PREPARAR_STAGING)
        for fonte in (ORCAMENTO, EXECUCAO):
            cursor.execute(esquema.ddl_staging(fonte))

        for fonte, caminho in arquivos:
            log.info("copiando %s", caminho.name)
            copiar_para_staging(cursor, fonte, caminho)

        log.info("recriando o esquema consultável")
        cursor.execute(esquema.CRIAR_ESQUEMA)
        log.info("transformando os dados")
        cursor.execute(esquema.TRANSFORMAR)
        cursor.execute(esquema.LIMPAR_STAGING)

        contagens = {}
        for tabela in esquema.TABELAS_CONSULTAVEIS:
            cursor.execute(f"SELECT count(*) FROM {tabela}")  # noqa: S608 (nome fixo)
            contagens[tabela] = cursor.fetchone()[0]
    return contagens


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ano", type=int, default=ANO_PADRAO)
    parser.add_argument("--so-baixar", action="store_true", help="não conecta ao banco")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    pasta = Path(os.environ.get("DADOS_DIR", "data/raw"))
    pasta.mkdir(parents=True, exist_ok=True)

    arquivos = []
    for fonte, url, nome in arquivos_do_ano(args.ano):
        destino = pasta / nome
        baixar(url, destino)
        arquivos.append((fonte, destino))

    if args.so_baixar:
        return

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("Defina DATABASE_URL para carregar no banco.")

    for tabela, total in carregar(database_url, arquivos).items():
        log.info("%-16s %10d linhas", tabela, total)


if __name__ == "__main__":
    main()
