# Consolidated Product Requirements Document (PRD) for RetroClamp

**Version:** 1.2.0
**Date:** 2025-05-03
**Author:** Claude 3.7 Sonnet

---

## 1. Purpose & Vision

RetroClamp is a modern, cross-platform GUI application that transforms the complex CHDMAN command-line utility into an intuitive, accessible interface. It enables users with varying levels of technical expertise to compress, decompress, and batch process disk images while preserving all the power and flexibility of the underlying CHDMAN tool.

### Core Value Proposition

RetroClamp bridges the gap between powerful command-line functionality and user-friendly design by:

- Centralizing compression workflows into a visually intuitive interface
- Providing comprehensive error handling and feedback
- Enabling batch processing with pause/resume capabilities
- Offering customizable themes with accessibility features
- Extending functionality with specialized tools for retro gaming

### Target Audience Spectrum

RetroClamp serves a range of users from casual gamers who need simple one-click solutions to archivists managing large collections with specific requirements. The interface progressively discloses advanced features, ensuring that basic operations remain simple while advanced capabilities are accessible when needed.

## 2. Scope

### Core Functionality

* **Compression/Decompression**: GUI interface for CHDMAN's createcd, createdvd, createhd, extract*, info, and verify operations
* **Archive Pre/Post-Processing**: Automatic extraction of compressed archives (.zip, .7z, .rar) before compression; optional re-archiving after decompression
* **Batch Processing**: Recursive folder scanning, drag-and-drop support, with pause/resume and checkpoint persistence
* **Logging and Feedback**: Real-time structured logs with level control and summary metrics
* **Theming**: QSS-based themes with contrast validation to meet WCAG-AA accessibility standards
* **Extensible Tools**: Framework for additional utilities (SCUMMVM generator, PS3 Wizard, DOS Launcher, etc.)

### Out of Scope

* Direct editing of CHD file contents (beyond metadata)
* Media playback or emulation capabilities
* Online database integration or network features (offline-first design)

## 3. Stakeholders & Personas

### Primary Stakeholders

* **Lead Developer**: Rene (Using Claude as AI coding assistant)
* **QA Engineers**: Responsible for testing and quality assurance
* **Documentation Writers**: Creating user guides and documentation
* **Open-Source Contributors**: Future community contributors

### User Personas

#### Casual Gamer

* **Technical Comfort Level**: 1-2 (Almost never uses command line)
* **Primary Goals**:
  * Drag and drop or browse to select archive files (ZIP/7z)
  * One-click 'Compress' to CHD for emulator compatibility
* **Pain Points**:
  * CLI-only CHDMAN with confusing flags and syntax
  * Lack of GUI progress feedback or error handling
* **Ideal Experience**: "Drop files → click 'Compress' → receive .chd outputs automatically"

#### Collector

* **Technical Comfort Level**: 3-5 (Comfortable with tools but avoids CLI)
* **Primary Goals**:
  * Batch compress large folders (500+ ROMs)
  * Run optional integrity checks after conversion
* **Pain Points**:
  * Manual decompress → compress flow consumes double storage space
  * Risk of running out of disk space with large temp files
* **Ideal Experience**: "Point to folder → app auto-extracts and converts one-by-one, deletes temp files, supports pause/resume and low-space alerts"

### Usage Scenarios

1. **Alice (Casual Gamer)**: Drags a folder of ISOs onto the window, selects 'Compress', and returns to find all .chd files ready.
2. **Bob (Collector)**: Resumes a paused batch job after reboot; checkpoint is restored and processing continues from where it left off.
3. **Charlie (Developer)**: Needs to batch convert a collection of ROMs with specific compression settings and generate reports for archival purposes.

## 4. Architecture Overview

### Project Structure

