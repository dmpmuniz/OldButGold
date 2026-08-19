# UI_GUIDELINES.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** User Interface Guidelines
> **Priority:** High

---

# 1. Purpose

This document defines the visual behavior and interaction model of the OldButGold user interface.

It specifies how information shall be presented to the user while preserving the principles defined in `DESIGN_PRINCIPLES.md`.

This document intentionally avoids implementation details.

---

# 2. Design Goals

The interface shall be:

* simple;
* deterministic;
* keyboard-first;
* information-oriented;
* distraction-free;
* consistent across all screens.

The interface shall resemble a mature native Linux application rather than a modern dashboard.

---

# 3. General Rules

The interface shall never contain:

* theme selector;
* appearance customization;
* command console;
* advanced menus;
* hidden developer options;
* plugin manager;
* settings window;
* configuration wizard;
* startup assistant.

The application shall expose only the options required to complete the validation workflow.

---

# 4. Navigation

Keyboard navigation is the primary interaction method.

The following keys shall be available throughout the application whenever applicable:

| Key         | Action                                             |
| ----------- | -------------------------------------------------- |
| ↑ ↓         | Move selection                                     |
| ← →         | Change option                                      |
| Enter       | Confirm                                            |
| Esc         | Return                                             |
| Tab         | Next control                                       |
| Shift + Tab | Previous control                                   |
| Space       | Toggle checkbox or radio button                    |
| R           | Refresh device list (device selection screen only) |

Mouse support shall remain fully functional.

Keyboard and mouse interactions shall always produce identical results.

---

# 5. Window Layout

Every screen shall follow the same structure.

```
┌──────────────────────────────────────────────┐
│ Header                                       │
├──────────────────────────────────────────────┤
│ Main Content                                 │
│                                              │
│                                              │
├──────────────────────────────────────────────┤
│ Action Buttons                               │
└──────────────────────────────────────────────┘
```

No screen shall significantly deviate from this layout.

---

# 6. Screen 1 — Startup

Purpose:

* display legal disclaimer;
* initialize the application;
* detect available drives.

While the disclaimer is displayed, initialization shall execute in the background.

Buttons:

* Continue
* Exit

Continue shall remain unavailable until initialization completes.

---

# 7. Screen 2 — Drive Selection

This is the main application screen.

Each drive shall occupy its own visual block.

Example:

```text
▶ WD Blue 1TB
  /dev/sdb • SATA • 931.5 GiB
  WDC WD10EZEX • USB 3.0 Adapter

Seagate Barracuda 2TB
/dev/sdc • SATA • 1.82 TiB
ST2000DM008 • Direct SATA

Samsung 980 PRO
/dev/nvme0n1 • Protected
NVMe SSD • Validation Disabled
```

Each drive shall contain enough information for reliable identification before selection.

Selected drives shall be visually highlighted.

A simple arrow alone is not sufficient.

A minimum vertical spacing shall separate consecutive drives.

---

# 8. Interrupted Validation

If an interrupted validation session exists, the drive list shall indicate it directly.

Example:

```text
WD Blue 1TB

Interrupted Validation

61% Completed
```

No popup shall appear automatically.

The session menu appears only after the user selects the drive.

---

# 9. Screen 3 — Validation Session

Displayed only when an interrupted session exists.

Information displayed:

* model;
* serial number;
* capacity;
* current stage;
* completion percentage;
* interruption time.

Available actions:

* Recover Validation
* Restart Validation
* View Session Details
* Back

---

# 10. Screen 4 — Drive Information

Immediately after SMART Short completes, the application shall present all collected information.

Information shall be organized into four compact panels.

```
┌──────────────────────┬──────────────────────┐
│ Device Information   │ Configuration        │
├──────────────────────┼──────────────────────┤
│ SMART Information    │ Geometry             │
└──────────────────────┴──────────────────────┘
```

Information shall never be displayed as a long vertical list.

The objective is to maximize information density while preserving readability.

---

# 11. Screen 5 — Validation Configuration

The interface shall expose only three configurable items.

Validation Profile

```
● Recommended

○ Extended
```

Filesystem

```
EXT4

NTFS

exFAT

FAT32
```

Volume Label

```
_____________________
```

No other validation parameters shall be visible.

---

# 12. Screen 6 — Final Confirmation

Before validation begins, the application shall summarize:

* selected drive;
* validation profile;
* filesystem;
* volume label.

A clear warning shall state that all existing data will be permanently destroyed.

Buttons:

* Back
* Start Validation

---

# 13. Screen 7 — Validation Execution

This is the primary execution screen.

The interface shall display:

Overall progress.

Current stage.

Current operation.

Current activity.

Elapsed time.

Estimated remaining time.

Current throughput.

Processed data.

Stage progress.

Pipeline status.

The application shall always describe the current operation.

Examples:

* Reading blocks
* Writing pattern 1
* Verifying pattern 1
* Collecting SMART data
* Creating GPT
* Creating filesystem

Generic messages such as "Processing" are prohibited.

---

# 14. Pipeline Display

The left side of the execution screen shall permanently display the validation pipeline.

Example:

```
✓ Device Identification

✓ SMART Short

▶ Badblocks

□ SMART Comparison

□ GPT

□ Filesystem

□ Report
```

Completed stages:

* green;
* check mark.

Current stage:

* highlighted.

Failed stages:

* red;
* X symbol.

Future stages:

* neutral.

The pipeline shall remain visible during the entire validation.

---

# 15. Progress Information

Progress bars shall represent actual execution.

Displayed percentages shall never be simulated.

Whenever available, stage-specific estimated time shall be shown.

Overall estimated completion time shall also be displayed.

---

# 16. Screen 8 — Validation Complete

The final screen shall summarize the completed validation.

Displayed information shall include:

* validation result;
* classification;
* SMART comparison summary;
* Badblocks result;
* filesystem created;
* total execution time.

Available actions:

* Export Report
* Validate Another Drive
* Exit

---

# 17. Screen 9 — Export Report

The application shall export reports exclusively in Markdown format.

No HTML, JSON or PDF export shall be provided.

---

# 18. Language

The interface shall automatically follow the operating system language whenever localization is available.

Technical terms shall remain consistent with industry-standard terminology.

---

# 19. Visual Style

The interface shall prioritize:

* alignment;
* spacing;
* consistency;
* readability.

Visual decoration shall be minimal.

The interface shall avoid:

* oversized buttons;
* excessive whitespace;
* unnecessary icons;
* decorative animations.

Every visual element shall have a functional purpose.

---

# 20. Interaction Philosophy

The user should never wonder:

* what the application is doing;
* what has already happened;
* what will happen next.

Every screen shall communicate the current state of the validation workflow clearly, using concise language, real technical information and consistent visual organization.

