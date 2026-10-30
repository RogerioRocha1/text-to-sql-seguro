"""Testes da carga que não precisam de banco: URLs, cabeçalhos e leitura do ZIP."""

import zipfile

import pytest

from assistente_sql.carga import abrir_csv
from assistente_sql.esquema import ddl_staging
from assistente_sql.fontes import (
    EXECUCAO,
    ORCAMENTO,
    arquivos_do_ano,
    conferir_cabecalho,
    ler_cabecalho,
)


def _linha_cabecalho(fonte):
    return (";".join(f'"{c}"' for c in fonte.cabecalho) + "\r\n").encode("cp1252")


def test_arquivos_do_ano_tem_orcamento_e_doze_meses():
    arquivos = arquivos_do_ano(2025)
    assert len(arquivos) == 13
    assert arquivos[0][0] is ORCAMENTO
    assert arquivos[0][1].endswith("/orcamento-despesa/2025")
    assert [a[1].rsplit("/", 1)[1] for a in arquivos[1:]] == [f"2025{m:02d}" for m in range(1, 13)]
    assert arquivos[-1][2] == "202512_Despesas.zip"


@pytest.mark.parametrize("fonte", [ORCAMENTO, EXECUCAO])
def test_cabecalho_em_cp1252_e_aceito(fonte):
    conferir_cabecalho(fonte, ler_cabecalho(_linha_cabecalho(fonte)))


def test_cabecalho_com_coluna_trocada_e_recusado():
    lido = ORCAMENTO.cabecalho
    lido[1], lido[2] = lido[2], lido[1]
    with pytest.raises(ValueError, match="coluna 2"):
        conferir_cabecalho(ORCAMENTO, lido)


def test_cabecalho_com_coluna_a_mais_e_recusado():
    with pytest.raises(ValueError, match="47 colunas, lidas 48"):
        conferir_cabecalho(EXECUCAO, [*EXECUCAO.cabecalho, "Nova coluna"])


def test_colunas_de_staging_sao_unicas():
    for fonte in (ORCAMENTO, EXECUCAO):
        assert len(set(fonte.colunas_staging)) == len(fonte.colunas_staging)


def test_ddl_staging_usa_schema_carga():
    ddl = ddl_staging(ORCAMENTO)
    assert "CREATE UNLOGGED TABLE carga.orcamento_bruto" in ddl
    assert ddl.count(" text") == len(ORCAMENTO.colunas)


def test_abrir_csv_le_o_unico_csv_do_zip(tmp_path):
    caminho = tmp_path / "x.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("2025_OrcamentoDespesa.csv", _linha_cabecalho(ORCAMENTO) + b'"2025"\r\n')
    arquivo, csv = abrir_csv(caminho)
    with arquivo, csv:
        assert ler_cabecalho(csv.readline()) == ORCAMENTO.cabecalho
        assert csv.read() == b'"2025"\r\n'


def test_abrir_csv_recusa_zip_sem_csv(tmp_path):
    caminho = tmp_path / "x.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("leia-me.txt", "nada")
    with pytest.raises(ValueError, match="esperado 1 CSV"):
        abrir_csv(caminho)
