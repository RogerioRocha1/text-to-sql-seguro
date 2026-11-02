"""Recursos compartilhados dos testes.

Testes marcados com ``banco`` usam o PostgreSQL do Marco 2 e só rodam com
DATABASE_URL_LEITOR definida; na CI, são pulados.
"""

import os

import psycopg
import pytest

URL_LEITOR = os.environ.get("DATABASE_URL_LEITOR")
banco = pytest.mark.skipif(not URL_LEITOR, reason="defina DATABASE_URL_LEITOR para rodar")


@pytest.fixture
def conexao_leitor():
    with psycopg.connect(URL_LEITOR) as conexao:
        yield conexao


@pytest.fixture
def cursor_leitor():
    with psycopg.connect(URL_LEITOR, autocommit=True) as conexao:
        yield conexao.cursor()
