# MASTER_SPECIFICATION.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Functional Specification
> **Priority:** High

---

# 1. Purpose

This document defines the functional behavior of OldButGold.

It specifies what the application shall do, how the validation workflow shall behave and which rules govern every stage of execution.

Implementation details are intentionally excluded.

---

# 2. Scope

OldButGold validates and prepares mechanical hard drives through a predefined workflow.

The workflow is fixed.

The application does not allow users to build or modify validation pipelines.

---

# 3. Supported Devices

The application shall support mechanical hard drives connected through any Linux-supported interface, including but not limited to:

* SATA
* USB
* USB-to-SATA bridges
* External enclosures
* Docking stations
* SAS adapters

Connection type shall not affect the validation workflow.

---

# 4. Unsupported Devices

The application shall not validate:

* SSD
* NVMe
* USB flash drives
* SD cards
* eMMC
* Optical drives
* Virtual block devices
* RAID virtual devices

Unsupported devices may be displayed but shall not be selectable.

---

# 5. Protected Devices

The application shall automatically protect devices that should never be modified.

Examples include:

* current system drive;
* current boot device;
* Linux installation drive;
* removable devices identified as unsupported;
* read-only devices.

Protected devices shall be clearly identified.

Protected devices shall never enter the validation workflow.

---

# 6. Workflow

The validation pipeline is fixed.

Every supported drive shall execute the following stages in order.

---

## Stage 1 — Application Startup

The application shall:

* initialize the runtime;
* verify bundled tools;
* detect available devices;
* display the legal disclaimer while device detection executes in the background.

No user interaction shall occur before initialization completes.

---

## Stage 2 — Device Discovery

The application shall enumerate every supported block device.

For each detected drive, the application shall obtain every piece of information that is immediately available without executing diagnostic tests.

Displayed information shall prioritize user identification of the drive.

---

## Stage 3 — Session Detection

Before allowing validation, the application shall determine whether the selected drive has an interrupted validation session.

If no session exists, the workflow proceeds normally.

If a session exists, the user shall decide how to proceed.

---

## Stage 4 — Session Decision

If an interrupted validation exists, the application shall offer:

* Recover Validation
* Restart Validation
* View Session Details
* Return

The application shall never choose automatically.

---

## Stage 5 — Drive Identification

The application shall uniquely identify the selected HDD using its hardware fingerprint.

The fingerprint shall be independent of:

* Linux device name;
* USB port;
* SATA port;
* enumeration order.

---

## Stage 6 — Initial SMART Collection

The application shall collect an initial SMART snapshot before any diagnostic operation.

This snapshot serves as the baseline for later comparison.

---

## Stage 7 — SMART Short Self-Test

The application shall execute a SMART Short Self-Test.

After completion, SMART information shall be collected again.

The updated information shall be presented to the user before validation configuration.

---

## Stage 8 — Validation Configuration

The user may configure only:

Validation Profile:

* Recommended
* Extended

Filesystem:

* EXT4
* NTFS
* exFAT
* FAT32

Volume Label (optional).

No additional validation parameters shall be exposed.

---

## Stage 9 — Final Confirmation

Before destructive operations begin, the application shall display:

* selected drive;
* selected validation profile;
* selected filesystem;
* selected label;
* clear warning that all existing data will be permanently destroyed.

Execution shall begin only after explicit confirmation.

---

## Stage 10 — Badblocks Validation

The application shall execute Badblocks according to the selected validation profile.

The application shall continuously collect execution progress.

Only actual execution data may be displayed.

Artificial progress indicators are prohibited.

---

## Stage 11 — Final SMART Collection

Immediately after Badblocks completes, the application shall:

* collect a new SMART snapshot;
* compare it against the initial snapshot;
* identify any observed changes.

No additional SMART self-test shall be executed at this stage.

---

## Stage 12 — Drive Preparation

Drive preparation shall execute only if validation completes successfully.

Preparation consists of:

1. Create GPT partition table.
2. Create one partition occupying the full drive.
3. Create the selected filesystem.
4. Apply the selected volume label.

Partition alignment shall be automatic.

No manual alignment options shall exist.

---

## Stage 13 — Report Generation

After successful completion, the application shall generate the validation report.

The report shall contain only observed facts.

No predictive statements shall be included.

---

## Stage 14 — Session Cleanup

When validation completes successfully, the application shall:

* remove checkpoints;
* remove temporary files;
* remove session metadata;
* preserve only exported reports and optional diagnostic logs.

---

# 7. Validation Profiles

Exactly two validation profiles shall exist.

---

## Recommended

Official OldButGold validation profile.

Optimized for practical refurbishment.

Recommended for normal use.

---

## Extended

Uses the complete Badblocks validation methodology.

Designed for maximum validation coverage.

---

# 8. Validation Sessions

Each HDD owns one independent validation session.

Sessions are associated with the HDD fingerprint.

Sessions shall never depend on:

* process identifiers;
* Linux device names;
* USB topology.

---

# 9. Session Recovery

Recovery shall execute only after:

* fingerprint validation;
* session integrity verification;
* compatibility verification.

Recovery shall restart from an internal safety rollback.

The rollback value is an implementation detail.

Users shall not configure it.

---

# 10. Restart Validation

Restart Validation shall:

* discard the interrupted session;
* remove checkpoints;
* remove temporary artifacts;
* create a completely new validation session.

No data from the discarded session shall influence the new validation.

---

# 11. Session Cleanup

If the user chooses to discard an interrupted validation session, every associated temporary artifact shall be permanently removed.

---

# 12. Progress Reporting

During execution, the application shall display only real execution information.

Whenever available, the interface shall present:

* current stage;
* current operation;
* completed stages;
* failed stages;
* overall progress;
* stage progress;
* estimated remaining time;
* elapsed time;
* throughput;
* processed data.

Displayed values shall originate from actual execution.

---

# 13. Error Handling

Whenever a stage fails, the application shall:

* stop the affected workflow;
* explain the failure;
* preserve recoverable session data whenever applicable;
* avoid executing dependent stages.

The application shall never silently ignore failures.

---

# 14. Reports

Reports shall be generated in Markdown only.

Report generation is optional.

The user may export the report or exit without exporting.

Reports shall contain only factual technical information.

---

# 15. Classification

The application shall classify validation results using predefined categories.

Each category shall include:

* classification name;
* short technical description;
* observed validation outcome.

Classification shall never imply future reliability guarantees.

---

# 16. Logging

Diagnostic logging may be maintained during execution.

Logs exist solely for troubleshooting.

Logs are not part of the validation report.

---

# 17. General Rules

The application shall never:

* invent values;
* estimate unavailable information;
* execute undocumented behavior;
* expose unnecessary technical parameters;
* continue interrupted validation without verification;
* modify protected devices;
* perform destructive operations without confirmation.

---

# 18. Completion

A validation is considered complete only when all mandatory workflow stages finish successfully.

Any interruption before completion shall produce an interrupted validation session eligible for recovery according to the rules defined in this specification.

