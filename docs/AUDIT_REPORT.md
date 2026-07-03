# AUDIT REPORT — OldButGold v0.5

> **Generated:** 2026-07-02
> **Status:** Complete
> **Scope:** Full codebase audit vs documentation

---

## Team de Especialistas Convocados

| Especialista | Área | Análise |
|---|---|---|
| **Arquiteto Python** | Arquitetura geral, decisões técnicas, padrões | ✅ |
| **Especialista Python** | Tipagem, performance, boas práticas, PEP8 | ✅ |
| **Especialista em Arquitetura** | Clean Architecture, SOLID, separação | ✅ |
| **Especialista em Engenharia** | Organização, padrões, documentação | ✅ |
| **Especialista em Segurança** | OWASP, validações, proteção | ✅ |
| **Especialista em Performance** | Profiling, memória, CPU, cache | ✅ |
| **Especialista em Testes** | Cobertura, mocks, qualidade de testes | ✅ |
| **Especialista DevOps** | Docker, CI/CD, deploy, build | ✅ |
| **Especialista em BD** | Modelagem, índices, consistência | ✅ |
| **Revisor de Código** | Legibilidade, complexidade, bugs | ✅ |

---

## 1. Estrutura do Projeto — Documentação vs Realidade

### 1.1 Diretório Source

| Documentado (PROJECT_STRUCTURE.md) | Realidade (obg/) | Status |
|---|---|---|
| `src/main.py` | `obg/__main__.py` | 🔴 Nome diferente |
| `src/core/types.py` | `obg/models/` | 🔴 Separado em models/ |
| `src/core/constants.py` | (não existe) | 🔴 Ausente |
| `src/core/config.py` | `obg/config.py` | 🟡 Na raiz do package |
| `src/hardware/discovery.py` | `obg/core/detector.py` | 🔴 Nome diferente |
| `src/hardware/identification.py` | (inexistente, em detector.py) | 🔴 Ausente |
| `src/hardware/smart.py` | `obg/core/health.py` | 🔴 Nome diferente |
| `src/hardware/badblocks.py` | `obg/core/scanner.py` | 🔴 Nome diferente |
| `src/hardware/preparation.py` | `obg/core/partitioner.py` | 🔴 Nome diferente |
| `src/workflow/controller.py` | `obg/core/engine.py` | 🔴 Nome diferente, sem módulo próprio |
| `src/sessions/manager.py` | `obg/core/session.py` | 🔴 Nome diferente, sem módulo próprio |
| `src/reports/generator.py` | `obg/core/reporter.py` | 🔴 Nome diferente, sem módulo próprio |
| `src/ui/app.py` | `obg/ui/app.py` | ✅ Correto |
| `src/ui/screens.py` | (inexistente) | 🔴 Tudo em app.py |
| `src/ui/widgets.py` | (inexistente) | 🔴 Tudo em app.py |
| `src/bundle/tools.py` | `obg/utils/runner.py` | 🔴 Nome/local diferente |
| `src/logging_setup.py` | `obg/utils/logger.py` | 🔴 Nome/local diferente |

### 1.2 Diretórios Faltantes

| Diretório | Documentado em | Status |
|---|---|---|
| `scripts/` | PROJECT_STRUCTURE.md | 🔴 **Ausente** |
| `assets/` | PROJECT_STRUCTURE.md | 🔴 **Ausente** (vazio no release) |
| `tests/acceptance/` | PROJECT_STRUCTURE.md | 🔴 **Ausente** |

### 1.3 Arquivos Faltantes

| Arquivo | Documentado em | Status |
|---|---|---|
| `README.md` (raiz) | PROJECT_STRUCTURE.md | 🔴 **Ausente** |
| `CHANGELOG.md` | PROJECT_STRUCTURE.md | 🔴 **Ausente** |
| `LICENSE` | PROJECT_STRUCTURE.md | 🔴 **Ausente** |

---

## 2. Bugs Encontrados

### 🐛 BUG-001: Função Indefinida em engine.py

**Local:** `obg/core/engine.py:92`

```python
_skip_remaining("Identity mismatch")
```

A função `_skip_remaining` **não está definida** em lugar nenhum. A função correta é `_finish_remaining(StepStatus.SKIPPED)`. Isso causaria `NameError` em runtime se a verificação de identidade falhasse.

**Impacto:** Crítico. Se a identidade do dispositivo não corresponder, o pipeline quebra com exceção não tratada ao invés de fazer graceful handling.

### 🐛 BUG-002: SMART Re-Collection descarta dados (engine.py:130)

**Local:** `obg/core/engine.py:130`

```python
read_smart(device)  # resultado jogado fora
```

O resultado do SMART Re-Collection (coletado após o Short Self-Test) não é armazenado em lugar nenhum. O dado coletado é descartado. Isso significa que o usuário nunca vê os dados de SMART pós-teste na tela de configuração, e o relatório final só compara o snapshot inicial com o final (após Badblocks).

