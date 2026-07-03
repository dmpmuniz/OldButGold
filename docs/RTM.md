# Requirement Traceability Matrix (RTM)

> **Project:** OldButGold V1
> **Generated:** Phase 1 — Project Discovery
> **Status:** Internal Working Document

---

## Legend

| State | Meaning |
|-------|---------|
| Not Started | Requirement identified, no implementation begun |
| In Progress | Implementation actively underway |
| Implemented | Code written, awaiting review |
| Reviewed | Code reviewed against specification |
| Validated | Acceptance test passed |
| Blocked | Cannot proceed (dependency or ambiguity) |

> **Note:** File paths in this RTM were updated to reflect the current `obg/` structure.
> See `COMPLIANCE_AUDIT.md` for the authoritative implementation mapping.

---

## RTM-01: Application Startup (Stage 1)

| Field | Value |
|-------|-------|
| **ID** | RTM-001 |
| **Source** | MASTER_SPECIFICATION §6 Stage 1 |
| **Acceptance Test** | A-001, A-002, A-003 |
| **Dependencies** | RTM-011 (Tool Verification) |
| **Status** | Implemented |

**Implementation:** `obg/__main__.py` + `obg/ui/app.py` StartupScreen

**Requirements:**
- Initialize runtime
- Verify bundled tools
- Detect available devices
- Display legal disclaimer while device detection executes in background
- No user interaction before initialization completes

---

## RTM-02: Device Discovery (Stage 2)

| Field | Value |
|-------|-------|
| **ID** | RTM-002 |
| **Source** | MASTER_SPECIFICATION §6 Stage 2 |
| **Acceptance Test** | B-001, B-002, B-003, B-004 |
| **Dependencies** | RTM-011 (Tool Verification) |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Enumerate every supported block device
- Obtain immediately available information without diagnostic tests
- Displayed information shall prioritize user identification
- Supported: SATA, USB, USB-to-SATA, enclosures, docking stations, SAS
- Unsupported devices displayed but not selectable (SSD, NVMe, USB flash, SD, eMMC, optical, virtual, RAID)

---

## RTM-03: Protected Devices

| Field | Value |
|-------|-------|
| **ID** | RTM-003 |
| **Source** | MASTER_SPECIFICATION §5 |
| **Acceptance Test** | B-003 |
| **Dependencies** | RTM-002 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Auto-protect system drive, boot device, Linux installation drive, unsupported removable devices, read-only devices
- Protected devices clearly identified
- Protected devices never enter validation workflow

---

## RTM-04: Session Detection (Stage 3)

| Field | Value |
|-------|-------|
| **ID** | RTM-004 |
| **Source** | MASTER_SPECIFICATION §6 Stage 3 |
| **Acceptance Test** | C-001, C-002 |
| **Dependencies** | RTM-002, RTM-016 (Session System) |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Determine whether selected drive has interrupted validation session
- If no session, proceed normally
- If session exists, user decides how to proceed

---

## RTM-05: Session Decision (Stage 4)

| Field | Value |
|-------|-------|
| **ID** | RTM-005 |
| **Source** | MASTER_SPECIFICATION §6 Stage 4 |
| **Acceptance Test** | C-003, C-004, C-005 |
| **Dependencies** | RTM-004 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Offer: Recover Validation, Restart Validation, View Session Details, Return
- Application shall never choose automatically

---

## RTM-06: Drive Identification (Stage 5)

| Field | Value |
|-------|-------|
| **ID** | RTM-006 |
| **Source** | MASTER_SPECIFICATION §6 Stage 5, DESIGN_PRINCIPLES §Principle 10 |
| **Acceptance Test** | B-004, C-003, C-005 |
| **Dependencies** | RTM-002 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Uniquely identify HDD using hardware fingerprint
- Fingerprint independent of Linux device name, USB port, SATA port, enumeration order
- Fingerprint includes: manufacturer, model, serial number, firmware version, capacity, logical/physical sector size

---

## RTM-07: Initial SMART Collection (Stage 6)

