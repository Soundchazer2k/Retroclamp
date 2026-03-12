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
- **Shadow:** `0 4px 20px rgba(0,0,0,0.5)`
- **Hover:** border lifts to `#6272a4`, shadow deepens; cursor pointer
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
  - Debug shortcut — 11px, `#6272a4`, opens debug log panel (drawer/dialog, not a page swap)
  - Version label — `v1.2.0`, 11px, `#6272a4`

---

## Section 2: Home View (`HomeView`)

### Structure

1. **Header** — "Welcome to RetroClamp" (22px, `#f8f8f2`) + "What do you want to do?" (13px, `#6272a4`)
2. **Action card row** — 3 Bold/Elevated cards side by side
3. **Recent files strip** — last 5 processed files; hidden if no history

### Action Cards

| Card | Icon | Title | Description |
|---|---|---|---|
| 1 | 💿 | Compress | Create CHD from disc images |
| 2 | 📦 | Batch | Process multiple files |
| 3 | 📂 | Extract Archive | Unpack ZIPs, 7z, RARs |

Clicking a card navigates to the corresponding view (same as clicking the sidebar item).

### Recent Files Strip

- Section label: "RECENT FILES" — 11px uppercase, `#6272a4`
- Rows: file icon · filename (truncated) · console tag · relative timestamp
- Clicking a row re-opens the file in Compression view
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
- Processing: `#8be9fd` (animated)
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
| 2 | 🔬 | BIOS Validator | Active |
| 3 | — | (placeholder) | Coming soon |

Coming-soon cards: 50% opacity, "Coming soon" in place of description, non-clickable.

### Tool Detail Panel

- `← Tools` back button in top-left
- Tool panel is a self-contained `QWidget` loaded by the plugin system
- Replaces the grid in the `ToolsView` content area (no separate window)

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

Settings auto-save on change. A "Saved" flash (`#50fa7b`, fades after 1.5s) appears bottom-right of content panel after each change. No explicit Save button.

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

### Files to retire (after replacement complete)

```
gui/compress_tab.py
gui/batch_tab.py
gui/tools_tab.py
gui/theme_tab.py
gui/debug_tab.py
```

`main.py` updated to instantiate `AppWindow` instead of the old tab-based window.

---

## Out of Scope (this spec)

- Accessibility / WCAG-AA audit (v1.4.0+)
- Theme editor (v1.4.0+)
- Free-form color picker in Appearance settings
- Animated view transitions
- New tool implementations beyond M3U Generator and BIOS Validator stubs
