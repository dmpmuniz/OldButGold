# ENGINEERING_GUIDELINES.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Engineering Guidelines
> **Priority:** Medium

---

# 1. Purpose

This document defines how OldButGold shall be engineered.

It specifies architectural rules, implementation constraints and engineering practices required to preserve the product philosophy defined by the higher-priority specification documents.

This document does not define product behavior.

---

# 2. Engineering Philosophy

Engineering decisions shall prioritize:

1. Correctness.
2. Simplicity.
3. Reliability.
4. Maintainability.
5. Deterministic behavior.

Performance optimizations shall never reduce correctness or transparency.

---

# 3. Architecture

The application shall be organized into clearly separated layers.

Current layer organization:

| Layer | Module(s) | Responsibility |
|-------|-----------|----------------|
| **Entry Point** | `__main__.py` | Privilege escalation, terminal setup |
| **Configuration** | `config.py` | Runtime config persistence (JSON) |
| **Core** | `core/` | 10 modules covering device discovery, SMART, Badblocks, partitioning, formatting, session, locking, classification, reporting, pipeline orchestration |
| **Models** | `models/` | 4 type modules: DiskInfo, SmartData, StepResult, ReportData |
| **UI** | `ui/app.py` | Textual TUI, 9 screen classes |
| **Utilities** | `utils/` | Logger, subprocess runner, path resolution |

Each module shall have a single responsibility.

Business logic shall remain separated from the user interface.

---

# 4. Modularity

Every module shall perform one well-defined task.

Modules shall communicate through well-defined interfaces.

Business logic shall never be embedded inside the user interface.

---

# 5. Single Source of Truth

Every piece of information shall exist in only one authoritative location.

Duplicated state shall be avoided.

Whenever possible, data shall be queried instead of copied.

---

# 6. External Utilities

OldButGold shall orchestrate trusted Linux utilities.

The application shall never reimplement their functionality.

Tool execution shall preserve the original behavior whenever possible.

Output parsing shall remain deterministic.

---

# 7. Bundled Dependencies

All required third-party utilities shall be distributed inside the application bundle whenever licensing permits.

The bundle shall be self-contained.

The operating system shall not be required to install additional packages to execute the validation workflow.

---

# 8. Runtime Dependencies

The application shall depend only on:

* Linux kernel interfaces;
* bundled utilities;
* the system terminal.

No network connectivity shall be required.

No package manager shall be required during execution.

---

# 9. Internal Terminal

The application shall execute all workflow operations inside its bundled terminal environment.

Users shall never interact directly with shell commands.

The terminal exists solely as the execution environment.

---

# 10. Privilege Escalation

Administrative privileges shall be requested only once.

After successful authentication, the entire validation workflow shall execute within the elevated runtime.

Repeated password prompts shall not occur during a validation session.

---

# 11. Error Handling

Every operation shall return explicit success or failure.

Errors shall never be ignored.

Unexpected conditions shall generate diagnostic information suitable for troubleshooting.

---

# 12. Recovery System

Long-running stages shall periodically persist recovery information.

Recovery data shall contain only the information necessary to safely reconstruct the validation session.

Recovery information shall never replace validation data.

---

# 13. Validation Sessions

Each HDD owns exactly one validation session.

Sessions shall be independent.

Multiple application instances validating different HDDs simultaneously shall be fully supported.

A single HDD shall never be validated by more than one application instance simultaneously.

---

# 14. Device Locking

Before starting validation, the application shall acquire an exclusive lock for the selected HDD.

If another OldButGold instance already owns the lock, validation shall be denied.

The user shall receive a clear explanation.

---

# 15. Hardware Identification

Every HDD shall be identified through its hardware fingerprint.

The implementation shall never rely on:

* `/dev/sdX`;
* USB topology;
* connection order;
* kernel enumeration order.

---

# 16. State Persistence

The application shall persist only the information required for:

* recovery;
* reporting;
* diagnostics.

Temporary runtime data shall remain temporary.

---

# 17. Temporary Files

Temporary files shall be stored separately from exported reports.

Temporary artifacts shall be removed automatically whenever no longer required.

Unexpected termination shall never permanently accumulate temporary files.

---

# 18. Logging

Diagnostic logs shall be structured.

Logs shall record:

* timestamps;
* executed stages;
* executed tools;
* failures;
* warnings;
* recovery events.

Logs shall never replace the Markdown report.

---

# 19. Report Generation

Reports shall be generated from collected validation data.

The report generator shall never invent or infer values.

Every reported value shall originate from observed execution.

---

# 20. User Interface Separation

The user interface shall never:

* execute shell commands;
* perform validation logic;
* parse utility output;
* manage sessions.

Its responsibility is limited to presenting information and collecting user input.

---

# 21. Workflow Controller

The workflow controller is responsible for:

* sequencing stages;
* enforcing workflow order;
* validating transitions;
* preventing invalid execution paths.

Every workflow transition shall be explicit.

---

# 22. Configuration

The application shall expose only configuration options approved by the product specification.

Implementation-specific parameters shall remain internal.

Hidden configuration files shall not alter application behavior outside the documented specification.

---

# 23. Deterministic Output

Given identical:

* hardware;
* validation profile;
* tool versions;
* execution environment;

the application shall attempt to produce equivalent results.

Implementation shall avoid non-deterministic behavior whenever possible.

---

# 24. Performance

Performance improvements are encouraged only when they:

* preserve correctness;
* preserve transparency;
* preserve deterministic behavior.

Artificial optimization that complicates maintenance shall be avoided.

---

# 25. Code Quality

The implementation shall prioritize:

* readability;
* simplicity;
* explicit behavior;
* low coupling;
* high cohesion.

Premature optimization shall be avoided.

---

# 26. Dead Code

Unused:

* files;
* modules;
* classes;
* functions;
* assets;
* dependencies;

shall be removed.

The repository shall contain only files required to build, execute or document the project.

---

# 27. Repository Organization

The project structure shall remain minimal.

Directory organization shall reflect responsibilities rather than implementation history.

Experimental code shall not remain in the primary codebase.

---

# 28. Build Output

The application shall produce a single distributable directory.

Users shall launch OldButGold through one executable entry point.

Launchers, wrapper scripts and redundant startup mechanisms shall be avoided whenever technically possible.

---

# 29. Compatibility

The application shall operate consistently across supported Linux distributions.

Distribution-specific behavior shall be minimized.

Whenever platform differences exist, the implementation shall prefer standardized Linux interfaces.

---

# 30. Engineering Rule

When implementation choices exist, engineers shall always choose the simplest solution that fully satisfies:

* DESIGN_PRINCIPLES.md
* PRODUCT_VISION.md
* MASTER_SPECIFICATION.md
* UI_GUIDELINES.md

No implementation decision may contradict any higher-priority specification document.

