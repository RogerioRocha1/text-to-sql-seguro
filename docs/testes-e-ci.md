# Testes e integração contínua

## Como executar

```bash
pip install -e ".[dev]"
pytest -v                                   # 256 testes; 15 pulados sem banco
pytest --cov=assistente_sql --cov-report=term-missing
ruff check . && ruff format --check .       # lint e formatação, como na CI
```

Os 15 testes marcados com `@banco` (em [`conftest.py`](../tests/conftest.py)) precisam do banco carregado e só rodam com `DATABASE_URL_LEITOR` definida, por exemplo `postgresql://leitor:<senha>@127.0.0.1:5432/despesas` com o `docker compose up` no ar. Nenhum teste chama o Ollama: o modelo é substituído por um modelo falso que devolve um texto fixo.

## O que é testado

| Arquivo | Testes | O que cobre |
| --- | ---: | --- |
| [`test_validador.py`](../tests/test_validador.py) | 90 | Consultas de leitura aprovadas; `LIMIT` acrescentado, reduzido ou mantido; dezenas de casos bloqueados (escrita, `WITH` com escrita, `SELECT INTO`, `FOR UPDATE`, vários comandos, funções perigosas, dados da sessão, `reg*`, `repeat` gigante, schemas e tabelas fora da lista); limite de custo; com banco, custo real de consultas legítimas e abusivas |
| [`test_ataques.py`](../tests/test_ataques.py) | 78 | O catálogo de 97 ataques (`eval/ataques.jsonl`) como teste: cada ataque em SQL esperado no validador é bloqueado; os que passam por ele são parados pelo banco (com banco) |
| [`test_explicacao.py`](../tests/test_explicacao.py) | 24 | Explicação de totais, rankings, filtros, percentuais, contagens, `ORDER BY` pela posição; filtro que o usuário não pediu aparece no texto; trecho desconhecido vira aviso e não texto inventado |
| [`test_esclarecimento.py`](../tests/test_esclarecimento.py) | 18 | Perguntas ambíguas disparam a regra certa; perguntas claras seguem direto; a escolha do usuário resolve a ambiguidade; ano fora de 2025; código de 5 dígitos não é confundido com ano |
| [`test_assistente.py`](../tests/test_assistente.py) | 12 | Configuração (modelo padrão 3B, contexto, tempo carregado); fluxo ponta a ponta com modelo falso: SQL destrutivo bloqueado antes do banco; falha do modelo; pergunta ambígua para antes do modelo; consulta bloqueada sem explicação; com banco, resposta completa, bloqueio por custo, erro de coluna e transação somente leitura |
| [`test_gerador.py`](../tests/test_gerador.py) | 14 | Esquema escrito como `CREATE TABLE` comentado; mensagens do prompt; extração do bloco `sql`; pedido HTTP ao Ollama (simulado), com contexto, limite de tokens e tempo carregado; nova tentativa só no laço de repetição; mensagem de erro do Ollama; com banco, leitura do esquema real |
| [`test_apresentacao.py`](../tests/test_apresentacao.py) | 11 | Conversão da tabela, colunas repetidas, nulos, escolha do gráfico; tela sem configuração mostra erro; com banco, a tela bloqueia SQL destrutivo |
| [`test_carga.py`](../tests/test_carga.py) | 9 | Lista dos 13 arquivos do ano; cabeçalho em Windows-1252 aceito; coluna trocada ou a mais recusada; staging no schema `carga`; leitura do CSV dentro do ZIP |

## Cobertura

Medida em 25/11/2026 com `pytest --cov=assistente_sql`, sem banco (como na CI):

| Módulo | Cobertura |
| --- | ---: |
| `validador.py` | 100% |
| `esclarecimento.py` | 100% |
| `apresentacao.py`, `esquema.py`, `fontes.py` | 100% |
| `gerador.py` | 86% |
| `explicacao.py` | 82% |
| `assistente.py` | 55% (o resto roda só com banco ou no CLI) |
| `carga.py` | 29% (download e gravação no banco não rodam na CI) |
| `app.py` | 0% na conta (a tela é exercitada pelo `AppTest` do Streamlit em `test_apresentacao.py`, que executa o arquivo como script e não é contado pelo `--cov=assistente_sql`; sem banco, só o caso de configuração incompleta roda) |
| **Total** | **70%** |

Os módulos que decidem a segurança (`validador.py`) e o comportamento com o usuário (`esclarecimento.py`) estão em 100%.

## Integração contínua

O workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) roda no GitHub Actions a cada push na `main` e em todo pull request:

1. Python 3.12 no `ubuntu-latest`;
2. `pip install -e ".[dev]"`;
3. `ruff check .` e `ruff format --check .`;
4. `pytest -v --cov=assistente_sql --cov-report=term-missing`.

A CI não sobe o banco nem o Ollama, então os 15 testes com `@banco` são pulados lá. Eles devem ser rodados localmente antes da tag `v1.0` (veja [evidências](../evidencias/README.md)). As execuções ficam em <https://github.com/RogerioRocha1/text-to-sql-seguro/actions>.

Pela regra da disciplina, código gerado por IA só entra na `main` com teste que passa na CI e com revisão de outro integrante no pull request.
