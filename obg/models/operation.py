from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from obg.models.disk import DiskSnapshot
from obg.models.classification import ClassificationResult


class StepStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    OK        = "ok"
    FAILED    = "failed"
    SKIPPED   = "skipped"
    CANCELLED = "cancelled"


@dataclass
class StepResult:
    name: str
    status: StepStatus
    started_at: datetime
    duration_seconds: float
    error: str | None = None
    output: str = ""


@dataclass
class OperationResult:
    success: bool
    cancelled: bool
    steps: list[StepResult]
    snapshot: DiskSnapshot
    classification: ClassificationResult
    report_path: str | None
    total_duration_seconds: float
