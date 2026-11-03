"""Testes do gerador: prompt, extração do SQL, cliente do Ollama e leitura do esquema."""

import io
import json

import pytest

from assistente_sql import gerador
from assistente_sql.esquema import TABELAS_CONSULTAVEIS
from assistente_sql.gerador import (
    Coluna,
    ModeloOllama,
    Tabela,
    extrair_sql,
    formatar_esquema,
    ler_esquema,
    montar_mensagens,
)
from conftest import banco

TABELA = Tabela(
    nome="execucao_mensal",
    comentario="Execução mensal.",
    colunas=(
        Coluna("uf", "text", "Sigla da UF.", ("SP", "RJ")),
        Coluna("valor_pago", "numeric(18,2)", "Valor pago (R$)."),
        Coluna("codigo_orgao", "text"),
    ),
    ligacoes=("FOREIGN KEY (codigo_orgao) REFERENCES orgao(codigo)",),
)


def test_formatar_esquema_escreve_create_table_comentado():
    texto = formatar_esquema([TABELA])
    assert texto.splitlines() == [
        "-- Execução mensal.",
        "CREATE TABLE execucao_mensal (",
        "  uf text,  -- Sigla da UF. | valores: SP, RJ",
        "  valor_pago numeric(18,2),  -- Valor pago (R$).",
        "  codigo_orgao text,",
        "  FOREIGN KEY (codigo_orgao) REFERENCES orgao(codigo)",
        ");",
    ]


def test_montar_mensagens_coloca_esquema_no_sistema_e_pergunta_no_usuario():
    sistema, usuario = montar_mensagens("Quanto foi pago?", "CREATE TABLE x ();")
    assert sistema["role"] == "system"
    assert "CREATE TABLE x ();" in sistema["content"]
    assert "SELECT" in sistema["content"]
    assert usuario == {"role": "user", "content": "Quanto foi pago?"}


@pytest.mark.parametrize(
    "texto",
    [
        "```sql\nSELECT 1\n```",
        "```SQL\nSELECT 1\n```",
        "Aqui está:\n```sql\nSELECT 1\n```\nEssa consulta soma...",
        "```\nSELECT 1\n```",
        "SELECT 1",
        "  SELECT 1  \n",
    ],
)
def test_extrair_sql(texto):
    assert extrair_sql(texto) == "SELECT 1"


def test_extrair_sql_pega_so_o_primeiro_bloco():
    assert extrair_sql("```sql\nSELECT 1\n```\n```sql\nDROP TABLE x\n```") == "SELECT 1"


def test_modelo_ollama_envia_pedido_e_le_resposta(monkeypatch):
    enviado = {}

    def urlopen_falso(pedido, timeout):
        enviado["url"] = pedido.full_url
        enviado["corpo"] = json.loads(pedido.data)
        resposta = {
            "message": {"content": "```sql\nSELECT 1\n```"},
            "prompt_eval_count": 1500,
            "eval_count": 20,
        }
        return io.BytesIO(json.dumps(resposta).encode())

    monkeypatch.setattr(gerador.urllib.request, "urlopen", urlopen_falso)
    modelo = ModeloOllama("http://ollama:11434/", "qwen2.5-coder:7b")
    resposta = modelo.gerar([{"role": "user", "content": "oi"}])

    assert enviado["url"] == "http://ollama:11434/api/chat"
    assert enviado["corpo"]["model"] == "qwen2.5-coder:7b"
    assert enviado["corpo"]["stream"] is False
    assert enviado["corpo"]["options"]["temperature"] == 0
    assert resposta.texto == "```sql\nSELECT 1\n```"
    assert (resposta.tokens_entrada, resposta.tokens_saida) == (1500, 20)


@banco
def test_ler_esquema_do_banco(cursor_leitor):
    tabelas = ler_esquema(cursor_leitor)
    assert [t.nome for t in tabelas] == list(TABELAS_CONSULTAVEIS)

    execucao = next(t for t in tabelas if t.nome == "execucao_mensal")
    colunas = {c.nome: c for c in execucao.colunas}
    assert "SP" in colunas["uf"].valores
    assert colunas["valor_pago"].comentario
    assert not colunas["codigo_funcao"].valores  # códigos não são listados
    assert any("REFERENCES orgao" in ligacao for ligacao in execucao.ligacoes)
