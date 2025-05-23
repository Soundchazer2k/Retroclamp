"""Custom title bar for RetroClamp application.

This module provides a custom title bar that replaces the OS chrome.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from modules.theme_utils import get_color_from_hex
from modules.ui_functions import load_svg_icon


class TitleBar(QWidget):
    """Custom title bar widget.

    This widget replaces the OS chrome with a custom title bar that includes
    window controls (minimize, maximize/restore, close) and supports window dragging.
    Features a modern design with smooth hover effects and proper spacing.
    """

    def __init__(self, parent=None, theme_config=None):
        """Initialize the title bar.

        Args:
            parent: Parent widget
            theme_config: Theme configuration dictionary
        """
        super().__init__(parent)
        self._drag_pos = None
        self.theme_config = theme_config or {}

        # Set up widget properties
        self.setFixedHeight(36)  # Slightly taller for better proportions
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 5, 0)
        layout.setSpacing(8)

        # App icon and title
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        icon_pixmap = load_svg_icon("disc", 20, "#f8f8f2").pixmap(20, 20)
        self.icon_label.setPixmap(icon_pixmap)
        layout.addWidget(self.icon_label)

        # Add some spacing between icon and title
        layout.addSpacing(8)

        # Title with custom styling - more like standard Windows title bar
        self.title_label = QLabel("RetroClamp")
        text_color = self.theme_config.get("colors", {}).get("text", "#f8f8f2")
        self.title_label.setStyleSheet(
            f"""
            font-size: 11pt;
            font-weight: normal;
            color: {text_color};
            font-family: 'Segoe UI', Arial, sans-serif;
        """
        )
        layout.addWidget(self.title_label)
        layout.addStretch()

        # Window controls with styling similar to Windows
        button_size = 45
        icon_size = 10

        self.min_button = QPushButton()
        self.min_button.setObjectName("minButton")
        self.min_button.setFixedSize(button_size, button_size)
        self.min_button.setIcon(load_svg_icon("minus", icon_size, "#f8f8f2"))
        self.min_button.setIconSize(QSize(icon_size, icon_size))
        self.min_button.setToolTip("Minimize")
        self.min_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.min_button)

        self.max_button = QPushButton()
        self.max_button.setObjectName("maxButton")
        self.max_button.setFixedSize(button_size, button_size)
        self.max_button.setIcon(load_svg_icon("square", icon_size, "#f8f8f2"))
        self.max_button.setIconSize(QSize(icon_size, icon_size))
        self.max_button.setToolTip("Maximize")
        self.max_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.max_button)

        self.close_button = QPushButton()
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(button_size, button_size)
        self.close_button.setIcon(load_svg_icon("x", icon_size, "#f8f8f2"))
        self.close_button.setIconSize(QSize(icon_size, icon_size))
        self.close_button.setToolTip("Close")
        self.close_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.close_button)

        # Set up button connections
        self.min_button.clicked.connect(self.window().showMinimized)
        self.max_button.clicked.connect(self._toggle_max_restore)
        self.close_button.clicked.connect(self.window().close)

        # Set stylesheet
        self._update_stylesheet()

    def _update_stylesheet(self):
        """Update the stylesheet based on the theme configuration."""
        bg_color = self.theme_config.get("colors", {}).get("background", "#282a36")
        error_color = self.theme_config.get("colors", {}).get("error", "#ff5555")
        text_color = self.theme_config.get("colors", {}).get("text", "#f8f8f2")

        # Create a slightly lighter version of bg_color for gradient effect
        # (like Windows title bar)
        bg_color_rgb = get_color_from_hex(bg_color)
        lighter_bg = (
            f"rgb({min(bg_color_rgb[0] + 15, 255)}, {min(bg_color_rgb[1] + 15, 255)}, "
            f"{min(bg_color_rgb[2] + 15, 255)})"
        )

        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1, stop:0 {lighter_bg}, stop:1 {bg_color}
                );
                color: {text_color};
                border: none;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            #closeButton:hover {{
                background-color: {error_color};
            }}
            #minButton, #maxButton {{
                margin-right: 0px;
            }}
        """
        )

    def _toggle_max_restore(self):
        """Toggle between maximized and normal window states."""
        w = self.window()
        if w.isMaximized():
            w.showNormal()
            self.max_button.setIcon(load_svg_icon("square", 10, "#f8f8f2"))
            self.max_button.setToolTip("Maximize")
        else:
            w.showMaximized()
            # Use a restore icon (two overlapping squares)
            self.max_button.setIcon(load_svg_icon("copy", 10, "#f8f8f2"))
            self.max_button.setToolTip("Restore")

    def mousePressEvent(self, event):
        """Handle mouse press events for window dragging."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Handle mouse move events for window dragging."""
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.window().move(self.window().pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """Handle mouse release events for window dragging."""
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        """Handle double-click events to maximize/restore the window."""
        if event.button() == Qt.LeftButton:
            self._toggle_max_restore()

    def paintEvent(self, event):
        """Custom paint event to add visual enhancements."""
        super().paintEvent(event)
