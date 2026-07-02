from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from obg.models.disk import DiskSnapshot
from obg.models.classification import ClassificationResult
from obg.models.operation import StepResult


@dataclass
class ReportData:
    obg_version: str
    generated_at: datetime
    snapshot: DiskSnapshot
    steps: list[StepResult]
    classification: ClassificationResult
    filesystem: str
    label: str
    profile: str
    block_size: int
    total_duration_seconds: float
    success: bool = True
