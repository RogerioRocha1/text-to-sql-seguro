"""Catálogo de ataques (eval/ataques.jsonl) como testes.

Cada ataque em SQL declara a barreira que deve pará-lo:
- ``validador``: bloqueado por ``validar``, sem banco (roda na CI);
- ``custo`` e ``banco``: só o banco real consegue parar (EXPLAIN ou tempo
  limite do usuário leitor); rodam com DATABASE_URL_LEITOR definida.
"""

import json
from pathlib import Path

import pytest

from assistente_sql import validar
from assistente_sql.assistente import responder
from assistente_sql.esquema import TABELAS_CONSULTAVEIS
from assistente_sql.gerador import RespostaModelo
from conftest import banco

ARQUIVO = Path(__file__).resolve().parents[1] / "eval" / "ataques.jsonl"
ATAQUES = [json.loads(linha) for linha in ARQUIVO.read_text(encoding="utf-8").splitlines() if linha]
SQL = [a for a in ATAQUES if a["tipo"] == "sql"]
TABELAS = frozenset(TABELAS_CONSULTAVEIS)


def _ids(ataques):
    return [a["id"] for a in ataques]


def _id(ataque):
    return ataque["id"]


def test_catalogo_bem_formado():
    ids = _ids(ATAQUES)
    assert len(ids) == len(set(ids)), "IDs repetidos no catálogo"
    for ataque in ATAQUES:
        assert ataque["tipo"] in {"sql", "pergunta"}
        assert ataque["categoria"] and ataque["entrada"].strip()
        if ataque["tipo"] == "sql":
            assert ataque["barreira_esperada"] in {"validador", "custo", "banco"}
    assert len(SQL) >= 50
    assert len(ATAQUES) - len(SQL) >= 20


@pytest.mark.parametrize(
    "ataque", [a for a in SQL if a["barreira_esperada"] == "validador"], ids=_id
)
def test_validador_bloqueia_ataque(ataque):
    resultado = validar(ataque["entrada"], TABELAS)
    assert not resultado.aprovada, f"deveria bloquear: {ataque['entrada']!r}"
    assert resultado.motivo


@pytest.mark.parametrize(
    "ataque", [a for a in SQL if a["barreira_esperada"] != "validador"], ids=_id
)
def test_ataques_que_passam_no_validador_sao_aprovados_por_ele(ataque):
    """Garante que o catálogo diz a verdade: estes só o banco consegue parar."""
    assert validar(ataque["entrada"], TABELAS).aprovada


class ModeloFixo:
    nome = "fixo"

    def __init__(self, sql):
        self.sql = sql

    def gerar(self, mensagens):
        return RespostaModelo(texto=f"```sql\n{self.sql}\n```")


@banco
@pytest.mark.parametrize(
    "ataque", [a for a in SQL if a["barreira_esperada"] != "validador"], ids=_id
)
def test_banco_para_o_que_o_validador_deixa_passar(conexao_leitor, ataque):
    resposta = responder("ataque", ModeloFixo(ataque["entrada"]), conexao_leitor, esquema="")
    assert resposta.situacao != "ok", resposta.sql_executado
