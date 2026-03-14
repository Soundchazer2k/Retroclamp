# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Installation
- `make install` - Install production dependencies
- `make dev-install` - Install dev dependencies + pre-commit hooks

### Core Development Commands
- `make run` - Run the application (python main.py)
- `make test` - Run tests with coverage reporting
- `make lint` - Run all linting (pre-commit run --all-files)
- `make format` - Format code with black and isort
- `make security` - Run security checks with bandit and safety
- `make analyze` - Run code analysis with retroclamp_analyzer.py
- `make clean` - Clean generated files

### Testing
- Primary framework: pytest with pytest-qt for GUI testing
- Test structure: `tests/core/` for backend, `tests/plugins/` for plugin system
- Individual test: `pytest tests/test_specific_file.py`
- Coverage reports include missing line identification

## Architecture Overview

**RetroClamp** is a PySide6 GUI application for CHDMAN operations with advanced batch processing capabilities and a professional layered theming system.

### Key Design Patterns
- **Worker-Manager Pattern**: Threaded operations using QRunnable workers
- **Signal-Driven Communication**: Qt signals for async progress reporting
- **Singleton Pattern**: Thread-safe managers (CHDManager, ArchiveManager)
- **Module Separation**: Clear backend/frontend separation

### Core Threading Model
- **QThreadPool**: Manages parallel worker threads
- **CHDManWorker**: Individual CHDMAN operations with real-time stdout/stderr parsing
- **BatchProcessor**: Coordinates multi-file operations with checkpoint management
- **Worker Deduplication**: Prevents duplicate operations in queue

### Project Structure
```
core/                   # Backend processing logic
├── chdman.py          # CHDMAN wrapper & threading system
├── batch_processor.py # Batch operations with resume capability
├── archive.py         # Multi-format archive extraction
├── file_scanner.py    # File discovery and filtering
└── debug_logger.py    # Comprehensive logging system

gui/                    # User interface components
├── *_tab.py          # Individual tab implementations
└── theme_*.py        # Dynamic theming system

modules/                # Supporting utilities
├── app_settings.py    # Centralized settings management
└── theme_config.py    # Theme system configuration
```

### Signal Architecture
- **CHDManSignals**: Core operation events (progress, completion, error)
- **BatchSignals**: Batch-level coordination with ETA calculations
- **ArchiveSignals**: Archive extraction status updates

### Advanced Features
- **Console-Specific Profiles**: Optimized compression settings for PS1, PS2, Dreamcast, etc.
- **Archive Integration**: Seamless ZIP/7z/RAR extraction before compression
- **Plugin System**: Extensible tools (ScummVM generator in `tools/`)
- **Checkpoint Management**: Resume-capable batch operations
- **Process Monitoring**: Dual execution paths (subprocess.Popen vs QProcess)

## Code Quality Setup

### Tools Configuration (pyproject.toml)
- **Black**: Line length 88, string normalization
- **Isort**: Black profile compatibility
- **Ruff**: Comprehensive rule set with specific ignores
- **Mypy**: Type checking with missing imports ignored
- **Pytest**: Coverage reporting with branch analysis

### Pre-commit Hooks
- Code formatting enforcement
- Security scanning with bandit
- Type checking validation
- YAML syntax validation
- Custom CHDMAN security checks

## Important Implementation Notes

### Threading Safety
- All managers use thread-safe patterns
- Qt signals handle cross-thread communication
- Worker deduplication prevents race conditions
- Process monitoring uses structured exception handling

### Error Handling
- Custom exception hierarchy for different operation types
- Signal-based error propagation for thread safety
- Graceful degradation in batch operations
- Exponential backoff for retry mechanisms

### Dependencies
- PySide6 for GUI framework
- QDarkStyleSheet for professional theming
- QtAwesome for modern icons
- py7zr and patool for archive support
- rich for enhanced console output
- pyinstaller for packaging

### Theming System
- **Base**: QDarkStyleSheet (professional foundation)
- **Overlay**: custom_overlay.qss (RetroClamp branding)
- **Colors**: Dracula-inspired palette with purple accents
- **Components**: Enhanced buttons, inputs, navigation, and dialogs
- **Fallbacks**: Graceful degradation if theming libraries unavailable

## Testing Strategy
- GUI components tested with pytest-qt
- Core modules have comprehensive unit tests
- Integration tests for end-to-end workflows
- Plugin API compliance validation
- Security scanning integrated into CI pipeline
