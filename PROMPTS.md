# Registro de uso de IA na programação

Regras da disciplina: pelo menos 10 interações relevantes até a entrega final. Cada registro traz o prompt, um resumo da resposta e a decisão do grupo (aceito, corrigido ou descartado), com o motivo. Código gerado por IA só entra na `main` com teste passando na CI e revisão de outro integrante.

**Ferramentas usadas:** Claude (chat), Claude Code (extensão do VS Code). _(acrescentar outras que o grupo usar)_

---

## 001 · Validador de SQL inicial

- **Data:** 28/10/2026
- **Integrante:** _(Rogério Rocha)_
- **Ferramenta:** Claude
- **Prompt (resumo):** pedido de um esqueleto de repositório para o Marco 1, com validador de SQL em SQLGlot, testes de ataques e CI no GitHub Actions.
- **Resposta (resumo):** validador que aceita só um `SELECT`, bloqueia DDL, DML e comandos do DuckDB, restringe tabelas a uma lista, bloqueia funções de leitura de arquivo e injeta `LIMIT`; 37 casos de teste.
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:** _(o que o grupo conferiu, o que mudou e por quê)_

---

## 002 · Revisão geral do projeto - Marco 1

- **Data:*29/10/2026*
- **Integrante:** _(Rogério Rocha)_
- **Ferramenta:** Claude
- **Prompt (resumo):** Analise detalhada sobre toda a criação e edição dos arquivos PROMPTS.md e README.md 
- **Resposta (resumo):** Alterado adicionando nome dos envolvidos e seus papeis, edição do documento "Proposta Técnica - Assistente de Dados com Text-to-SQL Seguro" 
- **Decisão:** aceito / corrigido / descartado
- **Motivo e revisão:** (Detalhar mapeando os papeis de cada integrante do projeto, e complementando o que o Claude não preencheu)

---

## 003 · Carga dos dados de despesas no PostgreSQL (Marco 2)

- **Data:** 29/10/2026
- **Integrante:** Rodrigo Santos
- **Ferramenta:** Claude Code (extensão do VS Code)
- **Prompt (resumo):** "Analise o material que já temos e vamos construir o Marco 2. Inicialmente, precisamos buscar dados públicos de gastos do governo e subir em um banco numa VM no Docker." Antes de começar, a IA perguntou onde o banco ia rodar, qual banco usar e quais dados baixar. O grupo respondeu: Docker Desktop local, PostgreSQL no lugar do DuckDB previsto no Marco 1 e Orçamento + Execução da Despesa de 2025.
- **Resposta (resumo):** a IA baixou um arquivo de amostra para conferir o formato real (Windows-1252, separador `;`, decimal com vírgula) e criou:
  - `fontes.py`: URLs e cabeçalho esperado de cada arquivo, com validação.
  - `esquema.py`: 6 tabelas com comentários e a transformação a partir do staging.
  - `carga.py`: download com cache e retentativa, `COPY` em uma única transação.
  - `docker-compose.yml`, `Dockerfile` e `docker/postgres/01-leitor.sh`, que cria o usuário somente leitura.
  - 9 testes novos.

  Antes de carregar, a IA varreu os 13 arquivos e encontrou linhas sem órgão em junho e dezembro (cerca de R$ 155 milhões por mês) e o órgão `-3` sem nome. Ela propôs normalizar essas linhas para o código `-1` "Sem informação", em vez de descartá-las.
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:** _(o grupo deve conferir e decidir. Pontos a revisar:)_
  - A troca de DuckDB por PostgreSQL exige adaptar o validador, que ainda usa dialeto `duckdb` e schema `main`.
  - O nome do autor de emenda parlamentar foi descartado (LGPD) e virou só a coluna `com_emenda`.
  - A normalização dos órgãos sem código é uma decisão de dados que precisa ser documentada no trabalho.

---

## 004 · Execução da carga e erro da IA no schema das tabelas

- **Data:** 29/10/2026
- **Integrante:** Rodrigo Santos
- **Ferramenta:** Claude Code (extensão do VS Code)
- **Prompt (resumo):** "Itens 1 e 2 feitos [WSL e Docker Desktop instalados], rode o item 3."
- **Resposta (resumo):** a IA iniciou o Docker Desktop, criou o `.env` com senhas aleatórias, subiu o PostgreSQL e rodou a carga: 791.013 linhas de execução e 26.160 de orçamento em cerca de 80 s. Depois conferiu duas coisas:
  - **Totais em reais:** somou os valores no banco e direto nos CSVs, e bateram ao centavo.
  - **Permissões do usuário `leitor`:** o teste revelou que ele não enxergava nenhuma tabela.
