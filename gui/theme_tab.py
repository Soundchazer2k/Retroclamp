"""Theme tab for RetroClamp.

This module provides the UI and functionality for customizing the application theme.
"""

import os

from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from modules.app_settings import AppSettings

# Import new theme manager
try:
    from core.theme_manager import ThemeManager, ThemeType
except ImportError:
    # Fallback for old theme system
    ThemeManager = None  # type: ignore[assignment,misc]
    ThemeType = None  # type: ignore[assignment,misc]

# Import local modules with fallbacks
try:
    from modules.theme_config import ThemeConfig
    from modules.theme_utils import calculate_contrast_ratio, is_accessible
    from modules.ui_functions import apply_theme, load_svg_icon
except ImportError:
    # Fallback implementations
    ThemeConfig = None  # type: ignore[assignment,misc]

    def calculate_contrast_ratio(color1, color2):  # type: ignore[misc]
        return 7.0

    def is_accessible(ratio):  # type: ignore[misc]
        return ratio >= 4.5

    def apply_theme(window, theme):  # type: ignore[misc]
        pass

    def load_svg_icon(name, size, color):  # type: ignore[misc]
        return None


class ColorButton(QPushButton):
    """Custom button for color selection.

    This button displays a color swatch and opens a color dialog when clicked.
    """

    color_changed = Signal(str, str)  # key, color

    def __init__(self, key: str, color: str, parent=None):
        """Initialize the ColorButton.

        Args:
            key: Color key
            color: Initial color (hex)
            parent: Parent widget
        """
        super().__init__(parent)
        self.key = key
        self.color = color
        self.setMinimumSize(QSize(60, 30))
        self.setMaximumSize(QSize(60, 30))
        self.update_color(color)

    def update_color(self, color: str):
        """Update the button color.

        Args:
            color: New color (hex)
        """
        self.color = color
        self.setStyleSheet(f"background-color: {color}; border: 1px solid #555;")

    def mousePressEvent(self, event):
        """Handle mouse press events.

        Args:
            event: Mouse event
        """
        if event.button() == Qt.LeftButton:
            # Open color dialog
            color = QColorDialog.getColor(QColor(self.color), self)

            if color.isValid():
                # Update color
                hex_color = color.name()
                self.update_color(hex_color)
                self.color_changed.emit(self.key, hex_color)

        super().mousePressEvent(event)


