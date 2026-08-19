# PROJECT_STRUCTURE.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Repository Structure Specification
> **Priority:** Medium

---

# 1. Purpose

This document defines the official repository structure of the OldButGold project.

Its objective is to establish a single, deterministic organization for source code, documentation, assets, releases and development artifacts.

Every contributor and AI agent shall follow this structure.

Creating undocumented directories or files is prohibited.

---

# 2. Design Goals

The repository structure shall be:

* simple;
* predictable;
* deterministic;
* easy to navigate;
* scalable;
* free of redundant directories.

A developer shall be able to understand the entire repository within a few minutes.

---

# 3. Repository Root

The repository root shall contain only the following items.

```text
OldButGold/
│
├── docs/
├── src/
├── tests/
├── scripts/
├── assets/
├── release/
│
├── README.md
├── CHANGELOG.md
├── LICENSE
├── .gitignore
└── pyproject.toml
```

No additional directories shall exist without explicit specification.

---

# 4. Documentation Directory

All project documentation shall reside inside:

```text
docs/
```

This directory shall contain every official project specification.

Example:

```text
docs/

DESIGN_PRINCIPLES.md

PRODUCT_VISION.md

MASTER_SPECIFICATION.md

UI_GUIDELINES.md

ENGINEERING_GUIDELINES.md

ACCEPTANCE_TESTS.md

PROJECT_STRUCTURE.md

TOOLCHAIN_SPECIFICATION.md

REPORT_SPECIFICATION.md

PROJECT_RULES.md
```

Documentation shall never be duplicated elsewhere.

---

# 5. Source Directory

All application source code shall reside inside:

```text
obg/
```

Current layout:

```text
obg/
│
├── __init__.py        # Package version
├── __main__.py        # Entry point
├── config.py          # Runtime configuration persistence
├── core/              # Business logic
│   ├── detector.py    # Device discovery (lsblk, device type)
│   ├── health.py      # SMART collection, short test
│   ├── scanner.py     # Badblocks execution
│   ├── partitioner.py # GPT, partition creation
│   ├── formatter.py   # Filesystem creation (mkfs.*)
│   ├── engine.py      # Pipeline orchestration (state machine)
│   ├── session.py     # Session create/load/save/delete
│   ├── lock.py        # Device locking (fcntl)
│   ├── classifier.py  # Gold/Silver/Bronze/Bad/Failed
│   ├── reporter.py    # Markdown report generator
│   └── __init__.py
├── models/            # Type definitions
│   ├── disk.py        # DiskInfo, SmartData, SmartDelta, DiskSnapshot
│   ├── classification.py  # Classification enum + result
│   ├── operation.py   # StepStatus, StepResult, OperationResult
│   ├── report.py      # ReportData
│   └── __init__.py
├── ui/                # User interface (Textual)
│   ├── app.py         # App class + all screen definitions
│   └── __init__.py
└── utils/             # Utilities
    ├── logger.py      # Structured diagnostic logging
    ├── runner.py      # Subprocess execution, tool resolution
    ├── paths.py       # Config/report directory resolution
    └── __init__.py
```

Every directory shall have a single responsibility.

Business logic shall remain separated from the user interface.

> **Note:** The current layout differs from the originally planned architecture
> (`src/hardware/`, `src/workflow/`, `src/bundle/`, etc.). Business logic lives
> in `core/`, types in `models/`, utilities in `utils/`. This is a valid flat
> structure; future refactoring may reintroduce the modular separation.

---

# 6. Assets Directory

Static resources shall reside inside:

```text
assets/
```

Examples include:

* icons;
* logos;
* fonts;
* static images.

Assets shall never contain executable files.

---

# 7. Tests Directory

All automated tests shall reside inside:

```text
tests/
```

Recommended structure:

```text
tests/

unit/

integration/

acceptance/
```

Test files shall never be mixed with production code.

---

# 8. Scripts Directory

Utility scripts shall reside inside:

```text
scripts/
```

Examples:

```text
scripts/

build.py

package.py

clean.py

release.py
```

Scripts shall automate development tasks only.

They shall never contain application business logic.

---

# 9. Release Directory

Every distributable artifact shall be generated inside:

```text
release/
```

Example:

```text
release/

OldButGold-v0.0.1/

OldButGold-v0.0.1.zip
```

The release directory shall never contain source code.

---

# 10. Distribution Directory

Every release shall be distributed as a single directory.

Example:

```text
OldButGold-v0.0.1/
│
├── OldButGold
├── tools/
├── lib/
├── assets/
├── reports/
├── sessions/
├── LICENSE
└── README.md
```

This directory is the complete application.

Nothing shall be installed into the operating system.

Removing this directory shall completely remove OldButGold.

---

# 11. Runtime Directories

The following directories belong exclusively to the distributed application.

```text
tools/
```

Contains bundled third-party executables.

---

```text
lib/
```

Contains bundled shared libraries required by the bundled executables.

---

```text
reports/
```

Default location for exported Markdown reports.

---

```text
sessions/
```

Stores temporary validation sessions and recovery checkpoints.

Its contents are managed exclusively by the application.

---

# 12. Versioning

The repository name shall remain constant.

Example:

```text
OldButGold/
```

The version number belongs only to release artifacts.

Example:

```text
OldButGold-v0.0.1

OldButGold-v0.0.2

OldButGold-v1.0.0
```

Repository directories shall never be renamed between releases.

---

# 13. Repository Cleanliness

The repository shall never contain temporary development directories such as:

```text
build/

build2/

old/

backup/

temp/

tmp/

debug/

test2/

new/

final/

final-final/

experiment/
```

These directories are prohibited.

---

# 14. Generated Files

Generated files shall never be committed unless they are official release artifacts.

Examples include:

* temporary logs;
* build caches;
* runtime sessions;
* generated reports;
* temporary packages.

Such files shall be ignored by version control whenever appropriate.

---

# 15. Release Packaging

Every official release shall produce:

```text
release/

OldButGold-vX.Y.Z/

OldButGold-vX.Y.Z.zip
```

The ZIP archive shall contain exactly one directory.

Extracting the archive shall immediately produce the runnable application.

Nested archives are prohibited.

---

# 16. Single Entry Point

The distributed application shall expose exactly one executable entry point.

Example:

```text
OldButGold
```

Additional launchers, wrapper scripts or alternative startup mechanisms shall not be distributed.

---

# 17. Repository Rules

Every file inside the repository shall satisfy at least one of the following purposes:

* source code;
* documentation;
* assets;
* tests;
* build automation;
* release artifacts.

Files that satisfy none of these purposes shall be removed.

---

# 18. Engineering Rule

Before creating any new file or directory, contributors and AI agents shall ask the following questions:

1. Is this file strictly necessary?
2. Does an equivalent file already exist?
3. Can the existing structure be reused?
4. Does this comply with this document?
5. Will this improve maintainability?

If any answer is **No**, the new file or directory shall not be created.

Repository simplicity is a permanent engineering objective.

