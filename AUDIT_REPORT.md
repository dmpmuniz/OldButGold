# OldButGold — Deep Code Audit

**Project:** OldButGold v0.7.2 (Textual TUI disk validation tool)
**Audit scope:** all `obg/` source, `scripts/`, `obg.spec`, `docs/` (14 specs), runtime bundle (`tools/`, `lib/`, `release/`)
**Date:** 2026-07-17
**Method:** full line-by-line read of `app.py` (980 lines) + all core modules, all 14 docs, static + dynamic verification (import, frozen-binary launch, tool resolution, bundled-lib check, test suite run).

---

## 1. Executive Summary

Top 5 most likely reasons "the app isn't working" (concrete, with citations):

1. **Destructive validation cannot be tested/observed without root + real disks, and the "Test Mode" path still runs the real destructive `badblocks -w` on ~1% of the disk** (`scanner.py:23`, `scanner.py:39`). There is no sandbox; on a dev box the app will silently wipe 1% of whatever disk is selected. In source mode it also fails immediately because it needs root (and `pkexec` is only wired into the frozen entry point, not `python -m obg`). This is the #1 reason a developer sees "nothing happens / it dies": `acquire_lock` then `badblocks` raise `PermissionError`/`RuntimeError` that get swallowed by the try/except in `ExecutionScreen._run` (`app.py:872-874`) and the screen just advances to Complete with `result=None`.

2. **The bundled `lib/` directory is non-functional and non-compliant** — there is **no `ld-linux` loader in `lib/`** (`ls lib/ | grep ld` → empty). `LD_LIBRARY_PATH` only affects an already-loaded dynamic linker, so the bundled `libc.so.6`/friends are never actually used by the bundled tools; they run against the host loader. On any host whose glibc differs from the bundled 2.43 this breaks entirely (violates TOOLCHAIN §5, §9, §14). On this exact host it happens to work only because host glibc == bundled glibc.

3. **`read_smart()` returns `None` whenever `smartctl` exits non-zero for any reason** (`health.py:41-44`), including permission errors and the case where the bundled smartctl needs a different privilege path. In source mode (not via `pkexec`) `smartctl -a` fails with rc=4 (open failed) → `None`. Downstream this forces classification to `FAILED` ("Final SMART data unavailable") even when the drive is healthy, so **every validation classifies as FAILED** (`classifier.py:14-15`).

4. **Source-mode execution is broken by design.** Running `python -m obg` (the documented `obg` console script / dev path) never escalates privileges — `pkexec`/terminal re-exec logic lives only in `__main__.main()` *after* `from obg.ui.app import ObgApp`, but the `os.execvp` re-launch uses `binary = sys.argv[0]` which, for `-m obg`, is the `-c` shim; and more importantly the whole privilege block is skipped unless `euid != 0`. So a developer testing from source gets no root, no tools-resolved-properly at runtime, and an instant failure cascade that is invisible (swallowed).

5. **`on_mount` writes a terminal resize escape `\x1b[8;30;100t` directly to `sys.stdout`** (`app.py:72`) *inside* Textual's TUI. Textual has already taken over the terminal; writing raw bytes to stdout can corrupt/desync the screen on some terminals, and the `\x1b[8;...t` sequence is a *request* to the terminal (not all terminals honor it). The same write is duplicated in `__main__.py:54`. This is cosmetic on most terminals but can cause a blank/garbled first frame.

**Bottom line:** the app launches and shows the Startup screen (verified: frozen binary renders the disclaimer, `--version` works, all 68 unit tests pass). The "isn't working" symptom is almost certainly the **destructive validation pipeline failing silently in source/privilege-less mode and then classifying everything FAILED**, combined with the non-functional bundled `lib/` making the "self-contained bundle" claim false.

---

## 2. Runtime / Startup Analysis

**Can the app start?** Yes — verified:
- `./dist/OldButGold --version` → `OldButGold v0.7.2` (exit 0).
- `./dist/OldButGold` renders the Startup screen (captured raw escape output; frame, disclaimer, Continue/Exit buttons present).
- `from obg.ui.app import ObgApp` imports cleanly in the venv (textual 8.2.8).

**Startup path trace:**
1. `obg/__main__.py:main()` → `logger.setup()` (writes `obg_<ts>.log` to **CWD**, not the documented `~/.cache/obg`).
2. If `euid != 0`: tries to find a terminal emulator and `os.execvp("pkexec", …)` (`:32-49`). **Frozen binary only** works this way. For `python -m obg` the re-exec target is wrong (`sys.argv[0]` is the `-c`/`-m` shim).
3. Writes `\x1b[8;30;100t` to stdout (`:54`) — see issue #5 above.
4. `ObgApp(test_mode=...).run()` → `ObgApp.on_mount` (`:71`) writes the same resize escape again and `push_screen(StartupScreen())`.

