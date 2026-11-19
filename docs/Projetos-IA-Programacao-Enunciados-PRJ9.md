# Projetos de IA na Programação: Enunciados, Calendário e Rubrica

Versão de 09/10/2026

## Visão geral

Cada grupo de 4 alunos escolhe um dos 16 temas e entrega, entre 30/11 e 02/12, um software funcional, com evidências verificáveis de funcionamento, que usa IA como componente do produto, construído com apoio de assistentes de código e avaliado com métricas, acompanhado de um trabalho de pesquisa em padrão ABNT e de uma documentação técnica.

- **Objetivo de aprendizagem:** projetar, construir e avaliar sistemas com IA com práticas reais de engenharia: testes, integração contínua, containers, métricas e análise crítica das limitações.
- **Formato:** grupos de 4 pessoas, um repositório Git por grupo e um tema por grupo, sem repetição enquanto houver temas livres.
- **Escolha do tema:** na aula de 17/10 cada grupo indica 3 opções em ordem de preferência, e o professor faz a atribuição.
- **Stack comum sugerida:** Python, FastAPI, Streamlit ou React, Git, Docker e Ollama para rodar modelos abertos localmente. Todo o projeto deve rodar a custo zero, conforme as regras de uso de IA. Cada tema indica ferramentas específicas.

Os papéis abaixo indicam quem lidera cada frente. Todos os integrantes escrevem código e precisam saber explicar qualquer parte do projeto.

| Papel | Lidera |
| --- | --- |
| Dados e Qualidade | Datasets, anotação, testes automatizados e integração contínua |
| Backend e Infraestrutura | APIs, containers, deploy e observabilidade |
| IA e Avaliação | Prompts, modelos, agentes, métricas e experimentos |
| Produto e Interface | Interface, documentação, vídeo da demo e coordenação das duas documentações |

## Calendário

As aulas vão de 17/10 a 28/11, quatro marcos de acompanhamento caem nos sábados de 24/10 a 21/11, e o envio final acontece de 30/11 a 02/12.

Linha do tempo: período de aulas de 17/10 a 28/11; marcos em 24/10, 07/11, 14/11 e 21/11; último dia de aula em 28/11; janela de envio final de 30/11 a 02/12.

O que cada marco exige:

1. **Aula inicial, 17/10:** formação dos grupos, apresentação dos temas e indicação de 3 preferências por grupo.
2. **Marco 1, 24/10:** proposta técnica de 1 a 2 páginas (problema, arquitetura, métricas de sucesso e plano), repositório criado e integração contínua mínima rodando um teste.
3. **Marco 2, 07/11:** protótipo ponta a ponta, ainda simples, com testes e Docker.
4. **Marco 3, 14/11:** MVP completo do tema, protocolo de avaliação definido (dados de teste separados, métricas e baseline) e introdução, referencial teórico e metodologia do trabalho de pesquisa redigidos.
5. **Marco 4, 21/11:** avaliação experimental concluída, funcionalidades congeladas, documentação técnica completa, pasta de evidências montada e rascunho do trabalho de pesquisa.
6. **28/11:** demonstrações curtas em aula, com feedback do professor e dos colegas.
7. **30/11 a 02/12:** envio final, conforme a seção Repositório e itens de envio.

As datas dos marcos usam os sábados do período (17/10 e 28/11 são sábados). Se a turma se reúne em outro dia, cada marco pode ser movido para a data equivalente. O sábado 31/10 fica para acompanhamento, sem entrega, e a defesa oral individual será marcada pelo professor.

## Regras de uso de IA na programação

O uso de IA é incentivado e deve ser registrado: o grupo responde por todo o código entregue, independentemente de quem ou do que o escreveu.

