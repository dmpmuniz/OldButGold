# SESSION_RECOVERY_SPECIFICATION.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Session Recovery Specification
> **Priority:** High

---

# 1. Purpose

This document defines the session recovery mechanism.

Its objective is to allow interrupted validations to resume safely without restarting the entire Badblocks execution.

---

# 2. Session Creation

A session shall be created automatically immediately before Badblocks starts.

No manual action is required.

---

# 3. Session Identifier

Each session shall receive a unique identifier.

The identifier shall contain at least:

* session UUID;
* creation timestamp.

---

# 4. Disk Fingerprint

Each session shall permanently store the validated device identity.

The fingerprint shall include every stable identifier available, including:

* manufacturer;
* model;
* serial number;
* firmware version;
* capacity;
* logical sector size;
* physical sector size.

Linux device names (e.g. `/dev/sda`) shall never be used as the primary identifier.

---

# 5. Checkpoints

Progress shall be saved periodically.

The default checkpoint interval shall be every 10% of completed work.

Additional checkpoints may be written during graceful shutdown.

---

# 6. Resume Validation

When the same physical disk is detected again, OldButGold shall automatically offer:

* Continue Validation
* Start From Beginning

No automatic resume shall occur without user confirmation.

---

# 7. Resume Safety

Resume shall only be allowed when the fingerprint matches the original session.

If any critical identifier differs, the session shall be rejected.

---

# 8. Resume Offset

Validation shall resume slightly before the last confirmed checkpoint.

This safety margin compensates for possible incomplete writes immediately before interruption.

---

# 9. Multiple Sessions

Multiple interrupted sessions may coexist.

Each session is independent.

The application shall identify the correct session by disk fingerprint.

---

# 10. Session Cleanup

Sessions shall be removed automatically when:

* validation completes successfully;
* user chooses "Start From Beginning";
* user explicitly deletes the session.

---

# 11. Interrupted Devices

Typical interruption causes include:

* power loss;
* USB disconnection;
* kernel reset;
* application crash;
* user interruption.

The recovery mechanism shall treat all interruption causes identically.

---

# 12. Engineering Rule

Session recovery exists only to continue interrupted validations safely.

It shall never modify completed validation results or reuse SMART snapshots from previous independent validation sessions.

