# Análise de erros — Avaliação do assistente Text-to-SQL

- **Projeto:** Assistente de despesas públicas — Text-to-SQL Seguro
- **Data da avaliação:** 7 de novembro de 2026
- **Modelo:** `qwen2.5-coder:3b` (Ollama)
- **Base consultada:** PostgreSQL 16, dados do exercício de 2025
- **Conjunto de avaliação:** 50 perguntas em `eval/perguntas.jsonl`
- **Execução original:** `resultados_20261107T193324Z.csv`

## 1. Objetivo

Este documento registra a análise dos erros observados na primeira avaliação experimental do assistente Text-to-SQL. O objetivo é identificar em que etapa ocorreram as falhas, classificar suas causas prováveis e preservar evidências para a análise do Marco 3.

A avaliação comparou duas condições:

- **Assistente completo:** utiliza as instruções fixas e o esquema dinâmico obtido do PostgreSQL.
- **Baseline:** utiliza as mesmas instruções fixas, mas não recebe o esquema dinâmico.

As duas condições utilizaram o mesmo modelo e mantiveram ativos o validador SQL, o limite de linhas, a verificação de custo e a conexão de leitura. Portanto, o baseline é especificamente uma condição **sem esquema dinâmico**, e não uma execução sem instruções ou sem controles de segurança.

## 2. Integridade do conjunto de avaliação

Antes da geração pelo modelo, o avaliador executou novamente as 50 consultas de referência no PostgreSQL. Todas foram conferidas com sucesso (`[OK] Q001` até `[OK] Q050`), sem divergências entre os resultados armazenados e os resultados retornados pelo banco.

As verificações estruturais anteriores também indicaram:

- 50 linhas no arquivo JSONL;
- 0 registros JSON inválidos;
- 50 perguntas carregadas;
- 0 IDs duplicados;
- 0 IDs faltantes;
- 0 registros com campos obrigatórios ausentes;
- 0 problemas na estrutura tabular dos resultados esperados.

A distribuição informada do conjunto por dificuldade foi de 9 perguntas fáceis, 29 intermediárias e 12 difíceis.

## 3. Resultado geral

### 3.1 Resultado após a reavaliação

A primeira execução classificou 27 de 50 respostas do assistente completo como corretas (54%). A revisão do critério de comparação recuperou quatro casos em que o conteúdo correspondia à referência, mas a comparação original era excessivamente rígida.

| Condição | Acertos | Total | Acurácia de execução |
|---|---:|---:|---:|
| Assistente completo | 31 | 50 | **62,0%** |
| Baseline sem esquema dinâmico | 0 | 50 | **0,0%** |

A acurácia é calculada como o número de resultados que correspondem à referência dividido pelo total de perguntas da condição. Uma consulta pode ser executada com sucesso e ainda assim ser considerada incorreta quando seu resultado não corresponde à referência.

### 3.2 Situação das consultas do assistente completo

| Situação registrada | Quantidade | Percentual das 50 perguntas |
|---|---:|---:|
| Executadas (`ok`) | 43 | 86% |
| Bloqueadas | 5 | 10% |
| Erro de execução por timeout | 2 | 4% |
| **Total** | **50** | **100%** |

Das 43 consultas executadas, 31 produziram o resultado esperado e 12 produziram resultado diferente. Assim, a taxa de acerto entre as consultas que chegaram a ser executadas foi de 31/43, aproximadamente **72,09%**.

O baseline teve 50 consultas bloqueadas e nenhum acerto (0/50). A análise detalhada dos SQLs do baseline ainda não foi concluída para as 50 perguntas; os exemplos apresentados adiante são amostras dos primeiros registros inspecionados.

### 3.3 Tempos médios de geração

Na execução original, os tempos médios de geração registrados foram:

| Condição | Tempo médio do modelo |
|---|---:|
| Assistente completo | 16,746 s |
| Baseline | 18,221 s |

Esses tempos representam a geração do modelo, não o tempo total da avaliação. A primeira chamada do assistente completo foi mais lenta que as seguintes, indicando possível influência do carregamento inicial do modelo. Como foi realizada uma única rodada, os tempos não devem ser interpretados como uma comparação de desempenho generalizável.

