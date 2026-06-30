from __future__ import annotations
import time
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Button, Input
from textual import work
from obg import __version__
from obg.utils import logger
from obg.core.detector import list_disks
from obg.core.engine import run_pipeline
from obg.core.health import read_smart, run_short_test
from obg.config import load_config, save_config
from obg.models.disk import DiskInfo
from obg.models.operation import StepStatus, OperationResult


class ObgApp(App):
    def __init__(self, test_mode: bool = False):
        super().__init__()
        self.test_mode = test_mode

    CSS = """
    Screen { background: #0a0a0a; color: #cccccc; }
    .header { dock: top; padding: 0 1; background: #111111; color: #cccccc; border-bottom: solid #333333; }
    .footer { dock: bottom; padding: 0 1; background: #111111; color: #666666; border-top: solid #333333; }
    .card { border: solid #333333; margin: 0 1; padding: 0 1; }
    .card-selected { border: solid #1a1a2e; margin: 0 1; padding: 0 1; background: #1a1a2e; }
    .card:hover { background: #1a1a2e; }
    .card-disabled { border: solid #333333; margin: 0 1; padding: 0 1; color: #555555; }
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
    """

    def on_mount(self) -> None:
        self.push_screen(StartupScreen())


class StartupScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Static(f"OldButGold v{__version__}  |  HDD Revival Toolkit", classes="header")
        with VerticalScroll():
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
            Button(" Continue ", id="continue-btn", variant="default", disabled=True),
            Button(" Exit ", id="exit-btn", variant="error"),
            classes="btn-row",
        )
        yield Static("  Initializing...  Esc Exit", classes="footer")

    def on_mount(self) -> None:
        self._init()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.exit()

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
            self.query_one(".footer").update("  Enter Continue   Esc Exit")
        except Exception:
            pass

    def _init_error(self, msg: str) -> None:
        try:
            self.query_one("#init-status").update(f"  Error: {msg}")
        except Exception:
            pass