| Field | Value |
|-------|-------|
| **ID** | RTM-007 |
| **Source** | MASTER_SPECIFICATION §6 Stage 6 |
| **Acceptance Test** | D-001 |
| **Dependencies** | RTM-006 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Collect initial SMART snapshot before any diagnostic operation
- Serves as baseline for later comparison

---

## RTM-08: SMART Short Self-Test (Stage 7)

| Field | Value |
|-------|-------|
| **ID** | RTM-008 |
| **Source** | MASTER_SPECIFICATION §6 Stage 7 |
| **Acceptance Test** | D-002, D-003 |
| **Dependencies** | RTM-007 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Execute SMART Short Self-Test
- Collect SMART information again after completion
- Present updated information to user before validation configuration

---

## RTM-09: Validation Configuration (Stage 8)

| Field | Value |
|-------|-------|
| **ID** | RTM-009 |
| **Source** | MASTER_SPECIFICATION §6 Stage 8 |
| **Acceptance Test** | E-001, E-002, E-003 |
| **Dependencies** | RTM-008 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Validation Profile: Recommended, Extended
- Filesystem: EXT4, NTFS, exFAT, FAT32
- Volume Label (optional)
- No additional parameters exposed

---

## RTM-10: Final Confirmation (Stage 9)

| Field | Value |
|-------|-------|
| **ID** | RTM-010 |
| **Source** | MASTER_SPECIFICATION §6 Stage 9 |
| **Acceptance Test** | F-001, F-002, F-003 |
| **Dependencies** | RTM-009 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Display: selected drive, validation profile, filesystem, volume label
- Clear warning: all existing data permanently destroyed
- Execution begins only after explicit confirmation

---

## RTM-11: Badblocks Validation (Stage 10)

| Field | Value |
|-------|-------|
| **ID** | RTM-011 |
| **Source** | MASTER_SPECIFICATION §6 Stage 10 |
| **Acceptance Test** | G-001, G-002, G-003, G-004 |
| **Dependencies** | RTM-010, RTM-015 (Profiles) |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Execute Badblocks according to selected validation profile
- Continuously collect execution progress
- Only actual execution data displayed
- Artificial progress indicators prohibited

---

## RTM-12: Final SMART Collection (Stage 11)

| Field | Value |
|-------|-------|
| **ID** | RTM-012 |
| **Source** | MASTER_SPECIFICATION §6 Stage 11 |
| **Acceptance Test** | D-004, D-005 |
| **Dependencies** | RTM-011 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Collect new SMART snapshot immediately after Badblocks completes
- Compare against initial snapshot
- Identify observed changes
- No additional SMART self-test at this stage

---

## RTM-13: Drive Preparation (Stage 12)

| Field | Value |
|-------|-------|
| **ID** | RTM-013 |
| **Source** | MASTER_SPECIFICATION §6 Stage 12 |
| **Acceptance Test** | H-001, H-002, H-003 |
| **Dependencies** | RTM-011 (must complete successfully) |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Execute only if validation completes successfully
- Create GPT partition table
- Create one partition occupying full drive
- Create selected filesystem
- Apply selected volume label
- Partition alignment automatic, no manual options

---

## RTM-14: Report Generation (Stage 13)

| Field | Value |
|-------|-------|
| **ID** | RTM-014 |
| **Source** | MASTER_SPECIFICATION §6 Stage 13, REPORT_SPECIFICATION |
| **Acceptance Test** | I-001, I-002, I-003 |
| **Dependencies** | RTM-013, RTM-012 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Generate Markdown report only
- Report naming: OldButGold-YYYYMMDD-HHMMSS-<DeviceModel>.md
- 9 sections in exact order (Summary, Device ID, SMART Comparison, Config, Badblocks, Filesystem, Timeline, Assessment, Disclaimer)
- Only observed facts, no predictions
- Legal disclaimer mandatory

---

## RTM-15: Validation Profiles

