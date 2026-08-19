# TUI Redesign — OldButGold

**Date:** 2026-07-26
**Version:** 0.8.3 → target 0.9.0
**Scope:** Full TUI layout + navigation overhaul. No business logic changes.

---

## Global Rules (ALL screens MUST follow)

1. **Fixed terminal size:** `SCREEN_SIZE = (120, 40)` no `ObgApp`. Canvas travado — componentes NUNCA redimensionam com o terminal.
2. **Keyboard navigation:** `BINDINGS` com `priority=True` em cada Screen. Setas/Tab/Enter/Esc funcionam em TODAS as telas. NUNCA usar `on_key` solto — sempre binding nomeado.
3. **Mouse navigation:** `on_click` ou `on_button_pressed` em TODOS os botões. Hover com `:hover` CSS.
4. **Layout:** CSS Grid (`grid-size`, `grid-columns`, `grid-rows`) para estrutura. `content-align: center middle` em telas com conteúdo esparso.
5. **Padding/Spacing:** Consistente em toda a UI. `padding: 1 2` nos containers, `margin: 0 1` entre widgets.
6. **Cores:** Paleta fixa: fundo `#0a0a0a`, borda `#444`, texto `#ccc`, ok `#0f0`, warn `#ff0`, fail `#f00`, gold `#0f0 bold`, silver `#aaa bold`, bronze `#cd7f32 bold`.
7. **NUNCA** usar `except Exception: pass` sem um `log_error()` ou comentário.
8. **Footer** em TODAS as telas: mostra atalhos de teclado disponíveis.

---

## Tela 1 — StartupScreen

**Abordagem:** A (cosmética)

### O que manter
- Fluxo: init detecta discos → habilita Continue
- Legal disclaimer completo
- Continue desabilitado até init terminar

### O que adicionar
- Logo ASCII no topo (arte OldButGold em block letters)
- Footer com atalhos: `[←][→] Navigate  [Enter] Select  [Esc] Exit`

### Layout
```
┌──────────────────────────────────────────────┐
│ OldButGold v0.9.0  /  Startup                │
├──────────────────────────────────────────────┤
│                                              │
│               _   _       _                   │
│              | | | |     | |                  │
│              | |_| | ___ | |__               │
│              |  _  |/ _ \| '_ \              │
│              | | | | (_) | |_) |             │
│              \_| |_/\___/|_.__/              │
│                                              │
│         HDD Validation & Refurbishment        │
│                    Toolkit                    │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ Legal Disclaimer                       │  │
│  │ OldButGold performs hardware...        │  │
│  │ ...                                    │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Detected 3 drive(s). Ready.                 │
│                                              │
│  [  Continue  ]  [   Exit    ]               │
├──────────────────────────────────────────────┤
│  ←/→ Navigate  Enter Select  Esc Exit        │
└──────────────────────────────────────────────┘
```

---

## Tela 2 — DriveSelectionScreen

**Abordagem:** A (cosmética)

### O que manter
- Cards de disco com modelo, device, transporte, capacidade, avisos
- Sessão interrompida com % na label
- Navegação setas + Enter + clique
- Refresh com R

### O que adicionar
- Tab/Shift+Tab entre cards e botões
- Footer completo: `↑/↓ Select  Enter Confirm  R Refresh  Tab Buttons  Esc Back`

---

## Tela 3 — SessionDecisionScreen

**Abordagem:** B (moderada)

### O que mudar
- Botão "Recover" → "Resume Validation" (atalho R)
- Botão "Restart" → "Start Over" (atalho S)
- Botão "View Details" → "View Drive Info" (atalho D)
- Botão "Back" mantido (Esc)

### Navegação
- Tab/Setas entre botões
- Atalhos de tecla: R, S, D
- Footer: `[R] Resume  [S] Start Over  [D] Drive Info  [Esc] Back`

---

## Tela 4 — MountWarningScreen

**Abordagem:** A (cosmética)

### O que mudar
- Conteúdo centralizado (`content-align: center middle`)
- Botões com Tab/Setas

---

## Tela 5 — DriveInfoScreen

**Abordagem:** B (moderada)

### Layout: 2 painéis lado a lado

