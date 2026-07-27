# TUI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign all 9 TUI screens with fixed layout, keyboard+mouse navigation, proper alignment, and centered content.

**Architecture:** All screens in `obg/ui/app.py`. Global CSS in `ObgApp.CSS`. No business logic changes.

**Tech Stack:** Textual 0.52+, Python 3.11+

---

## Task 1: Global — SCREEN_SIZE + CSS base + navigation system

**Files:**
- Modify: `obg/ui/app.py:49-95` (ObgApp class + CSS)

**Changes:**
- Add `SCREEN_SIZE = (120, 40)` to `ObgApp`
- Rewrite CSS with grid-based layout, consistent colors, padding
- Standardize BINDINGS pattern across all screens

```python
# In ObgApp:
CSS = """
Screen { background: #000000; }
#app-frame { width: 100%; height: 100%; border: solid #444444; background: #0a0a0a; layout: vertical; }
#header { dock: top; height: 1; background: #111111; color: #cccccc; padding: 0 1; }
#body { height: 1fr; overflow-y: auto; }
#footer { dock: bottom; height: 1; background: #111111; color: #888888; padding: 0 1; }
.card { border: solid #333333; margin: 0 1 1 1; padding: 0 1; }
.card-selected { border: solid #00ff00; margin: 0 1 1 1; padding: 0 1; background: #0a1a0a; }
.card-disabled { border: solid #333333; margin: 0 1 1 1; padding: 0 1; color: #555555; }
.card:hover { background: #1a1a1a; }
.group-title { color: #cccccc; text-style: bold; margin-top: 1; }
.warning { color: #ffff00; text-style: bold; }
.ok { color: #00ff00; }
.failed { color: #ff0000; text-style: bold; }
.step-ok { color: #00ff00; }
.step-running { color: #ffff00; }
.step-failed { color: #ff0000; }
.step-pending { color: #666666; }
.step-skipped { color: #555555; }
.gold { color: #00ff00; text-style: bold; }
.silver { color: #aaaaaa; text-style: bold; }
.bronze { color: #cd7f32; text-style: bold; }
.btn-row { height: 3; align: center middle; }
.btn-row Button { width: 1fr; margin: 0 1; }
.btn-row Button:hover { background: #1a3a1a; }
.btn-row Button:focus { border: solid #00ff00; }
.steps-col { width: 30%; min-width: 25; border-right: solid #333333; }
.output-col { width: 70%; min-width: 40; }
.panel-box { border: solid #333333; margin: 0 1; padding: 0 1; }
.empty-msg { content-align: center middle; height: 100%; color: #666666; }
.progress-info { color: #aaaaaa; }
ProgressBar { margin: 0 2; height: 2; }
#metrics-list { border: solid #333333; margin: 0 1; padding: 0 1; color: #cccccc; min-height: 10; }
.warning-box { border: solid #ff0000; margin: 1 2; padding: 1; color: #ffff00; text-style: bold; content-align: center middle; }
.metric-card { border: solid #333333; padding: 0 1; margin: 0 1; min-height: 3; }
"""
```

- [ ] **Step 1:** Add `SCREEN_SIZE` to `ObgApp.__init__`
- [ ] **Step 2:** Replace CSS block
- [ ] **Step 3:** Run tests
- [ ] **Step 4:** Commit

---

## Task 2: ExecutionScreen — Complete layout rewrite

**Files:**
- Modify: `obg/ui/app.py:702-934`

**Layout (right column, top→bottom):**
1. ProgressBar (big, height 2)
2. Metrics Grid (3×3 cards)
3. Disk Info Panel (3 columns: Model | Serial | Temp/SMART)
4. Output Log (RichLog, max 8 lines)

**Implementation:**
- Rewrite `compose()` for the right column layout
- Rewrite `_update_progress()` to write to individual metric cards
- Add disk info update to `_tick()` (query temperature each tick)
- Keep ALL logic methods unchanged: `_run`, `_on_step`, `_on_output`, `_append`, `_complete`