## 4. Ajuste do critério de comparação

A revisão identificou quatro falsos negativos na classificação original:

| Pergunta | Diferença observada | Tratamento na reavaliação |
|---|---|---|
| Q008 | O modelo retornou `84.842035...`; a referência armazenava `84.84`. | Comparação numérica arredondada a duas casas decimais. |
| Q014 | O modelo retornou `94.134857...`; a referência armazenava `94.13`. | Comparação numérica arredondada a duas casas decimais. |
| Q022 | Os valores das categorias estavam corretos, mas sem arredondamento a duas casas e em ordem diferente. | Comparação numérica a duas casas e sem exigir ordem para distribuição sem ranking. |
| Q038 | As três categorias e seus valores estavam corretos, mas as linhas vieram em outra ordem. | Comparação sem exigir ordem para distribuição sem ranking. |

A função de comparação foi ajustada para comparar valores numéricos com precisão de centavos usando `Decimal` e `ROUND_HALF_UP`. Para perguntas cuja formulação exige um ranking, a ordem deve ser preservada. O campo `comparar_ordem: true` foi incluído no JSONL para Q028, Q030, Q032, Q035 e Q042.

A reavaliação foi feita sobre o CSV histórico, sem chamar novamente o modelo. O CSV original foi preservado e um novo CSV e JSON foram gerados com a classificação corrigida.

**Nota de interpretação:** a regra de duas casas decimais é o critério adotado nesta rodada para os resultados numéricos do conjunto. Se forem adicionados no futuro indicadores numéricos que exijam precisão superior a duas casas, a regra deverá ser revista ou especificada por pergunta.

## 5. Análise individual dos 19 erros do assistente completo

Os 19 casos que permaneceram incorretos após a reavaliação estão distribuídos em 12 consultas executadas com resultado incorreto, 5 consultas bloqueadas e 2 erros de execução por timeout.

### 5.1 Consultas executadas, mas com resultado incorreto (12 casos)

#### Q012 — Maior pagamento por município e UF

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** município `PORTO ALEGRE`, UF `RS`, total pago de `2554377366.33`.
- **SQL gerado:** agrupou por município e UF, mas não restringiu os registros a municípios válidos e UFs identificadas.
- **Resultado observado:** linha com município e UF nulos e total de `4582732927535.67`.
- **Classificação:** filtro insuficiente / inclusão de registros sem localização identificada.

#### Q013 — Quantidade de municípios distintos

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** 282 combinações distintas de UF e município, com pagamentos positivos.
- **SQL gerado:** `COUNT(DISTINCT municipio)`, sem considerar a UF na identidade do município e sem aplicar todos os filtros de validade da referência.
- **Resultado observado:** 280.
- **Classificação:** granularidade incorreta na contagem distinta; a pergunta exige considerar o par (UF, município).

#### Q019 — Média mensal do valor pago

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** média dos 12 totais mensais, `405688628819.44`.
- **SQL gerado:** calculou `AVG(valor_pago)` diretamente sobre os registros de `execucao_mensal`.
- **Resultado observado:** `6154467.177951841499`.
- **Classificação:** agregação na granularidade errada. A pergunta solicita a média dos totais mensais, não a média dos registros individuais.

#### Q020 — Diferença entre empenhado e pago

- **Situação:** `ok`, mas resultado incorreto segundo o critério estrutural.
- **Referência:** uma coluna com a diferença `319507129772.96`.
- **SQL gerado:** retornou três colunas: total empenhado, total pago e a diferença.
- **Resultado observado:** a terceira coluna continha a diferença correta, mas as duas colunas adicionais fizeram o resultado divergir da estrutura esperada.
- **Classificação:** formato/estrutura de saída incorreta, embora o valor solicitado estivesse presente.

#### Q023 — Pagamentos em despesas correntes provenientes de emendas

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** `24098661574.32`.
- **SQL gerado:** realizou JOINs com `orcamento`, `funcao` e `subfuncao`, incluindo relacionamento entre tabelas de fatos por chaves insuficientes.
- **Resultado observado:** `15676896232092.50`.
- **Classificação:** JOIN desnecessário que multiplicou registros e inflou a soma. A pergunta podia ser respondida diretamente pela tabela `execucao_mensal`.

