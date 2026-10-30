"""SQL da carga: esquema consultável (``public``) e transformação a partir do staging.

O staging fica no schema ``carga``, todo em texto, exatamente como veio do CSV.
As tabelas de ``public`` são as únicas que o assistente enxerga; os comentários
em tabelas e colunas são lidos depois para montar o prompt do modelo.
"""

from __future__ import annotations

from assistente_sql.fontes import Fonte

TABELAS_CONSULTAVEIS = (
    "orgao",
    "funcao",
    "subfuncao",
    "programa_acao",
    "orcamento",
    "execucao_mensal",
)


def ddl_staging(fonte: Fonte) -> str:
    colunas = ",\n    ".join(f"{c} text" for c in fonte.colunas_staging)
    return (
        f"DROP TABLE IF EXISTS carga.{fonte.tabela_staging};\n"
        f"CREATE UNLOGGED TABLE carga.{fonte.tabela_staging} (\n    {colunas}\n);"
    )


PREPARAR_STAGING = """
DROP SCHEMA IF EXISTS carga CASCADE;
CREATE SCHEMA carga;

-- "1234,56" -> 1234.56; vazio -> NULL
CREATE OR REPLACE FUNCTION carga.num(v text) RETURNS numeric(18, 2)
LANGUAGE sql IMMUTABLE AS $$ SELECT replace(nullif(trim(v), ''), ',', '.')::numeric(18, 2) $$;

CREATE OR REPLACE FUNCTION carga.txt(v text) RETURNS text
LANGUAGE sql IMMUTABLE AS $$ SELECT nullif(trim(v), '') $$;
"""

