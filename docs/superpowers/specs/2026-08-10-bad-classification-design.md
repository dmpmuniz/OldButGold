# Design: BAD classification + manufacturer thresholds (v1.0.0)

Date: 2026-08-10
Status: Approved verbally by user; written for the record (not committed yet — user holds commit until his own tests pass)

## Problem

- A disk with 100+ reallocated sectors received BRONZE, same as a disk with 7. No ceiling exists: BRONZE covers `reallocated > 5` to infinity.
- Bad blocks > 0 already disqualify GOLD/SILVER, but 1 and 10,000 bad blocks are both BRONZE.
- SILVER never checks `uncorrectable_sectors` — a disk with uncorrectable > 0 can be SILVER.

## Decisions (user-approved)

1. **New 5th classification `BAD`** — validation completed but the disk is condemned.
2. **Source of the "safe number": manufacturer threshold** — parsed from smartctl `THRESH`/`WHEN_FAILED` columns (normalized VALUE <= THRESH → `FAILING_NOW`).
3. **Passed = BAD; near = BRONZE warning** — proximity = normalized `VALUE - THRESH <= 10` (only when raw > 0 for that attribute).
4. **Any bad block (> 0) = BAD.**
5. **Attributes monitored: 5 (Reallocated_Sector_Ct), 197 (Current_Pending_Sector), 198 (Offline_Uncorrectable).**
6. **Fix SILVER gap: require `uncorrectable_sectors == 0`.**
7. **Cable warning**: UDMA CRC errors (max of attrs 187/199) > 0 → informative reason on any classification, never changes the class.
8. **SMART overall FAILED after validation moves from FAILED to BAD** (validation completed; verdict is condemned, not interrupted). FAILED remains execution-failure only.
9. NVMe out of scope (not a validation target since v0.11.0).

## New hierarchy (evaluation order)

1. **FAILED** — validation did not complete (interrupted, filesystem failed, final SMART unavailable).
2. **BAD** — bad blocks > 0, OR FAILING_NOW on 5/197/198, OR SMART overall FAILED after validation.
3. **GOLD** — unchanged (all zero, PASSED before/after, no delta).
4. **SILVER** — unchanged + `uncorrectable_sectors == 0` (gap fixed).
5. **BRONZE** — everything else: 1–5 reallocated, pending/uncorrectable > 0 (not FAILING_NOW), wear delta during test, near-threshold warning, cable warning.

## Data model (obg/models/disk.py)

```python
@dataclass
class SmartAttribute:
    value: int        # normalized
    worst: int
    thresh: int
    when_failed: str  # "-" | "FAILING_NOW" | "In_the_past"
    raw: int

@dataclass
class SmartData:
    ...
    attributes: dict[int, SmartAttribute] = field(default_factory=dict)
```

## Parser (obg/core/health.py)

- `_parse_attribute_table` → `dict[int, SmartAttribute]` (was `dict[int, int]`).
- `crc_errors = max(attrs.get(187, 0), attrs.get(199, 0))` (manufacturers vary).
- NVMe: `attributes` stays empty.
- `SmartData` public fields (reallocated/pending/uncorrectable/crc) unchanged → no downstream breakage.

## Classifier (obg/core/classifier.py)

- Helpers: `_failing_now(sd, attr)` = `when_failed == "FAILING_NOW"`; `_near_thresh(sd, attr, margin=10)` = `thresh > 0 and raw > 0 and 0 < value - thresh <= margin`.
- BAD checked after execution-failure FAILED, before GOLD.
- Cable warning appended to reasons of any class when `crc_errors > 0` (recommendation unchanged by it).
- BAD recommendation: "Not recommended for use — physical defects detected."

## Surface impact

- `Classification.BAD = "BAD"` (models/classification.py)
- `app.py` CompleteScreen css map: `"BAD": "err"`
- `reporter.py`: prints enum value automatically (explicit test added)
- `docs/CLASSIFICATION SPECIFICATION.md`: 5 levels; §3 "No additional classifications" revoked
- Tests: parser thresholds, classifier BAD triggers (badblocks / FAILING_NOW ×3 / SMART FAILED), near-threshold warning, cable warning, SILVER gap, updated integration expectations

## Out of scope

- Configurable thresholds in UI
- NVMe classification changes
- CRC-driven class downgrades