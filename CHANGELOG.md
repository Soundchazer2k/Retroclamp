# RetroClamp Changelog

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
