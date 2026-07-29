# TUI Premium Redesign Design Spec

## Goal
Rewrite all 9 TUI screens from scratch with a premium aesthetic: double-line box-drawing borders, consistent visual hierarchy, status badges, and polished metric presentation. No business logic changes.

## Visual Language

### CSS Classes
| Class | Border | Background | Use |
|-------|--------|------------|-----|
| `.panel` | `double #00ff00` (╔═╗║╚╝) | `#0a0a0a` | Main content containers |
| `.panel-warn` | `double #ffff00` | `#1a1a0a` | Warning panels |
| `.panel-error` | `double #ff0000` | `#1a0a0a` | Error panels |
| `.panel-selected` | `double #00ff00` | `#0a1a0a` | Selected/interactive panels |
| `.panel-disabled` | `double #444444` | `#0a0a0a` | Disabled items |
| `.title-bar` | `solid #00ff00` | `#001100` | Screen headers |
| `.section-title` | — | — | Bold green group titles |
| `.metric-card` | `solid #333333` | `#0a0a0a` | Individual metrics (3-col grid) |
| `.status-badge` | `solid #333333` | varies | Status indicators |
| `.btn-bar` | — | — | Button row container |
| `.btn` | `double #00ff00` | `#0a1a0a` | Individual buttons |
| `.btn:hover` | `double #00ff00` bg `#1a3a1a` | — | Hover state |
| `.btn-selected` | `double #00ff00` bg `#0a1a0a` | — | Selected button |

### Color Palette
- Primary: `#00ff00` (green) — borders, titles, selection
- Warning: `#ffff00` (yellow) — warnings
- Error: `#ff0000` (red) — errors, failures
- Text: `#cccccc` (light gray) — primary text
- Muted: `#888888` (gray) — secondary text
- Background: `#000000` (black) — screen bg
- Panel bg: `#0a0a0a` (near-black) — panel backgrounds

### Spacing
- 2-space indent inside panels
- 1-line gap between panels
- Metric cards: 3-column grid, min-width 12 chars each
- Buttons: centered in btn-bar, min-width 14 chars

## Screen Designs

### 1. StartupScreen
```
┌─ OldButGold v0.9.0 / Startup ───────────────────────────────┐
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║       O L D   B U T   G O L D                        ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   HDD Validation & Refurbishment Toolkit                   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║ Legal Disclaimer                                     ║   │
│   ║                                                      ║   │
│   ║  OldButGold performs hardware validation...          ║   │
│   ║  Use of this software is entirely at the user's      ║   │
│   ║  own risk.                                           ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   [ Detected 3 drive(s). Ready. ]                         │
│                                                            │
│         ╔══════════╗    ╔══════════╗                        │
│         ║  Continue  ║    ║   Exit     ║                        │
│         ╚══════════╝    ╚══════════╝                        │
│                                                            │
│  ←/→ Navigate  Enter Select  Esc Exit                     │
└────────────────────────────────────────────────────────────┘
```

### 2. DriveSelectionScreen
```
┌─ OldButGold v0.9.0 / Select Drive ──────────────────────────┐
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Samsung SSD 870 EVO 1TB                             ║   │
│   ║  /dev/sda  SATA  1.0 TB                              ║   │
│   ║  ! WARNING: Drive contains active filesystem         ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   ═════════════════════════════════════════════════════════   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Seagate BarraCuda 2TB                                ║   │
│   ║  /dev/sdb  SATA  2.0 TB                              ║   │
│   ║  ! Interrupted Validation - 42%                        ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│         ╔══════════╗  ╔══════════╗  ╔══════════╗  ╔════╗   │
│         ║   Back   ║  ║ Continue ║  ║ Refresh  ║  ║Quit║   │
│         ╚══════════╝  ╚══════════╝  ╚══════════╝  ╚════╝   │
│                                                            │
│  ↑/↓ Select  Enter Confirm  R Refresh  Esc Back           │
└────────────────────────────────────────────────────────────┘
```

### 3. MountWarningScreen
```
┌─ OldButGold v0.9.0 / Drive Mounted ─────────────────────────┐
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Samsung SSD 870 EVO 1TB                              ║   │
│   ║  /dev/sda  1.0 TB                                     ║   │
│   ║                                                      ║   │
│   ║  This drive has mounted partitions:                  ║   │
│   ║  • /dev/sda1 → /mnt/data                             ║   │
│   ║  • /dev/sda2 → /mnt/backup                           ║   │
│   ║                                                      ║   │
│   ║  All data on these partitions will be                ║   │
│   ║  inaccessible until remounted.                       ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   [ Unmounting... ]                                        │
│                                                            │
│         ╔══════════════════╗  ╔══════════╗               │
│         ║ Unmount & Continue ║  ║   Back     ║               │
│         ╚══════════════════╝  ╚══════════╝               │
│                                                            │
│  Esc Back  Enter Unmount                                    │
└────────────────────────────────────────────────────────────┘
```

