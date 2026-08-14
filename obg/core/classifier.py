from __future__ import annotations
from obg.models.disk import DiskSnapshot, SmartData
from obg.models.classification import Classification, ClassificationResult

# Attributes whose manufacturer threshold (normalized VALUE <= THRESH) condemns a disk.
THRESHOLD_ATTRS = {
    5: "Reallocated sectors",
    197: "Pending sectors",
    198: "Uncorrectable sectors",
}

# A normalized-value margin (in the 0-253 scale) still considered "near" the threshold.
NEAR_THRESH_MARGIN = 10


def _failing_now(sd: SmartData | None) -> bool:
    if sd is None:
        return False
    return any(
        sd.attributes.get(attr_id) is not None and sd.attributes[attr_id].when_failed == "FAILING_NOW"
        for attr_id in THRESHOLD_ATTRS
    )





def _failing_now_reasons(sd: SmartData | None) -> list[str]:
    if sd is None:
        return []
    return [
        f"{label} at manufacturer threshold (FAILING_NOW): {sd.attributes[attr_id].raw}"
        for attr_id, label in THRESHOLD_ATTRS.items()
        if sd.attributes.get(attr_id) is not None
        and sd.attributes[attr_id].when_failed == "FAILING_NOW"
    ]


def _near_thresh_reasons(sd: SmartData | None) -> list[str]:
    if sd is None:
        return []
    reasons = []
    for attr_id, label in THRESHOLD_ATTRS.items():
        a = sd.attributes.get(attr_id)
        if a is None:
            continue
        if a.thresh > 0 and a.raw > 0 and 0 < a.value - a.thresh <= NEAR_THRESH_MARGIN:
            reasons.append(
                f"{label} near manufacturer limit ({a.raw} set to fail at threshold {a.thresh})"
            )
    return reasons


def _cable_warning(sd: SmartData | None) -> str | None:
    if sd and sd.crc_errors > 0:
        return (
            f"Interface/cable errors detected: {sd.crc_errors} UDMA CRC error(s) — "
            "reconnect or replace the cable and revalidate before trusting this result"
        )
    return None


def classify(snapshot: DiskSnapshot) -> ClassificationResult:
    smart_before = snapshot.smart_before
    smart_after = snapshot.smart_after
    delta = snapshot.smart_delta
    bb = snapshot.badblocks_count
    smart_unavailable = smart_before is None and smart_after is None

    # FAILED — validation cannot complete
    failed_reasons = []
    if not smart_unavailable:
        if smart_after is None:
            failed_reasons.append("Final SMART data unavailable — health check failed")
        if smart_after and smart_after.overall_health not in ("PASSED", "FAILED"):
            failed_reasons.append(f"SMART health check returned: {smart_after.overall_health}")
    if not snapshot.filesystem_created:
        failed_reasons.append("Filesystem creation failed")
    if not snapshot.uninterrupted:
        failed_reasons.append("Validation was interrupted before completion")

    if failed_reasons:
        return ClassificationResult(
            classification=Classification.FAILED,
            reasons=failed_reasons,
            recommendation="Not recommended for use — high risk of data loss.",
        )

    # BAD — validation completed but the disk is condemned
    if (
        bb > 0
        or _failing_now(smart_after)
        or (smart_after is not None and smart_after.overall_health == "FAILED")
    ):
        bad_reasons = []
        if smart_after and smart_after.overall_health == "FAILED":
            bad_reasons.append("SMART health check FAILED after validation")
        if bb > 0:
            bad_reasons.append(f"Bad blocks found: {bb}")
        bad_reasons += _failing_now_reasons(smart_after)
        cable = _cable_warning(smart_after)
        if cable:
            bad_reasons.append(cable)
        return ClassificationResult(
            classification=Classification.BAD,
            reasons=bad_reasons,
            recommendation="Not recommended for use — physical defects detected.",
        )

    # GOLD — all conditions met
    is_gold = (
        smart_before is not None
        and smart_after is not None
        and smart_before.overall_health == "PASSED"
        and smart_after.overall_health == "PASSED"
        and smart_after.reallocated_sectors == 0
        and smart_after.pending_sectors == 0
        and smart_after.uncorrectable_sectors == 0
        and bb == 0
        and snapshot.filesystem_created
        and snapshot.uninterrupted
        and (delta is None or (delta.reallocated == 0 and delta.pending == 0 and delta.uncorrectable == 0))
    )

    if is_gold:
        reasons = [
            "SMART health PASSED before and after validation",
            "No reallocated sectors",
            "No pending sectors",
            "No uncorrectable sectors",
            "No bad blocks found",
        ]
        cable = _cable_warning(smart_after)
        if cable:
            reasons.append(cable)
        return ClassificationResult(
            classification=Classification.GOLD,
            reasons=reasons,
            recommendation="Safe for primary and critical use.",
        )

    # SILVER — no bad blocks, SMART passed, minor observations
    is_silver = (
        smart_after is not None
        and smart_after.overall_health == "PASSED"
        and smart_after.reallocated_sectors <= 5
        and smart_after.pending_sectors == 0
        and smart_after.uncorrectable_sectors == 0
        and (delta is None or delta.reallocated == 0)
        and bb == 0
    )

    if is_silver:
        reasons = ["SMART health PASSED", "No bad blocks found", "No pending sectors"]
        if smart_after and smart_after.reallocated_sectors > 0:
            reasons.append(f"Non-critical wear: {smart_after.reallocated_sectors} reallocated sector(s)")
        cable = _cable_warning(smart_after)
        if cable:
            reasons.append(cable)
        return ClassificationResult(
            classification=Classification.SILVER,
            reasons=reasons,
            recommendation="Safe for standard use. Monitor periodically.",
        )

    # BRONZE — validation completed but defects or warning signs detected
    bronze_reasons = []
    if smart_unavailable:
        bronze_reasons.append("SMART data not available for this device type")
    if smart_after and smart_after.overall_health == "PASSED":
        bronze_reasons.append("SMART health PASSED")
    if smart_after and smart_after.reallocated_sectors > 5:
        bronze_reasons.append(f"Significant wear: {smart_after.reallocated_sectors} reallocated sectors")
    if smart_after and smart_after.pending_sectors > 0:
        bronze_reasons.append(f"Pending sectors: {smart_after.pending_sectors}")
    if smart_after and smart_after.uncorrectable_sectors > 0:
        bronze_reasons.append(f"Uncorrectable sectors: {smart_after.uncorrectable_sectors}")
    if delta and delta.reallocated > 0:
        bronze_reasons.append(f"New reallocated sectors during test: +{delta.reallocated}")
    bronze_reasons += _near_thresh_reasons(smart_after)
    cable = _cable_warning(smart_after)
    if cable:
        bronze_reasons.append(cable)

    return ClassificationResult(
        classification=Classification.BRONZE,
        reasons=bronze_reasons,
        recommendation="Suitable for secondary or archival use. Plan for replacement.",
    )