```
retroclamp/
├── .gitmodules                   # Tabler Icons submodule
│
├── config/                       # Configuration files
│   └── theme.json                # Theme parameters (source of truth)
│
├── core/                         # Core functionality modules
│   ├── chdman.py                 # CHDMAN wrapper (REQ-001–REQ-004)
│   ├── archive.py                # Zip/7z/unrar extraction logic
│   ├── file_scanner.py           # Batch scan & drag-drop support
│   ├── checkpoint.py             # Pause/resume state persistence
│   └── __init__.py
│
├── gui/                          # GUI components
│   ├── main_window.py            # Entry UI, tab container
│   ├── compression_tab.py        # Compress/Decompress interface
│   ├── metadata_tab.py           # CHD metadata viewer/editor
│   ├── tools_tab.py              # Tools plugin container
│   ├── theme_editor.py           # Theme Editor UI
│   └── widgets/                  # Reusable UI widgets
│
├── modules/                      # Shared helpers & utilities
│   ├── app_settings.py           # Persisted preferences
│   ├── theme_config.py           # Theme configuration loading
│   ├── theme_utils.py            # Contrast checks & validation
│   ├── ui_functions.py           # Dynamic QSS builder & icon loader
│   └── resources_rc.py           # Compiled Qt resource bindings
│
├── tools/                        # Standalone tools & wizards
│   ├── theme_studio.py           # Visual theme generator
│   ├── scummvm_generator.py      # SCUMMVM .scummvm file creator
│   ├── ps3_wizard.py             # PS3 game entry creator
│   ├── dos_launcher.py           # DOS launcher script generator
│   ├── folder_structure.py       # Frontend folder layout tool
│   ├── bios_checker.py           # BIOS presence/validation tool
│   ├── dat_validator.py          # DAT-file checksum & rename
│   └── cheat_installer.py        # Install emulator cheat files
│
├── resources/                    # Static assets
│   ├── icons/
│   │   └── tabler-icons/         # Git submodule
│   ├── icon.ico
│   └── resources.qrc             # Qt resource listing
│
├── themes/                       # Built-in QSS themes
│   ├── default.qss
│   └── dark.qss
│
├── tests/                        # Test suite
│   ├── test_chdman.py
│   ├── test_file_scanner.py
│   └── ...
│
├── main.py                       # Application entry point
└── ...
```

### Component Responsibilities

#### Core Modules (`core/`)

* Purpose: Backend functionality and processing logic without UI dependencies
* Key files:
  * `chdman.py`: Wrapper for CHDMAN CLI operations
  * `archive.py`: Archive extraction and compression logic
  * `file_scanner.py`: File system traversal and filtering
  * `checkpoint.py`: State persistence for pause/resume capability

#### GUI Layer (`gui/`)

* Purpose: User interface implementation using PySide6
* Key files:
  * `main_window.py`: Main application window and tab container
  * `compression_tab.py`: Primary interface for compression/extraction
  * `metadata_tab.py`: CHD metadata viewing and editing
  * `tools_tab.py`: Container for tool plugins
  * `theme_editor.py`: Interface for theme customization

#### Shared Helpers (`modules/`)

* Purpose: Common utilities used across multiple components
* Key files:
  * `app_settings.py`: Application preferences management
  * `theme_config.py`: Theme configuration loader
  * `theme_utils.py`: Contrast validation and accessibility checks
  * `ui_functions.py`: UI utility functions and dynamic styling

#### Standalone Tools (`tools/`)

* Purpose: Independent utilities that can run separately
* Key files:
  * `theme_studio.py`: Visual theme creator and editor
  * Various emulator-specific utilities (SCUMMVM, PS3, DOS, etc.)

## 5. Functional Requirements

### Compression and Extraction (REQ-001 to REQ-004)

* **REQ-001**: GUI-triggered CHDMAN compression for CD/DVD/HD images

  * Support for .cue/.bin, .iso, and raw image files
  * Configurable compression settings (algorithm, hunk size)
  * Progress indication with estimated time remaining

* **REQ-002**: GUI-triggered CHDMAN extraction with optional packaging

  * Extract CHD files back to original formats
  * Optional re-compression into standard archive formats

* **REQ-003**: Pre-process compressed archives for CHD conversion

  * Automatic extraction of .zip, .7z, and .rar archives
  * Smart detection of content type (CD, DVD, HD)

* **REQ-004**: Skip extraction for raw images

  * Direct processing of uncompressed files

### Batch Processing (REQ-005 to REQ-006)

* **REQ-005**: Batch folder processing with recursive option

  * Process entire directories of images
  * Toggle for recursive subdirectory scanning

* **REQ-006**: Drag-and-drop support

  * Accept files and folders via drag-and-drop
  * Visual feedback during drag operation

### Theming and UI (REQ-007 to REQ-008)

* **REQ-007**: QSS theme loading system

  * Load themes from config/theme.json
  * Dynamic application of themes without restart

* **REQ-008**: Theme Editor tab

  * Visual editor for theme customization
  * Real-time theme preview
  * Accessibility validation

### Advanced Features (REQ-009 to REQ-012)

* **REQ-009**: Smart CHDMAN parameter presets

  * Optimized default settings for different media types

* **REQ-010**: Custom compression profiles

  * Save and load user-defined parameter sets

