# PRODUCT_VISION.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Product Vision
> **Priority:** High

---

# 1. Purpose

OldButGold exists to provide a standardized, deterministic and user-friendly workflow for validating and preparing mechanical hard drives using trusted Linux utilities.

The application transforms a complex sequence of command-line operations into a single guided process while preserving technical accuracy, transparency and reproducibility.

OldButGold does not replace existing Linux tools. It orchestrates them into a reliable validation workflow.

---

# 2. Vision

To become the simplest and most trustworthy offline utility for validating, refurbishing and preparing mechanical hard drives before they are returned to service.

---

# 3. Mission

Provide a conservative validation workflow that:

* minimizes user error;
* maximizes validation reliability;
* presents only real technical information;
* remains simple enough for occasional users;
* remains trustworthy enough for experienced users.

---

# 4. Product Identity

OldButGold is a validation workflow.

It is not a disk utility collection.

It is not a benchmarking suite.

It is not a partition manager.

It is not a recovery application.

Its value comes from executing a predefined workflow correctly, consistently and safely.

---

# 5. Primary Goals

The application shall:

* identify every connected mechanical hard drive;
* protect devices that should not be modified;
* collect hardware information;
* validate drive health using SMART;
* execute Badblocks using predefined validation profiles;
* compare drive health before and after validation;
* prepare the drive with a new partition table and filesystem only after successful validation;
* generate a professional validation report;
* recover interrupted validation sessions whenever safe.

---

# 6. Target Users

OldButGold is intended for users who need to validate mechanical hard drives before reuse.

Typical scenarios include:

* refurbishing used HDDs;
* validating second-hand drives;
* preparing archive drives;
* preparing backup drives;
* testing drives acquired from unknown sources;
* validating external USB hard drives;
* validating SATA hard drives through adapters or docking stations.

The application is designed for both technical and non-technical users.

---

# 7. Supported Hardware

OldButGold supports only mechanical hard drives (HDD).

Supported connection methods include, but are not limited to:

* SATA;
* USB;
* USB-to-SATA adapters;
* external enclosures;
* docking stations;
* SAS adapters supported by Linux.

The connection method is irrelevant provided the operating system exposes the drive correctly.

---

# 8. Unsupported Hardware

The following devices are outside the project scope:

* SSD;
* NVMe SSD;
* USB flash drives;
* SD cards;
* eMMC devices;
* optical drives;
* RAID virtual devices;
* loop devices.

Such devices may be listed for informational purposes but shall not participate in the validation workflow.

---

# 9. Product Workflow

OldButGold executes a fixed validation pipeline.

The user does not assemble or customize the workflow.

The application is responsible for executing every stage in the correct order.

This guarantees consistency and reproducibility across all validated drives.

---

# 10. Validation Philosophy

Every drive follows the same fundamental process:

1. Detect the drive.
2. Identify the hardware.
3. Capture an initial SMART snapshot.
4. Execute SMART Short Self-Test.
5. Collect updated SMART information.
6. Execute Badblocks using the selected validation profile.
7. Capture a final SMART snapshot.
8. Compare SMART information before and after validation.
9. Create a new GPT partition table.
10. Create the selected filesystem.
11. Generate the final report.

If any mandatory stage fails, subsequent destructive stages shall not execute unless explicitly defined by the workflow.

---

# 11. Validation Profiles

The application provides only two validation profiles.

## Recommended

The official OldButGold validation profile.

Optimized for practical HDD refurbishment while balancing validation quality and execution time.

Recommended for nearly all users.

---

## Extended

Uses the complete Badblocks validation strategy as recommended by its original documentation.

Designed for users who require maximum validation coverage regardless of execution time.

---

# 12. Session Recovery

Validation sessions exist exclusively to recover interrupted workflows.

If a validation is interrupted, the application shall:

* identify the drive;
* verify its fingerprint;
* validate session integrity;
* allow the user to recover or discard the interrupted session.

Recovery shall always restart from an internal safety margin rather than assuming the last recorded position is fully valid.

---

# 13. User Experience

The application shall require as few decisions as possible.

The user should never need to understand:

* SMART commands;
* Badblocks parameters;
* sector alignment;
* partition alignment;
* command-line utilities;
* Linux storage internals.

The application translates technical complexity into a guided workflow without hiding important information.

---

# 14. Reports

Every successful validation may produce a Markdown report.

The report documents the executed workflow and observed results.

Reports describe facts only.

They never predict future reliability or certify the drive.

---

# 15. Product Boundaries

OldButGold intentionally avoids becoming a general-purpose storage utility.

The application shall never expand into unrelated domains such as:

* performance benchmarking;
* file recovery;
* cloning;
* disk imaging;
* partition editing;
* filesystem repair;
* storage monitoring;
* system administration.

Maintaining a narrow scope is fundamental to the product identity.

---

# 16. Product Values

OldButGold is built around five core values:

* Simplicity.
* Transparency.
* Safety.
* Determinism.
* Reliability.

Every feature, workflow and implementation decision shall reinforce these values.

---

# 17. Success Criteria

The product succeeds when a user can validate and prepare a mechanical hard drive through a single guided workflow without needing to understand the underlying Linux utilities, while still receiving complete, accurate and verifiable technical information throughout the entire process.

---

# 18. Vision Statement

OldButGold delivers a professional, deterministic and conservative HDD validation workflow by orchestrating trusted Linux utilities into a single offline application that is simple to use, technically transparent and focused exclusively on mechanical hard drive validation.

