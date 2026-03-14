# RetroClamp GUI Card Redesign — Design Spec

**Date:** 2026-03-12
**Status:** Approved
**Scope:** Full GUI redesign — `gui/` directory rebuilt; `core/` and `modules/` untouched

---

## Overview

Replace the current `QTabWidget`-based layout with a persistent sidebar shell and a `QStackedWidget` content area. All views are rebuilt as clean `QWidget` subclasses using a bold/elevated card design language. The Dracula palette and existing theming stack are preserved; the structural chrome is what changes.

---

## Design Decisions

| Question | Answer |
|---|---|
| Navigation | Full sidebar, icon + text, always visible (Notion/Figma style) |
| Home screen | Quick-start — 3 large action cards, recent files strip |
| Redesign scope | All views (full rebuild of `gui/`) |
| Card style | Bold/Elevated — deep shadow, 38px emoji icon, purple accent bar |
| Sidebar items | 5 items: Home, Compression, Batch, Tools, Settings |
| Demoted items | Theme merged into Settings › Appearance; Debug moved to sidebar footer |

---

## Architecture: Approach B — Shell-First, Views Rewritten

Build the new `AppWindow` shell first. Existing backend (`core/`, `modules/`) is untouched. Old `gui/*_tab.py` files remain in place until their replacement is complete and tested, then are deleted. Each new view is a standalone `QWidget` dropped into the `QStackedWidget`.

### App Shell

```
AppWindow (QMainWindow)
└── Central widget (QWidget, horizontal layout)
    ├── SidebarWidget (QWidget, fixed 220px)
    └── QStackedWidget
        ├── index 0: HomeView
        ├── index 1: CompressionView
        ├── index 2: BatchView
        ├── index 3: ToolsView
        └── index 4: SettingsView
```

`SidebarWidget` emits `page_changed(int)`. `AppWindow` connects it to `QStackedWidget.setCurrentIndex()`. Navigation is instant with no transitions.

---

## Color Reference

| Token | Value | Usage |
|---|---|---|
| `bg` | `#282a36` | Main window background |
| `sidebar-bg` | `#21222c` | Sidebar background (one step darker) |
| `surface` | `#313444` | Card and panel backgrounds |
| `surface-raised` | `#353749` | Elevated card backgrounds |
| `border` | `#44475a` | Default borders |
| `muted` | `#6272a4` | Secondary text, inactive labels |
| `fg` | `#f8f8f2` | Primary text |
| `purple` | `#bd93f9` | Accent — active nav, bars, CTAs |
| `cyan` | `#8be9fd` | Processing state indicator |
| `green` | `#50fa7b` | Success/Done state |
| `red` | `#ff5555` | Error state |

---

## Card Component (Shared)

Used on Home screen and Tools grid. Consistent across both contexts.

- **Size:** ~180×160px (Home/Tools), adjustable
- **Background:** `#353749`
- **Border:** `1px solid #44475a`
- **Border-radius:** 12px
- **Shadow:** `QGraphicsDropShadowEffect` — blur radius 20, offset (0, 4), color `rgba(0,0,0,0.5)`. Qt stylesheet does not support `box-shadow`; this effect is applied programmatically in `ActionCard.__init__`.
- **Hover:** border lifts to `#6272a4`, shadow blur radius increases to 28; cursor set via `self.setCursor(Qt.PointingHandCursor)` in `__init__` (Qt stylesheet does not support `cursor` property)
- **Contents (top to bottom):**
  1. Emoji icon — 38px
  2. Purple accent bar — 32px × 3px, `#bd93f9`, border-radius 2px
  3. Title — 15px, semibold, `#f8f8f2`
  4. Description — 12px, `#6272a4`, max 2 lines

---

## Section 1: App Shell & Sidebar

### Sidebar

- **Width:** 220px, fixed, never collapsed
- **Background:** `#21222c`
- **Header:** App logo/name — `⬡ RetroClamp`, 16px, `#bd93f9`
- **Nav items (top section):** Home, Compression, Batch, Tools, Settings
  - Active: 3px purple left border + `#313444` background fill
  - Hover: `#313444` background, no border
  - Inactive: transparent
