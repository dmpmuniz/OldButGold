# Changelog

## v0.9.0

- TUI redesign: all 9 screens with consistent card/metric layout, SCREEN_SIZE fixed at 120x40
- ExecutionScreen: large ProgressBar + 3x3 metric cards + disk info panel + output log
- MainMenuScreen: DVD-blade box-drawing title, disclaimer in card
- CompleteScreen: card-organized sections
- ValidationConfigScreen: card-based selection instead of text markers
- DriveInfoScreen, SessionDecisionScreen, MountWarningScreen, FinalConfirmationScreen: card wrappers
- Relabeled "Steps" → "Validation Stages" on execution screen
- CSS: metric-card, startup-btn.selected, warning-box

## v0.8.1

- Fix badblocks validation profiles to match official documentation
- Recommended: `badblocks -wsv -b 4096 -t 0xaa -t 0x55 <device>` (2 patterns, 4K blocks)
- Extended: `badblocks -wsv <device>` (native 4 patterns, no -b, no -t)
- Remove Extended read-only verification pass
- Centralize command building in `scanner.get_profile_command()`
- Add profile descriptions to configuration screen
- Update test to match correct Extended profile command

## v0.7.7 (unreleased)

- Fix runner.py: bundled `lib/` path leaking into `LD_LIBRARY_PATH` during source-mode execution, causing system commands to fail with symbol lookup errors.

## v0.7.6

- Real SMART metrics on CompleteScreen
- SMART Short Self-Test moved pre-pipeline (SmartTestScreen)
- Fix pipeline header label

## v0.7.5

- Fix pipeline screen step-column header label (Pipeline -> Steps)

## v0.7.4

- Fix badblocks never running (verify_identity whitespace)
- Real NVMe SMART parsing

## v0.7.3

- Bump version and rebuild release

## v0.7.2

- Fix audit findings F1-F16: surface pipeline errors, root-gated SMART, non-destructive test, bundled ld-linux, self-contained reports, classifier FS/uninterrupted

## v0.7.1

- MEGA AUDIT fixes: SSD/NVMe support, scrollable body, live output
- Fix badblocks resume blocks-count, fix formatter error message
- Fix classifier: pending sectors -> Bronze, UNKNOWN health -> Failed
- CRITICAL fix: restore ExecutionScreen class, fix SMART flow, fix classifier
- Fix freeze on 'Validate Another Drive'

## v0.7.0

- Pipeline reorganization, SMART metrics/ETA, UI descriptions, bug fixes
- Fix SyntaxError in app.py caused PyInstaller 'invalid module'

## v0.6.1

- Fix badblocks/SMART runtime bugs, test mode, cleanup

## v0.6.0

- Over-engineering audit and corrections

## v0.5.2

- Critical bug fixes and improvements

## v0.5.1

- Fix bundle tool resolution, add bundle-tools.sh, update release
- Bugfixes, docs alignment, full codebase audit
