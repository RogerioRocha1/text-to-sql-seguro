"""Validador de SQL: decide se uma consulta gerada pelo modelo pode ir ao banco.

Etapa 1, ``validar`` (sem banco; todas as regras precisam passar):
1. A consulta precisa ser SQL válido no dialeto do PostgreSQL.
2. Exatamente um comando, e ele precisa ser uma leitura (SELECT, com ou sem
   WITH, ou UNION/INTERSECT/EXCEPT de SELECTs).
3. Nenhum comando de escrita ou administração em nenhum ponto da árvore,
   incluindo CTE que altera dados, SELECT INTO (cria tabela) e FOR UPDATE.
4. Só tabelas da lista permitida (ou nomes definidos em WITH), no schema
   ``public``. Isso bloqueia pg_catalog, information_schema e funções no FROM.
5. Nenhuma função que leia arquivos, execute SQL em texto, altere estado
   (sequências, configurações) ou exponha dados do servidor.
6. LIMIT obrigatório: se faltar, é adicionado; se passar do máximo, é reduzido.

Etapa 2, ``verificar_custo`` (com banco): roda EXPLAIN, sem executar a
consulta, e recusa se o custo estimado pelo planejador passar do máximo.

A lista de funções proibidas é uma lista de bloqueio e, por isso, incompleta
por natureza. A garantia final vem do banco: o usuário ``leitor`` só tem
SELECT, roda em transação somente leitura e tem tempo máximo por consulta.
"""

from __future__ import annotations

from dataclasses import dataclass

import psycopg
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

DIALETO = "postgres"
LIMITE_PADRAO = 1000

# Medido no banco de 2025 (eval/README.md): consultas legítimas custam até
# ~50 mil; autojunções de execucao_mensal começam em ~30 milhões.
CUSTO_MAXIMO_PADRAO = 1_000_000

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
        "TruncateTable",
        "Copy",
        "Command",
        "Transaction",
        "Set",
        "Grant",
        "Revoke",
        "Into",  # SELECT ... INTO nova_tabela
        "Lock",  # SELECT ... FOR UPDATE / FOR SHARE
        "Pragma",
        "Attach",
        "Detach",
        "Install",
        "LoadData",
        "Use",
    )
    if hasattr(exp, nome)
)

_FUNCOES_PROIBIDAS = {
    # configuração e sequências (alteram estado)
    "set_config",
    "current_setting",
    "nextval",
    "setval",
    "currval",
    "lastval",
    # executam SQL recebido como texto
    "ts_stat",
    "ts_rewrite",
    # dados do servidor e da sessão
    "version",
    "current_version",
    "current_user",
    "session_user",
    "current_database",
    "current_schema",
    "current_schemas",
    # arquivos e ambiente (outros dialetos)
    "glob",
    "getenv",
    "system",
}
_PREFIXOS_PROIBIDOS = (
    "pg_",  # pg_sleep, pg_read_file, pg_ls_dir, pg_terminate_backend...
    "lo_",  # lo_import, lo_export (objetos grandes, leem e gravam arquivos)
    "dblink",
    "query_to_xml",  # executa a consulta passada como texto
    "cursor_to_xml",
    "table_to_xml",
    "schema_to_xml",
    "database_to_xml",
    "inet_",
    "binary_upgrade_",
    "read_",
)

_SCHEMAS_PERMITIDOS = {"", "public"}


@dataclass(frozen=True)
class ResultadoValidacao:
    aprovada: bool
    sql: str | None = None
    motivo: str | None = None
    custo_estimado: float | None = None


def _reprovar(motivo: str, custo_estimado: float | None = None) -> ResultadoValidacao:
    return ResultadoValidacao(aprovada=False, motivo=motivo, custo_estimado=custo_estimado)


def _nome_funcao(no: exp.Func) -> str:
    if isinstance(no, exp.Anonymous):
        return str(no.name).lower()
    return no.sql_name().lower()


def _funcao_proibida(nome: str) -> bool:
    return nome in _FUNCOES_PROIBIDAS or nome.startswith(_PREFIXOS_PROIBIDOS)


def validar(
    sql: str,
    tabelas_permitidas: set[str] | frozenset[str] | tuple[str, ...],
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
        if tabela.catalog:
            return _reprovar(f"O banco '{tabela.catalog}' não pode ser consultado.")
        if tabela.db.lower() not in _SCHEMAS_PERMITIDOS:
            return _reprovar(f"O schema '{tabela.db}' não pode ser consultado.")
        if tabela.name.lower() not in permitidas:
            return _reprovar(f"A tabela '{tabela.name}' não existe ou não pode ser consultada.")

    for funcao in raiz.find_all(exp.Func):
        nome = _nome_funcao(funcao)
        if _funcao_proibida(nome):
            return _reprovar(f"A função '{nome}' não é permitida.")

    limite = raiz.args.get("limit")
    if isinstance(limite, exp.Fetch):
        return _reprovar("Use LIMIT em vez de FETCH FIRST para limitar as linhas.")
    if limite is None:
        raiz = raiz.limit(limite_maximo)
    else:
        valor = limite.expression if isinstance(limite, exp.Limit) else None
        if not (isinstance(valor, exp.Literal) and valor.is_int):
            return _reprovar("O limite de linhas precisa ser um número inteiro.")
        if int(valor.this) > limite_maximo:
            raiz = raiz.limit(limite_maximo)

    return ResultadoValidacao(aprovada=True, sql=raiz.sql(dialect=DIALETO))


def verificar_custo(
    cursor: psycopg.Cursor,
    resultado: ResultadoValidacao,
    custo_maximo: float = CUSTO_MAXIMO_PADRAO,
) -> ResultadoValidacao:
    """Estima o custo de uma consulta já aprovada por ``validar``, sem executá-la.

    Só aceita resultados aprovados: o texto que vai ao EXPLAIN é o SQL
    regenerado pelo SQLGlot, nunca o texto original do modelo. Se o banco
    recusar a consulta (coluna inexistente, tipo errado), devolve reprovação
    com a mensagem do banco; quem chama decide se desfaz a transação.
    """
    if not resultado.aprovada or resultado.sql is None:
        raise ValueError("verificar_custo só recebe consultas aprovadas por validar().")

    try:
        cursor.execute(f"EXPLAIN (FORMAT JSON) {resultado.sql}")  # noqa: S608 (SQL validado)
        plano = cursor.fetchone()[0][0]["Plan"]
    except psycopg.Error as erro:
        mensagem = erro.diag.message_primary or str(erro)
        return _reprovar(f"O banco recusou a consulta: {mensagem}")

    custo = float(plano["Total Cost"])
    if custo > custo_maximo:
        return _reprovar(
            f"A consulta é pesada demais (custo estimado {custo:,.0f}, máximo "
            f"{custo_maximo:,.0f}). Tente filtrar mais ou evitar junções sem condição.",
            custo_estimado=custo,
        )
    return ResultadoValidacao(aprovada=True, sql=resultado.sql, custo_estimado=custo)
