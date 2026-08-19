from __future__ import annotations

import os
import re
import subprocess
import time
from typing import Callable

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from obg import __version__
from obg.config import load_config, save_config, VALID_FILESYSTEMS, VALID_PROFILES
from obg.core.detector import list_disks, list_mock_disks
from obg.core.engine import STEPS as PIPELINE_STAGES
from obg.core.engine import run_pipeline
from obg.core.health import read_smart
from obg.core.session import complete_session, find_session
from obg.models.disk import DiskInfo
from obg.models.operation import OperationResult, StepStatus
from obg.utils import logger

# Matches badblocks progress lines for both passes, e.g.
# "Testing with pattern 0xaa:   50.00% done, 0:05:00 elapsed. (0/0/0 errors)" (write pass)
# "Reading and comparing:   50.00% done, 0:05:00 elapsed." (read-back pass)
BB_LINE_RE = re.compile(
    r"(?:Testing with pattern (\S+):\s+|Reading and comparing:\s+)?"
    r"([\d.]+)% done,\s+([\d:]+) elapsed\.?\s*(?:\((\d+)/(\d+)/(\d+)\s*errors?\)?)?"
)


def _is_scan_operation(operation: str) -> bool:
    return "Writing" in operation or "Reading" in operation or "pattern" in operation.lower()


LABEL_MAX_LENGTH = 16


def _suggest_label(model: str) -> str:
    """Suggest a filesystem label from the drive brand (first word of the model)."""
    if not model or not model.strip():
        return ""
    brand = model.strip().split()[0].upper()
    brand = re.sub(r"[^A-Z0-9_-]", "", brand)
    return brand[:LABEL_MAX_LENGTH]

PALETTE = {
    "bg": "#0d1117",
    "panel": "#161b22",
    "panel-soft": "#1c2430",
    "border": "#30363d",
    "accent": "#58a6ff",
    "text": "#c9d1d9",
    "muted": "#8b949e",
    "faint": "#6e7681",
    "ok": "#3fb950",
    "warn": "#d29922",
    "err": "#f85149",
}


