from __future__ import annotations
import os
import re
import subprocess
import sys
import threading
import time
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Button, Input, ProgressBar
from textual import work
from obg import __version__

from obg.core.detector import list_disks, list_mock_disks
from obg.core.engine import run_pipeline, STEPS as PIPELINE_STAGES
from obg.core.reporter import _format_duration as _format_eta
from obg.core.health import read_smart
from obg.core.session import find_session, complete_session
from obg.config import load_config, save_config, VALID_PROFILES, VALID_FILESYSTEMS
from obg.models.disk import DiskInfo
from obg.models.operation import StepStatus, OperationResult


def _get_mounted_partitions(device: str) -> list[tuple[str, str]]:
    try:
        with open("/proc/mounts") as f:
            mounts = [l.split() for l in f.readlines() if l.strip()]
    except OSError:
        return []
    result = []
    for parts in mounts:
        if len(parts) >= 2 and parts[0].startswith(device):
            result.append((parts[0], parts[1]))
    return result


def _unmount_partitions(partitions: list[tuple[str, str]]) -> list[str]:
    import subprocess as _sp
    errors = []
    for dev, mnt in partitions:
        result = _sp.run(["umount", mnt], capture_output=True, text=True)
        if result.returncode != 0:
            errors.append(f"{mnt} ({dev}): {(result.stderr or result.stdout or 'failed').strip()}")
    return errors


class ObgApp(App):
    def __init__(self, test_mode: bool = False, mock_path: str | None = None):
        super().__init__()
        self.test_mode = test_mode
        self.mock_path = mock_path

    CSS = """
    Screen { background: #000000; align: center middle; }
    #app-frame { width: 100%; height: 100%; max-width: 150; max-height: 80; border: solid #444444; background: #0a0a0a; layout: vertical; }
    #header { dock: top; height: 1; background: #111111; color: #cccccc; padding: 0 1; }
    #body { height: 1fr; overflow-y: auto; }
    #footer { dock: bottom; height: 1; background: #111111; color: #666666; padding: 0 1; }
    .card { border: solid #333333; margin: 0 1 1 1; padding: 0 1; }
    .card-selected { border: solid #1a1a2e; margin: 0 1 1 1; padding: 0 1; background: #1a1a2e; }
    .card:hover { background: #1a1a2e; }
    .card-disabled { border: solid #333333; margin: 0 1 1 1; padding: 0 1; color: #555555; }
    .group-title { color: #cccccc; text-style: bold; margin-top: 1; }
    .config-group { margin: 0 0 0 2; }
    .config-label { color: #666666; margin-top: 1; }
    .warning { color: #ffff00; text-style: bold; }
    .ok { color: #00ff00; }
    .step-ok { color: #00ff00; }
    .step-running { color: #ffff00; }
    .step-failed { color: #ff0000; }
    .step-pending { color: #666666; }
    .step-skipped { color: #666666; }
    .gold { color: #00ff00; text-style: bold; }
    .silver { color: #aaaaaa; text-style: bold; }
    .bronze { color: #cd7f32; text-style: bold; }
    .failed { color: #ff0000; text-style: bold; }
    .empty-msg { content-align: center middle; height: 100%; color: #666666; }
    .btn-row { height: 3; align: center middle; }
    .btn-row Button { width: 1fr; margin: 0 1; }
    .steps-col { width: 30%; min-width: 25; }
    .output-col { width: 70%; min-width: 40; }
    .panel-box { border: solid #333333; margin: 0 1; padding: 0 1; }
    .dialog-overlay { background: rgba(0,0,0,0.7); align: center middle; }
    .dialog-box { width: 50; min-width: 40; border: solid #333333; background: #111111; padding: 1; }
    .progress-info { color: #aaaaaa; }
    ProgressBar { margin: 0 2; }
    #metrics-list { border: solid #333333; margin: 0 1; padding: 0 1; color: #aaaaaa; min-height: 8; }
    .startup-btn { width: 1fr; margin: 0 1; }
    .startup-btn.selected { background: #1a3a1a; border: solid #00ff00; }
    .metric-box { border: solid #333333; margin: 0 1 1 1; padding: 0 1; width: 1fr; }
    .metric-row { height: auto; }
    .metric-row > .metric-box { width: 1fr; }
    """

    def on_mount(self) -> None:
        self.push_screen(StartupScreen())


