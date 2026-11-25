# Referência da interface e dos comandos

O projeto não tem API HTTP própria: o usuário usa a tela do Streamlit, e o desenvolvedor usa os comandos de linha abaixo. Todos os comandos `docker compose exec app ...` rodam com o projeto no ar; os comandos `python ...` rodam fora do Docker, no ambiente de desenvolvimento, com `DATABASE_URL_LEITOR` e `OLLAMA_URL` definidas.

## Tela (Streamlit)

Endereço: <http://localhost:8501> (porta em `APP_PORTA`). Passo a passo com capturas no [manual do usuário](manual-do-usuario.md).

| Elemento | Quando aparece | O que mostra |
| --- | --- | --- |
| Aviso azul "Preparando o modelo" | Logo depois de abrir, enquanto o modelo carrega em segundo plano | Pode digitar; a primeira resposta espera o fim do preparo |
| Campo "Sua pergunta" e botão **Perguntar** | Sempre | Texto livre em português; abaixo, três perguntas de exemplo |
| Caixa azul com botões | Pergunta ambígua (`esclarecimento`) | A pergunta do assistente e uma opção por botão; clicar refaz a pergunta com a escolha |
| Faixa verde | `ok` | "Consulta executada: N linha(s)." |
| Faixa vermelha | `bloqueada`, `erro_execucao`, `erro_modelo` | A situação e o motivo |
| **O que a consulta faz** | Consulta aprovada pelo validador | Explicação em tópicos; se parte for técnica demais, um aviso para conferir o SQL |
| SQL | Sempre que houve SQL | "SQL executado" (com `LIMIT`) ou "SQL gerado pelo modelo" (quando bloqueado) |
| Gráfico | Resultado com uma categoria e um valor | Linha para meses, barras horizontais para as demais categorias |
| Tabela | `ok` com linhas | Resultado com valores formatados; aviso quando não há registros |
| **Detalhes** | Sempre | JSON com o tempo de cada etapa, o custo estimado e os tokens de entrada e saída |

## Perguntas pela linha de comando

```bash
python -m assistente_sql.assistente "Quanto o Ministério da Saúde pagou em 2025?" ["outra pergunta" ...]
python -m assistente_sql.assistente --sem-esclarecimento "Quanto o governo gastou com saúde?"
# dentro do Docker:
docker compose exec app python -m assistente_sql.assistente "Quanto o Ministério da Saúde pagou em 2025?"
```

| Opção | Efeito |
| --- | --- |
| `perguntas` (uma ou mais) | Responde cada uma e imprime situação, tempos, SQL, explicação, motivo e as 10 primeiras linhas; em pergunta ambígua, imprime as opções |
| `--sem-esclarecimento` | Não para nas perguntas ambíguas; gera o SQL mesmo assim |

## Carga dos dados

```bash
docker compose run --rm carga                                  # carga padrão (só se o banco estiver vazio)
docker compose run --rm carga python -m assistente_sql.carga   # força a recarga (recria as tabelas)
python -m assistente_sql.carga --so-baixar                     # só baixa os ZIPs para data/raw/
```

| Opção | Efeito |
| --- | --- |
| `--ano ANO` | Ano a baixar (padrão 2025, ou `ANO_DADOS`) |
| `--so-baixar` | Baixa e confere os arquivos sem conectar ao banco |
| `--se-vazio` | Pula a carga se o banco já tem dados (usada pelo `docker compose up`) |

## Scripts de avaliação

Detalhes de cada experimento em [guia-de-avaliacao.md](guia-de-avaliacao.md). Os resultados vão para `eval/resultados/` com a data e a hora em UTC no nome (`AAAAMMDDTHHMMSSZ`).

| Comando | Precisa de | Opções |
| --- | --- | --- |
| `python eval/avaliar.py` | Banco e modelo | `--modo completo\|baseline\|ambos`, `--conjunto teste\|dev`, `--limite N`, `--reavaliar-csv ARQUIVO` (recalcula sem modelo nem banco) |
| `python eval/avaliar_ataques.py` | Banco; modelo só para os ataques em linguagem natural | `--so-sql` (sem modelo), `--gerados ARQUIVO.jsonl` (reaproveita o texto já gerado pelo modelo) |
| `python eval/avaliar_explicacoes.py gerar` | Nada (lê um CSV de `avaliar.py`) | `--csv ARQUIVO`, `--amostra 20`, `--semente 9` |
| `python eval/avaliar_explicacoes.py resumir FICHA.csv [...]` | Nada | Fichas preenchidas pelas pessoas avaliadoras |
| `python eval/avaliar_esclarecimento.py` | Nada | Lê `perguntas.jsonl`, `perguntas_dev.jsonl` e, se existir, `perguntas_ambiguas.jsonl` |

## Uso como biblioteca

O fluxo inteiro está em uma função, usada pela tela, pelo CLI e pela avaliação:

```python
from assistente_sql.assistente import responder
from assistente_sql.gerador import ModeloOllama

resposta = responder(
    pergunta,
    ModeloOllama(url, nome),
    conexao_leitor,
    esquema,
    limite_linhas=1000,
    custo_maximo=1_000_000,
    esclarecer=True,
)
resposta.situacao  # ok | esclarecimento | bloqueada | erro_execucao | erro_modelo
resposta.sql_executado  # SQL com LIMIT que foi ao banco (None se não executou)
resposta.explicacao  # Explicacao(passos, completa); .texto junta os passos em tópicos
resposta.esclarecimento  # Esclarecimento(regra, pergunta, opcoes) quando ambígua
resposta.colunas, resposta.linhas, resposta.tempos, resposta.custo_estimado, resposta.motivo
```

Outras funções públicas: `validador.validar(sql, tabelas, limite)` e `validador.verificar_custo(cursor, validacao, custo_maximo)`, `esclarecimento.verificar(pergunta)`, `explicacao.explicar(sql)`, `gerador.ler_esquema(cursor)` e `gerador.formatar_esquema(tabelas)`.

## Comandos úteis do Docker Compose

| Comando | Para quê |
| --- | --- |
| `docker compose up -d` | Sobe tudo |
| `docker compose ps -a` | Situação dos serviços |
| `docker compose logs -f --timestamps app` | Log das perguntas, com data e hora |
| `docker compose exec db psql -U leitor -d despesas` | Console SQL como usuário somente leitura |
| `docker compose up -d --build` | Reconstrói a imagem depois de `git pull` |
| `docker compose stop` / `docker compose down -v` | Para / apaga tudo, inclusive banco e modelo |