- **Decisão:** corrigido
- **Motivo e revisão:** **erro da IA.**
  - **Causa:** o `search_path` padrão do Postgres é `"$user", public`. Como o usuário dono se chama `carga`, mesmo nome do schema de staging, as tabelas finais foram criadas em `carga.*` em vez de `public.*`.
  - **Correção:** `search_path=public` fixo na conexão e recriação do schema `carga` a cada execução.
  - **Verificação:** depois da correção, o `leitor` lê as 6 tabelas, mas `DELETE`, `INSERT`, `CREATE`, `DROP`, `pg_read_file` e o acesso ao schema `carga` são negados. Isso vale mesmo numa transação aberta como `READ WRITE`.
  - **Outro erro da IA:** ela estimou "~767 mil linhas" antes da carga, mas o total real era 791.013. A contagem do banco foi conferida contra a soma das linhas dos CSVs.
  - **Bloqueio do ambiente:** a IA tentou instalar um PostgreSQL temporário via `pip` para testar antes de o Docker existir, e a permissão automática do Claude Code bloqueou o comando.

---

## 005 · Guia de instalação do Docker e do banco no README

- **Data:** 29/10/2026
- **Integrante:** Rodrigo Santos
- **Ferramenta:** Claude Code (extensão do VS Code)
- **Prompt (resumo):** "Inclua no README, na parte do Marco 2, como instalar o Docker e as dependências para ter o banco na VM."
- **Resposta (resumo):** seção com:
  - instalação no Windows (WSL2 + Docker Desktop + Git) e numa VM Ubuntu (Docker Engine pelo repositório oficial);
  - passos para configurar e subir o banco, com a saída esperada da carga;
  - comandos de conferência e acesso via túnel SSH;
  - tabela de problemas comuns.

  A IA conferiu no container que o UID do usuário da carga é 1000, valor citado na solução de permissão de `data/raw`.
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:** _(o caminho Windows foi executado nesta sessão; os comandos para Ubuntu vêm da documentação oficial do Docker e **não foram testados** numa VM. Um integrante deve testá-los antes da entrega.)_

---

## 006 · Verificação das regras de registro de uso de IA

- **Data:** 29/10/2026
- **Integrante:** Rodrigo Santos
- **Ferramenta:** Claude Code (extensão do VS Code)
- **Prompt (resumo):** "Verifique no enunciado se não era necessário salvar a interação com a IA do chat em algum arquivo."
- **Resposta (resumo):** a IA confirmou a regra do enunciado: registro em `PROMPTS.md` com pelo menos 10 interações (prompt, resumo, decisão e motivo), avaliado no critério 5 da rubrica. Ela registrou as interações 003 a 006 e preencheu a lista de ferramentas.
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:** _(conferir se os resumos refletem o que aconteceu)_

---

## 007 · Levantamento das pendências do Marco 2

- **Data:** 31/10/2026
- **Integrante:** Thallia Silva de Oliveira
- **Ferramenta:** Claude (chat)
- **Prompt (resumo):** "Identifique o que ainda falta para finalizar o Marco 2 na minha branch `dados-qualidade`, dentro do meu papel de Dados e Qualidade."
- **Resposta (resumo):** o Claude apontou as pendências do meu papel: decisões em branco no `PROMPTS.md`, documentar a normalização dos órgãos sem código, completar a tabela de contribuição do README e testar os comandos de Ubuntu do guia do Docker.
- **Decisão:** aceito
- **Motivo e revisão:** conferi cada pendência nos arquivos do repositório antes de começar a corrigir.

---

## 008 · Validador adaptado para PostgreSQL, com limite de custo (preparação do Marco 3)

- **Data:** 02/11/2026
- **Integrante:** Rodrigo Santos
- **Ferramenta:** Claude Code (extensão do VS Code)
- **Prompt (resumo):** "Analise os últimos commits da branch main. Vamos começar a preparação para o Marco 3." Depois: "Podemos começar pelo passo 1 [validador para PostgreSQL]. Faça no padrão de gerar uma branch nova."
- **Resposta (resumo):** a IA analisou os commits e apontou que o Marco 2 estava marcado como concluído no README sem que existissem ainda Ollama, Streamlit ou o fluxo ponta a ponta. Depois, propôs um plano para o Marco 3. Na branch `validador-postgres`:
  - Testou primeiro como o SQLGlot interpreta ataques do PostgreSQL e encontrou três brechas da versão DuckDB: `SELECT * INTO <tabela permitida>` (cria tabela), `FOR UPDATE` e funções perigosas que não estavam na lista.
  - Trocou o dialeto para `postgres` e o schema para `public`, adicionou as funções perigosas e criou `verificar_custo`, que usa `EXPLAIN` sem executar a consulta.
  - Calibrou o limite de custo medindo 10 consultas no banco real (tabela em `eval/README.md`): legítimas até cerca de 47 mil, abusivas a partir de 31 milhões. O limite ficou em 1.000.000.
  - Os testes passaram de 46 para 88: o catálogo tem 54 casos bloqueados, há 4 testes de custo com cursor falso, para a CI, e 4 contra o banco real. A cobertura do validador é de 100%.
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:** _(o revisor do PR deve conferir:)_
  - A lista de funções proibidas é uma lista de bloqueio, incompleta por natureza; a proteção final continua sendo o usuário `leitor`.
  - `version()` e `current_user` foram bloqueadas por precaução, embora o risco seja baixo.
  - O limite de 1.000.000 foi calibrado com poucas consultas; deve ser revisto com as 50 perguntas de referência.
  - **Erro da IA (corrigido):** na primeira versão, a mensagem para `outro_banco.public.orgao` dizia "schema 'public' não pode ser consultado". Ela foi trocada por uma mensagem que fala do banco externo.

