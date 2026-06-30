# PROJECT_RULES.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Project Rules
> **Priority:** High

---

# 1. Purpose

This document defines the non-negotiable engineering rules that every contributor and AI agent shall follow when working on the OldButGold project.

These rules exist to preserve the architecture, maintainability and philosophy of the project.

They complement, but never replace, the official project specifications.

---

# 2. Rule Hierarchy

When implementing any modification, the following documents shall be respected in order of priority:

1. DESIGN_PRINCIPLES.md
2. PRODUCT_VISION.md
3. MASTER_SPECIFICATION.md
4. UI_GUIDELINES.md
5. ENGINEERING_GUIDELINES.md
6. PROJECT_STRUCTURE.md
7. TOOLCHAIN_SPECIFICATION.md
8. REPORT_SPECIFICATION.md
9. ACCEPTANCE_TESTS.md
10. PROJECT_RULES.md

Higher-priority documents always override lower-priority documents.

---

# 3. No Hallucinations

AI agents shall never:

* invent requirements;
* invent features;
* invent workflows;
* invent configuration options;
* invent command-line parameters;
* invent hardware information;
* invent SMART values;
* invent Badblocks results;
* invent progress information.

If information cannot be obtained, it shall be reported as unavailable.

---

# 4. No Architectural Changes

The following components are considered frozen architecture:

* validation pipeline;
* runtime bundle;
* project structure;
* report format;
* user workflow.

No architectural changes may be introduced without explicit specification updates.

---

# 5. Simplicity First

Before implementing any solution, contributors shall ask:

* Is this required?
* Is there a simpler solution?
* Can existing code solve the problem?
* Does this increase project complexity?

If complexity increases without measurable benefit, the solution shall be rejected.

---

# 6. Single Responsibility

Every:

* module;
* class;
* function;
* file;

shall have a single responsibility.

Large multi-purpose files shall be avoided.

---

# 7. No Duplicate Code

Logic shall exist in only one location.

Copy-and-paste implementations are prohibited.

Reusable behavior shall be shared through existing modules.

---

# 8. No Dead Code

The repository shall never contain:

* unused functions;
* unused modules;
* obsolete implementations;
* commented-out legacy code;
* abandoned experiments.

Unused code shall be removed rather than preserved.

---

# 9. No Temporary Files

Development artifacts shall not remain inside the repository.

Examples include:

* temporary builds;
* debug outputs;
* experimental scripts;
* backup copies;
* generated caches.

---

# 10. No Redundant Files

Before creating a new file, contributors shall verify that an appropriate file does not already exist.

Creating nearly identical files is prohibited.

---

# 11. No Alternative Implementations

The repository shall contain only one official implementation for each feature.

Legacy implementations shall be removed after replacement.

---

# 12. Preserve Working Code

Fixes shall be minimal.

Code that already functions correctly shall not be rewritten without technical justification.

Refactoring shall never change observable behavior unless required by the specification.

---

# 13. Incremental Development

Changes shall be implemented in small, verifiable steps.

Large rewrites are discouraged.

Every completed step shall leave the project in a buildable state.

---

# 14. Validation Before Completion

No task is complete until:

* implementation is finished;
* project builds successfully;
* acceptance tests pass;
* obsolete code is removed.

---

# 15. Runtime Integrity

The application shall always execute bundled tools.

Host-installed equivalents shall never be substituted automatically.

Silent fallbacks are prohibited.

---

# 16. User Interface

The UI shall remain:

* simple;
* deterministic;
* consistent;
* free of unnecessary options.

Developer-oriented controls shall never appear in the production interface.

---

# 17. Logging

Logs exist for diagnostics.

Reports exist for users.

These responsibilities shall never be mixed.

---

# 18. Documentation

Whenever behavior changes, affected documentation shall be updated within the same change.

Implementation and documentation shall never intentionally diverge.

---

# 19. Build Artifacts

Only official release artifacts belong inside the `release/` directory.

Generated files shall not be committed elsewhere.

---

# 20. Dependency Control

New third-party dependencies require technical justification.

Existing bundled utilities shall be preferred whenever they satisfy the requirement.

Redundant libraries are prohibited.

---

# 21. Performance

Optimization shall never reduce:

* correctness;
* readability;
* maintainability;
* determinism.

Premature optimization is prohibited.

---

# 22. Error Messages

Errors presented to users shall:

* describe the problem;
* avoid internal implementation details;
* provide actionable information whenever possible.

Generic error messages are discouraged.

---

# 23. Code Review Checklist

Before considering any task complete, contributors and AI agents shall verify:

* Does the implementation satisfy the specification?
* Is the solution the simplest possible?
* Was any unnecessary file created?
* Was any obsolete file removed?
* Was duplicated logic eliminated?
* Was documentation updated?
* Does the project still build?
* Do acceptance tests still pass?
* Does the implementation preserve deterministic behavior?

Any negative answer shall block completion.

---

# 24. Repository Discipline

The repository shall always remain clean.

Every file shall have a clear purpose.

Every directory shall have a documented responsibility.

Every executable shall belong to the official build.

Anything that does not satisfy these conditions shall be removed.

---

# 25. Final Engineering Rule

When uncertainty exists, contributors and AI agents shall **not** invent a solution.

They shall instead:

1. consult the official specification documents;
2. reuse existing project architecture whenever possible;
3. implement the smallest compliant solution;
4. stop and request clarification if the specification is genuinely ambiguous.

OldButGold values correctness, determinism and simplicity above implementation speed or unnecessary feature expansion.

