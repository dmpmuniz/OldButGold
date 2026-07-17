import json
import os
import pytest
from datetime import datetime
from obg.models.disk import DiskInfo, SmartData, SmartDelta, DiskSnapshot
from obg.models.classification import Classification, ClassificationResult
from obg.models.operation import StepStatus, StepResult
from obg.models.report import ReportData
from obg.core.classifier import classify
from obg.core.reporter import generate_report
from obg.utils.paths import reports_dir


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


def _make_smart(health="PASSED", realloc=0, pending=0, uncorrectable=0):
    return SmartData(
        overall_health=health, reallocated_sectors=realloc,
        pending_sectors=pending, uncorrectable_sectors=uncorrectable,
        crc_errors=0, temperature=38, power_on_hours=4210,
        raw_output="smartctl output", collected_at=datetime.now(),
    )


def _make_snapshot(smart_before=None, smart_after=None, delta=None, bb=0):
    return DiskSnapshot(
        disk_info=_make_info(), smart_before=smart_before,
        smart_after=smart_after, smart_delta=delta,
        badblocks_count=bb,
    )


def test_classify_gold():
    snap = _make_snapshot(_make_smart(), _make_smart())
    result = classify(snap)
    assert result.classification == Classification.GOLD


def test_classify_silver():
    snap = _make_snapshot(_make_smart(), _make_smart(realloc=3))
    result = classify(snap)
    assert result.classification == Classification.SILVER


def test_classify_bronze():
    snap = _make_snapshot(_make_smart(), _make_smart(realloc=10))
    result = classify(snap)
    assert result.classification == Classification.BRONZE


def test_classify_bronze_badblocks():
    snap = _make_snapshot(_make_smart(), _make_smart(), bb=5)
    result = classify(snap)
    assert result.classification == Classification.BRONZE
    assert any("Bad blocks found: 5" in r for r in result.reasons)


def test_classify_failed_smart_fail():
    snap = _make_snapshot(_make_smart(), _make_smart(health="FAILED"))
    result = classify(snap)
    assert result.classification == Classification.FAILED


def test_classify_bronze_pending():
    snap = _make_snapshot(_make_smart(), _make_smart(pending=1))
    result = classify(snap)
    assert result.classification == Classification.BRONZE


def test_generate_report_creates_file():
    now = datetime.now()
    snap = _make_snapshot(_make_smart(), _make_smart())
    classification = classify(snap)
    steps = [
        StepResult(name="Quick Identify", status=StepStatus.OK, started_at=now, duration_seconds=3.0),
    ]
    data = ReportData(
        obg_version="1.0.0", generated_at=now, snapshot=snap,
        steps=steps, classification=classification,
        filesystem="ext4", label="data", profile="recommended", block_size=65536,
        total_duration_seconds=100.0, success=True,
    )
    report_path = generate_report(data)
    assert os.path.exists(report_path)