# Recria o esquema consultável do zero a cada carga (a carga é idempotente).
CRIAR_ESQUEMA = """
DROP TABLE IF EXISTS execucao_mensal, orcamento, programa_acao, subfuncao, funcao, orgao;

CREATE TABLE orgao (
    codigo text PRIMARY KEY,
    nome text NOT NULL,
    codigo_orgao_superior text NOT NULL,
    nome_orgao_superior text NOT NULL
);
COMMENT ON TABLE orgao IS
    'Órgãos do governo federal (ex.: Ministério da Saúde, Fundação Oswaldo Cruz).';
COMMENT ON COLUMN orgao.codigo IS
    'Código SIAFI do órgão (ex.: 36201). Códigos negativos indicam órgão não informado.';
COMMENT ON COLUMN orgao.nome_orgao_superior IS
    'Ministério ou poder ao qual o órgão está vinculado.';

CREATE TABLE funcao (
    codigo text PRIMARY KEY,
    nome text NOT NULL
);
COMMENT ON TABLE funcao IS
    'Área de governo da despesa (ex.: Saúde, Educação, Previdência Social).';

CREATE TABLE subfuncao (
    codigo text PRIMARY KEY,
    nome text NOT NULL
);
COMMENT ON TABLE subfuncao IS
    'Detalhamento da função (ex.: Atenção básica, Ensino superior).';

CREATE TABLE programa_acao (
    codigo_programa text NOT NULL,
    nome_programa text NOT NULL,
    codigo_acao text NOT NULL,
    nome_acao text NOT NULL,
    PRIMARY KEY (codigo_programa, codigo_acao)
);
COMMENT ON TABLE programa_acao IS
    'Programas orçamentários e suas ações. Uma ação é identificada pelo par (programa, ação).';

CREATE TABLE orcamento (
    ano integer NOT NULL,
    codigo_orgao text NOT NULL REFERENCES orgao (codigo),
    codigo_unidade_orcamentaria text NOT NULL,
    nome_unidade_orcamentaria text NOT NULL,
    codigo_funcao text NOT NULL REFERENCES funcao (codigo),
    codigo_subfuncao text NOT NULL REFERENCES subfuncao (codigo),
    codigo_programa text NOT NULL,
    codigo_acao text NOT NULL,
    categoria_economica text NOT NULL,
    grupo_despesa text NOT NULL,
    elemento_despesa text NOT NULL,
    valor_inicial numeric(18, 2) NOT NULL,
    valor_atualizado numeric(18, 2) NOT NULL,
    valor_empenhado numeric(18, 2) NOT NULL,
    valor_realizado numeric(18, 2) NOT NULL,
    FOREIGN KEY (codigo_programa, codigo_acao) REFERENCES programa_acao
);
COMMENT ON TABLE orcamento IS
    'Orçamento anual da despesa: quanto foi previsto (inicial e atualizado), '
    'empenhado e realizado, por órgão, função, programa, ação e natureza. Valores em reais.';
COMMENT ON COLUMN orcamento.valor_inicial IS 'Valor aprovado na Lei Orçamentária Anual (R$).';
COMMENT ON COLUMN orcamento.valor_atualizado IS
    'Valor autorizado após créditos adicionais e cortes (R$).';
COMMENT ON COLUMN orcamento.valor_empenhado IS 'Valor reservado para pagamento (R$).';
COMMENT ON COLUMN orcamento.valor_realizado IS 'Valor efetivamente executado no ano (R$).';
COMMENT ON COLUMN orcamento.grupo_despesa IS
    'Ex.: Pessoal e Encargos Sociais, Outras Despesas Correntes, Investimentos.';

CREATE TABLE execucao_mensal (
    ano integer NOT NULL,
    mes integer NOT NULL CHECK (mes BETWEEN 1 AND 12),
    codigo_orgao text NOT NULL REFERENCES orgao (codigo),
    codigo_unidade_gestora text NOT NULL,
    nome_unidade_gestora text NOT NULL,
    codigo_funcao text NOT NULL REFERENCES funcao (codigo),
    codigo_subfuncao text NOT NULL REFERENCES subfuncao (codigo),
    codigo_programa text NOT NULL,
    codigo_acao text NOT NULL,
    uf text,
    municipio text,
    categoria_economica text NOT NULL,
    grupo_despesa text NOT NULL,
    elemento_despesa text NOT NULL,
    modalidade_despesa text NOT NULL,
    com_emenda boolean NOT NULL,
    valor_empenhado numeric(18, 2) NOT NULL,
    valor_liquidado numeric(18, 2) NOT NULL,
    valor_pago numeric(18, 2) NOT NULL,
    valor_restos_a_pagar_inscritos numeric(18, 2) NOT NULL,
    valor_restos_a_pagar_cancelados numeric(18, 2) NOT NULL,
    valor_restos_a_pagar_pagos numeric(18, 2) NOT NULL,
    FOREIGN KEY (codigo_programa, codigo_acao) REFERENCES programa_acao
);
COMMENT ON TABLE execucao_mensal IS
    'Execução da despesa lançada em cada mês: valores empenhados, liquidados e pagos, '
    'por órgão, unidade gestora, função, programa, ação, UF e natureza. Valores em reais. '
    'Para o total do ano, some os meses.';
COMMENT ON COLUMN execucao_mensal.uf IS 'Sigla da UF do gasto; NULL quando nacional.';
COMMENT ON COLUMN execucao_mensal.com_emenda IS
    'Verdadeiro se a despesa veio de emenda parlamentar.';
COMMENT ON COLUMN execucao_mensal.valor_pago IS 'Valor pago no mês (R$).';
COMMENT ON COLUMN execucao_mensal.valor_liquidado IS
    'Valor reconhecido como devido no mês, após entrega do bem ou serviço (R$).';
COMMENT ON COLUMN execucao_mensal.valor_restos_a_pagar_pagos IS
    'Pagamentos no mês de despesas empenhadas em anos anteriores (R$).';
"""