**Resize escape:** `\x1b[8;30;100t` = "set text-area size to 30 rows × 100 cols" *request*. Double-written (app.py:72 and __main__.py:54). Even if honored, the CSS frame is `max-width:120; max-height:40` (`app.py:32`), which contradicts AGENT_RULES.md (documents "fixed layout 100×30", `#app-frame { width:100; height:30 }`). The CSS does **not** fix the size to 100×30 — it only caps it. On a smaller terminal the `align: center middle` frame floats and the disclaimer text (which is laid out for 100 cols) wraps/overflows.

**Frozen binary vs `tools/`/`lib/`:**
- `_tool_dir()` (`runner.py:21-27`): when `sys.frozen`, returns `Path(sys.executable).parent` (the release dir). `release/OldButGold-v0.7.2/` contains `tools/`, `lib/`, etc. → tool resolution works (verified: `smartctl` → `…/tools/smartctl`).
- `lib/` is present but **lacks `ld-linux-x86-64.so.2`** → `LD_LIBRARY_PATH` set in `_build_env()` (`:47-54`) is **ineffective** for choosing the bundled libc. Bundled tools load the host loader → host libs. Functional *here* only because host glibc == bundled glibc (both 2.43). Not portable.

**Does the frozen binary actually launch?** Yes (see above). It is viable on this machine; the bundle is not self-contained elsewhere.

---

## 3. Screen-by-Screen Audit

### StartupScreen (`app.py:77-175`)
- Shows: header, disclaimer, init status, Continue (disabled) / Exit buttons.
- `_init` runs `list_disks()` in a thread (`app.py:155-161`); on success enables Continue. **Data populated** when disks detected.
- Risk: if `list_disks()` raises, `_init_error` shows it — good. But `list_disks()` runs `smartctl -i` per disk (`detector.py:53-64`); under source/non-root this prints rc!=0 → `_check_smart` returns False (fine, not a crash). No crash risk.
- `BINDINGS` use `Binding(...)` with `priority=True` — matches AGENT_RULES.md note (tuple form would `SyntaxError`). OK.

### DriveSelectionScreen (`app.py:178-282`)
- Shows: one card per disk with model/device/transport/capacity; warning if mounted/boot; "Interrupted Validation - X%" if a session exists.
- Rebuilds cards on refresh/select. **Data populated** from `list_disks()`.
- `on_key` up/down clamps with `min(len-1, …)`; if `len(self._disks)==0`, `max(0,-1)=0` and `_rebuild` already guarded. OK.
- `on_click` uses `event.widget.idx` — works because `widget.idx = i` is monkey-patched (`:240`). Fragile but functional.
- Risk: `find_session(disk)` requires fingerprint match incl. `capacity_bytes`; fine.
- No crash risk identified.

### SessionDecisionScreen (`app.py:285-332`)
- Shows model/serial/capacity/stage/completed%/started. Buttons Recover/Restart/View Details/Back.
- Spec UI §9 wants buttons "Recover Validation / Restart Validation / View Session Details / Back" — code labels them "Recover/Restart/View Details/Back" (acceptable).
- `on_key` Enter → `SmartTestScreen(self.disk, resume=True)`. OK.
- `restart-btn` calls `complete_session(self.disk)` then `SmartTestScreen(self.disk)` (new validation) — correct per spec §10.
- No crash risk.

### SmartTestScreen (`app.py:335-374`)
- Shows "Collecting SMART data…", runs `read_smart(device)` in a thread, pushes to DriveInfoScreen.
- **Major silent-failure path:** if `read_smart` returns `None` (common in non-root/source mode, see §6), it still proceeds to DriveInfoScreen with `smart_data=None`, which then re-fetches and also gets None → shows "SMART not available". Validation continues and later **classifies FAILED**. No crash, but a correctness/UX failure.

### DriveInfoScreen (`app.py:377-460`)
- Four-panel layout: Device Info | Configuration on row 1; SMART | Geometry on row 2. **Matches UI §10 four-panel requirement.**
- Accesses `disk.firmware`, `disk.current_fs or 'None'`, `disk.partition_table or 'None'`, `disk.logical_sector`, `disk.physical_sector` — all exist on `DiskInfo`.
- `_update_smart` reads `sd.overall_health`, `sd.temperature`, `sd.power_on_hours`, `sd.reallocated_sectors`, `sd.pending_sectors`, `sd.uncorrectable_sectors` — all exist on `SmartData`.
- "RPM: N/A" is a hardcoded literal — fine.
- `on_key` Enter → `ValidationConfigScreen`; Esc → pops until stack ≤ 2 (skips SmartTestScreen, per AGENT_RULES.md). OK.
- No crash risk (guarded `try/except` around SMART update).