### 4. SessionDecisionScreen
```
┌─ OldButGold v0.9.0 / Session Recovery ──────────────────────┐
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Interrupted Validation Session                       ║   │
│   ║                                                      ║   │
│   ║  Model:         Samsung SSD 870 EVO 1TB              ║   │
│   ║  Serial:        S5Z8NX0M123456                       ║   │
│   ║  Capacity:      1.0 TB                               ║   │
│   ║  Current Stage: Badblocks Validation                  ║   │
│   ║  Completed:     42%                                   ║   │
│   ║  Started:       2026-07-29 14:30:00                   ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   This drive has an interrupted validation session.       │
│   What would you like to do?                              │
│                                                            │
│         ╔══════════╗  ╔══════════╗  ╔══════════════╗  ╔════╗│
│         ║  Recover  ║  ║ Restart  ║  ║ View Details ║  ║Back║│
│         ╚══════════╝  ╚══════════╝  ╚══════════════╝  ╚════╝│
│                                                            │
│  Enter Select  Esc Back                                      │
└────────────────────────────────────────────────────────────┘
```

### 5. DriveInfoScreen
```
┌─ OldButGold v0.9.0 / Drive Info / Samsung SSD... ───────────┐
│                                                            │
│   ╔══════════════════════════╗  ╔═══════════════════════╗   │
│   ║  Device Information      ║  ║  Configuration          ║   ║
│   ║  Model: Samsung SSD...   ║  ║  Interface: SATA        ║   ║
│   ║  Serial: S5Z8NX0M...     ║  ║  Transport: SATA       ║   ║
│   ║  Firmware: EXM7...       ║  ║  SMART: Supported       ║   ║
│   ║  Capacity: 1.0 TB        ║  ║  Current FS: ext4      ║   ║
│   ║  WWN: 0x52...            ║  ║  Partition: GPT        ║   ║
│   ║  Device: /dev/sda        ║  ║                        ║   ║
│   ╚══════════════════════════╝  ╚═══════════════════════╝   │
│                                                            │
│   ╔══════════════════════════╗  ╔═══════════════════════╗   │
│   ║  SMART Information       ║  ║  Geometry              ║   ║
│   ║  Health: PASSED         ║  ║  Logical Sector: 512   ║   ║
│   ║  Temp: 35°C             ║  ║  Physical Sector: 4096 ║   ║
│   ║  Power-on: 1200 h       ║  ║                        ║   ║
│   ║  Reallocated: 0         ║  ║                        ║   ║
│   ║  Pending: 0             ║  ║                        ║   ║
│   ╚══════════════════════════╝  ╚═══════════════════════╝   │
│                                                            │
│         ╔══════════╗  ╔══════════╝                       │
│         ║ Continue ║  ║   Back     ║                       │
│         ╚══════════╝  ╚══════════╝                       │
│                                                            │
│  Esc Back  Enter Continue                                    │
└────────────────────────────────────────────────────────────┘
```

### 6. ValidationConfigScreen
```
┌─ OldButGold v0.9.0 / Configuration ──────────────────────────┐
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Validation Profile                                    ║   │
│   ║  ╔══════════════╗                                      ║   │
│   ║  ║  Recommended  ║  ← selected                        ║   │
│   ║  ╚══════════════╝                                      ║   │
│   ║  ══════════════════                                    ║   │
│   ║  ║  Extended     ║                                      ║   │
│   ║  ╚══════════════╝                                      ║   │
│   ║                                                      ║   │
│   ║  Optimized validation created for OldButGold.        ║   │
│   ║  Uses two destructive validation patterns...         ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Filesystem                                          ║   │
│   ║  ╔══════════════╗  ╔══════════════╗  ╔══════════════╗  ║   │
│   ║  ║  ext4        ║  ║  ntfs        ║  ║  exfat       ║  ║   │
│   ║  ╚══════════════╝  ╚══════════════╝  ╚══════════════╝  ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Volume Label (optional)                             ║   │
│   ║  [_________________________]                         ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│         ╔══════════╗  ╔══════════════╗                     │
│         ║   Back   ║  ║  Continue    ║                     │
│         ╚══════════╝  ╚══════════════╝                     │
│                                                            │
│  Esc Back  Enter Continue                                    │
└────────────────────────────────────────────────────────────┘
```

