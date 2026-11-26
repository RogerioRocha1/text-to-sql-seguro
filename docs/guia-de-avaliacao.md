# Guia de avaliação

Como reproduzir cada número do projeto com um comando. O protocolo completo, a calibração do custo e a análise de cada rodada estão em [`eval/README.md`](../eval/README.md); a análise dos 19 erros do assistente está em [`eval/analise_erros.md`](../eval/analise_erros.md).

## Protocolo

- **Conjunto de teste separado:** 50 perguntas (Q001–Q050) com SQL de referência conferido no banco. Elas não foram usadas para ajustar o prompt, que não muda desde 02/11/2026; o conjunto foi criado em 07/11/2026.
- **Conjunto de desenvolvimento:** 10 perguntas (D01–D10) para ajustar prompt e regras.
- **Acurácia por execução:** a resposta está certa quando as linhas devolvidas são iguais às da referência, com valores comparados em centavos e ordem exigida só nas perguntas de ranking (`comparar_ordem`).
- **Baselines:** (1) o mesmo modelo sem o esquema no prompt; (2) o mesmo SQL sem a etapa de validação, medido no catálogo de ataques.
- **Metas:** definidas na proposta técnica de 28/10/2026, antes do código, e não alteradas.

## Resultados frente às metas

| Métrica | Meta | Resultado | Situação | Arquivo |
| --- | --- | --- | --- | --- |
| Acurácia por execução (teste) | ≥ 70% e acima dos baselines | **62% (31/50)**; baseline sem esquema 0/50 | Abaixo da meta; acima do baseline | `resultados_20261107T193324Z_reavaliado_20261107T204218Z.json` |
| Ataques sem efeito | 100% | **72/72 em SQL e 25/25 em linguagem natural**, depois da correção de 9 brechas; sem validador, 29/72 e 4/25 tiveram efeito | Meta atingida | `ataques_resumo_20261117T190054Z.json` |
| Falsos bloqueios | ≤ 5% | **0%**: 0 das 50 referências e 0 dos 43 SQLs executados | Meta atingida | idem |
| Pedido de esclarecimento em perguntas ambíguas | ≥ 60% | Pendente (falta o conjunto de perguntas ambíguas). Perguntas claras com esclarecimento desnecessário: **0/60** | Pendente | `esclarecimento_20261125T221816Z.json` |
| Clareza da explicação | ≥ 75% "entendeu" | Pendente (avaliação por pessoas). Automática: **43/43 com explicação e 40/43 (93%) completas** | Pendente | `explicacoes_automaticas_20261125T221815Z.json` |
| Latência | Mediana ≤ 15 s | **14,0 s** na rodada de 07/11. Depois das otimizações de 25/11, com o modelo aquecido: 8 a 10 s na CPU e 1 a 3 s na GPU | Meta atingida | `resultados_20261107T193324Z.csv`; medições de 25/11 em [`eval/README.md`](../eval/README.md#desempenho-e-escolha-do-modelo-25112026) |

Todos os arquivos estão em `eval/resultados/`. As rodadas com o modelo usaram `qwen2.5-coder:3b`, temperatura 0, PostgreSQL 16, `CUSTO_MAXIMO` de 1.000.000 e `statement_timeout` de 15 s.

**O que mudou depois da rodada de 07/11.** O prompt e o modelo (3B) são os mesmos. Mudaram o validador (9 bloqueios novos em 17/11, que continuam aprovando os 43 SQLs executados e as 50 referências), a explicação (não altera o SQL) e o pedido de esclarecimento (não dispara em nenhuma das 50 perguntas). Em 25/11 também mudaram os parâmetros de geração: o contexto passou de 8.192 para 4.096 tokens, a resposta ficou limitada a 512 tokens e o gerador passou a tentar de novo quando o modelo entra em laço de repetição. Nas medições de desempenho essas mudanças não alteraram as respostas, mas não houve rodada do conjunto de teste com elas. Por isso, a recomendação é uma rodada de confirmação antes da tag `v1.0` (veja abaixo).

## Como reproduzir

Com o projeto no ar (`docker compose up -d`). Os resultados novos ganham a data e a hora no nome e não apagam os anteriores.

| O que reproduzir | Comando | Precisa de | Tempo aproximado |
| --- | --- | --- | --- |
| Acurácia e baseline sem esquema (teste) | `docker compose exec app python /app/eval/avaliar.py --modo ambos` | Banco e modelo | 15 a 30 min na CPU com o 3B aquecido |
| Recalcular a acurácia de 07/11 sem modelo nem banco | `docker compose exec app python /app/eval/avaliar.py --reavaliar-csv /app/eval/resultados/resultados_20261107T193324Z.csv` | Nada | Segundos |
| Conjunto de desenvolvimento | `docker compose exec app python /app/eval/avaliar.py --conjunto dev --modo ambos` | Banco e modelo | 5 a 10 min |
| Ataques em SQL, com e sem validador | `docker compose exec app python /app/eval/avaliar_ataques.py --so-sql` | Banco | Cerca de 2 min |
| Todos os ataques, reaproveitando o texto do modelo de 17/11 | `docker compose exec app python /app/eval/avaliar_ataques.py --gerados /app/eval/resultados/ataques_gerados_20261117T184715Z.jsonl` | Banco | Cerca de 2 min |
| Métricas automáticas da explicação e ficha da amostra | `docker compose exec app python /app/eval/avaliar_explicacoes.py gerar` | Nada | Segundos |
| Clareza a partir das fichas preenchidas | `docker compose exec app python /app/eval/avaliar_explicacoes.py resumir /app/eval/resultados/ficha_pessoa1.csv /app/eval/resultados/ficha_pessoa2.csv` | Fichas | Segundos |
| Pedido de esclarecimento | `docker compose exec app python /app/eval/avaliar_esclarecimento.py` | Nada | Segundos |
| Testes de custo no banco real | `DATABASE_URL_LEITOR=... pytest tests/test_validador.py -v` | Banco | Segundos |

Para usar o modelo da avaliação, defina `OLLAMA_MODELO=qwen2.5-coder:3b` no `.env` e rode `docker compose up -d`. Com outro modelo, o resultado é de outra condição e deve ser registrado como rodada nova.

## O que falta para fechar a avaliação

Duas metas dependem de pessoas e não podem ser preenchidas pela IA nem por quem escreveu as regras:

1. **Clareza da explicação.** Duas pessoas sem formação em TI leem a pergunta e a explicação de cada uma das 20 consultas sorteadas em `explicacoes_ficha_20261125T221815Z.csv` (sem olhar o SQL) e marcam `entendeu` como `sim`, `parcial` ou `nao`. Um integrante marca `fiel_ao_sql` numa terceira cópia. O passo a passo está em [`eval/README.md`](../eval/README.md#avaliação-por-pessoas-pendente).
2. **Cobertura do esclarecimento.** Um integrante que **não leu** `esclarecimento.py` escreve `eval/perguntas_ambiguas.jsonl`, com perguntas ambíguas (`"ambigua": true`) e algumas claras de controle (`"ambigua": false`), uma por linha: `{"id": "A01", "pergunta": "...", "ambigua": true, "motivo": "não diz se é valor pago ou empenhado"}`. Depois roda `avaliar_esclarecimento.py`.

Recomendado, e sem depender de outras pessoas: **uma rodada de confirmação do conjunto de teste com a configuração atual** (`docker compose exec app python /app/eval/avaliar.py --modo ambos`, com o 3B). Ela mostra se os parâmetros de 25/11 mudaram a acurácia e fecha a avaliação com a versão que vai na tag. Registre a rodada nova sem apagar a de 07/11.

Opcional, se houver uma máquina com GPU de 6 GB ou mais: uma rodada com `qwen2.5-coder:7b`, recomendado no README para quem tem GPU. Todos os números de acurácia hoje são do 3B.

## Cuidados de interpretação

- Uma única rodada por condição: não há medida de variação entre repetições.
- O conjunto de teste foi escrito pelo grupo, que conhece o esquema; ele mede este banco, não generalização para outros.
- O baseline sem esquema foi bloqueado em 50 de 50 perguntas por inventar tabelas e colunas. O 0% mede a dependência do esquema, não a qualidade do SQL em si.
- `situacao = ok` não quer dizer resposta certa: 12 das 43 consultas executadas devolveram resultado diferente da referência.
- Os tempos dependem da máquina; a primeira pergunta inclui o carregamento do modelo.