- **Footer (bottom section):**
  - Debug shortcut — 11px, `#6272a4`, opens `DebugDialog`: a modeless `QDialog` (non-blocking, stays open while the app is used) that surfaces `DebugLogger` output. Contains a scrollable `QPlainTextEdit` (monospace, `#f8f8f2` on `#1e1f29`, read-only) that auto-scrolls to the latest entry. `DebugLogger` writes to a rotating log file; `DebugDialog` tails it via a `QTimer` (250ms interval): on each tick, open the log file at a stored `_log_offset` byte position, read any new bytes, append decoded text to the `QPlainTextEdit`, and advance `_log_offset`. Footer row has a `[ Clear ]` button (calls `DebugLogger.clear_log()` — a new method added in this redesign that truncates the log file safely through the existing `RotatingFileHandler`; direct file truncation must not be used as the handler holds an open file descriptor on Windows) and a `[ Copy ]` button (copies current `QPlainTextEdit` text to clipboard). Not a page swap — the stacked widget index does not change.
  - Version label — `v1.2.0`, 11px, `#6272a4`

---

## Section 2: Home View (`HomeView`)

### Structure

1. **Header** — "Welcome to RetroClamp" (22px, `#f8f8f2`) + "What do you want to do?" (13px, `#6272a4`)
2. **Action card row** — 3 Bold/Elevated cards side by side
3. **Recent files strip** — last 5 processed files; hidden if no history

### Action Cards

| Card | Icon | Title | Description | Destination |
|---|---|---|---|---|
| 1 | 💿 | Compress | Create CHD from disc images | `CompressionView` (index 1) |
| 2 | 📦 | Batch | Process multiple files | `BatchView` (index 2) |
| 3 | 📂 | Extract Archive | Unpack ZIPs, 7z, RARs | `CompressionView` (index 1) |

Clicking a card navigates to the corresponding view (same as clicking the sidebar item). "Extract Archive" opens `CompressionView` — the compression and extraction workflow share the same view.

### Recent Files Strip

- Section label: "RECENT FILES" — 11px uppercase, `#6272a4`
- Rows: file icon · filename (truncated) · relative timestamp
- Clicking a row calls `AppWindow.open_file(path)`, which navigates to `CompressionView` (index 1) and calls `CompressionView.load_file(path: str)` to pre-populate the source file list; console profile is set to Auto-detect
- Hidden entirely if no history (no empty state placeholder)

---

## Section 3: Compression View (`CompressionView`)

### Layout

Two-column: **left panel** (~55%) source/settings, **right panel** (~45%) live output. Both panels use card surface (`#313444`, `border-radius: 10px`).

### Left Panel

**Source drop zone**
- Dashed border (`1.5px dashed #44475a`) when empty
- Collapses to compact file list once files are loaded
- File list rows: filename · size · status chip (Queued/Done/Error) · ✕ remove button

**Settings (stacked, with section labels)**
1. Output path — dropdown (Same as source / Custom) + folder picker if custom
2. Console profile — dropdown (Auto-detect, PS1, PS2, Dreamcast, Saturn, …)
3. "Advanced ▾" disclosure row — expands additional CHDMAN flags (hidden by default)

**Action buttons**
- `[ Compress ]` — primary, full purple fill (`#bd93f9` bg, `#282a36` text), 40px tall
- `[ Extract ]` — secondary, outlined style
- During operation: Compress becomes `[ Cancel ]`

### Right Panel

- Monospace log stream (`#f8f8f2` on `#1e1f29`)
- Status bar at bottom: detected console tag · completed count · error count
- Error lines highlighted in `#ff5555`

---

## Section 4: Batch View (`BatchView`)

### Layout

Three zones: config bar (top), queue table (middle, fills available space), progress footer (bottom, pinned).

### Config Bar

Single horizontal strip (not a card). Source folder + output folder with browse buttons. Console profile dropdown. Recurse subdirectories checkbox.

### Queue Table

Columns: status indicator · filename · detected console · state chip

State chip colors:
- Queued: `#6272a4`
- Processing: `#8be9fd` — `QPropertyAnimation(opacity_effect, b"opacity")` on `QGraphicsOpacityEffect`, pulsing 0.5→1.0→0.5, 800ms duration, loop count −1
- Done: `#50fa7b`
- Error: `#ff5555` + inline `[!]` expand button for error detail

Rows selectable for bulk remove. Table fills all available vertical space.

### Footer

