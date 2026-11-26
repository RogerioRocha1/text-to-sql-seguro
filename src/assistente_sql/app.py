"""Interface web: streamlit run src/assistente_sql/app.py"""

from __future__ import annotations

import logging
import threading

import psycopg
import streamlit as st

from assistente_sql.apresentacao import SITUACOES, escolher_grafico, para_tabela
from assistente_sql.assistente import Configuracao, responder
from assistente_sql.gerador import formatar_esquema, ler_esquema

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("assistente_sql")

EXEMPLOS = [
    "Quais os 5 estados que mais receberam pagamentos em 2025?",
    "Qual foi o valor pago por mês na função Saúde?",
    "Qual o orçamento atualizado e o realizado do Ministério da Educação?",
]


@st.cache_resource(show_spinner="Lendo o esquema do banco...")
def carregar_esquema(url: str) -> str:
    with psycopg.connect(url) as conexao, conexao.cursor() as cursor:
        return formatar_esquema(ler_esquema(cursor))


@st.cache_resource(show_spinner=False)
def aquecer_modelo(config: Configuracao, esquema: str) -> threading.Thread:
    """Uma vez por servidor: carrega o modelo e lê o esquema em segundo plano.

    Sem isso, a 1ª pergunta paga a carga do modelo e a leitura do prompt
    (~33 s do 3b numa CPU de 4 núcleos); as seguintes já reaproveitam a leitura.
    """

    def tarefa() -> None:
        try:
            config.criar_modelo().aquecer(esquema)
            log.info("modelo %s aquecido", config.ollama_modelo)
        except Exception:  # o app funciona sem aquecimento, só a 1ª pergunta demora
            log.warning("não foi possível aquecer o modelo", exc_info=True)

    thread = threading.Thread(target=tarefa, name="aquecer-modelo", daemon=True)
    thread.start()
    return thread


def _escolher(pergunta: str) -> None:
    """Botão de esclarecimento: a pergunta reescrita volta para o formulário."""
    st.session_state["pergunta_escolhida"] = pergunta


def mostrar_esclarecimento(resposta) -> None:
    esclarecimento = resposta.esclarecimento
    st.info(esclarecimento.pergunta)
    colunas = st.columns(len(esclarecimento.opcoes))
    for i, (coluna, opcao) in enumerate(zip(colunas, esclarecimento.opcoes, strict=True)):
        coluna.button(
            opcao.rotulo,
            key=f"opcao_{i}",
            on_click=_escolher,
            args=(esclarecimento.aplicar(resposta.pergunta, opcao),),
            width="stretch",
        )


def mostrar_resposta(resposta) -> None:
    if resposta.situacao == "esclarecimento":
        mostrar_esclarecimento(resposta)
        return

    situacao = SITUACOES.get(resposta.situacao, resposta.situacao)
    if resposta.situacao == "ok":
        st.success(f"{situacao}: {len(resposta.linhas)} linha(s).")
    else:
        st.error(f"{situacao}. {resposta.motivo or ''}")

    if resposta.explicacao:
        st.markdown("**O que a consulta faz**\n\n" + resposta.explicacao.texto)
        if not resposta.explicacao.completa:
            st.caption("Parte da consulta é técnica demais para resumir; confira o SQL abaixo.")

    sql = resposta.sql_executado or resposta.sql_gerado
    if sql:
        st.caption("SQL" + (" executado" if resposta.sql_executado else " gerado pelo modelo"))
        st.code(sql, language="sql")

    if resposta.situacao == "ok":
        tabela = para_tabela(resposta)
        if tabela.empty:
            st.warning("A consulta não encontrou nenhum registro.")
        else:
            grafico = escolher_grafico(tabela)
            if grafico and grafico.tipo == "linha":
                st.line_chart(tabela, x=grafico.eixo_x, y=grafico.eixo_y)
            elif grafico:
                st.bar_chart(tabela, x=grafico.eixo_x, y=grafico.eixo_y, horizontal=True)
            st.dataframe(tabela, hide_index=True, width="stretch")

    detalhes = {f"tempo de {etapa} (s)": round(t, 2) for etapa, t in resposta.tempos.items()}
    if resposta.custo_estimado is not None:
        detalhes["custo estimado"] = round(resposta.custo_estimado)
    detalhes["tokens (entrada/saída)"] = f"{resposta.tokens_entrada}/{resposta.tokens_saida}"
    with st.expander("Detalhes"):
        st.json(detalhes)


def main() -> None:
    st.set_page_config(page_title="Assistente de despesas públicas", page_icon="📊")
    st.title("Assistente de despesas públicas")
    st.write(
        "Pergunte em português sobre o orçamento e a execução da despesa do governo "
        "federal em 2025 (Portal da Transparência). A consulta SQL gerada é validada "
        "antes de ir ao banco, e o banco só permite leitura."
    )

    config = Configuracao.do_ambiente()
    if not config.database_url_leitor:
        st.error("Configuração incompleta: defina DATABASE_URL_LEITOR.")
        st.stop()

    try:
        esquema = carregar_esquema(config.database_url_leitor)
    except psycopg.Error as erro:
        st.error(f"Não foi possível conectar ao banco: {erro}")
        st.stop()

    if aquecer_modelo(config, esquema).is_alive():
        st.info(
            "Preparando o modelo em segundo plano. Você já pode perguntar; "
            "a primeira resposta só sai quando ele terminar de carregar."
        )

    escolhida = st.session_state.pop("pergunta_escolhida", None)
    if escolhida:  # o usuário respondeu a um esclarecimento
        st.session_state["campo_pergunta"] = escolhida

    with st.form("pergunta"):
        pergunta = st.text_input("Sua pergunta", placeholder=EXEMPLOS[0], key="campo_pergunta")
        enviada = st.form_submit_button("Perguntar") or bool(escolhida)
    st.caption("Exemplos: " + " · ".join(EXEMPLOS))

    if enviada and pergunta.strip():
        modelo = config.criar_modelo()
        with (
            st.spinner("Gerando e conferindo a consulta..."),
            psycopg.connect(config.database_url_leitor) as conexao,
        ):
            resposta = responder(
                pergunta.strip(),
                modelo,
                conexao,
                esquema,
                config.limite_linhas,
                config.custo_maximo,
            )
        mostrar_resposta(resposta)


main()
