# RetroClamp Changelog

## [1.2.1-dev] - Development Version

### Fixed
- **Critical:** Fixed `AttributeError` crash when clicking the Batch button on the Home screen. The `self.batch_page` reference was stale after the batch tab was refactored into the Compression page as a sub-tab. Navigation now correctly opens the Compression page and selects the Batch Processing tab (`main.py`).
- **Bug:** Fixed `human_readable_size()` in `utils.py` formatting the original byte value instead of the scaled value, which produced wildly incorrect output (e.g. `"1610612736.00 GB"` instead of `"1.50 GB"`).
- **CI:** Removed `|| true` from the `pytest` call in `python-app.yml`, so test failures now correctly fail the build and the badge reflects real status.
- **Performance:** Eliminated redundant double `os.walk()` pass in `DiskImageScanWorker` (`file_scanner.py`). Directory trees were previously walked twice — once to count files, once to scan — now done in a single pass.
- **Logging:** Replaced all direct `open("error.log", "a")` writes in `file_scanner.py` and `gui/compression_tab.py` with proper `logging` module calls. The old approach hard-coded a relative file path and bypassed log-level filtering.
- **Version string:** `main.py` was hard-coded to report version `"1.0.0"`. It now reads from `version.__version__` so the reported version stays in sync.
- **UI:** Removed duplicated `padding-left: 16px;` property from all seven nav button stylesheets in `main.py`.
- **UI:** Fixed sidebar toggle mid-animation edge case. The collapse/expand decision now uses a midpoint threshold instead of an exact width equality check, so rapid clicks during animation behave correctly.
- **Dependencies:** Added `rarfile>=4.0` to `requirements.txt` (was imported in `batch_tab.py` but not declared).
- **Docs:** Merged duplicate Installation section in `README.md` into a single clear numbered list.
- **Repo hygiene:** Removed stale development artifacts from the repository (`compression_tab.py.fixed`, `compression_tab_backup_before_async_patch.py`, `fix_indentation.py`, `focused_analysis.py`, `retroclamp_analyzer.py`, `analysis_report.json`, `bandit_report.txt`). Added corresponding patterns to `.gitignore` to prevent recurrence.

### Changed
- Version bumped from `1.2.0` to `1.2.1-dev` to mark this bugfix development cycle.

## [1.2.0-dev] - Development Version

### In Progress
- Enhanced batch processing capabilities
- Improved error handling for large batches
- Multi-threading optimizations for batch operations
- Better progress reporting for batch tasks

## [1.1.0] - 2025-05-11

### Added
- CHDMAN executable integration in bin directory
- CHDManager batch processing functionality
- Command-line batch processor tool
- Setup script for CHDMAN installation
- Intelligent disc image selection that prioritizes .cue files over .bin files
- Proper tracking of active workers using the `active_workers` list
- Overall progress bar showing average completion across all tasks

### Fixed
- Permission error handling for output directories
- String decoding issues in process output handling
- Missing progress bar in CompressionTab UI
- Misleading "ERROR:" prefixes in normal progress messages
- Duplicate method definitions in CompressionTab class
- Proper handling of .cue/.bin file pairs to ensure only one task per disc

## [1.0.0] - 2025-05-04

### Added
- Modern GUI with PySide6
- Dracula-inspired dark theme
- Navigation sidebar with collapsible menu
- Home screen with feature cards
- Custom resize handle with SVG icon
- Theme configuration system
- Icon loading system with Tabler Icons
- Application settings persistence

### Changed
- Improved window resizing behavior
- Enhanced UI responsiveness

### Fixed
- Window close event handling
- Resize handle positioning