- Full-width progress bar: `#bd93f9` fill on `#44475a` track
- Below bar: file count · ETA · action buttons
- Button states:
  - At rest: only `[ Start ]` active
  - Running: `[ Pause ]` and `[ Cancel ]` active, `[ Start ]` disabled
  - Paused: `[ Resume ]` replaces `[ Pause ]`
- Checkpoint state saves automatically; cancelled batches resume next session silently

---

## Section 5: Tools View (`ToolsView`)

### Layout

Card grid (same Bold/Elevated cards as Home screen). Clicking a card opens the tool's detail panel. A back chevron `← Tools` returns to the grid.

### Tool Cards

| Card | Icon | Title | Status |
|---|---|---|---|
| 1 | 📋 | M3U Generator | Active |
| 2 | 🎮 | ScummVM Generator | Active |
| 3 | 🔬 | BIOS Validator | Coming soon |

Coming-soon cards: `QGraphicsOpacityEffect(opacity=0.5)` applied programmatically to the card widget (Qt stylesheet `opacity` does not propagate to child widgets); "Coming soon" in place of description; non-clickable.

### Tool Detail Panel

- `← Tools` back button in top-left
- Tool panel is a self-contained `QWidget` loaded by the plugin system
- Replaces the grid in the `ToolsView` content area (no separate window)

### Plugin API Contract

The existing `register_tab(main_window)` plugin API is incompatible with the new architecture. New contract:

- **Method:** `register_panel(tools_view: ToolsView) -> QWidget`
- **Argument:** `tools_view` — provided so plugins can trigger back-navigation via `tools_view.show_grid()`
- **Return:** A self-contained `QWidget` that `ToolsView` embeds in its content area
- `tools/plugin_template.py` must be updated to implement `register_panel`; this update is in scope for this redesign
- **Plugin discovery:** `ToolsView` loads plugins via a hardcoded list: `TOOL_PLUGINS = [m3u_generator, scummvm_generator, bios_validator]`. No directory scanning. A plugin that returns `None` from `register_panel` is treated as unavailable — its card renders as coming-soon. `tools/bios_validator.py` is a stub module implementing `register_panel` that returns `None`, which produces the BIOS Validator coming-soon card without special-casing in `ToolsView`.

---

## Section 6: Settings View (`SettingsView`)

### Layout

Mini two-column layout within the view: category list (left, ~180px) + content panel (right).

### Categories

1. **General** — language placeholder, startup behavior (reopen last session), worker thread count
2. **Appearance** *(formerly Theme tab)* — theme selector, accent color, font size
3. **CHDMAN** — executable path + Verify button, compression level slider, checksum toggle
4. **Paths** — default source folder, default output folder, temp directory
5. **Advanced** — max concurrent workers, debug log verbosity, keep-extracted-archives toggle

### Appearance Category

- Theme: radio group — Dark (Dracula) default, Light, High Contrast
- Accent color: 3 swatches — Purple `#bd93f9`, Cyan `#8be9fd`, Green `#50fa7b`
- Font size: Small / Medium (default) / Large radio
- Live preview (no save button needed)

### Save Behavior

Settings auto-save on change via `AppSettings.set(category, key, value)` (`modules/app_settings.py`). A "Saved" flash (`#50fa7b`, fades after 1.5s) appears bottom-right of content panel after each change. No explicit Save button.

### AppSettings Keys Required

New keys this redesign must add to `DEFAULT_SETTINGS` in `modules/app_settings.py`:

| Category | Key | Type | Default | Notes |
|---|---|---|---|---|
| `appearance` *(new category)* | `theme` | str | `"dracula"` | Replaces `general.theme` — simultaneously remove `general.theme` from `DEFAULT_SETTINGS` and migrate any persisted value on first launch after upgrade |
| `appearance` | `accent_color` | str | `"#bd93f9"` | — |
| `appearance` | `font_size` | str | `"medium"` | — |
| `general` | `reopen_last_session` | bool | `False` | — |
| `general` | `worker_thread_count` | int | `2` | — |
| `chdman` *(new category)* | `compression_level` | str | `""` | — |
| `chdman` | `verify_checksum` | bool | `True` | — |

Existing keys used directly (no changes needed): `paths.chdman_path`, `paths.last_input_directory`, `paths.last_output_directory`, `batch.max_concurrent_jobs`, `logging.level`.

**Notes on existing keys and key interactions:**

