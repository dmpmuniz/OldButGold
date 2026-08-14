from datetime import datetime

from obg.models.disk import DiskInfo, SmartAttribute, SmartData, SmartDelta, DiskSnapshot
from obg.models.classification import Classification
from obg.core.classifier import classify


def _make_info():
    return DiskInfo(
        device="/dev/sdb", model="WD Elements 25A3", serial="WX41A19TEST",
        firmware="1028", capacity_bytes=2000398934016, capacity_human="2.0 TB",
        interface="usb", transport="usb-uas", logical_sector=512, physical_sector=4096,
        smart_supported=True, uas_enabled=True,
        current_fs="ntfs", partition_table="gpt",
        is_mounted=False, is_boot_disk=False,
        temperature=38, power_on_hours=4210,
        is_supported=True,
    )


def _attrs(realloc_raw=0, pending_raw=0, uncorrectable_raw=0,
           value=100, thresh=0, when_failed="-", crc=0):
    attrs = {
        5: SmartAttribute(value=value, worst=value, thresh=thresh, when_failed=when_failed, raw=realloc_raw),
        197: SmartAttribute(value=100, worst=100, thresh=0, when_failed="-", raw=pending_raw),
        198: SmartAttribute(value=100, worst=100, thresh=0, when_failed="-", raw=uncorrectable_raw),
    }
    if crc:
        attrs[199] = SmartAttribute(value=200, worst=200, thresh=0, when_failed="-", raw=crc)
    return attrs


def _smart(health="PASSED", realloc=0, pending=0, uncorrectable=0, crc=0, attrs=None):
    attr_map = _attrs(realloc_raw=realloc, pending_raw=pending, uncorrectable_raw=uncorrectable, crc=crc)
    for attr_id, overrides in (attrs or {}).items():
        attr_map[attr_id] = _replace_attr(attr_map, attr_id, **overrides)
    return SmartData(
        overall_health=health,
        reallocated_sectors=realloc,
        pending_sectors=pending,
        uncorrectable_sectors=uncorrectable,
        crc_errors=crc,
        temperature=38,
        power_on_hours=4210,
        raw_output="smartctl output",
        collected_at=datetime.now(),
        attributes=attr_map,
    )


def _replace_attr(attrs, attr_id, **kwargs):
    old = attrs[attr_id]
    return SmartAttribute(
        value=kwargs.get("value", old.value),
        worst=kwargs.get("worst", old.worst),
        thresh=kwargs.get("thresh", old.thresh),
        when_failed=kwargs.get("when_failed", old.when_failed),
        raw=kwargs.get("raw", old.raw),
    )


def _snapshot(smart_before=None, smart_after=None, delta=None, bb=0):
    return DiskSnapshot(
        disk_info=_make_info(), smart_before=smart_before,
        smart_after=smart_after, smart_delta=delta,
        badblocks_count=bb,
    )


def _delta(realloc=0, pending=0, uncorrectable=0, crc=0):
    return SmartDelta(reallocated=realloc, pending=pending, uncorrectable=uncorrectable,
                      crc_errors=crc, temperature=None)


def test_badblocks_any_positive_is_bad():
    snap = _snapshot(_smart(), _smart(), bb=1)
    result = classify(snap)
    assert result.classification == Classification.BAD


def test_failing_now_reallocated_is_bad():
    after = _smart(realloc=200, attrs={5: {"value": 20, "thresh": 36, "when_failed": "FAILING_NOW", "raw": 200}})
    snap = _snapshot(_smart(), after)
    result = classify(snap)
    assert result.classification == Classification.BAD


def test_failing_now_pending_is_bad():
    after = _smart(pending=12, attrs={197: {"value": 60, "when_failed": "FAILING_NOW", "raw": 12}})
    snap = _snapshot(_smart(), after)
    result = classify(snap)
    assert result.classification == Classification.BAD


def test_failing_now_uncorrectable_is_bad():
    after = _smart(uncorrectable=5, attrs={198: {"value": 50, "when_failed": "FAILING_NOW", "raw": 5}})
    snap = _snapshot(_smart(), after)
    result = classify(snap)
    assert result.classification == Classification.BAD


def test_smart_overall_failed_after_validation_is_bad():
    snap = _snapshot(_smart(), _smart(health="FAILED"))
    result = classify(snap)
    assert result.classification == Classification.BAD


def test_many_reallocated_without_failing_now_is_bronze():
    after = _smart(realloc=140, attrs={5: {"value": 73, "thresh": 36, "when_failed": "-", "raw": 140}})
    snap = _snapshot(_smart(), after)
    result = classify(snap)
    assert result.classification == Classification.BRONZE
    assert any("140 reallocated" in r for r in result.reasons)


def test_near_threshold_is_bronze_with_warning():
    after = _smart(realloc=8, attrs={5: {"value": 44, "thresh": 36, "when_failed": "-", "raw": 8}})
    snap = _snapshot(_smart(), after)
    result = classify(snap)
    assert result.classification == Classification.BRONZE
    assert any("próximo do limite" in r or "near" in r.lower() or "limit" in r.lower() for r in result.reasons)


def test_near_threshold_does_not_downgrade_when_no_wear():
    snap = _snapshot(_smart(attrs={5: {"value": 44, "thresh": 36, "when_failed": "-", "raw": 0}}),
                     _smart(attrs={5: {"value": 44, "thresh": 36, "when_failed": "-", "raw": 0}}))
    result = classify(snap)
    assert result.classification == Classification.GOLD


def test_cable_warning_appears_but_class_unchanged():
    after = _smart(crc=9)
    snap = _snapshot(_smart(), after)
    result = classify(snap)
    assert result.classification == Classification.GOLD
    assert any("9" in r and "cable" in r.lower() for r in result.reasons)


def test_silver_requires_zero_uncorrectable():
    snap = _snapshot(_smart(), _smart(realloc=3, uncorrectable=1))
    result = classify(snap)
    assert result.classification == Classification.BRONZE


def test_silver_still_works():
    snap = _snapshot(_smart(), _smart(realloc=3))
    result = classify(snap)
    assert result.classification == Classification.SILVER


def test_gold_unchanged():
    snap = _snapshot(_smart(), _smart())
    result = classify(snap)
    assert result.classification == Classification.GOLD