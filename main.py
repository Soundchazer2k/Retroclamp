"""RetroClamp - Modern GUI for CHDMAN operations.

This is the main entry point for the RetroClamp application, which provides
a modern, user-friendly interface for compressing, decompressing, and managing
disk images using the CHDMAN utility.
"""

import logging
import os
import sys
import traceback

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# Set environment variables for high DPI scaling
os.environ["QT_FONT_DPI"] = "96"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from gui.batch_tab import BatchTab
from gui.compression_tab import CompressionTab
from gui.extraction_tab import ExtractionTab

# Import GUI modules
from gui.home_tab import HomeTab
from gui.settings_tab import SettingsTab
from gui.theme_tab import ThemeTab
from gui.title_bar import TitleBar
from modules.app_settings import AppSettings
from modules.theme_config import ThemeConfig

# Import local modules
from modules.ui_functions import apply_theme, load_svg_icon, resize_grips
from version import __version__

# Global settings
SETTINGS = None
THEME_CONFIG = None


class MainWindow(QMainWindow):
    """Main window for the RetroClamp application.

    This class represents the main application window, containing the sidebar menu,
    content area, and various UI elements.
    """

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        # Initialize settings
        global SETTINGS, THEME_CONFIG
        SETTINGS = AppSettings()
        THEME_CONFIG = ThemeConfig()

        # Load theme
        theme_name = SETTINGS.get("general", "theme", "dracula")
        self.theme_config = THEME_CONFIG.load_theme(theme_name)

        # If theme loading failed, use a default theme
        if self.theme_config is None:
            self.theme_config = {
                "colors": {
                    "primary": "#bd93f9",
                    "secondary": "#ff79c6",
                    "accent": "#8be9fd",
                    "background": "#282a36",
                    "secondaryBackground": "#44475a",
                    "tertiaryBackground": "#6272a4",
                    "text": "#f8f8f2",
                    "secondaryText": "#d8d8d2",
                    "disabledText": "#6272a4",
                    "success": "#50fa7b",
                    "warning": "#ffb86c",
                    "error": "#ff5555",
                    "info": "#8be9fd",
                }
            }

        # Set up window properties
        self.setWindowTitle("RetroClamp")
        self.setWindowIcon(QIcon("resources/icon.ico"))
        self.resize(1200, 800)

        # Set proper window flags to enable frameless window with resizing
        flags = self.windowFlags()
        # Remove all window decoration flags to customize window appearance
        flags &= ~Qt.WindowType.WindowTitleHint
        flags &= ~Qt.WindowType.WindowSystemMenuHint
        # Enable frameless window but keep resizing capability
        flags |= Qt.WindowType.FramelessWindowHint
        # Add back only the specific flags we need for minimize, maximize, close
        flags |= (
            Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowFlags(flags)

        # Set up UI
        self.setup_ui()
        self.connect_signals()

        # Apply theme
        apply_theme(self, self.theme_config)

        # Show the window
        self.show()

    def setup_ui(self):
        """Set up the user interface."""
        # Create central widget for the main window
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout - vertical layout to stack title bar above content
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Add custom title bar for window dragging and controls
        self.title_bar = TitleBar(self, self.theme_config)
        self.main_layout.addWidget(self.title_bar)

        # Main content layout (horizontal): sidebar menu and main content area
        self.main_content_layout = QHBoxLayout()
        self.main_content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_content_layout.setSpacing(0)
        self.main_layout.addLayout(self.main_content_layout)

        # Sidebar (left menu) background frame
        self.left_menu_bg = QFrame()
        self.left_menu_bg.setObjectName("leftMenuBg")
        self.left_menu_bg.setMinimumWidth(220)  # expanded width
        self.left_menu_bg.setMaximumWidth(220)  # expanded width
        # Collapsed width (for compact mode) – increased for better usability
        self.collapsed_width = 80  # was 60

        # Layout for sidebar menu (vertical)
        self.left_menu_layout = QVBoxLayout(self.left_menu_bg)
        self.left_menu_layout.setContentsMargins(0, 12, 0, 12)
        self.left_menu_layout.setSpacing(8)

        # Top menu section (contains main navigation buttons)
        self.top_menu = QFrame()
        self.top_menu.setObjectName("topMenu")
        self.top_menu.setMinimumHeight(50)

        # Layout for top menu buttons
        self.top_menu_layout = QVBoxLayout(self.top_menu)
        self.top_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.top_menu_layout.setSpacing(0)

        # Top menu buttons
        self.btn_home = QPushButton("Home")
        self.btn_home.setObjectName("btn_home")
        self.btn_home.setProperty("icon_name", "home")
        # make icons a bit larger
        icon = load_svg_icon("home", 32, "#f8f8f2")
        self.btn_home.setIcon(icon)
        self.btn_home.setIconSize(QSize(32, 32))
        # bump button height to match
        self.btn_home.setMinimumHeight(120)

        # increase font size and left-align everything
        self.btn_home.setFont(QFont("Segoe UI", 11))
        self.btn_home.setStyleSheet(
            """
            text-align: left;
            padding-left: 16px;
        """
        )
        self.top_menu_layout.addWidget(self.btn_home)

        self.btn_compress = QPushButton("Compress")
        self.btn_compress.setObjectName("btn_compress")
        self.btn_compress.setProperty("icon_name", "file-zip")
        # make icons a bit larger
        icon = load_svg_icon("file-zip", 32, "#f8f8f2")
        self.btn_compress.setIcon(icon)
        self.btn_compress.setIconSize(QSize(32, 32))
        # bump button height to match
        self.btn_compress.setMinimumHeight(120)

        # increase font size and left-align everything
        self.btn_compress.setFont(QFont("Segoe UI", 11))
        self.btn_compress.setStyleSheet(
            """
            text-align: left;
            padding-left: 16px;
        """
        )
        self.top_menu_layout.addWidget(self.btn_compress)

        self.btn_extract = QPushButton("Extract")
        self.btn_extract.setObjectName("btn_extract")
        self.btn_extract.setProperty("icon_name", "file-export")
        # make icons a bit larger
        icon = load_svg_icon("file-export", 32, "#f8f8f2")
        self.btn_extract.setIcon(icon)
        self.btn_extract.setIconSize(QSize(32, 32))
        # bump button height to match
        self.btn_extract.setMinimumHeight(120)

        # increase font size and left-align everything
        self.btn_extract.setFont(QFont("Segoe UI", 11))
        self.btn_extract.setStyleSheet(
            """
            text-align: left;
            padding-left: 16px;
        """
        )
        self.top_menu_layout.addWidget(self.btn_extract)

        self.btn_tools = QPushButton("Tools")
        self.btn_tools.setObjectName("btn_tools")
        self.btn_tools.setProperty("icon_name", "tool")
        # make icons a bit larger
        icon = load_svg_icon("tool", 32, "#f8f8f2")
        self.btn_tools.setIcon(icon)
        self.btn_tools.setIconSize(QSize(32, 32))
        # bump button height to match
        self.btn_tools.setMinimumHeight(120)

        # increase font size and left-align everything
        self.btn_tools.setFont(QFont("Segoe UI", 11))
        self.btn_tools.setStyleSheet(
            """
            text-align: left;
            padding-left: 16px;
        """
        )
        self.top_menu_layout.addWidget(self.btn_tools)

        self.btn_theme = QPushButton("Theme")
        self.btn_theme.setObjectName("btn_theme")
        self.btn_theme.setProperty("icon_name", "palette")
        # make icons a bit larger
        icon = load_svg_icon("palette", 32, "#f8f8f2")
        self.btn_theme.setIcon(icon)
        self.btn_theme.setIconSize(QSize(32, 32))
        # bump button height to match
        self.btn_theme.setMinimumHeight(120)

        # increase font size and left-align everything
        self.btn_theme.setFont(QFont("Segoe UI", 11))
        self.btn_theme.setStyleSheet(
            """
            text-align: left;
            padding-left: 16px;
        """
        )
        self.top_menu_layout.addWidget(self.btn_theme)

        # Menu spacer
        self.menu_spacer = QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        # Bottom menu
        self.bottom_menu = QFrame()
        self.bottom_menu.setObjectName("bottomMenu")
        # Increase minimum height to match the visual height of top menu
        self.bottom_menu.setMinimumHeight(120)  # Changed from 50 to 120

        # Bottom menu layout
        self.bottom_menu_layout = QVBoxLayout(self.bottom_menu)
        self.bottom_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_menu_layout.setSpacing(0)

        # Bottom menu buttons
        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setProperty("icon_name", "settings")
        # make icons a bit larger
        icon = load_svg_icon("settings", 32, "#f8f8f2")
        self.btn_settings.setIcon(icon)
        self.btn_settings.setIconSize(QSize(32, 32))
        # bump button height to match
        self.btn_settings.setMinimumHeight(120)

        # increase font size and left-align everything
        self.btn_settings.setFont(QFont("Segoe UI", 11))
        self.btn_settings.setStyleSheet(
            """
            text-align: left;
            padding-left: 16px;
        """
        )
        self.bottom_menu_layout.addWidget(self.btn_settings)

        # Toggle button
        self.toggle_button = QPushButton("Hide")
        self.toggle_button.setObjectName("toggleButton")
        self.toggle_button.setProperty("icon_name", "menu-2")
        # make icons a bit larger
        icon = load_svg_icon("menu-2", 32, "#f8f8f2")
        self.toggle_button.setIcon(icon)
        self.toggle_button.setIconSize(QSize(32, 32))
        # bump button height to match
        self.toggle_button.setMinimumHeight(120)

        # increase font size and left-align everything
        self.toggle_button.setFont(QFont("Segoe UI", 11))
        self.toggle_button.setStyleSheet(
            """
            text-align: left;
            padding-left: 16px;
        """
        )

        # Add widgets to left menu layout
        self.left_menu_layout.addWidget(self.top_menu)
        # Store nav buttons and their labels for collapse/expand
        self.nav_buttons = [
            (self.btn_home, "Home"),
            (self.btn_compress, "Compress"),
            (self.btn_extract, "Extract"),
            (self.btn_tools, "Tools"),
            (self.btn_theme, "Theme"),
            (self.btn_settings, "Settings"),
            (self.toggle_button, "Hide"),  # Add toggle button to the list
        ]

        # Add widgets to left menu layout
        self.left_menu_layout.addStretch()
        self.left_menu_layout.addWidget(self.bottom_menu)
        self.left_menu_layout.addWidget(self.toggle_button)

        # Content area
        self.content_area = QFrame()
        self.content_area.setObjectName("contentArea")

        # Content area layout
        self.content_area_layout = QVBoxLayout(self.content_area)
        self.content_area_layout.setContentsMargins(0, 0, 0, 0)
        self.content_area_layout.setSpacing(0)

        # We already have a title bar in the main layout,
        # so we don't need another one here

        # Content
        self.content = QFrame()
        self.content.setObjectName("content")

        # Content inner layout
        self.content_inner_layout = QVBoxLayout(self.content)
        self.content_inner_layout.setContentsMargins(10, 10, 10, 10)
        self.content_inner_layout.setSpacing(0)

        # Pages
        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")
        # Prevent scrollbars from appearing when resizing
        self.pages.setFrameShape(QFrame.NoFrame)  # Remove frame
        self.pages.setLineWidth(0)  # No border

        # Home page
        self.home_page = HomeTab()
        self.home_page.setObjectName("homePage")
        self.pages.addWidget(self.home_page)

        # Compression page with tabs
        self.compression_page = QTabWidget()
        self.compression_page.setObjectName("compressionPage")
        # Prevent scrollbars from appearing when resizing
        self.compression_page.setDocumentMode(True)  # More compact appearance
        self.compression_page.setUsesScrollButtons(False)  # Disable scroll buttons

        # Add the same tab styling as in settings_tab.py
        self.compression_page.setStyleSheet(
            """
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #444;
                border-bottom: none;
                border-radius: 4px 4px 0 0;
                background: #333;
                color: #ccc;
            }
            QTabBar::tab:selected {
                background: #6272a4;           /* active tab highlight */
                color: #f8f8f2;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                top: -1px;                     /* overlap with tabs */
            }
        """
        )

        # Add single file compression tab
        self.single_file_tab = CompressionTab()
        self.compression_page.addTab(self.single_file_tab, "Single File")

        # Add batch processing tab
        self.batch_tab = BatchTab()
        self.compression_page.addTab(self.batch_tab, "Batch Processing")

        self.pages.addWidget(self.compression_page)

        # Extraction page
        self.extraction_page = ExtractionTab()
        self.extraction_page.setObjectName("extractionPage")
        self.pages.addWidget(self.extraction_page)

        # Tools page
        from gui.tools_tab import ToolsTab

        self.tools_page = ToolsTab()
        self.pages.addWidget(self.tools_page)

        # Theme page
        self.theme_page = ThemeTab()
        self.theme_page.setObjectName("themePage")
        self.pages.addWidget(self.theme_page)

        # Settings page
        self.settings_page = SettingsTab()
        self.settings_page.setObjectName("settingsPage")
        self.pages.addWidget(self.settings_page)

        # Batch page is now included as a tab in the compression page

        # Add pages to content inner layout
        self.content_inner_layout.addWidget(self.pages)

        # Add content widget to content area layout
        self.content_area_layout.addWidget(self.content)

        # Create a custom resize handle with an icon that matches the application style
        self.resize_handle = QPushButton(self.content)
        self.resize_handle.setObjectName("resizeHandle")
        self.resize_handle.setFixedSize(16, 16)
        self.resize_handle.setFlat(True)

        # Use the provided SVG icon

        # Get theme colors for consistent styling
        colors = self.theme_config.get("colors", {})
        text_color = colors.get(
            "text", "#f8f8f2"
        )  # Use text color from theme (same as other icons)

        # Load the provided SVG icon
        icon = load_svg_icon("resize_icon_exact", 16, text_color)
        self.resize_handle.setIcon(icon)
        self.resize_handle.setIconSize(QSize(16, 16))

        # Make it transparent except for the icon
        self.resize_handle.setStyleSheet(
            "#resizeHandle { background-color: transparent; border: none; }"
            "#resizeHandle:hover { background-color: rgba(255, 255, 255, 0.1); }"
        )
        self.resize_handle.setCursor(Qt.CursorShape.SizeFDiagCursor)

        # Install event filter to handle mouse events for resizing
        self.resize_handle.installEventFilter(self)

        # We'll position it correctly in showEvent and resizeEvent

        # Add widgets to main content layout
        self.main_content_layout.addWidget(self.left_menu_bg)
        self.main_content_layout.addWidget(self.content_area)

        # Set initial page
        self.pages.setCurrentWidget(self.home_page)

        # Connect home page signals
        self.connect_home_signals()

        # Set up tools page
        # self.setup_tools_page()

    def connect_home_signals(self):
        """Connect home page signals."""
        # Connect home page signals to page changes
        self.home_page.compress_clicked.connect(
            lambda: self.change_page(self.compression_page)
        )
        self.home_page.extract_clicked.connect(
            lambda: self.change_page(self.extraction_page)
        )
        self.home_page.tools_clicked.connect(lambda: self.change_page(self.tools_page))
        self.home_page.batch_clicked.connect(self._navigate_to_batch_tab)

    def _navigate_to_batch_tab(self):
        """Navigate to the Batch Processing tab inside the compression page."""
        self.change_page(self.compression_page)
        self.compression_page.setCurrentWidget(self.batch_tab)

    # def setup_tools_page(self):
    #     """Set up the tools page."""
    #     # Plugin system removed in favor of direct ToolsTab integration.
    #     pass

    def connect_signals(self):
        """Connect widget signals to slots."""
        # Menu buttons
        self.btn_home.clicked.connect(lambda: self.change_page(self.home_page))
        self.btn_compress.clicked.connect(
            lambda: self.change_page(self.compression_page)
        )
        self.btn_extract.clicked.connect(lambda: self.change_page(self.extraction_page))
        self.btn_tools.clicked.connect(lambda: self.change_page(self.tools_page))
        self.btn_theme.clicked.connect(lambda: self.change_page(self.theme_page))
        self.btn_settings.clicked.connect(lambda: self.change_page(self.settings_page))

        # Toggle button
        self.toggle_button.clicked.connect(self.toggle_menu)

        # Connect title bar window buttons
        # Note: The title bar already connects its buttons to window actions internally
        # so we don't need to connect them again here

    def change_page(self, page):
        """Change the current page."""
        # Set current page
        self.pages.setCurrentWidget(page)

        # Check if sidebar is collapsed
        collapsed = self.left_menu_bg.width() <= self.collapsed_width

        # Update selected button
        buttons = [
            self.btn_home,
            self.btn_compress,
            self.btn_extract,
            self.btn_tools,
            self.btn_theme,
            self.btn_settings,
        ]

        # Map pages to buttons
        page_to_button = {
            self.home_page: self.btn_home,
            self.compression_page: self.btn_compress,
            self.extraction_page: self.btn_extract,
            self.tools_page: self.btn_tools,
            self.theme_page: self.btn_theme,
            self.settings_page: self.btn_settings,
        }

        # Get button for current page
        selected_button = page_to_button.get(page)

        # Reset all buttons
        for button in buttons:
            button.setProperty("selected", "false")

            # Apply appropriate styling based on collapsed state
            if collapsed:
                button.setStyleSheet("text-align: center;")
                button.setIconSize(
                    QSize(48, 48)
                )  # Make icons even larger in collapsed mode
            else:
                # Use fixed positioning for icons and text
                button.setStyleSheet("padding-left: 16px; text-align: left;")
                button.setIconSize(QSize(32, 32))

            # Update icon color
            icon_name = button.property("icon_name")
            if icon_name:
                button.setIcon(load_svg_icon(icon_name, 24, "#f8f8f2"))

        # Select the button
        if selected_button:
            selected_button.setProperty("selected", "true")

            # Get theme colors
            colors = self.theme_config.get("colors", {})
            primary = colors.get("primary", "#bd93f9")
            background = colors.get("background", "#282a36")

            # Apply appropriate styling based on collapsed state
            if collapsed:
                selected_button.setStyleSheet(
                    f"background-color: {primary}; color: {background};"
                    " text-align: center;"
                )
            else:
                # Use fixed positioning for icons and text (same as non-selected)
                selected_button.setStyleSheet(
                    f"background-color: {primary}; color: {background};"
                    " padding-left: 16px; text-align: left;"
                )

            # Update icon color
            icon_name = selected_button.property("icon_name")
            if icon_name:
                selected_button.setIcon(load_svg_icon(icon_name, 24, background))

    def toggle_menu(self):
        """Toggle the left menu between expanded and collapsed states."""
        # Get current and min/max widths
        width = self.left_menu_bg.width()
        min_width = self.collapsed_width  # Use the class variable we defined
        max_width = 240  # Match the suggested value

        # Set target width based on current state.
        # Use midpoint threshold so a mid-animation click still behaves correctly.
        midpoint = (min_width + max_width) // 2
        target_width = max_width if width <= midpoint else min_width

        # Once collapsed, remove the text; when expanded, restore it
        if target_width == min_width:
            self.toggle_button.setText("")  # icons-only
            # collapse - set center alignment and larger icons for all buttons
            for btn in (
                self.btn_home,
                self.btn_compress,
                self.btn_extract,
                self.btn_tools,
                self.btn_theme,
                self.btn_settings,
                self.toggle_button,
            ):
                btn.setStyleSheet("text-align: center;")
                btn.setIconSize(QSize(48, 48))  # Larger icons in collapsed mode
        else:
            self.toggle_button.setText("Hide")  # full label
            # expand - set left alignment and standard icon size for all buttons
            for btn in (
                self.btn_home,
                self.btn_compress,
                self.btn_extract,
                self.btn_tools,
                self.btn_theme,
                self.btn_settings,
                self.toggle_button,
            ):
                btn.setStyleSheet(
                    "padding-left: 16px; text-align: left;"
                )  # Fixed positioning
                btn.setIconSize(QSize(32, 32))

        # Create minimum width animation
        self.animation_min = QPropertyAnimation(self.left_menu_bg, b"minimumWidth")
        self.animation_min.setDuration(300)
        self.animation_min.setStartValue(width)
        self.animation_min.setEndValue(target_width)
        self.animation_min.setEasingCurve(QEasingCurve.InOutQuart)

        # Create maximum width animation
        self.animation_max = QPropertyAnimation(self.left_menu_bg, b"maximumWidth")
        self.animation_max.setDuration(300)
        self.animation_max.setStartValue(width)
        self.animation_max.setEndValue(target_width)
        self.animation_max.setEasingCurve(QEasingCurve.InOutQuart)

        # Start animations
        self.animation_min.start()
        self.animation_max.start()

        # When done, update each button's text & icon size
        self.animation_min.finished.connect(self._update_nav_button_states)

    def toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
            self.maximize_btn.setIcon(load_svg_icon("square", 16, "#f8f8f2"))
        else:
            self.showMaximized()
            self.maximize_btn.setIcon(load_svg_icon("copy", 16, "#f8f8f2"))

    def showEvent(self, event):
        """Handle show events.

        Args:
            event: Show event
        """
        # Call parent method
        super().showEvent(event)

        # Position the resize handle at the bottom-right corner
        # when window is first shown
        if hasattr(self, "resize_handle"):
            self._update_resize_handle_position()

    def resizeEvent(self, event):
        """Handle resize events.

        Args:
            event: Resize event
        """
        # Call parent method
        super().resizeEvent(event)

        # Position the resize handle at the bottom-right corner
        if hasattr(self, "resize_handle"):
            self._update_resize_handle_position()

        # Update resize grips (legacy support)
        resize_grips(self)

    def _update_resize_handle_position(self):
        """Update the position of the resize handle to the bottom-right corner."""
        # Use QTimer to ensure content has proper size when positioning
        QTimer.singleShot(
            0,
            lambda: self.resize_handle.move(
                self.content.width() - 16, self.content.height() - 16
            ),
        )

    def _update_nav_button_states(self):
        """Update button text and icon size based on sidebar collapse state."""
        # collapse if width <= min_width
        collapsed = self.left_menu_bg.width() <= self.collapsed_width
        for btn, label in self.nav_buttons:
            if collapsed:
                # hide text, bump icon
                btn.setText("")
                btn.setIconSize(
                    QSize(48, 48)
                )  # Increased from 40 to 48 for larger icons
                btn.setStyleSheet("text-align: center;")  # center align when collapsed
            else:
                # restore
                btn.setText(label)
                btn.setIconSize(QSize(32, 32))  # standard size with text
                btn.setStyleSheet(
                    "text-align: left; padding-left: 16px;"
                )  # left align when expanded

    def eventFilter(self, obj, event):
        """Filter events for objects that have installed an event filter.

        Args:
            obj: Object that sent the event
            event: Event object

        Returns:
            True if the event was handled, False otherwise
        """
        # Handle resize handle events
        if obj == self.resize_handle:
            if event.type() == event.Type.MouseButtonPress:
                # Store initial position and window size
                self._resize_start_pos = QPoint(
                    event.globalPosition().x(), event.globalPosition().y()
                )
                self._resize_start_size = self.size()
                return True
            elif event.type() == event.Type.MouseMove and hasattr(
                self, "_resize_start_pos"
            ):
                # Calculate the new size
                current_pos = QPoint(
                    event.globalPosition().x(), event.globalPosition().y()
                )
                delta = current_pos - self._resize_start_pos
                new_size = self._resize_start_size + QSize(delta.x(), delta.y())
                # Apply minimum size constraints
                new_size = QSize(
                    max(new_size.width(), 800), max(new_size.height(), 600)
                )
                # Resize the window
                self.resize(new_size)
                return True
            elif event.type() == event.Type.MouseButtonRelease:
                # Clean up
                if hasattr(self, "_resize_start_pos"):
                    delattr(self, "_resize_start_pos")
                if hasattr(self, "_resize_start_size"):
                    delattr(self, "_resize_start_size")
                return True
        # Pass the event to the parent class
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """Handle application close event.

        This method is called when the application is closed. It ensures that
        all temporary directories are cleaned up and all CHDMAN processes are
        terminated.

        Args:
            event: Close event
        """
        # Check if confirmation is required
        if SETTINGS.get("general", "confirm_exit", True):
            # Show confirmation dialog
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Are you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.No:
                event.ignore()
                return

        # Log the close event with a very visible message
        print("\n\n***** APPLICATION CLOSING - CLEANUP STARTING *****\n\n")

        # Clean up temporary directories in the compression tab
        if hasattr(self, "single_file_tab") and self.single_file_tab:
            print("Cleaning up compression tab resources...")
            try:
                self.single_file_tab.cleanup_temp_directories()
                print("Compression tab cleanup completed successfully")
            except Exception as e:
                print(f"ERROR during compression tab cleanup: {str(e)}")

        # Terminate any running CHDMAN processes
        try:
            if hasattr(self, "single_file_tab") and self.single_file_tab:
                self.single_file_tab.chd_manager.terminate_all_chdman_processes()
                print("CHDMAN processes terminated successfully")
        except Exception as e:
            print(f"ERROR terminating CHDMAN processes: {str(e)}")

        # Clean up resources
        print("Application closing, cleaning up resources...")

        # Clean up compression tab resources (temp directories and CHDMAN processes)
        if hasattr(self, "compression_tab") and self.compression_tab:
            print("Cleaning up compression tab resources...")
            self.compression_tab.cleanup()

        # Save settings
        if hasattr(SETTINGS, "save"):
            SETTINGS.save()

        # Call parent method
        super().closeEvent(event)


def log_uncaught_exception(exc_type, exc_value, exc_traceback):
    # Log to error.log
    with open("error.log", "a", encoding="utf-8") as f:
        f.write("\n--- Uncaught Exception ---\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    # Also print to stderr
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    # Show a message box if possible
    try:
        from PySide6.QtWidgets import QMessageBox

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Application Error")
        msg.setText("An unexpected error occurred. See error.log for details.")
        msg.setDetailedText(
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        )
        msg.exec()
    except Exception as e:
        logging.warning(f"Exception executing message dialog: {e}")


sys.excepthook = log_uncaught_exception


def main():
    """Main entry point for the application."""
    # Create application
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("RetroClamp")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("RetroClamp")
    app.setOrganizationDomain("retroclamp.org")

    # Create window and keep a reference to prevent garbage collection
    _ = MainWindow()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