- **Ferramentas:** assistentes de código e modelos que o grupo possa usar sem pagar, como planos gratuitos para estudantes (por exemplo, o do GitHub Copilot, conforme as condições vigentes) ou ferramentas de código aberto com modelos locais (por exemplo, Continue ou Aider com Ollama). O README declara quais foram usadas.
- **Registro em `PROMPTS.md`:** pelo menos 10 interações relevantes, cada uma com o prompt, um resumo da resposta e o que foi aceito, corrigido ou descartado, com o motivo.
- **Testes primeiro:** código gerado por IA só entra na branch principal com teste automatizado que passa na integração contínua.
- **Revisão cruzada:** nenhum integrante aprova o próprio pull request. Todo PR tem ao menos um revisor humano do grupo.
- **Segredos:** chaves de API ficam em variáveis de ambiente e o arquivo `.env` fica no `.gitignore`. Nenhuma chave no histórico do Git.
- **Dados e LGPD:** usar apenas dados abertos, públicos ou sintéticos. Nenhum dado pessoal real em datasets, prompts ou logs.
- **Custo:** custo zero. Nenhum integrante paga por API, hospedagem ou ferramenta. Use modelos abertos locais (Ollama, llama.cpp), camadas gratuitas, notebooks em nuvem gratuitos e software de código aberto. Quem usar uma camada gratuita documenta o limite de uso e garante que o projeto também funcione com um modelo local.
- **Licenças:** bibliotecas e códigos de terceiros são permitidos com a licença citada no README. Copiar um projeto pronto sem declarar é falta de integridade acadêmica.
- **Defesa oral individual:** cada integrante explica, sem consultar a IA, um trecho do código escolhido pelo professor. A data da defesa será definida pelo professor.

## Repositório e itens de envio

O envio final, entre 30/11 e 02/12, consiste no link de um repositório que qualquer pessoa consegue executar com um comando, mais as evidências de funcionamento, o trabalho de pesquisa em padrão ABNT, a documentação técnica e o registro de uso de IA.

Estrutura mínima do repositório:

```text
README.md             problema, arquitetura, como rodar, contribuição de cada integrante
PROMPTS.md            registro de uso de IA na programação
LICENSE
docker-compose.yml    sobe o projeto com um comando
.github/workflows/    integração contínua (testes e lint)
src/                  código da aplicação
tests/                testes automatizados
eval/                 scripts, dados e resultados da avaliação experimental
evidencias/           vídeo, logs, prints e índice das evidências de funcionamento
docs/                 documentação técnica em Markdown e trabalho de pesquisa em PDF
```

| Item de envio | Requisito |
| --- | --- |
| Link do repositório | Acesso público, ou privado com o professor como colaborador, enviado até 02/12 |
| Versão avaliada | Tag `v1.0` criada até 02/12, com commits de todos os integrantes. Commits posteriores não são considerados |
| Execução reproduzível | `docker compose up` sobe o projeto sem pagamento de nenhum serviço. O README lista as variáveis necessárias, sem as chaves |
| Evidências de funcionamento | Pasta `evidencias/` com vídeo, execução verde da integração contínua, resultados da avaliação e índice, conforme a seção Evidências de funcionamento |
| Trabalho de pesquisa (ABNT) | PDF em `docs/`, de 12 a 20 páginas textuais, conforme a seção Documentação a entregar |
| Documentação técnica | Pasta `docs/` em Markdown, com o conteúdo mínimo descrito na seção Documentação a entregar |
| `PROMPTS.md` | Pelo menos 10 interações registradas, conforme as regras de uso de IA |
| Canal de envio | A definir pelo professor (por exemplo, o AVA com o link do repositório) |

## Evidências de funcionamento

Além do link do repositório, cada grupo envia provas substanciais de que construiu o sistema e de que ele funciona, de modo que o professor consiga conferir cada afirmação do trabalho de pesquisa. As evidências ficam na pasta `evidencias/` do repositório, com um `README.md` que as indexa.

| # | Evidência | O que enviar | Como o professor confere | Obrigatória |
| --- | --- | --- | --- | --- |
| 1 | Execução gravada | Vídeo de 3 a 5 minutos, com a tela inteira visível, subindo o projeto do zero com `docker compose up` e percorrendo o fluxo principal | Assiste e compara com o código da tag `v1.0` | Sim |
| 2 | Integração contínua | Link da execução verde dos testes na tag `v1.0` e uma captura dela | Abre a execução no repositório | Sim |
| 3 | Resultados da avaliação | Tabelas, gráficos e saídas brutas (CSV ou JSON) geradas pelos scripts de `eval/`, com o comando que as regera | Reexecuta o comando e compara os números | Sim |
| 4 | Logs de uma execução completa | Trechos de logs com data e hora, mostrando entradas, decisões do sistema e saídas | Confere a coerência com o vídeo e com o código | Sim |
| 5 | Capturas de tela | Pelo menos 5 situações de uso diferentes, incluindo uma falha tratada pelo sistema | Compara com o vídeo e com a execução local | Não |
| 6 | Casos de falha | Pelo menos 3 casos em que o sistema errou, com a análise da causa | Lê a análise e testa o caso, se possível | Sim |
| 7 | Histórico do Git | Commits de todos os integrantes e pull requests revisados por outro membro | Consulta o histórico no repositório | Sim |
| 8 | Índice de evidências | `evidencias/README.md` ligando cada afirmação do trabalho de pesquisa à evidência que a comprova | Usa como roteiro de conferência | Sim |

