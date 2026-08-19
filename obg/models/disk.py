from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SmartAttribute:
    value: int
    worst: int
    thresh: int
    when_failed: str
    raw: int


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
    smart_supported: bool
    uas_enabled: bool
    current_fs: str | None
    partition_table: str | None
    is_mounted: bool
    is_boot_disk: bool
    temperature: int | None
    power_on_hours: int | None
    wwn: str | None = None
    is_supported: bool = True
    is_mock: bool = False
    rotational: bool = True


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
    power_cycle_count: int | None = None
    attributes: dict[int, SmartAttribute] = field(default_factory=dict)


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
    filesystem_created: bool = True
    uninterrupted: bool = True
