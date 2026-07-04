from __future__ import annotations
import time
from datetime import datetime
from typing import Callable
from obg.models.disk import DiskInfo, DiskSnapshot, SmartDelta
from obg.models.operation import StepStatus, StepResult, OperationResult
from obg.models.classification import Classification, ClassificationResult
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
from obg.core.session import create_session, find_session, update_checkpoint, update_stage, complete_session


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

        def _run(name: str, body: Callable, fatal: bool = True) -> bool:
            sr = _run_step(name)
            step_results.append(sr)
            if is_cancelled():
                _finish_step(sr, StepStatus.CANCELLED)
                _finish_remaining(StepStatus.CANCELLED)
                return False
            try:
                body()
                _finish_step(sr, StepStatus.OK)
                return True
            except Exception as e:
                _finish_step(sr, StepStatus.FAILED, str(e))
                if fatal:
                    _finish_remaining(StepStatus.SKIPPED)
                    return False
                return True

        smart_before = None
        smart_after = None
        delta = None
        bb_count = 0
        report_path = None
        partition = None
        snapshot = None
        classification = None

        # Step 1: Drive Identification
        def _identify():
            if not verify_identity(device, disk_info.model, disk_info.serial):
                raise RuntimeError("Device identity mismatch")
        if not _run("Drive Identification", _identify):
            return _build_result(False, False, step_results, start_time, report_path, disk_info, smart_before, smart_after, delta, bb_count)

        # Step 2: Initial SMART Collection
        def _init_smart():
            nonlocal smart_before
            smart_before = read_smart(device)
        _run("Initial SMART Collection", _init_smart, fatal=False)

        # Step 3: SMART Short Self-Test
        def _short_test():
            ok = run_short_test(device, on_output=on_output)
            if not ok:
                raise RuntimeError("SMART Short Self-Test did not complete successfully")
        _run("SMART Short Self-Test", _short_test, fatal=False)

        # Step 4: SMART Re-Collection
        def _recollect():
            nonlocal smart_after
            smart_after = read_smart(device)
        _run("SMART Re-Collection", _recollect, fatal=False)

        # Step 5: Badblocks Validation
        def _badblocks():
            nonlocal bb_count
            resume_offset = 0
            if resume:
                existing = find_session(disk_info)
                if existing:
                    resume_offset = existing.get("badblocks_offset", 0)
                    stage = existing.get("current_stage", "")
                    if stage and stage != "Badblocks Validation":
                        resume_offset = 0
            if resume_offset == 0:
                create_session(disk_info)
            update_stage(disk_info, "Badblocks Validation")
            def _on_checkpoint(offset: float) -> None:
                update_checkpoint(disk_info, offset)
            bb_count = run_badblocks(
                device, on_output, on_checkpoint=_on_checkpoint,
                test_mode=test_mode, profile=profile, resume_offset=resume_offset,
            )
            update_stage(disk_info, "Post Validation")
        if not _run("Badblocks Validation", _badblocks):
            return _build_result(False, False, step_results, start_time, report_path, disk_info, smart_before, smart_after, delta, bb_count)

        # Step 6: Final SMART Collection
        _run("Final SMART Collection", lambda: read_smart(device), fatal=False)

        # Step 7: SMART Comparison
        def _compare():
            nonlocal delta
            if smart_before and smart_after:
                delta = SmartDelta(
                    reallocated=smart_after.reallocated_sectors - smart_before.reallocated_sectors,
                    pending=smart_after.pending_sectors - smart_before.pending_sectors,
                    uncorrectable=smart_after.uncorrectable_sectors - smart_before.uncorrectable_sectors,
                    crc_errors=smart_after.crc_errors - smart_before.crc_errors,
                    temperature=(smart_after.temperature - smart_before.temperature)
                        if smart_after.temperature is not None and smart_before.temperature is not None else None,
                )
        _run("SMART Comparison", _compare, fatal=False)

        # Step 8: Create GPT
        if not _run("Create GPT", lambda: create_gpt(device)):
            return _build_result(False, False, step_results, start_time, report_path, disk_info, smart_before, smart_after, delta, bb_count)

        # Step 9: Create Partition
        def _part():
            nonlocal partition
            partition = create_partition(device)
        if not _run("Create Partition", _part):
            return _build_result(False, False, step_results, start_time, report_path, disk_info, smart_before, smart_after, delta, bb_count)

        # Step 10: Format Filesystem
        if not _run("Format Filesystem", lambda: format_filesystem(partition, filesystem, label, on_output)):
            return _build_result(False, False, step_results, start_time, report_path, disk_info, smart_before, smart_after, delta, bb_count)

        # Step 11: Generate Report
        def _report():
            nonlocal snapshot, classification, report_path
            snapshot = DiskSnapshot(
                disk_info=disk_info, smart_before=smart_before,
                smart_after=smart_after, smart_delta=delta,
                badblocks_count=bb_count,
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
        _run("Generate Report", _report, fatal=False)

        # Step 12: Session Cleanup
        sr = _run_step("Session Cleanup")
        step_results.append(sr)
        if not resume:
            try:
                complete_session(disk_info)
            except Exception:
                pass
        _finish_step(sr, StepStatus.OK)

        return _build_result(True, False, step_results, start_time, report_path, disk_info, smart_before, smart_after, delta, bb_count, snapshot=snapshot, classification=classification)
    finally:
        release_lock(device)


def _build_result(
    success: bool,
    cancelled: bool,
    steps: list[StepResult],
    start_time: float,
    report_path: str | None,
    disk_info: DiskInfo,
    smart_before=None,
    smart_after=None,
    delta=None,
    bb_count: int = 0,
    snapshot: DiskSnapshot | None = None,
    classification: ClassificationResult | None = None,
) -> OperationResult:
    if snapshot is None:
        snapshot = DiskSnapshot(
            disk_info=disk_info, smart_before=smart_before,
            smart_after=smart_after, smart_delta=delta,
            badblocks_count=bb_count,
        )
    if classification is None:
        if not success:
            failed_step = None
            for s in steps:
                if s.status in (StepStatus.FAILED, StepStatus.SKIPPED):
                    failed_step = s
                    break
            reason = f"Pipeline failed at: {failed_step.name}" if failed_step else "Validation did not complete successfully"
            classification = ClassificationResult(
                classification=Classification.FAILED,
                reasons=[reason],
                recommendation="Not recommended for use — validation could not be completed.",
            )
        else:
            classification = classify(snapshot)
    return OperationResult(
        success=success, cancelled=cancelled, steps=steps,
        snapshot=snapshot, classification=classification,
        report_path=report_path,
        total_duration_seconds=time.monotonic() - start_time,
    )
