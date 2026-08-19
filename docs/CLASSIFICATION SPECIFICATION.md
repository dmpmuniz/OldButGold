# CLASSIFICATION_SPECIFICATION.md

> **Document Status:** Draft v1.0
> **Project:** OldButGold – HDD Revival Toolkit
> **Document Type:** Disk Classification Specification
> **Priority:** High

---

# 1. Purpose

This document defines the official classification system used by OldButGold.

The objective is to provide a simple, deterministic and repeatable assessment of the validation results.

The classification is intended to summarize the observed validation session only.

It is **not** a prediction of future reliability.

---

# 2. General Principles

Classification is based exclusively on observed data collected during execution.

No inference or prediction shall influence the classification.

Every execution shall produce the same classification when identical results are obtained.

---

# 3. Classification Levels

OldButGold defines five official classifications:

* Gold
* Silver
* Bronze
* Bad
* Failed

No additional classifications shall exist.

---

# 4. Gold

A disk shall receive **Gold** only when all of the following conditions are satisfied:

* SMART Short completed successfully before validation.
* SMART Short completed successfully after validation.
* SMART comparison shows no relevant degradation.
* Badblocks completed successfully.
* No bad blocks detected.
* Filesystem successfully created.
* Validation completed without interruption.

Gold does **not** guarantee future reliability.

---

# 5. Silver

A disk shall receive **Silver** when:

* validation completed successfully;
* no bad blocks were detected;
* filesystem creation succeeded;

but one or more non-critical SMART observations require user attention.

Examples include:

* aging indicators;
* elevated power-on hours;
* historical SMART warnings that remained unchanged.

Silver indicates a successful validation with observed conditions that deserve monitoring.

---

# 6. Bronze

A disk shall receive **Bronze** when validation completes but the observed condition indicates that the device should not be trusted for important data.

Typical examples include:

* one or more bad blocks detected;
* SMART degradation observed during comparison;
* filesystem successfully created despite detected media defects.

Bronze indicates that the disk may still be usable for non-critical purposes.

---

# 7. Failed

A disk shall receive **Failed** whenever validation cannot be successfully completed.

Examples include:

* SMART failure;
* Badblocks aborted;
* unreadable media;
* device disconnected;
* filesystem creation failed;
* unrecoverable execution errors.

No further interpretation shall be provided.

---

# 7a. Bad

A disk shall receive **Bad** when validation completes but the observed condition condemns the device for reliable use.

A disk is Bad when any of the following is observed after validation:

* one or more bad blocks detected by badblocks;
* SMART attribute 5 (Reallocated Sector Count), 197 (Current Pending Sector) or 198 (Offline Uncorrectable) is `FAILING_NOW` — the drive's own manufacturer threshold has been exceeded;
* SMART overall-health self-assessment result is `FAILED`.

Bad indicates the disk should not be trusted with data, even for archival use.

---

# 7b. Near-Threshold and Interface Warnings

When a monitored attribute has wear (raw value > 0) and its normalized value is within 10 points of the manufacturer threshold, the disk receives Bronze with a warning that the drive is approaching its manufacturer limit.

When UDMA CRC interface errors (attributes 187/199) are present, an informative cable warning is added to the reasons of any classification. It never changes the classification by itself.

---

# 8. Classification Rules

Only one classification may be assigned.

Multiple classifications are prohibited.

---

# 9. User Communication

The classification shall be presented together with a concise explanation.

Example:

**Gold**

> Validation completed successfully. No bad blocks detected. SMART remained stable throughout the validation session.

---

# 10. Engineering Rule

Classifications are summaries of observed execution.

They shall never be interpreted as:

* certification;
* warranty;
* guarantee;
* prediction.

Only measured results determine the assigned classification.