- **Gerado pelo próprio sistema:** as evidências precisam sair da execução real do projeto. Capturas editadas, números inventados ou resultados copiados de outro lugar são fraude acadêmica.
- **Resultado ruim não reprova:** um experimento que não deu certo, bem documentado e analisado, vale mais do que um resultado bom sem comprovação.
- **Conferência ao vivo:** na defesa oral, o professor pode escolher uma evidência e pedir que o grupo a reproduza na hora.
- **Sem segredos:** vídeos, logs e capturas não podem mostrar chaves de API, senhas ou dados pessoais.

## Documentação a entregar

Cada grupo entrega dois documentos com finalidades diferentes: um trabalho de pesquisa em padrão ABNT, que apresenta e avalia o projeto como um estudo, e uma documentação técnica, que permite a outra pessoa instalar, usar e reproduzir o sistema.

| Aspecto | Trabalho de pesquisa (ABNT) | Documentação técnica |
| --- | --- | --- |
| Pergunta que responde | Por que o problema importa e com que evidência a solução funciona | Como instalar, usar, manter e reproduzir o sistema |
| Leitor | Professor e banca acadêmica | Desenvolvedor ou usuário que não conhece o projeto |
| Formato | PDF em padrão ABNT | Markdown na pasta `docs/` do repositório |
| Extensão | De 12 a 20 páginas textuais | O necessário para cumprir o conteúdo mínimo |
| Rascunhos | 14/11 (introdução, referencial teórico e metodologia) e 21/11 (completo) | 21/11 (completa) |

### Trabalho de pesquisa (padrão ABNT)

- **Normas:** formatação conforme a ABNT NBR 14724 (trabalhos acadêmicos), citações pela NBR 10520, referências pela NBR 6023, resumo pela NBR 6028, sumário pela NBR 6027 e numeração progressiva das seções pela NBR 6024. Vale a versão vigente de cada norma.
- **Formatação:** papel A4, fonte tamanho 12 (Times New Roman ou Arial), espaçamento de 1,5 entre linhas, margens de 3 cm (superior e esquerda) e 2 cm (inferior e direita), citações longas com recuo de 4 cm e fonte tamanho 10.
- **Estrutura:** elementos pré-textuais (capa, folha de rosto, resumo e abstract com palavras-chave, listas de figuras e de tabelas quando houver, sumário), elementos textuais (1 Introdução, 2 Referencial teórico, 3 Metodologia, 4 Resultados e discussão, 5 Considerações finais) e elementos pós-textuais (referências e apêndices).
- **O que cada capítulo cobre:** a introdução apresenta o problema, o objetivo e a justificativa. O referencial teórico resume o estado da arte do tema. A metodologia descreve a arquitetura, os dados, as métricas e o baseline. Os resultados apresentam a avaliação experimental com tabelas e gráficos. As considerações finais tratam de limitações, riscos éticos e trabalhos futuros.
- **Fontes:** no mínimo 8 referências, das quais pelo menos 4 são artigos científicos, documentação oficial ou normas. Blogs e páginas de empresas podem complementar, mas não substituem fontes primárias.
- **Uso de IA na escrita:** permitido para revisar e organizar o texto. Toda citação e toda referência precisam ser conferidas pelo grupo na fonte original. Referência inexistente ou inventada é falta grave.
- **Ferramentas gratuitas:** LibreOffice Writer ou Google Docs com modelo ABNT, ou LaTeX com a classe abnTeX2, e Zotero para gerenciar as referências.
- **Entrega:** arquivo PDF em `docs/pesquisa-abnt.pdf`.

### Documentação técnica

A documentação técnica fica na pasta `docs/` do repositório, em Markdown, e pode ser publicada sem custo com MkDocs e GitHub Pages, de forma opcional. Conteúdo mínimo:

1. **Visão geral e arquitetura:** diagrama de componentes (Mermaid ou imagem) e fluxo de dados.
2. **Instalação e execução:** pré-requisitos, variáveis de ambiente (sem as chaves) e o comando que sobe o projeto.
3. **Decisões de arquitetura:** de 3 a 5 registros curtos, cada um com contexto, decisão e alternativas descartadas.
4. **Referência da API ou da interface:** endpoints (a documentação OpenAPI do FastAPI serve) ou comandos disponíveis.
5. **Dados e modelos:** origem, licença, tratamento e uma ficha do modelo ou do conjunto de dados.
6. **Guia de avaliação:** como reproduzir os experimentos e as métricas com um comando.
7. **Testes e integração contínua:** o que é testado, como executar e qual a cobertura.
8. **Segurança, privacidade e limitações:** riscos conhecidos, o que o sistema não faz e o tratamento de dados conforme a LGPD.
9. **Manual do usuário:** passo a passo com capturas de tela.

Critério de qualidade: uma pessoa que não participou do projeto precisa conseguir instalar, executar e reproduzir os resultados usando apenas essa documentação.

## Rubrica de avaliação

A avaliação soma 100 pontos: os critérios 1 a 6 valem para o grupo e o critério 7 é individual. Cada tema traz, ao final, critérios específicos que detalham os critérios 2 e 3.

| # | Critério | Peso | Nível máximo | Nível insuficiente |
| --- | --- | --- | --- | --- |
| 1 | Problema, arquitetura e planejamento | 10 | Problema delimitado, métricas de sucesso definidas antes do código, arquitetura documentada e plano cumprido nos marcos | Problema vago, sem métricas, marcos não cumpridos |
| 2 | Funcionamento do MVP e do desafio do tema | 20 | Fluxo principal funciona de ponta a ponta, o desafio do tema é enfrentado, não contornado, e o funcionamento é comprovado por evidências verificáveis | Funciona apenas em exemplos escolhidos a dedo ou sem evidências que permitam conferir |
| 3 | Avaliação experimental | 20 | Conjunto de teste separado, comparação com um baseline simples, análise de erros e resultados reproduzíveis | Apenas demonstração visual, sem números |
| 4 | Qualidade de engenharia | 15 | Testes automatizados, integração contínua verde, Docker, tratamento de erros, cuidados de segurança e custo zero | Sem testes, sem CI, segredos expostos ou dependência de serviço pago |
| 5 | Uso crítico da IA | 10 | `PROMPTS.md` mostra decisões, correções e descartes; o grupo sabe explicar o que a IA errou | Registro genérico ou código gerado sem revisão |
| 6 | Documentação (pesquisa ABNT e técnica) e demonstração | 15 | Pesquisa conforme a ABNT, com referências verificáveis e limitações discutidas com honestidade; documentação técnica que permite instalar e reproduzir o sistema sem ajuda; vídeo mostrando o sistema funcionando | Pesquisa fora do padrão ou com referências inventadas; documentação que não permite rodar o sistema |
| 7 | Contribuição individual e defesa oral | 10 | Commits relevantes e explicação segura de um trecho do código sem consultar a IA | Poucos commits ou incapacidade de explicar o próprio trabalho |


## Tema 9. Assistente de dados com text-to-SQL seguro

O grupo constrói uma interface em linguagem natural para consultar um banco real, garantindo que as consultas geradas sejam corretas, seguras e explicadas ao usuário.

- **O que constroem:** um assistente que traduz perguntas em SQL sobre dados abertos (por exemplo, dados do governo), valida a consulta, executa e mostra tabela e gráfico.
- **Stack sugerida:** PostgreSQL ou DuckDB, SQLGlot, modelo aberto local (Ollama), Streamlit.
- **MVP até 14/11:** 50 perguntas de teste com as consultas de referência e a acurácia medida.
- **Desafio central:** validar o SQL antes de executar (somente leitura, limite de linhas e de custo estimado), explicar a consulta ao usuário e perguntar quando o esquema for ambíguo.
- **Critérios específicos (rubrica 2 e 3):**
  - Acurácia por execução: o resultado da consulta gerada precisa ser igual ao da consulta de referência.
  - Tentativas de comandos destrutivos e de injeção de SQL bloqueadas, com o catálogo dos casos testados.
  - Comparação com um baseline simples, por exemplo o mesmo modelo sem receber o esquema ou sem a etapa de validação.
  - Explicação das consultas em linguagem que um usuário não técnico entenda, avaliada em amostra.

