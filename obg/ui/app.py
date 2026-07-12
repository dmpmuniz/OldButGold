from __future__ import annotations
import os
import re
import subprocess
import sys
import time
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Button, Input, ProgressBar
from textual import work
from obg import __version__

from obg.core.detector import list_disks
from obg.core.engine import run_pipeline, STEPS as PIPELINE_STAGES
from obg.core.reporter import _format_duration as _format_eta
from obg.core.health import read_smart, run_short_test
from obg.core.session import find_session, complete_session
from obg.config import load_config, save_config, VALID_PROFILES, VALID_FILESYSTEMS
from obg.models.disk import DiskInfo
from obg.models.operation import StepStatus, OperationResult


class ObgApp(App):
    def __init__(self, test_mode: bool = False):
        super().__init__()
        self.test_mode = test_mode

    CSS = """
    Screen { background: #000000; align: center middle; }
    #app-frame { width: 100; height: 30; border: solid #444444; background: #0a0a0a; layout: vertical; }
    #header { dock: top; height: 1; background: #111111; color: #cccccc; border-bottom: solid #333333; padding: 0 1; }
    #body { height: 1fr; overflow-y: auto; }
    #footer { dock: bottom; height: 1; background: #111111; color: #666666; border-top: solid #333333; padding: 0 1; }
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
    .steps-col { width: 38%; min-width: 25; }
    .output-col { width: 62%; min-width: 30; }
    .panel-box { border: solid #333333; margin: 0 1; padding: 0 1; }
    .dialog-overlay { background: rgba(0,0,0,0.7); align: center middle; }
    .dialog-box { width: 50; min-width: 40; border: solid #333333; background: #111111; padding: 1; }
    .progress-info { color: #aaaaaa; }
    ProgressBar { margin: 0 2; }
    .startup-btn { width: 1fr; margin: 0 1; }
    .startup-btn.selected { background: #1a3a1a; border: solid #00ff00; }
    .metric-box { border: solid #333333; margin: 0 1 1 1; padding: 0 1; width: 1fr; }
    .metric-row { height: auto; }
    .metric-row > .metric-box { width: 1fr; }
    """

    def on_mount(self) -> None:
        sys.stdout.write("\x1b[8;30;100t")
        sys.stdout.flush()
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
            yield Static(f"OldButGold v{__version__}  |  HDD Revival Toolkit", id="header")
            with Container(id="body"):
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
            yield Static(f"OldButGold v{__version__}  |  Select Drive", id="header")
            with Container(id="body"):
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

    def _refresh(self) -> None:
        try:
            self._disks = list_disks()
        except Exception:
            self._disks = []
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
        session = find_session(disk)
        if session:
            self.app.push_screen(SessionDecisionScreen(disk, session))
        else:
            self.app.push_screen(SmartTestScreen(disk))


class SessionDecisionScreen(Screen):
    def __init__(self, disk: DiskInfo, session: dict) -> None:
        super().__init__()
        self.disk = disk
        self.session = session

    def compose(self) -> ComposeResult:
        total_blocks = self.disk.capacity_bytes // 4096 if self.disk.capacity_bytes else 1
        pct = min(99, int(self.session.get("badblocks_offset", 0) / total_blocks * 100))
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  |  Session Recovery", id="header")
            with Container(id="body"):
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
            self.app.push_screen(SmartTestScreen(self.disk, resume=True))

    def on_button_pressed(self, event) -> None:
        if event.button.id == "recover-btn":
            self.app.push_screen(SmartTestScreen(self.disk, resume=True))
        elif event.button.id == "restart-btn":
            complete_session(self.disk)
            self.app.push_screen(SmartTestScreen(self.disk))
        elif event.button.id == "details-btn":
            self.app.push_screen(DriveInfoScreen(self.disk, None))
        elif event.button.id == "back-btn":
            self.app.pop_screen()


