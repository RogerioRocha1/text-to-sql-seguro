# Decisões de dados

## Órgãos sem código na execução da despesa (proposta)

**Situação.** Ao varrer os 13 arquivos do Portal da Transparência (o orçamento anual e os 12 arquivos mensais de execução), encontramos lançamentos de execução sem órgão informado. Conferindo no banco depois da carga:

- **Código `-1` ("Sem informação"):** 1.985 linhas em junho e 1.428 em dezembro, ligadas à unidade gestora `-9`. Empenhado, liquidado e pago são zero. Só há valores de restos a pagar: R$ 156,1 milhões em restos a pagar pagos em junho e R$ 152,9 milhões em dezembro (cerca de R$ 309 milhões no total), além de valores inscritos positivos e negativos.
- **Código `-3`:** presente em 10 meses (todos, exceto junho e dezembro), com cerca de 535 linhas por mês e sem nome de órgão. Só há valores de restos a pagar inscritos, positivos e negativos.

**Alternativas consideradas.**

1. *Descartar as linhas.* Seria simples, mas os totais de restos a pagar do banco deixariam de bater com os arquivos do Portal (perderíamos cerca de R$ 309 milhões em restos a pagar pagos).
2. *Deixar o órgão vazio (NULL).* Quebraria a ligação com a tabela `orgao` (chave estrangeira) e faria essas linhas sumirem em qualquer `JOIN`.
3. *Normalizar para "Sem informação" (escolhida).* Onde o código ou o nome do órgão vem vazio, a carga preenche o código `-1` e o nome "Sem informação". O órgão `-3` mantém o código e ganha o nome "Sem informação". Nenhum valor é perdido e as linhas continuam ligadas à tabela `orgao`.

**Decisão proposta.** Adotar a alternativa 3. A normalização é feita na carga (`TRANSFORMAR`, em `esquema.py`).

**Consequências.**

- Os totais do banco continuam batendo com os arquivos originais (na interação 004 a soma foi conferida ao centavo).
- Consultas agrupadas por órgão vão mostrar linhas "Sem informação". Isso não é erro, e o assistente deve tratá-la como categoria normal.
- Como essas linhas só têm valores de restos a pagar, perguntas sobre valor pago ou empenhado por órgão não são afetadas por elas. Perguntas sobre restos a pagar são.
- O comentário da coluna `orgao.codigo` já avisa que códigos negativos indicam órgão não informado.

**Pendente de confirmação do grupo.** Aprovar ou ajustar a decisão. Se aprovada, registrar o resultado na interação 003 do `PROMPTS.md`.