### ValidationConfigScreen (`app.py:463-567`)
- Shows profile radio list (Recommended/Extended), filesystem list (ext4/ntfs/exfat/fat32), label Input.
- Keyboard nav: up/down → profile, left/right → filesystem, Enter → continue; all gated by `not isinstance(self.focused, Input)` (`:504-513`).
- `_fs_idx` lookup: `self.FS_OPTIONS.index(self.config["filesystem"])` — `config["filesystem"]` is always valid (load_config clamps). OK.
- `on_click` parses `prof-`/`fs-` ids; `cid[5:]` for prof and `cid[3:]` for fs — but profile ids are `prof-recommended`/`prof-extended` → `cid[5:]` = "recommended"/"extended" (correct); fs ids `fs-ext4` → `cid[3:]` = "ext4" (correct).
- **Spec compliance:** only 2 profiles + 4 filesystems + optional label shown (E-001/E-002/E-003). OK.
- No crash risk.

### FinalConfirmationScreen (`app.py:570-617`)
- Shows drive/serial/capacity/profile/filesystem/label + destructive warning.
- `self.config['profile'].title()` — `config['profile']` is always a valid key (load clamps). OK.
- Warning shown whether mounted or not (spec F-001). OK.
- No crash risk.

### ExecutionScreen (`app.py:621-881`)
- Shows 10-step pipeline (left), ProgressBar + progress-info + live-output (right), footer elapsed/cancel.
- `compose()` builds `self._step_widgets` by iterating `PIPELINE_STAGES` (imported as `STEPS` from engine — correct, 10 stages).
- **`on_mount` writes resize escape AGAIN?** No, only `ObgApp.on_mount` does. OK here.
- `_run` calls `run_pipeline(...)` with `on_step=self._on_step`, `on_output=self._on_output`, `is_cancelled=lambda: self._cancelled`. The callbacks use `self.app.call_from_thread` — correct for thread→main thread.
- **Silent failure masking:** `except Exception as e: self.app.call_from_thread(self._on_output, f"ERROR: {e}"); self.app.call_from_thread(self._complete, None)` (`:872-874`). Any exception in the whole pipeline → CompleteScreen with `result=None`, no stack trace to user (only to log). This is exactly why the app "isn't working" but shows no obvious error: a privilege/tool failure is hidden and the run silently ends as "Pipeline failed or was cancelled."
- Progress parsing: badblocks `(xx.xx%) done, hh:mm:ss elapsed` matched; `bad blocks found` parsed; SMART `SMART test: N% complete` matched. Reasonable.
- Potential `KeyError`/`AttributeError`: none in the parsing path (all regex-group guarded).
- `TEST MODE`/`RESUME` branches handled. OK-ish.
- No guaranteed crash, but the swallow-the-exception design hides the real failure.

### CompleteScreen (`app.py:884-980`)
- If `result` truthy: reads `r.classification.classification.value`, `r.snapshot.smart_before/after`, `r.snapshot.badblocks_count`, `r.classification.reasons`, `r.total_duration_seconds`, `r.report_path`.
  - All attributes exist on `OperationResult`/`DiskSnapshot`/`ClassificationResult`. OK.
  - `cls_val = r.classification.classification.value`; `yield Static(f"  {cls_val}", classes=cls_val.lower())` — CSS has `.gold/.silver/.bronze/.failed` (app.py:50-53). `FAILED.value` = `"FAILED"` → `classes="failed"` ✓. `GOLD/SILVER/BRONZE` → lowercased ✓.
- If `result` None: "Pipeline failed or was cancelled." ✓.
- `_export_report` uses `xdg-open` — host dependency, but the report path is `$HOME/.local/share/oldbutgold/reports/...`, **not** the bundle `reports/` (spec §11 / PROJECT_STRUCTURE §11 says reports live in the distributed `reports/`). Mismatch (see §7).
- No crash risk.

---

## 4. Pipeline Audit (run_pipeline, engine.py)

Trace with per-step risk & output correctness:

| Step | Function | Runs? | Crash risk | Output correctness |
|------|----------|-------|-----------|--------------------|
| Drive Identification | `verify_identity` (`detector.py:145`) → `lsblk -o NAME,MODEL,SERIAL device -J` | Yes (fatal) | Needs root for raw device; non-root → rc!=0 → returns False → pipeline aborts with "Device identity mismatch" | OK if root |
| Initial Health Check | `run_short_test` + `read_smart` | Yes (non-fatal) | `run_short_test` runs `smartctl -t short` (needs root); non-root → rc not in (0,2) → returns False, but step still marked OK-ish | SMART before collected; **rc=4/permission → `read_smart` returns None** → `smart_before=None` |
| Surface Validation | `run_badblocks` (`scanner.py`) | Yes (fatal) | **DESTRUCTIVE `-w` even in Recommended profile**; needs root; non-root → PermissionError (swallowed) | badblocks count parsed; resume offset logic buggy (see below) |
| Final Health Check | `read_smart` | Yes (non-fatal) | same None issue | `smart_after` may be None |
| Compare Results | builds `SmartDelta` | Yes (non-fatal) | guarded by `if smart_before and smart_after` | deltas correct when both present |
| Prepare Disk | `create_gpt` (`sgdisk --zap-all`) | Yes (fatal) | needs root | OK if root |
| Create Partition | `create_partition` (`sgdisk -n ...` + `partprobe`) | Yes (fatal) | needs root | returns `${dev}1`/`${dev}p1` |
| Format Filesystem | `format_filesystem` (`mkfs.*`) | Yes (fatal) | label truncation handled; needs root | OK if root |
| Generate Report | `classify` + `generate_report` | Yes (non-fatal) | **If `smart_after is None` → classify returns FAILED** (`classifier.py:14`) | report written to `~/.local/share/.../reports` (not bundle) |
| Session Cleanup | `complete_session` | Yes | guarded | removes session json |

**Resume bug (`engine.py:119-138` + `session.py`):** On resume, `existing.get("current_stage","")` — but the session stage is always either `"Badblocks Validation"` (set at `:131`) or `"Post Validation"` (set at `:138`). On a real resume the stage is `"Post Validation"`, so `stage != "Badblocks Validation"` is True → `resume_offset = 0` (`:127-128`). **This means resume restarts badblocks from 0%, defeating the entire recovery feature** (violates MASTER §9, SESSION_RECOVERY §8 "resume slightly before last checkpoint").

**badblocks args (`scanner.py`):**
- Non-resume full run: `badblocks -w -s -v device` (no `-b`, no block range) — default 1024-byte blocks, whole disk. The progress parser expects `(xx.xx%) done` which badblocks `-s` emits. OK.
- test_mode: limits to ~1% via `-b 4096` + block count. Fine for a smoke test but **still destructive write** on that 1%.
- The "1%" heuristic `int(total_blocks * 0.01)` for a multi-TB disk is fine; `MARGIN_BLOCKS=100` safety margin is honored.

**smartctl parsing (`health.py`):** `_parse_attribute_table` splits on whitespace and takes `parts[0]` as attr id and `parts[-1]` as raw — standard `smartctl -A` layout. Temperature=194, POH=9, realloc=5, pending=197, uncorrect=198, crc=199. Correct for ATA. NVMe not handled (out of scope).

**partitioner/formatter:** correct invocations; `mkfs.ntfs` via `mkntfs` symlink present in `tools/`. OK.

---

## 5. Tool Resolution Audit (runner.py)

`_resolve_tool(name)` (`runner.py:30-44`):
- If frozen: looks for `exe_dir/tools/name`. If missing → raises `FileNotFoundError` ("must be executed from a complete distribution"). **This is the correct TOOLCHAIN §12/§20 behavior — it does NOT silently fall back to host binaries.** Good (and it matches PROJECT RULES §15 "silent fallbacks prohibited").
- If not frozen: `pkg_dir` = `obg/utils/../../` = repo root (`:24`). If `repo/tools` exists → uses it (verified: resolves `tools/smartctl`). Otherwise falls back to `shutil.which(name)` — **in source mode this WILL use a host-installed binary if `tools/` is absent**, which is the intended dev behavior.

`_build_env()` (`:47-54`): prepends `exe_dir/lib` to `LD_LIBRARY_PATH` only if `lib/` exists. **But without `ld-linux` in `lib/`, this env var never actually selects the bundled libc** (the kernel-invoked loader is fixed). So:
- On this host (glibc 2.43 == bundled): works via host loader.
- On any other glibc: bundled binaries fail to start (`version 'GLIBC_2.xx' not found`), and `_resolve_tool` wouldn't even raise because the file *exists* — the failure surfaces only at `subprocess` exec as a `FileNotFoundError`/bad-exec, which `run()` does not special-case → bubbles up and is swallowed by the ExecutionScreen try/except.

**Missing-tool simulation:** remove `tools/smartctl` from a frozen bundle → `_resolve_tool` raises `FileNotFoundError` → `run()` in `detector._check_smart` calls `run(["smartctl",...])` → raises → caught in `_check_smart`? No: `_check_smart` calls `run(...)` with no try/except, so the exception propagates to `list_disks()` → returns `[]` (only if caught) — actually `list_disks` calls `run(cmd)` first (`:91`) which would raise before reaching `_check_smart`. `list_disks` has **no try/except around the initial `run(cmd)`**, so a missing `lsblk` raises all the way to `StartupScreen._init` (caught → `_init_error`). Acceptable (shows error). But for `smartctl` specifically, `_check_smart` is called *inside* the loop per disk and **has no try/except** — if `lsblk` succeeds but `smartctl` is missing, `_check_smart` raises and `list_disks` returns `[]` abruptly (drives disappear). Minor robustness gap.