class SmartTestScreen(Screen):
    def __init__(self, disk: DiskInfo, resume: bool = False) -> None:
        super().__init__()
        self.disk = disk
        self.resume = resume

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  |  SMART Short Self-Test", id="header")
            with Container(id="body"):
                yield Static("  Running SMART Short Self-Test...", classes="group-title")
                yield Static("", classes="config-group")
                yield Static(f"  Device: {self.disk.device}", classes="config-group")
                yield Static(f"  Model:  {self.disk.model}", classes="config-group")
                yield Static(f"  Serial: {self.disk.serial}", classes="config-group")
                yield Static("", classes="config-group")
                yield Static("  This may take up to 2 minutes.", id="test-status", classes="config-group")
            yield Static("  Please wait...", id="footer")

    def on_mount(self) -> None:
        self._run_test()

    @work(thread=True)
    def _run_test(self) -> None:
        try:
            self.app.call_from_thread(self._set_status, "  Running short test...")
            run_short_test(self.disk.device, on_output=lambda msg: self.app.call_from_thread(self._set_status, f"  {msg}"))
            self.app.call_from_thread(self._set_status, "  Collecting SMART data...")
            sd = read_smart(self.disk.device)
            self.app.call_from_thread(self._done, sd)
        except Exception as e:
            self.app.call_from_thread(self._set_status, f"  SMART Short failed: {e}")
            self.app.call_from_thread(self._done, None)

    def _set_status(self, msg: str) -> None:
        try:
            self.query_one("#test-status").update(msg)
        except Exception:
            pass

    def _done(self, smart_data) -> None:
        self.app.push_screen(DriveInfoScreen(self.disk, smart_data, resume=self.resume))