# Dimensões vêm da união das duas fontes; em caso de nome divergente para o
# mesmo código, prevalece o da execução (arquivo mais recente).
TRANSFORMAR = """
-- A execução traz lançamentos sem órgão (ajustes de junho e dezembro, com UG -9)
-- e o órgão -3 sem nome. Em vez de descartar valores, seguimos a convenção da
-- própria CGU: código -1 e nome 'Sem informação'.
UPDATE carga.execucao_bruta
SET cod_orgao = coalesce(carga.txt(cod_orgao), '-1'),
    nome_orgao = coalesce(carga.txt(nome_orgao), 'Sem informação'),
    cod_orgao_superior = coalesce(carga.txt(cod_orgao_superior), '-1'),
    nome_orgao_superior = coalesce(carga.txt(nome_orgao_superior), 'Sem informação')
WHERE carga.txt(cod_orgao) IS NULL OR carga.txt(nome_orgao) IS NULL
   OR carga.txt(cod_orgao_superior) IS NULL OR carga.txt(nome_orgao_superior) IS NULL;

INSERT INTO orgao
SELECT DISTINCT ON (codigo) codigo, nome, codigo_orgao_superior, nome_orgao_superior
FROM (
    SELECT 1 AS prioridade, carga.txt(cod_orgao) AS codigo, carga.txt(nome_orgao) AS nome,
           carga.txt(cod_orgao_superior) AS codigo_orgao_superior,
           carga.txt(nome_orgao_superior) AS nome_orgao_superior
    FROM carga.execucao_bruta
    UNION ALL
    SELECT 2, carga.txt(cod_orgao), carga.txt(nome_orgao),
           carga.txt(cod_orgao_superior), carga.txt(nome_orgao_superior)
    FROM carga.orcamento_bruto
) t
ORDER BY codigo, prioridade, nome;

INSERT INTO funcao
SELECT DISTINCT ON (codigo) codigo, nome
FROM (
    SELECT 1 AS prioridade, carga.txt(cod_funcao) AS codigo, carga.txt(nome_funcao) AS nome
    FROM carga.execucao_bruta
    UNION ALL
    SELECT 2, carga.txt(cod_funcao), carga.txt(nome_funcao) FROM carga.orcamento_bruto
) t
ORDER BY codigo, prioridade, nome;

INSERT INTO subfuncao
SELECT DISTINCT ON (codigo) codigo, nome
FROM (
    SELECT 1 AS prioridade, carga.txt(cod_subfuncao) AS codigo,
           carga.txt(nome_subfuncao) AS nome
    FROM carga.execucao_bruta
    UNION ALL
    SELECT 2, carga.txt(cod_subfuncao), carga.txt(nome_subfuncao) FROM carga.orcamento_bruto
) t
ORDER BY codigo, prioridade, nome;

INSERT INTO programa_acao
SELECT DISTINCT ON (codigo_programa, codigo_acao)
       codigo_programa, nome_programa, codigo_acao, nome_acao
FROM (
    SELECT 1 AS prioridade, carga.txt(cod_programa) AS codigo_programa,
           carga.txt(nome_programa) AS nome_programa, carga.txt(cod_acao) AS codigo_acao,
           carga.txt(nome_acao) AS nome_acao
    FROM carga.execucao_bruta
    UNION ALL
    SELECT 2, carga.txt(cod_programa), carga.txt(nome_programa),
           carga.txt(cod_acao), carga.txt(nome_acao)
    FROM carga.orcamento_bruto
) t
ORDER BY codigo_programa, codigo_acao, prioridade, nome_programa, nome_acao;

INSERT INTO orcamento
SELECT exercicio::integer, carga.txt(cod_orgao), carga.txt(cod_uo), carga.txt(nome_uo),
       carga.txt(cod_funcao), carga.txt(cod_subfuncao), carga.txt(cod_programa),
       carga.txt(cod_acao), carga.txt(nome_categoria), carga.txt(nome_grupo),
       carga.txt(nome_elemento), carga.num(valor_inicial), carga.num(valor_atualizado),
       carga.num(valor_empenhado), carga.num(valor_realizado)
FROM carga.orcamento_bruto;

-- O nome do autor da emenda identifica uma pessoa física; guardamos só se houve emenda.
INSERT INTO execucao_mensal
SELECT split_part(ano_mes, '/', 1)::integer, split_part(ano_mes, '/', 2)::integer,
       carga.txt(cod_orgao), carga.txt(cod_ug), carga.txt(nome_ug),
       carga.txt(cod_funcao), carga.txt(cod_subfuncao), carga.txt(cod_programa),
       carga.txt(cod_acao), carga.txt(uf), carga.txt(municipio),
       carga.txt(nome_categoria), carga.txt(nome_grupo), carga.txt(nome_elemento),
       carga.txt(nome_modalidade),
       coalesce(carga.txt(nome_autor_emenda), 'SEM EMENDA') <> 'SEM EMENDA',
       carga.num(valor_empenhado), carga.num(valor_liquidado), carga.num(valor_pago),
       carga.num(valor_rp_inscritos), carga.num(valor_rp_cancelado), carga.num(valor_rp_pagos)
FROM carga.execucao_bruta;

CREATE INDEX ON orcamento (codigo_orgao);
CREATE INDEX ON orcamento (codigo_funcao);
CREATE INDEX ON execucao_mensal (codigo_orgao);
CREATE INDEX ON execucao_mensal (codigo_funcao);
CREATE INDEX ON execucao_mensal (ano, mes);
CREATE INDEX ON execucao_mensal (uf);
"""

LIMPAR_STAGING = """
DROP TABLE IF EXISTS carga.orcamento_bruto, carga.execucao_bruta;
"""
