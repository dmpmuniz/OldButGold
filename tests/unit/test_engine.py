import time
from datetime import datetime
from obg.models.disk import DiskInfo, DiskSnapshot, SmartDelta
from obg.models.operation import StepStatus, StepResult, OperationResult
from obg.models.classification import Classification, ClassificationResult
from obg.core.engine import _build_result
from obg.models.report import ReportData


def _make_info():
    return DiskInfo(
        device="/dev/sdb", model="Test", serial="SN123", firmware="FW1",
        capacity_bytes=1000000, capacity_human="1 MB",
        interface="usb", transport="usb-uas", logical_sector=512, physical_sector=4096,
        smart_supported=True, uas_enabled=True,
        current_fs=None, partition_table=None,
        is_mounted=False, is_boot_disk=False,
        temperature=None, power_on_hours=None, is_supported=True,
    )


def _make_step(name, status):
    return StepResult(name=name, status=status, started_at=datetime.now(), duration_seconds=0)


def _build(success, cancelled, steps, info):
    return _build_result(success, cancelled, steps, time.monotonic(), None, info)


def test_build_result_failed_returns_failed_classification():
    info = _make_info()
    steps = [_make_step("Drive Identification", StepStatus.FAILED)]
    result = _build(False, False, steps, info)
    assert result.success is False
    assert result.cancelled is False
    assert result.classification.classification == Classification.FAILED


def test_build_result_cancelled_returns_failed_classification():
    info = _make_info()
    steps = [_make_step("Drive Identification", StepStatus.CANCELLED)]
    result = _build(False, True, steps, info)
    assert result.success is False
    assert result.cancelled is True
    assert result.classification.classification == Classification.FAILED


def test_build_result_failed_reason_mentions_failing_step():
    info = _make_info()
    steps = [
        _make_step("Step 1", StepStatus.OK),
        _make_step("Step 2", StepStatus.FAILED),
    ]
    result = _build(False, False, steps, info)
    assert any("Step 2" in r for r in result.classification.reasons)


def test_build_result_failed_no_failed_step_fallback_reason():
    info = _make_info()
    steps = [_make_step("Step 1", StepStatus.OK)]
    result = _build(False, False, steps, info)
    assert any("not complete" in r.lower() for r in result.classification.reasons)


def test_build_result_includes_snapshot():
    info = _make_info()
    steps = [_make_step("Step 1", StepStatus.FAILED)]
    result = _build(False, False, steps, info)
    assert result.snapshot is not None
    assert result.snapshot.disk_info == info


def test_build_result_has_duration():
    info = _make_info()
    steps = [_make_step("Step 1", StepStatus.FAILED)]
    result = _build(False, False, steps, info)
    assert result.total_duration_seconds > 0


def test_build_result_skipped_step_found_as_failed():
    info = _make_info()
    steps = [
        _make_step("Step 1", StepStatus.OK),
        _make_step("Step 2", StepStatus.SKIPPED),
    ]
    result = _build(False, False, steps, info)
    assert any("Step 2" in r for r in result.classification.reasons)
