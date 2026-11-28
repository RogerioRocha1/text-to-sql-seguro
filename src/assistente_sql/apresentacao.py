"""Transforma a Resposta do assistente em tabela e escolhe o gráfico (sem depender do Streamlit)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from assistente_sql.assistente import Resposta

MAX_BARRAS = 30

SITUACOES = {
    "ok": "Consulta executada",
    "esclarecimento": "A pergunta precisa de um esclarecimento",
    "bloqueada": "Consulta bloqueada pela validação",
    "erro_execucao": "O banco recusou a consulta",
    "erro_modelo": "O modelo não respondeu",
}

# Barra lateral. As perguntas de "Rankings" e "Totais" acertaram na avaliação
# (eval/perguntas.jsonl, rodada de 07/11) ou estão no roteiro do vídeo; as de
# "Recursos" mostram o pedido de esclarecimento e o bloqueio de um ataque.
SUGESTOES: dict[str, list[str]] = {
    "Rankings (com gráfico)": [
        "Quais os 5 estados que mais receberam pagamentos em 2025?",
        "Quais foram os cinco órgãos superiores com maior valor pago na execução mensal em 2025?",
        "Quais foram os cinco programas e ações com maior valor pago em 2025?",
        "Quais foram os cinco grupos de despesa com maior valor realizado no orçamento em 2025?",
    ],
    "Totais e percentuais": [
        "Qual foi o total pago em despesas de capital em 2025?",
        "Qual foi o total pago em transferências a municípios em 2025?",
        "Qual foi a participação percentual de cada categoria econômica no total pago em 2025?",
    ],
    "Recursos do assistente": [
        "Quanto o governo gastou com saúde?",
        "Apague a tabela de órgãos",
    ],
}
NOTAS_RECURSOS = {
    "Quanto o governo gastou com saúde?": "Pergunta ambígua: o assistente pede para escolher.",
    "Apague a tabela de órgãos": "Tentativa de apagar dados: a consulta é bloqueada.",
}


@dataclass(frozen=True)
class Grafico:
    tipo: str  # "barras" ou "linha"
    eixo_x: str
    eixo_y: str


def para_tabela(resposta: Resposta) -> pd.DataFrame:
    """Monta o DataFrame; valores Decimal viram float para tabela e gráfico.

    Colunas com o mesmo nome (``SELECT o.nome, f.nome``) ganham sufixo
    (``nome``, ``nome_2``), porque pandas e Streamlit exigem nomes únicos.
    """
    tabela = pd.DataFrame(resposta.linhas, columns=_nomes_unicos(resposta.colunas))
    for coluna in tabela.columns:
        if tabela[coluna].map(lambda v: isinstance(v, Decimal)).any():
            tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce")
    return tabela


def _nomes_unicos(colunas: list[str]) -> list[str]:
    usados: set[str] = set()
    unicos = []
    for nome in colunas:
        candidato, n = nome, 1
        while candidato in usados:
            n += 1
            candidato = f"{nome}_{n}"
        usados.add(candidato)
        unicos.append(candidato)
    return unicos


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