| Field | Value |
|-------|-------|
| **ID** | RTM-015 |
| **Source** | MASTER_SPECIFICATION §7, PRODUCT_VISION §11 |
| **Acceptance Test** | E-001, G-001, G-002 |
| **Dependencies** | None |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Exactly two profiles: Recommended, Extended
- Recommended: optimized for practical refurbishment
- Extended: complete Badblocks methodology, maximum coverage

---

## RTM-16: Session System

| Field | Value |
|-------|-------|
| **ID** | RTM-016 |
| **Source** | MASTER_SPECIFICATION §8, SESSION_RECOVERY_SPECIFICATION |
| **Acceptance Test** | C-001 through C-005, L-001, L-002 |
| **Dependencies** | RTM-006 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Each HDD owns one independent session
- Session associated with HDD fingerprint
- Sessions independent of PIDs, device names, USB topology
- Unique identifier: UUID + creation timestamp
- Disk fingerprint: manufacturer, model, serial, firmware, capacity, sector sizes
- Checkpoints every 10% of completed work
- Graceful shutdown additional checkpoints

---

## RTM-17: Session Recovery

| Field | Value |
|-------|-------|
| **ID** | RTM-017 |
| **Source** | MASTER_SPECIFICATION §9, SESSION_RECOVERY_SPECIFICATION §6-8 |
| **Acceptance Test** | C-003, C-005, L-001, L-002 |
| **Dependencies** | RTM-016 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Resume only after fingerprint validation, session integrity verification, compatibility verification
- Resume from internal safety rollback (implementation detail, not user-configurable)
- Resume slightly before last confirmed checkpoint
- Multiple interrupted sessions may coexist
- Session cleanup on successful completion, restart, or explicit deletion

---

## RTM-18: Error Handling

| Field | Value |
|-------|-------|
| **ID** | RTM-018 |
| **Source** | MASTER_SPECIFICATION §13 |
| **Acceptance Test** | Implicit in all error-path tests |
| **Dependencies** | None |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Stop affected workflow on failure
- Explain the failure
- Preserve recoverable session data when applicable
- Avoid executing dependent stages
- Never silently ignore failures

---

## RTM-19: Progress Reporting

| Field | Value |
|-------|-------|
| **ID** | RTM-019 |
| **Source** | MASTER_SPECIFICATION §12, UI_GUIDELINES §13-15 |
| **Acceptance Test** | G-003, G-004, K-004 |
| **Dependencies** | RTM-011 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Display: current stage, operation, completed stages, failed stages, overall progress, stage progress, estimated remaining time, elapsed time, throughput, processed data
- Only actual execution data
- Pipeline visualization with ✓ (green), ▶ (highlighted), ✗ (red), □ (neutral)

---

## RTM-20: Classification Engine

| Field | Value |
|-------|-------|
| **ID** | RTM-020 |
| **Source** | CLASSIFICATION_SPECIFICATION |
| **Acceptance Test** | Implicit in report tests |
| **Dependencies** | RTM-012, RTM-011, RTM-013 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Four levels: Gold, Silver, Bronze, Failed
- Gold: all conditions met (SMART Short success x2, no degradation, Badblocks success, no bad blocks, filesystem created, no interruption)
- Silver: successful validation, no bad blocks, filesystem success, but non-critical SMART observations
- Bronze: validation completes but bad blocks detected or SMART degradation
- Failed: validation cannot complete
- Only one classification per validation
- No predictions or guarantees

---

## RTM-21: Tool Execution & Bundle

| Field | Value |
|-------|-------|
| **ID** | RTM-021 |
| **Source** | TOOLCHAIN_SPECIFICATION, ENGINEERING_GUIDELINES §7-8 |
| **Acceptance Test** | M-001, M-002, M-003 |
| **Dependencies** | None |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Self-contained: no host package installation required
- Runtime isolation: never execute host-installed tools
- All tools invoked via explicit paths from tools/
- Libraries loaded from lib/
- Verify: executable exists, utilities exist, libraries exist, files executable
- Missing components prevent execution
- Alpine Linux packages as source
- No PATH resolution