### 7. FinalConfirmationScreen
```
┌─ OldButGold v0.9.0 / Confirm ───────────────────────────────┐
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Validation Summary                                  ║   │
│   ║                                                      ║   │
│   ║  Drive:    Samsung SSD 870 EVO 1TB                   ║   │
│   ║  Serial:   S5Z8NX0M123456                            ║   │
│   ║  Capacity: 1.0 TB                                    ║   │
│   ║                                                      ║   │
│   ║  Profile:     Recommended                           ║   │
│   ║  Filesystem:  ext4                                   ║   │
│   ║  Label:       (none)                                 ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   ═════════════════════════════════════════════════════════   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  WARNING: ALL EXISTING DATA WILL BE                  ║   │
│   ║  PERMANENTLY DESTROYED!                                ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│         ╔══════════╗  ╔══════════════════╗               │
│         ║   Back   ║  ║ Start Validation ║               │
│         ╚══════════╝  ╚══════════════════╝               │
│                                                            │
│  Esc Back  Enter Start                                      │
└────────────────────────────────────────────────────────────┘
```

### 8. ExecutionScreen
```
┌─ OldButGold v0.9.0 / Validation ────────────────────────────┐
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Validation Stages                                    ║   │
│   ║  [✓]  Quick Identify                                 ║   │
│   ║  [✓]  SMART Short Self-Test                           ║   │
│   ║  [▶]  Badblocks Validation                            ║   │
│   ║  [ ]  Filesystem Creation                             ║   │
│   ║  [ ]  Final Verification                              ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   ═════════════════════════════════════════════════════════   │
│                                                            │
│   [████████████████████████████████████████░░░░░░░░░░] 42%  │
│                                                            │
│   ╔══════════╗  ╔══════════╗  ╔══════════╗  ╔══════════╗   │
│   ║Operation ║  ║Progress  ║  ║   ETA    ║  ║   Speed  ║   │
│   ║Writing   ║  ║42.5%     ║  ║ 15m 30s  ║  ║ 85.2 MB/s║   │
│   ╚══════════╝  ╚══════════╝  ╚══════════╝  ╚══════════╝   │
│                                                            │
│   ╔══════════╗  ╔══════════╗  ╔══════════╗  ╔══════════╗   │
│   ║ Pattern  ║  ║Elapsed   ║  ║Bad Blocks║  ║  Errors  ║   │
│   ║ 0xAA     ║  ║ 22m 15s  ║  ║    None  ║  ║   None   ║   │
│   ╚══════════╝  ╚══════════╝  ╚══════════╝  ╚══════════╝   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Samsung SSD 870 EVO 1TB  |  S5Z8NX0M...  |  Temp: 35°C ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   [ Output log: badblocks: opening /dev/sda...            ]  │
│   [ 42.5% done, 22:15 elapsed. (0/0/0 errors)            ]  │
│                                                            │
│  [C] Cancel  —  Elapsed: 00:22:15                           │
└────────────────────────────────────────────────────────────┘
```

### 9. CompleteScreen
```
┌─ OldButGold v0.9.0 / Complete ──────────────────────────────┐
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  [GOLD]                                               ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Samsung SSD 870 EVO 1TB                              ║   │
│   ║  S5Z8NX0M123456  |  1.0 TB                            ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Filesystem:    ext4                                  ║   │
│   ║  Label:         (none)                                ║   │
│   ║  Bad Blocks:    0                                     ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  SMART Comparison                                    ║   │
│   ║  Reallocated Sectors  Before: 0    After: 0    Delta: — ║   │
│   ║  Pending Sectors      Before: 0    After: 0    Delta: — ║   │
│   ║  Uncorrectable        Before: 0    After: 0    Delta: — ║   │
│   ║  CRC Errors           Before: 0    After: 0    Delta: — ║   │
│   ║  Temperature          Before: 35°C After: 38°C Delta: +3°C ║   │
│   ║  Power-On Hours       Before: 1200 After: 1205         ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Validation passed. No issues detected.               ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│   ╔══════════════════════════════════════════════════════╗   │
│   ║  Duration: 22m 15s                                    ║   │
│   ║  Report: /home/user/reports/obg_20260729_143000.md    ║   │
│   ╚══════════════════════════════════════════════════════╝   │
│                                                            │
│         ╔══════════════╗  ╔══════════════════╗  ╔════╗   │
│         ║ Export Report ║  ║ Validate Another ║  ║ Quit ║   │
│         ╚══════════════╝  ╚══════════════════╝  ╚════╝   │
│                                                            │
│  Enter Another  Q Quit                                       │
└────────────────────────────────────────────────────────────┘
```

## Implementation Notes

1. **No business logic changes**: All screen logic (navigation, data flow, callbacks) remains identical. Only compose() and CSS change.
2. **Tests unaffected**: Tests don't directly test TUI screens.
3. **SCREEN_SIZE stays (120, 40)**: Premium aesthetic within same dimensions.
4. **Box-drawing**: Use Unicode double-line (╔═╗║╚╝) for panels, single-line (─│┌┐└┘) for inner borders.
5. **Keyboard navigation**: Arrow keys, Enter, Esc work exactly as before. Mouse click support retained.
