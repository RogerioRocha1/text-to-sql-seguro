"""Gerador de SQL: monta o prompt a partir do banco e pede a consulta ao modelo local.

O esquema mostrado ao modelo é lido do próprio PostgreSQL (tabelas, colunas,
comentários, chaves estrangeiras e valores comuns de colunas categóricas), para
que o prompt nunca fique desatualizado em relação ao banco.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

import psycopg

from assistente_sql.esquema import TABELAS_CONSULTAVEIS

# Colunas de texto com até este número de valores distintos têm os valores
# listados no prompt (UF, grupo de despesa, modalidade...).
MAX_VALORES_CATEGORICOS = 40


@dataclass(frozen=True)
class Coluna:
    nome: str
    tipo: str
    comentario: str | None = None
    valores: tuple[str, ...] = ()


@dataclass(frozen=True)
class Tabela:
    nome: str
    comentario: str | None
    colunas: tuple[Coluna, ...]
    ligacoes: tuple[str, ...] = field(default=())


_SQL_COLUNAS = """
SELECT c.relname, obj_description(c.oid, 'pg_class'), a.attname,
       format_type(a.atttypid, a.atttypmod), col_description(c.oid, a.attnum)
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
WHERE n.nspname = 'public' AND c.relname = ANY(%(tabelas)s)
ORDER BY array_position(%(tabelas)s, c.relname::text), a.attnum
"""

_SQL_LIGACOES = """
SELECT c.conrelid::regclass::text, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE c.contype = 'f' AND n.nspname = 'public'
ORDER BY 1, 2
"""

# Valores mais comuns guardados pelo ANALYZE; não varre as tabelas.
_SQL_VALORES = """
SELECT tablename, attname, most_common_vals::text::text[]
FROM pg_stats
WHERE schemaname = 'public' AND n_distinct BETWEEN 1 AND %(maximo)s
  AND tablename = ANY(%(tabelas)s) AND attname NOT LIKE 'codigo%%'
"""


def ler_esquema(cursor: psycopg.Cursor) -> list[Tabela]:
    """Lê do banco a descrição das tabelas consultáveis."""
    tabelas = list(TABELAS_CONSULTAVEIS)
    cursor.execute(_SQL_VALORES, {"tabelas": tabelas, "maximo": MAX_VALORES_CATEGORICOS})
    valores = {(t, c): tuple(v or ()) for t, c, v in cursor.fetchall()}

    cursor.execute(_SQL_LIGACOES)
    ligacoes: dict[str, list[str]] = {}
    for tabela, definicao in cursor.fetchall():
        ligacoes.setdefault(tabela, []).append(definicao)

    cursor.execute(_SQL_COLUNAS, {"tabelas": tabelas})
    colunas: dict[str, list[Coluna]] = {}
    comentarios: dict[str, str | None] = {}
    for tabela, comentario_tabela, coluna, tipo, comentario in cursor.fetchall():
        comentarios[tabela] = comentario_tabela
        colunas.setdefault(tabela, []).append(
            Coluna(coluna, tipo, comentario, valores.get((tabela, coluna), ()))
        )

    return [
        Tabela(nome, comentarios[nome], tuple(colunas[nome]), tuple(ligacoes.get(nome, ())))
        for nome in tabelas
        if nome in colunas
    ]


def formatar_esquema(tabelas: list[Tabela]) -> str:
    """Escreve o esquema como CREATE TABLE comentado, formato que o modelo conhece bem."""
    blocos = []
    for tabela in tabelas:
        linhas = []
        if tabela.comentario:
            linhas.append(f"-- {tabela.comentario}")
        linhas.append(f"CREATE TABLE {tabela.nome} (")
        definicoes = []
        for coluna in tabela.colunas:
            notas = []
            if coluna.comentario:
                notas.append(coluna.comentario)
            if coluna.valores:
                notas.append("valores: " + ", ".join(coluna.valores))
            nota = f"  -- {' | '.join(notas)}" if notas else ""
            definicoes.append((f"  {coluna.nome} {coluna.tipo}", nota))
        definicoes += [(f"  {ligacao}", "") for ligacao in tabela.ligacoes]
        for i, (definicao, nota) in enumerate(definicoes):
            virgula = "," if i < len(definicoes) - 1 else ""
            linhas.append(f"{definicao}{virgula}{nota}")
        linhas.append(");")
        blocos.append("\n".join(linhas))
    return "\n\n".join(blocos)


INSTRUCOES = """\
Você escreve consultas SQL para PostgreSQL sobre despesas do governo federal \
brasileiro em 2025 (dados do Portal da Transparência).

Regras:
- Responda apenas com uma consulta SELECT dentro de um bloco ```sql```, sem explicação.
- Use somente as tabelas e colunas do esquema abaixo.
- Valores estão em reais. "Gasto" ou "pago" vem de execucao_mensal.valor_pago; \
"previsto" ou "orçado" vem de orcamento. Para totais do ano, some todos os meses.
- Ministérios e poderes estão em orgao.nome_orgao_superior; orgao.nome é o órgão \
vinculado (autarquia, fundação, universidade).
- Nunca compare nomes com "=". Para buscar por nome, ignore acentos e maiúsculas: \
unaccent(coluna) ILIKE unaccent('%termo%').
- Traga nomes legíveis (por exemplo, o nome do órgão), não só códigos.

Esquema:
{esquema}
"""


def montar_mensagens(pergunta: str, esquema: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": INSTRUCOES.format(esquema=esquema)},
        {"role": "user", "content": pergunta},
    ]


_BLOCO_SQL = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extrair_sql(texto: str) -> str:
    """Tira o SQL de dentro do bloco de código da resposta do modelo."""
    bloco = _BLOCO_SQL.search(texto)
    return (bloco.group(1) if bloco else texto).strip()


@dataclass(frozen=True)
class RespostaModelo:
    texto: str
    tokens_entrada: int = 0
    tokens_saida: int = 0
    segundos: float = 0.0


class Modelo(Protocol):
    nome: str

    def gerar(self, mensagens: list[dict[str, str]]) -> RespostaModelo: ...


class ModeloOllama:
    """Cliente mínimo da API /api/chat do Ollama (sem dependências extras)."""

    def __init__(self, url: str, nome: str, timeout: float = 300, contexto: int = 8192):
        self.url = url.rstrip("/")
        self.nome = nome
        self.timeout = timeout
        self.contexto = contexto

    def gerar(self, mensagens: list[dict[str, str]]) -> RespostaModelo:
        corpo = {
            "model": self.nome,
            "messages": mensagens,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": self.contexto},
        }
        pedido = urllib.request.Request(  # noqa: S310 (URL vem da configuração)
            f"{self.url}/api/chat",
            data=json.dumps(corpo).encode(),
            headers={"Content-Type": "application/json"},
        )
        inicio = time.perf_counter()
        with urllib.request.urlopen(pedido, timeout=self.timeout) as resposta:  # noqa: S310
            dados = json.load(resposta)
        return RespostaModelo(
            texto=dados["message"]["content"],
            tokens_entrada=dados.get("prompt_eval_count", 0),
            tokens_saida=dados.get("eval_count", 0),
            segundos=time.perf_counter() - inicio,
        )