#### Q027 — Saldo líquido de restos a pagar inscritos

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** soma líquida dos valores positivos e negativos, `-56752209.21`.
- **SQL gerado:** subtraiu a soma dos valores negativos da soma dos positivos. Como os valores negativos já possuem sinal negativo, isso aumentou o saldo em vez de compensá-lo.
- **Resultado observado:** `3504025582.09`.
- **Classificação:** interpretação incorreta do sinal e do conceito de saldo líquido.

#### Q033 — Participação percentual dos grupos no valor realizado

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** percentual de cada grupo sobre o total de `valor_realizado`.
- **SQL gerado:** utilizou `SUM(valor_inicial)` como denominador e `SUM(valor_realizado)` como numerador.
- **Resultado observado:** percentuais como `101.58%` para Inversões Financeiras e `91.39%` para Outras Despesas Correntes, em vez da participação no total realizado.
- **Classificação:** denominador financeiro incorreto; confundiu orçamento inicial com total realizado.

#### Q040 — Mês com menor valor pago

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** menor total mensal; fevereiro (mês 2), `266116937177.61`.
- **SQL gerado:** ordenou os registros individuais por `valor_pago` e selecionou o menor registro, sem agrupar por mês.
- **Resultado observado:** mês 6, valor `-3196742742.40`.
- **Classificação:** ausência de agregação mensal; confundiu menor lançamento individual com menor total mensal.

#### Q045 — Transferências a estados e ao Distrito Federal

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** filtro pela modalidade `Transferências a Estados e ao Distrito Federal`; total `303905913330.97`.
- **SQL gerado:** filtrou por UFs (`DF` e `ES`), em vez de filtrar a modalidade da despesa.
- **Resultado observado:** `50806910031.09`.
- **Classificação:** interpretação incorreta da modalidade de despesa como localização geográfica.

#### Q046 — Mês com maior valor liquidado

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** soma de `valor_liquidado` por mês; janeiro, total `737206617291.00`.
- **SQL gerado:** utilizou `MAX(valor_liquidado)` por mês, em vez de `SUM(valor_liquidado)`.
- **Resultado observado:** mês 1 com `344051961358.97`.
- **Classificação:** agregação incorreta. Identificou o mês, mas retornou o maior lançamento individual daquele mês, não o total mensal.

#### Q047 — UF com maior pagamento de emendas

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** maior soma por UF identificada, excluindo `uf IS NULL`; SP, `2356499809.35`.
- **SQL gerado:** agrupou por UF, mas não excluiu a categoria nula.
- **Resultado observado:** UF nula, total `6220976170.89`.
- **Classificação:** filtro incompleto; registros sem UF foram tratados como se fossem uma localização estadual.

#### Q050 — Pagamentos de despesas de capital no segundo semestre

- **Situação:** `ok`, mas resultado incorreto.
- **Referência:** meses 7 a 12 (`BETWEEN 7 AND 12`), total `797513618401.80`.
- **SQL gerado:** utilizou `BETWEEN 6 AND 12`, incluindo junho.
- **Resultado observado:** `823389765809.81`.
- **Classificação:** interpretação incorreta do intervalo temporal.

### 5.2 Consultas bloqueadas (5 casos)

#### Q025 — Unidade gestora com maior pagamento

- **Situação:** `bloqueada`.
- **Motivo registrado:** tabela `unidade_gestora` não existe ou não pode ser consultada.
- **Problema:** o modelo inventou uma tabela separada para unidade gestora, embora os campos `codigo_unidade_gestora` e `nome_unidade_gestora` estejam em `execucao_mensal`.
- **Classificação:** alucinação de tabela / desconhecimento da estrutura real.

#### Q029 — Programa e ação com maior valor pago

