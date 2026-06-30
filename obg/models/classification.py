from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Classification(Enum):
    GOLD   = "GOLD"
    SILVER = "SILVER"
    BRONZE = "BRONZE"
    FAILED = "FAILED"

@dataclass
class ClassificationResult:
    classification: Classification
    reasons: list[str]
    recommendation: str
