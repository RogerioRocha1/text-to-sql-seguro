"""Perguntas ambíguas em relação ao esquema: o assistente pergunta antes de gerar o SQL."""

import pytest

from assistente_sql.esclarecimento import verificar


@pytest.mark.parametrize(
    ("pergunta", "regra"),
    [
        ("Quanto o governo gastou com saúde?", "medida_de_gasto"),
        ("Quais os órgãos que mais gastaram?", "medida_de_gasto"),
        ("Quanto foi aplicado em educação?", "medida_de_gasto"),
        ("Qual o orçamento do Ministério da Educação?", "tipo_de_orcamento"),
        ("Qual o valor previsto para a função Defesa?", "tipo_de_orcamento"),
        ("Quanto foi pago em 2024?", "ano_indisponivel"),
        ("Quanto o MEC gastou em 2023?", "ano_indisponivel"),
    ],
)
def test_perguntas_ambiguas(pergunta, regra):
    esclarecimento = verificar(pergunta)
    assert esclarecimento is not None
    assert esclarecimento.regra == regra
    assert esclarecimento.opcoes


@pytest.mark.parametrize(
    "pergunta",
    [
        # perguntas do conjunto de desenvolvimento e da tela: dizem qual medida querem
        "Quanto o Ministério da Saúde pagou em 2025?",
        "Qual o orçamento atualizado e o realizado do Ministério da Educação?",
        "Quanto foi empenhado pelo Ministério da Fazenda em 2025?",
        "Quais os 5 estados que mais receberam pagamentos em 2025?",
        "Qual foi o valor pago por mês na função Saúde?",
        "Quanto foi gasto (valor liquidado) em dezembro?",
        "Qual o orçamento inicial da função Saúde?",
        "Quantos órgãos existem?",
    ],
)
def test_perguntas_claras_seguem_direto(pergunta):
    assert verificar(pergunta) is None


def test_escolha_do_usuario_resolve_a_ambiguidade():
    pergunta = "Quanto o governo gastou com saúde?"
    esclarecimento = verificar(pergunta)
    for opcao in esclarecimento.opcoes:
        reescrita = esclarecimento.aplicar(pergunta, opcao)
        assert reescrita.startswith("Quanto o governo gastou com saúde (considere o valor")
        assert verificar(reescrita) is None


def test_ano_indisponivel_troca_o_ano():
    pergunta = "Quanto foi pago em 2024?"
    esclarecimento = verificar(pergunta)
    assert "2025" in esclarecimento.pergunta and "2024" in esclarecimento.pergunta
    assert esclarecimento.aplicar(pergunta, esclarecimento.opcoes[0]) == "Quanto foi pago em 2025?"


def test_codigo_de_cinco_digitos_nao_e_ano():
    assert verificar("Quanto o órgão 20101 pagou em 2025?") is None