---

## 009 · Gerador com Ollama e fluxo ponta a ponta (Marco 2)

- **Data:** 02/11/2026
- **Integrante:** Rodrigo Santos
- **Ferramenta:** Claude Code (extensão do VS Code)
- **Prompt (resumo):** "Qual o próximo passo para finalizarmos o Marco 2?" e, depois do plano (gerador → executor → Streamlit → Docker), "pode seguir".
- **Resposta (resumo):** na branch `prototipo-ponta-a-ponta`, criada a partir de `validador-postgres`:
  - **Ollama no compose:** serviços `ollama` e `ollama-modelo`; GPU opcional em `docker-compose.gpu.yml`, para não quebrar `docker compose up` em máquinas sem NVIDIA.
  - **`gerador.py`:** lê do banco o esquema (comentários, chaves estrangeiras e valores comuns via `pg_stats`), monta o prompt como `CREATE TABLE` comentado e chama a API do Ollama.
  - **`assistente.py`:** encadeia gerar → validar → custo → executar como `leitor`, em transação somente leitura sempre desfeita; inclui uma linha de comando.
  - **Carga:** passou a criar a extensão `unaccent`, porque 262 nomes têm acento e 2.807 não, e a rodar `ANALYZE`.
  - **Testes:** 21 novos (107 no total); o modelo é falso na CI.
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:**
  - **Bloqueio de ambiente:** a imagem do Ollama (8,5 GB) deixou só 5,1 GB livres no disco; o integrante liberou espaço antes de baixar o modelo de 7B.
  - **Erros do modelo encontrados no teste manual:** "Ministério da Saúde" e "Ministério da Educação" retornaram `NULL`, porque o modelo filtrou `orgao.nome` em vez de `nome_orgao_superior`. Uma regra no prompt corrigiu, e os valores passaram a bater com o SQL de referência.
  - **Erro que ficou em aberto:** "Fiocruz" foi respondida com o total do Ministério da Saúde. Foi registrada em `evidencias/casos-de-falha.md` em vez de ajustar o prompt pergunta a pergunta, para não decorar perguntas que poderiam cair na avaliação.
  - **Ataques em português:** o modelo gerou `DROP TABLE` quando pedido, e o validador bloqueou.

---

## 010 · Interface Streamlit e projeto completo com `docker compose up` (Marco 2)

- **Data:** 02/11/2026
- **Integrante:** Rodrigo Santos
- **Ferramenta:** Claude Code (extensão do VS Code)
- **Prompt (resumo):** "Vamos seguir" (interface Streamlit e serviço `app` no compose, últimos itens do Marco 2).
- **Resposta (resumo):**
  - **`app.py`:** pergunta, situação, SQL, tabela, gráfico e detalhes de tempo, custo e tokens.
  - **`apresentacao.py`:** converte o resultado em tabela e escolhe o gráfico (linha para mês, barras para categoria) sem depender do Streamlit, para ser testável.
  - **Serviço `app` no compose:** espera a carga e o download do modelo.
  - **Carga com `--se-vazio`** e download do modelo só quando ele falta: o projeto sobe em segundos e sem internet depois da primeira vez.
  - **Testes:** 10 novos, incluindo a interface com o simulador do Streamlit (`AppTest`).
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:**
  - **Teste dentro do container `app`:** 3 perguntas pela interface.
    - "valor pago por mês na função Saúde": 12 linhas e gráfico de linha.
    - "5 órgãos superiores com maior orçamento": gráfico de barras.
    - "Apague a tabela de órgãos": bloqueada, com o motivo na tela.
  - **Ponto a conferir:** o modelo ainda usa `funcao.nome = 'Saúde'` (com `=`) apesar da regra; funcionou porque o nome é exato, mas é frágil. Avaliar no Marco 3.
  - **Log da interface:** o log do servidor no container ficou vazio nesse teste, porque as perguntas foram feitas por outro processo. O log de evidência precisa sair do uso real pelo navegador.

---

## Modelo para novos registros

```markdown
## 00N · Título curto

- **Data:**
- **Integrante:**
- **Ferramenta:**
- **Prompt (resumo):**
- **Resposta (resumo):**
- **Decisão:** aceito / corrigido / descartado
- **Motivo e revisão:**
```
