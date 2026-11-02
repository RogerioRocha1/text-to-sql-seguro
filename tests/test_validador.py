"""Testes do validador. Cada ataque do catálogo deve virar um caso aqui."""

import psycopg
import pytest

from assistente_sql import validar, verificar_custo
from assistente_sql.esquema import TABELAS_CONSULTAVEIS
from assistente_sql.validador import ResultadoValidacao
from conftest import banco

TABELAS = frozenset(TABELAS_CONSULTAVEIS)


def aprova(sql: str, limite: int = 1000):
    resultado = validar(sql, TABELAS, limite_maximo=limite)
    assert resultado.aprovada, resultado.motivo
    return resultado.sql


# --- Consultas legítimas ---------------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM orgao",
        "select nome from ORGAO where codigo = '26000'",
        "SELECT o.nome, SUM(e.valor_pago) AS pago FROM execucao_mensal e "
        "JOIN orgao o ON o.codigo = e.codigo_orgao GROUP BY o.nome ORDER BY pago DESC",
        "WITH total AS (SELECT codigo_orgao, SUM(valor_pago) v FROM execucao_mensal "
        "GROUP BY 1) SELECT * FROM total",
        "SELECT codigo FROM orgao UNION SELECT codigo_orgao FROM orcamento",
        "SELECT * FROM public.orgao",
        "SELECT * FROM orgao;",
        "SELECT * FROM orgao; -- comentário no fim",
        "SELECT nome FROM subfuncao WHERE nome ILIKE '%saúde%'",
        "SELECT mes, ROUND(SUM(valor_pago) / 1e9, 2) FROM execucao_mensal "
        "WHERE uf = 'SP' GROUP BY mes ORDER BY mes",
        "SELECT string_agg(nome, ', ') FROM funcao",
        "SELECT COALESCE(uf, 'Nacional') AS uf, SUM(valor_pago) FROM execucao_mensal GROUP BY 1",
        "SELECT p.nome_acao FROM programa_acao p JOIN orcamento r "
        "ON (r.codigo_programa, r.codigo_acao) = (p.codigo_programa, p.codigo_acao)",
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


def test_limit_em_union_vale_para_o_resultado_todo():
    sql = aprova("SELECT codigo FROM orgao UNION SELECT codigo FROM funcao", limite=5)
    assert sql.endswith("LIMIT 5")


# --- Catálogo de ataques e consultas que devem ser bloqueadas -------------


