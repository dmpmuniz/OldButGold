# REFACTOR PLAN — OldButGold

> **Status:** Draft for review
> **Goal:** Align code with documentation, fix bugs, make release functional

---

## ⚖️ Decisão Arquitetural

Existem **duas abordagens** para resolver o doc-vs-code mismatch:

### Opção A: Refatorar código para seguir a documentação (src/hardware/, src/workflow/, etc.)
- **Prós:** Arquitetura limpa, módulos especializados, documentação vira verdade
- **Contras:** Semana de refatoração, risco de introduzir bugs em código funcional, zero valor para o usuário
- **Custo:** Muito alto

### Opção B: Alinhar documentação com o código + corrigir bugs críticos
- **Prós:** Rápido, preserva código funcional, foca no que quebra/atrapalha
- **Contras:** Arquitetura atual não é ideal (monolitos), dívida técnica permanece
- **Custo:** Baixo

### ✅ Recomendação: Opção B (Pragmática)

Código funciona. Reescrever por estética arquitetural é over-engineering. Corrigimos:
1. Bugs que **quebram** o runtime
2. Dados que **não chegam** ao usuário
- Release **não funcional**
3. Documentação **divergente**

---

## Fases de Execução

### Fase 1: Correções Críticas

| # | Tarefa | Arquivo | Risco |
|---|---|---|---|
| 1.1 | BUG-001: `_skip_remaining` → `_finish_remaining` | `obg/core/engine.py:92` | 🔴 Crash |
| 1.2 | BUG-002: Armazenar SMART Re-Collection | `obg/core/engine.py:130` | 🟡 Perda de dado |
| 1.3 | Validar que testes passam | `pytest tests/` | — |

### Fase 2: Release Funcional

| # | Tarefa | Risco |
|---|---|---|
| 2.1 | Criar `scripts/build.py` com lógica de bundle | 🔴 Release quebrado |
| 2.2 | Script deve copiar tools/ e lib/ para o release | 🔴 |
| 2.3 | Script deve gerar ZIP | — |

### Fase 3: Alinhamento de Documentação

| # | Documento | O que mudar |
|---|---|---|
| 3.1 | `PROJECT_STRUCTURE.md` | src/ → obg/, adicionar models/, utils/ |
| 3.2 | `ARCHITECTURE ANALYSIS.md` | Atualizar layer diagram e module deps |
| 3.3 | `ENGINEERING_GUIDELINES.md` | §3 Architecture: refletir estrutura real |
| 3.4 | `COMPLIANCE_AUDIT.md` | Atualizar com paths corretos |
| 3.5 | `RTM.md` | Verificar se RTMs apontam para arquivos corretos |

### Fase 4: Refatoração Pontual (Opcional)

| # | Tarefa | Motivação |
|---|---|---|
| 4.1 | Quebrar `ui/app.py` em `ui/screens/*.py` | 730+ linhas, difícil manutenção |
| 4.2 | Criar `obg/core/constants.py` para valores fixos | Separar do config.py |
| 4.3 | Melhorar tipagem em classify() e session.py | Qualidade |

### Fase 5: Verificação

| # | Tarefa |
|---|---|
| 5.1 | `pytest tests/` — 100% passando |
| 5.2 | `python -m obg --version` — executa sem erro |
| 5.3 | Revisão final dos docs alterados |

---

## Risco e Mitigação

| Risco | Probabilidade | Mitigação |
|---|---|---|
| BUG-001 causar crash em produção | Alta (100% se identity mismatch) | Fix imediato |
| Release não funcional | Alta (tools/ vazio) | Script de build na Fase 2 |
| Doc divergir de novo | Média | Adicionar verificação no release checklist |
| Refatoração quebrar teste | Baixa | Fase 5 valida tudo |

---

## Timeline Estimada

| Fase | Esforço | Depende de |
|---|---|---|
| Fase 1: Correções | 15 min | Nada |
| Fase 2: Release | 2-3h | Fase 1 |
| Fase 3: Docs | 1h | Nada |
| Fase 4: Refatoração | 4-6h | Fase 1 (opcional) |
| Fase 5: Verificação | 30 min | Todas |

**Total (obrigatório):** ~4h  
**Total (com refatoração):** ~10h

---

*Aprovado pelo Arquiteto. Pendente: revisão do usuário.*