**Painel Esquerdo — Identificação:**
- Model
- Serial
- Firmware
- Capacity
- Device
- WWN
- Interface
- Transport
- Sector Size (Logical / Physical)

**Painel Direito — Saúde e Status:**
- SMART Health (PASSED/FAILED)
- Temperature
- Power-on Hours
- Power Cycles
- Reallocated Sectors
- Pending Sectors
- Uncorrectable Sectors
- CRC Errors
- Current FS
- Partition Table
- UAS status

---

## Tela 6 — ValidationConfigScreen

**Abordagem:** A (cosmética)

### O que mudar
- Visual refresh: melhor espaçamento, centralizado, seções bem separadas
- Navegação por Tab entre grupos (perfil → filesystem → label → botões)
- Manter `RadioSet`-style visual com marcadores ou usar `ListView`
- Descrição do perfil abaixo da seleção

---

## Tela 7 — FinalConfirmationScreen

**Abordagem:** B (moderada)

### O que mudar
- Aviso de destruição em caixa com borda vermelha e ícone ⚠
- Conteúdo centralizado
- Informações: Drive, Serial, Capacity, Profile, Filesystem, Label

### Layout
```
┌──────────────────────────────────────────────┐
│ OldButGold v0.9.0  /  Confirm                │
├──────────────────────────────────────────────┤
│                                              │
│         Validation Summary                    │
│                                              │
│  Drive:     WDC WD10EZEX-00WN4A0             │
│  Serial:    WD-WCC6Y6KZ6KZ6                  │
│  Capacity:  1.0 TB                           │
│                                              │
│  Profile:     Recommended                     │
│  Filesystem:  ext4                           │
│  Label:       MYDRIVE                        │
│                                              │
│  ┌── ⚠ WARNING ──────────────────────────┐  │
│  │  ALL EXISTING DATA WILL BE             │  │
│  │  PERMANENTLY DESTROYED.               │  │
│  └───────────────────────────────────────┘  │
│                                              │
│  [  Back  ]  [  Start Validation  ]          │
├──────────────────────────────────────────────┤
│  Esc Back  Enter Start                       │
└──────────────────────────────────────────────┘
```

---

## Tela 8 — ExecutionScreen (VALIDAÇÃO)

**Abordagem:** C (reescrita de layout)
**Prioridade:** MÁXIMA — garantir com a vida

### Layout fixo (120×40)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ OldButGold v0.9.0  /  Validation                                                     │
├───────────────────────────────┬──────────────────────────────────────────────────────┤
│  Steps                        │  ████████████████████████░░░░░░░░░░░░  45.2%         │
│                               │                                                        │
│  [▶] Drive Identification     │  ┌──────────┬──────────┬──────────┐                    │
│  [✓] Initial SMART            │  │Operation │Progress  │   ETA    │                    │
│  [✓] Surface Scan (Badblocks) │  │Writing…  │  45.2%   │  2h 15m  │                    │
│  [ ] SMART Comparison         │  ├──────────┼──────────┼──────────┤                    │
│  [ ] Create GPT               │  │  Speed   │  Pattern │ Elapsed  │                    │
│  [ ] Create Partition         │  │ 45 MB/s  │  0xaa    │  1h 45m  │                    │
│  [ ] Format Filesystem        │  ├──────────┼──────────┼──────────┤                    │
│  [ ] Generate Report          │  │Bad blocks│  Errors  │          │                    │
│  [ ] Session Cleanup          │  │    None   │ 0/0/0    │          │                    │
│                               │  └──────────┴──────────┴──────────┘                    │
│                               │                                                        │
│                               │  ┌── Disk Info ───────────────────────────────────┐   │
│                               │  │ WDC WD10EZEX  │  WD-WCC6Y6KZ  │  42°C          │   │
│                               │  │ SMART: PASSED │  UAS: Yes     │                │   │
│                               │  └────────────────────────────────────────────────┘   │
│                               │                                                        │
│                               │  ┌── Output ───────────────────────────────────────┐   │
│                               │  │ Testing with pattern 0xaa: 45.20% done,         │   │
│                               │  │   1:45 elapsed. (0/0/0 errors)                  │   │
│                               │  │ Testing with pattern 0xaa: 45.50% done,         │   │
│                               │  │   1:45 elapsed. (0/0/0 errors)                  │   │
│                               │  └────────────────────────────────────────────────┘   │
├───────────────────────────────┴──────────────────────────────────────────────────────┤
│  [C] Cancel  —  Elapsed: 01:45:23                                                     │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### Componentes da coluna direita (topo → base)