@pytest.mark.parametrize(
    "sql",
    [
        # escrita e estrutura
        "DROP TABLE orgao",
        "DELETE FROM orgao",
        "INSERT INTO orgao VALUES ('1', 'x', '1', 'x')",
        "UPDATE orgao SET nome = 'x'",
        "TRUNCATE orgao",
        "CREATE TABLE copia AS SELECT * FROM orgao",
        "ALTER TABLE orgao ADD COLUMN x INT",
        "GRANT SELECT ON orgao TO PUBLIC",
        # escrita escondida dentro de um SELECT
        "WITH apagados AS (DELETE FROM orgao RETURNING *) SELECT * FROM apagados",
        "SELECT * INTO orgao_copia FROM orgao",
        "SELECT * INTO funcao FROM orgao",
        "SELECT * FROM orgao FOR UPDATE",
        # vários comandos
        "SELECT * FROM orgao; DROP TABLE orgao",
        "SELECT 1; SELECT 2",
        # sessão e administração do PostgreSQL
        "SET search_path = carga",
        "BEGIN",
        "VACUUM orgao",
        "DO $$ BEGIN DELETE FROM orgao; END $$",
        "CALL procedimento()",
        "PREPARE p AS SELECT 1",
        "EXPLAIN ANALYZE SELECT * FROM orgao",
        "LISTEN canal",
        "COPY orgao TO '/tmp/vazamento.csv'",
        "COPY (SELECT 1) TO PROGRAM 'id'",
        # funções perigosas
        "SELECT pg_sleep(60)",
        "SELECT nome FROM orgao WHERE pg_sleep(1) IS NOT NULL",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT pg_ls_dir('.')",
        "SELECT pg_terminate_backend(1)",
        "SELECT lo_import('/etc/passwd')",
        "SELECT set_config('statement_timeout', '0', false)",
        "SELECT current_setting('data_directory')",
        "SELECT nextval('sequencia')",
        "SELECT query_to_xml('DELETE FROM orgao', true, true, '')",
        "SELECT table_to_xml('carga.orcamento_bruto', true, true, '')",
        "SELECT * FROM ts_stat('SELECT 1')",
        "SELECT * FROM dblink('host=x', 'SELECT 1') AS t(a int)",
        "SELECT version()",
        "SELECT current_user",
        "SELECT inet_server_addr()",
        # catálogo do sistema, outros schemas e funções no FROM
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT * FROM pg_user",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM carga.orcamento_bruto",
        "SELECT * FROM main.orgao",
        "SELECT * FROM outro_banco.public.orgao",
        "SELECT * FROM generate_series(1, 1000000000)",
        # tabelas fora da lista
        "SELECT * FROM usuarios",
        # limite fora do formato
        "SELECT * FROM orgao LIMIT (SELECT 10)",
        "SELECT * FROM orgao LIMIT ALL",
        "SELECT * FROM orgao FETCH FIRST 5 ROWS ONLY",
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


# --- Custo estimado (EXPLAIN) ----------------------------------------------


class CursorFalso:
    """Imita o cursor do psycopg devolvendo um plano com custo fixo."""

    def __init__(self, custo=None, erro=None):
        self.custo, self.erro, self.executado = custo, erro, None

    def execute(self, sql):
        self.executado = sql
        if self.erro:
            raise self.erro

    def fetchone(self):
        return ([{"Plan": {"Total Cost": self.custo}}],)


def _aprovada(sql="SELECT * FROM orgao"):
    return validar(sql, TABELAS)


def test_custo_abaixo_do_maximo_aprova_e_informa_custo():
    cursor = CursorFalso(custo=31_119.5)
    resultado = verificar_custo(cursor, _aprovada(), custo_maximo=1_000_000)
    assert resultado.aprovada
    assert resultado.custo_estimado == 31_119.5
    assert cursor.executado == "EXPLAIN (FORMAT JSON) SELECT * FROM orgao LIMIT 1000"


def test_custo_acima_do_maximo_reprova():
    resultado = verificar_custo(CursorFalso(custo=8e9), _aprovada(), custo_maximo=1_000_000)
    assert not resultado.aprovada
    assert resultado.custo_estimado == 8e9
    assert "pesada demais" in resultado.motivo


def test_erro_do_banco_vira_reprovacao_com_a_mensagem():
    erro = psycopg.errors.UndefinedColumn('column "valor" does not exist')
    resultado = verificar_custo(CursorFalso(erro=erro), _aprovada())
    assert not resultado.aprovada
    assert "valor" in resultado.motivo


def test_custo_recusa_consulta_nao_aprovada():
    with pytest.raises(ValueError, match="aprovadas"):
        verificar_custo(CursorFalso(custo=1), ResultadoValidacao(aprovada=False, motivo="x"))


# --- Custo no banco real (roda só com DATABASE_URL_LEITOR definida) --------


@banco
def test_banco_aprova_agregacao_por_funcao(cursor_leitor):
    sql = (
        "SELECT f.nome, SUM(e.valor_pago) FROM execucao_mensal e "
        "JOIN funcao f ON f.codigo = e.codigo_funcao GROUP BY 1 ORDER BY 2 DESC"
    )
    resultado = verificar_custo(cursor_leitor, _aprovada(sql))
    assert resultado.aprovada, resultado.motivo


@banco
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM execucao_mensal a CROSS JOIN execucao_mensal b",
        "SELECT a.uf, COUNT(*) FROM execucao_mensal a JOIN execucao_mensal b "
        "ON a.uf = b.uf GROUP BY 1",
    ],
)
def test_banco_reprova_autojuncao_da_execucao(cursor_leitor, sql):
    resultado = verificar_custo(cursor_leitor, _aprovada(sql))
    assert not resultado.aprovada
    assert resultado.custo_estimado > 1_000_000


@banco
def test_banco_reprova_coluna_inexistente(cursor_leitor):
    resultado = verificar_custo(cursor_leitor, _aprovada("SELECT valor FROM orcamento"))
    assert not resultado.aprovada
    assert "valor" in resultado.motivo