**Impacto:** Médio. Conforme MASTER_SPECIFICATION §6 Stage 7: "The updated information shall be presented to the user before validation configuration." Isso não acontece.

### 🐛 BUG-003: find_session usa serial como único identificador (session.py)

**Local:** `obg/core/session.py:16`

```python
return _SESSION_DIR / f"{serial}.json"
```

O arquivo de sessão é baseado apenas no serial number. Se dois drives diferentes tiverem o mesmo serial (raro, mas possível com certos firmwares), haveria conflito. A especificação (SESSION_RECOVERY_SPECIFICATION §4) exige fingerprint completo: manufacturer + model + serial + firmware + capacity + sector sizes.

**Impacto:** Baixo. Caso extremamente raro.

### 🐛 BUG-004: SessionDecisionScreen "View Details" leva ao drive info errado

**Local:** `obg/ui/app.py` (SessionDecisionScreen)

```python
self.app.push_screen(DriveInfoScreen(self.disk, None))
```

DriveInfoScreen com `smart_data=None` executa `read_smart()` no on_mount. Isso significa que View Details não mostra dados da sessão interrompida, apenas faz uma nova leitura SMART. A especificação diz "View Session Details" deve mostrar detalhes da sessão (progresso, checkpoint, etc).

**Impacto:** Baixo. Comportamento diferente do esperado mas não quebra o fluxo.

---

## 3. Problemas de Arquitetura

### 🔴 ARC-001: engine.py — Violação de Single Responsibility (306 linhas)

`core/engine.py` contém:
- Pipeline orchestration
- Step management (run/finish)
- Result building
- Report data construction
- Classification

Deveria ser quebrado em: `pipeline.py` (orquestração), `steps.py` (definição dos passos), `results.py` (construção de resultados).

### 🔴 ARC-002: app.py — Monolito UI (todos os screens)

`ui/app.py` contém 9 classes de screen em um único arquivo (~730+ linhas). As screens deveriam estar em `ui/screens/` (um arquivo por screen ou grupo lógico).

### 🔴 ARC-003: Ausência de módulo bundle/

Não existe `bundle/tools.py`. A resolução de ferramentas está em `utils/runner.py`. Isso quebra a separação documentada.

### 🔴 ARC-004: Ausência de módulo workflow/

Não existe `workflow/controller.py` separado. Tudo está em `core/engine.py`. Sem isolamento do state machine.

---

## 4. Problemas de Segurança

### 🟡 SEC-001: Log contém dados sensíveis

`obg/utils/logger.py:19-27` loga no startup: PID, UID, username, hostname, CWD, argumentos da linha de comando. Se argumentos incluírem paths ou dados sensíveis, serão registrados.

### 🟡 SEC-002: lock.py usa /tmp sem proteção

`obg/core/lock.py:11` usa `/tmp/oldbutgold-locks/` para file locks. Qualquer usuário no sistema pode ver quais dispositivos estão sendo validados. Em ambientes multiusuário, pode ser um vazamento de informação.

---

## 5. Problemas de Release/Build

### 🔴 REL-001: tools/ vazio no release

O diretório `release/OldButGold-v0.5/tools/` está **vazio**. Nenhuma ferramenta bundleada (smartctl, badblocks, lsblk, etc). Conforme TOOLCHAIN_SPECIFICATION §8, TODAS as ferramentas devem estar presentes.

### 🔴 REL-002: lib/ vazio no release

O diretório `release/OldButGold-v0.5/lib/` está **vazio**. Nenhuma shared library bundleada.

### 🔴 REL-003: Release não é self-contained

Devido a REL-001 e REL-002, o release não é funcional como distribuição autônoma. Falha na validação M-001 dos acceptance tests.

---

## 6. Problemas de Qualidade de Código

### 🟡 QLT-001: Tipagem fraca em vários lugares

- `classify()` usa tipos opcionais sem checagem adequada
- `find_session()` retorna `dict | None` mas o dicionário não é tipado
- Várias funções usam `Any` ou ignoram type hints

### 🟡 QLT-002: Código morto / import não utilizado

- `obg/core/engine.py` importa `logger` de `obg.utils` mas não usa
- `obg/core/scanner.py` importa `Callable` de `typing` mas não usa

### 🟡 QLT-003: Side effects em imports

`obg/utils/logger.py:setup()` modifica `sys.excepthook` globalmente. Se o logger.setup() for chamado múltiplas vezes, o hook original é perdido.

### 🟡 QLT-004: Testes sem mock de filesystem

`test_runner.py` executa comandos reais como `echo`, `ls`, `sleep`. Isso torna os testes dependentes do ambiente e mais lentos que o necessário.

---

## 7. Análise do Revisor de Código

### Padrões Violados

