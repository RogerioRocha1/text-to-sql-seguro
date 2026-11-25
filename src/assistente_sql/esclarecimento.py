"""Pergunta ao usuário quando a pergunta é ambígua em relação ao esquema.

O banco guarda várias medidas para a mesma ideia: "gasto" pode ser o valor
empenhado, o liquidado ou o pago; "orçamento" pode ser o inicial ou o
atualizado. Em vez de deixar o modelo escolher em silêncio, o assistente
pergunta antes de gerar o SQL.

As regras são poucas, explícitas e conservadoras: só disparam quando a
pergunta não diz qual medida quer. Elas rodam antes do modelo, então não
gastam tempo de GPU e podem ser testadas sem o Ollama. Quando o usuário
escolhe uma opção, o complemento é somado à pergunta original, e a pergunta
resultante já não dispara a mesma regra.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

ANO_DOS_DADOS = 2025


@dataclass(frozen=True)
class Opcao:
    rotulo: str  # texto do botão
    complemento: str  # somado à pergunta quando o usuário escolhe a opção


@dataclass(frozen=True)
class Esclarecimento:
    regra: str  # identificador curto, vai para o log e para a avaliação
    pergunta: str  # o que o assistente pergunta ao usuário
    opcoes: tuple[Opcao, ...]

    def aplicar(self, pergunta_original: str, opcao: Opcao) -> str:
        """Pergunta reescrita com a escolha do usuário."""
        if self.regra == "ano_indisponivel":
            return _ANO.sub(str(ANO_DOS_DADOS), pergunta_original)
        return f"{pergunta_original.rstrip(' ?')} ({opcao.complemento})?"


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def _tem(texto: str, padrao: str) -> bool:
    return re.search(padrao, texto) is not None


_ANO = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")

# "gasto", "gastou", "gastos", "aplicou", "destinou", "custou"...
_GASTO = r"\b(gast\w*|aplic(ou|aram|ado|ados|ada|adas)|destin(ou|aram|ado|ados)|cust(ou|aram))\b"
# medidas que respondem "qual valor": se aparecer uma, a pergunta já escolheu
_MEDIDA_EXECUCAO = r"\b(pag\w*|empenh\w*|liquid\w*|realizad\w*|executad\w*|restos)\b"
_MEDIDA_ORCAMENTO = r"\b(orcament\w*|orcad\w*|previst\w*|autorizad\w*|dotac\w*)\b"
_TIPO_ORCAMENTO = r"\b(inicia\w*|atualizad\w*|autorizad\w*|loa|lei orcamentaria|aprovad\w*)\b"


def verificar(pergunta: str) -> Esclarecimento | None:
    """Devolve o esclarecimento a pedir ao usuário, ou None se a pergunta é clara."""
    texto = _normalizar(pergunta)

    anos = {int(a) for a in _ANO.findall(texto)}
    if anos and ANO_DOS_DADOS not in anos:
        lista = ", ".join(str(a) for a in sorted(anos))
        return Esclarecimento(
            "ano_indisponivel",
            f"Os dados carregados são só de {ANO_DOS_DADOS}, e a pergunta fala de {lista}. "
            f"Quer a resposta para {ANO_DOS_DADOS}?",
            (Opcao(f"Sim, usar {ANO_DOS_DADOS}", str(ANO_DOS_DADOS)),),
        )

    medida_execucao = _tem(texto, _MEDIDA_EXECUCAO)
    medida_orcamento = _tem(texto, _MEDIDA_ORCAMENTO)

    if _tem(texto, _GASTO) and not (medida_execucao or medida_orcamento):
        return Esclarecimento(
            "medida_de_gasto",
            "“Gasto” pode ser medido de formas diferentes. Qual valor você quer?",
            (
                Opcao("Valor pago (dinheiro que saiu)", "considere o valor pago"),
                Opcao(
                    "Valor empenhado (reservado para pagar)",
                    "considere o valor empenhado",
                ),
                Opcao(
                    "Valor liquidado (serviço ou bem entregue)",
                    "considere o valor liquidado",
                ),
            ),
        )

    if medida_orcamento and not _tem(texto, _TIPO_ORCAMENTO) and not medida_execucao:
        return Esclarecimento(
            "tipo_de_orcamento",
            "O orçamento tem dois valores previstos. Qual você quer?",
            (
                Opcao(
                    "Inicial (aprovado na Lei Orçamentária)",
                    "considere o orçamento inicial",
                ),
                Opcao(
                    "Atualizado (depois de créditos e cortes)",
                    "considere o orçamento atualizado",
                ),
            ),
        )
    return None