---

## 6. Data Model Audit (attributes accessed in app.py vs dataclasses)

Cross-checked every attribute read in `app.py` against `obg/models/`:

| Attribute used in app.py | Model | Exists? |
|--------------------------|-------|---------|
| `disk.model/.device/.transport/.capacity_human/.is_mounted/.is_boot_disk/.serial/.firmware/.current_fs/.partition_table/.logical_sector/.physical_sector/.capacity_bytes/.is_supported` | `DiskInfo` (`disk.py:7`) | ✅ all present |
| `disk.capacity_bytes // 4096` (`:233`, `:292`) | `DiskInfo` | ✅ |
| `session.get("badblocks_offset"/"current_stage"/"created_at")` | dict (session.py) | ✅ keys present |
| `smart_data.overall_health/.temperature/.power_on_hours/.reallocated_sectors/.pending_sectors/.uncorrectable_sectors` | `SmartData` (`disk.py:30`) | ✅ |
| `r.classification.classification.value`, `r.classification.reasons` | `ClassificationResult` (`classification.py`) | ✅ |
| `r.snapshot.smart_before/.smart_after/.badblocks_count` | `DiskSnapshot` (`disk.py:52`) | ✅ |
| `r.total_duration_seconds`, `r.report_path` | `OperationResult` (`operation.py`) | ✅ |

**No `AttributeError`/`KeyError` mismatch found in `app.py` against the dataclasses.** The data model is internally consistent (this is why the 68 unit tests pass). The real attribute-related failure is *runtime None* (`smart_before`/`smart_after` become `None` because `read_smart` returns `None`), which is handled by classifier (→ FAILED) but is a **behavior** bug, not a crash.

---

## 7. Documentation Compliance

### REPO STRUCTURE vs PROJECT STRUCTURE.md
- Doc §3 shows repo root containing `src/`; actual is `obg/`. Doc §5 explicitly acknowledges the `obg/` flat layout as valid ("This is a valid flat structure"). ✅ (doc is self-consistent).
- Doc §3 lists root items: `docs/ src/ tests/ scripts/ assets/ release/ README.md CHANGELOG.md LICENSE .gitignore pyproject.toml`. **Missing in repo:** `CHANGELOG.md` and `README.md` at root (RELEASE CHECKLIST requires README/CHANGELOG). `release.py` copies `README.md`/`LICENSE` if present but they don't exist → release omits them (release/OldButGold-v0.7.2 has no README/LICENSE). **Severity: Medium** (violates BUILD §7 "documentation exists", RELEASE CHECKLIST, AGENT_RULES "release must contain README/LICENSE").
- `build/` and `dist/` dirs exist in repo root (`:find` output) — PROJECT STRUCTURE §13 prohibits temp dirs (build/build2/...). `build/`/`dist/` are generated. **Severity: Low** (cleanliness).
- `assets/` exists but is empty (`.gitkeep` only). Spec allows empty assets. OK.

### Release directory (PROJECT STRUCTURE §10 / BUILD §3)
- `release/OldButGold-v0.7.2/` contains: `OldButGold`, `tools/` (14), `lib/` (19), `assets/`, `reports/`, `sessions/`. Doc §10 wants exactly those + `LICENSE` + `README.md`. **`tools/`=14 and `lib/`=19 match the doc's "14 tools / 19 libs" expectation.** ✅ counts correct. **Missing README/LICENSE** (Medium).
- `release/OldButGold-v0.7.2/` also contains a stray `obg_20260717_145739.log` (logger writes to CWD = release dir when run from there). AGENT_RULES says log goes to CWD by design, but it pollutes the release dir and `release.py` only excludes `*.log` from the **zip**, not from the dir. Minor.

### TOOLCHAIN SPECIFICATION
- §8 required tools: smartctl, badblocks, lsblk, blockdev, sgdisk, partprobe, mkfs.ext4, mkfs.ntfs, mkfs.exfat, mkfs.fat — **all 10 present** in `tools/`. ✅ (plus mke2fs/mkntfs real binaries + symlinks).
- §5/§9/§14 "execute only from `tools/`, libs from `lib/`, never host": **violated** — no `ld-linux` in `lib/`, so bundled libs are not actually used; tools run via host loader. **Severity: High** (self-containment claim false; breaks on divergent glibc).
- §12 "verify bundled executable exists / required libs exist / executable" — `_resolve_tool` checks existence+executable bit (`:34`) but **never checks `lib/` completeness** (no ld-linux check). **Severity: Medium**.
- §20 "never silently substitute host binaries" — source-mode `_resolve_tool` *does* fall back to `shutil.which` when `tools/` absent. This is intended for dev but is a documented divergence; acceptable with caveat.

