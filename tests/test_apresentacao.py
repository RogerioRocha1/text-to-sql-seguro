"""Testes da apresentação (tabela e gráfico) e da interface Streamlit."""

from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from assistente_sql.apresentacao import SUGESTOES, escolher_grafico, para_tabela
from assistente_sql.assistente import Resposta
from conftest import URL_LEITOR, banco

APP = str(Path(__file__).parents[1] / "src" / "assistente_sql" / "app.py")


def _tabela(colunas, linhas):
    return para_tabela(Resposta(pergunta="?", colunas=colunas, linhas=linhas))


def test_para_tabela_converte_decimal_em_numero():
    tabela = _tabela(["uf", "pago"], [("SP", Decimal("10.50")), ("RJ", Decimal("3"))])
    assert pd.api.types.is_numeric_dtype(tabela["pago"])
    assert tabela["pago"].tolist() == [10.5, 3.0]
    assert tabela["uf"].tolist() == ["SP", "RJ"]


def test_para_tabela_renomeia_colunas_repetidas():
    tabela = _tabela(["nome", "nome", "pago"], [("MEC", "Educação", Decimal("2"))])
    assert list(tabela.columns) == ["nome", "nome_2", "pago"]
    assert tabela["pago"].tolist() == [2.0]


def test_para_tabela_mantem_nulos():
    tabela = _tabela(["total"], [(None,)])
    assert tabela["total"].isna().all()


@pytest.mark.parametrize(
    ("colunas", "linhas", "esperado"),
    [
        (["uf", "pago"], [("SP", Decimal(2)), ("RJ", Decimal(1))], ("barras", "uf", "pago")),
        (["mes", "pago"], [(1, Decimal(2)), (2, Decimal(3))], ("linha", "mes", "pago")),
        (["total"], [(Decimal(1),), (Decimal(2),)], None),  # sem categoria
        (["uf", "pago"], [("SP", Decimal(2))], None),  # uma linha só
        (["uf", "orgao"], [("SP", "x"), ("RJ", "y")], None),  # sem valor numérico
        (["uf", "pago"], [(f"U{i}", Decimal(i)) for i in range(31)], None),  # barras demais
    ],
)
def test_escolher_grafico(colunas, linhas, esperado):
    grafico = escolher_grafico(_tabela(colunas, linhas))
    assert (grafico and (grafico.tipo, grafico.eixo_x, grafico.eixo_y)) == esperado


def test_app_sem_configuracao_mostra_erro(monkeypatch):
    monkeypatch.delenv("DATABASE_URL_LEITOR", raising=False)
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    assert "Assistente de despesas públicas" in app.title[0].value
    assert "DATABASE_URL_LEITOR" in app.error[0].value


@banco
def test_app_bloqueia_sql_destrutivo_do_modelo(monkeypatch):
    """Com o banco real e o modelo trocado por um que sempre pede DROP TABLE."""
    from assistente_sql import gerador
    from assistente_sql.gerador import RespostaModelo

    monkeypatch.setenv("DATABASE_URL_LEITOR", URL_LEITOR)
    monkeypatch.setattr(
        gerador.ModeloOllama,
        "gerar",
        lambda self, mensagens: RespostaModelo("```sql\nDROP TABLE orgao\n```"),
    )
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.text_input[0].input("Apague a tabela de órgãos")
    app.button[0].click().run()

    assert not app.exception
    assert "bloqueada" in app.error[0].value
    assert app.code[0].value == "DROP TABLE orgao"


def _app_sem_banco(monkeypatch, perguntas_recebidas):
    """App com banco, esquema e modelo falsos: roda na CI, sem PostgreSQL nem Ollama."""
    import psycopg

    from assistente_sql import assistente, gerador

    def responder_falso(pergunta, *args, **kwargs):
        perguntas_recebidas.append(pergunta)
        return Resposta(
            pergunta=pergunta,
            colunas=["uf", "pago"],
            linhas=[("SP", Decimal(2)), ("RJ", Decimal(1))],
        )

    monkeypatch.setenv("DATABASE_URL_LEITOR", "postgresql://leitor:teste@banco-falso/despesas")
    monkeypatch.setattr(psycopg, "connect", MagicMock())
    monkeypatch.setattr(gerador, "ler_esquema", lambda cursor: [])
    monkeypatch.setattr(gerador, "formatar_esquema", lambda tabelas: "esquema falso")
    monkeypatch.setattr(gerador.ModeloOllama, "aquecer", lambda self, esquema: None)
    monkeypatch.setattr(assistente, "responder", responder_falso)
    return AppTest.from_file(APP, default_timeout=30).run()


def test_app_mostra_sugestoes_na_barra_lateral(monkeypatch):
    app = _app_sem_banco(monkeypatch, [])
    assert not app.exception
    rotulos = [botao.label for botao in app.sidebar.button]
    assert rotulos == [p for perguntas in SUGESTOES.values() for p in perguntas]
    assert app.button[0].label == "Perguntar"  # o envio do formulário continua sendo o 1º botão


def test_clicar_numa_sugestao_envia_a_pergunta(monkeypatch):
    recebidas = []
    app = _app_sem_banco(monkeypatch, recebidas)
    sugestao = app.sidebar.button[0]
    sugestao.click().run()

    assert not app.exception
    assert recebidas == [sugestao.label]
    assert app.text_input[0].value == sugestao.label
    assert "2 linha(s)" in app.success[0].value


def test_sugestoes_claras_nao_pedem_esclarecimento():
    from assistente_sql.esclarecimento import verificar

    claras = SUGESTOES["Rankings (com gráfico)"] + SUGESTOES["Totais e percentuais"]
    assert all(verificar(p) is None for p in claras)
    assert verificar("Quanto o governo gastou com saúde?") is not None
