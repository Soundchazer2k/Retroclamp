"""RetroClamp - Modern GUI for CHDMAN operations.

This is the main entry point for the RetroClamp application, which provides
a modern, user-friendly interface for compressing, decompressing, and managing
disk images using the CHDMAN utility.
"""

import os
import sys
import traceback

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt
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
from modules.ui_functions import apply_theme, load_svg_icon  # Removed resize_grips

# Global settings
SETTINGS = AppSettings()  # Initialize globally
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
        # SETTINGS = AppSettings() # Removed, now initialized globally
        SETTINGS.set("logging", "enabled", True)
        SETTINGS.set("logging", "log_level", "DEBUG")

        # Initialize the DebugLogger with the loaded settings
        from core.debug_logger import get_logger

        self.logger = get_logger(SETTINGS)
        if self.logger:
            self.logger.info("main", "DebugLogger initialized with AppSettings.")

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
        self.setMinimumSize(800, 600)  # Explicitly set a smaller minimum window size
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

        # Initialize state flags for event handling
        self._resizing = False
        self._dragging = False

        # Install event filter on the title bar for dragging (must be after setup_ui)
        if hasattr(self, "title_bar"):
            self.title_bar.installEventFilter(self)
        else:
            if self.logger:  # DIAGNOSTIC
                self.logger.warning(
                    "main.__init__",
                    "self.title_bar not found after setup_ui. Dragging will not work.",
                )

        # Show the window - moved after filter installation and flag init
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
        # Consistent expanded width
        self.left_menu_bg.setMinimumWidth(240)
        self.left_menu_bg.setMaximumWidth(240)
        self.collapsed_width = 80

        # Layout for sidebar menu (vertical)
        self.left_menu_layout = QVBoxLayout(self.left_menu_bg)
        self.left_menu_layout.setContentsMargins(0, 12, 0, 12)
        self.left_menu_layout.setSpacing(8)

        # Top menu section (contains main navigation buttons)
        self.top_menu = QFrame()
        self.top_menu.setObjectName("topMenu")
        # This minimum height will be dictated by its children (buttons)
        self.top_menu.setMinimumHeight(0)

        # Layout for top menu buttons
        self.top_menu_layout = QVBoxLayout(self.top_menu)
        self.top_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.top_menu_layout.setSpacing(0)

        # Top menu buttons
        self.btn_home = QPushButton("Home")
        self.btn_home.setObjectName("btn_home")
        self.btn_home.setProperty("icon_name", "home")
        icon = load_svg_icon("home", 32, "#f8f8f2")
        self.btn_home.setIcon(icon)
        self.btn_home.setIconSize(QSize(32, 32))
        # REDUCED BUTTON HEIGHT FOR BETTER VERTICAL RESIZING
        self.btn_home.setMinimumHeight(45)  # Changed from 60

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
        icon = load_svg_icon("file-zip", 32, "#f8f8f2")
        self.btn_compress.setIcon(icon)
        self.btn_compress.setIconSize(QSize(32, 32))
        # REDUCED BUTTON HEIGHT
        self.btn_compress.setMinimumHeight(45)  # Changed from 60

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
        icon = load_svg_icon("file-export", 32, "#f8f8f2")
        self.btn_extract.setIcon(icon)
        self.btn_extract.setIconSize(QSize(32, 32))
        # REDUCED BUTTON HEIGHT
        self.btn_extract.setMinimumHeight(45)  # Changed from 60

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
        icon = load_svg_icon("tool", 32, "#f8f8f2")
        self.btn_tools.setIcon(icon)
        self.btn_tools.setIconSize(QSize(32, 32))
        # REDUCED BUTTON HEIGHT
        self.btn_tools.setMinimumHeight(45)  # Changed from 60

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
        icon = load_svg_icon("palette", 32, "#f8f8f2")
        self.btn_theme.setIcon(icon)
        self.btn_theme.setIconSize(QSize(32, 32))
        # REDUCED BUTTON HEIGHT
        self.btn_theme.setMinimumHeight(45)  # Changed from 60

        self.btn_theme.setFont(QFont("Segoe UI", 11))
        self.btn_theme.setStyleSheet(
            """
            text-align: left;
            padding-left: 16px;
        """
        )
        self.top_menu_layout.addWidget(self.btn_theme)

        # Menu spacer (this handles the vertical expansion/contraction between sections)
        self.menu_spacer = QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        # Bottom menu
        self.bottom_menu = QFrame()
        self.bottom_menu.setObjectName("bottomMenu")
        # This minimum height will be dictated by its children (buttons)
        self.bottom_menu.setMinimumHeight(0)

        # Bottom menu layout
        self.bottom_menu_layout = QVBoxLayout(self.bottom_menu)
        self.bottom_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_menu_layout.setSpacing(0)

        # Bottom menu buttons
        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setProperty("icon_name", "settings")
        icon = load_svg_icon("settings", 32, "#f8f8f2")
        self.btn_settings.setIcon(icon)
        self.btn_settings.setIconSize(QSize(32, 32))
        # REDUCED BUTTON HEIGHT
        self.btn_settings.setMinimumHeight(45)  # Changed from 60

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
        icon = load_svg_icon("menu-2", 32, "#f8f8f2")
        self.toggle_button.setIcon(icon)
        self.toggle_button.setIconSize(QSize(32, 32))
        # REDUCED BUTTON HEIGHT
        self.toggle_button.setMinimumHeight(45)  # Changed from 60

        self.toggle_button.setFont(QFont("Segoe UI", 11))
        self.toggle_button.setStyleSheet(
            """
            text-align: left;
            padding-left: 16px;
        """
        )

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
        self.left_menu_layout.addWidget(self.top_menu)
        self.left_menu_layout.addStretch()  # This is the spacer
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
        self.single_file_tab = CompressionTab(app_settings=SETTINGS)
        self.compression_page.addTab(self.single_file_tab, "Single File")

        # Add batch processing tab
        self.batch_tab = BatchTab(app_settings=SETTINGS)
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
        # MAKE RESIZE HANDLE CHILD OF CENTRAL_WIDGET FOR CORRECT POSITIONING
        self.resize_handle = QPushButton(self.central_widget)  # Changed parent here
        self.resize_handle.setObjectName("resizeHandle")
        self.resize_handle.setFixedSize(16, 16)
        self.resize_handle.setFlat(True)
        # self.resize_handle.setText("R") # DIAGNOSTIC: Set text to see if button appears - REMOVED

        # Use the provided SVG icon
        colors = self.theme_config.get("colors", {})
        text_color = colors.get("text", "#f8f8f2")
        icon = load_svg_icon("resize_icon_exact", 16, text_color)
        self.resize_handle.setIcon(icon)
        self.resize_handle.setIconSize(QSize(16, 16))

        # DIAGNOSTIC: Use a theme color for background instead of fully transparent
        bg_color = self.theme_config.get("colors", {}).get(
            "secondaryBackground", "#44475a"
        )
        hover_bg_color = "rgba(255, 255, 255, 0.1)"  # Keep hover distinct
        self.resize_handle.setStyleSheet(
            f"#resizeHandle {{ background-color: {bg_color}; border: none; }}"
            f"#resizeHandle:hover {{ background-color: {hover_bg_color}; }}"
        )
        self.resize_handle.setCursor(Qt.CursorShape.SizeFDiagCursor)

        # Install event filter to handle mouse events for resizing
        self.resize_handle.installEventFilter(self)
        if self.logger:  # DIAGNOSTIC
            self.logger.info(
                "main.setup_ui",
                "Resize handle created, text set to 'R', and event filter installed.",
            )  # DIAGNOSTIC

        # Add widgets to main content layout
        self.main_content_layout.addWidget(self.left_menu_bg)
        self.main_content_layout.addWidget(self.content_area)

        # Set initial page
        self.pages.setCurrentWidget(self.home_page)

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

        # Home page feature button signals
        if hasattr(self, "home_page"):
            self.home_page.compress_clicked.connect(
                lambda: self.change_page(self.compression_page)
            )
            self.home_page.extract_clicked.connect(
                lambda: self.change_page(self.extraction_page)
            )
            self.home_page.tools_clicked.connect(
                lambda: self.change_page(self.tools_page)
            )
            self.home_page.batch_clicked.connect(
                lambda: self.change_page(self.batch_page)
            )

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
                button.setIconSize(QSize(48, 48))
            else:
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
        min_width = self.collapsed_width
        max_width = 240

        # Set target width based on current state
        target_width = max_width if width == min_width else min_width

        # When target is collapsed, set text empty and adjust icon sizes for all buttons
        if target_width == min_width:
            for btn, _ in self.nav_buttons:
                btn.setText("")  # Remove text when collapsing
                btn.setIconSize(QSize(48, 48))  # Larger icons in collapsed mode
                btn.setStyleSheet("text-align: center;")  # Center align icons
        else:
            # When expanding, restore text and standard icon size
            for btn, label in self.nav_buttons:
                btn.setText(label)  # Restore text
                btn.setIconSize(QSize(32, 32))  # Standard icon size
                btn.setStyleSheet(
                    "padding-left: 16px; text-align: left;"
                )  # Left align text

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

        # The _update_nav_button_states is now integrated into the toggle_menu logic
        # We don't need to connect finished signal if text/icon updates are done upfront

    def toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
            self.maximize_btn.setIcon(load_svg_icon("square", 16, "#f8f8f2"))
        else:
            self.showMaximized()
            self.maximize_btn.setIcon(load_svg_icon("copy", 16, "#f8f8f2"))

    def showEvent(self, event):
        """Handle show events."""
        if self.logger:  # DIAGNOSTIC
            self.logger.debug("main.showEvent", "showEvent triggered.")  # DIAGNOSTIC
        self._update_resize_handle_position()
        super().showEvent(event)

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)  # Restore super call
        if self.logger:  # DIAGNOSTIC
            self.logger.debug(
                "main.resizeEvent", f"resizeEvent triggered. New size: {event.size()}."
            )  # DIAGNOSTIC
        self._update_resize_handle_position()

    def _update_resize_handle_position(self):
        """Update the position of the resize handle to the bottom-right corner."""
        if hasattr(self, "resize_handle") and hasattr(self, "central_widget"):
            parent_width = self.central_widget.width()
            parent_height = self.central_widget.height()
            handle_width = self.resize_handle.width()
            handle_height = self.resize_handle.height()

            # Position at the bottom-right corner of the central_widget
            x = parent_width - handle_width
            y = parent_height - handle_height
            self.resize_handle.move(x, y)
            self.resize_handle.raise_()  # DIAGNOSTIC: Ensure it's on top
            if self.logger:  # DIAGNOSTIC
                self.logger.debug(
                    "main._update_resize_handle_position",
                    f"Resize handle moved to ({x}, {y}) and raised.",
                )  # DIAGNOSTIC
        elif self.logger:
            self.logger.warning(
                "main._update_resize_handle_position",
                "Resize handle or central_widget not found for positioning.",
            )  # DIAGNOSTIC

    def eventFilter(self, obj, event):
        """Filter events for objects that have installed an event filter.

        Args:
            obj: Object that sent the event
            event: Event object

        Returns:
            True if the event was handled, False otherwise
        """
        try:
            # Handle resize handle events
            if obj == self.resize_handle:
                if event.type() == event.Type.MouseButtonPress:
                    self._resize_start_pos = QPoint(
                        event.globalPosition().x(), event.globalPosition().y()
                    )
                    self._resize_start_size = self.size()
                    self._resizing = True
                    event.accept()  # Accept event to prevent further processing
                    return True
                elif event.type() == event.Type.MouseMove and self._resizing:
                    current_pos = QPoint(
                        event.globalPosition().x(), event.globalPosition().y()
                    )
                    delta = current_pos - self._resize_start_pos

                    # Calculate raw new dimensions
                    new_width = self._resize_start_size.width() + delta.x()
                    new_height = self._resize_start_size.height() + delta.y()

                    # DIAGNOSTIC LOGGING
                    if self.logger:
                        self.logger.debug(
                            "MainWindow.eventFilter.resize",
                            f"StartSize: {self._resize_start_size}, Delta: {delta}, "
                            f"Raw NewSize: ({new_width}, {new_height})",
                        )

                    # Apply minimum size constraints
                    min_w = self.minimumWidth()  # From setMinimumSize or default 0
                    min_h = self.minimumHeight()  # From setMinimumSize or default 0

                    # If min_w/min_h are still 0 (not explicitly set to something > 0),
                    # then fall back to minimumSizeHint.
                    if min_w == 0:
                        min_w = self.minimumSizeHint().width()
                    if min_h == 0:
                        min_h = self.minimumSizeHint().height()

                    if self.logger:
                        self.logger.debug(
                            "MainWindow.eventFilter",
                            f"Using effective minimums for constraint: width={min_w}, height={min_h}",
                        )

                    # Diagnostic prints
                    constrained_width = max(new_width, min_w)
                    constrained_height = max(new_height, min_h)

                    # DIAGNOSTIC LOGGING
                    if self.logger:
                        self.logger.debug(
                            "MainWindow.eventFilter.resize",
                            f"Constrained NewSize: ({constrained_width}, {constrained_height})",
                        )

                    self.resize(constrained_width, constrained_height)
                    event.accept()
                    return True
                elif event.type() == event.Type.MouseButtonRelease:
                    self._resizing = False
                    if hasattr(self, "_resize_start_pos"):
                        del self._resize_start_pos
                    # Do not clear _resize_start_size here, it's just a snapshot
                    event.accept()
                    return True

            # Handle title bar events for dragging
            elif obj == self.title_bar:
                if event.type() == event.Type.MouseButtonPress:
                    if event.button() == Qt.MouseButton.LeftButton:
                        self._dragging = True
                        self._drag_start_position = (
                            event.globalPosition().toPoint()
                            - self.frameGeometry().topLeft()
                        )
                        event.accept()
                        return True
                elif event.type() == event.Type.MouseMove and self._dragging:
                    self.move(
                        event.globalPosition().toPoint() - self._drag_start_position
                    )
                    event.accept()
                    return True
                elif event.type() == event.Type.MouseButtonRelease:
                    if event.button() == Qt.MouseButton.LeftButton:
                        self._dragging = False
                        event.accept()
                        return True
        except AttributeError as e:
            log_msg = f"AttributeError in eventFilter: {e} on object {obj}, event type {event.type()}"
            if self.logger:
                self.logger.error("MainWindow.eventFilter", log_msg)
            else:
                print(log_msg)
            # For an error loop, returning False might be safer than re-raising
            # or letting it fall through to super if the error is persistent.
            return False  # Attempt to break loop by not consuming event if error occurs
        except Exception as e:
            log_msg = f"Unexpected error in eventFilter: {e} on object {obj}, event type {event.type()}"
            if self.logger:
                self.logger.error("MainWindow.eventFilter", log_msg)
            else:
                print(log_msg)
            return False  # Attempt to break loop

        # Pass unhandled events to the parent class's event filter
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
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        self.logger.info("main", "Application closing - cleanup starting.")

        # Terminate any running CHDMAN processes
        try:
            if hasattr(self, "compression_page") and self.compression_page.chd_manager:
                self.logger.info(
                    "main", "Terminating CHDMAN processes from compression_page."
                )
                self.compression_page.chd_manager.terminate_all_processes()
            if hasattr(self, "extraction_page") and self.extraction_page.chd_manager:
                self.logger.info(
                    "main", "Terminating CHDMAN processes from extraction_page."
                )
                self.extraction_page.chd_manager.terminate_all_processes()
            # Add other pages if they also use chd_manager directly
        except Exception as e:
            self.logger.error("main", f"Error terminating CHDMAN processes: {str(e)}")

        # Clean up temporary directories
        # Example for extraction_page, adapt for other pages if needed
        if hasattr(self, "extraction_page") and hasattr(
            self.extraction_page, "cleanup_temp_directories"
        ):
            try:
                self.logger.info(
                    "main", "Cleaning up extraction_page temporary directories."
                )
                self.extraction_page.cleanup_temp_directories()
            except Exception as e:
                self.logger.error(
                    "main", f"Error during extraction_page cleanup: {str(e)}"
                )

        # Add cleanup for other tabs like batch_tab if they have similar methods
        if hasattr(self, "batch_page") and hasattr(
            self.batch_page, "cleanup_temp_directories"
        ):
            try:
                self.logger.info(
                    "main", "Cleaning up batch_page temporary directories."
                )
                self.batch_page.cleanup_temp_directories()
            except Exception as e:
                self.logger.error("main", f"Error during batch_page cleanup: {str(e)}")

        # Save settings
        if hasattr(SETTINGS, "save"):
            self.logger.info("main", "Saving application settings.")
            SETTINGS.save()

        super().closeEvent(event)


def log_uncaught_exception(exc_type, exc_value, exc_traceback):
    # Log to error.log
    with open("error.log", "a", encoding="utf-8") as f:
        f.write("\n--- Uncaught Exception ---\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    traceback.print_exception(
        exc_type, exc_value, exc_traceback
    )  # Also print to stderr
    try:
        from PySide6.QtWidgets import QMessageBox

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Application Error")
        msg.setText("An unexpected error occurred. See error.log for details.")
        msg.setDetailedText(
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        )
        msg.exec()
    except Exception as e:
        # Use standard logging if DebugLogger isn't available or fails here
        import logging

        logging.warning(f"Exception executing message dialog: {e}")


sys.excepthook = log_uncaught_exception


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("RetroClamp")
    app.setApplicationVersion(
        SETTINGS.get("general", "version", "1.2.0-dev")
    )  # Use version from settings
    app.setOrganizationName("RetroClamp")
    app.setOrganizationDomain("retroclamp.org")

    _ = MainWindow()  # Create window and keep a reference
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
