# Registro de uso de IA na programação

Regras da disciplina: pelo menos 10 interações relevantes até a entrega final. Cada registro traz o prompt, um resumo da resposta e a decisão do grupo (aceito, corrigido ou descartado), com o motivo. Código gerado por IA só entra na `main` com teste passando na CI e revisão de outro integrante.

**Ferramentas usadas:** _(listar aqui, por exemplo: Claude, GitHub Copilot para estudantes, Continue + Ollama)_

---

## 001 · Validador de SQL inicial

- **Data:** 28/10/2026
- **Integrante:** _(nome)_
- **Ferramenta:** Claude
- **Prompt (resumo):** pedido de um esqueleto de repositório para o Marco 1, com validador de SQL em SQLGlot, testes de ataques e CI no GitHub Actions.
- **Resposta (resumo):** validador que aceita só um `SELECT`, bloqueia DDL, DML e comandos do DuckDB, restringe tabelas a uma lista, bloqueia funções de leitura de arquivo e injeta `LIMIT`; 37 casos de teste.
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:** _(o que o grupo conferiu, o que mudou e por quê)_

---

## Modelo para novos registros

```markdown
## 00N · Título curto

- **Data:**
- **Integrante:**
- **Ferramenta:**
- **Prompt (resumo):**
- **Resposta (resumo):**
- **Decisão:** aceito / corrigido / descartado
- **Motivo e revisão:**
```
