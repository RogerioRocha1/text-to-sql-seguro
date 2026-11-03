"""Testes da apresentação (tabela e gráfico) e da interface Streamlit."""

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from assistente_sql.apresentacao import escolher_grafico, para_tabela
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
