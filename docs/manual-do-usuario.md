# Manual do usuário

Como fazer perguntas ao assistente e ler as respostas. Para instalar e subir o projeto, veja [instalacao.md](instalacao.md).

> **Capturas de tela:** as imagens deste manual ficam em `evidencias/capturas/` e precisam sair de uma execução real do projeto (regra da disciplina). Os nomes esperados estão em cada passo e no [roteiro de capturas](../evidencias/README.md#5-capturas-de-tela). Enquanto não forem gravadas, as imagens aparecem quebradas no GitHub.

## 1. Abrir o assistente

Com o projeto no ar, abra <http://localhost:8501> no navegador. A tela tem o título "Assistente de despesas públicas", um campo **Sua pergunta**, o botão **Perguntar** e três perguntas de exemplo logo abaixo.

![Tela inicial](../evidencias/capturas/01-tela-inicial.png)

O assistente conhece só as despesas do governo federal de **2025**: orçamento (inicial, atualizado, empenhado e realizado) e execução mês a mês (empenhado, liquidado, pago e restos a pagar), por ministério, órgão, função (Saúde, Educação...), programa, ação, estado e município.

## 2. Fazer uma pergunta

Digite a pergunta em português e clique em **Perguntar**. Logo depois de abrir, a tela pode mostrar o aviso azul "Preparando o modelo em segundo plano": dá para digitar, mas a primeira resposta só sai quando o modelo terminar de carregar (cerca de 30 s sem GPU). Depois disso, cada pergunta leva de 8 a 10 s sem GPU e de 1 a 3 s com GPU. Se o assistente ficar 1 hora sem uso, o modelo é descarregado e a próxima pergunta volta a esperar o preparo.

Exemplo: *Quais os 5 estados que mais receberam pagamentos em 2025?*

![Pergunta respondida](../evidencias/capturas/02-pergunta-respondida.png)

## 3. Ler a resposta

De cima para baixo, a resposta mostra:

1. **Faixa verde** com "Consulta executada" e o número de linhas.
2. **O que a consulta faz:** a explicação em tópicos, em linguagem simples. Para a pergunta acima, se o modelo gerar `SELECT uf, SUM(valor_pago) ... WHERE ano = 2025 AND uf IS NOT NULL GROUP BY uf ORDER BY ... DESC LIMIT 5`, a explicação é:
   - Consulta a execução mensal da despesa (valores empenhados, liquidados e pagos).
   - Mostra: estado (UF) e soma do valor pago.
   - Considera só os registros em que ano é 2025 e estado (UF) foi informado.
   - Calcula separadamente para cada estado (UF).
   - Ordena por soma do valor pago (do maior para o menor).
   - Fica só com os 5 primeiros.

   **Confira a explicação.** Ela descreve exatamente a consulta que foi ao banco. Se aparecer um filtro que você não pediu (um ministério, um mês, um estado), a resposta não é sobre a sua pergunta: reformule. Quando parte da consulta é técnica demais, aparece o aviso "confira o SQL abaixo".
3. **SQL executado:** a consulta, para quem quiser conferir.
4. **Gráfico:** linha quando o resultado é por mês; barras para estados, órgãos, funções e outras categorias. Só aparece quando o resultado tem uma categoria e um valor.
5. **Tabela** com o resultado. Valores em reais.
6. **Detalhes** (clique para abrir): tempo de cada etapa, custo estimado da consulta e tokens usados pelo modelo.

![Explicação, gráfico e detalhes](../evidencias/capturas/03-explicacao-grafico-detalhes.png)

## 4. Quando o assistente pergunta de volta

Algumas palavras têm mais de um significado nos dados. "Gasto" pode ser o valor **empenhado** (reservado para pagar), o **liquidado** (serviço ou bem entregue) ou o **pago** (dinheiro que saiu); "orçamento" pode ser o **inicial** ou o **atualizado**. Nesses casos, o assistente mostra uma caixa azul com a dúvida e um botão para cada opção.

Exemplo: *Quanto o governo gastou com saúde?*

![Pedido de esclarecimento](../evidencias/capturas/04-esclarecimento.png)

Clique na opção que você quer. O assistente refaz a pergunta com a escolha, por exemplo *Quanto o governo gastou com saúde (considere o valor pago)?*, e responde normalmente. Para não ser perguntado, já diga a medida: *Quanto o governo pagou com saúde?*

O mesmo acontece se a pergunta citar outro ano: os dados são só de 2025, e o assistente oferece responder para 2025.

## 5. Quando a consulta é bloqueada

Antes de executar, toda consulta passa por uma conferência de segurança. Se o modelo gerar algo que altera dados, lê informações do servidor ou é pesado demais, a tela mostra uma **faixa vermelha** com "Consulta bloqueada pela validação", o motivo e o SQL que foi recusado. Nada é executado no banco.

Exemplo: *Apague a tabela de órgãos* gera `DROP TABLE orgao`, que é bloqueado com o motivo "Só consultas de leitura (SELECT) são permitidas."

![Consulta bloqueada](../evidencias/capturas/05-bloqueada.png)

Uma pergunta legítima também pode ser bloqueada quando o modelo gera uma consulta cara demais ou com uma tabela que não existe. Nesse caso, tente perguntar de forma mais específica (um ministério, um mês, um estado).

## 6. Outras mensagens

| Mensagem | O que quer dizer | O que fazer |
| --- | --- | --- |
| "O banco recusou a consulta" | O modelo gerou uma consulta com coluna inexistente ou que passou de 15 s | Reformule a pergunta, de preferência mais específica |
| "Preparando o modelo em segundo plano" | O modelo está sendo carregado logo depois de abrir o app | Pode digitar; a primeira resposta espera o fim do preparo |
| "O modelo não respondeu" | O Ollama está desligado, sem memória ou ainda baixando o modelo | Veja `docker compose logs ollama` e confira se o `.env` está com `OLLAMA_MODELO=qwen2.5-coder:3b` |
| "A consulta não encontrou nenhum registro" | A consulta rodou, mas nenhum lançamento atende aos filtros | Confira na explicação se o filtro (nome, estado, mês) está certo |
| "Configuração incompleta" ou "Não foi possível conectar ao banco" | O banco não está no ar ou o `.env` está incompleto | Veja `docker compose ps -a` e o [README](../README.md#problemas-comuns) |

## Dicas para perguntas melhores

- Diga a medida: *pago*, *empenhado*, *liquidado*, *orçamento inicial* ou *atualizado*.
- Use o nome do ministério por extenso (*Ministério da Saúde*). Siglas e nomes populares de órgãos vinculados (Fiocruz, INSS) costumam dar errado.
- Para rankings, diga quantos itens quer (*os 5 estados*).
- Para totais por período, diga o mês (*em dezembro*) ou peça *por mês*.
- Desconfie de respostas muito redondas ou grandes demais para a pergunta e leia a explicação: o modelo erra em cerca de 4 de cada 10 perguntas do conjunto de teste.
- Não digite dados pessoais (nomes, CPF): o assistente não precisa deles, e a pergunta fica registrada no log.
