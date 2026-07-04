from __future__ import annotations
import os
from obg.models.report import ReportData
from obg.utils.paths import reports_dir


def generate_report(data: ReportData) -> str:
    report_dir = reports_dir()
    safe_model = "".join(c if c.isalnum() or c in "-_" else "_" for c in data.snapshot.disk_info.model)
    filename = f"OldButGold-{data.generated_at.strftime('%Y%m%d-%H%M%S')}-{safe_model}.md"
    path = os.path.join(report_dir, filename)
    content = _generate_markdown(data)
    os.makedirs(report_dir, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return path


def _format_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    elif m > 0:
        return f"{m}m {s:02d}s"
    else:
        return f"{s}s"


def _generate_markdown(data: ReportData) -> str:
    info = data.snapshot.disk_info
    smart_before = data.snapshot.smart_before
    smart_after = data.snapshot.smart_after
    delta = data.snapshot.smart_delta
    cls = data.classification
    profile = data.profile.title()
    total = _format_duration(data.total_duration_seconds)

    lines = [
        "# OldButGold Validation Report",
        "",
        "---",
        "",
        "## 1. Validation Summary",
        "",
        f"| Field              | Value                        |",
        f"|--------------------|------------------------------|",
        f"| Date               | {data.generated_at.strftime('%Y-%m-%d %H:%M:%S')} |",
        f"| Application        | OldButGold v{data.obg_version} |",
        f"| Profile            | {profile:<29s} |",
        f"| Classification     | {cls.classification.value:<29s} |",
        f"| Result             | {'Completed' if data.success else 'Interrupted':<29s} |",
        "",
        "---",
        "",
        "## 2. Device Identification",
        "",
        "| Field              | Value                          |",
        "|--------------------|--------------------------------|",
        f"| Model              | {info.model:<30s} |",
        f"| Serial             | {info.serial:<30s} |",
        f"| Firmware           | {info.firmware:<30s} |",
        f"| Capacity           | {info.capacity_human} ({info.capacity_bytes:,} B) |",
        f"| Logical Sector     | {info.logical_sector} B |",
        f"| Physical Sector    | {info.physical_sector} B |",
        f"| Interface          | {info.interface:<30s} |",
        f"| Transport          | {info.transport:<30s} |",
        "",
        "---",
        "",
        "## 3. SMART Comparison",
        "",
    ]

    if smart_before and smart_after:
        lines.extend([
            "| Attribute             | Before | After  | Delta  |",
            "|-----------------------|--------|--------|--------|",
            f"| Overall Health        | {smart_before.overall_health:<6s} | {smart_after.overall_health:<6s} | {'Unchanged' if smart_before.overall_health == smart_after.overall_health else 'Changed':<6s} |",
            f"| Reallocated Sectors   | {smart_before.reallocated_sectors:<6} | {smart_after.reallocated_sectors:<6} | {'Unchanged' if delta and delta.reallocated == 0 else f'+{delta.reallocated}' if delta else 'N/A':<6s} |",
            f"| Pending Sectors       | {smart_before.pending_sectors:<6} | {smart_after.pending_sectors:<6} | {'Unchanged' if delta and delta.pending == 0 else f'+{delta.pending}' if delta else 'N/A':<6s} |",
            f"| Uncorrectable Sectors | {smart_before.uncorrectable_sectors:<6} | {smart_after.uncorrectable_sectors:<6} | {'Unchanged' if delta and delta.uncorrectable == 0 else f'+{delta.uncorrectable}' if delta else 'N/A':<6s} |",
            f"| CRC Errors            | {smart_before.crc_errors:<6} | {smart_after.crc_errors:<6} | {'Unchanged' if delta and delta.crc_errors == 0 else f'+{delta.crc_errors}' if delta else 'N/A':<6s} |",
            f"| Temperature (°C)      | {str(smart_before.temperature) if smart_before.temperature is not None else 'N/A':<6s} | {str(smart_after.temperature) if smart_after.temperature is not None else 'N/A':<6s} | {'Unchanged' if delta and delta.temperature == 0 else ('+' + str(delta.temperature) + '°C') if delta and delta.temperature is not None else 'N/A':<6s} |",
        ])
    else:
        lines.append("SMART data was not available for comparison.")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Validation Configuration",
        "",
        "| Field              | Value                        |",
        "|--------------------|------------------------------|",
        f"| Profile            | {profile:<29s} |",
        f"| Filesystem         | {data.filesystem:<29s} |",
        f"| Volume Label       | {data.label:<29s} |",
        f"| Duration           | {total:<29s} |",
        "",
        "---",
        "",
        "## 5. Badblocks Result",
        "",
        "| Field              | Value                        |",
        "|--------------------|------------------------------|",
        f"| Status             | {'Completed' if data.success else 'Interrupted':<29s} |",
        f"| Bad Blocks         | {data.snapshot.badblocks_count:<29} |",
        f"| Block Size         | {'4096 B':<29s} |",
        f"| Duration           | {total:<29s} |",
        "",
        "---",
        "",
        "## 6. Filesystem Creation",
        "",
        "| Field              | Value                        |",
        "|--------------------|------------------------------|",
        f"| Partition Table    | GPT                          |",
        f"| Filesystem         | {data.filesystem:<29s} |",
        f"| Volume Label       | {data.label:<29s} |",
        "",
        "---",
        "",
        "## 7. Validation Timeline",
        "",
    ])

    for step in data.steps:
        if step.status.value == "ok":
            lines.append(f"* {step.name} — completed")
        elif step.status.value == "failed":
            lines.append(f"* {step.name} — failed")
        elif step.status.value == "skipped":
            lines.append(f"* {step.name} — skipped")
        elif step.status.value == "cancelled":
            lines.append(f"* {step.name} — cancelled")

    lines.extend([
        "",
        "---",
        "",
        "## 8. Final Assessment",
        "",
        f"**{cls.classification.value}**",
        "",
    ])
    for r in cls.reasons:
        lines.append(f"- {r}")
    lines.extend([
        "",
        f"**Recommendation:** {cls.recommendation}",
        "",
        "---",
        "",
        "## 9. Legal Disclaimer",
        "",
        "> **OldButGold performs hardware validation using industry-standard diagnostic utilities. "
        "Validation results reflect only the observed condition of the storage device during execution. "
        "No report constitutes a guarantee of future reliability, data integrity or continued operation. "
        "Storage devices may fail without prior warning. The user remains solely responsible for backup, "
        "data protection and all decisions made based on this report. Use of this software is entirely at the user's own risk.**",
        "",
        "---",
        "",
        f"*Generated by OldButGold v{data.obg_version}*",
    ])

    return "\n".join(lines) + "\n"
