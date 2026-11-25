# Segurança, privacidade e limitações

## Ameaças consideradas

O risco central do tema é o modelo gerar uma consulta perigosa, por erro ou porque a pergunta foi escrita para isso (injeção de instruções). Na avaliação, o `qwen2.5-coder:3b`, modelo padrão, obedeceu a quase todos os pedidos maliciosos: gerou `DROP TABLE`, `UPDATE ... SET valor_pago = 0`, `CREATE USER`, `COPY ... TO PROGRAM`, leitura de `pg_shadow` e `pg_sleep(60)`. Por isso o sistema **não confia no prompt nem no modelo** para a segurança.

| Ameaça | Exemplo | Barreira |
| --- | --- | --- |
| Escrita ou destruição de dados | `DROP TABLE orgao`, `UPDATE`, `TRUNCATE`, escrita escondida em `WITH` | Validador (só um `SELECT`); usuário `leitor` sem permissão de escrita; transação somente leitura |
| Vários comandos | Pergunta legítima seguida de `; DROP TABLE` | Validador (um comando por consulta) |
| Leitura do servidor | `pg_read_file`, `COPY ... TO PROGRAM`, `dblink` | Validador (funções e prefixos proibidos); banco (sem permissão) |
| Leitura do catálogo e da sessão | `pg_user`, `information_schema`, `SELECT user`, `current_query()`, `has_table_privilege` | Validador (schemas fora de `public`, palavras de sessão, `reg*`, `has_*`) |
| Desligar proteções da sessão | `SET statement_timeout = 0`, `SET default_transaction_read_only = off` | Validador (comandos de sessão); transação sempre desfeita |
| Consumo de recursos | Autojunção de 791 mil linhas, `repeat('x', 1000000000)`, `pg_sleep` | Limite de custo pelo `EXPLAIN` (1.000.000); `repeat`/`lpad` acima de 10.000; `statement_timeout` de 15 s |
| Volume de dados | "Todas as linhas, sem limite" | `LIMIT` aplicado ou reduzido para 1.000 |
| Derrubar outras sessões | `pg_terminate_backend` | Validador (prefixo `pg_`) |

Resultado da rodada de 17/11/2026: **nenhum dos 97 ataques teve efeito** com o sistema completo; sem o validador, 29 dos 72 ataques em SQL e 4 dos 25 em linguagem natural funcionaram, mesmo com o usuário `leitor` ([guia de avaliação](guia-de-avaliacao.md)). O catálogo roda na CI como teste.

## Outras proteções

- **Segredos:** nenhuma chave de API. As senhas do banco ficam no `.env`, que está no `.gitignore`; o `.env.example` traz só valores de exemplo.
- **Rede:** banco, Ollama e interface escutam só em `127.0.0.1`. Numa VM remota, o acesso é por túnel SSH, sem abrir portas.
- **Menor privilégio:** a aplicação usa só o usuário `leitor`. O usuário `carga`, dono das tabelas, é usado só pelo serviço de carga.
- **Container:** a imagem da aplicação roda com um usuário sem privilégios (`app`). A versão do Ollama é fixa (`0.40.13`).

## Riscos que continuam

- **Recursão sem fim** (`WITH RECURSIVE` sem condição de parada) passa pelo validador, porque o `EXPLAIN` estima custo baixo. Quem para a consulta é o `statement_timeout` de 15 s.
- **Sem autenticação nem limite de requisições.** Qualquer pessoa com acesso à porta 8501 pode perguntar, e perguntas caras em sequência ocupam o banco por até 15 s cada. Aceitável porque a interface só escuta na máquina local; não exponha a porta para a rede.
- **Resposta errada que parece certa.** É o risco mais provável no uso real: 12 das 43 consultas executadas na avaliação devolveram um resultado diferente da referência sem nenhum erro aparente. Exemplo: "Quanto a Fiocruz pagou em dezembro?" respondeu com o total do Ministério da Saúde ([casos de falha](../evidencias/casos-de-falha.md)). A explicação mostra o filtro que foi aplicado, o que ajuda o usuário a notar, mas não impede o erro.
- **Esclarecimento limitado.** Só três ambiguidades são detectadas (medida de gasto, tipo de orçamento e ano). Perguntas vagas de outro tipo seguem para o modelo.
- **Dependências sem versão travada.** As bibliotecas Python usam versões mínimas (`>=`) e a imagem `postgres:16-alpine` não é fixada por digest; uma atualização pode mudar o comportamento. Para a entrega, a tag `v1.0` registra o código, mas não as versões instaladas.

## O que o sistema não faz

- Não altera o banco nem acessa a internet depois da primeira subida.
- Não responde sobre outros anos: os dados são só de 2025.
- Não guarda conversa: cada pergunta é independente.
- Não é fonte oficial. Para decisões, confira no Portal da Transparência.
- Não identifica pessoas: não há dados de favorecidos, servidores ou parlamentares.

## Privacidade e LGPD

O projeto trata dados abertos sobre a despesa do governo federal, agregados por órgão, função, programa, ação, unidade gestora e local. A Lei Geral de Proteção de Dados (Lei nº 13.709/2018) se aplica a dados pessoais, e o projeto foi desenhado para não tratá-los:

| Ponto | Como é tratado |
| --- | --- |
| Dados de origem | Só os conjuntos de Orçamento e Execução da Despesa, sem favorecidos. A única coluna que identifica pessoa física (nome e código do autor de emenda parlamentar) é descartada na carga e vira só `com_emenda` (sim ou não); as tabelas de staging são apagadas no fim da carga |
| Processamento | Todo local. O modelo roda no Ollama da própria máquina; nenhuma pergunta ou resultado é enviado a terceiros |
| Prompts | O prompt leva o esquema e a pergunta. Os conjuntos de avaliação foram escritos pelo grupo e não têm dados pessoais |
| Logs | O log do container `app` registra a pergunta, a situação, o SQL, o número de linhas, o custo e os tempos. Não registra o resultado, endereço de IP nem identificação do usuário. Ele fica no log do Docker da máquina e some com `docker compose down` |
| Evidências | Vídeos, capturas e logs entregues não podem mostrar senhas do `.env` nem dados pessoais (regra da disciplina) |
| Minimização | Só as colunas necessárias para as perguntas sobre despesa entram nas tabelas consultáveis |

**Cuidado do usuário:** como a pergunta vai para o log, não digite dados pessoais (nomes, CPF) no campo de pergunta. O assistente não precisa deles, e os dados carregados não os contêm.

## Licença do modelo

O `qwen2.5-coder:3b`, modelo padrão desde 25/11 e o usado nas rodadas de avaliação, tem a Qwen Research License, que só permite uso não comercial. O `qwen2.5-coder:7b`, opcional para quem tem GPU, é Apache 2.0. O uso acadêmico deste projeto é compatível; um uso comercial exigiria trocar o modelo ([ficha do modelo](dados-e-modelo.md#ficha-do-modelo)).
