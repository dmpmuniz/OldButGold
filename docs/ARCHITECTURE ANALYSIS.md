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

### Source Layout (Current)

```
obg/
├── __init__.py             # Package version
├── __main__.py             # Entry point (privilege escalation, terminal resize)
├── config.py               # Runtime configuration persistence (JSON)
├── core/
│   ├── __init__.py
│   ├── detector.py         # Device discovery (lsblk, device type, transport)
│   ├── health.py           # SMART collection, short self-test, polling
│   ├── scanner.py          # Badblocks execution, progress parsing, checkpoints
│   ├── partitioner.py      # sgdisk (GPT), partition creation, partprobe
│   ├── formatter.py        # Filesystem creation (mkfs.ext4, mkfs.ntfs, etc.)
│   ├── engine.py           # Pipeline orchestration, state machine
│   ├── session.py          # Session create/load/save/delete, checkpoints
│   ├── lock.py             # Device locking (fcntl flock)
│   ├── classifier.py      # Gold/Silver/Bronze/Failed classification
│   └── reporter.py         # Markdown report builder
├── models/
│   ├── __init__.py
│   ├── disk.py             # DiskInfo, SmartData, SmartDelta, DiskSnapshot
│   ├── classification.py  # Classification enum + ClassificationResult
│   ├── operation.py        # StepStatus, StepResult, OperationResult
│   └── report.py           # ReportData
├── ui/
│   ├── __init__.py
│   └── app.py              # Textual App + all 9 screen classes
└── utils/
    ├── __init__.py
    ├── logger.py            # Structured diagnostic logging
    ├── runner.py            # Subprocess execution, tool resolution, LD_LIBRARY_PATH
    └── paths.py             # Config/report directory resolution
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

### Module Dependencies (Directed) — Current

| Module | Depends On |
|--------|-----------|
| `models/disk` | (none) |
| `models/classification` | (none) |
| `models/operation` | `models/disk`, `models/classification` |
| `models/report` | `models/disk`, `models/classification`, `models/operation` |
| `utils/logger` | (none) |
| `utils/paths` | (none) |
| `utils/runner` | `utils/logger` |
| `config` | `utils/paths` |
| `core/detector` | `utils/runner`, `models/disk` |
| `core/health` | `utils/runner`, `models/disk` |
| `core/scanner` | `utils/runner` |
| `core/partitioner` | `utils/runner` |
| `core/formatter` | `utils/runner` |
| `core/session` | `models/disk` |
| `core/lock` | (none) |
| `core/classifier` | `models/disk`, `models/classification` |
| `core/reporter` | `models/report`, `utils/paths` |
| `core/engine` | `core/*` (all), `models/*` (all), `utils/logger`, `config` |
| `ui/app` | `core/*`, `models/*`, `config`, `utils/logger` |
| `__main__` | `ui/app`, `utils/logger` |

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
