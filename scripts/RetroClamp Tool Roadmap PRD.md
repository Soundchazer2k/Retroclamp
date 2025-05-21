# RetroClamp Tool Roadmap PRD: Automating Common Frontend Configuration Tasks

**Document Version:** 1.0  
**Date:** 2025-05-19  
**Author:** Soundchazer

---

## Overview

This document defines the Product Requirements for seven auxiliary tools to be integrated into or offered alongside RetroClamp. These tools aim to solve common and repetitive frontend configuration challenges through AI-assisted automation and file system analysis.

Each tool targets a specific friction point encountered when preparing ROMs for display and execution in emulator frontends.

---

## Tool Roadmap

### 1. **ROM File Naming Normalizer**

**Goal:** Rename ROMs to match the most accurate naming convention from No-Intro, Redump, or TOSEC databases to improve metadata scraping success.

**Tasks:**

- Implement fuzzy-matching against official DATs.

- Allow user to select preferred database (No-Intro, Redump, TOSEC).

- Detect and log renaming suggestions.

- Batch rename files with confirmation dialog.

- Log changes with original vs. new name.

**Module:** `tools/rom_renamer.py`

**AI Reference Block:**

- **Input Files:** `.cue`, `.bin`, `.iso`, `.zip`, `.7z`

- **Reference Data:** DAT XML or JSON exports from No-Intro, Redump, TOSEC

- **Matching Rules:** Levenshtein similarity ≥ 0.85, strip tags like "(USA)", "[!]", serials

- **Output:** Renamed files or log mapping original ↔ new name

- **Options:** Dry-run mode, safe renaming toggle

- **Edge Cases:** Multi-disc sets, hacks, translated versions

---

### 2. **M3U Playlist Generator**

**Goal:** Automatically detect and group multi-disc games and generate valid `.m3u` playlists with proper disc order.

**Tasks:**

- Scan folders for ROMs with "(Disc X)", "CDx", or similar patterns.

- Group disc sets under a unified title using fuzzy grouping.

- Generate `.m3u` file with ordered disc entries.

- Support both relative and absolute paths.

- Optionally move disc files into a subfolder after M3U creation.

- Include support for special systems (PSX, Saturn, PC-FX).

**Module:** `tools/m3u_generator.py`

**AI Reference Block:**

- **Input Files:** `.cue`, `.chd`, `.bin`

- **Grouping Rules (Regex):** `(?i)\(disc\s?\d+\)`, `(?i)CD\d`, `(?i)Disk\d`

- **Output File:** `.m3u` with correct line order

- **Path Format:** Relative by default (configurable)

- **Frontend Compatibility:**
  
  - Batocera: hides disc files
  
  - LaunchBox: supports M3U and adds discs as additional apps
  
  - RetroArch: required for multi-disc support

- **Preferences:**
  
  - Move grouped discs to subfolder `/discs` (optional)
  
  - Warn if disc count is less than expected (e.g. FF7 with 1 disc only)

- **Test Case Required:** Sample PSX game with 3 discs, mixed naming

---

### 3. **Folder Structure Organizer**

**Goal:** Reorganize ROM folders based on frontend-specific best practices (e.g., Batocera, LaunchBox).

**Tasks:**

- Define folder structure templates for supported frontends.

- Detect current file layout and suggest changes.

- Allow users to apply changes or manually override.

- Move/rename files and directories as needed.

- Validate structure post-operation.

**Module:** `tools/folder_structure.py`

**AI Reference Block:**

- **Input:** Root ROM directory

- **Frontend Templates:** JSON schemas with paths per system

- **Supported Frontends:** Batocera, LaunchBox, Pegasus, EmulationStation

- **Example Schema:**
  
  ```json
  {
    "batocera": {
      "psx": "roms/psx/",
      "sega_cd": "roms/segacd/"
    },
    "launchbox": {
      "default": "Games/<System Name>/"
    }
  }
  ```

- **Output:** Folder structure audit report + proposed changes

- **Options:** Dry-run preview, backup before move

---

### 4. **BIOS Validator**

**Goal:** Detect missing or mismatched BIOS files for each supported emulator core or system.

**Tasks:**

- Load required BIOS checksum list from community-maintained database.