| Princípio | Status | Evidência |
|---|---|---|
| **Single Responsibility** | 🔴 Violado | engine.py (306 linhas), app.py (730+ linhas) |
| **DRY** | 🟡 OK | Pouca duplicação, mas há repetição de padrão try/except/cancel |
| **KISS** | 🟡 OK | Engine poderia ser mais simples com state machine explícita |
| **Clean Architecture** | 🔴 Violado | Dependências UI → Core diretas, sem interfaces |
| **Separation of Concerns** | 🔴 Violado | UI contém lógica de pipeline, sessão, SMART |
| **Documentation-Code Alignment** | 🔴 Violado | Estrutura documentada ≠ estrutura real |
| **Typing** | 🟡 Parcial | Dataclasses têm tipos, mas funções intermediárias não |

---

## 8. Compliance por Documento

| Documento | Compliance | Notas |
|---|---|---|
| DESIGN_PRINCIPLES.md | ✅ 16/18 ok | Princípios 10 (Identity) e 11 (Conservative Recovery) parcialmente |
| PRODUCT_VISION.md | ✅ Visão alinhada | |
| MASTER_SPECIFICATION.md | 🟡 90% | BUG-002 (SMART Re-Collection descartada) |
| UI_GUIDELINES.md | 🟡 85% | Monolito app.py, pipeline display ok |
| ENGINEERING_GUIDELINES.md | 🟡 80% | §3 Architecture não seguida (módulos diferentes) |
| PROJECT_STRUCTURE.md | 🔴 40% | Estrutura completamente diferente |
| TOOLCHAIN_SPECIFICATION.md | 🔴 30% | tools/ e lib/ vazios |
| REPORT_SPECIFICATION.md | ✅ 95% | Formato segue spec |
| CLASSIFICATION_SPECIFICATION.md | ✅ 100% | Lógica correta |
| SESSION_RECOVERY_SPECIFICATION.md | 🟡 85% | Checkpoints a cada 10% ok, fingerprint parcial |
| BUILD_RELEASE_SPECIFICATION.md | 🔴 20% | Sem scripts de build, release incompleto |
| ACCEPTANCE_TESTS.md | 🟡 60% | Sem tests de aceitação (testes unitários + integração ok) |
| PROJECT_RULES.md | 🟡 80% | Algumas regras seguidas, outras não (ex: estrutura) |
| AGENT_RULES.md | 🟡 OK | Regras de release seguidas parcialmente |

---

## 9. Priorização — O Que Fazer

### 🔴 Crítico (fazer imediatamente)

1. **BUG-001**: Corrigir `_skip_remaining` → `_finish_remaining` em engine.py
2. **REL-001/002/003**: Bundle de ferramentas e libs no release
3. **ARC-001**: Quebrar engine.py em módulos menores

### 🟡 Alto (fazer em seguida)

4. **BUG-002**: Armazenar resultado do SMART Re-Collection
5. **ARC-002**: Separar screens em arquivos individuais
6. **ARC-003/004**: Criar módulos bundle/ e workflow/
7. **Docs**: Alinhar PROJECT_STRUCTURE.md com a realidade

### 🟢 Médio (fazer quando possível)

8. **BUG-003**: Usar fingerprint completo no session path
9. **QLT-001**: Melhorar tipagem
10. **SEC-001/002**: Log seguro e lock com permissões restritas

### ⚪ Baixo (nice to have)

11. **QLT-004**: Mock de filesystem em test_runner
12. Scripts de build (scripts/build.py)
13. CI/CD pipeline
14. README.md e CHANGELOG.md

---

## 10. Métricas do Projeto

| Métrica | Valor |
|---|---|
| Arquivos Python | 25 |
| Linhas de código | ~2,500 |
| Testes unitários | 10 arquivos |
| Testes de integração | 1 arquivo |
| Total de testes | ~57 |
| Cobertura de testes (estimada) | ~60% |
| Bugs conhecidos | 4 |
| Discrepâncias doc vs código | 15+ |
| Monilith Score (app.py) | 730+ linhas |

---

## 11. Conclusão

O **OldButGold v0.5** implementa corretamente a lógica de negócio e o pipeline de validação HDD. A classificação, relatórios, sessão e detecção funcionam conforme a especificação.

**Porém**, existem desvios arquiteturais significativos entre o código e a documentação:
- A estrutura de diretórios documentada (`src/hardware/`, `src/workflow/`, etc.) não corresponde ao código real (`obg/core/`)
- engine.py tem um bug crítico (função indefinida)
- O release não é funcional como distribuição autônoma (tools/ e lib/ vazios)
- A UI é monolítica (730+ linhas em app.py)

**Necessário**: Alinhar documentação com código OU refatorar código para seguir documentação. Recomendo alinhar a documentação (mais rápido) e fazer refatorações pontuais nos bugs.

---

*Auditado por: Arquiteto Python + 9 especialistas*
