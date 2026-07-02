import pytest
from datetime import datetime
from obg.models.disk import DiskInfo, SmartData, SmartDelta, DiskSnapshot
from obg.models.classification import Classification, ClassificationResult
from obg.models.operation import StepStatus, StepResult, OperationResult
from obg.models.report import ReportData


def test_disk_info_creation():
    info = DiskInfo(
        device="/dev/sdb", model="WD Elements", serial="WX123", firmware="1.0",
        capacity_bytes=2000398934016, capacity_human="2.0 TB",
        interface="usb", transport="usb-uas", logical_sector=512, physical_sector=4096,
        min_io=4096, optimal_io=33553920, alignment_offset=0, rpm=5400,
        smart_supported=True, uas_enabled=True,
        current_fs="ntfs", partition_table="gpt",
        is_mounted=False, is_boot_disk=False,
        temperature=38, power_on_hours=4210,
        is_supported=True,
    )
    assert info.device == "/dev/sdb"
    assert info.capacity_bytes == 2000398934016
    assert info.transport == "usb-uas"
    assert info.rpm == 5400


def test_smart_data_creation():
    now = datetime.now()
    sd = SmartData(
        overall_health="PASSED", reallocated_sectors=0, pending_sectors=0,
        uncorrectable_sectors=0, crc_errors=0, temperature=38,
        power_on_hours=4210, raw_output="smartctl output", collected_at=now,
    )
    assert sd.overall_health == "PASSED"
    assert sd.temperature == 38
    assert sd.collected_at == now


def test_step_status_enum_values():
    values = [s.value for s in StepStatus]
    expected = ["pending", "running", "ok", "failed", "skipped", "cancelled"]
    assert values == expected


def test_step_result_creation():
    now = datetime.now()
    sr = StepResult(name="Quick Identify", status=StepStatus.OK, started_at=now, duration_seconds=3.0)
    assert sr.error is None
    assert sr.output == ""
    assert sr.status == StepStatus.OK


def test_operation_result_creation():
    info = DiskInfo(
        device="/dev/sdb", model="Test", serial="T123", firmware="1.0",
        capacity_bytes=1000000000, capacity_human="1 GB",
        interface="sata", transport="sata", logical_sector=512, physical_sector=512,
        min_io=512, optimal_io=0, alignment_offset=0, rpm=7200,
        smart_supported=True, uas_enabled=False,
        current_fs=None, partition_table=None,
        is_mounted=False, is_boot_disk=False,
        temperature=None, power_on_hours=None,
        is_supported=True,
    )
    snapshot = DiskSnapshot(disk_info=info, smart_before=None, smart_after=None,
                           smart_delta=None, badblocks_count=0, badblocks_raw_output="")
    classification = ClassificationResult(
        classification=Classification.GOLD,
        reasons=["test"],
        recommendation="Test",
    )
    op = OperationResult(
        success=True, cancelled=False, steps=[], snapshot=snapshot,
        classification=classification, report_path="/tmp/test/report.md",
        total_duration_seconds=100.0,
    )
    assert op.success is True
    assert op.cancelled is False
    assert op.classification.classification == Classification.GOLD
