"""Testes do validador. Cada ataque do catálogo deve virar um caso aqui."""

import pytest

from assistente_sql import validar

TABELAS = frozenset({"orgao", "funcao", "programa_acao", "orcamento", "execucao_mensal"})


def aprova(sql: str, limite: int = 1000):
    resultado = validar(sql, TABELAS, limite_maximo=limite)
    assert resultado.aprovada, resultado.motivo
    return resultado.sql


# --- Consultas legítimas ---------------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM orgao",
        "select nome from ORGAO where codigo = 26000",
        "SELECT o.nome, SUM(e.valor_pago) AS pago FROM execucao_mensal e "
        "JOIN orgao o ON o.codigo = e.codigo_orgao GROUP BY o.nome ORDER BY pago DESC",
        "WITH total AS (SELECT codigo_orgao, SUM(valor_pago) v FROM execucao_mensal "
        "GROUP BY 1) SELECT * FROM total",
        "SELECT codigo FROM orgao UNION SELECT codigo_orgao FROM orcamento",
        "SELECT * FROM main.orgao",
        "SELECT * FROM orgao;",
        "SELECT * FROM orgao; -- comentário no fim",
    ],
)
def test_aprova_consultas_de_leitura(sql):
    aprova(sql)


def test_adiciona_limit_quando_falta():
    assert aprova("SELECT * FROM orgao", limite=50).endswith("LIMIT 50")


def test_reduz_limit_acima_do_maximo():
    assert aprova("SELECT * FROM orgao LIMIT 99999", limite=100).endswith("LIMIT 100")


def test_mantem_limit_menor_que_o_maximo():
    assert aprova("SELECT * FROM orgao LIMIT 10", limite=100).endswith("LIMIT 10")


# --- Catálogo de ataques e consultas que devem ser bloqueadas -------------


@pytest.mark.parametrize(
    "sql",
    [
        # escrita e estrutura
        "DROP TABLE orgao",
        "DELETE FROM orgao",
        "INSERT INTO orgao VALUES (1, 'x')",
        "UPDATE orgao SET nome = 'x'",
        "CREATE TABLE copia AS SELECT * FROM orgao",
        "ALTER TABLE orgao ADD COLUMN x INT",
        # vários comandos
        "SELECT * FROM orgao; DROP TABLE orgao",
        "SELECT 1; SELECT 2",
        # administração do DuckDB
        "ATTACH 'outro.db' AS outro",
        "COPY orgao TO 'vazamento.csv'",
        "PRAGMA database_list",
        "INSTALL httpfs",
        "LOAD httpfs",
        "CALL pragma_version()",
        # leitura de arquivos e do sistema
        "SELECT * FROM 'segredos.csv'",
        "SELECT * FROM read_csv('segredos.csv')",
        "SELECT read_text('/etc/passwd')",
        "SELECT getenv('HOME')",
        "SELECT * FROM glob('*')",
        "SELECT * FROM duckdb_tables()",
        "SELECT * FROM information_schema.tables",
        # tabelas fora da lista
        "SELECT * FROM usuarios",
        # limite não numérico
        "SELECT * FROM orgao LIMIT (SELECT 10)",
        # entradas inválidas
        "",
        "   ",
        "isto não é sql",
    ],
)
def test_bloqueia(sql):
    resultado = validar(sql, TABELAS)
    assert not resultado.aprovada, f"deveria bloquear: {sql!r}"
    assert resultado.sql is None
    assert resultado.motivo