- **Situação:** `bloqueada`.
- **Motivo registrado:** `missing FROM-clause entry for table "p"`.
- **Problema:** o SQL declarou o alias `pa` para `programa_acao`, mas tentou selecionar `p.nome_programa`; também utilizou `a.nome_acao` sem declarar o alias `a`.
- **Classificação:** inconsistência de aliases e referências a tabelas não declaradas.

#### Q039 — Participação das categorias no orçamento atualizado

- **Situação:** `bloqueada`.
- **Motivo registrado:** `aggregate function calls cannot contain window function calls`.
- **Problema:** o SQL combinou funções agregadas e de janela em uma expressão inválida para o PostgreSQL.
- **Classificação:** construção SQL inválida envolvendo agregação e função de janela.

#### Q048 — Maior percentual de realização por função

- **Situação:** `bloqueada`.
- **Motivo registrado:** `column e.valor_realizado does not exist`.
- **Problema:** o modelo tentou buscar `valor_realizado` na tabela `execucao_mensal`. Essa coluna pertence a `orcamento`.
- **Classificação:** atribuição de coluna à tabela errada.

#### Q049 — Maior percentual empenhado por órgão superior

- **Situação:** `bloqueada`.
- **Motivo registrado:** `column "empenhado" does not exist`.
- **Problema:** o SQL utilizou nomes genéricos como `empenhado` e `orçado`, em vez dos nomes reais `valor_empenhado` e `valor_atualizado`.
- **Classificação:** alucinação/uso de nomes de colunas inexistentes.

### 5.3 Erros de execução por timeout (2 casos)

#### Q017 — Função com maior valor pago

- **Situação:** `erro_execucao`.
- **Motivo registrado:** `canceling statement due to statement timeout`.
- **Problema:** o SQL juntou `funcao`, `orcamento` e `execucao_mensal`, relacionando as duas tabelas de fatos por `codigo_orgao` e filtrando o ano pela tabela `orcamento`.
- **Classificação:** JOIN entre fatos com granularidade inadequada, gerando consulta excessivamente custosa e timeout.

#### Q028 — Cinco funções com maior valor pago

- **Situação:** `erro_execucao`.
- **Motivo registrado:** `canceling statement due to statement timeout`.
- **Problema:** repetiu a estratégia de JOIN entre `funcao`, `orcamento` e `execucao_mensal`, relacionando as tabelas de fatos por `codigo_orgao`.
- **Classificação:** JOIN entre fatos com granularidade inadequada, gerando consulta excessivamente custosa e timeout.

## 6. Resultado do baseline

O baseline obteve 0 acertos em 50 perguntas e todas as 50 consultas foram classificadas como bloqueadas. Nos primeiros cinco exemplos inspecionados, o modelo gerou referências a campos e relacionamentos inexistentes, como `id_orcamento`, `id_emenda`, `data_execucao`, `orgao_id`, além de utilizar `YEAR()` e tabelas/colunas que não correspondem ao esquema do projeto.

Esses exemplos são compatíveis com a hipótese de que o esquema dinâmico ajuda o modelo a produzir SQL alinhado à estrutura real da base. Entretanto, como a inspeção detalhada apresentada aqui cobre apenas os primeiros exemplos do baseline, não se atribui uma causa individual a cada um dos 50 bloqueios sem analisar os demais registros do CSV.

## 7. Síntese das causas observadas

Os erros do assistente completo mostram quatro grupos principais de dificuldade:

1. **Interpretação e granularidade:** não identificar que a pergunta exige total mensal, total por município/UF, ou exclusão de registros sem localização.
2. **Escolha de campos e conceitos financeiros:** confundir valor inicial, atualizado, realizado, empenhado, liquidado e pago; ou interpretar incorretamente saldos com valores negativos.
3. **Construção de SQL e relacionamentos:** inventar tabelas/colunas, utilizar aliases inconsistentes e realizar JOINs desnecessários entre tabelas de fatos.
4. **Desempenho e custo:** consultas com relacionamentos inadequados podem ultrapassar o `statement_timeout`, mesmo sem serem comandos destrutivos.

Os resultados também mostram que `situacao = ok` não significa resposta correta: 12 consultas foram executadas com sucesso, mas produziram resultados diferentes dos esperados.

## 8. Limitações e cuidados de interpretação

