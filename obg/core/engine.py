from __future__ import annotations
import time
from datetime import datetime
from typing import Callable
from obg.models.disk import DiskInfo, DiskSnapshot, SmartDelta
from obg.models.operation import StepStatus, StepResult, OperationResult
from obg import __version__
from obg.models.report import ReportData
from obg.core.detector import verify_identity
from obg.core.health import read_smart, run_short_test
from obg.core.scanner import run_badblocks
from obg.core.partitioner import create_gpt, create_partition
from obg.core.formatter import format_filesystem
from obg.core.classifier import classify
from obg.core.reporter import generate_report
from obg.core.lock import acquire_lock, release_lock
from obg.core.session import create_session, find_session, update_checkpoint, complete_session
from obg.utils import logger


STEPS = [
    "Drive Identification",
    "Initial SMART Collection",
    "SMART Short Self-Test",
    "SMART Re-Collection",
    "Badblocks Validation",
    "Final SMART Collection",
    "SMART Comparison",
    "Create GPT",
    "Create Partition",
    "Format Filesystem",
    "Generate Report",
    "Session Cleanup",
]


def run_pipeline(
    device: str,
    disk_info: DiskInfo,
    filesystem: str,
    label: str,
    profile: str,
    on_step: Callable[[str, StepStatus], None],
    on_output: Callable[[str], None],
    is_cancelled: Callable[[], bool],
    test_mode: bool = False,
    resume: bool = False,
) -> OperationResult:
    start_time = time.monotonic()
    step_results: list[StepResult] = []
    smart_before = None
    smart_after = None
    delta = None
    bb_count = 0
    report_path = None
    partition = None
    disconnected = False

    if not acquire_lock(device):
        raise RuntimeError(f"Cannot acquire exclusive lock for {device}")

    try:
        def _run_step(name: str) -> StepResult:
            on_step(name, StepStatus.RUNNING)
            return StepResult(name=name, status=StepStatus.RUNNING, started_at=datetime.now(), duration_seconds=0)

        def _finish_step(sr: StepResult, status: StepStatus, error: str | None = None, output: str = "") -> None:
            sr.status = status
            sr.duration_seconds = (datetime.now() - sr.started_at).total_seconds()
            sr.error = error
            sr.output = output
            on_step(sr.name, status)

        def _finish_remaining(status: StepStatus) -> None:
            for name in STEPS:
                if any(s.name == name for s in step_results):
                    continue
                sr = _run_step(name)
                _finish_step(sr, status)
                step_results.append(sr)

        # Step 1: Drive Identification
        sr = _run_step("Drive Identification")
        step_results.append(sr)
        if is_cancelled() or disconnected:
            _finish_step(sr, StepStatus.CANCELLED)
            _finish_remaining(StepStatus.CANCELLED)
            return _build_result(False, True, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
        try:
            if not verify_identity(device, disk_info.model, disk_info.serial):
                _finish_step(sr, StepStatus.FAILED, "Device identity mismatch")
                _skip_remaining("Identity mismatch")
                return _build_result(False, False, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
            _finish_step(sr, StepStatus.OK)
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))
            _finish_remaining(StepStatus.SKIPPED)
            return _build_result(False, False, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)

        # Step 2: Initial SMART Collection
        sr = _run_step("Initial SMART Collection")
        step_results.append(sr)
        if is_cancelled() or disconnected:
            _finish_step(sr, StepStatus.CANCELLED)
            _finish_remaining(StepStatus.CANCELLED)
            return _build_result(False, True, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
        try:
            smart_before = read_smart(device)
            _finish_step(sr, StepStatus.OK)
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))

        # Step 3: SMART Short Self-Test
        sr = _run_step("SMART Short Self-Test")
        step_results.append(sr)
        if is_cancelled() or disconnected:
            _finish_step(sr, StepStatus.CANCELLED)
            _finish_remaining(StepStatus.CANCELLED)
            return _build_result(False, True, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
        try:
            ok = run_short_test(device)
            _finish_step(sr, StepStatus.OK if ok else StepStatus.FAILED)
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))

        # Step 4: SMART Re-Collection
        sr = _run_step("SMART Re-Collection")
        step_results.append(sr)
        if is_cancelled() or disconnected:
            _finish_step(sr, StepStatus.CANCELLED)
            _finish_remaining(StepStatus.CANCELLED)
            return _build_result(False, True, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
        try:
            read_smart(device)
            _finish_step(sr, StepStatus.OK)
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))

        # Step 5: Badblocks Validation
        sr = _run_step("Badblocks Validation")
        step_results.append(sr)
        if is_cancelled() or disconnected:
            _finish_step(sr, StepStatus.CANCELLED)
            _finish_remaining(StepStatus.CANCELLED)
            return _build_result(False, True, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
        try:
            resume_offset = 0
            if resume:
                existing = find_session(disk_info)
                if existing:
                    resume_offset = existing.get("badblocks_offset", 0)
            if resume_offset == 0:
                create_session(disk_info)
            def _on_checkpoint(offset: float) -> None:
                update_checkpoint(disk_info, offset)
            bb_count = run_badblocks(
                device, on_output, on_checkpoint=_on_checkpoint,
                test_mode=test_mode, profile=profile, resume_offset=resume_offset,
            )
            _finish_step(sr, StepStatus.OK, output=f"{bb_count} bad blocks")
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))
            _finish_remaining(StepStatus.SKIPPED)
            return _build_result(False, False, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)

        # Step 6: Final SMART Collection
        sr = _run_step("Final SMART Collection")
        step_results.append(sr)
        if is_cancelled() or disconnected:
            _finish_step(sr, StepStatus.CANCELLED)
            _finish_remaining(StepStatus.CANCELLED)
            return _build_result(False, True, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
        try:
            smart_after = read_smart(device)
            _finish_step(sr, StepStatus.OK)
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))

        # Step 7: SMART Comparison
        sr = _run_step("SMART Comparison")
        step_results.append(sr)
        if is_cancelled() or disconnected:
            _finish_step(sr, StepStatus.CANCELLED)
            _finish_remaining(StepStatus.CANCELLED)
            return _build_result(False, True, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
        try:
            if smart_before and smart_after:
                delta = SmartDelta(
                    reallocated=smart_after.reallocated_sectors - smart_before.reallocated_sectors,
                    pending=smart_after.pending_sectors - smart_before.pending_sectors,
                    uncorrectable=smart_after.uncorrectable_sectors - smart_before.uncorrectable_sectors,
                    crc_errors=smart_after.crc_errors - smart_before.crc_errors,
                    temperature=(smart_after.temperature - smart_before.temperature)
                        if smart_after.temperature is not None and smart_before.temperature is not None else None,
                )
            _finish_step(sr, StepStatus.OK)
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))

        # Step 8: Create GPT
        sr = _run_step("Create GPT")
        step_results.append(sr)
        if is_cancelled() or disconnected:
            _finish_step(sr, StepStatus.CANCELLED)
            _finish_remaining(StepStatus.CANCELLED)
            return _build_result(False, True, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
        try:
            create_gpt(device)
            _finish_step(sr, StepStatus.OK)
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))
            _finish_remaining(StepStatus.SKIPPED)
            return _build_result(False, False, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)

        # Step 9: Create Partition
        sr = _run_step("Create Partition")
        step_results.append(sr)
        if is_cancelled() or disconnected:
            _finish_step(sr, StepStatus.CANCELLED)
            _finish_remaining(StepStatus.CANCELLED)
            return _build_result(False, True, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
        try:
            partition = create_partition(device)
            _finish_step(sr, StepStatus.OK, output=partition)
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))
            _finish_remaining(StepStatus.SKIPPED)
            return _build_result(False, False, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)

        # Step 10: Format Filesystem
        sr = _run_step("Format Filesystem")
        step_results.append(sr)
        if is_cancelled() or disconnected:
            _finish_step(sr, StepStatus.CANCELLED)
            _finish_remaining(StepStatus.CANCELLED)
            return _build_result(False, True, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
        try:
            format_filesystem(partition, filesystem, label, on_output)
            _finish_step(sr, StepStatus.OK)
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))
            _finish_remaining(StepStatus.SKIPPED)
            return _build_result(False, False, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)

        # Step 11: Generate Report
        sr = _run_step("Generate Report")
        step_results.append(sr)
        try:
            snapshot = DiskSnapshot(
                disk_info=disk_info, smart_before=smart_before,
                smart_after=smart_after, smart_delta=delta,
                badblocks_count=bb_count, badblocks_raw_output="",
            )
            classification = classify(snapshot)
            report_data = ReportData(
                obg_version=__version__, generated_at=datetime.now(),
                snapshot=snapshot, steps=step_results,
                classification=classification, filesystem=filesystem,
                label=label, profile=profile, block_size=65536,
                total_duration_seconds=time.monotonic() - start_time,
                success=True,
            )
            report_path = generate_report(report_data)
            _finish_step(sr, StepStatus.OK)
        except Exception as e:
            _finish_step(sr, StepStatus.FAILED, str(e))

        # Step 12: Session Cleanup
        sr = _run_step("Session Cleanup")
        step_results.append(sr)
        if not resume:
            try:
                complete_session(disk_info)
            except Exception:
                pass
        _finish_step(sr, StepStatus.OK)

        return _build_result(True, False, step_results, disk_info, smart_before, smart_after, delta, bb_count, start_time, report_path)
    finally:
        release_lock(device)


def _build_result(
    success: bool,
    cancelled: bool,
    steps: list[StepResult],
    disk_info: DiskInfo,
    smart_before,
    smart_after,
    delta,
    bb_count: int,
    start_time: float,
    report_path: str | None,
) -> OperationResult:
    snapshot = DiskSnapshot(
        disk_info=disk_info, smart_before=smart_before,
        smart_after=smart_after, smart_delta=delta,
        badblocks_count=bb_count, badblocks_raw_output="",
    )
    classification = classify(snapshot)
    return OperationResult(
        success=success, cancelled=cancelled, steps=steps,
        snapshot=snapshot, classification=classification,
        report_path=report_path,
        total_duration_seconds=time.monotonic() - start_time,
    )
