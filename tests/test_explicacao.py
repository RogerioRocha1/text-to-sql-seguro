"""Explicação da consulta em linguagem simples (montada a partir do SQL, sem o modelo)."""

import pytest

from assistente_sql.explicacao import explicar


def passos(sql):
    explicacao = explicar(sql)
    assert explicacao is not None
    return explicacao.passos


def test_total_de_um_ministerio():
    # SQL real gerado pelo qwen2.5-coder:7b para D01 (eval/resultados, 17/11)
    resultado = passos(
        "SELECT SUM(execucao_mensal.valor_pago) AS total_pagamento FROM execucao_mensal "
        "JOIN orgao ON execucao_mensal.codigo_orgao = orgao.codigo "
        "WHERE orgao.nome_orgao_superior = 'Ministério da Saúde' "
        "AND execucao_mensal.ano = 2025 LIMIT 1000"
    )
    assert resultado == (
        "Consulta a execução mensal da despesa (valores empenhados, liquidados e pagos), "
        "cruzando com a lista de órgãos.",
        "Mostra: soma do valor pago.",
        "Considera só os registros em que ministério ou poder é “Ministério da Saúde” "
        "e ano é 2025.",
    )


def test_ranking_com_agrupamento_ordem_e_limite():
    resultado = passos(
        "SELECT e.municipio, SUM(e.valor_pago) AS total_pago FROM execucao_mensal AS e "
        "WHERE e.ano = 2025 AND e.uf = 'SP' GROUP BY e.municipio "
        "ORDER BY total_pago DESC LIMIT 3"
    )
    assert "Mostra: município e soma do valor pago." in resultado
    assert "Calcula separadamente para cada município." in resultado
    assert "Ordena por soma do valor pago (do maior para o menor)." in resultado
    assert resultado[-1] == "Fica só com os 3 primeiros."


def test_explicacao_mostra_filtro_que_o_usuario_nao_pediu():
    # D10: o modelo filtrou o Ministério da Saúde sem a pergunta pedir;
    # a explicação deixa o erro visível para o usuário.
    resultado = " ".join(
        passos(
            "SELECT e.municipio, SUM(e.valor_pago) AS total_pago FROM execucao_mensal AS e "
            "JOIN orgao AS o ON e.codigo_orgao = o.codigo WHERE e.ano = 2025 "
            "AND o.nome_orgao_superior = 'Ministério da Saúde' GROUP BY e.municipio "
            "ORDER BY total_pago DESC LIMIT 3"
        )
    )
    assert "ministério ou poder é “Ministério da Saúde”" in resultado


@pytest.mark.parametrize(
    ("condicao", "esperado"),
    [
        ("mes = 12", "mês é dezembro"),
        ("mes BETWEEN 1 AND 6", "mês está entre janeiro e junho"),
        ("com_emenda IS TRUE", "a despesa veio de emenda parlamentar"),
        ("com_emenda = false", "a despesa não veio de emenda parlamentar"),
        ("uf IS NULL", "estado (UF) não foi informado"),
        ("uf IS NOT NULL", "estado (UF) foi informado"),
        ("uf IN ('SP', 'RJ')", "estado (UF) é um destes: “SP”, “RJ”"),
        ("valor_pago > 1000", "valor pago é maior que 1000"),
        (
            "unaccent(municipio) ILIKE unaccent('%sao paulo%')",
            "município contém “sao paulo” (sem diferenciar maiúsculas e acentos)",
        ),
        ("municipio ILIKE 'Campinas'", "município é “Campinas” (sem diferenciar maiúsculas)"),
        ("municipio LIKE 'São%'", "município começa com “São”"),
    ],
)
def test_condicoes(condicao, esperado):
    sql = f"SELECT municipio FROM execucao_mensal WHERE {condicao}"  # noqa: S608 (só texto)
    resultado = " ".join(passos(sql))
    assert esperado in resultado


def test_nome_depende_da_tabela_pelo_apelido():
    resultado = " ".join(
        passos(
            "SELECT f.nome, s.nome FROM execucao_mensal e "
            "JOIN funcao f ON f.codigo = e.codigo_funcao "
            "JOIN subfuncao s ON s.codigo = e.codigo_subfuncao"
        )
    )
    assert "Mostra: função e subfunção." in resultado


def test_percentual_e_contagens():
    assert passos(
        "SELECT round(SUM(valor_realizado) / NULLIF(SUM(valor_atualizado), 0) * 100, 1) "
        "FROM orcamento"
    )[1] == (
        "Mostra: percentual de soma do valor realizado em relação a soma do "
        "orçamento atualizado (arredondado)."
    )
    assert passos("SELECT COUNT(DISTINCT uf) FROM execucao_mensal")[1] == (
        "Mostra: quantidade de estado (UF) diferentes."
    )
    assert passos("SELECT COUNT(*) FROM orgao")[1] == "Mostra: quantidade de registros."


def test_order_by_pela_posicao_da_coluna():
    resultado = passos(
        "SELECT uf, SUM(valor_pago) FROM execucao_mensal GROUP BY uf ORDER BY 2 DESC"
    )
    assert "Ordena por soma do valor pago (do maior para o menor)." in resultado


def test_limite_de_seguranca_so_aparece_quando_muda_algo():
    com_linhas = passos("SELECT uf FROM execucao_mensal LIMIT 1000")
    assert com_linhas[-1] == "Mostra no máximo 1.000 linhas (limite de segurança)."
    total = passos("SELECT SUM(valor_pago) FROM execucao_mensal LIMIT 1000")
    assert not any("limite" in p for p in total)


def test_trecho_que_nao_sabe_explicar_vira_aviso_e_nao_texto_inventado():
    explicacao = explicar("SELECT uf FROM execucao_mensal WHERE length(municipio) > 3")
    assert explicacao is not None and not explicacao.completa
    assert "confira no SQL" in explicacao.texto


def test_consulta_com_etapa_intermediaria_e_marcada_como_incompleta():
    explicacao = explicar("WITH t AS (SELECT uf FROM execucao_mensal) SELECT * FROM t")
    assert explicacao is not None and not explicacao.completa


@pytest.mark.parametrize("sql", [None, "", "SELECT FROM WHERE ((("])
def test_sql_vazio_ou_ilegivel_nao_tem_explicacao(sql):
    assert explicar(sql) is None


def test_texto_em_lista():
    explicacao = explicar("SELECT uf FROM execucao_mensal")
    assert explicacao.texto.startswith("- Consulta a execução mensal")