- Os resultados correspondem a uma única rodada de avaliação com 50 perguntas. Não foram apresentadas execuções repetidas para medir variabilidade entre rodadas.
- O conjunto é composto por dados de 2025 e pelo esquema disponível nessa versão do banco; os resultados não podem ser automaticamente generalizados para outros anos ou bases.
- O modelo avaliado foi `qwen2.5-coder:3b`, executado localmente via Ollama. O desempenho e os tempos dependem também do ambiente de hardware e da configuração local.
- O baseline foi definido como o mesmo fluxo sem esquema dinâmico. Como todas as suas consultas foram bloqueadas, a diferença observada é expressiva, mas deve ser descrita dentro dessa definição específica de baseline.
- O assistente completo foi executado antes do baseline na rodada registrada. A ordem de execução e o aquecimento do modelo podem influenciar medidas de tempo; por isso, os tempos médios não devem ser tratados como comparação controlada de latência.
- A revisão do avaliador alterou o critério de comparação dos resultados, não os SQLs gerados nem as respostas do modelo. A acurácia de 62% é a métrica recalculada a partir dos resultados históricos com o critério corrigido.
- A comparação numérica em duas casas decimais foi escolhida para este conjunto. Perguntas futuras que precisem de precisão diferente devem declarar seu critério.
- Os resultados da primeira rodada devem permanecer preservados. Melhorias futuras no prompt ou no modelo devem ser avaliadas em uma nova rodada identificada, sem substituir os arquivos históricos.

## 9. Recomendações para a próxima iteração

As ações abaixo são recomendações para trabalho futuro, não resultados já realizados:

1. Melhorar as instruções sobre granularidade: distinguir média de registros de média de totais mensais; distinguir menor lançamento de menor total agregado.
2. Reforçar as regras sobre filtros de localização: quando a pergunta solicitar estados/UFs, excluir `uf IS NULL`; quando solicitar município e UF, considerar a combinação dos dois campos e tratar registros sem localização explicitamente.
3. Reforçar o uso dos campos financeiros corretos e a interpretação de valores negativos em saldos líquidos.
4. Orientar o modelo a evitar JOIN direto entre as tabelas de fatos `orcamento` e `execucao_mensal` para calcular somas, salvo quando houver uma estratégia de agregação e relacionamento apropriada.
5. Tornar mais explícito no prompt quais colunas pertencem a cada tabela e que `unidade_gestora` não é uma tabela consultável independente.
6. Acrescentar testes de regressão para os 19 casos de falha identificados, mantendo os SQLs de referência como oráculo.
7. Realizar uma nova rodada após as alterações, identificando os novos arquivos e preservando a rodada original para comparação.
8. Completar a inspeção individual dos 50 SQLs do baseline antes de descrever as causas específicas de todos os bloqueios.

## 10. Arquivos e comandos de reprodução

Arquivos da rodada original e da reavaliação:

- `eval/resultados/resultados_20261107T193324Z.csv`
- `eval/resultados/resumo_20261107T193324Z.json`
- `eval/resultados/resultados_20261107T193324Z_reavaliado_20261107T204218Z.csv`
- `eval/resultados/resultados_20261107T193324Z_reavaliado_20261107T204218Z.json`

Comando usado para executar as duas condições com as 50 perguntas:

```powershell
docker compose exec app python /app/eval/avaliar.py --modo ambos
```

Comando usado para reavaliar o CSV histórico sem novas chamadas ao modelo:

```powershell
docker compose exec app python /app/eval/avaliar.py --reavaliar-csv /app/eval/resultados/resultados_20261107T193324Z.csv
```

---

**Conclusão:** na primeira rodada, após corrigir o critério de comparação, o assistente completo obteve 31 acertos em 50 perguntas (62,0%), enquanto o baseline sem esquema dinâmico obteve 0 acertos e teve 50 consultas bloqueadas. A análise dos 19 erros remanescentes evidencia limitações de interpretação semântica, escolha de campos, construção de JOINs e desempenho das consultas. Esses achados devem orientar a próxima iteração, preservando-se os resultados desta rodada como registro histórico.
