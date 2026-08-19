# DESIGN_PRINCIPLES.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Foundational Design Principles
> **Priority:** Highest

---

# 1. Purpose

This document defines the fundamental principles that govern every design, engineering and implementation decision within the OldButGold project.

These principles are mandatory and take precedence over implementation preferences, architectural decisions and feature requests.

Any behavior that conflicts with these principles shall be considered incorrect, even if technically functional.

---

# 2. Design Principles

---

## Principle 01 — Truth Over Convenience

The application shall never invent, estimate, simulate or fabricate technical information when real data can be obtained.

Only verified information produced by trusted system utilities may be presented to the user.

If information cannot be determined, the application shall explicitly report that it is unavailable instead of making assumptions.

---

## Principle 02 — Validation, Not Certification

OldButGold validates only the observable condition of a mechanical hard drive during the executed validation workflow.

The application does not certify, guarantee or predict future reliability, remaining lifespan or data integrity.

Validation results represent the observed state at the time of execution only.

---

## Principle 03 — Deterministic Behavior

Given the same hardware, validation profile and execution conditions, the application shall produce equivalent results.

Behavior shall be predictable, repeatable and reproducible.

Random or undocumented behavior is not acceptable.

---

## Principle 04 — Safety First

Whenever safety and convenience conflict, safety shall always take priority.

The application shall never perform destructive operations without explicit user confirmation.

Protected devices shall never be modified.

Potentially dangerous operations shall always require deliberate user action.

---

## Principle 05 — Keep It Simple (KISS)

Every workflow, screen, interaction and implementation shall remain as simple as possible.

Complexity is acceptable only when it demonstrably improves reliability, correctness or user safety.

Features that exist solely for convenience, aesthetics or novelty are outside the project scope.

---

## Principle 06 — Offline First

The application shall operate entirely offline.

Internet connectivity is never required for normal operation.

Cloud services, telemetry, user accounts, online activation and remote dependencies are outside the scope of this project.

---

## Principle 07 — Single Purpose

OldButGold exists exclusively to inspect, validate, refurbish and prepare mechanical hard drives.

The application is not a disk management suite, recovery utility, benchmarking tool or storage administration platform.

Features unrelated to the validation workflow shall not be implemented.

---

## Principle 08 — Transparency

The application shall clearly communicate:

* what is currently being executed;
* what has already been completed;
* what remains to be executed;
* the current validation status;
* warnings and failures.

The application shall never hide important technical information from the user.

---

## Principle 09 — Recoverability

Long-running operations shall support safe recovery whenever technically possible.

Recovery shall never compromise validation integrity.

Whenever safe recovery cannot be guaranteed, the affected validation stage shall be restarted instead of making assumptions.

---

## Principle 10 — Identity Before Action

Every mechanical hard drive shall be identified using its hardware fingerprint before any destructive or recovery operation.

Device names such as `/dev/sda`, `/dev/sdb` or similar shall never be considered unique identifiers.

Recovery is permitted only when the detected drive matches the stored fingerprint.

---

## Principle 11 — Conservative Recovery

Interrupted validation sessions shall never continue blindly.

Whenever a validation session is recovered, the application shall restart from a predefined internal safety margin to revalidate previously processed regions.

Recovery shall always prioritize correctness over execution time.

---

## Principle 12 — Session Isolation

Each mechanical hard drive owns its own independent validation session.

Validation sessions shall never depend on process identifiers, operating system device names or USB connection order.

Each drive shall be recoverable independently.

---

## Principle 13 — Clean Execution

Temporary files, checkpoints and runtime artifacts exist only to support the current validation session.

Completed, discarded or restarted sessions shall automatically remove temporary data.

Only user-selected outputs, such as exported reports, may remain after completion.

---

## Principle 14 — Native Linux Philosophy

OldButGold orchestrates mature and trusted Linux utilities instead of replacing or reimplementing them.

Whenever possible, existing system tools shall be used exactly as intended by their original documentation.

The application adds orchestration, validation workflow and user experience—not alternative implementations.

---

## Principle 15 — User Responsibility

OldButGold provides technical observations, measurements and validation results.

The decision to continue using, storing data on or deploying a validated drive remains exclusively the responsibility of the user.

The application does not guarantee suitability for any specific workload.

---

## Principle 16 — Real Data Only

Every value presented by the application shall originate from an actual measurement, system query or trusted utility.

Progress indicators, estimated times, throughput values and status information shall always reflect real execution.

Placeholder values, simulated progress and fabricated metrics are strictly prohibited.

---

## Principle 17 — Specification First

Implementation shall always follow the project specification.

Undocumented behavior shall never be inferred.

When uncertainty exists, clarification shall be requested rather than implementing assumptions.

If specification documents conflict, the document with higher priority shall prevail.

---

## Principle 18 — Timeless Design

The application shall prioritize clarity, stability and longevity over visual trends.

The user interface should resemble a mature native Linux utility: clean, functional, predictable and free from unnecessary visual elements.

---

# 3. Non-Goals

The following are intentionally outside the scope of OldButGold:

* SSD optimization.
* NVMe management.
* RAID management.
* LVM management.
* Disk cloning.
* File recovery.
* Secure erase utilities.
* Performance benchmarking.
* Continuous SMART monitoring.
* Cloud synchronization.
* Automatic updates.
* User accounts.
* Telemetry.
* Plugin systems.
* Themes or appearance customization.
* General-purpose partition management.

---

# 4. Engineering Rule

Every proposed feature shall satisfy all of the following conditions:

1. It solves a real problem within the HDD validation workflow.
2. It does not violate any design principle defined in this document.
3. It does not unnecessarily increase implementation complexity.
4. It preserves deterministic behavior.
5. It improves reliability, safety or usability without compromising simplicity.

Features that fail any of these conditions shall not be implemented.

---

# 5. Design Philosophy

OldButGold is not a collection of disk utilities.

It is a deterministic validation workflow that integrates mature Linux tools into a single, consistent, transparent and conservative user experience.

Its purpose is not to replace trusted Linux utilities, but to orchestrate them through a standardized process that minimizes user error, maximizes reproducibility and presents only verifiable technical information.

Every engineering decision made within this project shall reinforce this philosophy.