- Scan user-defined BIOS directories.

- Report missing or invalid BIOS files.

- Suggest known BIOS filename and source.

- Optional: Export checklist or generate dummy placeholders.

**Module:** `tools/bios_checker.py`

**AI Reference Block:**

- **Input Directory:** BIOS folder

- **Reference Data:** Libretro BIOS list (CSV or JSON)

- **Validation:** CRC32, SHA1 checksum

- **Output:** Table of found/missing BIOSes, with match status

- **Frontend Use:** RetroArch, Batocera, EmulationStation

- **Special Case:** PSX BIOS must be named `scph1001.bin` (strict match)

---

### 5. **Scraper-Compatible Metadata Renamer**

**Goal:** Rename `.cue`, `.m3u`, or compressed files to match titles recognized by scraping tools like Skraper, LaunchBox DB, etc.

**Tasks:**

- Cross-reference user filenames with external metadata sources.

- Normalize titles to remove hashes, serials, region suffixes, etc.

- Create aliases or symbolic links where renaming is undesired.

- Present batch rename proposals for approval.

**Module:** `tools/metadata_normalizer.py`

**AI Reference Block:**

- **Input:** ROM files, `.m3u`, `.cue`, `.zip`, `.7z`

- **Scraper DBs:** LaunchBox XML, Skraper JSON, Screenscraper API (optional)

- **Normalization:** Remove `[!], (USA), Rev 1`, etc.

- **Output:** Cleaned filenames; optional alias `.txt` or `.lnk`

- **Frontend Impact:** Better match with scraping engines

---

### 6. **Disc File Redundancy Cleaner**

**Goal:** Prevent duplicate entries in frontend game lists by hiding or moving disc files when M3U is present.

**Tasks:**

- Identify multi-disc games with existing `.m3u` files.

- Move redundant `.cue`, `.bin`, or `.chd` files to a subfolder (e.g., `discs/`).

- Optionally change extensions to custom (e.g., `.hidden`) to hide from scanners.

- Ensure operation is reversible.

**Module:** `tools/disc_cleaner.py`

**AI Reference Block:**

- **Input:** Directory with `.m3u` and disc files

- **Match Logic:** Disc files listed inside `.m3u`

- **Actions:** Move matching files to `/discs/`, or rename extension

- **Options:** Generate undo script/log

- **Target Frontends:** EmulationStation, Batocera, Attract Mode

---

### 7. **M3U Compatibility Verifier**

**Goal:** Alert users when M3U playlists are used with frontends or emulators that lack proper support.

**Tasks:**

- Create a mapping of emulator → core → M3U support.

- For each M3U file, check associated platform and assigned emulator.

- Alert users if unsupported core is detected.

- Optionally suggest alternative handling methods (e.g., Additional Apps in LaunchBox).

**Module:** `tools/m3u_verifier.py`

**AI Reference Block:**

- **Input:** `.m3u` file, assigned emulator/core

- **Reference Table:** JSON mapping of supported cores/emulators:
  
  ```json
  {
    "RetroArch": ["Beetle PSX", "Flycast", "Genesis Plus GX"],
    "DuckStation": ["Yes"],
    "PCSX2": ["No"]
  }
  ```

- **Output:** Warning if incompatible, suggestion if available

- **UI Hook:** Display inside "Tools" tab or during M3U generation

---

## Deliverables

- Seven new or enhanced tools integrated into RetroClamp’s "Tools" tab.

- Shared logging system integration.

- Optional wizard to run multiple tools as a single workflow (e.g., “Fix My Collection”).

- JSON config file to define per-frontend behavior profiles.

## Timeline Estimate

| Tool                       | Est. Duration |
| -------------------------- | ------------- |
| ROM File Naming Normalizer | 4–5 days      |
| M3U Playlist Generator     | 3–4 days      |
| Folder Structure Organizer | 3 days        |
| BIOS Validator             | 2–3 days      |
| Metadata Renamer           | 3 days        |
| Disc Cleaner               | 2 days        |
| M3U Verifier               | 2 days        |

---

**Total Estimate:** 3.5 weeks of development time

**Next Step:** Begin implementation of `m3u_generator.py`, then expand with unified frontend behavior profiles in `folder_structure.py`.
