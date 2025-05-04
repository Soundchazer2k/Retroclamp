# RetroClamp

A modern GUI for CHDMAN operations, allowing you to compress, decompress, and manage disk images with ease.

## Current Status

- **Version 1.0.0**: Basic GUI implementation complete with modern interface and theme system
- **Version 1.1.0-dev**: Currently implementing CHDMAN integration and batch processing

See the [CHANGELOG.md](CHANGELOG.md) for detailed version history and the [ROADMAP.md](docs/ROADMAP.md) for development plans.

## Features

- **Compression**: Convert disk images (ISO, BIN, IMG, etc.) to CHD format for efficient storage
- **Extraction**: Extract disk images from CHD files to various formats
- **Batch Processing**: Process multiple files in batch mode
- **Tool Plugins**: Extensible plugin system for additional tools
- **Dynamic Theming**: Customizable themes with accessibility validation
- **Modern UI**: Clean, responsive interface built with PySide6 (Qt)

## Requirements

- Python 3.8+
- PySide6
- CHDMAN executable (part of MAME)

## Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the setup script: `setup_chdman.bat` (Windows) or `./setup_chdman.sh` (Linux/macOS)
4. Copy the CHDMAN executable to the `bin` directory
5. Run the application: `python main.py`

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/retroclamp.git
   cd retroclamp
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```
   
   Or use the provided batch file:
   ```
   run_retroclamp.bat
   ```

## Project Structure

- `core/`: Core functionality modules
  - `chdman.py`: CHDMAN wrapper for compression/extraction
  - `archive.py`: Archive handling (ZIP, 7z, RAR)
  - `file_scanner.py`: File scanning and filtering
  - `checkpoint.py`: Checkpoint system for pause/resume
- `gui/`: GUI components
  - `home_tab.py`: Home screen
  - `compression_tab.py`: Compression interface
  - `extraction_tab.py`: Extraction interface
  - `theme_tab.py`: Theme customization
  - `settings_tab.py`: Application settings
- `modules/`: Shared modules
  - `theme_config.py`: Theme configuration
  - `theme_utils.py`: Theme utilities
  - `ui_functions.py`: UI functions
  - `app_settings.py`: Settings management
- `tools/`: Plugin system and tools
  - `__init__.py`: Plugin manager
  - `scummvm_generator.py`: SCUMMVM configuration generator
- `config/`: Configuration files
  - `theme.json`: Default theme
  - `theme_light.json`: Light theme
- `resources/`: Resources like icons

## Creating Plugins

RetroClamp supports a plugin system for adding new tools. To create a plugin:

1. Create a new Python file in the `tools/` directory
2. Define the following metadata variables:
   ```python
   PLUGIN_NAME = "Your Plugin Name"
   PLUGIN_DESCRIPTION = "Description of your plugin"
   PLUGIN_VERSION = "1.0.0"
   PLUGIN_AUTHOR = "Your Name"
   ```
3. Implement a `register_tab` function that takes a parent widget and adds your tool's UI to it

See `tools/scummvm_generator.py` for an example.

## License

MIT

## Acknowledgments

- [CHDMAN](https://docs.mamedev.org/tools/chdman.html) - The compression/extraction tool
- [PyDracula](https://github.com/Wanderson-Magalhaes/Modern_GUI_PyDracula_PySide6_or_PyQt6) - UI design inspiration
- [Tabler Icons](https://tabler-icons.io/) - Icons used in the application
- [namDHC and Tools-CHD](https://github.com/farmerbb/namerica-dhc) - CLI inspiration
- [RetroBat](https://www.retrobat.org/), [Batocera](https://batocera.org/), and [Libretro](https://www.libretro.com/) - UX flow inspiration