- [ ] **Step 1:** Rewrite `compose()` — ProgressBar + metrics grid + disk info panel + RichLog
- [ ] **Step 2:** Rewrite `_show_step_info()` — clear all widgets
- [ ] **Step 3:** Rewrite `_update_progress()` — write to individual metric cards
- [ ] **Step 4:** Update `_tick()` — update disk info panel (temp, elapsed)
- [ ] **Step 5:** Run tests
- [ ] **Step 6:** Commit

---

## Task 3: CompleteScreen — DataTable + classification icon

**Files:**
- Modify: `obg/ui/app.py:937-1067`

**Changes:**
- Classification with icon (⭐/🥈/🥉/✗)
- SMART comparison as DataTable
- Red-bordered error section
- Better visual separation

- [ ] **Step 1:** Rewrite `compose()` — classification icon, DataTable for SMART, error box
- [ ] **Step 2:** Run tests
- [ ] **Step 3:** Commit

---

## Task 4: DriveInfoScreen — 2-panel layout

**Files:**
- Modify: `obg/ui/app.py:436-526`

**Changes:**
- 2 panels side by side (Grid)
- Panel 1: Model, Serial, Firmware, Capacity, Device, WWN, Interface, Transport, Sector Size
- Panel 2: SMART Health, Temp, POH, Cycles, Reallocated, Pending, Uncorrectable, CRC, FS, Partition, UAS

- [ ] **Step 1:** Rewrite `compose()` — Grid with 2 panels
- [ ] **Step 2:** Run tests
- [ ] **Step 3:** Commit

---

## Task 5: SessionDecisionScreen — Button rename + shortcuts

**Files:**
- Modify: `obg/ui/app.py:318-365`

**Changes:**
- Resume Validation (R), Start Over (S), View Drive Info (D), Back (Esc)
- Footer with shortcut hints
- Keyboard: Tab between buttons, R/S/D shortcuts

- [ ] **Step 1:** Update button labels + add BINDINGS for R/S/D
- [ ] **Step 2:** Update footer
- [ ] **Step 3:** Run tests
- [ ] **Step 4:** Commit

---

## Task 6: FinalConfirmationScreen — Warning box + center

**Files:**
- Modify: `obg/ui/app.py:651-698`

**Changes:**
- Warning in red-bordered box with ⚠
- Centered layout
- Style improvements

- [ ] **Step 1:** Rewrite `compose()` — warning box, centered
- [ ] **Step 2:** Run tests
- [ ] **Step 3:** Commit

---

## Task 7: ValidationConfigScreen — Visual refresh

**Files:**
- Modify: `obg/ui/app.py:529-648`

**Changes:**
- Better spacing and centering
- Clear section separation
- Tab navigation between sections

- [ ] **Step 1:** Update `compose()` CSS classes and spacing
- [ ] **Step 2:** Run tests
- [ ] **Step 3:** Commit

---

## Task 8: StartupScreen — ASCII logo

**Files:**
- Modify: `obg/ui/app.py:101-201`

**Changes:**
- Add ASCII art logo block
- Centered layout
- Footer with full shortcut hints

- [ ] **Step 1:** Rewrite `compose()` — add logo, center, full footer
- [ ] **Step 2:** Run tests
- [ ] **Step 3:** Commit

---

## Task 9: MountWarningScreen — Centered

**Files:**
- Modify: `obg/ui/app.py:368-431`

**Changes:**
- Centered content
- Button navigation

- [ ] **Step 1:** Update `compose()` — centered
- [ ] **Step 2:** Run tests
- [ ] **Step 3:** Commit

---

## Task 10: DriveSelectionScreen — Cosmetic

**Files:**
- Modify: `obg/ui/app.py:204-316`

**Changes:**
- Tab between cards and buttons
- Footer polish

- [ ] **Step 1:** Add Tab navigation support
- [ ] **Step 2:** Update footer
- [ ] **Step 3:** Run tests
- [ ] **Step 4:** Commit

---

## Final Verification

- [ ] Run all 68+ tests: `pytest tests/ -x -q`
- [ ] Run full pipeline in test mode: `python3 -m obg --test --mock /tmp/test.img`
- [ ] Bump version to 0.9.0
- [ ] Rebuild release
- [ ] Create review agent with design doc comparison
