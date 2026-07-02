from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DiskInfo:
    device: str
    model: str
    serial: str
    firmware: str
    capacity_bytes: int
    capacity_human: str
    interface: str
    transport: str
    logical_sector: int
    physical_sector: int
    min_io: int
    optimal_io: int
    alignment_offset: int
    rpm: int | None
    smart_supported: bool
    uas_enabled: bool
    current_fs: str | None
    partition_table: str | None
    is_mounted: bool
    is_boot_disk: bool
    temperature: int | None
    power_on_hours: int | None
    is_supported: bool = True


@dataclass
class SmartData:
    overall_health: str
    reallocated_sectors: int
    pending_sectors: int
    uncorrectable_sectors: int
    crc_errors: int
    temperature: int | None
    power_on_hours: int | None
    raw_output: str
    collected_at: datetime


@dataclass
class SmartDelta:
    reallocated: int
    pending: int
    uncorrectable: int
    crc_errors: int
    temperature: int | None


@dataclass
class DiskSnapshot:
    disk_info: DiskInfo
    smart_before: SmartData | None
    smart_after: SmartData | None
    smart_delta: SmartDelta | None
    badblocks_count: int
    badblocks_raw_output: str
