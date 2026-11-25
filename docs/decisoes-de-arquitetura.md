# Decisões de arquitetura

Registros curtos das decisões que mais pesam no projeto. Cada um traz o contexto, a decisão e as alternativas descartadas. A decisão sobre os órgãos sem código está em [decisoes-de-dados.md](decisoes-de-dados.md).

## DA-01 · PostgreSQL 16 em Docker no lugar do DuckDB

- **Data:** Marco 2 (proposta revisada em 17/11/2026)
- **Contexto:** a proposta de 28/10 previa DuckDB. A defesa em camadas precisa de um usuário do banco que só tenha `SELECT`, de transações somente leitura e de um tempo máximo por consulta. O validador também usa o `EXPLAIN` do banco para estimar o custo antes de executar.
- **Decisão:** PostgreSQL 16 em container, com o usuário `leitor` criado por `docker/postgres/01-leitor.sh` (`SELECT` só no schema `public`, `default_transaction_read_only` e `statement_timeout` de 15 s).
- **Alternativas descartadas:** DuckDB, que é mais simples de distribuir, mas não tem usuários e permissões no mesmo nível, e SQLite, pelo mesmo motivo e pelo `EXPLAIN` sem estimativa de custo.

## DA-02 · Validação pela árvore sintática (SQLGlot), não por expressão regular

- **Data:** Marco 1
- **Contexto:** o modelo pode gerar SQL destrutivo ou caro, inclusive por injeção de instruções na pergunta. Uma lista de palavras proibidas é fácil de contornar (comentários, maiúsculas, escrita escondida em `WITH`).
- **Decisão:** `validador.py` analisa a consulta no dialeto do PostgreSQL com o SQLGlot e aceita só um `SELECT` sobre as tabelas permitidas, sem funções perigosas, com `LIMIT` aplicado e custo estimado pelo `EXPLAIN` abaixo de 1.000.000. O catálogo de 97 ataques (`eval/ataques.jsonl`) virou teste automatizado.
- **Alternativas descartadas:** expressões regulares (contornáveis), confiar só no usuário `leitor` (não impede consultas caras nem a leitura de dados da sessão) e pedir ao modelo que "não gere comandos perigosos" (o modelo gerou `DROP`, `CREATE USER` e `COPY TO PROGRAM` quando pedido).

## DA-03 · Esquema lido do próprio banco a cada execução

- **Data:** Marco 2
- **Contexto:** o baseline sem esquema acertou 0 de 50 perguntas: o modelo inventou tabelas e colunas em todos os casos. Um esquema escrito à mão no prompt fica desatualizado quando a carga muda.
- **Decisão:** `gerador.ler_esquema` lê do PostgreSQL as tabelas, colunas, comentários, chaves estrangeiras e valores comuns das colunas categóricas e escreve tudo como `CREATE TABLE` comentado.
- **Alternativas descartadas:** esquema fixo no código (desatualiza) e busca de tabelas relevantes por embeddings (desnecessária com 6 tabelas e mais um serviço para manter).

## DA-04 · Explicação da consulta montada a partir do SQL, sem o modelo

- **Data:** 19/11/2026 (Marco 4)
- **Contexto:** o tema exige explicar a consulta em linguagem que um usuário não técnico entenda. A proposta de 28/10 previa que o modelo escrevesse a explicação.
- **Decisão:** `explicacao.py` descreve, a partir da árvore do SQLGlot do SQL que vai ao banco, a fonte dos dados, o que é mostrado, os filtros, o agrupamento, a ordem e o limite, com os nomes das colunas traduzidos (`nome_orgao_superior` vira "ministério ou poder", `mes = 12` vira "mês é dezembro"). O que não sabe descrever vira "confira no SQL", e a explicação fica marcada como incompleta.
- **Por quê:**
    - a explicação descreve exatamente a consulta executada. Quando o modelo erra, por exemplo filtrando um ministério que a pergunta não pediu (D10 do conjunto de desenvolvimento), a explicação mostra o erro em vez de escondê-lo;
    - não acrescenta uma segunda chamada ao modelo, que levaria de 5 a 7 s na GPU de referência e poria em risco a meta de latência (mediana ≤ 15 s);
    - é testável na CI, que não roda o Ollama.
- **Alternativas descartadas:** pedir a explicação ao modelo, na mesma chamada ou numa segunda (pode descrever uma consulta diferente da executada e aumenta a latência), e mostrar só o SQL (não atende ao usuário não técnico).
- **Limitação:** consultas com `WITH`, `UNION` ou funções pouco comuns ficam com explicação parcial. Na rodada de teste de 07/11, 40 das 43 consultas executadas tiveram explicação completa (`eval/README.md`).

## DA-05 · Pedido de esclarecimento por regras, antes do modelo

- **Data:** 19/11/2026 (Marco 4)
- **Contexto:** o tema exige perguntar quando o esquema for ambíguo. O banco guarda várias medidas para a mesma ideia: "gasto" pode ser o valor empenhado, o liquidado ou o pago, e "orçamento" pode ser o inicial ou o atualizado. Os dados também cobrem só 2025. Antes, o prompt escolhia em silêncio ("gasto" virava valor pago).
- **Decisão:** `esclarecimento.py` verifica a pergunta antes de chamar o modelo, com três regras explícitas: medida de gasto não informada, tipo de orçamento não informado e ano diferente de 2025. Quando uma regra dispara, a tela mostra a pergunta e botões com as opções. A opção escolhida é somada à pergunta original, que então segue para o modelo.
- **Por quê:** não gasta tempo de GPU com perguntas que vão voltar, é previsível (a mesma pergunta sempre gera o mesmo esclarecimento) e é testável sem o Ollama. As regras não disparam em nenhuma das 50 perguntas de teste nem das 10 de desenvolvimento, então a acurácia medida não muda.
- **Alternativas descartadas:** deixar o modelo decidir se pergunta (com temperatura 0 ele tende a responder sempre, e uma resposta fora do formato `sql` vira erro), pedir ao modelo várias consultas e comparar os resultados (multiplica a latência) e não perguntar nada (contorna o desafio do tema).
- **Limitação:** as regras só cobrem ambiguidades conhecidas do esquema. Perguntas vagas de outro tipo seguem para o modelo: "Quanto custa a saúde?" não dispara nenhuma regra, e em "Como foi o gasto social?" a regra pergunta a medida, mas "social" continua vago depois da escolha. A medida de cobertura usa um conjunto de perguntas ambíguas escrito por quem não leu as regras (`eval/avaliar_esclarecimento.py`).
