"""Transforma a Resposta do assistente em tabela e escolhe o gráfico (sem depender do Streamlit)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from assistente_sql.assistente import Resposta

MAX_BARRAS = 30

SITUACOES = {
    "ok": "Consulta executada",
    "bloqueada": "Consulta bloqueada pela validação",
    "erro_execucao": "O banco recusou a consulta",
    "erro_modelo": "O modelo não respondeu",
}


@dataclass(frozen=True)
class Grafico:
    tipo: str  # "barras" ou "linha"
    eixo_x: str
    eixo_y: str


def para_tabela(resposta: Resposta) -> pd.DataFrame:
    """Monta o DataFrame; valores Decimal viram float para tabela e gráfico."""
    tabela = pd.DataFrame(resposta.linhas, columns=resposta.colunas)
    for coluna in tabela.columns:
        if tabela[coluna].map(lambda v: isinstance(v, Decimal)).any():
            tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce")
    return tabela


def escolher_grafico(tabela: pd.DataFrame) -> Grafico | None:
    """Gráfico simples quando há uma categoria (ou mês) e um valor numérico.

    Mês vira linha; outra categoria vira barras (até MAX_BARRAS). Resultado de
    uma linha só, ou sem coluna numérica, fica só na tabela.
    """
    if len(tabela) < 2 or len(tabela.columns) < 2:
        return None
    numericas = [c for c in tabela.columns if pd.api.types.is_numeric_dtype(tabela[c])]
    categorias = [c for c in tabela.columns if c not in numericas]

    if "mes" in tabela.columns:
        valores = [c for c in numericas if c != "mes"]
        return Grafico("linha", "mes", valores[0]) if valores else None
    if len(categorias) == 1 and numericas and len(tabela) <= MAX_BARRAS:
        return Grafico("barras", categorias[0], numericas[0])
    return None
