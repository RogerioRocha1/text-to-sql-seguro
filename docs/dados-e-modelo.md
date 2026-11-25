# Dados e modelo

## Origem e licença dos dados

| Item | Valor |
| --- | --- |
| Publicador | Controladoria-Geral da União (CGU), Portal da Transparência do Governo Federal |
| Conjuntos | Orçamento da Despesa (anual) e Execução da Despesa (mensal) |
| Período | Exercício de 2025: orçamento anual e execução de janeiro a dezembro |
| Endereço de download | `https://portaldatransparencia.gov.br/download-de-dados/orcamento-despesa/2025` e `.../despesas-execucao/202501` a `.../despesas-execucao/202512` ([`fontes.py`](../src/assistente_sql/fontes.py)) |
| Formato | ZIP com CSV separado por `;`, codificação Windows-1252, números com vírgula decimal |
| Licença | Dados abertos do governo federal. A página de download não declara uma licença específica e remete aos Termos de Uso do Portal. O grupo cita a fonte no README e não redistribui os arquivos: eles são baixados pela carga e ficam em `data/raw/`, fora do Git |
| Pessoas físicas | Os dois conjuntos descrevem a despesa por órgão, função, programa e ação. A única coluna que identifica pessoa (nome e código do autor de emenda parlamentar) é descartada na carga |

## Tratamento

A carga ([`carga.py`](../src/assistente_sql/carga.py)) roda numa única transação e é idempotente: recria as tabelas a cada execução.

1. **Download:** os 13 ZIPs vão para `data/raw/`. Um arquivo que já existe não é baixado de novo, então a carga é reproduzível com a mesma foto dos dados.
2. **Conferência do layout:** o cabeçalho de cada CSV é comparado com a lista esperada em `fontes.py`. Se a CGU mudar uma coluna, a carga falha em vez de gravar colunas trocadas.
3. **Staging:** os CSVs entram como texto no schema `carga`, que o usuário `leitor` não enxerga. As tabelas de staging são apagadas no fim da carga.
4. **Transformação** ([`esquema.py`](../src/assistente_sql/esquema.py)): números com vírgula viram `numeric(18,2)`; textos vazios viram `NULL`; o autor de emenda vira só a coluna booleana `com_emenda`; órgãos sem código viram "Sem informação" ([decisoes-de-dados.md](decisoes-de-dados.md)); as dimensões (órgão, função, subfunção, programa e ação) são separadas em tabelas ligadas por chaves estrangeiras.
5. **Comentários:** cada tabela e coluna recebe um `COMMENT` em português. Esses comentários são lidos pelo gerador e vão no prompt do modelo.

## Ficha do conjunto de dados

| Tabela | Linhas | Principais colunas |
| --- | ---: | --- |
| `orgao` | 268 | `codigo`, `nome`, `codigo_orgao_superior`, `nome_orgao_superior` (ministério ou poder) |
| `funcao` | 29 | `codigo`, `nome` (ex.: Saúde, Educação) |
| `subfuncao` | 102 | `codigo`, `nome` |
| `programa_acao` | 2.437 | `codigo_programa`, `nome_programa`, `codigo_acao`, `nome_acao` |
| `orcamento` | 26.160 | `codigo_orgao`, unidade orçamentária, função, subfunção, programa, ação, `categoria_economica`, `grupo_despesa`, `elemento_despesa`, `valor_inicial`, `valor_atualizado`, `valor_empenhado`, `valor_realizado` |
| `execucao_mensal` | 791.013 | `mes`, `codigo_orgao`, unidade gestora, função, subfunção, programa, ação, `uf`, `municipio`, categoria, grupo, elemento e modalidade de despesa, `com_emenda`, `valor_empenhado`, `valor_liquidado`, `valor_pago`, restos a pagar inscritos, cancelados e pagos |

- **Uso pretendido:** consultas agregadas sobre o orçamento e a execução da despesa federal de 2025, para fins de estudo.
- **Não serve para:** outros anos (a carga só tem 2025), despesa por favorecido ou por documento (os conjuntos usados não têm esses níveis), nem para conclusões oficiais: o Portal é a fonte de referência.
- **Particularidades conhecidas:** a execução é por unidade gestora e mês, com `uf` e `municipio` vazios em parte das linhas; restos a pagar inscritos podem ser negativos; há lançamentos com órgão "Sem informação" que só têm restos a pagar.
- **Atualização:** a foto usada na avaliação foi baixada entre o fim de outubro e o início de novembro de 2026 (carga do Marco 2). Se o Portal atualizar algum arquivo, quem baixar depois pode obter números diferentes dos resultados esperados de `eval/perguntas.jsonl`. O registro do hash SHA-256 dos ZIPs, previsto na proposta, ainda não foi implementado. Para outra data ou ano, rode a carga de novo (`--ano`) e refaça a calibração do custo e a avaliação.

