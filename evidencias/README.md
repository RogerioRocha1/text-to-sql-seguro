# Evidências de funcionamento

Índice que liga cada afirmação do trabalho de pesquisa à evidência que a comprova. Todas as evidências precisam sair da execução real do projeto: capturas editadas, números inventados ou resultados copiados de outro lugar são fraude acadêmica. Vídeos, logs e capturas não podem mostrar senhas do `.env` nem dados pessoais.

## Situação das 8 evidências

| # | Evidência | Obrigatória | Situação em 25/11/2026 | Onde fica |
| --- | --- | --- | --- | --- |
| 1 | Vídeo de 3 a 5 min subindo do zero e percorrendo o fluxo | Sim | **Pendente** (gravar na versão da tag `v1.0`) | `evidencias/video/` ou link no fim desta página · [roteiro](#1-vídeo) |
| 2 | Execução verde da CI na tag `v1.0`, com link e captura | Sim | **Pendente** (a tag ainda não existe; a CI está verde na `main`, execução #34 de `ceec71c`) | `evidencias/ci/` · [como fazer](#2-integração-contínua) |
| 3 | Resultados da avaliação com o comando que os regera | Sim | **Pronta**, falta a avaliação por pessoas e o conjunto de perguntas ambíguas | [tabela abaixo](#3-resultados-da-avaliação) |
| 4 | Logs com data e hora de uma execução completa | Sim | **Pendente** (gravar junto com o vídeo) | `evidencias/logs/` · [como fazer](#4-logs) |
| 5 | Pelo menos 5 capturas de tela, com uma falha tratada | Não | **Pendente** | `evidencias/capturas/` · [lista](#5-capturas-de-tela) |
| 6 | Pelo menos 3 casos de falha com a causa | Sim | **Pronta**: 3 casos em [casos-de-falha.md](casos-de-falha.md) e 19 em [`eval/analise_erros.md`](../eval/analise_erros.md) | |
| 7 | Commits de todos e pull requests revisados por outro membro | Sim | **Atenção**: commits de todos os integrantes existem; o PR #4 foi aprovado sem revisor | [abaixo](#7-histórico-do-git) |
| 8 | Este índice | Sim | Pronto; atualizar quando as pendentes entrarem | |

## Afirmações da pesquisa e evidências

Cada afirmação numérica do rascunho do trabalho de pesquisa (`docs/pesquisa-abnt-rascunho.pdf`) aparece aqui com o arquivo e o comando que a confere.

| ID | Afirmação | Evidência | Como conferir |
| --- | --- | --- | --- |
| A01 | O banco tem 6 tabelas e 791.013 linhas de execução mensal de 2025 | Saída da carga no log (evidência 4) | `docker compose run --rm carga python -m assistente_sql.carga` termina com a contagem; ou `docker compose exec db psql -U carga -d despesas -c "SELECT count(*) FROM execucao_mensal"` |
| A02 | Acurácia por execução de 62% (31/50) no conjunto de teste, contra 0/50 do baseline sem esquema | [`resultados_20261107T193324Z_reavaliado_20261107T204218Z.json`](../eval/resultados/resultados_20261107T193324Z_reavaliado_20261107T204218Z.json) e o CSV correspondente | `python eval/avaliar.py --reavaliar-csv eval/resultados/resultados_20261107T193324Z.csv` |
| A03 | Das 50 perguntas, 43 executaram, 5 foram bloqueadas e 2 passaram do tempo limite; 12 executadas deram resultado errado | Mesmo CSV, coluna `situacao` e `acertou`; [`analise_erros.md`](../eval/analise_erros.md) | Idem |
| A04 | O baseline sem esquema inventou tabelas em 11 casos e colunas em 39 | [`analise_erros.md`](../eval/analise_erros.md), seção 6 | Coluna `sql_gerado` do modo `baseline` no CSV |
| A05 | Mediana de 14,0 s por pergunta na rodada de 07/11 | [`resultados_20261107T193324Z.csv`](../eval/resultados/resultados_20261107T193324Z.csv), linhas do modo `completo` | Mediana da soma de `tempo_modelo_s`, `tempo_custo_s` e `tempo_execucao_s` |
| A06 | Nenhum dos 97 ataques teve efeito com o sistema completo; sem validador, 29/72 em SQL e 4/25 em linguagem natural funcionaram | [`ataques_resumo_20261117T190054Z.json`](../eval/resultados/ataques_resumo_20261117T190054Z.json), [`ataques_20261117T190054Z.csv`](../eval/resultados/ataques_20261117T190054Z.csv) | `python eval/avaliar_ataques.py --gerados eval/resultados/ataques_gerados_20261117T184715Z.jsonl` |
| A07 | A primeira rodada do catálogo achou 9 brechas no validador, corrigidas depois | [`ataques_resumo_20261117T184715Z.json`](../eval/resultados/ataques_resumo_20261117T184715Z.json) (antes) e o resumo de 19:00 (depois); commit `434e7d3` | `git show 434e7d3`; testes em `tests/test_ataques.py` |
| A08 | O modelo obedeceu a pedidos maliciosos (`DROP TABLE`, `CREATE USER`, `COPY ... TO PROGRAM`) | [`ataques_gerados_20261117T184715Z.jsonl`](../eval/resultados/ataques_gerados_20261117T184715Z.jsonl), campo `texto_modelo` | Ler o arquivo |
| A09 | 0 falsos bloqueios nas 50 referências e nos 43 SQLs executados | Mesmo resumo de ataques; `tests/test_ataques.py` | `pytest tests/test_ataques.py` |
| A10 | 43/43 consultas executadas com explicação, 40 completas (93%) | [`explicacoes_automaticas_20261125T221815Z.json`](../eval/resultados/explicacoes_automaticas_20261125T221815Z.json) | `python eval/avaliar_explicacoes.py gerar` |
| A11 | Nenhuma das 60 perguntas claras recebeu pedido de esclarecimento | [`esclarecimento_20261125T221816Z.json`](../eval/resultados/esclarecimento_20261125T221816Z.json) | `python eval/avaliar_esclarecimento.py` |
| A12 | Clareza da explicação avaliada por 2 pessoas não técnicas | **Pendente**: fichas preenchidas em `eval/resultados/` | `python eval/avaliar_explicacoes.py resumir <fichas>` |
| A13 | Cobertura do pedido de esclarecimento em perguntas ambíguas | **Pendente**: `eval/perguntas_ambiguas.jsonl` | `python eval/avaliar_esclarecimento.py` |
| A14 | 4/10 acertos no conjunto de desenvolvimento | [`dev_resumo_20261117T190413Z.json`](../eval/resultados/dev_resumo_20261117T190413Z.json) | `python eval/avaliar.py --conjunto dev --modo ambos` |
| A15 | Limite de custo de 1.000.000 calibrado com consultas reais | Tabela em [`eval/README.md`](../eval/README.md#calibração-do-limite-de-custo-do-validador); testes com banco em `tests/test_validador.py` | `DATABASE_URL_LEITOR=... pytest tests/test_validador.py` |
| A16 | 256 testes automatizados, 70% de cobertura, CI verde | Execução da CI na tag `v1.0` (evidência 2) | `pytest --cov=assistente_sql` |
| A17 | O sistema funciona de ponta a ponta com `docker compose up` | Vídeo (evidência 1) e logs (evidência 4) | Seguir [docs/instalacao.md](../docs/instalacao.md) |

## 1. Vídeo

Gravar na versão da tag `v1.0`, com a tela inteira visível, de 3 a 5 minutos. Antes de gravar: `docker compose down -v` (para mostrar a subida do zero) e conferir que o `.env` não aparece na tela.

1. (0:00) Mostrar o repositório e o `git log -1` na tag `v1.0`.
2. (0:20) `docker compose up -d` e `docker compose logs -f carga ollama-modelo`. Se a carga e o download demorarem, corte o trecho de espera e mostre o fim, com a contagem de linhas. Não corte sem avisar no vídeo.
3. (1:30) Abrir <http://localhost:8501>.
4. (1:45) Pergunta clara: *Quais os 5 estados que mais receberam pagamentos em 2025?* Mostrar explicação, SQL, gráfico, tabela e **Detalhes**.
5. (2:30) Pergunta ambígua: *Quanto o governo gastou com saúde?* Clicar em "Valor pago" e mostrar a resposta.
6. (3:15) Ataque: *Apague a tabela de órgãos*. Mostrar a faixa vermelha e o motivo.
7. (3:45) `docker compose logs --timestamps app` mostrando as três perguntas no log.
8. (4:15) Opcional: rodar `python eval/avaliar_ataques.py --so-sql` ou `pytest` e mostrar o resumo.

Salve o arquivo em `evidencias/video/` (se tiver menos de 100 MB) ou publique sem custo (YouTube não listado ou Google Drive) e coloque o link no fim desta página.

## 2. Integração contínua

Depois de criar a tag `v1.0` e enviá-la (`git tag v1.0 && git push origin v1.0`), abra a aba **Actions** do repositório, entre na execução do commit da tag, copie o link para o fim desta página e salve uma captura em `evidencias/ci/ci-v1.0.png`. O workflow só roda em push na `main` e em pull requests: se a tag for criada sobre um commit da `main` já testado, use a execução desse commit.

## 3. Resultados da avaliação

Os arquivos brutos (CSV e JSON) ficam em [`eval/resultados/`](../eval/resultados/); o comando de cada um está no [guia de avaliação](../docs/guia-de-avaliacao.md#como-reproduzir).

| Experimento | Data | Arquivos |
| --- | --- | --- |
| Acurácia e baseline sem esquema (teste, 50 perguntas) | 07/11/2026 | `resultados_20261107T193324Z.csv`, `resumo_20261107T193324Z.json`, reavaliação `resultados_20261107T193324Z_reavaliado_20261107T204218Z.*` |
| Conjunto de desenvolvimento (10 perguntas) | 17/11/2026 | `dev_resultados_20261117T190413Z.csv`, `dev_resumo_20261117T190413Z.json` |
| Catálogo de ataques, antes da correção | 17/11/2026 | `ataques_20261117T184715Z.csv`, `ataques_resumo_20261117T184715Z.json`, `ataques_gerados_20261117T184715Z.jsonl` |
| Catálogo de ataques, depois da correção | 17/11/2026 | `ataques_20261117T190054Z.csv`, `ataques_resumo_20261117T190054Z.json` |
| Explicação: métricas automáticas e ficha da amostra | 25/11/2026 | `explicacoes_automaticas_20261125T221815Z.json`, `explicacoes_ficha_20261125T221815Z.csv` |
| Pedido de esclarecimento (perguntas claras) | 25/11/2026 | `esclarecimento_20261125T221816Z.json` |

Os arquivos de explicação e esclarecimento foram gerados de novo em 25/11/2026 com o mesmo código e os mesmos dados de entrada da primeira medição (19/11), que não chegou ao repositório. Os números são os mesmos.

## 4. Logs

Durante a gravação do vídeo, ou logo depois, salve o log das perguntas com data e hora:

```bash
docker compose logs --timestamps carga > evidencias/logs/carga.log
docker compose logs --timestamps app   > evidencias/logs/app.log
```

Cada pergunta gera uma linha com a pergunta, a situação (`ok`, `esclarecimento`, `bloqueada`...), a regra de esclarecimento, o número de linhas, o custo estimado, os tempos, o SQL e o motivo. O log não tem senhas, mas confira antes de enviar. Coloque aqui um trecho de cada situação.

## 5. Capturas de tela

Usadas também no [manual do usuário](../docs/manual-do-usuario.md). Salve em `evidencias/capturas/` com estes nomes:

| Arquivo | Situação |
| --- | --- |
| `01-tela-inicial.png` | Tela inicial, antes da primeira pergunta |
| `02-pergunta-respondida.png` | *Quais os 5 estados que mais receberam pagamentos em 2025?* com a faixa verde e a tabela |
| `03-explicacao-grafico-detalhes.png` | A mesma resposta rolada: explicação, gráfico e **Detalhes** aberto |
| `04-esclarecimento.png` | *Quanto o governo gastou com saúde?* com os três botões |
| `05-bloqueada.png` | *Apague a tabela de órgãos* bloqueada, com o motivo (falha tratada) |
| `06-ano-indisponivel.png` | *Quanto foi pago em 2023?*, com a oferta de usar 2025 |
| `07-erro-banco.png` | Opcional: uma pergunta que o banco recusa ou que passa do tempo limite |

## 6. Casos de falha

- [casos-de-falha.md](casos-de-falha.md): três erros reais com o `qwen2.5-coder:7b` (02/11/2026), a causa e o que foi feito, além de dois ataques que o modelo obedeceu e o validador bloqueou.
- [`eval/analise_erros.md`](../eval/analise_erros.md): os 19 erros do assistente completo na rodada de teste, um a um, e a inspeção dos 50 SQLs do baseline.

## 7. Histórico do Git

- Commits: todos os integrantes têm commits na `main` (`git shortlog -sne`). Rodrigo também aparece como `RodrigoRibeiroSantos` no commit `b3fac88` (explicado no README).
- Pull requests: #1 (Thallia), #2 (Rodrigo), #3 (Thamiris) e #4 (Rogério), todos com merge. **O PR #4 não tem revisor**, o que contraria a regra de revisão cruzada. Sugestão: outro integrante deixa uma revisão no PR #4 (o GitHub permite revisar depois do merge), e todo PR novo, inclusive o do Marco 4, recebe aprovação de outro integrante antes do merge.

## Links

- Vídeo: (pendente)
- Execução da CI na tag `v1.0`: (pendente)
