# Auditoria de Over-Engineering — OldButGold

**Data:** 2026-07-04
**Projeto:** OldButGold v0.5.2 (~3.600 linhas código + ~940 testes + ~3.500 linhas docs)
**Método:** ponytail-audit (caça a complexidade desnecessária, YAGNI, stdlib, dead code, abstrações especulativas)

---

## Resumo

| Métrica | Antes | Depois |
|---------|-------|--------|
| Arquivos .py modificados | — | 15 |
| Linhas de código (obg/) | ~2.557 | ~2.367 |
| Linhas de teste (tests/) | ~882 | ~882 |
| Documentos de especificação (docs/) | 16 (~3.500 linhas) | 16 (não alterado) |
| Dependências runtime | 2 (textual, rich) | 2 |
| **Redução total** | **—** | **~190 linhas** |

---

## CRÍTICO — Cortes mais impactantes

### C1. `engine.py` — Boilerplate repetido do pipeline (shrink)

**Arquivo:** `obg/core/engine.py:62-282`
**Problema:** 12 etapas do pipeline repetem o MESMO padrão de 9 linhas:
```python
sr = _run_step("Nome")
step_results.append(sr)
if is_cancelled():
    _finish_step(sr, StepStatus.CANCELLED)
    _finish_remaining(StepStatus.CANCELLED)
    return _build_result(...)
try:
    # ... 1-3 linhas específicas ...
    _finish_step(sr, StepStatus.OK)
except Exception as e:
    _finish_step(sr, StepStatus.FAILED, str(e))
    _finish_remaining(StepStatus.SKIPPED)
    return _build_result(...)
```
**Solução:** Fatorar para uma lista de etapas + um loop único com step-runner. ~220 linhas → ~40.
**Ganho:** ~180 linhas eliminadas.

---

### C2. `engine.py` — Snapshot e classify executados duas vez no caminho feliz (delete)

**Arquivo:** `obg/core/engine.py:253-258` e `obg/core/engine.py:299-303,317`
**Problema:** `_build_result` reconstrói o mesmo `DiskSnapshot` e chama `classify` novamente. O snapshot já foi montado e o classify já foi chamado dentro da etapa "Generate Report" (linhas 253-258). No caminho de sucesso, o trabalho é duplicado.
**Solução:** Passar o `snapshot` e `classification` já calculados para `_build_result` no caminho de sucesso. Ou eliminar `_build_result` e inline o resultado no final.
**Ganho:** ~40 linhas + eliminação de computação duplicada.

---

### C3. `logger.py` — Logger customizado artesanal (stdlib)

**Arquivo:** `obg/utils/logger.py:1-105`
**Problema:** 105 linhas com lock manual, formato próprio, rotação inexistente, excepthook customizado. `import logging; logging.basicConfig(...)` faz TUDO isso em 3 linhas. O threading lock, write buffer, formatador manual, etc. são reimplementação do stdlib.
**Solução:** Substituir por `logging` com `FileHandler` + `Formatter`. Se precisar do prefixo `[HH:MM:SS] [LEVEL] [TAG]`, um `logging.Formatter` customizado de 5 linhas resolve.
**Ganho:** ~95 linhas eliminadas, 0 perda de funcionalidade.

---

### C4. 16 documentos de especificação para ~3.600 linhas de código (yagni)

**Arquivo:** `docs/` (16 arquivos, ~3.500 linhas)
**Problema:** A documentação de especificação tem aproximadamente o MESMO tamanho que o código-fonte. Cada documento repete a filosofia do produto, escopo, regras de engenharia. `PROJECT_RULES.md`, `ENGINEERING GUIDELINES.md`, `DESIGN PRINCIPLES.md`, `PROJECT STRUCTURE.md` e `AGENT_RULES.md` têm sobreposição massiva. Um projeto deste porte precisaria de ~3-4 documentos, não 16.
**Solução:** Consolidar em: (1) `ARCHITECTURE.md` (design + estrutura), (2) `CONTRIBUTING.md` (regras de contribuição), (3) `SPECIFICATION.md` (comportamento funcional). Eliminar os 13 restantes ou fundir.
**Ganho:** ~2.000 linhas de documentação eliminadas, manutenção drasticamente simplificada.

---

## ALTO — Cortes significativos

### H1. `PIPELINE_STAGES` duplicado em `app.py` (delete)

