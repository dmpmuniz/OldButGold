# ACCEPTANCE_TESTS.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Acceptance Test Specification
> **Priority:** Medium

---

# 1. Purpose

This document defines the acceptance criteria required before an OldButGold release can be considered production-ready.

Every requirement described in the higher-priority specification documents shall be verifiable through objective testing.

Any failed acceptance test shall block the release.

---

# 2. General Acceptance Criteria

The application shall:

* complete installation without additional system packages;
* execute from the distributed bundle;
* operate entirely offline;
* require only one privilege escalation;
* follow the complete validation workflow;
* generate deterministic results;
* produce only real technical information.

---

# 3. Startup

### Test A-001 — Application Launch

**Objective**

Verify that the application starts correctly.

**Expected Result**

* Application launches successfully.
* Runtime initializes.
* Bundled tools are detected.
* Disclaimer screen is displayed.
* Device discovery starts automatically.

---

### Test A-002 — Continue Button

**Objective**

Verify initialization behavior.

**Expected Result**

Continue remains unavailable until initialization completes.

---

### Test A-003 — Exit

**Objective**

Verify application shutdown.

**Expected Result**

Application closes without leaving temporary runtime artifacts.

---

# 4. Device Detection

### Test B-001 — HDD Enumeration

Verify that all supported HDDs are detected.

---

### Test B-002 — Unsupported Devices

Verify that SSDs, NVMe drives and unsupported devices cannot enter the validation workflow.

---

### Test B-003 — Protected Devices

Verify that protected devices are clearly identified and cannot be selected.

---

### Test B-004 — Drive Information

Verify that every detected HDD displays sufficient identification information for reliable user selection.

---

# 5. Session Recovery

### Test C-001 — No Session

Selecting a drive without an interrupted session shall immediately continue the workflow.

---

### Test C-002 — Interrupted Session

An interrupted validation shall be detected automatically.

---

### Test C-003 — Recover

Recovery shall resume only after fingerprint verification succeeds.

---

### Test C-004 — Restart

Restart shall permanently discard the interrupted session and begin a completely new validation.

---

### Test C-005 — Wrong Drive

Recovery shall be denied when the detected HDD fingerprint differs from the stored session.

---

# 6. SMART

### Test D-001 — Initial Snapshot

Verify that an initial SMART snapshot is collected before the SMART Short Self-Test.

---

### Test D-002 — SMART Short

Verify that the SMART Short Self-Test executes successfully.

---

### Test D-003 — Updated Snapshot

Verify that SMART information is collected again immediately after the SMART Short completes.

---

### Test D-004 — Final Snapshot

Verify that a final SMART snapshot is collected immediately after Badblocks completes.

---

### Test D-005 — SMART Comparison

Verify that the report compares the initial and final SMART snapshots.

---

# 7. Validation Configuration

### Test E-001 — Validation Profiles

Verify that only:

* Recommended
* Extended

are available.

---

### Test E-002 — Filesystems

Verify that only:

* EXT4
* NTFS
* exFAT
* FAT32

are available.

---

### Test E-003 — Volume Label

Verify that the volume label is optional.

---

# 8. Confirmation

### Test F-001 — Final Warning

Verify that the confirmation screen clearly states that all existing data will be permanently destroyed.

---

### Test F-002 — Cancel

Verify that cancelling returns to the previous screen.

---

### Test F-003 — Confirm

Verify that destructive operations begin only after explicit confirmation.

---

# 9. Badblocks

### Test G-001 — Recommended Profile

Verify that the Recommended profile executes correctly.

---

### Test G-002 — Extended Profile

Verify that the Extended profile executes correctly.

---

### Test G-003 — Real Progress

Verify that displayed progress corresponds to actual execution.

Artificial progress is prohibited.

---

### Test G-004 — Stage Information

Verify that the current operation accurately reflects the work being performed.

Examples include:

* Reading
* Writing
* Verifying

Generic status messages are not acceptable.

---

# 10. Drive Preparation

### Test H-001 — GPT Creation

Verify that GPT is created only after successful validation.

---

### Test H-002 — Filesystem Creation

Verify that the selected filesystem is created successfully.

---

### Test H-003 — Volume Label

Verify that the selected label is applied correctly.

---

# 11. Reports

### Test I-001 — Markdown Export

Verify successful Markdown report generation.

---

### Test I-002 — Report Accuracy

Verify that every reported value corresponds to actual collected information.

---

### Test I-003 — Report Content

Verify that no predictive statements or future reliability guarantees appear in the report.

---

# 12. Cleanup

### Test J-001 — Successful Completion

Verify that completed validation sessions remove all temporary artifacts.

---

### Test J-002 — Restart Cleanup

Verify that restarting validation removes the discarded session.

---

### Test J-003 — Interrupted Session

Verify that interrupted validation preserves only the data required for recovery.

---

# 13. User Interface

### Test K-001 — Keyboard Navigation

Verify that every screen is fully operable using the keyboard.

---

### Test K-002 — Mouse Navigation

Verify equivalent behavior using the mouse.

---

### Test K-003 — Drive Highlight

Verify that the selected drive is visually highlighted.

---

### Test K-004 — Pipeline

Verify that:

* completed stages display a green check;
* failed stages display a red X;
* the current stage is highlighted.

---

### Test K-005 — Information Layout

Verify that drive information is displayed using the four-panel layout defined in the UI specification.

---

# 14. Reliability

### Test L-001 — Unexpected Termination

Interrupt the application during Badblocks.

Verify that recovery is available.

---

### Test L-002 — USB Disconnect

Disconnect an external HDD during validation.

Verify that the session enters a recoverable state.

---

### Test L-003 — Multiple Instances

Launch multiple application instances validating different HDDs.

Verify that independent sessions execute correctly.

---

### Test L-004 — Duplicate Validation

Attempt to validate the same HDD simultaneously from two application instances.

The second validation shall be refused.

---

# 15. Bundle

### Test M-001 — Self-Contained Distribution

Verify that all bundled tools execute correctly without installing additional packages.

---

### Test M-002 — Offline Operation

Disconnect network access.

Verify that the complete workflow continues normally.

---

### Test M-003 — Distribution Independence

Verify successful execution on supported Linux distributions without workflow changes.

---

# 16. Regression Requirements

Every release shall successfully pass every acceptance test defined in this document.

No previously passing acceptance test may fail after introducing new functionality.

---

# 17. Release Criteria

A release is eligible for production only when:

* every mandatory acceptance test passes;
* no critical defects remain open;
* no workflow stage violates the project specifications;
* all reports contain only verified technical information;
* deterministic behavior is preserved.

Failure to satisfy any of these conditions shall prevent release.