---

## RTM-22: Privilege Escalation

| Field | Value |
|-------|-------|
| **ID** | RTM-022 |
| **Source** | ENGINEERING_GUIDELINES §10 |
| **Acceptance Test** | A-001 |
| **Dependencies** | RTM-021 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Request administrative privileges only once via pkexec
- Entire validation workflow executes within elevated runtime
- No repeated password prompts

---

## RTM-23: UI Layer

| Field | Value |
|-------|-------|
| **ID** | RTM-023 |
| **Source** | UI_GUIDELINES (all sections) |
| **Acceptance Test** | K-001 through K-005 |
| **Dependencies** | RTM-001 through RTM-014 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Simple, deterministic, keyboard-first, information-oriented, distraction-free
- No theme selector, appearance customization, command console, advanced menus, hidden options, plugin manager, settings, config wizard, startup assistant
- 9 screens: Startup, Drive Selection, Session Decision, Drive Info (4-panel), Validation Config, Final Confirmation, Execution, Complete, Export
- Keyboard navigation: ↑↓, ←→, Enter, Esc, Tab, Shift+Tab, Space, R
- Mouse support equivalent to keyboard
- Pipeline display on execution screen
- Mature native Linux aesthetic

---

## RTM-24: Workflow Controller

| Field | Value |
|-------|-------|
| **ID** | RTM-024 |
| **Source** | ENGINEERING_GUIDELINES §21 |
| **Acceptance Test** | All workflow tests |
| **Dependencies** | RTM-001 through RTM-014 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Sequence stages, enforce order, validate transitions, prevent invalid paths
- Every workflow transition explicit
- Pipeline fixed, no reordering, no skipping, no optional workflows

---

## RTM-25: Build & Release

| Field | Value |
|-------|-------|
| **ID** | RTM-025 |
| **Source** | BUILD_RELEASE_SPECIFICATION |
| **Acceptance Test** | Release verification |
| **Dependencies** | RTM-021 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Single distributable directory
- Bundle: app + tools + libs + assets + docs
- ZIP packaging with single nested directory
- One executable entry point
- Deterministic builds
- Pre-release validation: build + acceptance tests + runtime verification + doc consistency

---

## RTM-26: Logging

| Field | Value |
|-------|-------|
| **ID** | RTM-026 |
| **Source** | ENGINEERING_GUIDELINES §18, MASTER_SPECIFICATION §16 |
| **Acceptance Test** | Implicit |
| **Dependencies** | None |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Diagnostic logging for troubleshooting
- Structured: timestamps, stages, tools, failures, warnings, recovery events
- Logs not part of validation report
- Logs never replace Markdown report

---

## RTM-27: Device Locking

| Field | Value |
|-------|-------|
| **ID** | RTM-027 |
| **Source** | ENGINEERING_GUIDELINES §14 |
| **Acceptance Test** | L-003, L-004 |
| **Dependencies** | RTM-006 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Acquire exclusive lock for selected HDD before validation
- If another instance owns lock, deny validation with clear explanation
- Multiple instances validating different HDDs fully supported

---

## RTM-28: Cleanup

| Field | Value |
|-------|-------|
| **ID** | RTM-028 |
| **Source** | MASTER_SPECIFICATION §6 Stage 14, DESIGN_PRINCIPLES §13 |
| **Acceptance Test** | J-001, J-002, J-003 |
| **Dependencies** | RTM-014 |
| **Status** | Implemented |

**Implementation:** See COMPLIANCE_AUDIT.md for authoritative path mapping

**Requirements:**
- Remove checkpoints, temporary files, session metadata on successful completion
- Preserve only exported reports and optional diagnostic logs
- Restart removes discarded session
- Interrupted session preserves only recovery-required data

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Total Requirements | 28 |
| Not Started | 0 |
| In Progress | 0 |
| Implemented | 28 |
| Reviewed | 0 |
| Validated | 0 |
| Blocked | 0 |