### CLASSIFICATION SPECIFICATION vs classifier.py
- GOLD (doc §4): requires SMART short before+after success, no degradation, no bad blocks, FS created, uninterrupted. Code `is_gold` (`:32-42`) checks `overall_health=="PASSED"` both before/after, zero realloc/pending/uncorrect/bb, delta zero. **Mismatch:** spec says Gold requires "Filesystem successfully created" and "Validation completed without interruption" — code does **not** check FS creation success or interruption in `is_gold` (it only checks SMART + bb). A disk where formatting failed but SMART is clean would still be Gold. **Severity: Medium.**
- SILVER (doc §5): completed, no bad blocks, FS ok, non-critical SMART observations. Code `is_silver` (`:58-65`) checks PASSED + realloc≤5 + pending==0 + bb==0. Matches intent. ✅
- BRONZE (doc §6): completes but defects (bad blocks / SMART degradation). Code (`:78-93`) appends bronze reasons. ✅
- FAILED (doc §7): SMART fail / badblocks aborted / FS fail / unrecoverable. Code (`:13-29`) covers SMART-after-None, SMART FAILED, unknown health, uncorrectable>0. **Mismatch:** code does **NOT** fail on `bb`-driven abort or `filesystem creation failed` explicitly — those are caught by engine's `_run` fatal flag and produce `FAILED` via `_build_result`'s fallback (`:234-245`), which is acceptable. But "uncorrectable sectors > 0" forces FAILED even though doc §6 lists uncorrectable/pending as *Bronze* territory ("pending sectors and bad blocks are Bronze, not Failed" — see `classifier.py:22` comment). **Discrepancy with the in-code comment's own intent:** the comment says pending/bad are Bronze, yet `failed_reasons` triggers FAILED on `uncorrectable_sectors > 0`. Minor inconsistency. **Severity: Low/Medium.**
- Single classification only (doc §8): code returns exactly one. ✅

### REPORT SPECIFICATION vs reporter.py
- §5 sections 1–9 in exact order: Validation Summary, Device Identification, SMART Comparison, Validation Configuration, Badblocks Result, Filesystem Creation, Validation Timeline, Final Assessment, Legal Disclaimer. **reporter.py generates all 9 in this order** (`:45-167`). ✅
- §3 naming `OldButGold-YYYYMMDD-HHMMSS-<Model>.md`: code uses `strftime('%Y%m%d-%H%M%S')` + safe model (`:10`). ✅
- §11 "Filesystem Creation generated only when FS creation succeeds": reporter **always** emits §6 regardless of success (`:116-123`). **Severity: Low** (minor; spec says conditional).
- §18 disclaimer text: matches verbatim. ✅
- HTML prohibited (§17): report uses only markdown tables/headings. ✅
- **Location:** spec §11 + PROJECT STRUCTURE §11 say reports go in the distributed `reports/`. Code writes to `~/.local/share/oldbutgold/reports/` (`paths.py:11`). **Severity: Medium** (deviates from "self-contained, nothing outside app dir" — TOOLCHAIN §2/§3).
- §9 "Badblocks parameters" in Validation Configuration: report §4 prints Profile/Filesystem/Label/Duration but **not the actual badblocks parameters** (block size only in §5). Minor.

### SESSION RECOVERY SPECIFICATION vs session.py
- §2 session created automatically before Badblocks: `engine._surface` calls `create_session` (`:130`). ✅
- §3 id includes UUID + timestamp: `create_session` stores `session_id` (uuid) + `created_at`. ✅
- §4 fingerprint (model/serial/firmware/capacity/sector sizes): stored. ✅ `find_session` verifies all. ✅
- §5 checkpoint every 10%: `scanner._line_handler` buckets by 10% (`:51`). ✅
- §8 resume slightly before last checkpoint: **NOT honored** — see §4 resume bug (resume_offset reset to 0 when stage=="Post Validation"). **Severity: High** (recovery feature broken).
- §10 cleanup on success/restart/delete: `complete_session` on success (`:203`) and on Restart button (app.py:327). ✅
- §7 reject if fingerprint differs: `find_session` returns None → no session → normal flow. ✅

