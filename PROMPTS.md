# Registro de uso de IA na programação

Regras da disciplina: pelo menos 10 interações relevantes até a entrega final. Cada registro traz o prompt, um resumo da resposta e a decisão do grupo (aceito, corrigido ou descartado), com o motivo. Código gerado por IA só entra na `main` com teste passando na CI e revisão de outro integrante.

**Ferramentas usadas:** Claude (chat), Claude Code (extensão do VS Code), ChatGPT (GPT-6). _(acrescentar outras que o grupo usar)_

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

## 011 · Guia de instalação completo e identidade do Git

- **Data:** 02/11/2026
- **Integrante:** Rodrigo Santos
- **Ferramenta:** Claude Code (extensão do VS Code)
- **Prompt (resumo):** "Add no README, junto com o guia de instalação do Docker, se precisa instalar algo mais e a rota para abrir o chat para perguntas." Depois: "Os commits feitos na minha máquina estão indo com o e-mail 2411288@escolas.anchieta.br?"
- **Resposta (resumo):**
  - **README:** o guia passou a cobrir o projeto inteiro:
    - o que é obrigatório instalar (só Docker e Git) e o que é opcional (driver NVIDIA, Python para desenvolvimento);
    - requisitos atualizados: cerca de 16 GB de disco e 8 GB de RAM para o modelo 7B, em vez dos 3 GB e 4 GB de quando só havia o banco;
    - a seção "Abrir o chat" (http://localhost:8501) e 7 problemas comuns novos;
    - `APP_PORTA` no `.env.example`.
  - **Git:** a IA verificou que os commits locais saíam com a conta pessoal (`RodrigoRibeiroSantos`, e-mail noreply). Ela configurou a identidade `rodrigo-santos-2411288` só neste repositório e reescreveu o autor dos 3 commits ainda não enviados, preservando datas e conteúdo. O `b3fac88`, já na `main`, ficou como estava, com uma nota no README.
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:**
  - **Erro da IA (corrigido):** o comando de checagem da GPU escrito no README (`docker run ... ollama/ollama nvidia-smi`) não funcionava, porque a imagem trata `nvidia-smi` como subcomando do `ollama`. A IA rodou o comando antes de entregar, viu o erro e corrigiu para `--entrypoint nvidia-smi`.
  - **Afirmação retirada:** o tempo da primeira pergunta na CPU ("alguns minutos") não tinha sido medido e passou a constar como não medido.
  - **Falha no ambiente:** a primeira tentativa de reescrever os autores falhou porque o PowerShell quebrou as aspas do comando; o Git recusou antes de alterar algo.
  - **Não testado:** os passos de Linux (NVIDIA Container Toolkit) e a subida em máquina sem GPU.

---

## 012 · Dúvidas sobre o funcionamento e PR único do Marco 2

- **Data:** 02/11/2026
- **Integrante:** Rodrigo Santos
- **Ferramenta:** Claude Code (extensão do VS Code)
- **Prompt (resumo):** "Quais exemplos de pergunta temos?", "As perguntas são hardcoded ou há alguma inteligência para interpretar e converter no SQL?" e "Vamos fazer [o PR]. Quero subir apenas 1 PR contendo tudo que fizemos. Os prompts foram salvos no arquivo?"
- **Resposta (resumo):**
  - **Exemplos:** a IA listou os 3 exemplos da interface e as perguntas já testadas, separando o que foi verificado das ideias não testadas. Também avisou que as perguntas usadas nos testes não podem entrar no conjunto de teste do Marco 3.
  - **Funcionamento:** explicou que nada é fixo além das 3 sugestões de texto e das regras gerais do prompt. O SQL é escrito pelo modelo a cada pergunta, a partir do esquema lido do banco. Citou como prova os erros do modelo (Fiocruz) e o `DROP TABLE` gerado por ele.
  - **PR:** conferiu que os registros 003 a 011 estavam no arquivo, criou este registro e enviou a branch `prototipo-ponta-a-ponta`, que já contém o commit do validador, para um PR único na `main`.
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:** _(o revisor do PR confere o conjunto; as decisões dos registros 003, 005, 006 e 008 a 012 ainda precisam ser preenchidas pelo grupo)_

---

## 013 · Construção do conjunto de 50 perguntas de referência (Marco 3)

- **Data:** 07/11/2026
- **Integrante:** Thamiris de Oliveira e Silva
- **Ferramenta:** ChatGPT (GPT-6)
- **Prompt (resumo):** Solicitação de orientação para construir um conjunto de 50 perguntas de avaliação para o assistente Text-to-SQL, utilizando o esquema e os dados reais do PostgreSQL, com SQL de referência, resultados esperados, categorias e níveis de dificuldade. As perguntas já utilizadas no desenvolvimento deveriam ser evitadas.
- **Resposta (resumo):** A IA orientou a exploração das dimensões disponíveis no banco de 2025 e propôs o formato JSONL. O grupo construiu `eval/perguntas.jsonl` com 50 perguntas, cada uma contendo identificador, pergunta em linguagem natural, SQL de referência, resultado esperado, categoria e dificuldade. Cada consulta foi executada no PostgreSQL antes de ser registrada.
- **Decisão:** aceito, com correções durante a construção.
- **Motivo e revisão:** O grupo executou as consultas e conferiu os resultados diretamente no banco. Quando foi identificado que o nome de um elemento de despesa estava realmente truncado na base, a pergunta correspondente foi substituída por uma consulta sobre o valor liquidado. A pergunta sobre restos a pagar inscritos também teve sua redação ajustada para deixar explícito que o resultado representa um saldo líquido de valores positivos e negativos. Ao final, as 50 referências foram conferidas novamente pelo avaliador, sem divergências.

---

## 014 · Implementação do avaliador experimental automatizado (Marco 3)

- **Data:** 07/11/2026
- **Integrante:** Thamiris de Oliveira e Silva
- **Ferramenta:** ChatGPT (GPT-6)
- **Prompt (resumo):** Solicitação para desenvolver um avaliador automático reutilizando a implementação existente em `assistente.py`, especialmente a função `responder()`, sem duplicar a lógica de geração, validação de SQL e execução somente leitura.
- **Resposta (resumo):** A IA propôs e auxiliou na implementação de `eval/avaliar.py`, que carrega as perguntas JSONL, confere as consultas de referência, executa o assistente completo e o baseline e registra resultados em CSV e JSON. Foram incluídas métricas de acurácia, situação das consultas, tempos, tokens e custo estimado. Também foi adicionada a montagem de volume `./eval:/app/eval` ao serviço `app` no Docker Compose, permitindo executar o avaliador no container e preservar os arquivos no computador.
- **Decisão:** aceito, com revisão e correção posterior.
- **Motivo e revisão:** A implementação foi exercitada primeiro com duas perguntas e depois com as 50. A equipe verificou o acesso aos arquivos dentro do container e conferiu que as referências eram executadas antes da chamada ao modelo. A primeira versão do avaliador apresentou uma comparação excessivamente rígida de precisão decimal e ordenação, problema documentado e corrigido na interação 016.

---

## 015 · Definição e execução do baseline sem esquema dinâmico (Marco 3)

- **Data:** 07/11/2026
- **Integrante:** Thamiris de Oliveira e Silva
- **Ferramenta:** ChatGPT (GPT-6)
- **Prompt (resumo):** Solicitação de uma condição baseline para comparar o assistente completo com uma versão que utiliza o mesmo modelo e as mesmas instruções fixas, mas não recebe o esquema dinâmico do PostgreSQL.
- **Resposta (resumo):** A IA propôs utilizar o mesmo Qwen2.5-Coder:3b nas duas condições. No baseline, o esquema dinâmico é enviado vazio, mas continuam ativos o validador SQL, a verificação de custo com `EXPLAIN`, o limite de linhas e a conexão com o usuário de leitura. Na primeira avaliação completa, o baseline teve zero acertos e 50 consultas bloqueadas. Os motivos individuais dos bloqueios ficaram registrados nos arquivos CSV e devem ser analisados caso a caso, sem presumir uma causa única para todos os resultados.
- **Decisão:** aceito.
- **Motivo e revisão:** A comparação mantém os mecanismos de segurança nas duas condições e procura avaliar a contribuição do esquema dinâmico. O grupo decidiu preservar os bloqueios como resultados observados, sem corrigir manualmente os SQLs do baseline. A limitação é registrada: trata-se de um baseline simples, sem contexto do esquema, e o resultado não deve ser generalizado para todo modelo ou configuração sem esquema.

---

## 016 · Correção dos critérios de comparação dos resultados (Marco 3)

- **Data:** 07/11/2026
- **Integrante:** Thamiris de Oliveira e Silva
- **Ferramenta:** ChatGPT (GPT-6)
- **Prompt (resumo):** Solicitação para investigar respostas classificadas como incorretas mesmo quando apresentavam valores numericamente equivalentes, ou os mesmos registros em ordem diferente, e corrigir o avaliador sem executar novamente o modelo.
- **Resposta (resumo):** A IA identificou que a primeira comparação exigia igualdade estrita entre valores e ordem das linhas. Propôs utilizar `Decimal` com arredondamento a duas casas decimais para comparações numéricas e permitir ignorar a ordem das linhas quando a pergunta não solicita ranking. Para rankings, foi criado o atributo `comparar_ordem`, marcado como verdadeiro nas questões Q028, Q030, Q032, Q035 e Q042. Também foi implementada a reavaliação de CSV histórico, sem chamadas adicionais ao Ollama.
- **Decisão:** aceito, após revisão.
- **Motivo e revisão:** A equipe identificou quatro falsos negativos na primeira avaliação: Q008, Q014, Q022 e Q038. Com os novos critérios, a reavaliação histórica passou de 27/50 (54%) para 31/50 (62%) acertos no assistente completo. O CSV original foi preservado e um novo CSV e JSON foram gerados. A comparação continua exigindo igualdade dos valores e da quantidade de linhas; somente a precisão decimal e a ordem, quando não significativa, receberam tratamento específico.

---

## 017 · Execução da avaliação experimental completa (Marco 3)

- **Data:** 07/11/2026
- **Integrante:** Thamiris de Oliveira e Silva
- **Ferramenta:** ChatGPT (GPT-6)
- **Prompt (resumo):** Solicitação de orientação para executar a avaliação completa com as 50 perguntas, comparando o assistente com esquema dinâmico e o baseline, utilizando os resultados de referência previamente conferidos.
- **Resposta (resumo):** A IA orientou a execução das duas condições experimentais com o mesmo modelo local Qwen2.5-Coder:3b. Todas as 50 consultas de referência foram executadas e conferidas pelo avaliador antes da geração. Na avaliação original, o assistente completo obteve 27/50 acertos (54%) e o baseline 0/50. Após a correção dos critérios de comparação descrita na interação 016, a avaliação histórica passou a registrar 31/50 acertos (62%) para o assistente completo e 0/50 para o baseline.
- **Decisão:** aceito como resultado experimental da primeira rodada.
- **Motivo e revisão:** Os arquivos CSV e JSON originais foram preservados, assim como os arquivos gerados na reavaliação histórica. A correção dos critérios de comparação não exigiu novas chamadas ao modelo. O grupo decidiu manter os resultados como evidência da primeira rodada, sem ajustar o prompt durante a avaliação e sem substituir os resultados originais pelos reavaliados.

---

## 018 · Análise e classificação das falhas da avaliação experimental (Marco 3)

- **Data:** 07/11/2026
- **Integrante:** Thamiris de Oliveira e Silva
- **Ferramenta:** ChatGPT (GPT-6)
- **Prompt (resumo):** Solicitação de análise dos 19 erros restantes do assistente completo após a reavaliação histórica, utilizando os SQLs gerados, resultados obtidos e mensagens de erro registrados no CSV.
- **Resposta (resumo):** A IA classificou os 19 resultados incorretos em três grupos principais: consultas executadas com resultado diferente do esperado, consultas bloqueadas pelo validador ou pelo banco e consultas interrompidas por timeout. Foram identificados problemas de interpretação da pergunta, agregações incorretas, joins inadequados, referências a colunas inexistentes e uso incorreto de aliases. Foi produzido `eval/analise_erros.md` com os resultados, exemplos e causas observadas.
- **Decisão:** aceito como diagnóstico da primeira rodada, com necessidade de revisão técnica pelo grupo.
- **Motivo e revisão:** A análise preserva os erros reais e distingue consultas executadas incorretamente de consultas bloqueadas ou interrompidas. O grupo decidiu não corrigir manualmente as respostas e não ajustar o prompt antes de documentar os resultados. As causas classificadas a partir dos SQLs e mensagens de erro devem ser tratadas como diagnóstico dos casos observados, não como prova de causa raiz para todos os problemas. O documento foi salvo em `eval/analise_erros.md`.

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
