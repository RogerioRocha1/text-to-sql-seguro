"""Validador de SQL: decide se uma consulta gerada pelo modelo pode ir ao banco.

Regras (todas precisam passar):
1. A consulta precisa ser SQL válido no dialeto do DuckDB.
2. Exatamente um comando, e ele precisa ser uma leitura (SELECT, com ou sem
   WITH, ou UNION/INTERSECT/EXCEPT de SELECTs).
3. Nenhum comando de escrita ou administração em nenhum ponto da árvore.
4. Só tabelas da lista permitida (ou nomes definidos em WITH), no schema
   ``main``. Isso também bloqueia leitura direta de arquivos (FROM 'x.csv').
5. Nenhuma função que leia arquivos, variáveis de ambiente ou metadados do
   sistema.
6. LIMIT obrigatório: se faltar, é adicionado; se passar do máximo, é reduzido.

A estimativa de custo pelo EXPLAIN depende do banco e entra no Marco 2.
"""

from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

DIALETO = "duckdb"
LIMITE_PADRAO = 1000

# Raiz aceita: SELECT (inclui WITH) ou operações de conjunto entre SELECTs.
_RAIZES_PERMITIDAS = (exp.Select, exp.SetOperation)

# Nós que nunca podem aparecer, em nenhum ponto da consulta.
_NOS_PROIBIDOS = tuple(
    getattr(exp, nome)
    for nome in (
        "Insert",
        "Update",
        "Delete",
        "Merge",
        "Drop",
        "Create",
        "Alter",
        "Copy",
        "Command",
        "Pragma",
        "Attach",
        "Detach",
        "Install",
        "LoadData",
        "Transaction",
        "Use",
    )
    if hasattr(exp, nome)
)

_FUNCOES_PROIBIDAS = {
    "glob",
    "getenv",
    "sniff_csv",
    "query",
    "query_table",
    "current_setting",
    "system",
}
_PREFIXOS_PROIBIDOS = ("read_", "parquet_", "duckdb_", "pragma_", "pg_", "iceberg_", "delta_")

_SCHEMAS_PERMITIDOS = {"", "main"}


@dataclass(frozen=True)
class ResultadoValidacao:
    aprovada: bool
    sql: str | None = None
    motivo: str | None = None


def _reprovar(motivo: str) -> ResultadoValidacao:
    return ResultadoValidacao(aprovada=False, motivo=motivo)


def _nome_funcao(no: exp.Func) -> str:
    if isinstance(no, exp.Anonymous):
        return str(no.name).lower()
    return no.sql_name().lower()


def _funcao_proibida(nome: str) -> bool:
    return nome in _FUNCOES_PROIBIDAS or nome.startswith(_PREFIXOS_PROIBIDOS)


def validar(
    sql: str,
    tabelas_permitidas: set[str] | frozenset[str],
    limite_maximo: int = LIMITE_PADRAO,
) -> ResultadoValidacao:
    """Valida ``sql`` e devolve a versão segura, com LIMIT aplicado."""
    if not sql or not sql.strip():
        return _reprovar("A consulta está vazia.")

    try:
        comandos = sqlglot.parse(sql, read=DIALETO)
    except ParseError:
        return _reprovar("A consulta não é um SQL válido.")

    semicolon = getattr(exp, "Semicolon", None)
    comandos = [
        c for c in comandos if c is not None and not (semicolon and isinstance(c, semicolon))
    ]
    if len(comandos) != 1:
        return _reprovar("Só é permitido um comando por consulta.")

    raiz = comandos[0]
    if not isinstance(raiz, _RAIZES_PERMITIDAS):
        return _reprovar("Só consultas de leitura (SELECT) são permitidas.")

    for no in raiz.walk():
        if isinstance(no, _NOS_PROIBIDOS):
            return _reprovar("A consulta contém um comando que altera ou administra o banco.")

    nomes_cte = {cte.alias_or_name.lower() for cte in raiz.find_all(exp.CTE)}
    permitidas = {t.lower() for t in tabelas_permitidas} | nomes_cte

    for tabela in raiz.find_all(exp.Table):
        if not isinstance(tabela.this, exp.Identifier):
            return _reprovar("Funções no lugar de tabelas não são permitidas.")
        if tabela.catalog or tabela.db.lower() not in _SCHEMAS_PERMITIDOS:
            return _reprovar(f"O schema '{tabela.db}' não pode ser consultado.")
        if tabela.name.lower() not in permitidas:
            return _reprovar(f"A tabela '{tabela.name}' não existe ou não pode ser consultada.")

    for funcao in raiz.find_all(exp.Func):
        nome = _nome_funcao(funcao)
        if _funcao_proibida(nome):
            return _reprovar(f"A função '{nome}' não é permitida.")

    limite = raiz.args.get("limit")
    if limite is None:
        raiz = raiz.limit(limite_maximo)
    else:
        valor = limite.expression if isinstance(limite, exp.Limit) else None
        if not (isinstance(valor, exp.Literal) and valor.is_int):
            return _reprovar("O limite de linhas precisa ser um número inteiro.")
        if int(valor.this) > limite_maximo:
            raiz = raiz.limit(limite_maximo)

    return ResultadoValidacao(aprovada=True, sql=raiz.sql(dialect=DIALETO))