### UI GUIDELINES vs app.py
- §6 Startup: Continue disabled until init — ✅ (`app.py:166`).
- §7 Drive Selection: each drive its own block, selected highlighted (`.card-selected`), warning if mounted. ✅ But spec example shows "Protected" badge for SSD/NVMe; code shows unsupported disks as `[Unsupported]` card but they are *still rendered* and only non-selectable on Enter (`:276`). Mouse click on unsupported card: `on_click` sets `_selected` then `_select` which returns early (`:276-277`) — but it already changed selection highlight. Minor.
- §10 four-panel Drive Information: ✅ (verified).
- §13 Execution screen shows operation/throughput/ETA/processed: ✅ parsed.
- §14 Pipeline left side with ✓/▶/✗ and colors: ✅ (`step-ok/running/failed` classes, icons ▶✓✗ in `_update_step`).
- §16 Complete screen actions Export/Another/Exit: ✅.
- **Window size:** doc implies fixed 100×30; CSS uses `max-width:120; max-height:40` and `align:center middle` (app.py:32). Contradicts AGENT_RULES "frame width:100;height:30". **Severity: Low** (layout drift).
- §4 keys: ← → change option, ↑ ↓ move, Enter confirm, Esc return, R refresh, Tab/Space. App implements ↑↓/←→/Enter/Esc/R. **Tab/Space not bound** (Textual default focus handles Tab; Space not used for radio toggle). Minor.

### ACCEPTANCE TESTS — which would FAIL
- **A-001 (launch + bundled tools detected):** Passes launch; "bundled tools detected" is not surfaced to the user (no startup integrity check screen). Partial.
- **M-001 (self-contained, no host deps):** **FAILS** — bundled `lib/` has no loader; host libs used.
- **D-001/D-003/D-004 (SMART snapshots):** In non-root/source mode `read_smart` → None → snapshots missing → classify FAILED. **Fails under dev/test conditions.**
- **C-003/C-005 (recover only after fingerprint, deny wrong drive):** Recover logic present but **resume offset reset to 0** → recovery does not actually resume (C-003 partially fails functionally).
- **G-003 (real progress):** Parser uses real badblocks output. ✅
- **I-001/I-002 (markdown report accurate):** Generated; but report location is `~/.local`, not bundle `reports/`. Deviation.
- **K-004 (pipeline colors):** ✅.

---

## 8. Findings Table

| ID | Severity | File:Line | Issue | Fix |
|----|----------|-----------|-------|-----|
| F1 | Critical | `scanner.py:23,39` | Validation runs **destructive `badblocks -w`** even in "Test Mode" (only ~1% limited) and in Recommended profile; no non-destructive option. On a dev box this silently wipes part of a selected disk. | Add a true dry-run/non-destructive mode for testing; gate destructive runs behind an explicit test-mode flag that writes to a loopback file, not a real device. |
| F2 | High | `lib/` (release) | No `ld-linux` loader in bundled `lib/` → `LD_LIBRARY_PATH` (runner.py:47-54) is ineffective; bundled libs never used; bundle is NOT self-contained (TOOLCHAIN §5/§9/§14). | Bundle the matching `ld-linux-x86-64.so.2` and invoke tools via that loader (e.g. `$lib/ld-linux --library-path $lib $tool`), or use a patchelf'd rpath. Verify on a non-2.43 host. |
| F3 | High | `health.py:41-44` | `read_smart` returns `None` on **any** non-zero rc (incl. permission errors / rc=4). In source/non-root mode this is the norm → `smart_before`/`smart_after` become None → classifier forces FAILED for every run (classifier.py:14). | Distinguish "tool unavailable / no permission" from "device has no SMART"; surface the error instead of silently None; require root before pipeline. |
| F4 | High | `engine.py:119-138` | Resume recovery is broken: when session stage is `"Post Validation"` (the normal resumed state), `resume_offset` is forced to 0 → badblocks restarts from scratch, defeating recovery (MASTER §9, SESSION_RECOVERY §8). | Track a dedicated `resumable` flag / last checkpoint; resume from `badblocks_offset - margin` whenever a valid in-progress session exists, regardless of the free-text `current_stage`. |
| F5 | High | `app.py:856-874` | Whole pipeline exception is swallowed: `except Exception: _on_output("ERROR:…"); _complete(None)`. User sees "Pipeline failed or was cancelled" with no root cause → "app isn't working" with no diagnosable error on-screen. | Preserve and display the exception message + last step; write full traceback to the log; show a real error screen. |
| F6 | Medium | `__main__.py:32-49` | Privilege escalation only works for the frozen binary; `python -m obg` / `obg` console script re-exec target is wrong (`sys.argv[0]` is the `-m` shim) and devs never get root → silent pipeline failure. | Make the pkexec/terminal re-exec robust to `python -m` and `console_scripts` entry points; or document that dev run requires `sudo`. |
| F7 | Medium | `app.py:72` + `__main__.py:54` | Raw resize escape `\x1b[8;30;100t` written to `sys.stdout` while Textual owns the terminal; duplicated; some terminals ignore/garble it. CSS frame is `max-width:120;max-height:40`, not the documented fixed 100×30. | Use Textual's own size handling or set the size once; align CSS (`width:100;height:30`) with AGENT_RULES. |
| F8 | Medium | `reporter.py:11` + `paths.py:11` | Reports written to `~/.local/share/oldbutgold/reports`, not the bundle `reports/` dir required by PROJECT STRUCTURE §11 / TOOLCHAIN §2-3. | Write to `<app_dir>/reports/` (resolve via `_tool_dir()`/frozen path) so the app stays self-contained. |
| F9 | Medium | `classifier.py:32-42` | GOLD does not verify filesystem-creation success or "uninterrupted" (spec §4); a disk whose format failed but SMART is clean is still classified GOLD. | Add FS-success and non-interruption checks to `is_gold`. |
| F10 | Medium | `release.py:71-77` | Release omits `README.md`/`LICENSE` because they don't exist at repo root (BUILD §7, RELEASE CHECKLIST, AGENT_RULES). | Add `README.md` and `LICENSE` to repo root; `release.py` already copies them if present. |
| F11 | Medium | `detector.py:53-64` | `_check_smart` calls `run(["smartctl",...])` with no try/except; a missing/failing smartctl raises and aborts `list_disks()` mid-loop (drives vanish). | Wrap `_check_smart` in try/except; treat failure as "SMART unknown" rather than crashing enumeration. |
| F12 | Low | `classifier.py:20-21` | `uncorrectable_sectors > 0` forces FAILED, contradicting the file's own comment (`:22`) that pending/bad are Bronze, and contradicting CLASSIFICATION §6/§7 intent. | Reclassify uncorrectable as Bronze-level unless paired with hard failure; align with doc. |
| F13 | Low | `reporter.py:116-123` | "Filesystem Creation" section always emitted even when FS creation failed (spec §11 says only when successful). | Emit §6 only when `success` and FS step OK. |
| F14 | Low | `PROJECT STRUCTURE §13` | `build/` and `dist/` dirs committed in repo root (temp dirs). | Add to `.gitignore`; keep out of VCS. |
| F15 | Low | `release/OldButGold-v0.7.2/obg_*.log` | Logger writes to CWD; running from the release dir pollutes it with a `.log`. | Keep log in a temp/cache dir; exclude from release dir (already excluded from zip). |
| F16 | Low | `app.py:32` vs AGENT_RULES | CSS frame sizing drift from documented 100×30 fixed layout. | Align CSS with documented fixed dimensions. |