* **REQ-011**: Real-time logging pane

  * Structured logs with filtering by level
  * Log export capability

* **REQ-012**: Pause/resume/cancel with checkpointing

  * Save state for interrupted operations
  * Resume from last successful operation

### Tools and Extensions (REQ-013 to REQ-023)

* **REQ-013**: Metadata viewer/editor tab

  * View and modify CHD metadata

* **REQ-014+**: Extensible tools tab with plugins

  * SCUMMVM generator
  * PS3 wizard
  * DOS launcher
  * BIOS checker
  * DAT validator
  * Etc.

## 6. Non-Functional Requirements

### Performance (NFR-001 to NFR-003)

* **NFR-001**: UI launch time under 2 seconds

  * Lazy-load modules not needed at startup
  * Optimize resource loading

* **NFR-002**: Heavy operations off the main thread

  * UI CPU usage under 10% during operations
  * Responsive interface during processing

* **NFR-003**: Lazy loading and caching of metadata

  * On-demand loading of detailed information

### Usability (NFR-004 to NFR-005)

* **NFR-004**: Scoped file scanning

  * Filter by extension
  * Respect recursion settings

* **NFR-005**: Robust error handling with user guidance

  * Clear error messages
  * Suggested actions for recovery

### Maintainability (NFR-006 to NFR-008)

* **NFR-006**: Persist settings in JSON format

  * Human-readable configuration
  * Easy backup and transfer

* **NFR-007**: Internationalization support

  * RTL layout support
  * Locale-aware formatting

* **NFR-008**: Lifecycle management

  * Update checks
  * Graceful shutdown
  * Crash recovery

### Accessibility

* **A11Y-001**: WCAG-AA contrast compliance

  * Ensure sufficient contrast ratios
  * Validate with theme_utils.py

* **A11Y-002**: Keyboard navigation

  * Full keyboard control of all features

* **A11Y-003**: Screen reader compatibility

  * Proper labels and ARIA attributes

## 7. UI/UX Design Guidelines

### Design Principles

* **Consistency**: Uniform visual elements, layout, and behavior

  * Consistent color schemes and typography
  * Uniform placement of navigation and controls
  * Standardized interaction patterns

* **Simplicity**: Focus on essential elements and clear workflows

  * Remove unnecessary UI elements
  * Use clear labels and straightforward language
  * Implement progressive disclosure for advanced options

* **Feedback**: Provide clear information about system state and user actions

  * Visual cues for interactive elements
  * Status indicators for ongoing processes
  * Clear messaging for action results

### Visual Design

* **Theme**: Dracula-inspired dark theme with light theme alternative
* **Icons**: Tabler Icons for consistent, modern appearance
* **Layout**: Fixed margins and spacing for visual consistency
* **Typography**: Clear, readable fonts with appropriate sizing

### Interaction Design

* **Hover states**: Visual feedback on mouse hover
* **Progress indicators**: For long-running operations
* **Drag-and-drop**: Visual feedback during drag operations
* **Keyboard shortcuts**: For common operations

## 8. CHDMAN Integration

### Core Functionality

The RetroClamp application will wrap the CHDMAN command-line utility to provide GUI access to its functionality. The `core/chdman.py` module will be responsible for:

* Executing CHDMAN commands with appropriate parameters
* Capturing and parsing command output
* Reporting progress and results to the GUI

### Supported CHDMAN Commands

* **createcd**: Create CHD from CD image (.cue/.bin, .iso)
* **createdvd**: Create CHD from DVD image (.iso)
* **createhd**: Create CHD from raw disk image
* **extractcd**: Extract CHD back to CD image format
* **extractdvd**: Extract CHD back to DVD image format
* **extractraw**: Extract CHD back to raw disk image
* **info**: Display CHD information
* **verify**: Verify CHD integrity

### Command Execution Pattern

```python
def execute_chdman_command(
    command: str,
    input_file: str,
    output_file: str = None,
    compression: str = None,
    hunk_size: int = None,
    force: bool = False,
    verbose: bool = True,
    **kwargs
) -> subprocess.Popen:
    """Execute a CHDMAN command with the specified parameters.

    Args:
        command: CHDMAN command to execute (e.g., 'createcd', 'info')
        input_file: Path to the input file
        output_file: Path to the output file (if applicable)
        compression: Compression algorithm(s) to use (if applicable)
        hunk_size: Hunk size in bytes (if applicable)
        force: Whether to force overwrite of output file
        verbose: Whether to enable verbose output
        **kwargs: Additional command-specific parameters

    Returns:
        subprocess.Popen object for monitoring the process
    """
    # Implementation
```