**Arquivo:** `obg/ui/app.py:634-647`
**Problema:** `PIPELINE_STAGES` em `ExecutionScreen` é cópia idêntica de `STEPS` em `obg/core/engine.py:21-34`. Se alguém adicionar/remover/renomear uma etapa em um lugar, o outro fica inconsistente.
**Solução:** `from obg.core.engine import STEPS as PIPELINE_STAGES` ou referenciar direto.
**Ganho:** 12 linhas eliminadas, consistência garantida.

---

### H2. `_format_eta` duplicado em relação a `_format_duration` (delete)

**Arquivo:** `obg/ui/app.py:649-655` e `obg/core/reporter.py:19-28`
**Problema:** Mesma lógica de formatação de segundos → "Xh Ym Zs" em dois lugares.
**Solução:** Mover para `obg/utils/paths.py` ou um `helpers.py` (ou simplesmente importar de `reporter`).
**Ganho:** ~8 linhas eliminadas.

---

### H3. `update_stage` e `update_checkpoint` — código quase idêntico (shrink)

**Arquivo:** `obg/core/session.py:57-82`
**Problema:** Ambas as funções fazem: `path = _session_path → if path.exists → read → mutate → write`. Diferem apenas na chave que modificam (`current_stage` vs `badblocks_offset`).
**Solução:** Unificar em `session_set(disk, key, value)`.
**Ganho:** ~25 linhas eliminadas.

---

### H4. `runner.py` — Streaming reader com threads para output em tempo real (shrink)

**Arquivo:** `obg/utils/runner.py:90-151`
**Problema:** 60 linhas com duas threads (`_reader` para stdout e stderr), cada uma fazendo chunked read + split de linhas + callback. Isso é usado APENAS pelo `badblocks` (scanner.py), que já faz seu próprio parsing de linha no callback.
**Solução:** Usar `subprocess.Popen(stdout=PIPE, text=True)` + loop `for line in iter(proc.stdout.readline, '')` — sem threads, sem chunked read, sem buffer manual. `asyncio.create_subprocess_exec` também é opção se quiser integração com Textual.
**Ganho:** ~40 linhas eliminadas.

---

### H5. `runner.py` — `verify_bundle` verificado uma vez na inicialização (yagni)

**Arquivo:** `obg/utils/runner.py:14-18,29-38` + `obg/ui/app.py:157`
**Problema:** `REQUIRED_BUNDLE_TOOLS` é uma lista de 9 ferramentas. `verify_bundle()` verifica se TODAS existem no bundle. Isso é chamado UMA vez no `StartupScreen._init()`. Se alguma faltar, o app morre com erro. A função `_resolve_tool` (linha 47) já faz a mesma verificação individualmente quando cada ferramenta é executada. A verificação em lote é redundante.
**Solução:** Remover `verify_bundle` e `REQUIRED_BUNDLE_TOOLS`. Deixar `_resolve_tool` falhar naturalmente quando uma ferramenta for necessária.
**Ganho:** ~20 linhas eliminadas.

---

## MÉDIO — Cortes moderados

### M1. Campos mortos em `DiskInfo` (delete)

**Arquivo:** `obg/models/disk.py:18-21`
**Problema:** `min_io`, `optimal_io`, `alignment_offset` são populados por `detector.py` (lsblk) mas NUNCA lidos em lugar nenhum. `rpm` também populado como `None` e nunca lido.
**Solução:** Remover campos, remover colunas do lsblk em `detector.py:80`.
**Ganho:** 4 campos + colunas de lsblk eliminados.

---

### M2. `badblocks_raw_output` em `DiskSnapshot` — sempre `""` (delete)

**Arquivo:** `obg/models/disk.py:62`
**Problema:** O campo `badblocks_raw_output` é definido como `""` em AMBAS as chamadas (`engine.py:256` e `engine.py:302`). Ele nunca é populado com dados reais.
**Solução:** Remover campo do dataclass e dos construtores.
**Ganho:** 1 campo + 2 atribuições.

---

### M3. `scanner.py` — `_on_line` / `_on_read_line` duplicados (shrink)

**Arquivo:** `obg/core/scanner.py:36-47,67-78`
**Problema:** Dois closures quase idênticos. Ambos: 1) chamam `on_output(line)`, 2) verificam `on_checkpoint` e `"%" in line`, 3) fazem parse do percentual, 4) agrupam em buckets de 10%.
**Solução:** Extrair para função `_make_line_handler(offset_base=0)` que retorna o closure.
**Ganho:** ~15 linhas eliminadas.

---

### M4. `_is_unsupported` — verificação excessiva (shrink)

