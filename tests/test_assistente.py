"""Testes do fluxo ponta a ponta com um modelo falso (o Ollama não roda na CI)."""

import pytest

from assistente_sql.assistente import Configuracao, responder
from assistente_sql.gerador import RespostaModelo
from conftest import banco


class ModeloFalso:
    nome = "falso"

    def __init__(self, texto=None, erro=None):
        self.texto, self.erro, self.mensagens = texto, erro, None

    def gerar(self, mensagens):
        self.mensagens = mensagens
        if self.erro:
            raise self.erro
        return RespostaModelo(texto=self.texto, tokens_entrada=100, tokens_saida=10, segundos=0.5)


class ConexaoProibida:
    """Falha se o fluxo tentar usar o banco quando não deveria."""

    def __getattr__(self, nome):
        pytest.fail(f"o banco não deveria ser usado (acessou {nome!r})")


def test_sql_destrutivo_do_modelo_e_bloqueado_antes_do_banco():
    modelo = ModeloFalso("```sql\nDROP TABLE orgao\n```")
    resposta = responder("Apague os órgãos", modelo, ConexaoProibida(), esquema="...")
    assert resposta.situacao == "bloqueada"
    assert resposta.sql_gerado == "DROP TABLE orgao"
    assert resposta.sql_executado is None
    assert "SELECT" in resposta.motivo


def test_falha_do_modelo_vira_erro_sem_tocar_no_banco():
    modelo = ModeloFalso(erro=ConnectionRefusedError("conexão recusada"))
    resposta = responder("Quanto foi pago?", modelo, ConexaoProibida(), esquema="...")
    assert resposta.situacao == "erro_modelo"
    assert "conexão recusada" in resposta.motivo


def test_pergunta_e_esquema_chegam_ao_modelo():
    modelo = ModeloFalso("```sql\nDROP TABLE x\n```")
    responder("Quanto foi pago?", modelo, ConexaoProibida(), esquema="CREATE TABLE orgao ();")
    assert "CREATE TABLE orgao ();" in modelo.mensagens[0]["content"]
    assert modelo.mensagens[-1]["content"] == "Quanto foi pago?"


def test_configuracao_le_variaveis_de_ambiente(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODELO", "qwen2.5-coder:3b")
    monkeypatch.setenv("LIMITE_LINHAS", "50")
    monkeypatch.setenv("CUSTO_MAXIMO", "1234")
    monkeypatch.delenv("DATABASE_URL_LEITOR", raising=False)
    config = Configuracao.do_ambiente()
    assert config.ollama_modelo == "qwen2.5-coder:3b"
    assert (config.limite_linhas, config.custo_maximo) == (50, 1234.0)
    assert config.database_url_leitor is None


# --- Com o banco real -------------------------------------------------------


@banco
def test_pergunta_respondida_de_ponta_a_ponta(conexao_leitor):
    modelo = ModeloFalso(
        "```sql\nSELECT uf, SUM(valor_pago) AS pago FROM execucao_mensal "
        "WHERE uf IS NOT NULL GROUP BY uf ORDER BY pago DESC LIMIT 3\n```"
    )
    resposta = responder("Top 3 UFs", modelo, conexao_leitor, esquema="...")
    assert resposta.situacao == "ok", resposta.motivo
    assert resposta.colunas == ["uf", "pago"]
    assert len(resposta.linhas) == 3
    assert resposta.custo_estimado is not None
    assert set(resposta.tempos) == {"modelo", "custo", "execucao"}


@banco
def test_consulta_cara_e_bloqueada_pelo_custo(conexao_leitor):
    modelo = ModeloFalso("SELECT COUNT(*) FROM execucao_mensal a CROSS JOIN execucao_mensal b")
    resposta = responder("?", modelo, conexao_leitor, esquema="...")
    assert resposta.situacao == "bloqueada"
    assert "pesada demais" in resposta.motivo
    assert resposta.linhas == []


@banco
def test_coluna_inexistente_vira_erro_e_conexao_continua_usavel(conexao_leitor):
    errada = responder("?", ModeloFalso("SELECT valor FROM orcamento"), conexao_leitor, "...")
    assert errada.situacao == "bloqueada"
    assert "valor" in errada.motivo

    certa = responder("?", ModeloFalso("SELECT COUNT(*) FROM orgao"), conexao_leitor, "...")
    assert certa.situacao == "ok", certa.motivo


@banco
def test_transacao_e_somente_leitura(conexao_leitor):
    responder("?", ModeloFalso("SELECT 1 FROM orgao LIMIT 1"), conexao_leitor, "...")
    assert conexao_leitor.read_only is True