### Progress Monitoring

```python
def monitor_progress(process: subprocess.Popen, callback: Callable[[float, str], None]) -> None:
    """Monitor the progress of a CHDMAN operation.

    Args:
        process: The subprocess.Popen object to monitor
        callback: Function to call with progress updates (percent, message)
    """
    # Implementation
```

## 9. Logging and Error Handling

### Logging Strategy

* **Structured Logging**: JSON or key=value format with timestamp, level, module, message
* **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
* **Persistence**: Rotate logs daily or at 50 MB; purge after 7 days
* **UI Integration**: Log pane with controls to pause, clear, save; filter by level

### Error Handling

* **User-Facing Errors**: Clear messages with suggested actions
* **System Errors**: Detailed logging with stack traces (hidden from user)
* **Recovery Mechanisms**: Automatic retry for transient errors
* **Graceful Degradation**: Maintain basic functionality when advanced features fail

## 10. Testing Strategy

### Unit Testing

* **Coverage Target**: ≥80% code coverage
* **Framework**: pytest
* **Key Test Areas**:
  * CHDMAN wrapper (`core/chdman.py`)
  * Archive handling (`core/archive.py`)
  * File scanning (`core/file_scanner.py`)
  * Theme utilities (`modules/theme_utils.py`)
  * UI functions (`modules/ui_functions.py`)

### Integration Testing

* **Approach**: GUI automation for end-to-end workflows
* **Key Scenarios**:
  * Compression workflow
  * Extraction workflow
  * Batch processing
  * Pause/resume functionality

### Performance Testing

* **Metrics**:
  * Startup time (target: <2 seconds)
  * Scanning speed (target: >1000 files/second)
  * UI responsiveness during operations
  * Memory usage (target: <512 MB on startup)

### Acceptance Testing

* **Criteria**:
  * User scenarios successfully completed
  * Functionality meets requirements
  * UI/UX meets design guidelines
  * Accessibility standards met

## 11. Implementation Guidelines for Claude

This section provides specific guidance for Claude as the AI coding assistant responsible for implementing RetroClamp.

### Code Style and Standards

* Follow PEP 8 for Python code style
* Use Google-style docstrings for all functions and classes
* Include type hints for all parameters and return values
* Ensure all code passes Black formatting and Ruff linting
* Maintain test coverage of at least 80%

### Core Module Implementation Pattern

```python
"""Module docstring explaining purpose."""
from typing import Dict, List, Optional, Union, Any
# Standard library imports
import os
import sys
# Third-party imports
import PySide6.QtCore as QtCore
# Local imports
from modules.app_settings import AppSettings

class CoreClassName:
    """Class docstring with purpose and usage example.

    Attributes:
        attr_name: Description of attribute
    """

    def __init__(self, param1: str, param2: Optional[int] = None) -> None:
        """Initialize the class.

        Args:
            param1: Description of param1
            param2: Description of param2, defaults to None
        """
        self.param1 = param1
        self.param2 = param2 or 0

    def method_name(self, arg1: str) -> bool:
        """Method docstring with purpose.

        Args:
            arg1: Description of arg1

        Returns:
            Description of return value

        Raises:
            ValueError: When arg1 is invalid
        """
        # Implementation
        return True
```

### GUI Module Implementation Pattern

```python
"""Module docstring explaining purpose."""
from typing import Dict, List, Optional, Union, Any
# Standard library imports
import os
# PySide6 imports
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel
)
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QIcon
# Local imports
from modules.ui_functions import load_svg_icon
from modules.theme_utils import apply_theme

class TabWidget(QWidget):
    """Class docstring with purpose and usage example.

    Signals:
        operation_completed: Emitted when operation finishes
    """
    operation_completed = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the widget.

        Args:
            parent: Parent widget, defaults to None
        """
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self) -> None:
        """Set up the user interface components."""
        self.layout = QVBoxLayout(self)
        # UI setup code

    def connect_signals(self) -> None:
        """Connect widget signals to slots."""
        # Signal connections

    @Slot()
    def on_button_clicked(self) -> None:
        """Handle button click event."""
        # Implementation
        self.operation_completed.emit(True)
```

### Test Module Implementation Pattern