class ThemeTab(QWidget):
    """Theme tab widget.

    This widget provides a UI for customizing the application theme.
    """

    def __init__(self, parent=None):
        """Initialize the ThemeTab widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Initialize settings
        self.settings = AppSettings()

        # Initialize theme manager (new system)
        if ThemeManager is not None:
            self.theme_manager = ThemeManager()
            # Create light overlay if it doesn't exist
            self.theme_manager.create_light_overlay()
        else:
            self.theme_manager = None

        # Initialize theme config (legacy fallback)
        if ThemeConfig is not None:
            self.theme_config = ThemeConfig()
            # Load current theme
            theme_name = self.settings.get("general", "theme", "dracula")
            self.current_theme = self.theme_config.load_theme(theme_name)
        else:
            self.theme_config = None
            self.current_theme = {}

        # Setup UI
        self.setup_ui()
        self.connect_signals()

        # Load themes
        self.load_themes()

    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title
        title_label = QLabel("Theme Customization")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title_label)

        # Description
        if self.theme_manager:
            desc_text = (
                "Select from Dark, Light, or System themes. "
                "The System theme automatically matches your operating system's appearance."
            )
        else:
            desc_text = (
                "Customize the application theme by selecting a predefined theme or "
                "creating your own. Changes will be applied immediately."
            )

        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Theme selection
        theme_group = QGroupBox("Theme Selection")
        theme_layout = QHBoxLayout(theme_group)

        theme_label = QLabel("Select Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(200)

        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()

        layout.addWidget(theme_group)

        # Create scroll area for color settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # Color settings container
        color_container = QWidget()
        self.color_layout = QVBoxLayout(color_container)
        self.color_layout.setContentsMargins(0, 0, 0, 0)
        self.color_layout.setSpacing(20)

        # Primary colors
        primary_group = QGroupBox("Primary Colors")
        primary_layout = QFormLayout(primary_group)

        # Create color buttons
        self.color_buttons = {}

        # Primary color
        self.color_buttons["primary"] = ColorButton("primary", "#bd93f9")
        primary_layout.addRow("Primary:", self.color_buttons["primary"])

        # Secondary color
        self.color_buttons["secondary"] = ColorButton("secondary", "#ff79c6")
        primary_layout.addRow("Secondary:", self.color_buttons["secondary"])

        # Accent color
        self.color_buttons["accent"] = ColorButton("accent", "#8be9fd")
        primary_layout.addRow("Accent:", self.color_buttons["accent"])

        self.color_layout.addWidget(primary_group)

        # Background colors
        bg_group = QGroupBox("Background Colors")
        bg_layout = QFormLayout(bg_group)

        # Background color
        self.color_buttons["background"] = ColorButton("background", "#282a36")
        bg_layout.addRow("Background:", self.color_buttons["background"])

        # Secondary background color
        self.color_buttons["secondaryBackground"] = ColorButton(
            "secondaryBackground", "#44475a"
        )
        bg_layout.addRow(
            "Secondary Background:", self.color_buttons["secondaryBackground"]
        )

        # Tertiary background color
        self.color_buttons["tertiaryBackground"] = ColorButton(
            "tertiaryBackground", "#6272a4"
        )
        bg_layout.addRow(
            "Tertiary Background:", self.color_buttons["tertiaryBackground"]
        )

        self.color_layout.addWidget(bg_group)

        # Text colors
        text_group = QGroupBox("Text Colors")
        text_layout = QFormLayout(text_group)

        # Text color
        self.color_buttons["text"] = ColorButton("text", "#f8f8f2")
        text_layout.addRow("Text:", self.color_buttons["text"])

        # Secondary text color
        self.color_buttons["secondaryText"] = ColorButton("secondaryText", "#d8d8d2")
        text_layout.addRow("Secondary Text:", self.color_buttons["secondaryText"])

        # Disabled text color
        self.color_buttons["disabledText"] = ColorButton("disabledText", "#6272a4")
        text_layout.addRow("Disabled Text:", self.color_buttons["disabledText"])

        self.color_layout.addWidget(text_group)

        # Status colors
        status_group = QGroupBox("Status Colors")
        status_layout = QFormLayout(status_group)

        # Success color
        self.color_buttons["success"] = ColorButton("success", "#50fa7b")
        status_layout.addRow("Success:", self.color_buttons["success"])

        # Warning color
        self.color_buttons["warning"] = ColorButton("warning", "#ffb86c")
        status_layout.addRow("Warning:", self.color_buttons["warning"])

        # Error color
        self.color_buttons["error"] = ColorButton("error", "#ff5555")
        status_layout.addRow("Error:", self.color_buttons["error"])

        # Info color
        self.color_buttons["info"] = ColorButton("info", "#8be9fd")
        status_layout.addRow("Info:", self.color_buttons["info"])

        self.color_layout.addWidget(status_group)

        # Set scroll area widget
        scroll_area.setWidget(color_container)
        layout.addWidget(scroll_area)

        # Accessibility warnings
        self.accessibility_group = QGroupBox("Accessibility")
        self.accessibility_layout = QVBoxLayout(self.accessibility_group)

        self.accessibility_label = QLabel("No accessibility issues detected.")
        self.accessibility_label.setWordWrap(True)
        self.accessibility_layout.addWidget(self.accessibility_label)

        layout.addWidget(self.accessibility_group)

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.setIcon(load_svg_icon("refresh", 16, "#f8f8f2"))
        self.reset_btn.setMinimumWidth(150)
        action_layout.addWidget(self.reset_btn)

        self.save_btn = QPushButton("Save Theme")
        self.save_btn.setIcon(load_svg_icon("device-floppy", 16, "#f8f8f2"))
        self.save_btn.setMinimumWidth(150)
        action_layout.addWidget(self.save_btn)

        self.apply_btn = QPushButton("Apply Theme")
        self.apply_btn.setIcon(load_svg_icon("check", 16, "#f8f8f2"))
        self.apply_btn.setMinimumWidth(150)
        action_layout.addWidget(self.apply_btn)

        layout.addLayout(action_layout)

    def connect_signals(self):
        """Connect widget signals to slots."""
        # Theme selection
        self.theme_combo.currentIndexChanged.connect(self.load_selected_theme)

        # Color buttons
        for _key, button in self.color_buttons.items():
            button.color_changed.connect(self.update_color)

        # Action buttons
        self.reset_btn.clicked.connect(self.reset_theme)
        self.save_btn.clicked.connect(self.save_theme)
        self.apply_btn.clicked.connect(self.apply_current_theme)

    def load_themes(self):
        """Load available themes."""
        # Get themes directory
        themes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

        # Clear combo box
        self.theme_combo.clear()

        # Add default themes
        self.theme_combo.addItem("Dracula (Dark)", "dracula")
        self.theme_combo.addItem("Light", "light")

        # Add custom themes
        custom_themes = []
        for filename in os.listdir(themes_dir):
            if (
                filename.startswith("theme_")
                and filename.endswith(".json")
                and filename != "theme.json"
                and filename != "theme_light.json"
            ):
                # Get theme name
                theme_name = filename[6:-5]  # Remove "theme_" prefix and ".json" suffix

                # Add to list
                custom_themes.append((theme_name.capitalize(), theme_name))

        # Sort custom themes
        custom_themes.sort()

        # Add separator
        if custom_themes:
            self.theme_combo.insertSeparator(self.theme_combo.count())

        # Add custom themes
        for name, value in custom_themes:
            self.theme_combo.addItem(f"{name} (Custom)", value)

        # Set current theme
        current_theme = self.settings.get("general", "theme", "dracula")
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break

    @Slot(int)
    def load_selected_theme(self, index):
        """Load the selected theme.

        Args:
            index: Selected index
        """
        # Get theme name
        theme_name = self.theme_combo.itemData(index)

        if not theme_name:
            return

        # Load theme
        theme = self.theme_config.load_theme(theme_name)

        if not theme:
            return

        # Update current theme
        self.current_theme = theme

        # Update color buttons
        colors = theme.get("colors", {})
        for key, button in self.color_buttons.items():
            if key in colors:
                button.update_color(colors[key])

        # Check accessibility
        self.check_accessibility()

    @Slot(str, str)
    def update_color(self, key, color):
        """Update a color in the current theme.

        Args:
            key: Color key
            color: New color (hex)
        """
        # Update theme
        if "colors" not in self.current_theme:
            self.current_theme["colors"] = {}

        self.current_theme["colors"][key] = color

        # Check accessibility
        self.check_accessibility()

    def check_accessibility(self):
        """Check theme colors for accessibility issues."""
        # Get colors
        colors = self.current_theme.get("colors", {})

        # Check text contrast
        issues = []

        # Text on background
        text = colors.get("text", "#f8f8f2")
        background = colors.get("background", "#282a36")
        ratio = calculate_contrast_ratio(text, background)
        if not is_accessible(ratio):
            issues.append(
                f"Text on background contrast ratio is {ratio:.2f}:1 "
                f"(should be at least 4.5:1)"
            )

        # Text on secondary background
        secondary_bg = colors.get("secondaryBackground", "#44475a")
        ratio = calculate_contrast_ratio(text, secondary_bg)
        if not is_accessible(ratio):
            issues.append(
                f"Text on secondary background contrast ratio is {ratio:.2f}:1 "
                f"(should be at least 4.5:1)"
            )

        # Text on tertiary background
        tertiary_bg = colors.get("tertiaryBackground", "#6272a4")
        ratio = calculate_contrast_ratio(text, tertiary_bg)
        if not is_accessible(ratio):
            issues.append(
                f"Text on tertiary background contrast ratio is {ratio:.2f}:1 "
                f"(should be at least 4.5:1)"
            )

        # Primary on background
        primary = colors.get("primary", "#bd93f9")
        ratio = calculate_contrast_ratio(primary, background)
        if not is_accessible(ratio):
            issues.append(
                f"Primary on background contrast ratio is {ratio:.2f}:1 "
                f"(should be at least 4.5:1)"
            )

        # Update accessibility label
        if issues:
            self.accessibility_label.setText(
                "Accessibility issues detected:\n\n" + "\n".join(issues)
            )
            self.accessibility_label.setStyleSheet("color: #ff5555;")
        else:
            self.accessibility_label.setText("No accessibility issues detected.")
            self.accessibility_label.setStyleSheet("")

    @Slot()
    def reset_theme(self):
        """Reset the current theme to default."""
        # Get current theme name
        theme_name = self.theme_combo.currentData()

        if not theme_name:
            return

        # Confirm reset
        reply = QMessageBox.question(
            self,
            "Reset Theme",
            f"Are you sure you want to reset the {theme_name} theme to default?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        # Load default theme
        if theme_name == "dracula":
            # Load built-in Dracula theme
            theme = self.theme_config.get_default_theme()
        elif theme_name == "light":
            # Load built-in Light theme
            theme = self.theme_config.get_light_theme()
        else:
            # Can't reset custom theme
            QMessageBox.information(
                self, "Reset Theme", "Custom themes cannot be reset to default."
            )
            return

        # Update current theme
        self.current_theme = theme

        # Update color buttons
        colors = theme.get("colors", {})
        for key, button in self.color_buttons.items():
            if key in colors:
                button.update_color(colors[key])

        # Check accessibility
        self.check_accessibility()

        # Save theme
        self.theme_config.save_theme(theme_name, theme)

        # Apply theme
        self.apply_current_theme()

    @Slot()
    def save_theme(self):
        """Save the current theme."""
        # Get current theme name
        theme_name = self.theme_combo.currentData()

        if not theme_name:
            return

        # Check if it's a built-in theme
        is_builtin = theme_name in ["dracula", "light"]

        if is_builtin:
            # Ask for a new name
            new_name, ok = QFileDialog.getSaveFileName(
                self,
                "Save Theme As",
                os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "config",
                    "theme_custom.json",
                ),
                "Theme Files (*.json)",
            )

            if not ok or not new_name:
                return

            # Get theme name from filename
            basename = os.path.basename(new_name)
            if basename.startswith("theme_") and basename.endswith(".json"):
                theme_name = basename[6:-5]  # Remove "theme_" prefix and ".json" suffix
            else:
                theme_name = "custom"

        # Save theme
        self.theme_config.save_theme(theme_name, self.current_theme)

        # Reload themes
        self.load_themes()

        # Show success message
        QMessageBox.information(
            self, "Theme Saved", f"Theme '{theme_name}' has been saved successfully."
        )

    @Slot()
    def apply_current_theme(self):
        """Apply the current theme."""
        # Get current theme name
        theme_name = self.theme_combo.currentData()

        if not theme_name:
            return

        # Save theme
        self.theme_config.save_theme(theme_name, self.current_theme)

        # Update settings
        self.settings.set("general", "theme", theme_name)
        self.settings.save_settings()

        # Apply theme to main window
        main_window = self.window()
        apply_theme(main_window, self.current_theme)
