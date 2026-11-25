# Instalação e execução

Resumo para subir o projeto do zero. O passo a passo por sistema operacional (Windows com WSL2, Ubuntu, GPU NVIDIA) e a tabela de problemas comuns estão no [README](../README.md#instalação-e-execução-com-docker-marco-2).

## Pré-requisitos

| Item | Obrigatório? | Observação |
| --- | --- | --- |
| Docker com Compose (Docker Desktop no Windows, Docker Engine no Linux) | Sim | `docker version` precisa mostrar Client e Server |
| Git | Sim | Para clonar o repositório |
| Disco livre | Sim | Cerca de 12 GB com o modelo padrão (3B); cerca de 15 GB com o 7B |
| RAM livre para o Docker | Sim | 4 GB com o 3B (ocupa cerca de 2,2 GB carregado). O 7B (5,5 GB) só vale com GPU NVIDIA de 6 GB ou mais |
| Internet | Só na primeira vez | Imagens, cerca de 90 MB de dados do Portal e o modelo |
| Driver NVIDIA | Não | Acelera o modelo; no Linux também o NVIDIA Container Toolkit |
| Python 3.11+ | Não | Só para rodar os testes e a avaliação fora do Docker |

## Variáveis de ambiente

Copie `.env.example` para `.env` e troque as duas senhas. Nenhuma chave de API é necessária. O `.env` está no `.gitignore`.

| Variável | Padrão | Para quê |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | (obrigatória) | Senha do usuário `carga`, dono das tabelas |
| `POSTGRES_LEITOR_SENHA` | (obrigatória) | Senha do usuário `leitor`, o único que a aplicação usa |
| `POSTGRES_DB` | `despesas` | Nome do banco |
| `POSTGRES_USER` | `carga` | Usuário dono, usado só pela carga |
| `POSTGRES_LEITOR_USUARIO` | `leitor` | Usuário somente leitura |
| `POSTGRES_PORTA` | `5432` | Porta do banco em `127.0.0.1` |
| `OLLAMA_MODELO` | `qwen2.5-coder:3b` | Modelo usado para gerar o SQL. Um `.env` copiado antes de 25/11 vem com o 7B: confira |
| `OLLAMA_CONTEXTO` | `4096` | Tamanho do contexto do modelo, em tokens (o prompt com o esquema usa cerca de 1.650) |
| `OLLAMA_KEEP_ALIVE` | `1h` | Tempo que o modelo fica carregado sem uso |
| `OLLAMA_URL` | `http://localhost:11434` | Endereço do Ollama fora do Docker (CLI e avaliação locais) |
| `OLLAMA_PORTA` | `11434` | Porta do Ollama em `127.0.0.1` |
| `COMPOSE_FILE` | (comentada) | Ativa a GPU: `docker-compose.yml;docker-compose.gpu.yml` no Windows, `:` no Linux |
| `ANO_DADOS` | `2025` | Ano baixado pela carga |
| `APP_PORTA` | `8501` | Porta da interface |
| `LIMITE_LINHAS` | `1000` | `LIMIT` aplicado pelo validador |
| `CUSTO_MAXIMO` | `1000000` | Custo máximo estimado pelo `EXPLAIN` ([calibração](../eval/README.md#calibração-do-limite-de-custo-do-validador)) |
| `DATABASE_URL_LEITOR` | (montada pelo Compose) | Só fora do Docker: `postgresql://leitor:<senha>@127.0.0.1:5432/despesas` |

## Subir o projeto

```bash
git clone https://github.com/RogerioRocha1/text-to-sql-seguro.git
cd text-to-sql-seguro
cp .env.example .env            # troque POSTGRES_PASSWORD e POSTGRES_LEITOR_SENHA
mkdir -p data/raw               # PowerShell: mkdir data\raw
docker compose up -d
docker compose logs -f carga ollama-modelo   # primeira vez: 10 a 30 min; Ctrl+C para sair
```

Abra <http://localhost:8501>. Ao abrir, o app prepara o modelo em segundo plano (cerca de 30 s na CPU e 2 a 4 s com GPU). A tabela "Qual modelo usar" do [README](../README.md#1-instalar-as-dependências) traz os tempos medidos. Na primeira vez, o `docker compose up` baixa os dados e carrega o banco (só se estiver vazio) e baixa o modelo (só se não estiver no volume). Nas seguintes, sobe em segundos e sem internet.

## Conferir

```bash
docker compose ps -a                        # db, ollama e app "Up"; carga e ollama-modelo "Exited (0)"
curl http://localhost:8501/_stcore/health   # "ok"
docker compose exec db psql -U carga -d despesas -c "\dt+"   # as 6 tabelas
```

A carga termina com a contagem de linhas: `orgao` 268, `funcao` 29, `subfuncao` 102, `programa_acao` 2.437, `orcamento` 26.160 e `execucao_mensal` 791.013.

## Parar e apagar

- `docker compose stop`: para os containers e mantém banco e modelo.
- `docker compose down -v`: apaga tudo, inclusive banco e modelo. Os ZIPs em `data/raw/` ficam.
- Trocou a senha no `.env` depois da primeira subida? As senhas só são lidas na criação do volume: rode `docker compose down -v` e suba de novo.

## Ambiente de desenvolvimento (opcional)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -v
ruff check . && ruff format --check .
```

Os testes que usam o banco real são pulados sem `DATABASE_URL_LEITOR`. Veja [testes-e-ci.md](testes-e-ci.md).
