"""Theme Manager for RetroClamp.

Handles theme selection, system theme detection, and dynamic theme switching
across different platforms with proper fallbacks.
"""

import os
from enum import Enum
from typing import Dict

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication


class ThemeType(Enum):
    """Available theme types."""

    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


class ThemeManager(QObject):
    """Manages application theming with cross-platform support."""

    # Signal emitted when theme changes
    theme_changed = Signal(str)  # theme_name

    def __init__(self):
        """Initialize the theme manager."""
        super().__init__()
        self.settings = QSettings("RetroClamp", "RetroClamp")
        self.current_theme = ThemeType.DARK
        self.base_stylesheets = {}
        self.custom_overlays = {}

        # Load available themes
        self._load_theme_definitions()

        # Detect system theme capability
        self.system_theme_supported = self._check_system_theme_support()

    def _load_theme_definitions(self):
        """Load theme stylesheet definitions."""
        self.base_stylesheets = {
            ThemeType.DARK: self._get_dark_stylesheet,
            ThemeType.LIGHT: self._get_light_stylesheet,
            ThemeType.SYSTEM: self._get_system_stylesheet,
        }

        self.custom_overlays = {
            ThemeType.DARK: "custom_overlay.qss",
            ThemeType.LIGHT: "light_overlay.qss",
            ThemeType.SYSTEM: None,  # Will be determined dynamically
        }

    def _check_system_theme_support(self) -> bool:
        """Check if system theme detection is supported on this platform."""
        try:
            # Try to access system palette
            palette = QApplication.palette()
            # Check if we can detect dark mode
            window_color = palette.color(QPalette.ColorRole.Window)
            return bool(window_color.lightness() < 128)  # Basic detection
        except Exception:
            return False

    def _get_dark_stylesheet(self) -> str:
        """Get dark theme base stylesheet."""
        try:
            import qdarkstyle

            return str(qdarkstyle.load_stylesheet_pyside6())
        except ImportError:
            # Fallback dark theme using Qt Fusion style
            return self._get_fallback_dark_stylesheet()

    def _get_light_stylesheet(self) -> str:
        """Get light theme base stylesheet."""
        try:
            import qdarkstyle

            # QDarkStyleSheet also has a light theme
            return str(qdarkstyle.load_stylesheet_pyside6(theme="light"))
        except (ImportError, TypeError):
            # Fallback to default Qt light theme
            return self._get_fallback_light_stylesheet()

    def _get_system_stylesheet(self) -> str:
        """Get system theme stylesheet based on OS settings."""
        if self._is_system_dark_mode():
            return self._get_dark_stylesheet()
        else:
            return self._get_light_stylesheet()

    def _is_system_dark_mode(self) -> bool:
        """Detect if system is in dark mode."""
        try:
            # Check system palette
            palette = QApplication.palette()
            window_color = palette.color(QPalette.ColorRole.Window)

            # If window background is dark, assume dark mode
            return bool(window_color.lightness() < 128)

        except Exception:
            # Default to dark mode if detection fails
            return True

    def _get_fallback_dark_stylesheet(self) -> str:
        """Fallback dark theme when QDarkStyleSheet is not available."""
        return """
        /* Fallback Dark Theme */
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }

        QFrame {
            background-color: #2b2b2b;
            border: none;
        }

        QPushButton {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px 16px;
            min-height: 20px;
        }

        QPushButton:hover {
            background-color: #4a4a4a;
            border-color: #888888;
        }

        QPushButton:pressed {
            background-color: #bd93f9;
            color: #ffffff;
        }

        QLineEdit {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 4px 8px;
        }

        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #2b2b2b;
        }

        QTabBar::tab {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 8px 16px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background-color: #bd93f9;
            color: #ffffff;
        }
        """

    def _get_fallback_light_stylesheet(self) -> str:
        """Fallback light theme using default Qt styling."""
        return """
        /* Fallback Light Theme - mostly default Qt styling */
        QMainWindow {
            background-color: #f0f0f0;
            color: #000000;
        }

        QPushButton {
            background-color: #e0e0e0;
            color: #000000;
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 8px 16px;
            min-height: 20px;
        }

        QPushButton:hover {
            background-color: #d0d0d0;
            border-color: #999999;
        }

        QPushButton:pressed {
            background-color: #bd93f9;
            color: #ffffff;
        }

        QLineEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 4px 8px;
        }

        QTabWidget::pane {
            border: 1px solid #cccccc;
            background-color: #f0f0f0;
        }

        QTabBar::tab {
            background-color: #e0e0e0;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 8px 16px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background-color: #bd93f9;
            color: #ffffff;
        }
        """

    def _load_custom_overlay(self, theme_type: ThemeType) -> str:
        """Load custom overlay stylesheet for the given theme."""
        overlay_file = self.custom_overlays.get(theme_type)

        if not overlay_file:
            return ""

        # For system theme, determine which overlay to use
        if theme_type == ThemeType.SYSTEM:
            if self._is_system_dark_mode():
                overlay_file = self.custom_overlays[ThemeType.DARK]
            else:
                overlay_file = self.custom_overlays[ThemeType.LIGHT]

        try:
            with open(overlay_file, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Custom overlay file {overlay_file} not found")
            return ""
        except Exception as e:
            print(f"Warning: Error loading overlay {overlay_file}: {e}")
            return ""

    def get_available_themes(self) -> Dict[str, str]:
        """Get dictionary of available themes."""
        themes = {
            "Dark": ThemeType.DARK.value,
            "Light": ThemeType.LIGHT.value,
        }

        # Only add system theme if supported
        if self.system_theme_supported:
            themes["System"] = ThemeType.SYSTEM.value

        return themes

    def get_current_theme(self) -> str:
        """Get the current theme name."""
        return str(self.current_theme.value)

    def set_theme(self, theme_name: str) -> bool:
        """Set the application theme.

        Args:
            theme_name: Name of theme to apply ('dark', 'light', 'system')

        Returns:
            True if theme was applied successfully, False otherwise
        """
        try:
            # Parse theme type
            if theme_name == "dark":
                theme_type = ThemeType.DARK
            elif theme_name == "light":
                theme_type = ThemeType.LIGHT
            elif theme_name == "system":
                if not self.system_theme_supported:
                    print("Warning: System theme not supported, falling back to dark")
                    theme_type = ThemeType.DARK
                else:
                    theme_type = ThemeType.SYSTEM
            else:
                print(f"Warning: Unknown theme '{theme_name}', falling back to dark")
                theme_type = ThemeType.DARK

            # Get base stylesheet
            base_stylesheet_func = self.base_stylesheets[theme_type]
            base_stylesheet = base_stylesheet_func()

            # Get custom overlay
            custom_overlay = self._load_custom_overlay(theme_type)

            # Combine stylesheets
            combined_stylesheet = base_stylesheet
            if custom_overlay:
                combined_stylesheet += (
                    "\n\n/* Custom RetroClamp Overlay */\n" + custom_overlay
                )

            # Apply to application
            app = QApplication.instance()
            if app:
                app.setStyleSheet(combined_stylesheet)  # type: ignore[union-attr,attr-defined]
                print(f"✅ Applied {theme_name} theme")

            # Update current theme
            self.current_theme = theme_type

            # Save preference
            self.settings.setValue("theme/current", theme_name)

            # Emit signal
            self.theme_changed.emit(theme_name)

            return True

        except Exception as e:
            print(f"Error applying theme '{theme_name}': {e}")
            return False

    def load_saved_theme(self) -> str:
        """Load theme from saved settings.

        Returns:
            Name of the loaded theme
        """
        saved_theme = self.settings.value("theme/current", "dark")

        # Validate saved theme exists
        available_themes = self.get_available_themes()
        if saved_theme not in available_themes.values():
            print(f"Warning: Saved theme '{saved_theme}' not available, using dark")
            saved_theme = "dark"

        # Apply the theme
        if self.set_theme(saved_theme):
            return str(saved_theme)
        else:
            # Fallback to dark if loading fails
            self.set_theme("dark")
            return "dark"

    def create_light_overlay(self):
        """Create a light theme overlay file if it doesn't exist."""
        light_overlay_path = "light_overlay.qss"

        if os.path.exists(light_overlay_path):
            return  # Already exists

        # Create light theme overlay based on dark overlay
        light_overlay_content = """/* ===================================================================
   RetroClamp Light Theme Custom QSS Overlay
   Applied on top of QDarkStyleSheet Light Theme
   =================================================================== */

/* 1. Light theme checkbox & radio indicators */
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #cccccc;
    border-radius: 3px;
    background: #ffffff;
}

QCheckBox::indicator:checked {
    background: #0078d4;
    border: 1px solid #0078d4;
    image: url(resources/checkmark.svg);
}

/* 2. Light theme button states */
QPushButton:hover {
    background-color: rgba(0, 0, 0, 0.05);
    border: 1px solid #999999;
}

QPushButton:pressed {
    background: #0078d4;
    color: #ffffff;
    border: 1px solid #0078d4;
}

/* Light theme sidebar navigation */
QPushButton[objectName^="btn_"][selected="true"] {
    background: transparent;
    border-left: 4px solid #0078d4;
    color: #0078d4;
    padding-left: 12px;
}

QPushButton[objectName^="btn_"]:hover {
    background: rgba(0, 120, 212, 0.1);
    border-left: 2px solid #0078d4;
    padding-left: 14px;
}

/* 3. Light theme progress bars & scrollbars */
QProgressBar::chunk {
    background: #0078d4;
    border-radius: 2px;
}

QScrollBar::handle:horizontal:hover,
QScrollBar::handle:vertical:hover {
    background: #0078d4;
}

/* 4. Light theme tabs */
QTabBar::tab:selected {
    background: #0078d4;
    color: #ffffff;
    font-weight: bold;
}

QTabBar::tab:hover {
    background: rgba(0, 120, 212, 0.15);
    color: #000000;
}

/* Override any specific tab widget styling */
QTabWidget QTabBar::tab:selected {
    background: #0078d4 !important;
    color: #ffffff !important;
}

QTabWidget QTabBar::tab:hover {
    background: rgba(0, 120, 212, 0.15) !important;
}

/* 5. Light theme form elements */
QLineEdit {
    background: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 4px 8px;
    color: #000000;
}

QLineEdit:focus {
    border: 1px solid #0078d4;
    background: #ffffff;
}

/* 6. Light theme groupbox styling */
QGroupBox::title {
    color: #0078d4;
}
"""

        try:
            with open(light_overlay_path, "w", encoding="utf-8") as f:
                f.write(light_overlay_content)
            print(f"✅ Created light theme overlay: {light_overlay_path}")
        except Exception as e:
            print(f"Warning: Could not create light overlay: {e}")
