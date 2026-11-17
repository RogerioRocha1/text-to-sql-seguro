# Avaliação

Perguntas de referência, catálogo de ataques, scripts e resultados (Marco 3).

## Calibração do limite de custo do validador

O validador recusa consultas cujo custo estimado pelo planejador do PostgreSQL (`EXPLAIN`, campo `Total Cost`, sem executar a consulta) passa de `CUSTO_MAXIMO_PADRAO` em [`validador.py`](../src/assistente_sql/validador.py). O custo é uma unidade arbitrária do PostgreSQL, então o limite foi escolhido medindo consultas reais no banco de 2025.

Medição de 02/11/2026: usuário `leitor`, PostgreSQL 16 no Docker Desktop, `statement_timeout` de 20 s, todas as consultas com `LIMIT 1000`.

| Consulta | Custo estimado | Tempo real |
| --- | ---: | ---: |
| `SELECT *` em `orgao` | 8 | 0,00 s |
| Primeiras linhas de `execucao_mensal` | 41 | 0,01 s |
| Orçamento atualizado e realizado por órgão superior | 1.203 | 0,01 s |
| Valor pago por mês em SP | 22.417 | 0,07 s |
| Valor pago por órgão em programas de saúde (3 tabelas) | 30.602 | 0,05 s |
| Valor pago por função | 31.119 | 0,23 s |
| `execucao_mensal` ordenada por valor pago | 46.690 | 0,07 s |
| `execucao_mensal` × `orgao` sem condição, ordenado | 126.314 | 0,28 s |
| Autojunção de `execucao_mensal` por UF | 31.656.465 | > 20 s |
| Produto cartesiano de `execucao_mensal` com ela mesma | 8.059.749.377 | > 20 s |

**Decisão:** limite de **1.000.000**. Ele fica cerca de 20 vezes acima da consulta legítima mais pesada medida e cerca de 30 vezes abaixo da menor consulta abusiva. Se a base crescer (mais anos de dados), refazer esta medição.

**Limitação:** o custo é uma estimativa. Uma consulta pode ficar abaixo do limite e ainda assim demorar; nesse caso vale o `statement_timeout` de 15 s do usuário `leitor`. Os casos do banco real estão em `tests/test_validador.py` e rodam com `DATABASE_URL_LEITOR` definida.

## Conjunto de perguntas e referências

O arquivo [`perguntas.jsonl`](perguntas.jsonl) contém 50 perguntas de referência (Q001–Q050), com as consultas SQL esperadas e os metadados usados na avaliação. As consultas de referência foram conferidas contra o banco antes da execução do benchmark; na rodada de 07/11/2026, as 50 referências passaram pela conferência (`[OK]`).

O conjunto cobre consultas sobre orçamento, execução financeira, classificação da despesa, emendas, localização, classificação funcional, restos a pagar, modalidade de despesa, unidades gestoras, programas e ações e órgãos. Os níveis registrados são fácil, intermediário e difícil.

### Critério de igualdade dos resultados

A avaliação compara o resultado produzido pelo assistente com o resultado de referência:

- Valores numéricos são normalizados para duas casas decimais antes da comparação, com arredondamento decimal (`ROUND_HALF_UP`). Isso evita reprovar resultados financeiramente equivalentes apenas porque uma consulta retornou mais casas decimais.
- Para perguntas sem exigência de classificação, as linhas são comparadas sem exigir a mesma ordem, preservando duplicatas.
- Para perguntas de ranking, o campo `comparar_ordem: true` exige que a sequência de linhas também seja igual à referência.
- Valores textuais são comparados preservando seu conteúdo.

A opção `comparar_ordem` está marcada nos registros de ranking em que a ordem faz parte da resposta esperada. Portanto, uma resposta não é considerada correta apenas por conter os mesmos valores quando a pergunta exige uma classificação.

## Como executar

Execute os comandos a partir da raiz do repositório, com os serviços do Docker Compose disponíveis.

### Teste rápido

O comando abaixo avalia apenas duas perguntas. Serve para verificar se o fluxo está funcionando; não substitui a execução completa nem deve ser usado como resultado final do benchmark.

```powershell
docker compose exec app python /app/eval/avaliar.py --modo ambos --limite 2
```

### Execução completa

O comando executa os dois modos de avaliação — assistente completo e baseline — sobre as 50 perguntas:

```powershell
docker compose exec app python /app/eval/avaliar.py --modo ambos
```

Os arquivos CSV e JSON gerados são salvos em `eval/resultados/`. O diretório local é montado no contêiner em `/app/eval` pelo volume configurado em `docker-compose.yml`, portanto os resultados permanecem disponíveis no repositório após a execução.

### Reavaliar um CSV já gerado

Quando a regra de comparação dos resultados é ajustada, é possível recalcular as métricas de um CSV histórico sem gerar novas respostas do modelo nem executar novamente as consultas no banco:

```powershell
docker compose exec app python /app/eval/avaliar.py --reavaliar-csv /app/eval/resultados/resultados_20261107T193324Z.csv
```

Essa opção produz novos arquivos CSV e JSON com o sufixo `_reavaliado_...`. Ela reavalia os resultados já registrados usando as referências e os critérios atuais de comparação. Não substitui uma nova execução do benchmark quando o modelo, o prompt, o banco ou a implementação do assistente forem alterados.

## Resultados da rodada de 07/11/2026

A primeira execução completa foi registrada em:

- CSV original: `resultados/resultados_20261107T193324Z.csv`
- Resumo JSON original: `resultados/resumo_20261107T193324Z.json`

Após a revisão do critério de igualdade — comparação numérica em centavos e comparação sem ordem para perguntas que não exigem ranking — o CSV histórico foi reavaliado, sem novas chamadas ao modelo:

- CSV reavaliado: `resultados/resultados_20261107T193324Z_reavaliado_20261107T204218Z.csv`
- Resumo JSON reavaliado: `resultados/resultados_20261107T193324Z_reavaliado_20261107T204218Z.json`

| Métrica | Assistente completo | Baseline |
| --- | ---: | ---: |
| Respostas corretas | 31/50 (62%) | 0/50 (0%) |
| Consultas com status `ok` | 43 | 0 |
| Consultas com status `erro_execucao` | 2 | 0 |
| Consultas bloqueadas | 5 | 50 |

No assistente completo, 31 das 50 perguntas foram respondidas com resultados iguais aos de referência. Outras 12 consultas tiveram status `ok`, mas os resultados não corresponderam à referência; duas falharam durante a execução e cinco foram bloqueadas. Assim, status `ok` indica que a consulta foi executada, não que a resposta esteja correta.

No baseline, nenhuma das 50 respostas chegou a produzir um resultado avaliado como correto: todas foram bloqueadas antes da obtenção de resultados. O baseline remove o contexto dinâmico do esquema, mantendo as proteções de validação. Portanto, o resultado observado nesta rodada é especificamente **0/50 respostas corretas e 50/50 bloqueadas**; não deve ser interpretado isoladamente como uma medida pura da qualidade de geração do modelo, pois não houve resultados executados para comparar.

A análise individual das 19 respostas incorretas ou não concluídas do assistente completo está em [`analise_erros.md`](analise_erros.md). Ela registra os IDs das perguntas, o comportamento observado e a classe de erro, incluindo filtros ausentes, agregações incorretas, junções que multiplicam valores, identificadores inexistentes e consultas que excederam o tempo limite.

## Interpretação e limitações

- Os números acima correspondem a uma rodada completa, em ambiente local, com o modelo `qwen2.5-coder:3b`, banco PostgreSQL 16 e os parâmetros registrados nos arquivos de resultado. Uma única execução não permite concluir que a taxa observada seja estável entre repetições ou ambientes.
- O tempo de resposta pode ser influenciado pelo carregamento inicial do modelo e pelas condições da máquina. Os tempos desta rodada devem ser tratados como observações do ambiente utilizado, não como uma comparação de desempenho generalizável.
- O arquivo atual contém um conjunto de 50 perguntas avaliado nesta rodada, mas ainda não formaliza, por si só, uma separação independente entre desenvolvimento/validação e teste cego. Além disso, algumas formulações ou tipos de consulta foram discutidos durante a preparação do projeto. Por isso, os resultados devem ser apresentados como **benchmark inicial do Marco 3**, e não como avaliação cega de generalização. Antes de ajustar prompts ou regras com base nos resultados e publicar uma nova métrica final, deve-se definir e documentar uma partição de desenvolvimento e uma partição de teste mantida separada.
- A igualdade em centavos é adequada ao foco financeiro do projeto, mas não mede equivalência semântica para além dos resultados retornados. A referência também precisa estar correta e representar exatamente a interpretação pretendida para cada pergunta.
- O baseline foi bloqueado em todos os casos. Para entender as causas em detalhe, é necessário inspecionar os SQLs gerados e os motivos de bloqueio registrados no CSV, sem atribuir a todos os casos a mesma causa sem essa inspeção.

## Artefatos

- `perguntas.jsonl`: perguntas, metadados e consultas de referência.
- `avaliar.py`: execução do benchmark, comparação dos resultados e geração de CSV/JSON; também permite reavaliar CSVs históricos.
- `resultados/`: arquivos CSV e JSON de cada execução e reavaliação.
- `analise_erros.md`: análise das 19 respostas incorretas ou não concluídas do assistente completo nesta rodada.
- `../tests/test_validador.py`: testes do validador, incluindo casos de custo no banco real quando `DATABASE_URL_LEITOR` está configurada.
