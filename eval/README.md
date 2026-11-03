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