- **`logging.log_level`**: `debug_logger.py` currently reads `logging.log_level` (not `logging.level`) at runtime — this is a pre-existing inconsistency between `DEFAULT_SETTINGS` and the actual read path. It is out of scope for this redesign. If `SettingsView` surfaces a log verbosity control, wire it to `logging.log_level`.
- **`general.theme` migration**: The existing `general.theme` key must be removed and replaced by `appearance.theme` (added in this redesign). Migration logic should run on first launch after upgrade; if `general.theme` is present, copy its value to `appearance.theme` then remove `general.theme`.
- **`chdman.verify_checksum`**: Stored and surfaced in `SettingsView`. Note: `core/chdman.py` does not currently implement a `--noverify` flag, and `core/` is out of scope for this redesign. The setting is therefore inert at runtime in this release — it will be wired to actual CHDMAN behavior in a future update that includes `core/` changes. This is distinct from `compression.verify_after_compression` (a separate existing key that triggers post-operation output verification).
- **`general.worker_thread_count`**: Governs `CHDManager`'s internal `QThreadPool` maximum thread count. There is no single global worker pool — each manager owns a private `QThreadPool`. `CHDManager.__init__` must be updated to read this setting and call `self.thread_pool.setMaxThreadCount(value)` on startup. This is distinct from `batch.max_concurrent_jobs` (the number of parallel CHD jobs within a single batch run), which is an existing key with no changes needed.
- **`chdman.compression_level`**: `core/chdman.py` types `compression_level` as `Optional[str]`, accepting CHDMAN codec strings (e.g. `"zstd"`, `"zlib"`, `"lzma"`). The empty string default means no override — CHDMAN uses its built-in default. The `SettingsView` CHDMAN panel must expose a codec dropdown, not a numeric slider.

---

## File Plan

### New files (to create)

```
gui/
├── app_window.py          # AppWindow — QMainWindow shell
├── sidebar_widget.py      # SidebarWidget — permanent nav
├── views/
│   ├── __init__.py
│   ├── home_view.py       # HomeView
│   ├── compression_view.py
│   ├── batch_view.py
│   ├── tools_view.py
│   └── settings_view.py
└── components/
    ├── __init__.py
    ├── action_card.py     # Reusable Bold/Elevated card widget
    ├── section_label.py   # Uppercase section header label
    └── status_chip.py     # Colored state indicator chip
```

### New files in `tools/` (to create)

```
tools/
├── m3u_generator.py       # Extracted from gui/m3u_tab.py; implements register_panel
└── bios_validator.py      # Stub; register_panel returns None (produces coming-soon card)
```

`tools/plugin_template.py` — **update** to implement `register_panel` API (not a new file).

### Existing files to update

```
tools/__init__.py              # CRITICAL: Replace register_tab detection (lines 109-111) and dispatch (line 192)
                               #   with register_panel. Without this, all per-plugin changes have no effect.
tools/scummvm_generator.py     # Replace register_tab(parent_widget) with register_panel(tools_view) -> QWidget
```

**Coordinated updates required** — these files reference `register_tab` and must be updated in the same change set to stay consistent. They are outside the GUI redesign scope but must not be left with broken references:

| File | Reference type |
|---|---|
| `quality_gates.py` | Validates plugin compliance (lines 451–452, 532) |
| `retroclamp_analyzer.py` | Plugin analysis check (line 308) |
| `focused_analysis.py` | Plugin report logic (lines 276, 329, 333, 343, 347) |
| `tests/plugins/test_plugin_template.py` | Plugin template compliance test (lines 38–41) |
| `scripts/validate_plugins.py` | Standalone validation script (lines 28–29) |
| `README.md` | Plugin API documentation (line 172) |

### Files to retire (after replacement complete)

```
gui/compression_tab.py
gui/extraction_tab.py    # functionality absorbed into compression_view.py
gui/batch_tab.py
gui/tools_tab.py
gui/m3u_tab.py
gui/theme_tab.py
gui/home_tab.py
gui/settings_tab.py
```

`main.py` updated to instantiate `AppWindow` instead of the old tab-based window.

---

## Out of Scope (this spec)

- Accessibility / WCAG-AA audit (v1.4.0+)
- Theme editor (v1.4.0+)
- Free-form color picker in Appearance settings
- Animated view transitions
- New tool implementations beyond M3U Generator and ScummVM Generator stubs (BIOS Validator is Coming soon)
