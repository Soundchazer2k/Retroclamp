"""Application settings module for RetroClamp.

This module provides functionality for managing application settings and preferences,
including loading, saving, and accessing settings values.
"""

import json
from typing import Dict, Any, Optional

from PySide6.QtCore import QObject, Signal, QSettings


class AppSettingsSignals(QObject):
    """Signals for application settings operations.
    
    Signals:
        loaded: Emitted when settings are loaded
        saved: Emitted when settings are saved
        changed: Emitted when a setting is changed
        error: Emitted when an error occurs
    """
    loaded = Signal()
    saved = Signal()
    changed = Signal(str, object)  # Setting key, new value
    error = Signal(str)  # Error message


class AppSettings:
    """Manager for application settings and preferences.
    
    This class provides functionality for managing application settings using QSettings,
    with support for default values and type conversion.
    """
    
    # Default settings
    DEFAULT_SETTINGS = {
        # General settings
        "general": {
            "theme": "dracula",
            "language": "en",
            "check_updates": True,
            "confirm_exit": True,
            "save_window_state": True,
            "show_tooltips": True,
        },
        # Compression settings
        "compression": {
            "default_algorithm": "zstd",
            "default_hunk_size": 4096,
            "verify_after_compression": True,
            "delete_source_after_compression": False,
            "overwrite_existing": False,
            "use_temp_directory": True,
            "temp_directory": "",  # Empty means use system temp
        },
        # Extraction settings
        "extraction": {
            "create_subdirectory": True,
            "overwrite_existing": False,
            "delete_source_after_extraction": False,
        },
        # Batch processing settings
        "batch": {
            "recursive_scan": True,
            "max_concurrent_jobs": 1,
            "auto_pause_on_low_disk": True,
            "low_disk_threshold_gb": 5,
            "save_checkpoint_interval": 5,  # minutes
        },
        # File types settings
        "file_types": {
            "cd_extensions": [".cue", ".bin", ".iso", ".img", ".cdr"],
            "dvd_extensions": [".iso", ".img"],
            "hd_extensions": [".vhd", ".vmdk", ".img", ".raw"],
            "archive_extensions": [".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"],
        },
        # Paths settings
        "paths": {
            "chdman_path": "chdman",  # Default assumes in PATH
            "last_input_directory": "",
            "last_output_directory": "",
            "recent_files": [],
            "recent_directories": [],
        },
        # Tools settings
        "tools": {
            "enabled_tools": ["scummvm_generator", "ps3_wizard", "dos_launcher"],
            "tool_settings": {},  # Tool-specific settings
        },
        # Advanced settings
        "advanced": {
            "log_level": "INFO",
            "max_log_size_mb": 10,
            "max_log_files": 5,
            "enable_experimental": False,
            "custom_parameters": "",
        },
    }
    
    def __init__(self):
        """Initialize the AppSettings."""
        self.signals = AppSettingsSignals()
        
        # Initialize QSettings
        self.qsettings = QSettings("RetroClamp", "RetroClamp")
        
        # Initialize settings dictionary
        self.settings = {}
        
        # Load settings
        self.load_settings()
    
    def load_settings(self) -> None:
        """Load settings from QSettings."""
        try:
            # Start with default settings
            self.settings = self._deep_copy_dict(self.DEFAULT_SETTINGS)
            
            # Load settings from QSettings
            for category in self.settings.keys():
                self.qsettings.beginGroup(category)
                for key in self.settings[category].keys():
                    if self.qsettings.contains(key):
                        value = self.qsettings.value(key, self.settings[category][key])
                        
                        # Convert value to the correct type based on default
                        default_value = self.settings[category][key]
                        if isinstance(default_value, bool):
                            # Handle boolean conversion (QSettings stores as string)
                            if isinstance(value, str):
                                value = value.lower() in ["true", "1", "yes"]
                            else:
                                value = bool(value)
                        elif isinstance(default_value, int):
                            value = int(value)
                        elif isinstance(default_value, float):
                            value = float(value)
                        elif isinstance(default_value, list):
                            # Handle list conversion
                            if isinstance(value, str):
                                value = json.loads(value)
                            
                        self.settings[category][key] = value
                self.qsettings.endGroup()
            
            self.signals.loaded.emit()
        except Exception as e:
            self.signals.error.emit(f"Error loading settings: {str(e)}")
            # Fallback to default settings
            self.settings = self._deep_copy_dict(self.DEFAULT_SETTINGS)
    
    def save_settings(self) -> None:
        """Save settings to QSettings."""
        try:
            # Save settings to QSettings
            for category, category_settings in self.settings.items():
                self.qsettings.beginGroup(category)
                for key, value in category_settings.items():
                    # Convert lists to JSON strings for storage
                    if isinstance(value, list):
                        value = json.dumps(value)
                    self.qsettings.setValue(key, value)
                self.qsettings.endGroup()
            
            self.qsettings.sync()
            self.signals.saved.emit()
        except Exception as e:
            self.signals.error.emit(f"Error saving settings: {str(e)}")
    
    def get(self, category: str, key: str, default: Any = None) -> Any:
        """Get a setting value.
        
        Args:
            category: Setting category
            key: Setting key
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value or default
        """
        if category in self.settings and key in self.settings[category]:
            return self.settings[category][key]
        return default
    
    def set(self, category: str, key: str, value: Any) -> None:
        """Set a setting value.
        
        Args:
            category: Setting category
            key: Setting key
            value: Setting value
        """
        # Ensure category exists
        if category not in self.settings:
            self.settings[category] = {}
        
        # Set the value
        self.settings[category][key] = value
        
        # Emit signal
        self.signals.changed.emit(f"{category}.{key}", value)
    
    def reset(self, category: Optional[str] = None, key: Optional[str] = None) -> None:
        """Reset settings to default values.
        
        Args:
            category: Category to reset (all if None)
            key: Key to reset (all in category if None)
        """
        if category is None:
            # Reset all settings
            self.settings = self._deep_copy_dict(self.DEFAULT_SETTINGS)
        elif category in self.settings:
            if key is None:
                # Reset entire category
                self.settings[category] = self._deep_copy_dict(self.DEFAULT_SETTINGS[category])
            elif key in self.settings[category]:
                # Reset specific key
                self.settings[category][key] = self.DEFAULT_SETTINGS[category][key]
    
    def add_recent_file(self, file_path: str, max_items: int = 10) -> None:
        """Add a file to the recent files list.
        
        Args:
            file_path: Path to the file
            max_items: Maximum number of items in the list
        """
        recent_files = self.get("paths", "recent_files", [])
        
        # Remove if already exists
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        # Add to the beginning
        recent_files.insert(0, file_path)
        
        # Limit the list size
        recent_files = recent_files[:max_items]
        
        # Update setting
        self.set("paths", "recent_files", recent_files)
    
    def add_recent_directory(self, directory_path: str, max_items: int = 10) -> None:
        """Add a directory to the recent directories list.
        
        Args:
            directory_path: Path to the directory
            max_items: Maximum number of items in the list
        """
        recent_directories = self.get("paths", "recent_directories", [])
        
        # Remove if already exists
        if directory_path in recent_directories:
            recent_directories.remove(directory_path)
        
        # Add to the beginning
        recent_directories.insert(0, directory_path)
        
        # Limit the list size
        recent_directories = recent_directories[:max_items]
        
        # Update setting
        self.set("paths", "recent_directories", recent_directories)
    
    def get_tool_setting(self, tool_name: str, key: str, default: Any = None) -> Any:
        """Get a tool-specific setting.
        
        Args:
            tool_name: Name of the tool
            key: Setting key
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value or default
        """
        tool_settings = self.get("tools", "tool_settings", {})
        
        if tool_name in tool_settings and key in tool_settings[tool_name]:
            return tool_settings[tool_name][key]
        
        return default
    
    def set_tool_setting(self, tool_name: str, key: str, value: Any) -> None:
        """Set a tool-specific setting.
        
        Args:
            tool_name: Name of the tool
            key: Setting key
            value: Setting value
        """
        tool_settings = self.get("tools", "tool_settings", {})
        
        # Ensure tool exists in settings
        if tool_name not in tool_settings:
            tool_settings[tool_name] = {}
        
        # Set the value
        tool_settings[tool_name][key] = value
        
        # Update setting
        self.set("tools", "tool_settings", tool_settings)
    
    def export_settings(self, file_path: str) -> bool:
        """Export settings to a JSON file.
        
        Args:
            file_path: Path to the output file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            self.signals.error.emit(f"Error exporting settings: {str(e)}")
            return False
    
    def import_settings(self, file_path: str) -> bool:
        """Import settings from a JSON file.
        
        Args:
            file_path: Path to the input file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                imported_settings = json.load(f)
            
            # Validate and merge settings
            for category, category_settings in imported_settings.items():
                if category in self.settings:
                    for key, value in category_settings.items():
                        if key in self.settings[category]:
                            # Ensure type compatibility
                            default_value = self.settings[category][key]
                            if isinstance(default_value, bool) and not isinstance(value, bool):
                                value = value.lower() in ["true", "1", "yes"] if isinstance(value, str) else bool(value)
                            elif isinstance(default_value, int) and not isinstance(value, int):
                                value = int(value)
                            elif isinstance(default_value, float) and not isinstance(value, float):
                                value = float(value)
                            
                            self.settings[category][key] = value
            
            # Save the imported settings
            self.save_settings()
            self.signals.loaded.emit()
            
            return True
        except Exception as e:
            self.signals.error.emit(f"Error importing settings: {str(e)}")
            return False
    
    @staticmethod
    def _deep_copy_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of a dictionary.
        
        Args:
            d: Dictionary to copy
            
        Returns:
            Deep copy of the dictionary
        """
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = AppSettings._deep_copy_dict(value)
            elif isinstance(value, list):
                result[key] = value.copy()
            else:
                result[key] = value
        return result
