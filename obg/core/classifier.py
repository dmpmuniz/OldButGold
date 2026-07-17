from __future__ import annotations
from obg.models.disk import DiskSnapshot
from obg.models.classification import Classification, ClassificationResult


def classify(snapshot: DiskSnapshot) -> ClassificationResult:
    smart_before = snapshot.smart_before
    smart_after = snapshot.smart_after
    delta = snapshot.smart_delta
    bb = snapshot.badblocks_count

    # FAILED — validation cannot complete
    failed_reasons = []
    if smart_after is None:
        failed_reasons.append("Final SMART data unavailable — health check failed")
    if smart_after and smart_after.overall_health == "FAILED":
        failed_reasons.append("SMART health check FAILED after validation")
    if smart_after and smart_after.pending_sectors > 0:
        failed_reasons.append(f"Pending sectors: {smart_after.pending_sectors}")
    if smart_after and smart_after.uncorrectable_sectors > 0:
        failed_reasons.append(f"Uncorrectable sectors: {smart_after.uncorrectable_sectors}")
    # ponytail: bad blocks are Bronze, not Failed (spec §6)

    if failed_reasons:
        return ClassificationResult(
            classification=Classification.FAILED,
            reasons=failed_reasons,
            recommendation="Not recommended for use — high risk of data loss.",
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
        and (delta is None or (delta.reallocated == 0 and delta.pending == 0 and delta.uncorrectable == 0))
    )

    if is_gold:
        return ClassificationResult(
            classification=Classification.GOLD,
            reasons=[
                "SMART health PASSED before and after validation",
                "No reallocated sectors",
                "No pending sectors",
                "No uncorrectable sectors",
                "No bad blocks found",
            ],
            recommendation="Safe for primary and critical use.",
        )

    # SILVER — no bad blocks, SMART passed, minor observations
    is_silver = (
        smart_after is not None
        and smart_after.overall_health == "PASSED"
        and smart_after.reallocated_sectors <= 5
        and (delta is None or delta.reallocated == 0)
        and bb == 0
    )

    if is_silver:
        reasons = ["SMART health PASSED", "No bad blocks found"]
        if smart_after and smart_after.reallocated_sectors > 0:
            reasons.append(f"Non-critical wear: {smart_after.reallocated_sectors} reallocated sector(s)")
        return ClassificationResult(
            classification=Classification.SILVER,
            reasons=reasons,
            recommendation="Safe for standard use. Monitor periodically.",
        )

    # BRONZE — validation completed but defects detected
    bronze_reasons = []
    if smart_after and smart_after.overall_health == "PASSED":
        bronze_reasons.append("SMART health PASSED")
    if smart_after and smart_after.reallocated_sectors > 5:
        bronze_reasons.append(f"Significant wear: {smart_after.reallocated_sectors} reallocated sectors")
    if delta and delta.reallocated > 0:
        bronze_reasons.append(f"New reallocated sectors during test: +{delta.reallocated}")
    if bb > 0:
        bronze_reasons.append(f"Bad blocks found: {bb}")

    return ClassificationResult(
        classification=Classification.BRONZE,
        reasons=bronze_reasons,
        recommendation="Suitable for secondary or archival use. Plan for replacement.",
    )
