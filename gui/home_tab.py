"""Home tab for RetroClamp.

This module provides the UI for the home screen of the application.
"""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from modules.ui_functions import load_svg_icon
from version import __version__


class FeatureButton(QPushButton):
    """Custom button for feature selection.

    This button displays an icon and text for a main feature.
    """

    def __init__(self, title: str, icon_name: str, description: str, parent=None):
        """Initialize the FeatureButton.

        Args:
            title: Button title
            icon_name: Name of the icon to display
            description: Feature description
            parent: Parent widget
        """
        super().__init__(parent)

        # Set up button properties
        self.setMinimumSize(180, 90)  # Reduced from 200x100 for better responsiveness
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("icon_name", icon_name)

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Use QPushButton's built-in icon instead of a separate label
        self.setIcon(load_svg_icon(icon_name, 32, "#f8f8f2"))
        self.setIconSize(QSize(32, 32))

        # Use QPushButton's built-in text instead of a separate label
        self.setText(title)

        # Store description for later use
        self.description = description

        # Set stylesheet with all styling in one call
        self.setStyleSheet(
            "QPushButton {"
            "    background-color: rgba(68, 71, 90, 0.8);"  # Restore button background
            "    border: none;"
            "    color: #f8f8f2;"
            "    text-align: left;"
            "    padding: 10px;"
            "    padding-left: 40px;"  # Make room for the icon
            "    font-size: 14pt;"
            "    font-weight: bold;"
            "    border-radius: 6px;"
            "}"
            "QPushButton:hover {"
            "    background-color: rgba(255, 255, 255, 0.12);"
            "    border: 1px solid #bd93f9;"
            "}"
            "QPushButton:pressed {"
            "    background-color: rgba(88, 91, 112, 1.0);"
            "}"
        )

        # Add drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))  # Semi-transparent black
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)

        # Setup hover animation
        self._original_geometry = None
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(100)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)

    def enterEvent(self, event):
        """Handle mouse enter event with subtle lift animation."""
        if not self._original_geometry:
            self._original_geometry = self.geometry()

        geom = self.geometry()
        self._anim.stop()
        self._anim.setStartValue(geom)
        self._anim.setEndValue(geom.adjusted(-2, -2, 2, 2))
        self._anim.start()

        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave event with animation back to original size."""
        if self._original_geometry:
            self._anim.stop()
            self._anim.setStartValue(self.geometry())
            self._anim.setEndValue(self._original_geometry)
            self._anim.start()

        super().leaveEvent(event)


class HomeTab(QWidget):
    """Home tab widget.

    This widget provides the main home screen for the application.
    """

    # Signals
    compress_clicked = Signal()
    extract_clicked = Signal()
    tools_clicked = Signal()
    batch_clicked = Signal()

    def __init__(self, parent=None):
        """Initialize the HomeTab widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Welcome section
        welcome_layout = QVBoxLayout()

        # Logo and title
        title_layout = QHBoxLayout()

        # Logo placeholder
        logo_label = QLabel()
        logo_label.setMinimumSize(QSize(64, 64))
        logo_label.setMaximumSize(QSize(64, 64))
        logo_label.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        logo_label.setPixmap(
            load_svg_icon("device-gamepad-2", 64, "#bd93f9").pixmap(64, 64)
        )
        title_layout.addWidget(logo_label)

        # Title and version
        title_version_layout = QVBoxLayout()

        title_label = QLabel("RetroClamp")
        title_label.setStyleSheet("font-size: 28pt; font-weight: bold;")
        title_version_layout.addWidget(title_label)

        version_display = __version__
        if not version_display.endswith("-dev"):
            version_display += "-dev"
        version_label = QLabel(f"Version {version_display}")
        version_label.setStyleSheet("font-size: 12pt; color: #6272a4;")
        title_version_layout.addWidget(version_label)

        title_layout.addLayout(title_version_layout)
        title_layout.addStretch()

        welcome_layout.addLayout(title_layout)

        # Description
        desc_label = QLabel(
            "RetroClamp is a modern GUI for CHDMAN operations, allowing you to "
            "compress, decompress, and manage disk images with ease. "
            "Select an option below to get started."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12pt; margin-top: 10px;")
        welcome_layout.addWidget(desc_label)

        layout.addLayout(welcome_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Features scroll area
        features_scroll_area = QScrollArea()
        features_scroll_area.setWidgetResizable(True)
        features_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        features_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        features_scroll_area.setFrameShape(QFrame.NoFrame)  # Remove frame

        # Features grid
        features_widget = QWidget()
        features_scroll_area.setWidget(features_widget)

        features_layout = QGridLayout(features_widget)
        features_layout.setContentsMargins(10, 10, 10, 10)
        features_layout.setSpacing(10)  # Reduced spacing for better responsiveness

        # Add scroll area to main layout
        layout.addWidget(features_scroll_area)

        # Compress button
        self.compress_btn = FeatureButton(
            "Compress Disk Images",
            "file-zip",
            "Compress disk images to CHD format for efficient storage.",
        )
        features_layout.addWidget(self.compress_btn, 0, 0)

        # Extract button
        self.extract_btn = FeatureButton(
            "Extract CHD Files",
            "file-export",
            "Extract disk images from CHD files to various formats.",
        )
        features_layout.addWidget(self.extract_btn, 0, 1)

        # Tools button
        self.tools_btn = FeatureButton(
            "Additional Tools",
            "tool",
            "Access additional tools for working with disk images.",
        )
        features_layout.addWidget(self.tools_btn, 1, 0)

        # Batch processing button
        self.batch_btn = FeatureButton(
            "Batch Processing", "list-check", "Process multiple files in batch mode."
        )
        features_layout.addWidget(self.batch_btn, 1, 1)

        # We don't need to add features_layout here as it already has a parent
        # (features_widget)

        # Feature descriptions
        desc_frame = QFrame()
        desc_frame.setFrameShape(QFrame.StyledPanel)
        desc_frame.setStyleSheet(
            "QFrame {"
            "    background-color: rgba(68, 71, 90, 0.5);"
            "    border-radius: 5px;"
            "    padding: 10px;"
            "}"
        )

        desc_layout = QVBoxLayout(desc_frame)

        self.feature_title_label = QLabel("Select a feature to get started")
        self.feature_title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        desc_layout.addWidget(self.feature_title_label)

        self.feature_desc_label = QLabel(
            "Hover over one of the feature buttons above to see a description here."
        )
        self.feature_desc_label.setWordWrap(True)
        self.feature_desc_label.setStyleSheet("font-size: 11pt;")
        desc_layout.addWidget(self.feature_desc_label)

        layout.addWidget(desc_frame)

        # Quick stats section
        stats_layout = QHBoxLayout()

        # Recent files
        recent_frame = QFrame()
        recent_frame.setFrameShape(QFrame.StyledPanel)
        recent_frame.setStyleSheet(
            "QFrame {"
            "    background-color: rgba(68, 71, 90, 0.3);"
            "    border-radius: 5px;"
            "    padding: 10px;"
            "}"
        )

        recent_layout = QVBoxLayout(recent_frame)

        recent_title = QLabel("Recent Files")
        recent_title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        recent_layout.addWidget(recent_title)

        self.recent_list = QLabel("No recent files")
        self.recent_list.setStyleSheet("font-size: 10pt; color: #d8d8d2;")
        recent_layout.addWidget(self.recent_list)

        stats_layout.addWidget(recent_frame)

        # Statistics
        stats_frame = QFrame()
        stats_frame.setFrameShape(QFrame.StyledPanel)
        stats_frame.setStyleSheet(
            "QFrame {"
            "    background-color: rgba(68, 71, 90, 0.3);"
            "    border-radius: 5px;"
            "    padding: 10px;"
            "}"
        )

        stats_inner_layout = QVBoxLayout(stats_frame)

        stats_title = QLabel("Statistics")
        stats_title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        stats_inner_layout.addWidget(stats_title)

        self.stats_list = QLabel("No statistics available")
        self.stats_list.setStyleSheet("font-size: 10pt; color: #d8d8d2;")
        stats_inner_layout.addWidget(self.stats_list)

        stats_layout.addWidget(stats_frame)

        layout.addLayout(stats_layout)

        # Add spacer
        layout.addStretch()

    def connect_signals(self):
        """Connect widget signals to slots."""
        # Feature buttons
        self.compress_btn.clicked.connect(self.compress_clicked)
        self.extract_btn.clicked.connect(self.extract_clicked)
        self.tools_btn.clicked.connect(self.tools_clicked)
        self.batch_btn.clicked.connect(self.batch_clicked)

        # Feature descriptions
        self.compress_btn.enterEvent = lambda e: self.update_description(
            "Compress Disk Images",
            "Convert disk images (ISO, BIN, IMG, etc.) to CHD format for efficient "
            "storage and emulation compatibility. CHD files are smaller and maintain "
            "all the original data.",
        )

        self.extract_btn.enterEvent = lambda e: self.update_description(
            "Extract CHD Files",
            "Extract disk images from CHD files to various formats such as ISO, BIN, "
            "or AVI. Choose the output format that best suits your needs.",
        )

        self.tools_btn.enterEvent = lambda e: self.update_description(
            "Additional Tools",
            "Access additional tools for working with disk images, including SCUMMVM "
            "configuration generation, metadata extraction, and more.",
        )

        self.batch_btn.enterEvent = lambda e: self.update_description(
            "Batch Processing",
            "Process multiple files in batch mode with customizable settings. "
            "Perfect for converting entire directories of disk images.",
        )

        # Reset description on leave
        self.compress_btn.leaveEvent = lambda e: self.reset_description()
        self.extract_btn.leaveEvent = lambda e: self.reset_description()
        self.tools_btn.leaveEvent = lambda e: self.reset_description()
        self.batch_btn.leaveEvent = lambda e: self.reset_description()

    def update_description(self, title: str, description: str):
        """Update the feature description.

        Args:
            title: Feature title
            description: Feature description
        """
        self.feature_title_label.setText(title)
        self.feature_desc_label.setText(description)

    def reset_description(self):
        """Reset the feature description to default."""
        self.feature_title_label.setText("Select a feature to get started")
        self.feature_desc_label.setText(
            "Hover over one of the feature buttons above to see a description here."
        )