---

## 9. Prioritized Fix List (most → least critical for "the app to actually work")

1. **F5 — Stop swallowing pipeline exceptions.** Surface the real error on-screen (and full traceback in the log). Until this is fixed you cannot even see *why* it "isn't working." (Highest leverage diagnostic fix.)
2. **F3 — Make SMART/root failures visible and required.** `read_smart` returning `None` on permission errors, plus no root in source mode, is the most likely cause of "everything classifies FAILED / nothing validates." Require elevation before the pipeline and report tool errors instead of None.
3. **F1 — Add a safe, non-destructive test path.** The current "Test Mode" still destructively writes ~1% of a real device. A developer testing the app will damage a disk. Use a file-backed loop device or a pure non-destructive read pass for test mode.
4. **F2 — Fix the bundled `lib/` (add `ld-linux`, invoke via it).** Without this the "self-contained bundle" claim is false and the binary will not run on most other Linux distros — the actual shipped product is broken off this machine.
5. **F4 — Fix resume offset.** Recovery currently restarts from 0%, so the headline "session recovery" feature does not recover.
6. **F6 — Make privilege escalation work for `python -m obg` / console script**, or document that dev runs need `sudo`. Otherwise developers can never exercise the real pipeline.
7. **F9/F12 — Align classifier with CLASSIFICATION SPEC** (Gold requires FS success; uncorrectable → Bronze not FAILED).
8. **F8 — Write reports into the bundle `reports/`** to honor self-containment.
9. **F10/F14/F15 — Housekeeping:** add README/LICENSE, gitignore `build/`/`dist/`, stop polluting the release dir with logs.
10. **F7/F16 — Fix the duplicated resize-escape write and align the frame CSS with the documented 100×30.**

---

### Appendix — Verification performed
- Frozen binary launches & renders Startup screen (`--version` → 0.7.2; raw TUI capture OK).
- Source import `import obg.ui.app` → OK (venv textual 8.2.8).
- Tool resolution: frozen → `tools/`; source → `tools/` (repo root) ✅; missing tool → `FileNotFoundError` (correct, no host fallback when frozen).
- `lib/` has 19 libs but **no `ld-linux`**; host glibc == bundled glibc (2.43) so it runs here by luck.
- `pytest` → **68 passed** (unit + 1 integration). Tests pass because they mock tools; they do not exercise the real destructive pipeline or the bundled-lib gap.
- Badblocks progress regex verified against `(xx.xx%) done, hh:mm:ss elapsed`.
