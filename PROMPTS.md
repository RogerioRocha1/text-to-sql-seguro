# Registro de uso de IA na programação

Regras da disciplina: pelo menos 10 interações relevantes até a entrega final. Cada registro traz o prompt, um resumo da resposta e a decisão do grupo (aceito, corrigido ou descartado), com o motivo. Código gerado por IA só entra na `main` com teste passando na CI e revisão de outro integrante.

**Ferramentas usadas:** _(listar aqui, por exemplo: Claude, GitHub Copilot para estudantes, Continue + Ollama)_

---

## 001 · Validador de SQL inicial

- **Data:** 28/10/2026
- **Integrante:** _(Rogério Rocha)_
- **Ferramenta:** Claude
- **Prompt (resumo):** pedido de um esqueleto de repositório para o Marco 1, com validador de SQL em SQLGlot, testes de ataques e CI no GitHub Actions.
- **Resposta (resumo):** validador que aceita só um `SELECT`, bloqueia DDL, DML e comandos do DuckDB, restringe tabelas a uma lista, bloqueia funções de leitura de arquivo e injeta `LIMIT`; 37 casos de teste.
- **Decisão:** _(aceito / corrigido / descartado)_
- **Motivo e revisão:** _(o que o grupo conferiu, o que mudou e por quê)_

---

## 002 · Revisão geral do projeto - Marco 1

- **Data:*29/10/2026*
- **Integrante:** _(Rogério Rocha)_
- **Ferramenta:** Claude
- **Prompt (resumo):** Analise detalhada sobre toda a criação e edição dos arquivos PROMPTS.md e README.md 
- **Resposta (resumo):** Alterado adicionando nome dos envolvidos e seus papeis, edição do documento "Proposta Técnica - Assistente de Dados com Text-to-SQL Seguro" 
- **Decisão:** aceito / corrigido / descartado
- **Motivo e revisão:** (Detalhar mapeando os papeis de cada integrante do projeto, e complementando o que o Claude não preencheu)

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
