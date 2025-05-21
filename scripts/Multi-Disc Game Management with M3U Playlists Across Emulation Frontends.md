# Multi-Disc Game Management with M3U Playlists Across Emulation Frontends

## Overview

This document provides best practices and technical notes for generating M3U playlist files for multi-disc game support across popular emulation frontends. It covers file/folder structures, naming conventions, emulator/core requirements, library integration, and metadata handling. Each section includes official documentation and community reference links for further review.

---

## Table of Contents

1. [Retrobat](#retrobat)

2. [Batocera](#batocera)

3. [LaunchBox](#launchbox)

4. [RetroArch](#retroarch)

5. [EmulationStation](#emulationstation)

6. [Pegasus Frontend](#pegasus-frontend)

7. [Simple Launcher](#simple-launcher)

8. [Attract Mode](#attract-mode)

9. [RetroFE](#retrofe)

10. [Playnite](#playnite)

11. [General References](#general-references)

---

## 1. Retrobat

- **M3U Usage:**
  
  - Place the `.m3u` file in the system’s ROMs folder. List each disc file by exact filename, including extension, one per line.
  
  - Use relative paths whenever possible.
  
  - The M3U file should be named as the game (e.g., `Final Fantasy VII.m3u`).
  
  - Disc images (.cue/.bin/.chd) should be in the same folder.

- **Library:**
  
  - Retrobat will display the M3U as a single game entry and hide the individual discs.

- **Emulator/Core:**
  
  - Uses RetroArch cores; M3U must match what the core supports (e.g., Beetle PSX, Flycast, Genesis Plus GX).

- **Disc Swapping:**
  
  - Handled via emulator’s UI (RetroArch: Quick Menu → Disk Control → Eject, select index, Close Tray).

- **Metadata:**
  
  - Scraping relies on the M3U’s name. Ensure it matches the game’s real name.

**Links:**

- [Retrobat Docs - Multi-Disc Games](https://wiki.retrobat.org/doku.php?id=multidisc)

- [RetroBat Official Wiki](https://wiki.retrobat.org/)

---

## 2. Batocera

- **M3U Usage:**
  
  - Similar to Retrobat: M3U in ROM folder, disc images in same or subfolder. Use relative paths in M3U.
  
  - Batocera will show one entry per M3U and hide disc files.

- **Emulator/Core:**
  
  - Uses RetroArch cores for disc-based systems (PSX, Saturn, etc.).
  
  - Standalone emulators (e.g., Redream, PCSX2) may not support M3U.

- **Disc Swapping:**
  
  - Emulator (usually RetroArch) handles it via Disk Control menu.

- **Special:**
  
  - Batocera v35+ auto-hides disc files when M3U is present.

- **Metadata:**
  
  - Name the M3U exactly as the real game for scraping.

**Links:**

- [Batocera Docs - Multi-Disc](https://wiki.batocera.org/multidisc)

- [Batocera Wiki](https://wiki.batocera.org/)

- [Forum: M3U Use & Setup](https://forum.batocera.org/d/5357-multi-disc-support-m3u)

---

## 3. LaunchBox / Big Box

- **M3U Usage:**
  
  - M3U file in the ROMs folder with disc images. Name M3U as game title.
  
  - LaunchBox can auto-generate M3Us or combine discs if enabled in settings.

- **Library:**
  
  - Combines multi-disc into a single entry. Optionally, you can add discs as "Additional Apps."

- **Emulator/Core:**
  
  - Works best with RetroArch, Mednafen, and DuckStation (standalone or libretro) for M3U launching.
  
  - For non-M3U-supporting emulators, use "Additional Apps" or manual swapping.

- **Disc Swapping:**
  
  - Use emulator’s menu. LaunchBox does not swap discs directly.

- **Metadata:**
  
  - Scrapes based on the M3U name.

**Links:**

- [LaunchBox Docs - Multi-Disc](https://forums.launchbox-app.com/topic/50796-multi-disc-game-support/)

- [LB Docs: M3U Playlists](https://forums.launchbox-app.com/topic/59549-multi-disc-games-with-m3u/)

- [Official LaunchBox Documentation](https://docs.launchbox-app.com/)

---

## 4. RetroArch

- **M3U Usage:**
  
  - Supported by all CD-based cores. List filenames (relative or absolute) in M3U.
  
  - Can use command line or content browser to load the M3U file.

- **Disc Swapping:**
  
  - Open Quick Menu → Disk Control → Eject, select new index, Close Tray.
  
  - Hotkeys can be configured for next/prev disc.

- **Best Practices:**
  
  - Use relative paths in M3U when possible for portability.
  
  - Ensure file encoding is UTF-8 without BOM and use LF line endings.

- **Cores:**
  
  - Beetle PSX, Flycast, Genesis Plus GX, Picodrive, Beetle Saturn, Mednafen, etc.

**Links:**

- [RetroArch Official Docs - Disk Control](https://docs.libretro.com/guides/disk-control/)

- [Libretro Forums - M3U Multi-Disc](https://forums.libretro.com/t/m3u-file-support-for-multi-disc-games/10831)

- [RetroAchievements Wiki - Multi-Disc](https://docs.retroachievements.org/FAQ/#how-do-i-load-multi-disc-games)

---

## 5. EmulationStation (RetroPie, Recalbox, Batocera, etc.)

- **M3U Usage:**
  
  - List .m3u as allowed extension in es_systems.cfg. Remove/rename .cue/.chd/.iso extensions if needed.
  
  - Use subfolders or rename extra disc extensions (e.g., .cd2, .cd3) to hide individual discs.

- **Library:**
  
  - Only M3U files are shown in the game list when configured.

- **Disc Swapping:**
  
  - Handled by emulator after launch.

- **Metadata:**
  
  - Use scraping tools that support M3U (Skraper, Universal XML Scraper).
  
  - For manual edit, ensure and fields in gamelist.xml point to the M3U file.

**Links:**

- [RetroPie Docs - Multi-Disc Games](https://retropie.org.uk/docs/Playstation-1/#multi-disc-games)

- [ES Wiki - es_systems.cfg](https://retropie.org.uk/docs/EmulationStation/#es_systemscfg)

- [Universal XML Scraper](http://www.universalmediaserver.com/)

---

## 6. Pegasus Frontend

- **M3U Usage:**
  
  - M3U files work; Pegasus can also use metadata.pegasus.txt to group multi-disc games.
  
  - You may need to tweak the file scanner and extensions.

- **Grouping:**
  
  - Prefer defining multi-disc in metadata.pegasus.txt for advanced control.
  
  - Or, scan for only .m3u files for simple cases.

- **Disc Swapping:**
  
  - Use the emulator’s UI after game launch.

- **Metadata:**
  
  - Use Skyscraper or similar to generate correct metadata entries.

**Links:**

- [Pegasus Docs](https://pegasus-frontend.org/docs/)

- [Skyscraper Docs](https://github.com/muldjord/skyscraper)

- [Community Thread: Multi-Disc Support](https://github.com/mmatyas/pegasus-frontend/issues/503)

---

## 7. Simple Launcher

- **M3U Usage:**
  
  - Add .m3u to allowed file extensions for disc-based systems.
  
  - Prefer placing only M3U files in scanned folder to avoid duplicates.

- **Disc Swapping:**
  
  - Swapping is handled in emulator, not by Simple Launcher.

- **File Paths:**
  
  - Use relative or absolute paths in M3U as needed. Ensure emulator launch command passes the M3U path correctly.

- **Metadata:**
  
  - Manual. Uses game filename or artwork named after the M3U.

**Links:**

- [Simple Launcher Official Page](https://sirhenrythe5th.itch.io/simple-launcher)

- [Simple Launcher GitHub](https://github.com/SirHenrythe5th/Simple-Launcher)

---

## 8. Attract Mode

- **M3U Usage:**
  
  - Configure emulator for only .m3u extension for disc-based platforms.
  
  - Place M3U in ROM directory, discs in subfolders or exclude their extensions.

- **Romlists:**
  
  - Romlist should only reference M3U entries for multi-disc games.
  
  - You may need to manually clean up duplicates.

- **Disc Swapping:**
  
  - Emulator handles disc swapping.

- **Metadata:**
  
  - Display name comes from M3U filename or romlist edits.

**Links:**

- [Attract Mode Docs](http://attractmode.org/docs/Emulators.html)

- [Forum: Multi-Disc Games](http://forum.attractmode.org/index.php?topic=3057.0)

---

## 9. RetroFE

- **M3U Usage:**
  
  - Add .m3u to platform extension list. Only list M3U files in ROM directory.
  
  - Use semicolon-separated romlist to specify M3U as game file.

- **Disc Swapping:**
  
  - Handled by emulator UI.

- **Metadata:**
  
  - Name entries by game, not by disc.

**Links:**

- [RetroFE Docs](https://retrofe.com/docs/)

- [Community: Multi-Disc Discussion](https://retropie.org.uk/forum/topic/25439/retrofe-multi-disc-setup)

---

## 10. Playnite

- **M3U Usage:**
  
  - Prefer importing only .m3u files for multi-disc games.
  
  - Manually set game’s ROM/installation path to M3U file.
  
  - Can combine disc entries using Playnite’s “Merge Games” or “Additional Applications” for non-M3U emulators.

- **Emulator/Core:**
  
  - Ensure .m3u is a supported extension for the assigned emulator.
  
  - RetroArch, Mednafen, and DuckStation support launching via M3U.

- **Disc Swapping:**
  
  - Emulator UI only.

- **Metadata:**
  
  - Scrapes based on the M3U filename.

**Links:**

- [Playnite Docs](https://playnite.link/docs.html)

- [GitHub Issue: Multi-Disc Discussion](https://github.com/JosefNemec/Playnite/issues/159)

- [Playnite Forums - Multi-Disc](https://playnite.link/forum/thread-416.html)

---

## 11. General References

- [Libretro Docs - M3U Format](https://docs.libretro.com/guides/disk-control/)

- [Reddit: Multi-Disc Game Management](https://www.reddit.com/r/RetroPie/comments/5t5jdw/multi_disc_games_best_practices/)

- [No-Intro Naming Conventions](https://wiki.no-intro.org/index.php?title=Naming_Conventions)

- [LaunchBox M3U Guide (Community)](https://forums.launchbox-app.com/topic/59549-multi-disc-games-with-m3u/)

- [Skraper Wiki - M3U](https://www.skraper.net/)

- [RetroArch FAQ - Multi-Disc](https://docs.retroachievements.org/FAQ/#how-do-i-load-multi-disc-games)

---

**For AI-Based M3U Generation:**

- Detect and group files with “(Disc X)” or similar tags for each game.

- Output an M3U file named as the base game, listing disc files in order, with relative paths if possible.

- Place M3U in the folder to be scanned by the frontend; optionally move disc images to a subfolder to avoid duplicates.

- Ensure emulator configuration in each frontend includes .m3u as a supported extension.

- For systems/emulators not supporting M3U, recommend using “Additional Applications” (LaunchBox, Playnite) or manual swapping.

---

**End of Guide**
