# Architecture Analysis

> **Phase 2 — Internal Working Document**
> **Status:** Complete

---

## Application Architecture

OldButGold is a Python TUI application using the Textual framework. It orchestrates bundled Linux utilities through a fixed validation pipeline.

### Layer Architecture

```
┌─────────────────────────────────────────────┐
│                  UI Layer                    │
│         (Textual TUI - screens)              │
├─────────────────────────────────────────────┤
│             Workflow Controller              │
│        (Pipeline sequencing, stages)         │
├──────────┬──────────┬───────────┬───────────┤
│ Hardware │ Sessions │ Reports   │ Classify   │
│ (Device, │ (Recovery│ (Markdown │ (Gold/     │
│  SMART,  │  Checkpt)│  Export)  │ Silver/    │
│  Badblocks│          │           │ Bronze/    │
│  Prep)   │          │           │ Failed)    │
├──────────┴──────────┴───────────┴───────────┤
│           Tool Execution Layer               │
│      (Bundle paths, LD_LIBRARY_PATH,         │
│       subprocess, output parsing)            │
├─────────────────────────────────────────────┤
│              Core Layer                      │
│    (Types, constants, config, fingerprint)   │
└─────────────────────────────────────────────┘
```

### Source Layout

```
src/
├── main.py                 # Entry point
├── core/
│   ├── __init__.py
│   ├── types.py            # Dataclasses: Device, Session, SMARTData, ValidationConfig
│   ├── constants.py        # Paths, profiles, filesystems, classification names
│   └── config.py           # Runtime configuration
├── hardware/
│   ├── __init__.py
│   ├── discovery.py        # lsblk enumeration, device type detection
│   ├── identification.py   # Fingerprint generation (serial, model, firmware, capacity)
│   ├── smart.py            # smartctl initial/final/short execution + parsing
│   ├── badblocks.py        # Badblocks execution, progress parsing
│   └── preparation.py      # sgdisk (GPT), mkfs.*, wipefs, partprobe
├── workflow/
│   ├── __init__.py
│   └── controller.py       # Pipeline state machine, stage sequencing
├── sessions/
│   ├── __init__.py
│   └── manager.py          # Session create/load/save/delete, checkpoints, fingerprint verify
├── reports/
│   ├── __init__.py
│   └── generator.py        # Markdown report builder
├── ui/
│   ├── __init__.py
│   ├── app.py              # Textual App class
│   ├── screens.py          # Screen definitions (9 screens)
│   └── widgets.py          # Custom widgets (pipeline display, progress)
├── bundle/
│   ├── __init__.py
│   └── tools.py            # Tool path resolution, LD_LIBRARY_PATH setup, execution
└── logging_setup.py        # Structured diagnostic logging
```

---

## Dependency Graph

```
main.py
  └── ui/app.py
        ├── workflow/controller.py
        │     ├── hardware/discovery.py
        │     ├── hardware/identification.py
        │     ├── hardware/smart.py
        │     ├── hardware/badblocks.py
        │     ├── hardware/preparation.py
        │     ├── sessions/manager.py
        │     ├── reports/generator.py
        │     └── (classification logic in types or dedicated module)
        ├── bundle/tools.py
        └── core/types.py, core/constants.py, core/config.py
```

### Module Dependencies (Directed)

| Module | Depends On |
|--------|-----------|
| `core/types` | (none) |
| `core/constants` | (none) |
| `core/config` | `core/constants` |
| `bundle/tools` | `core/constants`, `core/config` |
| `hardware/discovery` | `bundle/tools`, `core/types` |
| `hardware/identification` | `bundle/tools`, `core/types` |
| `hardware/smart` | `bundle/tools`, `core/types` |
| `hardware/badblocks` | `bundle/tools`, `core/types` |
| `hardware/preparation` | `bundle/tools`, `core/types` |
| `sessions/manager` | `core/types`, `hardware/identification` |
| `reports/generator` | `core/types` |
| `workflow/controller` | `hardware/*`, `sessions/manager`, `reports/generator` |
| `ui/app` | `workflow/controller`, `bundle/tools`, `core/*` |
| `main.py` | `ui/app` |

---

## Implementation Order (Dependency-Driven)

| Order | Work Package | Rationale |
|-------|-------------|-----------|
| 1 | WP-01: Core Infrastructure | Foundation for all modules |
| 2 | WP-11: Tool Execution | Required by all hardware modules |
| 3 | WP-02: Device Discovery | First workflow stage, uses tools |
| 4 | WP-03: SMART Collection | Uses tools, devices |
| 5 | WP-04: Badblocks Engine | Uses tools, long-running |
| 6 | WP-05: Session Recovery | Uses identification, checkpoints |
| 7 | WP-06: Drive Preparation | Uses tools, last hardware stage |
| 8 | WP-07: Classification | Uses SMART + Badblocks results |
| 9 | WP-08: Report Generation | Uses all collected data |
| 10 | WP-10: Workflow Controller | Orchestrates all stages |
| 11 | WP-09: UI Layer | Depends on all backend |
| 12 | WP-12: Privilege Escalation | Runtime wrapper |
| 13 | WP-13: Build & Release | Final packaging |

---

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.11+ | Spec requirement, subprocess for tools |
| TUI Framework | Textual | Modern, keyboard-first, widget-based, Linux-native aesthetic |
| Tool Execution | subprocess with explicit paths | Spec requirement: no PATH resolution |
| Library Path | LD_LIBRARY_PATH env manipulation | Load bundled libs before host libs |
| Session Storage | JSON files in sessions/ | Simple, human-readable, no DB dependency |
| Report Format | Markdown (.md) | Spec requirement |
| Build | PyInstaller or similar | Single executable bundling |
| Privilege Escalation | pkexec | Spec requirement |

---

## Validation Pipeline Stages

```
1. Startup ──→ 2. Device Discovery ──→ 3. Session Detection
                                              │
                    ┌─────────────────────────┤
                    │                         │
              No Session              Session Exists
                    │                         │
                    │                    4. Session Decision
                    │                    (Recover/Restart/Back)
                    │                         │
                    └────────┬────────────────┘
                             │
                      5. Drive Identification
                             │
                      6. Initial SMART Collection
                             │
                      7. SMART Short Self-Test
                             │
                      8. Validation Configuration
                             │
                      9. Final Confirmation
                             │
                     10. Badblocks Validation
                             │
                     11. Final SMART Collection
                             │
                     12. Drive Preparation (if success)
                             │
                     13. Report Generation
                             │
                     14. Session Cleanup
```
