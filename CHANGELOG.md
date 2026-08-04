# Changelog

## v0.10.1

- Fix Recommended profile: single destructive pattern (`-t 0xaa`, 4K blocks) — 1 write pass + 1 read pass (2 passes total), instead of two test patterns (4 passes)
- Fix app/UI appearing frozen during long scans: streaming subprocess runner now detects stalls (no output for 10 min) and aborts with a clean failure; cancel (`C`) now stops badblocks mid-scan and reports the step as cancelled
- Fix missing timeouts on interactive commands (lsblk, smartctl) so drive refresh and SMART steps cannot hang indefinitely
- Fix MarkupError crash rendering the cancelled-step icon (`[/]` close-tag → `[#]`)
- MainScreen refresh (R / Refresh button) verified end-to-end; bounded by new timeouts so it cannot stall on wedged devices
- docs: align Recommended profile description (single pattern) in TUI design spec

## v0.10.0

- TUI reescrita do zero: 9 telas unificadas em 5 (Main, Drive, Config, Execution, Complete) — fluxo KISS
- Paleta cinza-azulada monocromática (#0d1117 bg, #58a6ff accent, #3fb950 ok, #d29922 warn, #f85149 err)
- Navegação completa por teclado e mouse em todas as telas (Enter/Esc com priority, cards clicáveis)
- MainScreen: disclaimer + lista de discos em um só fluxo
- DriveScreen: Device/Configuration/SMART unificados + avisos de montagem/sessão + ações (Back/Unmount/Recover/Restart/Configure)
- ConfigScreen: seleção de perfil/filesystem/label + confirmação final
- ExecutionScreen: stages + progresso + 9 mini-cards de métricas + log; cancelamento com `c`
- CompleteScreen: classificação, comparação SMART, assessment, export/novo teste/sair
- Bug fix: `pop_to_root` não estoura mais a MainScreen (base da pilha)
- Smoke test de navegação completa em PTY (entrada → cancelamento → retorno → exit limpo)

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