class DriveSelectionScreen(Screen):
    BINDINGS = [("r", "refresh", "Refresh"), ("q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self._disks: list[DiskInfo] = []
        self._selected = 0

    def compose(self) -> ComposeResult:
        yield Static(f"OldButGold v{__version__}  |  Select Drive", classes="header")
        yield VerticalScroll(id="disk-list")
        yield Static("  Up/Down Select   Enter Confirm   R Refresh   Esc Back   Q Quit", classes="footer")

    def on_mount(self) -> None:
        self._refresh()

    def action_refresh(self) -> None:
        self._refresh()

    def action_quit(self) -> None:
        self.app.exit()

    def _refresh(self) -> None:
        try:
            self._disks = list_disks()
        except Exception:
            self._disks = []
        self._selected = 0
        self._rebuild()

    def _rebuild(self) -> None:
        container = self.query_one("#disk-list")
        container.remove_children()
        if not self._disks:
            container.mount(Static("No drives detected. Press R to refresh.", classes="empty-msg"))
            return
        for i, disk in enumerate(self._disks):
            if disk.is_supported:
                selected = i == self._selected
                css = "card-selected" if selected else "card"
                sel_arrow = " >" if selected else "  "
                lines = [
                    f"{sel_arrow} {disk.model}",
                    f"   {disk.device}  {disk.transport}  {disk.capacity_human}",
                ]
                widget = Static("\n".join(lines), classes=css)
            else:
                reason = "SSD / Unsupported" if not disk.is_supported else ""
                lines = [
                    f"   {disk.model}",
                    f"   {disk.device}  {disk.capacity_human}  [Protected]  {reason}",
                ]
                widget = Static("\n".join(lines), classes="card-disabled")
            widget.idx = i
            container.mount(widget)

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
        self.app.push_screen(DriveInfoScreen(disk))


class DriveInfoScreen(Screen):
    def __init__(self, disk: DiskInfo) -> None:
        super().__init__()
        self.disk = disk
        self._smart_data = None

    def compose(self) -> ComposeResult:
        yield Static(f"OldButGold v{__version__}  |  {self.disk.model}", classes="header")
        with VerticalScroll():
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
                    yield Static(f"  RPM: {self.disk.rpm or 'N/A'}")
        yield Static("  Esc Back   Enter Continue", classes="footer")

    def on_mount(self) -> None:
        self._fetch_smart()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "enter":
            self.app.push_screen(ValidationConfigScreen(self.disk))

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

    def __init__(self, disk: DiskInfo) -> None:
        super().__init__()
        self.disk = disk
        self.config = load_config()
        self.FS_OPTIONS = ["ext4", "ntfs", "exfat", "fat32"]
        self.PROFILES = ["Recommended", "Extended"]
        self._profile_idx = 0 if self.config["profile"] == "recommended" else 1
        self._fs_idx = self.FS_OPTIONS.index(self.config["filesystem"]) if self.config["filesystem"] in self.FS_OPTIONS else 0

    def compose(self) -> ComposeResult:
        yield Static(f"OldButGold v{__version__}  |  Configuration", classes="header")
        with VerticalScroll():
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
            yield Static("", classes="config-group")
            yield Horizontal(
                Button(" Back ", id="back-btn"),
                Button(" Continue ", id="continue-btn"),
                classes="btn-row",
            )
        yield Static("  Esc Back   Enter Continue", classes="footer")

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
            self._profile_idx = 0 if p == "recommended" else 1
            self._update_labels()
        elif cid and cid.startswith("fs-"):
            f = cid[3:]
            if f in self.FS_OPTIONS:
                self._fs_idx = self.FS_OPTIONS.index(f)
                self._update_labels()

    def _move(self, direction: int, axis: int) -> None:
        if axis == 1:
            if direction > 0:
                self._profile_idx = (self._profile_idx + 1) % 2
            else:
                self._profile_idx = (self._profile_idx - 1) % 2
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
        self.app.push_screen(FinalConfirmationScreen(self.disk, self.config))


class FinalConfirmationScreen(Screen):
    def __init__(self, disk: DiskInfo, config: dict) -> None:
        super().__init__()
        self.disk = disk
        self.config = config

    def compose(self) -> ComposeResult:
        yield Static(f"OldButGold v{__version__}  |  Confirm", classes="header")
        with VerticalScroll():
            yield Static("  Validation Summary", classes="group-title")
            yield Static(f"  Drive:  {self.disk.model}")
            yield Static(f"  Serial: {self.disk.serial}")
            yield Static(f"  Capacity: {self.disk.capacity_human}")
            yield Static("")
            yield Static(f"  Profile:     {self.config['profile'].title()}")
            yield Static(f"  Filesystem:  {self.config['filesystem']}")
            yield Static(f"  Label:       {self.config.get('label', '(none)') or '(none)'}")
            yield Static("")
            yield Static("  !  ALL EXISTING DATA WILL BE", classes="warning")
            yield Static("  !  PERMANENTLY DESTROYED.", classes="warning")
            yield Static("", classes="config-group")
            yield Horizontal(
                Button(" Back ", id="back-btn"),
                Button(" Start Validation ", id="start-btn"),
                classes="btn-row",
            )
        yield Static("  Esc Back   Enter Start", classes="footer")

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
        self.app.push_screen(ExecutionScreen(self.disk, self.config))


class ExecutionScreen(Screen):
    def __init__(self, disk: DiskInfo, config: dict) -> None:
        super().__init__()
        self.disk = disk
        self.config = config
        self._step_widgets: dict[str, Static] = {}
        self._output_lines: list[str] = []
        self._start_time = time.monotonic()
        self._cancelled = False
        self._done = False

    PIPELINE_STAGES = [
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

    def compose(self) -> ComposeResult:
        mode = "  [TEST MODE]" if self.app.test_mode else ""
        yield Static(f"OldButGold v{__version__}  |  Validating {self.disk.device}{mode}", classes="header")
        with Horizontal():
            with VerticalScroll(classes="steps-col"):
                yield Static("  Pipeline", classes="group-title")
                for s in self.PIPELINE_STAGES:
                    w = Static(f"  [ ]  {s}", classes="step-pending")
                    self._step_widgets[s] = w
                    yield w
            with VerticalScroll(classes="output-col"):
                yield Static("  Output", classes="group-title")
                yield Static("", id="live-output")
        yield Static("  [C] Cancel  Elapsed: 00:00:00", classes="footer")

    def on_mount(self) -> None:
        self.set_interval(1.0, self._tick)
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
            self.query_one(".footer").update(f"  [C] Cancel  Elapsed: {h:02d}:{m:02d}:{s:02d}")
        except Exception:
            pass

    def _on_step(self, name: str, status: StepStatus) -> None:
        self.app.call_from_thread(self._update_step, name, status)

    def _update_step(self, name: str, status: StepStatus) -> None:
        icons = {
            StepStatus.RUNNING: ("[>]", "step-running"),
            StepStatus.OK: ("[x]", "step-ok"),
            StepStatus.FAILED: ("[!]", "step-failed"),
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

    def _on_output(self, line: str) -> None:
        self.app.call_from_thread(self._append, line)

    def _append(self, line: str) -> None:
        self._output_lines.append(line)
        if len(self._output_lines) > 200:
            self._output_lines = self._output_lines[-200:]
        try:
            self.query_one("#live-output").update("\n".join(self._output_lines[-20:]))
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
                on_step=self._on_step,
                on_output=self._on_output,
                is_cancelled=lambda: self._cancelled,
                test_mode=self.app.test_mode,
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
        yield Static(f"OldButGold v{__version__}  |  Validation Complete", classes="header")
        with VerticalScroll():
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
            yield Static("", classes="config-group")
            yield Horizontal(
                Button(" Validate Another Drive ", id="another-btn"),
                Button(" Quit ", id="quit-btn"),
                classes="btn-row",
            )
        yield Static("  Enter Another   Q Quit", classes="footer")

    def on_key(self, event) -> None:
        if event.key == "enter":
            self._go_another()
        elif event.key == "q":
            self.app.exit()

    def on_button_pressed(self, event) -> None:
        if event.button.id == "another-btn":
            self._go_another()
        elif event.button.id == "quit-btn":
            self.app.exit()

    def _go_another(self) -> None:
        while len(self.app.screen_stack) > 1:
            try:
                self.app.pop_screen()
            except Exception:
                break

    def action_quit(self) -> None:
        self.app.exit()
