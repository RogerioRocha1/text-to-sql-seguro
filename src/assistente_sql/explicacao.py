"""Explica em português simples o que a consulta SQL faz.

A explicação é montada a partir da árvore do SQLGlot do SQL que vai ao banco,
e não pedida ao modelo. Assim ela descreve exatamente a consulta executada
(inclusive quando o modelo errou, o que ajuda o usuário a perceber o erro),
não aumenta o tempo de resposta e pode ser testada sem o Ollama.

O que a explicação não sabe descrever vira um aviso para conferir o SQL, em
vez de um texto inventado.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from assistente_sql.validador import DIALETO, LIMITE_PADRAO

TABELAS = {
    "execucao_mensal": "a execução mensal da despesa (valores empenhados, liquidados e pagos)",
    "orcamento": "o orçamento anual (valores previstos e realizados)",
    "orgao": "a lista de órgãos",
    "funcao": "as funções de governo",
    "subfuncao": "as subfunções",
    "programa_acao": "os programas e ações",
}

# Nome de coluna -> como o usuário entende. Colunas "nome" dependem da tabela.
COLUNAS = {
    "ano": "ano",
    "mes": "mês",
    "valor_pago": "valor pago",
    "valor_empenhado": "valor empenhado",
    "valor_liquidado": "valor liquidado",
    "valor_inicial": "orçamento inicial",
    "valor_atualizado": "orçamento atualizado",
    "valor_realizado": "valor realizado",
    "valor_restos_a_pagar_inscritos": "restos a pagar inscritos",
    "valor_restos_a_pagar_cancelados": "restos a pagar cancelados",
    "valor_restos_a_pagar_pagos": "restos a pagar pagos",
    "nome_orgao_superior": "ministério ou poder",
    "codigo_orgao_superior": "código do ministério ou poder",
    "codigo_orgao": "código do órgão",
    "codigo_funcao": "código da função",
    "codigo_subfuncao": "código da subfunção",
    "codigo_programa": "código do programa",
    "codigo_acao": "código da ação",
    "nome_programa": "programa",
    "nome_acao": "ação",
    "nome_unidade_gestora": "unidade gestora",
    "codigo_unidade_gestora": "código da unidade gestora",
    "nome_unidade_orcamentaria": "unidade orçamentária",
    "codigo_unidade_orcamentaria": "código da unidade orçamentária",
    "uf": "estado (UF)",
    "municipio": "município",
    "categoria_economica": "categoria econômica",
    "grupo_despesa": "grupo de despesa",
    "elemento_despesa": "elemento de despesa",
    "modalidade_despesa": "modalidade de aplicação",
    "com_emenda": "emenda parlamentar",
}
NOME_POR_TABELA = {
    "orgao": "órgão",
    "funcao": "função",
    "subfuncao": "subfunção",
    "programa_acao": "programa",
}
CODIGO_POR_TABELA = {
    "orgao": "código do órgão",
    "funcao": "código da função",
    "subfuncao": "código da subfunção",
}

MESES = (
    "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro"
).split()

AGREGACOES = {
    exp.Sum: "soma do {}",
    exp.Avg: "média do {}",
    exp.Max: "maior {}",
    exp.Min: "menor {}",
}

COMPARACOES = {
    exp.EQ: "é",
    exp.NEQ: "é diferente de",
    exp.GT: "é maior que",
    exp.GTE: "é maior ou igual a",
    exp.LT: "é menor que",
    exp.LTE: "é menor ou igual a",
}

CONFIRA = "uma condição mais técnica (confira no SQL)"


@dataclass(frozen=True)
class Explicacao:
    passos: tuple[str, ...]
    completa: bool = True  # False quando algum trecho virou "confira no SQL"

    @property
    def texto(self) -> str:
        return "\n".join(f"- {passo}" for passo in self.passos)


@dataclass
class _Contexto:
    apelidos: dict[str, str] = field(default_factory=dict)  # apelido -> tabela
    tabelas: list[str] = field(default_factory=list)
    calculos: dict[str, str] = field(default_factory=dict)  # apelido da coluna -> descrição
    mostradas: list[str] = field(default_factory=list)  # descrição de cada coluna do SELECT
    completa: bool = True


def explicar(sql: str | None, limite_padrao: int = LIMITE_PADRAO) -> Explicacao | None:
    """Explica o SQL em passos curtos. Devolve None se não conseguir ler a consulta."""
    if not sql:
        return None
    try:
        arvore = sqlglot.parse_one(sql, read=DIALETO)
    except SqlglotError:
        return None

    passos: list[str] = []
    contexto = _Contexto()
    if arvore.args.get("with_"):
        passos.append("Primeiro monta uma tabela intermediária e depois consulta sobre ela.")
        contexto.completa = False
    if isinstance(arvore, exp.SetOperation):
        passos.append("Junta o resultado de mais de uma consulta (confira no SQL).")
        return Explicacao(tuple(passos), completa=False)
    if not isinstance(arvore, exp.Select):
        return None

    _ler_tabelas(arvore, contexto)
    passos.append(_fonte(contexto))
    passos.append(_colunas(arvore, contexto))

    filtros = [_condicao(c, contexto) for c in _partes_and(arvore.args.get("where"))]
    if filtros:
        passos.append("Considera só os registros em que " + _lista(filtros) + ".")

    agrupamento = arvore.args.get("group")
    if agrupamento:
        nomes = [_valor(e, contexto) for e in agrupamento.expressions]
        passos.append("Calcula separadamente para cada " + _lista(nomes) + ".")

    filtros_grupo = [_condicao(c, contexto) for c in _partes_and(arvore.args.get("having"))]
    if filtros_grupo:
        passos.append(
            "Depois do cálculo, mantém só os grupos em que " + _lista(filtros_grupo) + "."
        )

    ordem = arvore.args.get("order")
    if ordem:
        passos.append(_ordem(ordem, contexto))

    if not _uma_linha_so(arvore):
        passos.append(_limite(arvore, limite_padrao, ordenado=bool(ordem)))
    return Explicacao(tuple(p for p in passos if p), completa=contexto.completa)


def _uma_linha_so(arvore: exp.Select) -> bool:
    """Total sem agrupamento: o limite de segurança não muda nada e só confundiria."""
    return not arvore.args.get("group") and all(
        c.find(exp.AggFunc) is not None for c in arvore.expressions
    )


def _ler_tabelas(arvore: exp.Select, contexto: _Contexto) -> None:
    for tabela in arvore.find_all(exp.Table):
        nome = tabela.name
        if nome not in contexto.tabelas:
            contexto.tabelas.append(nome)
        contexto.apelidos[tabela.alias_or_name] = nome
        contexto.apelidos[nome] = nome


def _fonte(contexto: _Contexto) -> str:
    principais = [t for t in contexto.tabelas if t in ("execucao_mensal", "orcamento")]
    outras = [t for t in contexto.tabelas if t not in principais]
    ordem = principais + outras
    if not ordem:
        return "Não consulta nenhuma tabela."
    descricoes = [TABELAS.get(t, t) for t in ordem]
    frase = f"Consulta {descricoes[0]}"
    if len(descricoes) > 1:
        frase += ", cruzando com " + _lista(descricoes[1:])
    return frase + "."


def _colunas(arvore: exp.Select, contexto: _Contexto) -> str:
    descricoes = []
    for coluna in arvore.expressions:
        alvo = coluna.this if isinstance(coluna, exp.Alias) else coluna
        descricao = _valor(alvo, contexto)
        if isinstance(coluna, exp.Alias):
            contexto.calculos[coluna.alias] = descricao
        descricoes.append(descricao)
    contexto.mostradas = descricoes
    inicio = "Mostra, sem repetir linhas: " if arvore.args.get("distinct") else "Mostra: "
    return inicio + _lista(descricoes) + "."


def _valor(no: exp.Expression, contexto: _Contexto) -> str:
    """Descreve uma coluna, uma agregação ou um cálculo simples."""
    if isinstance(no, exp.Paren):
        return _valor(no.this, contexto)
    if isinstance(no, exp.Star):
        return "todas as colunas"
    if isinstance(no, exp.Column):
        return _coluna(no, contexto)
    if isinstance(no, exp.Count):
        alvo = no.this
        if isinstance(alvo, exp.Distinct):
            nomes = [_valor(e, contexto) for e in alvo.expressions]
            return "quantidade de " + _lista(nomes) + " diferentes"
        if alvo is None or isinstance(alvo, exp.Star):
            return "quantidade de registros"
        return "quantidade de registros com " + _valor(alvo, contexto)
    for tipo, modelo in AGREGACOES.items():
        if isinstance(no, tipo):
            return modelo.format(_valor(no.this, contexto))
    if isinstance(no, exp.Round):
        return _valor(no.this, contexto) + " (arredondado)"
    if isinstance(no, (exp.Coalesce, exp.Nullif)):
        return _valor(no.this, contexto)
    if isinstance(no, (exp.Cast, exp.TryCast)):
        return _valor(no.this, contexto)
    if isinstance(no, exp.Sub):
        return f"diferença entre {_valor(no.left, contexto)} e {_valor(no.right, contexto)}"
    if isinstance(no, exp.Add):
        return f"{_valor(no.left, contexto)} mais {_valor(no.right, contexto)}"
    if isinstance(no, exp.Div):
        if isinstance(no.right, exp.Literal) or _literal_numerico(no.left):
            return f"{_valor(no.left, contexto)} dividido por {_valor(no.right, contexto)}"
        return f"proporção entre {_valor(no.left, contexto)} e {_valor(no.right, contexto)}"
    if (
        isinstance(no, exp.Mul)
        and _e_cem(no.right)
        and isinstance(_sem_parenteses(no.left), exp.Div)
    ):
        divisao = _sem_parenteses(no.left)
        return (
            f"percentual de {_valor(divisao.left, contexto)} "
            f"em relação a {_valor(divisao.right, contexto)}"
        )
    if isinstance(no, exp.Mul):
        return f"{_valor(no.left, contexto)} vezes {_valor(no.right, contexto)}"
    if isinstance(no, exp.Literal):
        return _literal(no)
    if isinstance(no, exp.Boolean):
        return "verdadeiro" if no.this else "falso"
    contexto.completa = False
    return "um cálculo (confira no SQL)"


def _coluna(no: exp.Column, contexto: _Contexto) -> str:
    nome = no.name
    if not no.table and nome in contexto.calculos:  # apelido definido no SELECT
        return contexto.calculos[nome]
    tabela = contexto.apelidos.get(no.table) if no.table else _tabela_da_coluna(nome, contexto)
    if nome == "nome" and tabela in NOME_POR_TABELA:
        return NOME_POR_TABELA[tabela]
    if nome == "codigo" and tabela in CODIGO_POR_TABELA:
        return CODIGO_POR_TABELA[tabela]
    return COLUNAS.get(nome, nome.replace("_", " "))


def _tabela_da_coluna(nome: str, contexto: _Contexto) -> str | None:
    """Sem prefixo, ``nome``/``codigo`` só são ambíguos se houver mais de uma dimensão."""
    if nome not in ("nome", "codigo"):
        return None
    candidatas = [t for t in contexto.tabelas if t in NOME_POR_TABELA]
    return candidatas[0] if len(candidatas) == 1 else None


def _partes_and(no: exp.Expression | None) -> list[exp.Expression]:
    if no is None:
        return []
    if isinstance(no, (exp.Where, exp.Having)):
        return _partes_and(no.this)
    if isinstance(no, exp.Paren) and isinstance(no.this, exp.And):
        return _partes_and(no.this)
    if isinstance(no, exp.And):
        return _partes_and(no.left) + _partes_and(no.right)
    return [no]


def _condicao(no: exp.Expression, contexto: _Contexto) -> str:
    if isinstance(no, exp.Paren):
        return _condicao(no.this, contexto)
    if isinstance(no, exp.Or):
        partes = _partes_or(no)
        return "(" + " ou ".join(_condicao(p, contexto) for p in partes) + ")"
    if isinstance(no, exp.Not):
        if isinstance(no.this, exp.Is):
            return _condicao_is(no.this, contexto, negada=True)
        return "não vale que " + _condicao(no.this, contexto)
    if isinstance(no, exp.Is):
        return _condicao_is(no, contexto)
    if isinstance(no, (exp.ILike, exp.Like)):
        return _condicao_texto(no, contexto)
    if isinstance(no, exp.In):
        valores = [_valor(v, contexto) for v in no.expressions]
        if valores:
            return f"{_valor(no.this, contexto)} é um destes: {', '.join(valores)}"
    if isinstance(no, exp.Between):
        inicio, fim = no.args["low"], no.args["high"]
        return (
            f"{_valor(no.this, contexto)} está entre "
            f"{_literal_da_coluna(no.this, inicio, contexto)} e "
            f"{_literal_da_coluna(no.this, fim, contexto)}"
        )
    for tipo, verbo in COMPARACOES.items():
        if isinstance(no, tipo):
            esquerda, direita = no.left, no.right
            if _e_coluna(esquerda, "com_emenda") and isinstance(direita, exp.Boolean):
                return _emenda(direita.this == (tipo is exp.EQ))
            if isinstance(esquerda, exp.Column) and isinstance(direita, exp.Column):
                break  # comparação entre colunas: difícil de explicar sem jargão
            return (
                f"{_valor(esquerda, contexto)} {verbo} "
                f"{_literal_da_coluna(esquerda, direita, contexto)}"
            )
    if _e_coluna(no, "com_emenda"):  # WHERE com_emenda
        return _emenda(True)
    contexto.completa = False
    return CONFIRA


def _partes_or(no: exp.Expression) -> list[exp.Expression]:
    if isinstance(no, exp.Paren) and isinstance(no.this, exp.Or):
        return _partes_or(no.this)
    if isinstance(no, exp.Or):
        return _partes_or(no.left) + _partes_or(no.right)
    return [no]


def _condicao_is(no: exp.Is, contexto: _Contexto, negada: bool = False) -> str:
    alvo, valor = no.this, no.expression
    negada = negada != bool(no.args.get("negate"))  # IS NOT vem como Is(negate=True)
    if _e_coluna(alvo, "com_emenda") and isinstance(valor, exp.Boolean):
        return _emenda(valor.this != negada)
    if isinstance(valor, exp.Null):
        return f"{_valor(alvo, contexto)} {'foi' if negada else 'não foi'} informado"
    contexto.completa = False
    return CONFIRA


def _condicao_texto(no: exp.Expression, contexto: _Contexto) -> str:
    alvo = no.this
    while isinstance(alvo, (exp.Anonymous, exp.Lower, exp.Upper)) and alvo.expressions[:1]:
        alvo = alvo.expressions[0]  # unaccent(x), lower(x)
    if isinstance(alvo, (exp.Lower, exp.Upper)):
        alvo = alvo.this
    padrao = _texto_do_padrao(no.expression)
    if padrao is None:
        contexto.completa = False
        return CONFIRA
    termo = padrao.strip("%")
    sem_caixa = " (sem diferenciar maiúsculas" + (
        " e acentos)" if "unaccent" in no.sql(dialect=DIALETO).lower() else ")"
    )
    if not isinstance(no, exp.ILike) and "unaccent" not in no.sql(dialect=DIALETO).lower():
        sem_caixa = ""
    nome = _valor(alvo, contexto)
    if "%" in termo or "_" in termo:
        return f"{nome} segue o padrão “{padrao}”{sem_caixa}"
    if padrao.startswith("%") and padrao.endswith("%"):
        return f"{nome} contém “{termo}”{sem_caixa}"
    if padrao.endswith("%"):
        return f"{nome} começa com “{termo}”{sem_caixa}"
    if padrao.startswith("%"):
        return f"{nome} termina com “{termo}”{sem_caixa}"
    return f"{nome} é “{termo}”{sem_caixa}"


def _texto_do_padrao(no: exp.Expression) -> str | None:
    while isinstance(no, exp.Anonymous) and no.expressions[:1]:
        no = no.expressions[0]  # unaccent('%saúde%')
    if isinstance(no, (exp.Lower, exp.Upper)):
        no = no.this
    if isinstance(no, exp.Literal) and no.is_string:
        return no.this
    return None


def _ordem(ordem: exp.Order, contexto: _Contexto) -> str:
    partes = []
    for item in ordem.expressions:
        nome = _valor(item.this, contexto)
        if _literal_numerico(item.this) and 0 < int(item.this.this) <= len(contexto.mostradas):
            nome = contexto.mostradas[int(item.this.this) - 1]  # ORDER BY 2
        decrescente = bool(item.args.get("desc"))
        if nome in ("mês", "ano"):
            partes.append(f"{nome} ({'do último para o primeiro' if decrescente else 'em ordem'})")
        elif nome in NOME_POR_TABELA.values() or nome in ("estado (UF)", "município"):
            partes.append(f"{nome} ({'de Z a A' if decrescente else 'em ordem alfabética'})")
        else:
            partes.append(
                f"{nome} ({'do maior para o menor' if decrescente else 'do menor para o maior'})"
            )
    return "Ordena por " + _lista(partes) + "."


def _limite(arvore: exp.Select, limite_padrao: int, ordenado: bool) -> str:
    limite = arvore.args.get("limit")
    if limite is None:
        return ""
    try:
        quantidade = int(limite.expression.this)
    except (AttributeError, TypeError, ValueError):
        return "Limita o número de linhas mostradas."
    if quantidade >= limite_padrao:
        return f"Mostra no máximo {quantidade:,} linhas (limite de segurança).".replace(",", ".")
    if ordenado:
        return (
            f"Fica só com os {quantidade} primeiros."
            if quantidade > 1
            else "Fica só com o primeiro."
        )
    return f"Mostra só {quantidade} linha(s)."


def _literal_da_coluna(coluna: exp.Expression, no: exp.Expression, contexto: _Contexto) -> str:
    """Valor comparado com a coluna; mês 12 vira "dezembro"."""
    if _e_coluna(coluna, "mes") and isinstance(no, exp.Literal) and not no.is_string:
        try:
            return MESES[int(no.this) - 1]
        except (ValueError, IndexError):
            pass
    if isinstance(no, exp.Literal):
        return _literal(no)
    return _valor(no, contexto)


def _literal(no: exp.Literal) -> str:
    return f"“{no.this}”" if no.is_string else no.this


def _sem_parenteses(no: exp.Expression) -> exp.Expression:
    while isinstance(no, exp.Paren):
        no = no.this
    return no


def _e_cem(no: exp.Expression) -> bool:
    return _literal_numerico(no) and no.this in ("100", "100.0")


def _literal_numerico(no: exp.Expression) -> bool:
    return isinstance(no, exp.Literal) and not no.is_string


def _e_coluna(no: exp.Expression, nome: str) -> bool:
    return isinstance(no, exp.Column) and no.name == nome


def _emenda(com: bool) -> str:
    return (
        "a despesa veio de emenda parlamentar"
        if com
        else "a despesa não veio de emenda parlamentar"
    )


def _lista(itens: list[str]) -> str:
    itens = [i for i in itens if i]
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]