class StartupScreen(Screen):
    BINDINGS = [
        Binding("left", "left", "", priority=True),
        Binding("right", "right", "", priority=True),
        Binding("enter", "enter", "Proceed", priority=True),
        Binding("escape", "escape", "Exit", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self._selected = 0

    def action_left(self) -> None:
        self._selected = 0
        self._update_buttons()

    def action_right(self) -> None:
        self._selected = 1
        self._update_buttons()

    def action_enter(self) -> None:
        if self._selected == 0:
            btn = self.query_one("#continue-btn")
            if not btn.disabled:
                self.app.push_screen(DriveSelectionScreen())
        else:
            self.app.exit()

    def action_escape(self) -> None:
        self.app.exit()

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  /  Startup", id="header")
            with VerticalScroll(id="body"):
                yield Static("", classes="config-group")
                yield Static("  OLD BUT GOLD", classes="group-title")
                yield Static("  HDD Validation & Refurbishment Toolkit", classes="config-group")
                yield Static("", classes="config-group")
                yield Static("  Legal Disclaimer", classes="group-title")
                yield Static(
                    "  OldButGold performs hardware validation using industry-standard diagnostic utilities.\n"
                    "  Validation results reflect only the observed condition of the storage device during execution.\n"
                    "  No report constitutes a guarantee of future reliability, data integrity or continued operation.\n"
                    "  Storage devices may fail without prior warning. The user remains solely responsible for\n"
                    "  backup, data protection and all decisions made based on this report.\n"
                    "  Use of this software is entirely at the user's own risk.",
                    classes="config-group",
                )
                yield Static("", classes="config-group")
                yield Static("  Initializing...", id="init-status", classes="config-group")
            yield Horizontal(
                Button(" Continue ", id="continue-btn", classes="startup-btn selected", disabled=True),
                Button(" Exit ", id="exit-btn", classes="startup-btn"),
                classes="btn-row",
            )
            yield Static("  Initializing, please wait...", id="footer")

    def on_mount(self) -> None:
        self._init()

    def _update_buttons(self) -> None:
        try:
            self.query_one("#continue-btn").remove_class("selected")
            self.query_one("#exit-btn").remove_class("selected")
            if self._selected == 0:
                self.query_one("#continue-btn").add_class("selected")
            else:
                self.query_one("#exit-btn").add_class("selected")
        except Exception:
            pass

    def on_button_pressed(self, event) -> None:
        if event.button.id == "continue-btn":
            self.app.push_screen(DriveSelectionScreen())
        elif event.button.id == "exit-btn":
            self.app.exit()

    @work(thread=True)
    def _init(self) -> None:
        try:
            disks = list_disks()
            if self.app.mock_path:
                disks = list_mock_disks(self.app.mock_path) + disks
            self.app.call_from_thread(self._init_done, disks)
        except Exception as e:
            self.app.call_from_thread(self._init_error, str(e))

    def _init_done(self, disks) -> None:
        try:
            self.query_one("#init-status").update(f"  Detected {len(disks)} drive(s). Ready.")
            self.query_one("#continue-btn").disabled = False
            self.query_one("#footer").update("  \u2190/\u2192 Navigate  Enter Select  Esc Exit")
        except Exception:
            pass

    def _init_error(self, msg: str) -> None:
        try:
            self.query_one("#init-status").update(f"  Error: {msg}")
        except Exception:
            pass


class DriveSelectionScreen(Screen):
    BINDINGS = [("r", "refresh", "Refresh")]

    def __init__(self) -> None:
        super().__init__()
        self._disks: list[DiskInfo] = []
        self._selected = 0

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  /  Select Drive", id="header")
            with VerticalScroll(id="body"):
                pass
            yield Horizontal(
                Button(" Back ", id="back-btn"),
                Button(" Continue ", id="continue-btn"),
                Button(" Refresh ", id="refresh-btn"),
                Button(" Quit ", id="quit-btn"),
                classes="btn-row",
            )
            yield Static("  \u2191/\u2193 Select   Enter Confirm   R Refresh   Esc Back", id="footer")

    def on_mount(self) -> None:
        self._refresh()

    def action_refresh(self) -> None:
        self._refresh()

    @work(thread=True)
    def _refresh(self) -> None:
        try:
            disks = list_disks()
            if self.app.mock_path:
                disks = list_mock_disks(self.app.mock_path) + disks
        except Exception:
            disks = []
        self.app.call_from_thread(self._rebuild_with, disks)

    def _rebuild_with(self, disks: list[DiskInfo]) -> None:
        self._disks = disks
        self._selected = 0
        self._rebuild()

    def _rebuild(self) -> None:
        c = self.query_one("#body")
        c.remove_children()
        if not self._disks:
            c.mount(Static("No drives detected. Press R to refresh.", classes="empty-msg"))
            return
        for i, disk in enumerate(self._disks):
            if disk.is_supported:
                selected = i == self._selected
                lines = [f"  {disk.model}", f"  {disk.device}  {disk.transport}  {disk.capacity_human}"]
                if disk.is_mounted or disk.is_boot_disk:
                    lines.append(f"  ! WARNING: Drive contains active filesystem — all data will be destroyed !")
                session = find_session(disk)
                if session:
                    total_blocks = disk.capacity_bytes // 4096 if disk.capacity_bytes else 1
                    pct = min(99, int(session.get("badblocks_offset", 0) / total_blocks * 100))
                    lines.append(f"  ! Interrupted Validation  -  {pct}%")
                widget = Static("\n".join(lines), classes="card-selected" if selected else "card")
            else:
                widget = Static(f"  {disk.model}\n  {disk.device}  {disk.capacity_human}  [Unsupported]",
                                classes="card-disabled")
            widget.idx = i
            c.mount(widget)

    def on_key(self, event) -> None:
        if event.key == "up":
            self._selected = max(0, self._selected - 1)
            self._rebuild()
        elif event.key == "down":
            self._selected = min(len(self._disks) - 1, self._selected + 1)
            self._rebuild()
        elif event.key == "enter":
            self._select()
        elif event.key == "escape":
            self.app.pop_screen()

    def on_button_pressed(self, event) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "continue-btn":
            self._select()
        elif event.button.id == "refresh-btn":
            self._refresh()
        elif event.button.id == "quit-btn":
            self.app.exit()

    def on_click(self, event) -> None:
        idx = getattr(event.widget, 'idx', None)
        if idx is not None and 0 <= idx < len(self._disks):
            self._selected = idx
            self._rebuild()
            self._select()

    def _select(self) -> None:
        if not self._disks:
            return
        disk = self._disks[self._selected]
        if not disk.is_supported:
            return
        if disk.is_mounted and not disk.is_mock:
            mounts = _get_mounted_partitions(disk.device)
            if mounts:
                self.app.push_screen(MountWarningScreen(disk, mounts))
                return
        session = find_session(disk)
        if session:
            self.app.push_screen(SessionDecisionScreen(disk, session))
        else:
            self.app.push_screen(DriveInfoScreen(disk))


class SessionDecisionScreen(Screen):
    def __init__(self, disk: DiskInfo, session: dict) -> None:
        super().__init__()
        self.disk = disk
        self.session = session

    def compose(self) -> ComposeResult:
        total_blocks = self.disk.capacity_bytes // 4096 if self.disk.capacity_bytes else 1
        pct = min(99, int(self.session.get("badblocks_offset", 0) / total_blocks * 100))
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  /  Session Recovery", id="header")
            with VerticalScroll(id="body"):
                yield Static("  Interrupted Validation Session", classes="group-title")
                yield Static("")
                yield Static(f"  Model:         {self.disk.model}")
                yield Static(f"  Serial:        {self.disk.serial}")
                yield Static(f"  Capacity:      {self.disk.capacity_human}")
                yield Static(f"  Current Stage: {self.session.get('current_stage', 'Badblocks Validation')}")
                yield Static(f"  Completed:     {pct}%")
                yield Static(f"  Started:       {self.session.get('created_at', 'Unknown')}")
                yield Static("")
                yield Static("  This drive has an interrupted validation session.", classes="config-group")
                yield Static("  What would you like to do?", classes="config-group")
            yield Horizontal(
                Button(" Recover ", id="recover-btn"),
                Button(" Restart ", id="restart-btn"),
                Button(" View Details ", id="details-btn"),
                Button(" Back ", id="back-btn"),
                classes="btn-row",
            )
            yield Static("  Enter Select   Esc Back", id="footer")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "enter":
            self.app.push_screen(ValidationConfigScreen(self.disk, resume=True))

    def on_button_pressed(self, event) -> None:
        if event.button.id == "recover-btn":
            self.app.push_screen(ValidationConfigScreen(self.disk, resume=True))
        elif event.button.id == "restart-btn":
            complete_session(self.disk)
            self.app.push_screen(DriveInfoScreen(self.disk))
        elif event.button.id == "details-btn":
            self.app.push_screen(DriveInfoScreen(self.disk, None))
        elif event.button.id == "back-btn":
            self.app.pop_screen()


class MountWarningScreen(Screen):
    def __init__(self, disk: DiskInfo, mounts: list[tuple[str, str]]) -> None:
        super().__init__()
        self.disk = disk
        self.mounts = mounts
        self._unmount_errors: list[str] = []

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  /  Drive Mounted", id="header")
            with VerticalScroll(id="body"):
                yield Static(f"  {self.disk.model}", classes="group-title")
                yield Static(f"  {self.disk.device}  {self.disk.capacity_human}")
                yield Static("")
                yield Static("  This drive has mounted partitions:", classes="warning")
                for dev, mnt in self.mounts:
                    yield Static(f"  \u2022 {dev}  \u2192  {mnt}", classes="config-group")
                yield Static("")
                yield Static("  All data on these partitions will be", classes="config-group")
                yield Static("  inaccessible until remounted.", classes="config-group")
                yield Static("", id="unmount-status")
            yield Horizontal(
                Button(" Unmount & Continue ", id="unmount-btn"),
                Button(" Back ", id="back-btn"),
                classes="btn-row",
            )
            yield Static("  Esc Back   Enter Unmount", id="footer")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "enter":
            self._do_unmount()

    def on_button_pressed(self, event) -> None:
        if event.button.id == "unmount-btn":
            self._do_unmount()
        elif event.button.id == "back-btn":
            self.app.pop_screen()

    @work(thread=True)
    def _do_unmount(self) -> None:
        self.app.call_from_thread(self._set_status, "  Unmounting...", "info")
        errs = _unmount_partitions(self.mounts)
        if errs:
            self.app.call_from_thread(self._set_status, "  " + "\n  ".join(errs), "failed")
            return
        self.app.call_from_thread(self._proceed)

    def _set_status(self, msg: str, cls: str = "info") -> None:
        try:
            self.query_one("#unmount-status").update(msg)
            self.query_one("#unmount-status").remove_class("info", "failed")
            self.query_one("#unmount-status").add_class(cls)
        except Exception:
            pass

    def _proceed(self) -> None:
        session = find_session(self.disk)
        if session:
            self.app.push_screen(SessionDecisionScreen(self.disk, session))
        else:
            self.app.push_screen(DriveInfoScreen(self.disk))





class DriveInfoScreen(Screen):
    def __init__(self, disk: DiskInfo, smart_data=None, resume: bool = False) -> None:
        super().__init__()
        self.disk = disk
        self._smart_data = smart_data
        self.resume = resume

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  /  Drive Info  /  {self.disk.model}", id="header")
            with VerticalScroll(id="body"):
                with Horizontal():
                    with VerticalScroll(classes="panel-box"):
                        yield Static("  Device Information", classes="group-title")
                        yield Static(f"  Model:  {self.disk.model}")
                        yield Static(f"  Serial: {self.disk.serial}")
                        yield Static(f"  Firmware: {self.disk.firmware}")
                        yield Static(f"  Capacity: {self.disk.capacity_human}")
                        yield Static(f"  WWN: {self.disk.wwn or 'N/A'}")
                        yield Static(f"  Device: {self.disk.device}")
                    with VerticalScroll(classes="panel-box"):
                        yield Static("  Configuration", classes="group-title")
                        yield Static(f"  Interface: {self.disk.interface}")
                        yield Static(f"  Transport: {self.disk.transport}")
                        yield Static(f"  SMART: {'Supported' if self.disk.smart_supported else 'Not available'}")
                        yield Static(f"  Current FS: {self.disk.current_fs or 'None'}")
                        yield Static(f"  Partition: {self.disk.partition_table or 'None'}")
                with Horizontal():
                    with VerticalScroll(classes="panel-box"):
                        yield Static("  SMART Information", classes="group-title")
                        yield Static("  Reading SMART data...", id="smart-panel")
                    with VerticalScroll(classes="panel-box"):
                        yield Static("  Geometry", classes="group-title")
                        yield Static(f"  Logical Sector:  {self.disk.logical_sector} B")
                        yield Static(f"  Physical Sector: {self.disk.physical_sector} B")
            yield Horizontal(
                Button(" Continue ", id="continue-btn"),
                Button(" Back ", id="back-btn"),
                classes="btn-row",
            )
            yield Static("  Esc Back   Enter Continue", id="footer")

    def on_mount(self) -> None:
        if self._smart_data is not None:
            self._update_smart(self._smart_data)
        else:
            self._fetch_smart()

    def on_key(self, event) -> None:
        if event.key == "escape":
            while len(self.app.screen_stack) > 2:
                self.app.pop_screen()
        elif event.key == "enter":
            self.app.push_screen(ValidationConfigScreen(self.disk, resume=self.resume))

    def on_button_pressed(self, event) -> None:
        if event.button.id == "continue-btn":
            self.app.push_screen(ValidationConfigScreen(self.disk, resume=self.resume))
        elif event.button.id == "back-btn":
            while len(self.app.screen_stack) > 2:
                self.app.pop_screen()

    @work(thread=True)
    def _fetch_smart(self) -> None:
        if self.disk.is_mock:
            self.app.call_from_thread(self._update_smart, None)
            return
        try:
            sd = read_smart(self.disk.device)
            self.app.call_from_thread(self._update_smart, sd)
        except Exception:
            self.app.call_from_thread(self._update_smart, None)

    def _update_smart(self, sd) -> None:
        try:
            panel = self.query_one("#smart-panel")
            if sd:
                panel.update(
                    f"  Health: {sd.overall_health}\n"
                    f"  Temp: {sd.temperature or 'N/A'} C\n"
                    f"  Power-on: {sd.power_on_hours or 'N/A'} h\n"
                    f"  Power Cycles: {sd.power_cycle_count or 'N/A'}\n"
                    f"  Reallocated: {sd.reallocated_sectors}\n"
                    f"  Pending: {sd.pending_sectors}\n"
                    f"  Uncorrectable: {sd.uncorrectable_sectors}\n"
                    f"  CRC Errors: {sd.crc_errors}"
                )
            else:
                panel.update("  SMART not available")
        except Exception:
            pass


class ValidationConfigScreen(Screen):
    BINDINGS = [("escape", "go_back")]

    def __init__(self, disk: DiskInfo, resume: bool = False) -> None:
        super().__init__()
        self.disk = disk
        self.resume = resume
        self.config = load_config()
        self.FS_OPTIONS = VALID_FILESYSTEMS
        self.PROFILES = [p.capitalize() for p in VALID_PROFILES]
        self.PROFILE_DESCRIPTIONS = {
            "recommended": "Optimized validation created for OldButGold.\nUses two destructive validation patterns (0xAA and 0x55)\nwith 4 KiB blocks for significantly faster validation.",
            "extended": "Original native badblocks destructive validation\nusing all default patterns for maximum confidence.",
        }
        self._profile_idx = next((i for i, p in enumerate(VALID_PROFILES) if p == self.config["profile"]), 0)
        self._fs_idx = self.FS_OPTIONS.index(self.config["filesystem"]) if self.config["filesystem"] in self.FS_OPTIONS else 0

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  /  Configuration", id="header")
            with VerticalScroll(id="body"):
                yield Static("  Validation Profile", classes="group-title")
                for p in self.PROFILES:
                    marker = "(*)" if p.lower() == self.PROFILES[self._profile_idx].lower() else "( )"
                    yield Static(f"  {marker} {p}", id=f"prof-{p.lower()}", classes="config-group")
                yield Static("", id="profile-desc")
                yield Static("  Filesystem", classes="config-label")
                for f in self.FS_OPTIONS:
                    marker = "(*)" if f == self.FS_OPTIONS[self._fs_idx] else "( )"
                    yield Static(f"  {marker} {f}", id=f"fs-{f}", classes="config-group")
                yield Static("  Volume Label (optional)", classes="config-label")
                yield Input(value=self.config.get("label", ""), id="label-input", classes="config-group")
            yield Horizontal(
                Button(" Back ", id="back-btn"),
                Button(" Continue ", id="continue-btn"),
                classes="btn-row",
            )
            yield Static("  Esc Back   Enter Continue", id="footer")

    def on_mount(self) -> None:
        try:
            self.query_one("#label-input").focus()
        except Exception:
            pass
        self._update_description()

    def on_key(self, event) -> None:
        if event.key == "up" and not isinstance(self.focused, Input):
            self._move(-1, -1)
        elif event.key == "down" and not isinstance(self.focused, Input):
            self._move(1, 1)
        elif event.key == "left" and not isinstance(self.focused, Input):
            self._move(-1, 0)
        elif event.key == "right" and not isinstance(self.focused, Input):
            self._move(1, 0)
        elif event.key == "enter" and not isinstance(self.focused, Input):
            self._continue()

    def on_click(self, event) -> None:
        cid = getattr(event.widget, 'id', None)
        if cid and cid.startswith("prof-"):
            p = cid[5:]
            if p in VALID_PROFILES:
                self._profile_idx = VALID_PROFILES.index(p)
                self._update_labels()
        elif cid and cid.startswith("fs-"):
            f = cid[3:]
            if f in self.FS_OPTIONS:
                self._fs_idx = self.FS_OPTIONS.index(f)
                self._update_labels()

    def _move(self, direction: int, axis: int) -> None:
        if axis == 1:
            self._profile_idx = (self._profile_idx + direction) % len(self.PROFILES)
        else:
            if direction > 0:
                self._fs_idx = (self._fs_idx + 1) % len(self.FS_OPTIONS)
            else:
                self._fs_idx = (self._fs_idx - 1) % len(self.FS_OPTIONS)
        self._update_labels()

    def _update_labels(self) -> None:
        for p in self.PROFILES:
            try:
                marker = "(*)" if p.lower() == self.PROFILES[self._profile_idx].lower() else "( )"
                self.query_one(f"#prof-{p.lower()}").update(f"  {marker} {p}")
            except Exception:
                pass
        for f in self.FS_OPTIONS:
            try:
                marker = "(*)" if f == self.FS_OPTIONS[self._fs_idx] else "( )"
                self.query_one(f"#fs-{f}").update(f"  {marker} {f}")
            except Exception:
                pass
        self._update_description()

    def _update_description(self) -> None:
        name = VALID_PROFILES[self._profile_idx]
        desc = self.PROFILE_DESCRIPTIONS.get(name, "")
        try:
            self.query_one("#profile-desc").update(f"  {desc}")
        except Exception:
            pass

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "continue-btn":
            self._continue()

    def _continue(self) -> None:
        self.config["profile"] = self.PROFILES[self._profile_idx].lower()
        self.config["filesystem"] = self.FS_OPTIONS[self._fs_idx]
        label = self.query_one("#label-input").value.strip()
        self.config["label"] = label
        save_config(self.config)
        self.app.push_screen(FinalConfirmationScreen(self.disk, self.config, resume=self.resume))


class FinalConfirmationScreen(Screen):
    def __init__(self, disk: DiskInfo, config: dict, resume: bool = False) -> None:
        super().__init__()
        self.disk = disk
        self.config = config
        self.resume = resume

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  /  Confirm", id="header")
            with VerticalScroll(id="body"):
                yield Static("  Validation Summary", classes="group-title")
                yield Static(f"  Drive:  {self.disk.model}")
                yield Static(f"  Serial: {self.disk.serial}")
                yield Static(f"  Capacity: {self.disk.capacity_human}")
                yield Static("")
                yield Static(f"  Profile:     {self.config['profile'].title()}")
                yield Static(f"  Filesystem:  {self.config['filesystem']}")
                yield Static(f"  Label:       {self.config.get('label', '(none)') or '(none)'}")
                yield Static("")
                if self.disk.is_mounted or self.disk.is_boot_disk:
                    yield Static("  !  DRIVE HAS AN ACTIVE FILESYSTEM!", classes="warning")
                    yield Static("  !  ALL EXISTING DATA WILL BE", classes="warning")
                    yield Static("  !  PERMANENTLY DESTROYED.", classes="warning")
                else:
                    yield Static("  !  ALL EXISTING DATA WILL BE", classes="warning")
                    yield Static("  !  PERMANENTLY DESTROYED.", classes="warning")
            yield Horizontal(
                Button(" Back ", id="back-btn"),
                Button(" Start Validation ", id="start-btn"),
                classes="btn-row",
            )
            yield Static("  Esc Back   Enter Start", id="footer")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "enter":
            self._start()

    def on_button_pressed(self, event) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "start-btn":
            self._start()

    def _start(self) -> None:
        self.app.push_screen(ExecutionScreen(self.disk, self.config, resume=self.resume))



class ExecutionScreen(Screen):
    def __init__(self, disk: DiskInfo, config: dict, resume: bool = False) -> None:
        super().__init__()
        self.disk = disk
        self.config = config
        self.resume = resume
        self._step_widgets: dict[str, Static] = {}
        self._start_time = time.monotonic()
        self._cancelled = False
        self._done = False
        self._bb_progress = 0.0
        self._bb_eta = ""
        self._bb_operation = ""
        self._bb_pattern = "—"
        self._bb_elapsed_str = "—"
        self._bb_speed = 0.0
        self._bb_errors = (0, 0, 0)
        self._bb_bad_count = 0
        self._bb_test_mode = False
        self._last_pct_time = 0.0
        self._last_pct = 0.0
        self._bb_blocksize = 4096
        self._current_step = ""
        if disk.capacity_bytes:
            self._bb_total_blocks = disk.capacity_bytes // self._bb_blocksize
        else:
            self._bb_total_blocks = 0

    def compose(self) -> ComposeResult:
        mode = "  [TEST MODE]" if self.app.test_mode else ""
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  /  Validation{mode}", id="header")
            with VerticalScroll(id="body"):
                with Horizontal():
                    with VerticalScroll(classes="steps-col"):
                        yield Static("  Steps", classes="group-title")
                        for s in PIPELINE_STAGES:
                            w = Static(f"  [ ]  {s}", classes="step-pending")
                            self._step_widgets[s] = w
                            yield w
                    with VerticalScroll(classes="output-col"):
                        yield ProgressBar(total=100, id="bb-progress", show_eta=False)
                        yield Static("", id="metrics-list")
            yield Static("  [C] Cancel  —  Elapsed: 00:00:00", id="footer")

    def on_mount(self) -> None:
        self.set_interval(1.0, self._tick)
        self._update_progress()
        self._run()

    def on_key(self, event) -> None:
        if event.key.lower() == "c" and not self._done:
            self._cancelled = True

    def _tick(self) -> None:
        if self._done:
            return
        e = int(time.monotonic() - self._start_time)
        h, m, s = e // 3600, (e % 3600) // 60, e % 60
        self._update_progress()
        try:
            self.query_one("#footer").update(f"  [C] Cancel  \u2014  Elapsed: {h:02d}:{m:02d}:{s:02d}")
        except Exception:
            pass

    def _on_step(self, name: str, status: StepStatus) -> None:
        self.app.call_from_thread(self._update_step, name, status)

    def _update_step(self, name: str, status: StepStatus) -> None:
        icons = {
            StepStatus.RUNNING: ("[\u25b6]", "step-running"),
            StepStatus.OK: ("[\u2713]", "step-ok"),
            StepStatus.FAILED: ("[\u2717]", "step-failed"),
            StepStatus.SKIPPED: ("[-]", "step-skipped"),
            StepStatus.CANCELLED: ("[/]", "step-skipped"),
            StepStatus.PENDING: ("[ ]", "step-pending"),
        }
        icon, css = icons.get(status, ("[ ]", "step-pending"))
        w = self._step_widgets.get(name)
        if w:
            w.update(f"  {icon}  {name}")
            w.remove_class("step-pending", "step-running", "step-ok", "step-failed", "step-skipped")
            w.add_class(css)
        if status == StepStatus.RUNNING:
            self._current_step = name
            self._show_step_info(name)

    def _show_step_info(self, name: str) -> None:
        self._bb_operation = name
        self._bb_progress = 0
        self._bb_eta = ""
        self._bb_speed = 0
        self._bb_errors = (0, 0, 0)
        try:
            self.query_one("#bb-progress", ProgressBar).update(progress=0)
            self.query_one("#metrics-list").update("")
        except Exception:
            pass

    def _on_output(self, line: str) -> None:
        self.app.call_from_thread(self._append, line)

    def _append(self, line: str) -> None:
        if "TEST MODE" in line:
            self._bb_test_mode = True
            self._bb_operation = line.strip()
            self._update_progress()
            return
        if "RESUME" in line and "resuming from" in line:
            self._update_progress()
            return
        if line.startswith("SMART comparison completed"):
            self._bb_operation = "SMART Comparison"
            self._bb_progress = 100
            self._update_progress()
            try:
                self.query_one("#metrics-list").update(line.replace("SMART comparison completed:\n", "").replace("\n", "\n"))
            except Exception:
                pass
            return
        sm = re.search(r'SMART test:\s*(\d+)% complete.*?(?:ETA\s+(\d+)m(\d+)s)?', line)
        if sm:
            pct = int(sm.group(1))
            self._bb_progress = float(pct)
            self._bb_operation = "SMART Short Self-Test"
            self._bb_pattern = "—"
            if sm.group(2):
                self._bb_eta = f"{sm.group(2)}m{sm.group(3)}s"
            self._update_progress()
            return
        pm = re.search(r'(?:Testing with pattern (\S+):\s+)?([\d.]+)% done,\s+([\d:]+) elapsed\.?\s*(?:\((\d+)/(\d+)/(\d+)\s*errors?\))?', line)
        if pm:
            pat = pm.group(1)
            if pat:
                self._bb_pattern = pat
                self._bb_operation = f"Writing {pat}"
            elif self._bb_operation in ("Preparing...", "SMART Short Self-Test", "SMART test:", "Surface Scan (Badblocks)", "Surface Scan"):
                self._bb_operation = "Writing (destructive)"
            now = time.monotonic()
            pct = float(pm.group(2))
            self._bb_progress = pct
            self._bb_elapsed_str = pm.group(3)
            if pm.group(4):
                self._bb_errors = (int(pm.group(4)), int(pm.group(5)), int(pm.group(6)))
            if pct > self._last_pct:
                elapsed_since = now - self._last_pct_time
                pct_delta = pct - self._last_pct
                if elapsed_since > 0 and pct_delta > 0:
                    rate = pct_delta / elapsed_since
                    remaining_pct = 100 - pct
                    eta_s = remaining_pct / rate if rate > 0 else 0
                    self._bb_eta = _format_eta(eta_s)
                    total_bytes = self.disk.capacity_bytes
                    if total_bytes > 0:
                        self._bb_speed = (rate / 100) * total_bytes / 1_000_000
                self._last_pct = pct
                self._last_pct_time = now
            self._update_progress()
            return
        if line.strip().isdigit():
            self._bb_bad_count += 1
            self._update_progress()
            return
        bm = re.search(r'(\d+),\s+(\d+)\s+bad\s+blocks?\s+found', line)
        if bm:
            self._bb_bad_count = int(bm.group(2))

    def _update_progress(self) -> None:
        try:
            self.query_one("#bb-progress", ProgressBar).update(progress=self._bb_progress)
        except Exception:
            pass
        pct = self._bb_progress
        r, w, c = self._bb_errors
        mode_tag = "  [TEST MODE]" if self._bb_test_mode else ""
        has_errors = r > 0 or w > 0 or c > 0
        is_badblocks = any(kw in self._bb_operation for kw in ("Writing", "pattern"))
        items = [
            ("Operation", self._bb_operation + mode_tag),
        ]
        if is_badblocks or pct > 0:
            items.append(("Progress", f"{pct:.1f}%"))
        if self._bb_eta:
            items.append(("ETA", self._bb_eta))
        if self._bb_speed > 0:
            items.append(("Speed", f"{self._bb_speed:.1f} MB/s"))
        if self._bb_pattern and is_badblocks:
            items.append(("Pattern", self._bb_pattern))
        if self._bb_elapsed_str and is_badblocks:
            items.append(("Elapsed", self._bb_elapsed_str))
        if self._bb_bad_count > 0:
            items.append(("Bad blocks", f"{self._bb_bad_count:,}"))
        elif is_badblocks:
            items.append(("Bad blocks", "None"))
        if has_errors:
            items.append(("Errors", f"{r}/{w}/{c} (R/W/C)"))
        pad = max((len(k) for k, _ in items), default=0) + 2
        lines = [f"  {k:<{pad}}{v}" for k, v in items]
        try:
            self.query_one("#metrics-list").update("\n".join(lines))
        except Exception:
            pass

    @work(thread=True)
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
            self.app.call_from_thread(self._complete, result, None)
        except Exception as e:
            import traceback as _tb
            _full = "".join(_tb.format_exception(type(e), e, e.__traceback__))
            from obg.utils import logger
            logger.error("PIPELINE", f"Pipeline failed:\n{_full}")
            self.app.call_from_thread(self._on_output, f"ERROR: {e}")
            self.app.call_from_thread(self._complete, None, _full)

    def _complete(self, result, error: str | None = None) -> None:
        self._done = True
        try:
            self.app.push_screen(CompleteScreen(self.disk, self.config, result, error=error))
        except Exception:
            pass


class CompleteScreen(Screen):
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, disk: DiskInfo, config: dict, result: OperationResult | None, error: str | None = None) -> None:
        super().__init__()
        self.disk = disk
        self.config = config
        self.result = result
        self.error = error
        self._report_exported = False

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  /  Complete", id="header")
            with VerticalScroll(id="body"):
                if self.result:
                    r = self.result
                    cls_val = r.classification.classification.value
                    yield Static(f"  {cls_val}", classes=cls_val.lower())
                    yield Static("")
                    yield Static(f"  {self.disk.model}")
                    yield Static(f"  {self.disk.serial}  |  {self.disk.capacity_human}")
                    yield Static("")
                    sb = r.snapshot.smart_before
                    sa = r.snapshot.smart_after
                    yield Static(f"  Filesystem:    {self.config['filesystem']}")
                    yield Static(f"  Label:         {self.config['label'] or '(none)'}")
                    yield Static(f"  Bad Blocks:    {r.snapshot.badblocks_count}")
                    yield Static("")
                    yield Static("  SMART Comparison", classes="group-title")
                    if sb and sa:
                        items = [
                            ("Reallocated Sectors", sb.reallocated_sectors, sa.reallocated_sectors, r.snapshot.smart_delta.reallocated if r.snapshot.smart_delta else None),
                            ("Pending Sectors", sb.pending_sectors, sa.pending_sectors, r.snapshot.smart_delta.pending if r.snapshot.smart_delta else None),
                            ("Uncorrectable Sectors", sb.uncorrectable_sectors, sa.uncorrectable_sectors, r.snapshot.smart_delta.uncorrectable if r.snapshot.smart_delta else None),
                            ("CRC Errors", sb.crc_errors, sa.crc_errors, r.snapshot.smart_delta.crc_errors if r.snapshot.smart_delta else None),
                        ]
                        for label, before, after, delta_val in items:
                            d = "unchanged"
                            if delta_val is not None:
                                if delta_val > 0:
                                    d = f"+{delta_val}"
                                elif delta_val < 0:
                                    d = f"{delta_val}"
                            yield Static(f"  {label:22s}  Before: {before:<6d}  After: {after:<6d}  Delta: {d}")
                        temp_str = f"  {'Temperature':22s}  Before: {sb.temperature or 'N/A':<6}  After: {sa.temperature or 'N/A':<6}"
                        if r.snapshot.smart_delta and r.snapshot.smart_delta.temperature is not None:
                            t = r.snapshot.smart_delta.temperature
                            temp_str += f"  Delta: {'+' if t >= 0 else ''}{t}°C"
                        yield Static(temp_str)
                        yield Static(f"  {'Power-On Hours':22s}  Before: {sb.power_on_hours or 'N/A':<6}  After: {sa.power_on_hours or 'N/A':<6}")
                    elif sb:
                        yield Static(f"  Health: {sb.overall_health}")
                    else:
                        yield Static("  SMART data not available")
                    yield Static("")
                    for reason in r.classification.reasons:
                        yield Static(f"  - {reason}")
                    for s in r.steps:
                        if s.status in (StepStatus.FAILED, StepStatus.SKIPPED) and s.error:
                            yield Static(f"  \u2192 {s.name}: {s.error[:200]}", classes="failed")
                    yield Static("")
                    dur = r.total_duration_seconds
                    h = int(dur // 3600)
                    m = int((dur % 3600) // 60)
                    s = int(dur % 60)
                    ds = f"{h}h {m:02d}m {s:02d}s" if h else (f"{m}m {s:02d}s" if m else f"{s}s")
                    yield Static(f"  Duration: {ds}")
                    yield Static("")
                    if r.report_path:
                        yield Static(f"  Report: {r.report_path}")
                        self._report_exported = True
                    else:
                        yield Static("  No report generated.")
                else:
                    yield Static("  Pipeline failed or was cancelled.", classes="failed")
                    if self.error:
                        yield Static("")
                        yield Static("  Root cause:", classes="warning")
                        for line in self.error.strip().splitlines()[-12:]:
                            yield Static(f"  {line}", classes="failed")
            yield Horizontal(
                Button(" Export Report ", id="export-btn"),
                Button(" Validate Another Drive ", id="another-btn"),
                Button(" Quit ", id="quit-btn"),
                classes="btn-row",
            )
            yield Static("  Enter Another   Q Quit", id="footer")

    def on_key(self, event) -> None:
        if event.key == "enter":
            self._go_another()
        elif event.key == "q":
            self.app.exit()

    def on_button_pressed(self, event) -> None:
        if event.button.id == "export-btn":
            self._export_report()
        elif event.button.id == "another-btn":
            self._go_another()
        elif event.button.id == "quit-btn":
            self.app.exit()

    def _export_report(self) -> None:
        if self.result and self.result.report_path:
            self._report_exported = True
            report_dir = os.path.dirname(self.result.report_path)
            try:
                subprocess.Popen(["xdg-open", report_dir],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.query_one("#footer").update(f"  Opening report folder...  Q Quit")
            except Exception:
                try:
                    self.query_one("#footer").update(f"  Report: {self.result.report_path}  Q Quit")
                except Exception:
                    pass
        else:
            try:
                self.query_one("#footer").update("  No report to export.  Q Quit")
            except Exception:
                pass

    def _go_another(self) -> None:
        while len(self.app.screen_stack) > 2:
            try:
                self.app.pop_screen()
            except Exception:
                break

    def action_quit(self) -> None:
        self.app.exit()