def _fmt_duration(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _get_mounted_partitions(device: str) -> list[tuple[str, str]]:
    try:
        with open("/proc/mounts") as f:
            rows = [line.split() for line in f if line.strip()]
    except OSError:
        return []
    return [(parts[0], parts[1]) for parts in rows if len(parts) >= 2 and parts[0].startswith(device)]


def _unmount_partitions(mounts: list[tuple[str, str]]) -> list[str]:
    errors = []
    for dev, mnt in mounts:
        result = subprocess.run(["umount", mnt], capture_output=True, text=True)
        if result.returncode != 0:
            errors.append(f"{mnt} ({dev}): {(result.stderr or result.stdout or 'failed').strip()}")
    return errors


class ObgApp(App):
    SCREEN_SIZE = (120, 40)
    TITLE = "OldButGold"

    def __init__(self, test_mode: bool = False, mock_path: str | None = None) -> None:
        super().__init__()
        self.test_mode = test_mode
        self.mock_path = mock_path

    CSS = f"""
    Screen {{ background: {PALETTE['bg']}; }}
    #header {{
        dock: top; height: 1;
        background: {PALETTE['panel']}; color: {PALETTE['muted']};
        padding: 0 2;
    }}
    #body {{ height: 1fr; overflow-y: auto; padding: 0 2; }}
    #footer {{
        dock: bottom; height: 1;
        background: {PALETTE['panel']}; color: {PALETTE['faint']};
        padding: 0 2;
    }}

    .panel {{ border: solid {PALETTE['border']}; background: {PALETTE['panel']}; padding: 0 1; margin: 1 0; }}
    .panel-title {{ color: {PALETTE['accent']}; text-style: bold; }}
    .panel-ok {{ border: solid {PALETTE['ok']}; }}
    .panel-warn {{ border: solid {PALETTE['warn']}; }}
    .panel-err {{ border: solid {PALETTE['err']}; }}

    .btn-row {{ height: 3; align: center middle; }}
    .btn-row Button {{
        width: 1fr; margin: 0 1;
        border: solid {PALETTE['border']};
        background: {PALETTE['panel']}; color: {PALETTE['text']};
    }}
    .btn-row Button:hover {{ border: solid {PALETTE['accent']}; }}
    .btn-row Button:focus {{ border: solid {PALETTE['accent']}; color: {PALETTE['accent']}; }}
    .btn-row Button:disabled {{ border: solid {PALETTE['border']}; color: {PALETTE['faint']}; }}

    .card {{
        border: solid {PALETTE['border']};
        background: {PALETTE['panel']};
        margin: 1 0; padding: 0 2;
    }}
    .card:hover {{ border: solid {PALETTE['accent']}; }}
    .card-selected {{ border: solid {PALETTE['accent']}; background: {PALETTE['panel-soft']}; }}
    .card-disabled {{ border: solid {PALETTE['border']}; background: {PALETTE['panel']}; color: {PALETTE['faint']}; }}
    .card-name {{ color: {PALETTE['text']}; text-style: bold; }}
    .card-meta {{ color: {PALETTE['muted']}; }}
    .card-badge {{ color: {PALETTE['warn']}; }}

    .label {{ color: {PALETTE['muted']}; }}
    .muted {{ color: {PALETTE['muted']}; }}
    .faint {{ color: {PALETTE['faint']}; }}
    .ok {{ color: {PALETTE['ok']}; }}
    .warn {{ color: {PALETTE['warn']}; text-style: bold; }}
    .err {{ color: {PALETTE['err']}; text-style: bold; }}
    .accent {{ color: {PALETTE['accent']}; text-style: bold; }}

    .step-pending {{ color: {PALETTE['faint']}; }}
    .step-running {{ color: {PALETTE['accent']}; text-style: bold; }}
    .step-ok {{ color: {PALETTE['ok']}; }}
    .step-failed {{ color: {PALETTE['err']}; }}
    .step-skipped {{ color: {PALETTE['faint']}; }}

    .metric-card {{
        border: solid {PALETTE['border']};
        background: {PALETTE['panel']};
        width: 1fr; min-width: 14; min-height: 3; margin: 0 1 1 0; padding: 0 1;
    }}
    .metric-title {{ color: {PALETTE['faint']}; }}
    .metric-value {{ color: {PALETTE['text']}; }}

    .disk-info-row {{ height: auto; }}
    .disk-info-row > Static {{
        width: 1fr; min-width: 14; height: 4; border: solid {PALETTE['border']};
        background: {PALETTE['panel']};
        margin: 0 1 0 0; padding: 0 1; content-align: center middle;
    }}

    .steps-col {{ width: 30; }}
    .output-col {{ width: 1fr; }}
    .output-col > Horizontal {{ width: 1fr; height: auto; }}

    #output-log {{ width: 1fr; height: 16; margin: 1 0 0 0; background: {PALETTE['panel']}; }}
    #output-log > Static {{ width: 1fr; color: {PALETTE['muted']}; }}

    #warning-box {{
        border: solid {PALETTE['err']};
        background: {PALETTE['panel']};
        margin: 1 0; padding: 1 2;
        color: {PALETTE['warn']}; text-style: bold;
        content-align: center middle;
    }}

    .sep {{ height: 1; background: {PALETTE['border']}; margin: 1 0; }}

    #smart-panel {{ min-height: 8; }}
    """

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def pop_to_root(self) -> None:
        while len(self.screen_stack) > 1 and not isinstance(self.screen_stack[-1], MainScreen):
            self.pop_screen()


class MainScreen(Screen):
    BINDINGS = [
        Binding("up", "move(-1)", "Up", priority=True),
        Binding("down", "move(1)", "Down", priority=True),
        Binding("enter", "select", "Select", priority=True),
        Binding("escape", "quit_app", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._disks: list[DiskInfo] = []
        self._selected = 0
        self._ready = False

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  |  Select Drive", id="header")
            with VerticalScroll(id="body"):
                yield Static(f"O L D   B U T   G O L D", classes="accent")
                yield Static(f"HDD validation and refurbishment workflow", classes="muted")
                yield Static("", classes="sep")
                yield Static(
                    "OldButGold validates the observable condition of a hard drive and does not"
                    "\nguarantee future reliability. Validation is destructive: all data on the selected"
                    "\ndrive will be permanently destroyed. Use entirely at your own risk.",
                    classes="muted",
                )
                yield Static("", classes="sep")
                yield Static("Detecting drives...", id="status", classes="muted")
                with VerticalScroll(id="drive-list"):
                    pass
            yield Horizontal(
                Button(" Continue ", id="continue-btn", disabled=True),
                Button(" Refresh ", id="refresh-btn"),
                Button(" Quit ", id="quit-btn"),
                classes="btn-row",
            )
            yield Static("  Up/Down select    Enter confirm    R refresh    Esc quit", id="footer")

    def on_mount(self) -> None:
        self._refresh()

    def action_move(self, delta: int) -> None:
        if not self._disks:
            return
        new_index = self._selected + delta
        if new_index < 0 or new_index >= len(self._disks):
            return
        self._selected = new_index
        self._paint_cards()

    def action_select(self) -> None:
        self._open_selected()

    def action_refresh(self) -> None:
        self._refresh()

    def action_quit_app(self) -> None:
        self.app.exit()

    def on_button_pressed(self, event) -> None:
        if event.button.id == "continue-btn":
            self._open_selected()
        elif event.button.id == "refresh-btn":
            self._refresh()
        elif event.button.id == "quit-btn":
            self.app.exit()

    def on_click(self, event) -> None:
        idx = getattr(event.widget, "idx", None)
        if idx is not None and 0 <= idx < len(self._disks):
            self._selected = idx
            self._open_selected()

    @work(thread=True, exit_on_error=False)
    def _refresh(self) -> None:
        try:
            disks = list_disks()
            if self.app.mock_path:
                disks = list_mock_disks(self.app.mock_path) + disks
        except Exception:
            disks = []
        try:
            self.app.call_from_thread(self._rebuild, disks)
        except Exception:
            pass

    def _rebuild(self, disks: list[DiskInfo]) -> None:
        self._disks = disks
        self._selected = 0
        self._ready = True
        drive_list = self.query_one("#drive-list", VerticalScroll)
        for child in list(drive_list.children):
            child.remove()
        if not disks:
            drive_list.mount(Static("No drives detected. Press R to refresh.", classes="muted"))
        else:
            for i, disk in enumerate(disks):
                drive_list.mount(self._card_for(disk, i))
        self._paint_cards()
        try:
            self.query_one("#status", Static).update(f"{len(disks)} drive(s) detected")
            self.query_one("#continue-btn", Button).disabled = not bool(disks)
        except Exception:
            pass

    def _card_for(self, disk: DiskInfo, index: int) -> Static:
        lines = [disk.model]
        lines.append(f"{disk.device}  |  {disk.transport}  |  {disk.capacity_human}")
        badges = []
        if disk.is_mock:
            badges.append("Mock")
        if disk.is_boot_disk:
            badges.append("System drive")
        if disk.is_mounted:
            badges.append("Mounted")
        if disk.is_supported is False:
            if not disk.rotational and disk.transport == "nvme":
                badges.append("NVMe (requires HDD)")
            elif not disk.rotational:
                badges.append("SSD (requires HDD)")
            else:
                badges.append("Unsupported")
        session = find_session(disk)
        if session:
            pct = self._session_pct(disk, session)
            badges.append(f"Interrupted {pct}%")
        if badges:
            lines.append("  ".join(f"\\[{b}]" for b in badges))
        widget = Static("\n".join(lines))
        widget.idx = index
        if not disk.is_supported:
            widget.add_class("card-disabled")
        else:
            widget.add_class("card")
        return widget

    @staticmethod
    def _session_pct(disk: DiskInfo, session: dict) -> int:
        total_blocks = disk.capacity_bytes // 4096 if disk.capacity_bytes else 1
        return min(99, int(session.get("badblocks_offset", 0) / total_blocks * 100))

    def _paint_cards(self) -> None:
        drive_list = self.query_one("#drive-list", VerticalScroll)
        for child in drive_list.children:
            idx = getattr(child, "idx", None)
            if idx is None:
                continue
            disabled = child.has_class("card-disabled")
            selected = idx == self._selected and not disabled
            child.set_class(selected, "card-selected")
            child.set_class(not selected and not disabled, "card")

    def _open_selected(self) -> None:
        if not self._ready or not self._disks:
            return
        disk = self._disks[self._selected]
        if not disk.is_supported:
            return
        self.app.push_screen(DriveScreen(disk))

    def refresh_drives(self) -> None:
        self._refresh()


class DriveScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
        Binding("enter", "primary", "Configure", priority=True),
    ]

    def __init__(self, disk: DiskInfo) -> None:
        super().__init__()
        self.disk = disk
        self.session = find_session(disk)
        self.mounts: list[tuple[str, str]] = []
        self._unmounted = False

    def compose(self) -> ComposeResult:
        self.mounts = _get_mounted_partitions(self.disk.device) if not self.disk.is_mock else []
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  |  Drive  |  {self.disk.model}", id="header")
            with VerticalScroll(id="body"):
                with Horizontal():
                    with Container(classes="panel"):
                        yield Static("Device", classes="panel-title")
                        yield Static(f"Model:      {self.disk.model}")
                        yield Static(f"Serial:     {self.disk.serial}")
                        yield Static(f"Firmware:   {self.disk.firmware}")
                        yield Static(f"Capacity:   {self.disk.capacity_human}")
                        yield Static(f"WWN:        {self.disk.wwn or 'n/a'}")
                        yield Static(f"Device:     {self.disk.device}")
                    with Container(classes="panel"):
                        yield Static("Configuration", classes="panel-title")
                        yield Static(f"Interface:      {self.disk.interface}")
                        yield Static(f"Transport:      {self.disk.transport}")
                        yield Static(f"SMART:          {'supported' if self.disk.smart_supported else 'not available'}")
                        yield Static(f"Filesystem:     {self.disk.current_fs or 'none'}")
                        yield Static(f"Partition:      {self.disk.partition_table or 'none'}")
                        yield Static(f"Geometry:       {self.disk.logical_sector}/{self.disk.physical_sector} B (log/phys)")
                with Container(classes="panel"):
                    yield Static("SMART", classes="panel-title")
                    yield Static("Collecting SMART data...", id="smart-body")
                if self.mounts:
                    with Container(classes="panel-warn", id="mounted-panel"):
                        yield Static("Drive is mounted", classes="warn")
                        for dev, mnt in self.mounts:
                            yield Static(f"  {dev}  ->  {mnt}", classes="muted")
                        yield Static("Partitions must be unmounted before validation.", classes="muted")
                if self.session:
                    with Container(classes="panel-warn", id="session-panel"):
                        yield Static("Interrupted validation", classes="warn")
                        yield Static(f"Stage:    {self.session.get('current_stage', 'Surface Scan (Badblocks)') or 'Surface Scan (Badblocks)'}")
                        yield Static(f"Progress: {MainScreen._session_pct(self.disk, self.session)}%")
                        yield Static(f"Started:  {self.session.get('created_at', 'unknown')}")
                yield Static("", id="status", classes="muted")
            yield Horizontal(
                Button(" Back ", id="back-btn"),
                Button(" Unmount ", id="unmount-btn"),
                Button(" Recover ", id="recover-btn"),
                Button(" Restart ", id="restart-btn"),
                Button(" Configure ", id="configure-btn"),
                classes="btn-row",
            )
            yield Static("  Esc back    Enter configure", id="footer")

    def on_mount(self) -> None:
        try:
            self.query_one("#unmount-btn", Button).disabled = not (self.mounts and not self._unmounted)
            self.query_one("#recover-btn", Button).disabled = not self.session
            self.query_one("#restart-btn", Button).disabled = not self.session
        except Exception:
            pass
        if not self.disk.is_mock:
            self._fetch_smart()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_primary(self) -> None:
        self._configure()

    def on_button_pressed(self, event) -> None:
        button_id = event.button.id
        if button_id == "back-btn":
            self.action_back()
        elif button_id == "unmount-btn":
            self._do_unmount()
        elif button_id == "recover-btn":
            self._start_with(resume=True)
        elif button_id == "restart-btn":
            self._restart()
        elif button_id == "configure-btn":
            self._configure()

    def _guard_mounted(self) -> bool:
        if self.disk.is_mock:
            return True
        if _get_mounted_partitions(self.disk.device):
            self._set_status("Partitions are still mounted. Unmount first.", warn=True)
            return False
        return True

    def _configure(self) -> None:
        if not self._guard_mounted():
            return
        self.app.push_screen(ConfigScreen(self.disk, resume=False))

    def _start_with(self, resume: bool) -> None:
        if not self._guard_mounted():
            return
        self.app.push_screen(ConfigScreen(self.disk, resume=resume))

    def _restart(self) -> None:
        complete_session(self.disk)
        self.session = None
        try:
            self.query_one("#session-panel", Container).remove()
        except Exception:
            pass
        self.query_one("#recover-btn", Button).disabled = True
        self.query_one("#restart-btn", Button).disabled = True
        self._set_status("Interrupted session discarded.")
        self._configure()

    @work(thread=True, exit_on_error=False)
    def _do_unmount(self) -> None:
        try:
            self.app.call_from_thread(self._set_status, "Unmounting partitions...")
        except Exception:
            pass
        errors = _unmount_partitions(self.mounts)
        if errors:
            try:
                self.app.call_from_thread(self._set_status, "; ".join(errors), warn=True)
            except Exception:
                pass
            return
        try:
            self.app.call_from_thread(self._unmount_done)
        except Exception:
            pass

    def _unmount_done(self) -> None:
        self._unmounted = True
        self.mounts = []
        try:
            self.query_one("#mounted-panel", Container).remove()
            self.query_one("#unmount-btn", Button).disabled = True
        except Exception:
            pass
        self._set_status("Partitions unmounted.")

    @work(thread=True, exit_on_error=False)
    def _fetch_smart(self) -> None:
        try:
            sd = read_smart(self.disk.device)
        except Exception:
            sd = None
        try:
            self.app.call_from_thread(self._show_smart, sd)
        except Exception:
            pass

    def _show_smart(self, sd) -> None:
        try:
            panel = self.query_one("#smart-body", Static)
            if not sd:
                panel.update("SMART data not available for this drive.")
                return
            panel.update(
                f"Health:  {sd.overall_health}"
                f"\nTemp:    {sd.temperature if sd.temperature is not None else 'n/a'} C"
                f"\nPower-on: {sd.power_on_hours if sd.power_on_hours is not None else 'n/a'} h"
                f"\nCycles:  {sd.power_cycle_count if sd.power_cycle_count is not None else 'n/a'}"
                f"\nReallocated:  {sd.reallocated_sectors}"
                f"\nPending:      {sd.pending_sectors}"
                f"\nUncorrectable: {sd.uncorrectable_sectors}"
                f"\nCRC errors:   {sd.crc_errors}"
            )
        except Exception:
            pass

    def _set_status(self, message: str, warn: bool = False) -> None:
        try:
            widget = self.query_one("#status", Static)
            widget.update(message)
            widget.set_class(warn, "warn")
            widget.set_class(not warn, "muted")
        except Exception:
            pass


class ConfigScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
        Binding("enter", "primary", "Start", priority=True),
    ]

    PROFILE_DESCRIPTIONS = {
        "recommended": "Two destructive patterns (0xaa / 0x55) with 4 KiB blocks. Balanced validation time.",
        "extended": "Native badblocks defaults: all four patterns, maximum coverage, longer runtime.",
    }

    def __init__(self, disk: DiskInfo, resume: bool = False) -> None:
        super().__init__()
        self.disk = disk
        self.resume = resume
        self.config = load_config()
        self._profile_idx = VALID_PROFILES.index(self.config["profile"]) if self.config["profile"] in VALID_PROFILES else 0
        self._fs_idx = VALID_FILESYSTEMS.index(self.config["filesystem"]) if self.config["filesystem"] in VALID_FILESYSTEMS else 0

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  |  Configure", id="header")
            with VerticalScroll(id="body"):
                with Container(classes="panel"):
                    yield Static(f"Drive:  {self.disk.model}", classes="panel-title")
                    yield Static(f"Serial: {self.disk.serial}   |   Capacity: {self.disk.capacity_human}", classes="muted")
                yield Static("Validation Profile", classes="panel-title")
                for profile in VALID_PROFILES:
                    widget = Static(f"{profile.title()}\n{self.PROFILE_DESCRIPTIONS[profile]}", id=f"prof-{profile}", classes="card")
                    widget.idx = VALID_PROFILES.index(profile)
                    yield widget
                yield Static("Filesystem", classes="panel-title")
                for fs in VALID_FILESYSTEMS:
                    widget = Static(fs.upper(), id=f"fs-{fs}", classes="card")
                    widget.idx = VALID_FILESYSTEMS.index(fs)
                    yield widget
                yield Static("Volume Label (optional)", classes="panel-title")
                yield Input(value=_suggest_label(self.disk.model), id="label-input")
                yield Static(
                    "All existing data on this drive will be permanently destroyed.",
                    id="warning-box",
                )
                yield Static("", id="status", classes="muted")
            yield Horizontal(
                Button(" Back ", id="back-btn"),
                Button(" Start Validation ", id="start-btn"),
                classes="btn-row",
            )
            yield Static("  Left/Right change    Tab label    Enter start    Esc back", id="footer")

    def on_mount(self) -> None:
        self._paint()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_primary(self) -> None:
        self._start()

    def on_key(self, event) -> None:
        if isinstance(self.focused, Input):
            return
        if event.key == "left":
            self._cycle("profile", -1)
        elif event.key == "right":
            self._cycle("profile", 1)
        elif event.key == "up":
            self._cycle("fs", -1)
        elif event.key == "down":
            self._cycle("fs", 1)

    def on_click(self, event) -> None:
        widget_id = getattr(event.widget, "id", None)
        idx = getattr(event.widget, "idx", None)
        if widget_id and widget_id.startswith("prof-") and idx is not None:
            self._profile_idx = idx
            self._paint()
        elif widget_id and widget_id.startswith("fs-") and idx is not None:
            self._fs_idx = idx
            self._paint()

    def on_button_pressed(self, event) -> None:
        if event.button.id == "back-btn":
            self.action_back()
        elif event.button.id == "start-btn":
            self._start()

    def _cycle(self, group: str, delta: int) -> None:
        if group == "profile":
            self._profile_idx = (self._profile_idx + delta) % len(VALID_PROFILES)
        else:
            self._fs_idx = (self._fs_idx + delta) % len(VALID_FILESYSTEMS)
        self._paint()

    def _paint(self) -> None:
        for profile in VALID_PROFILES:
            try:
                widget = self.query_one(f"#prof-{profile}", Static)
                widget.set_class(VALID_PROFILES.index(profile) == self._profile_idx, "card-selected")
                widget.set_class(VALID_PROFILES.index(profile) != self._profile_idx, "card")
            except Exception:
                pass
        for fs in VALID_FILESYSTEMS:
            try:
                widget = self.query_one(f"#fs-{fs}", Static)
                widget.set_class(VALID_FILESYSTEMS.index(fs) == self._fs_idx, "card-selected")
                widget.set_class(VALID_FILESYSTEMS.index(fs) != self._fs_idx, "card")
            except Exception:
                pass

    def _start(self) -> None:
        self.config["profile"] = VALID_PROFILES[self._profile_idx]
        self.config["filesystem"] = VALID_FILESYSTEMS[self._fs_idx]
        try:
            self.config["label"] = self.query_one("#label-input", Input).value.strip()
        except Exception:
            self.config["label"] = ""
        save_config(self.config)
        self.app.push_screen(ExecutionScreen(self.disk, self.config, resume=self.resume))


class ExecutionScreen(Screen):
    STEP_ICONS = {
        StepStatus.PENDING: ("[ ]", "step-pending"),
        StepStatus.RUNNING: ("[>]", "step-running"),
        StepStatus.OK: ("[x]", "step-ok"),
        StepStatus.FAILED: ("[!]", "step-failed"),
        StepStatus.SKIPPED: ("[-]", "step-skipped"),
        StepStatus.CANCELLED: ("[#]", "step-skipped"),
    }

    def __init__(self, disk: DiskInfo, config: dict, resume: bool = False) -> None:
        super().__init__()
        self.disk = disk
        self.config = config
        self.resume = resume
        self._step_widgets: dict[str, Static] = {}
        self._start_time = time.monotonic()
        self._cancelled = False
        self._done = False
        self._log_lines: list[str] = []
        self._operation = "Preparing"
        self._progress = 0.0
        self._eta = ""
        self._speed = 0.0
        self._pattern = ""
        self._elapsed = ""
        self._errors = (0, 0, 0)
        self._bad_blocks = 0
        self._test_mode = self.app.test_mode
        self._last_pct = 0.0
        self._last_pct_time = 0.0
        self._current_step = ""

    def compose(self) -> ComposeResult:
        mode = "  |  TEST MODE" if self.app.test_mode else ""
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  |  Validation{mode}", id="header")
            with Horizontal(id="body"):
                with VerticalScroll(classes="steps-col"):
                    yield Static("Stages", classes="panel-title")
                    for step in PIPELINE_STAGES:
                        widget = Static(f"[ ]  {step}", classes="step-pending")
                        self._step_widgets[step] = widget
                        yield widget
                with VerticalScroll(classes="output-col"):
                    with Horizontal():
                        yield Static("Operation\n—", id="m-op", classes="metric-card")
                        yield Static("Progress\n—", id="m-pct", classes="metric-card")
                        yield Static("ETA\n—", id="m-eta", classes="metric-card")
                    with Horizontal():
                        yield Static("Speed\n—", id="m-spd", classes="metric-card")
                        yield Static("Pattern\n—", id="m-pat", classes="metric-card")
                        yield Static("Elapsed\n—", id="m-elapsed", classes="metric-card")
                    with Horizontal():
                        yield Static("Bad Blocks\n—", id="m-bad", classes="metric-card")
                        yield Static("Errors\n—", id="m-err", classes="metric-card")
                        yield Static("Status\n—", id="m-status", classes="metric-card")
                    with Horizontal(classes="disk-info-row"):
                        yield Static("", id="disk-model")
                        yield Static("", id="disk-serial")
                        yield Static("", id="disk-smart")
                    with VerticalScroll(id="output-log"):
                        yield Static("", id="output-log-text")
            yield Static("  [C] Cancel   |   Elapsed 00:00:00", id="footer")

    def on_mount(self) -> None:
        self.set_interval(1.0, self._tick)
        try:
            self.query_one("#disk-model", Static).update(f"Model\n{self.disk.model}")
            self.query_one("#disk-serial", Static).update(f"Serial\n{self.disk.serial}")
        except Exception:
            pass
        if self.disk.smart_supported and not self.disk.is_mock:
            self._fetch_smart()
        self._run()

    def on_key(self, event) -> None:
        if event.key.lower() == "c" and not self._done:
            self._cancelled = True

    def _tick(self) -> None:
        if self._done:
            return
        elapsed = _fmt_duration(time.monotonic() - self._start_time)
        try:
            self.query_one("#footer", Static).update(f"  [C] Cancel   |   Elapsed {elapsed}")
        except Exception:
            pass

    @work(thread=True, exit_on_error=False)
    def _fetch_smart(self) -> None:
        try:
            sd = read_smart(self.disk.device)
        except Exception:
            sd = None
        try:
            self.app.call_from_thread(self._show_smart, sd)
        except Exception:
            pass

    def _show_smart(self, sd) -> None:
        if not sd:
            return
        try:
            self.query_one("#disk-smart", Static).update(
                f"SMART\n{sd.overall_health}  {sd.temperature if sd.temperature is not None else 'n/a'} C"
            )
        except Exception:
            pass

    @work(thread=True, exit_on_error=False)
    def _run(self) -> None:
        try:
            result = run_pipeline(
                device=self.disk.device,
                disk_info=self.disk,
                filesystem=self.config["filesystem"],
                label=self.config["label"],
                profile=self.config["profile"],
                on_step=self._on_step,
                on_output=self._on_output,
                is_cancelled=lambda: self._cancelled,
                test_mode=self.app.test_mode,
                resume=self.resume,
            )
            try:
                self.app.call_from_thread(self._finish, result, None)
            except Exception as exc:
                logger.error("PIPELINE", f"Could not dispatch completion callback: {exc}")
        except Exception as e:
            import traceback

            full = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.error("PIPELINE", f"Pipeline failed:\n{full}")
            try:
                self.app.call_from_thread(self._finish, None, full)
            except Exception as exc:
                logger.error("PIPELINE", f"Could not dispatch failure callback: {exc}")

    def _on_step(self, name: str, status: StepStatus) -> None:
        try:
            self.app.call_from_thread(self._update_step, name, status)
        except Exception:
            pass

    def _update_step(self, name: str, status: StepStatus) -> None:
        icon, css = self.STEP_ICONS.get(status, ("[ ]", "step-pending"))
        widget = self._step_widgets.get(name)
        if widget:
            widget.update(f"{icon}  {name}")
            for cls in ("step-pending", "step-running", "step-ok", "step-failed", "step-skipped"):
                widget.remove_class(cls)
            widget.add_class(css)
        if status == StepStatus.RUNNING:
            self._current_step = name
            self._operation = name
            self._reset_metrics()

    def _reset_metrics(self) -> None:
        self._progress = 0.0
        self._eta = ""
        self._speed = 0.0
        self._errors = (0, 0, 0)
        self._last_pct = 0.0
        self._last_pct_time = 0.0
        try:
            for metric_id in ("m-pct", "m-eta", "m-spd", "m-pat", "m-elapsed", "m-err", "m-bad", "m-status"):
                self.query_one(f"#{metric_id}", Static).update("—")
            self.query_one("#m-op", Static).update(f"Operation\n{self._operation}")
            self._log_lines = []
            self.query_one("#output-log-text", Static).update("")
        except Exception:
            pass

    def _on_output(self, line: str) -> None:
        try:
            self.app.call_from_thread(self._append, line)
        except Exception:
            pass

    def _append(self, line: str) -> None:
        line = line.strip()
        if not line:
            return
        if "TEST MODE" in line:
            self._test_mode = True
            return
        smart_match = re.match(r"SMART test:\s*(\d+)% complete", line)
        if smart_match:
            self._operation = "SMART Short Self-Test"
            self._progress = float(smart_match.group(1))
            eta_match = re.search(r"ETA\s+(\d+)m(\d+)s", line)
            self._eta = f"{eta_match.group(1)}m{eta_match.group(2)}s" if eta_match else ""
            self._paint()
            return
        bb_match = BB_LINE_RE.match(line)
        if bb_match:
            pattern, pct, elapsed, r, w, c = bb_match.groups()
            if pattern:
                self._pattern = pattern
                self._operation = f"Writing {pattern}"
            elif "Reading and comparing" in line:
                self._operation = f"Reading {self._pattern}" if self._pattern else "Reading"
            elif not self._operation or "SMART" in self._operation:
                self._operation = "Writing"
            self._progress = float(pct)
            self._elapsed = elapsed
            if r is not None:
                self._errors = (int(r), int(w), int(c))
            self._estimate_eta()
            self._paint()
            return
        if line.isdigit():
            self._bad_blocks += 1
            self._paint()
            return
        summary_match = re.match(r"(?:Pass completed,)?\s*(\d+)(?:,\s+(\d+))?\s+bad\s+blocks?\s+found", line)
        if summary_match:
            self._bad_blocks = int(summary_match.group(2) or summary_match.group(1))
            self._paint()
            return
        self._log(line)

    def _estimate_eta(self) -> None:
        now = time.monotonic()
        if self._progress < self._last_pct:
            # Progress went backwards — a new pass (e.g. read-back) has started.
            # Reset tracking so the ETA is recalculated from the current pass.
            self._last_pct = self._progress
            self._last_pct_time = now
            self._eta = ""
            self._speed = 0.0
            return
        if self._progress > self._last_pct and now - self._last_pct_time > 0.5:
            pct_delta = self._progress - self._last_pct
            dt = now - self._last_pct_time
            if pct_delta > 0 and dt > 0:
                remaining = (100 - self._progress) / (pct_delta / dt)
                self._eta = _fmt_duration(remaining)
                if self.disk.capacity_bytes:
                    self._speed = (pct_delta / dt) / 100 * self.disk.capacity_bytes / 1_000_000
            self._last_pct = self._progress
            self._last_pct_time = now

    def _log(self, line: str) -> None:
        self._log_lines.append(line)
        del self._log_lines[:-60]
        try:
            log = self.query_one("#output-log", VerticalScroll)
            self.query_one("#output-log-text", Static).update("\n".join(self._log_lines[-20:]))
            # scroll_end must run AFTER the layout refresh: the Static's height
            # only updates on the next frame, so scrolling immediately would
            # scroll against the old (1-line) content and stay on top.
            self.call_after_refresh(log.scroll_end, animate=False)
        except Exception:
            pass

    def _paint(self) -> None:
        mode_tag = " [TEST MODE]" if self._test_mode else ""
        is_scan = _is_scan_operation(self._operation)
        try:
            self.query_one("#m-op", Static).update(f"Operation\n{self._operation}{mode_tag}")
            if is_scan or self._progress > 0:
                self.query_one("#m-pct", Static).update(f"Progress\n{self._progress:.1f}%")
            if self._eta:
                self.query_one("#m-eta", Static).update(f"ETA\n{self._eta}")
            elif is_scan:
                self.query_one("#m-eta", Static).update("ETA\n—")
            if self._speed > 0:
                self.query_one("#m-spd", Static).update(f"Speed\n{self._speed:.1f} MB/s")
            elif is_scan:
                self.query_one("#m-spd", Static).update("Speed\n—")
            if self._pattern and is_scan:
                self.query_one("#m-pat", Static).update(f"Pattern\n{self._pattern}")
            if self._elapsed and is_scan:
                self.query_one("#m-elapsed", Static).update(f"Elapsed\n{self._elapsed}")
            if is_scan:
                self.query_one("#m-bad", Static).update(f"Bad Blocks\n{self._bad_blocks if self._bad_blocks else 'none'}")
            r, w, c = self._errors
            if is_scan:
                self.query_one("#m-err", Static).update(f"Errors\n{r}/{w}/{c}" if (r or w or c) else "Errors\nnone")
            if is_scan:
                self.query_one("#m-status", Static).update("Status\nDestructive scan")
        except Exception:
            pass

    def _finish(self, result: OperationResult | None, error: str | None) -> None:
        self._done = True
        try:
            self.app.push_screen(CompleteScreen(self.disk, self.config, result, error=error))
        except Exception:
            pass


class CompleteScreen(Screen):
    BINDINGS = [
        Binding("enter", "another", "Another", priority=True),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self, disk: DiskInfo, config: dict, result: OperationResult | None, error: str | None = None) -> None:
        super().__init__()
        self.disk = disk
        self.config = config
        self.result = result
        self.error = error

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  |  Complete", id="header")
            with VerticalScroll(id="body"):
                if self.result:
                    yield from self._compose_success()
                else:
                    with Container(classes="panel-err"):
                        yield Static("Pipeline failed or was cancelled.", classes="err")
                    if self.error:
                        with Container(classes="panel"):
                            yield Static("Details", classes="panel-title")
                            for line in self.error.strip().splitlines()[-10:]:
                                yield Static(line, classes="muted")
            yield Horizontal(
                Button(" Export Report ", id="export-btn"),
                Button(" Another Drive ", id="another-btn"),
                Button(" Quit ", id="quit-btn"),
                classes="btn-row",
            )
            yield Static("  Enter another    Q quit", id="footer")

    def _compose_success(self) -> ComposeResult:
        result = self.result
        cls = result.classification
        css_class = {
            "GOLD": "ok",
            "SILVER": "accent",
            "BRONZE": "warn",
            "BAD": "err",
            "FAILED": "err",
        }.get(cls.classification.value, "muted")
        with Container(classes="panel"):
            yield Static(f"{cls.classification.value}", classes=css_class)
            yield Static(cls.recommendation, classes="muted")
        with Container(classes="panel"):
            yield Static(f"Drive:  {self.disk.model}", classes="panel-title")
            yield Static(f"Serial: {self.disk.serial}   |   Capacity: {self.disk.capacity_human}", classes="muted")
            yield Static(f"Filesystem: {self.config['filesystem'].upper()}   |   Label: {self.config.get('label') or '(none)'}", classes="muted")
        if result.snapshot.smart_before and result.snapshot.smart_after:
            before = result.snapshot.smart_before
            after = result.snapshot.smart_after
            delta = result.snapshot.smart_delta
            with Container(classes="panel"):
                yield Static("SMART comparison", classes="panel-title")
                for label, b, a, d in [
                    ("Reallocated sectors", before.reallocated_sectors, after.reallocated_sectors, delta.reallocated if delta else None),
                    ("Pending sectors", before.pending_sectors, after.pending_sectors, delta.pending if delta else None),
                    ("Uncorrectable", before.uncorrectable_sectors, after.uncorrectable_sectors, delta.uncorrectable if delta else None),
                    ("CRC errors", before.crc_errors, after.crc_errors, delta.crc_errors if delta else None),
                ]:
                    dtext = "unchanged" if d == 0 else f"{'+' if d and d > 0 else ''}{d}"
                    yield Static(f"  {label:<22} before {b:<6} after {a:<6} delta {dtext}", classes="muted")
        with Container(classes="panel"):
            yield Static("Assessment", classes="panel-title")
            for reason in cls.reasons:
                yield Static(f"  - {reason}", classes="muted")
        duration = _fmt_duration(result.total_duration_seconds)
        with Container(classes="panel"):
            yield Static(f"Duration: {duration}", classes="muted")
            yield Static(f"Bad blocks: {result.snapshot.badblocks_count}", classes="muted")
            if result.report_path:
                yield Static(f"Report: {result.report_path}", classes="ok")

    def action_another(self) -> None:
        self._go_another()

    def action_quit_app(self) -> None:
        self.app.exit()

    def on_button_pressed(self, event) -> None:
        if event.button.id == "export-btn":
            self._export()
        elif event.button.id == "another-btn":
            self._go_another()
        elif event.button.id == "quit-btn":
            self.app.exit()

    def _go_another(self) -> None:
        main = self.app.screen_stack[0]
        self.app.pop_to_root()
        if isinstance(main, MainScreen):
            main.refresh_drives()

    def _export(self) -> None:
        if not self.result or not self.result.report_path:
            return
        report_dir = os.path.dirname(self.result.report_path)
        try:
            subprocess.Popen(
                ["xdg-open", report_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        try:
            self.query_one("#footer", Static).update("  Report folder opened.    Q quit")
        except Exception:
            pass