1. **ProgressBar** — `ProgressBar(total=100, id="bb-progress", show_eta=False)`, altura 2, cor verde.
2. **Metrics Grid** — `Grid` 3×3 com cards:
   - (0,0) Operation: texto da operação atual
   - (0,1) Progress: X.X%
   - (0,2) ETA: Xh Xm
   - (1,0) Speed: X MB/s
   - (1,1) Pattern: 0xaa/0x55
   - (1,2) Elapsed: Xh Xm
   - (2,0) Bad blocks: count
   - (2,1) Errors: R/W/C
   - (2,2) (vazio ou reservado)
3. **Disk Info Panel** — `Horizontal` com 3 `Static` lado a lado: Modelo | Serial | Temperatura, SMART status, UAS.
4. **Output Log** — `RichLog` (máx 8 linhas) mostrando as últimas linhas de output do comando atual.

### Lógica (manter INALTERADA)
- `_run()`, `_on_step()`, `_on_output()`, `_append()`, `_update_progress()`, `_complete()`, `_tick()`
- Só muda o `compose()` e `_update_progress()` para escrever nos novos widgets.

### Estados
- **Running:** ProgressBar anima, metrics atualizam, output log scrolla
- **Idle (entre passos):** ProgressBar 0%, operation = nome do passo, sem output
- **SMART test:** metrics mostram "SMART Short Self-Test" com %
- **Badblocks:** metrics mostram Operation/Progress/ETA/Speed/Pattern/Bad blocks
- **Erro:** passo marca vermelho, output log mostra erro

---

## Tela 9 — CompleteScreen

**Abordagem:** B (moderada)

### O que mudar
- Classificação com ícone grande (⭐ GOLD / 🥈 SILVER / 🥉 BRONZE / ✗ FAILED)
- Comparação SMART em `DataTable` (colunas: Attribute | Before | After | Delta)
- Seção de erros mais visível (caixa vermelha)
- Divisão visual entre seções (bordas)

### Layout
```
┌──────────────────────────────────────────────┐
│ OldButGold v0.9.0  /  Complete               │
├──────────────────────────────────────────────┤
│                                              │
│  ⭐  GOLD                                     │
│                                              │
│  WDC WD10EZEX-00WN4A0                        │
│  WD-WCC6Y6KZ6KZ6  |  1.0 TB                  │
│                                              │
│  Filesystem: ext4   Label: MYDRIVE            │
│  Bad Blocks: 0   Duration: 2h 15m 30s         │
│                                              │
│  ┌── SMART Comparison ────────────────────┐  │
│  │ Attribute         Before  After  Delta │  │
│  │ Reallocated           5      5       0 │  │
│  │ Pending               0      0       0 │  │
│  │ Uncorrectable         0      0       0 │  │
│  │ CRC Errors            2      2       0 │  │
│  │ Temperature          42     43      +1 │  │
│  │ Power-On Hours     1234   1234       0 │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Reasons:                                    │
│  - Zero bad blocks detected                  │
│  - SMART attributes within normal range      │
│                                              │
│  Report: /path/to/report.md                  │
│                                              │
│  [ Export Report ] [ Validate Another ] [ Q ]│
├──────────────────────────────────────────────┤
│  Enter Another   Q Quit                       │
└──────────────────────────────────────────────┘
```

---

## Implementation Order

1. **Global:** `SCREEN_SIZE`, CSS base, bindings system
2. **ExecutionScreen** (prioridade máxima)
3. **CompleteScreen**
4. **DriveInfoScreen**
5. **SessionDecisionScreen**
6. **FinalConfirmationScreen**
7. **ValidationConfigScreen**
8. **StartupScreen** (logo ASCII)
9. **MountWarningScreen**
10. **DriveSelectionScreen**

Each step: alterar compose/CSS → testar → passar nos testes existentes.