## Conjuntos de avaliação

| Arquivo | Itens | Uso |
| --- | ---: | --- |
| [`eval/perguntas.jsonl`](../eval/perguntas.jsonl) | 50 (Q001–Q050) | Teste: só medir. 9 fáceis, 29 intermediárias, 12 difíceis, em 11 categorias (orçamento, execução, emendas, localização, restos a pagar...). Cada item tem pergunta, SQL de referência e resultado esperado conferido no banco |
| [`eval/perguntas_dev.jsonl`](../eval/perguntas_dev.jsonl) | 10 (D01–D10) | Desenvolvimento: ajustar prompt e regras. Busca de órgão por nome e sigla, função e localização |
| [`eval/ataques.jsonl`](../eval/ataques.jsonl) | 97 | Segurança: 72 ataques em SQL e 25 em linguagem natural, cada um com a barreira esperada (validador, custo ou banco) |
| `eval/perguntas_ambiguas.jsonl` | pendente | Cobertura do pedido de esclarecimento; deve ser escrito por quem não leu as regras ([guia de avaliação](guia-de-avaliacao.md)) |

As perguntas foram escritas pelo grupo, sobre dados públicos, e não contêm dados pessoais.

## Ficha do modelo

| Item | Valor |
| --- | --- |
| Modelo | Qwen2.5-Coder, versão instruída, distribuída pelo Ollama: `qwen2.5-coder:3b` (padrão desde 25/11 e o usado nas rodadas de avaliação de 07/11 e 17/11) e `qwen2.5-coder:7b` (opcional, para GPU NVIDIA de 6 GB ou mais; não avaliado no conjunto de teste) |
| Desenvolvedor | Equipe Qwen, Alibaba Cloud. Relatório técnico: Hui et al., *Qwen2.5-Coder Technical Report*, arXiv:2409.12186, 2024 |
| Licença | **3B, o padrão: Qwen Research License, só para uso não comercial (pesquisa ou avaliação).** 7B: Apache 2.0. O uso neste projeto acadêmico é compatível com as duas; quem quiser usar o sistema comercialmente deve trocar o 3B pelo 7B ou por outro modelo com licença permissiva |
| Tamanho | 3B: cerca de 1,9 GB em disco e 2,2 GB de memória carregado; 7B: 4,7 GB em disco e 5,5 GB de memória (quantização padrão do Ollama) |
| Servidor | Ollama 0.40.13 em container (`ollama/ollama:0.40.13`), API local em `127.0.0.1:11434` |
| Parâmetros | Temperatura 0, contexto de 4.096 tokens (`OLLAMA_CONTEXTO`), no máximo 512 tokens na resposta, modelo mantido carregado por 1 h (`OLLAMA_KEEP_ALIVE`), uma nova tentativa quando o Ollama aborta por repetição e tempo máximo de 300 s por chamada ([`gerador.py`](../src/assistente_sql/gerador.py)). As rodadas de 07/11 e 17/11 usaram contexto de 8.192, sem limite de tokens e sem nova tentativa |
| Entrada | Instruções fixas (`gerador.INSTRUCOES`), esquema lido do banco como `CREATE TABLE` comentado e a pergunta do usuário |
| Saída esperada | Um bloco `sql` com uma consulta PostgreSQL; o texto fora do bloco é ignorado |
| Treinamento pelo grupo | Nenhum. O modelo é usado como veio; não há ajuste fino nem envio de dados para fora da máquina |
| Desempenho medido | 31/50 (62%) de acurácia por execução no conjunto de teste com o 3B (07/11); 4/10 no conjunto de desenvolvimento (17/11); mediana de 14,0 s por pergunta na rodada de 07/11. Depois das otimizações de 25/11, com o modelo aquecido: cerca de 8 a 10 s por pergunta numa CPU de 4 núcleos e 1 a 3 s numa RTX 3050 ([guia de avaliação](guia-de-avaliacao.md), [eval/README.md](../eval/README.md#desempenho-e-escolha-do-modelo-25112026)) |
| Limitações observadas | O 3B às vezes entra em laço de repetição, tratado com uma nova tentativa. Confunde órgão vinculado e ministério, erra siglas (Fiocruz, INSS), esquece `SUM`, junta tabelas de fatos e inventa colunas ([`eval/analise_erros.md`](../eval/analise_erros.md)). Obedece a pedidos maliciosos: gerou `DROP TABLE`, `CREATE USER` e `COPY ... TO PROGRAM` quando pedido. Por isso a segurança não depende do modelo |
| Papel no sistema | Só gera SQL. A explicação e o pedido de esclarecimento não usam o modelo ([DA-04 e DA-05](decisoes-de-arquitetura.md)) |
