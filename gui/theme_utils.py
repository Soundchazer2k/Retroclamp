"""Theme utilities for RetroClamp.

This module provides utility functions for working with themes and colors
in the application UI.
"""

from typing import Optional, Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap

from .theme_config import DARK_THEME, ThemeConfig


def get_theme_color(color_name: str, theme: Optional[ThemeConfig] = None) -> str:
    """Get a color from the current theme.

    Args:
        color_name: Name of the color to get (e.g., 'primary', 'background')
        theme: Optional theme to get the color from. If None, uses the default dark
            theme.

    Returns:
        str: The color as a hex string (e.g., "#2a82da")

    Raises:
        ValueError: If the color name is invalid
    """
    if theme is None:
        theme = DARK_THEME

    # Map color names to theme attributes
    color_map = {
        "primary": theme.primary_color,
        "primary_dark": theme.secondary_color,
        "background": theme.background_color,
        "text": theme.text_color,
        "highlight": theme.highlight_color,
        "disabled": theme.disabled_color,
        "error": theme.error_color,
        "success": theme.success_color,
        "warning": theme.warning_color,
    }

    # Try to get the color from the map
    try:
        return color_map[color_name.lower()]
    except KeyError as err:
        raise ValueError(f"Invalid color name: {color_name}") from err


def get_contrasting_text_color(
    bg_color: Union[str, QColor], dark: str = "#000000", light: str = "#ffffff"
) -> str:
    """Get a contrasting text color (black or white) for a given background color.

    Args:
        bg_color: Background color as a hex string or QColor
        dark: Dark text color to use (default: black)
        light: Light text color to use (default: white)

    Returns:
        str: The contrasting color as a hex string
    """
    if isinstance(bg_color, str):
        bg_color = QColor(bg_color)

    # Calculate perceived brightness (0-255)
    brightness = (
        0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()
    )

    # Return dark or light color based on brightness
    return dark if brightness > 128 else light


def apply_stylesheet(widget, theme: ThemeConfig):
    """Apply a stylesheet to a widget based on the theme.

    Args:
        widget: The widget to apply the stylesheet to
        theme: The theme to use for styling
    """
    # Get contrast colors for text
    disabled_text_color = theme.disabled_color
    highlight_text_color = get_contrasting_text_color(theme.primary_color)

    stylesheet = f"""
    QWidget {{
        background-color: {theme.background_color};
        color: {theme.text_color};
        font-family: Arial, sans-serif;
        font-size: 12px;
    }}

    QPushButton {{
        background-color: {theme.primary_color};
        color: {highlight_text_color};
        border: 1px solid {theme.secondary_color};
        border-radius: 4px;
        padding: 5px 10px;
        min-width: 80px;
    }}

    QPushButton:hover {{
        background-color: {theme.secondary_color};
    }}

    QPushButton:disabled {{
        background-color: {theme.disabled_color};
        color: {disabled_text_color};
        border-color: {theme.disabled_color};
    }}

    QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, \
    QDateEdit, QDateTimeEdit, QTimeEdit {{
        background-color: {theme.highlight_color};
        color: {theme.text_color};
        border: 1px solid {theme.disabled_color};
        border-radius: 3px;
        padding: 3px 5px;
    }}

    QLabel {{
        color: {theme.text_color};
    }}

    QProgressBar {{
        border: 1px solid {theme.disabled_color};
        border-radius: 3px;
        text-align: center;
    }}

    QProgressBar::chunk {{
        background-color: {theme.primary_color};
        width: 10px;
    }}

    QTabBar::tab {{
        background: {theme.highlight_color};
        color: {theme.text_color};
        border: 1px solid {theme.disabled_color};
        border-bottom: none;
        padding: 5px 10px;
        margin-right: 2px;
    }}

    QTabBar::tab:selected, QTabBar::tab:hover {{
        background: {theme.primary_color};
        color: {highlight_text_color};
    }}
    """

    widget.setStyleSheet(stylesheet)


def create_icon(icon_name: str, color: Optional[str] = None, size: int = 24) -> QIcon:
    """Create an icon with optional color and size.

    Args:
        icon_name: Name of the icon file (without extension)
        color: Optional color to apply to the icon (hex string)
        size: Size of the icon in pixels (default: 24)

    Returns:
        QIcon: The created icon
    """
    # This is a placeholder - in a real implementation, you would load the icon
    # from your resources and apply the color if specified
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    # In a real implementation, you would load and color the icon here
    # For now, we'll just return a blank icon
    return QIcon(pixmap)