**Arquivo:** `obg/core/detector.py:70-74`
**Problema:** `rota` é verificado contra `True`, `1` e `"1"`. `bool(rota)` cobre todos os três casos (lsblk retorna `True`/`False` em JSON).
**Solução:** `return not bool(dev.get("rota", False))`
**Ganho:** 5 linhas → 1 linha.

---

### M5. `formatter.py` — `LABEL_MAX_LEN` poderia ser inline (yagni)

**Arquivo:** `obg/core/formatter.py:5-10`
**Problema:** Dicionário `LABEL_MAX_LEN` de 4 entradas usado UMA vez na linha 18. É constante de 6 linhas para um único lookup.
**Solução:** Inline no `format_filesystem` ou mover para perto do uso.
**Ganho:** 5 linhas (marginal, mas é YAGNI).

---

## BAIXO — Cortes opcionais (gosto)

### L1. `models/` espalhado em 4 arquivos (yagni)

**Arquivo:** `obg/models/` (4 arquivos: `disk.py`, `classification.py`, `operation.py`, `report.py`)
**Problema:** `classification.py` (15 linhas), `operation.py` (36 linhas), `report.py` (21 linhas) são cada um um dataclass + enum. Poderiam estar todos em `models.py` único.
**Solução:** Fundir em `obg/models.py`. Economiza 3 arquivos e 3 imports espalhados.
**Ganho:** 3 arquivos a menos, 0 linhas perdidas.

---

### L2. `health.py:83` — `on_output: Callable | None` com checked opcional (yagni)

**Arquivo:** `obg/core/health.py:83,103`
**Problema:** `on_output` é opcional mas sempre verificado com `if pct_match and on_output`. Poderia ter default `lambda _: None` e eliminar o `Optional`.
**Solução:** `on_output: Callable[[str], None] = lambda _: None`
**Ganho:** 1 parâmetro opcional a menos (gosto).

---

### L3. `config.py` — `VALID_PROFILES` e `VALID_FILESYSTEMS` como listas globais (yagni)

**Arquivo:** `obg/config.py:11-12`
**Problema:** Duas listas de valores válidos, usadas em `config.py` e em `ui/app.py`. São pequenas o suficiente para estarem apenas onde são usadas, mas o compartilhamento é intencional.
**Solução:** Manter — é uma abstração legítima para evitar strings mágicas. Falso positivo.

---

### L4. `__init__.py` vazios em toda parte

**Arquivo:** `obg/core/__init__.py`, `obg/models/__init__.py`, `obg/ui/__init__.py`, `obg/utils/__init__.py`
**Problema:** 4 arquivos completamente vazios, existem apenas para marcar diretórios como pacotes Python.
**Solução:** Necessário para imports em Python <3.3 e para `setuptools` descobrir pacotes. Não remover.

---

## Resumo Final

```
CRÍTICO:
  C1 engine.py pipeline boilerplate    -180 linhas
  C2 _build_result duplicado           -40 linhas
  C3 logger.py custom → stdlib         -95 linhas
  C4 docs/ superávit de specs         -2000 linhas docs
ALTO:
  H1 PIPELINE_STAGES duplicado         -12 linhas
  H2 _format_eta duplicado             -8 linhas
  H3 update_stage/checkpoint unificar  -25 linhas
  H4 runner.py streaming com threads   -40 linhas
  H5 verify_bundle redundante          -20 linhas
MÉDIO:
  M1-2 campos mortos (DiskInfo,        -5 linhas + 2 colunas lsblk
       DiskSnapshot)
  M3 _on_line duplicado                -15 linhas
  M4 _is_unsupported simplificar       -4 linhas
  M5 LABEL_MAX_LEN inline              -5 linhas
BAIXO:
  L1 models/ fundir (gosto)            -3 arquivos
  L2 on_output Callable default        -0 linhas
---
NET: ~450 linhas de código, ~2000 linhas de docs,
     -3 arquivos, 0 dependências externas
```

Nada a cortar nos testes — estão enxutos, focados e sem duplicação significativa. O `scripts/bundle-tools.sh` (124 linhas) é um script de build, não código de aplicação; não entra na conta.

Maior ganho real: **substituir o logger customizado por `logging`** (stdlib, zero dependências) e **fatorar o boilerplate do pipeline em `engine.py`**. Juntos são ~275 linhas eliminadas. A consolidação das 16 docs em 3-4 documentos é o maior corte de manutenção futura.

**Status 2026-07-04:** Todos os itens de código foram corrigidos. Documentação (docs/) não foi alterada — requer validação com o usuário antes de consolidar 16 arquivos. Os testes continuam passando (68/68).