```python
"""Tests for module_name module."""
import pytest
from unittest.mock import MagicMock, patch
# Import module to test
from core.module_name import ClassName

def test_method_success():
    """Test method_name succeeds with valid input."""
    # Arrange
    obj = ClassName("valid_param")

    # Act
    result = obj.method_name("valid_arg")

    # Assert
    assert result is True

def test_method_failure():
    """Test method_name fails with invalid input."""
    # Arrange
    obj = ClassName("valid_param")

    # Act/Assert
    with pytest.raises(ValueError):
        obj.method_name("")
```

### CHDMAN Wrapper Implementation

The `core/chdman.py` module should:

* Provide a class-based interface to CHDMAN commands
* Handle command execution and output parsing
* Support progress monitoring and cancellation
* Implement error handling and recovery

```python
class CHDMan:
    """Wrapper for the CHDMAN command-line utility.

    Provides a Pythonic interface to CHDMAN operations including
    compression, extraction, verification, and information retrieval.
    """

    def __init__(self, executable_path: str = "chdman"):
        """Initialize the CHDMan wrapper.

        Args:
            executable_path: Path to the CHDMAN executable
        """
        self.executable_path = executable_path

    def create_cd(self, input_file: str, output_file: str,
                  compression: Optional[str] = None,
                  hunk_size: Optional[int] = None,
                  force: bool = False,
                  progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """Create a CHD file from a CD image.

        Args:
            input_file: Path to the input .cue or .iso file
            output_file: Path for the output .chd file
            compression: Compression algorithm(s) to use
            hunk_size: Size of data hunks in bytes
            force: Whether to overwrite existing output file
            progress_callback: Function to call with progress updates

        Returns:
            True if successful, False otherwise

        Raises:
            FileNotFoundError: If input file doesn't exist
            RuntimeError: If CHDMAN operation fails
        """
        # Implementation
```

### Theme Configuration Implementation

The theme system should:

* Load theme configuration from JSON files
* Generate QSS stylesheets dynamically
* Validate color contrast for accessibility
* Support switching themes at runtime

```python
def load_theme_config(theme_name: str = "default") -> Dict[str, Any]:
    """Load theme configuration from JSON file.

    Args:
        theme_name: Name of theme to load

    Returns:
        Dictionary containing theme configuration
    """
    # Implementation

def generate_qss(theme_config: Dict[str, Any]) -> str:
    """Generate QSS stylesheet from theme configuration.

    Args:
        theme_config: Theme configuration dictionary

    Returns:
        QSS stylesheet as string
    """
    # Implementation

def validate_contrast(foreground: str, background: str) -> Tuple[float, bool]:
    """Validate contrast ratio between colors.

    Args:
        foreground: Foreground color in hex format
        background: Background color in hex format

    Returns:
        Tuple of (contrast_ratio, meets_wcag_aa)
    """
    # Implementation
```

## 12. Timeline and Milestones

### Phase 1 (4 weeks): Core Functionality

* Basic application structure and scaffold
* CHDMAN wrapper implementation
* Compression/decompression UI
* Basic logging pane
* Unit tests for core functionality

### Phase 2 (4 weeks): Batch Processing

* Batch file processing
* Archive pre/post-processing
* Checkpoint system for pause/resume
* File scanner with recursion
* Drag-and-drop support

### Phase 3 (4 weeks): Tools Tab

* Tools tab infrastructure
* SCUMMVM generator
* PS3 wizard implementation
* Metadata viewer/editor
* Additional tool plugins

### Phase 4 (4 weeks): Refinement

* Theming system with editor
* Internationalization
* Accessibility improvements
* Documentation and polish
* Final QA and testing

## 13. Success Metrics

### Technical Metrics

* **Test Coverage**: ≥80%
* **Startup Time**: ≤2 seconds
* **Batch Failure Rate**: ≤1%
* **Memory Footprint**: ≤512 MB on startup
* **CPU Usage**: Background tasks ≤10% CPU

### User Experience Metrics

* **User Satisfaction**: ≥4.5/5 in user testing
* **Task Completion Rate**: ≥95% for common tasks
* **Time-to-Value**: First compression completed in ≤60 seconds from app launch for new users

## 14. Conclusion

RetroClamp aims to combine the power of CHDMAN with an intuitive, accessible interface that serves users across the technical expertise spectrum. By focusing on core user needs while providing depth through progressive disclosure, the application will simplify the management of disk images for emulation and archival purposes.

The implementation will follow software engineering best practices, with a modular architecture, comprehensive testing, and attention to performance and accessibility. Claude, as the AI coding assistant, will implement the codebase according to the patterns and guidelines specified in this document.
