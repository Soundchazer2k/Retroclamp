"""UI functions module for RetroClamp.

This module provides utility functions for UI operations, including
dynamic icon loading, theme application, and widget manipulation.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QMainWindow,
    QPushButton,
    QWidget,
)

from modules.theme_config import ThemeConfig


def load_svg_icon(name: str, size: int = 24, color_hex: str = "#ffffff") -> QIcon:
    """Load an SVG icon from the resources directory or create a fallback icon.

    Args:
        name: Icon name (without .svg extension)
        size: Icon size in pixels
        color_hex: Color in hex format (e.g., "#ffffff")

    Returns:
        QIcon object with the rendered icon
    """
    # Create a new QIcon
    icon = QIcon()

    # Try to load from resources first
    module_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(module_dir)

    # Define possible icon paths in order of preference
    icon_paths = [
        os.path.join(
            project_dir,
            "resources",
            "icons",
            "tabler-icons",
            "icons",
            "outline",
            f"{name}.svg",
        ),
        os.path.join(
            project_dir, "resources", "icons", "tabler-icons-svg", f"{name}.svg"
        ),
        os.path.join(project_dir, "resources", "icons", f"{name}.svg"),
    ]

    # Try each path until we find an existing file
    icon_path = None
    for path in icon_paths:
        if os.path.exists(path):
            icon_path = path
            break

    # If a valid icon path was found, use it
    if icon_path is not None:
        try:
            # Create a transparent pixmap
            pix = QPixmap(size, size)
            pix.fill(Qt.GlobalColor.transparent)

            # Create a painter for the pixmap
            painter = QPainter(pix)

            # Create an SVG renderer
            renderer = QSvgRenderer(icon_path)

            # Set up rendering hints
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            # Render the SVG onto the pixmap
            renderer.render(painter)

            # Clean up the painter
            painter.end()

            # Add the pixmap to the icon
            icon.addPixmap(pix)

        except Exception as e:
            print(f"Error loading SVG icon {name}: {str(e)}")
            # Fall through to create a fallback icon

    # If we couldn't load or render the SVG, create a fallback icon
    if icon.isNull() or icon.pixmap(size, size).isNull():
        # Create a simple colored square as a fallback
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw a colored square with the first letter of the name
        color = QColor(color_hex)
        painter.setPen(color)
        painter.setBrush(color)

        # Draw a circle with the first letter
        painter.drawEllipse(2, 2, size - 4, size - 4)

        # Add the first letter of the name
        if name:
            font = painter.font()
            font.setPointSize(int(size * 0.6))
            font.setBold(True)
            painter.setFont(font)

            # Set text color (invert the background color)
            text_color = QColor(
                255 - color.red(), 255 - color.green(), 255 - color.blue()
            )
            painter.setPen(text_color)

            # Draw the text centered
            painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, name[0].upper())

        painter.end()

        # Add the pixmap to the icon
        icon.addPixmap(pix)

    return icon


def apply_theme(
    window: QMainWindow, theme_config: Optional[Dict[str, Any]] = None
) -> None:
    """Apply a theme to the main window.

    Args:
        window: Main window to apply the theme to
        theme_config: Theme configuration dictionary (loads default if None)
    """
    # Create theme manager
    theme_manager = ThemeConfig()

    # Load theme if not provided
    if theme_config is None:
        theme_config = theme_manager.load_theme()

        if theme_config is None:
            # Fallback to default theme
            theme_config = {
                "name": "dracula",
                "colors": {
                    "primary": "#bd93f9",
                    "secondary": "#ff79c6",
                    "accent": "#50fa7b",
                    "background": "#282a36",
                    "secondaryBackground": "#44475a",
                    "foreground": "#f8f8f2",
                    "secondaryForeground": "#6272a4",
                },
            }

    # Apply basic colors to window
    colors = theme_config.get("colors", {})
    background_color = colors.get("background", "#282a36")
    text_color = colors.get("text", colors.get("foreground", "#f8f8f2"))

    # Create a basic stylesheet
    basic_qss = f"""
    QWidget {{
        background-color: {background_color};
        color: {text_color};
    }}
    """

    # Apply stylesheet to the window
    window.setStyleSheet(basic_qss)

    # Update icons with theme colors
    update_icons(window, theme_config)


def update_icons(window: QWidget, theme_config: Dict[str, Any]) -> None:
    """Update icons in a widget with theme colors.

    Args:
        window: Widget containing buttons with icons
        theme_config: Theme configuration dictionary
    """
    # If theme_config is None, use default colors
    if theme_config is None:
        theme_config = {}

    colors = theme_config.get("colors", {})
    # Handle both 'foreground' and 'text' for compatibility
    foreground = colors.get("text", colors.get("foreground", "#f8f8f2"))
    primary = colors.get("primary", "#bd93f9")

    # Define icon mappings (button name -> icon name)
    icon_mappings = {
        "toggleButton": "menu-2",
        "btn_home": "home",
        "btn_widgets": "layout-grid",
        "btn_new": "file-plus",
        "btn_save": "device-floppy",
        "btn_exit": "logout",
        "btn_settings": "settings",
        "btn_compress": "file-zip",
        "btn_extract": "file-export",
        "btn_info": "info-circle",
        "btn_verify": "check",
        "btn_theme": "palette",
        "btn_tools": "tool",
        "minimizeAppBtn": "minus",
        "maximizeRestoreAppBtn": "square",
        "closeAppBtn": "x",
    }

    # Update icons for all buttons with mappings
    for button_name, icon_name in icon_mappings.items():
        button = window.findChild(QPushButton, button_name)
        if button:
            # Use primary color for selected buttons, foreground for others
            if button.property("selected") == "true":
                button.setIcon(load_svg_icon(icon_name, 24, primary))
            else:
                button.setIcon(load_svg_icon(icon_name, 24, foreground))


def select_menu(
    widget: QWidget, menu_buttons: List[QPushButton], selected_button: QPushButton
) -> None:
    """Select a menu button and update styles.

    Args:
        widget: Parent widget containing the buttons
        menu_buttons: List of all menu buttons
        selected_button: Button to select
    """
    # Get theme colors
    theme_manager = ThemeConfig()
    theme_config = theme_manager.current_theme

    if not theme_config:
        theme_config = theme_manager.load_theme()

    colors = theme_config.get("colors", {}) if theme_config else {}
    primary = colors.get("primary", "#bd93f9")
    foreground = colors.get("foreground", "#f8f8f2")

    # Reset all buttons
    for button in menu_buttons:
        button.setProperty("selected", "false")
        button.setStyleSheet("")

        # Update icon color
        icon_name = button.property("icon_name")
        if icon_name:
            button.setIcon(load_svg_icon(icon_name, 24, foreground))

    # Select the button
    selected_button.setProperty("selected", "true")
    selected_button.setStyleSheet(
        f"background-color: {primary}; color: {colors.get('background', '#282a36')};"
    )

    # Update icon color
    icon_name = selected_button.property("icon_name")
    if icon_name:
        selected_button.setIcon(
            load_svg_icon(icon_name, 24, colors.get("background", "#282a36"))
        )


def toggle_menu(window: QMainWindow, enable: bool) -> None:
    """Toggle the visibility of the left menu.

    Args:
        window: Main window containing the menu
        enable: Whether to enable the animation
    """
    if not hasattr(window, "ui") or not hasattr(window.ui, "leftMenuBg"):
        return

    # Get current width
    width = window.ui.leftMenuBg.width()

    # Define target widths
    max_width = 200  # Maximum menu width
    min_width = 60  # Minimum menu width

    # Set target width based on current state
    target_width = max_width if width == min_width else min_width

    # Animate the width change
    window.animation = window.ui.leftMenuBg.animate(
        "minimumWidth", "maximumWidth", target_width, 300
    )
    window.animation.start()


def set_window_shadow(
    window: QWidget,
    color: str = "#000000",
    blur_radius: int = 20,
    offset: Tuple[int, int] = (0, 0),
) -> None:
    """Apply a drop shadow effect to a window.

    Args:
        window: Widget to apply shadow to
        color: Shadow color in hex format
        blur_radius: Shadow blur radius
        offset: Shadow offset (x, y)
    """
    shadow = QGraphicsDropShadowEffect(window)
    shadow.setBlurRadius(blur_radius)
    shadow.setColor(QColor(color))
    shadow.setOffset(offset[0], offset[1])
    window.setGraphicsEffect(shadow)


def set_button_hover_effect(
    button: QPushButton, hover_color: str, normal_color: str
) -> None:
    """Set a hover effect for a button.

    Args:
        button: Button to apply effect to
        hover_color: Color when hovered in hex format
        normal_color: Normal color in hex format
    """
    button.setStyleSheet(
        f"""
        QPushButton {{
            background-color: {normal_color};
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
    """
    )


def create_rounded_widget(widget: QWidget, radius: int = 10) -> None:
    """Apply rounded corners to a widget.

    Args:
        widget: Widget to apply rounded corners to
        radius: Corner radius in pixels
    """
    # Set stylesheet for rounded corners
    widget.setStyleSheet(
        f"""
        border-radius: {radius}px;
        background-color: {widget.palette().color(QPalette.Window).name()};
    """
    )

    # Make sure the widget clips its children to the rounded shape
    widget.setAttribute(Qt.WA_TranslucentBackground)
    widget.setMask(
        QRect(0, 0, widget.width(), widget.height()).adjusted(
            radius, radius, -radius, -radius
        )
    )
