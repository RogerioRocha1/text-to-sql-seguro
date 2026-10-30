"""Arquivos de despesas do Portal da Transparência (CGU) usados pelo projeto.

Cada fonte declara a URL de download e o cabeçalho esperado do CSV, na ordem
do arquivo, com o nome da coluna correspondente na tabela de staging. Se a CGU
mudar o layout, a carga falha na validação do cabeçalho em vez de gravar
colunas trocadas.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

URL_BASE = "https://portaldatransparencia.gov.br/download-de-dados"
ENCODING_CSV = "cp1252"
SEPARADOR_CSV = ";"


@dataclass(frozen=True)
class Fonte:
    nome: str
    tabela_staging: str
    colunas: tuple[tuple[str, str], ...]  # (cabeçalho no CSV, coluna no staging)

    @property
    def cabecalho(self) -> list[str]:
        return [c[0] for c in self.colunas]

    @property
    def colunas_staging(self) -> list[str]:
        return [c[1] for c in self.colunas]


ORCAMENTO = Fonte(
    nome="orcamento-despesa",
    tabela_staging="orcamento_bruto",
    colunas=(
        ("EXERCÍCIO", "exercicio"),
        ("CÓDIGO ÓRGÃO SUPERIOR", "cod_orgao_superior"),
        ("NOME ÓRGÃO SUPERIOR", "nome_orgao_superior"),
        ("CÓDIGO ÓRGÃO SUBORDINADO", "cod_orgao"),
        ("NOME ÓRGÃO SUBORDINADO", "nome_orgao"),
        ("CÓDIGO UNIDADE ORÇAMENTÁRIA", "cod_uo"),
        ("NOME UNIDADE ORÇAMENTÁRIA", "nome_uo"),
        ("CÓDIGO FUNÇÃO", "cod_funcao"),
        ("NOME FUNÇÃO", "nome_funcao"),
        ("CÓDIGO SUBFUNÇÃO", "cod_subfuncao"),
        ("NOME SUBFUNÇÃO", "nome_subfuncao"),
        ("CÓDIGO PROGRAMA ORÇAMENTÁRIO", "cod_programa"),
        ("NOME PROGRAMA ORÇAMENTÁRIO", "nome_programa"),
        ("CÓDIGO AÇÃO", "cod_acao"),
        ("NOME AÇÃO", "nome_acao"),
        ("CÓDIGO CATEGORIA ECONÔMICA", "cod_categoria"),
        ("NOME CATEGORIA ECONÔMICA", "nome_categoria"),
        ("CÓDIGO GRUPO DE DESPESA", "cod_grupo"),
        ("NOME GRUPO DE DESPESA", "nome_grupo"),
        ("CÓDIGO ELEMENTO DE DESPESA", "cod_elemento"),
        ("NOME ELEMENTO DE DESPESA", "nome_elemento"),
        ("ORÇAMENTO INICIAL (R$)", "valor_inicial"),
        ("ORÇAMENTO ATUALIZADO (R$)", "valor_atualizado"),
        ("ORÇAMENTO EMPENHADO (R$)", "valor_empenhado"),
        ("ORÇAMENTO REALIZADO (R$)", "valor_realizado"),
        (
            "% REALIZADO DO ORÇAMENTO (COM RELAÇÃO AO ORÇAMENTO ATUALIZADO)",
            "pct_realizado",
        ),
    ),
)

# "Subfução" está escrito assim no arquivo da CGU.
EXECUCAO = Fonte(
    nome="despesas-execucao",
    tabela_staging="execucao_bruta",
    colunas=(
        ("Ano e mês do lançamento", "ano_mes"),
        ("Código Órgão Superior", "cod_orgao_superior"),
        ("Nome Órgão Superior", "nome_orgao_superior"),
        ("Código Órgão Subordinado", "cod_orgao"),
        ("Nome Órgão Subordinado", "nome_orgao"),
        ("Código Unidade Gestora", "cod_ug"),
        ("Nome Unidade Gestora", "nome_ug"),
        ("Código Gestão", "cod_gestao"),
        ("Nome Gestão", "nome_gestao"),
        ("Código Unidade Orçamentária", "cod_uo"),
        ("Nome Unidade Orçamentária", "nome_uo"),
        ("Código Função", "cod_funcao"),
        ("Nome Função", "nome_funcao"),
        ("Código Subfução", "cod_subfuncao"),
        ("Nome Subfunção", "nome_subfuncao"),
        ("Código Programa Orçamentário", "cod_programa"),
        ("Nome Programa Orçamentário", "nome_programa"),
        ("Código Ação", "cod_acao"),
        ("Nome Ação", "nome_acao"),
        ("Código Plano Orçamentário", "cod_plano_orc"),
        ("Plano Orçamentário", "nome_plano_orc"),
        ("Código Programa Governo", "cod_programa_governo"),
        ("Nome Programa Governo", "nome_programa_governo"),
        ("UF", "uf"),
        ("Município", "municipio"),
        ("Código Subtítulo", "cod_subtitulo"),
        ("Nome Subtítulo", "nome_subtitulo"),
        ("Código Localizador", "cod_localizador"),
        ("Nome Localizador", "nome_localizador"),
        ("Sigla Localizador", "sigla_localizador"),
        ("Descrição Complementar Localizador", "desc_localizador"),
        ("Código Autor Emenda", "cod_autor_emenda"),
        ("Nome Autor Emenda", "nome_autor_emenda"),
        ("Código Categoria Econômica", "cod_categoria"),
        ("Nome Categoria Econômica", "nome_categoria"),
        ("Código Grupo de Despesa", "cod_grupo"),
        ("Nome Grupo de Despesa", "nome_grupo"),
        ("Código Elemento de Despesa", "cod_elemento"),
        ("Nome Elemento de Despesa", "nome_elemento"),
        ("Código Modalidade da Despesa", "cod_modalidade"),
        ("Modalidade da Despesa", "nome_modalidade"),
        ("Valor Empenhado (R$)", "valor_empenhado"),
        ("Valor Liquidado (R$)", "valor_liquidado"),
        ("Valor Pago (R$)", "valor_pago"),
        ("Valor Restos a Pagar Inscritos (R$)", "valor_rp_inscritos"),
        ("Valor Restos a Pagar Cancelado (R$)", "valor_rp_cancelado"),
        ("Valor Restos a Pagar Pagos (R$)", "valor_rp_pagos"),
    ),
)


def arquivos_do_ano(ano: int) -> list[tuple[Fonte, str, str]]:
    """Lista (fonte, URL, nome do arquivo local) de tudo que a carga de ``ano`` precisa."""
    arquivos = [
        (ORCAMENTO, f"{URL_BASE}/{ORCAMENTO.nome}/{ano}", f"{ano}_OrcamentoDespesa.zip"),
    ]
    for mes in range(1, 13):
        periodo = f"{ano}{mes:02d}"
        arquivos.append(
            (EXECUCAO, f"{URL_BASE}/{EXECUCAO.nome}/{periodo}", f"{periodo}_Despesas.zip")
        )
    return arquivos


def ler_cabecalho(linha: bytes) -> list[str]:
    """Decodifica a primeira linha do CSV da CGU em uma lista de nomes de coluna."""
    texto = linha.decode(ENCODING_CSV).lstrip("﻿")
    return next(csv.reader(io.StringIO(texto), delimiter=SEPARADOR_CSV))


def conferir_cabecalho(fonte: Fonte, lido: list[str]) -> None:
    """Falha se o cabeçalho do arquivo não for exatamente o esperado para a fonte."""
    esperado = fonte.cabecalho
    if lido == esperado:
        return
    diferencas = [
        f"coluna {i + 1}: esperado {e!r}, lido {r!r}"
        for i, (e, r) in enumerate(zip(esperado, lido, strict=False))
        if e != r
    ]
    if len(lido) != len(esperado):
        diferencas.append(f"esperadas {len(esperado)} colunas, lidas {len(lido)}")
    raise ValueError(f"Layout de {fonte.nome} mudou: " + "; ".join(diferencas))