class DriveInfoScreen(Screen):
    def __init__(self, disk: DiskInfo, smart_data=None, resume: bool = False) -> None:
        super().__init__()
        self.disk = disk
        self._smart_data = smart_data
        self.resume = resume

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  |  {self.disk.model}", id="header")
            with Container(id="body"):
                with Horizontal():
                    with VerticalScroll(classes="panel-box"):
                        yield Static("  Device Information", classes="group-title")
                        yield Static(f"  Model:  {self.disk.model}")
                        yield Static(f"  Serial: {self.disk.serial}")
                        yield Static(f"  Firmware: {self.disk.firmware}")
                        yield Static(f"  Capacity: {self.disk.capacity_human}")
                    with VerticalScroll(classes="panel-box"):
                        yield Static("  Configuration", classes="group-title")
                        yield Static(f"  Interface: {self.disk.transport}")
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
                        yield Static(f"  RPM: N/A")
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
                    f"  Temp: {sd.temperature or 'N/A'}C\n"
                    f"  Power-on: {sd.power_on_hours or 'N/A'} h\n"
                    f"  Reallocated: {sd.reallocated_sectors}\n"
                    f"  Pending: {sd.pending_sectors}\n"
                    f"  Uncorrectable: {sd.uncorrectable_sectors}"
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
        self._profile_idx = next((i for i, p in enumerate(VALID_PROFILES) if p == self.config["profile"]), 0)
        self._fs_idx = self.FS_OPTIONS.index(self.config["filesystem"]) if self.config["filesystem"] in self.FS_OPTIONS else 0

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  |  Configuration", id="header")
            with Container(id="body"):
                yield Static("  Validation Profile", classes="group-title")
                for p in self.PROFILES:
                    marker = "(*)" if p.lower() == self.PROFILES[self._profile_idx].lower() else "( )"
                    yield Static(f"  {marker} {p}", id=f"prof-{p.lower()}", classes="config-group")
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
            yield Static(f"OldButGold v{__version__}  |  Confirm", id="header")
            with Container(id="body"):
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


    STEP_DESCRIPTIONS = {
        "Drive Identification": "Verifying device identity and accessibility...\nChecking that the expected drive is present and reachable.",
        "Initial Health Check": "Running SMART short self-test...\nThe drive firmware performs an internal diagnostic scan.\nEstimated duration: up to 2 minutes.",
        "Surface Validation": "Scanning the entire disk surface for bad sectors.\nThis is the longest step and may take hours depending on disk size and speed.",
        "Final Health Check": "Re-reading SMART attributes after surface validation...\nChecking for any changes in drive health metrics.",
        "Compare Results": "Comparing SMART snapshots taken before and after validation...\nDetecting changes caused by the validation process.",
        "Prepare Disk": "Creating a new GPT partition table...",
        "Create Partition": "Creating a primary partition spanning the full disk capacity...",
        "Format Filesystem": "Formatting the partition with the selected filesystem...",
        "Generate Report": "Compiling validation data and generating the final report...",
        "Session Cleanup": "Cleaning up temporary session data...",
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
            yield Static(f"OldButGold v{__version__}  |  Validating{mode}", id="header")
            with Container(id="body"):
                with Horizontal():
                    with VerticalScroll(classes="steps-col"):
                        yield Static("  Pipeline", classes="group-title")
                        for s in PIPELINE_STAGES:
                            w = Static(f"  [ ]  {s}", classes="step-pending")
                            self._step_widgets[s] = w
                            yield w
                    with VerticalScroll(classes="output-col"):
                        yield Static("  Progress", classes="group-title")
                        yield ProgressBar(total=100, id="bb-progress", show_eta=False)
                        yield Static("", id="progress-info", classes="progress-info")
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
        desc = self.STEP_DESCRIPTIONS.get(name, name)
        self._bb_operation = name
        self._bb_progress = 0
        self._bb_eta = ""
        self._bb_speed = 0
        self._bb_errors = (0, 0, 0)
        try:
            self.query_one("#bb-progress", ProgressBar).update(progress=0)
            self.query_one("#progress-info").update(f"  {desc}")
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
        if "read-only verification pass" in line:
            self._bb_operation = "Reading (non-destructive)"
            self._bb_pattern = "—"
            self._update_progress()
            return
        if line.startswith("Compare Results:"):
            self._bb_operation = "Compare Results"
            self._bb_progress = 100
            self._update_progress()
            try:
                self.query_one("#progress-info").update(line.replace("Compare Results:\n", "  ").replace("\n", "\n  "))
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
        pm = re.search(r'(?:Testing with pattern (\S+):\s+)?([\d.]+)% done,\s+([\d:]+) elapsed', line)
        if pm:
            pat = pm.group(1)
            if pat:
                self._bb_pattern = pat
                self._bb_operation = f"Writing pattern {pat}"
            elif self._bb_operation in ("Preparing...", "SMART Short Self-Test", "Reading (non-destructive)"):
                self._bb_operation = "Writing (destructive)"
            now = time.monotonic()
            pct = float(pm.group(2))
            self._bb_progress = pct
            self._bb_elapsed_str = pm.group(3)
            em = re.search(r'\((\d+)/(\d+)/(\d+)\s*errors?\)', line)
            if em:
                self._bb_errors = (int(em.group(1)), int(em.group(2)), int(em.group(3)))
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
        total = self._bb_total_blocks
        cur_block = int(total * pct / 100) if total > 0 else 0
        cur_sector = cur_block * (self._bb_blocksize // 512)
        r, w, c = self._bb_errors
        hdr = "  [TEST MODE]" if self._bb_test_mode else ""
        is_badblocks = any(kw in self._bb_operation for kw in ("Writing", "Reading", "pattern"))
        lines = [f"  {self._bb_operation}{hdr}"]
        if is_badblocks:
            lines += [
                f"  Pattern:   {self._bb_pattern}",
                f"  Progress:  {pct:.1f}%",
                f"  Block:     {cur_block:,} / {total:,}",
                f"  Sector:    {cur_sector:,}",
                f"  Speed:     {self._bb_speed:.1f} MB/s" if self._bb_speed > 0 else "  Speed:     —",
                f"  Elapsed:   {self._bb_elapsed_str}",
                f"  ETA:       {self._bb_eta}" if self._bb_eta else "  ETA:       —",
                f"  Bad:       Found {self._bb_bad_count:,}" if self._bb_bad_count > 0 else f"  Bad:       {self._bb_bad_count}",
                f"  Errors:    {r}/{w}/{c} (R/W/C)" if r > 0 or w > 0 or c > 0 else None,
            ]
        elif pct > 0:
            lines.append(f"  Progress:  {pct:.0f}%")
        desc = self.STEP_DESCRIPTIONS.get(self._bb_operation, "")
        if desc:
            lines.append(f"")
            lines.append(f"  {desc}")
        info = "\n".join(l for l in lines if l is not None)
        try:
            self.query_one("#progress-info").update(info)
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
            self.app.call_from_thread(self._complete, result)
        except Exception as e:
            self.app.call_from_thread(self._on_output, f"ERROR: {e}")
            self.app.call_from_thread(self._complete, None)

    def _complete(self, result) -> None:
        self._done = True
        try:
            self.app.push_screen(CompleteScreen(self.disk, self.config, result))
        except Exception:
            pass


class CompleteScreen(Screen):
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, disk: DiskInfo, config: dict, result: OperationResult | None) -> None:
        super().__init__()
        self.disk = disk
        self.config = config
        self.result = result
        self._report_exported = False

    def compose(self) -> ComposeResult:
        with Container(id="app-frame"):
            yield Static(f"OldButGold v{__version__}  |  Validation Complete", id="header")
            with Container(id="body"):
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
                    yield Static(f"  SMART Before:  {sb.overall_health if sb else 'N/A'}")
                    yield Static(f"  SMART After:   {sa.overall_health if sa else 'N/A'}")
                    yield Static(f"  Bad Blocks:    {r.snapshot.badblocks_count}")
                    yield Static("")
                    for reason in r.classification.reasons:
                        yield Static(f"  - {reason}")
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
        while len(self.app.screen_stack) > 1:
            try:
                self.app.pop_screen()
            except Exception:
                break

    def action_quit(self) -> None:
        self.app.exit()
