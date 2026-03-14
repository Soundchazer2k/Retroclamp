"""RetroClamp - Modern GUI for CHDMAN operations.

This is the main entry point for the RetroClamp application, which provides
a modern, user-friendly interface for compressing, decompressing, and managing
disk images using the CHDMAN utility.
"""

import os
import platform
import sys
import traceback
from typing import Any, Optional

# Modern theming (with fallbacks)
try:
    import qdarkstyle
except ImportError:
    qdarkstyle = None

try:
    import qtawesome as qta
except ImportError:
    qta = None

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QSettings,
    QSize,
    Qt,
)
from PySide6.QtGui import QAction, QCloseEvent, QFont, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizeGrip,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# Set environment variables for high DPI scaling
os.environ["QT_FONT_DPI"] = "96"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from gui.app_window import AppWindow
from gui.batch_tab import BatchTab
from gui.compression_tab import CompressionTab
from gui.extraction_tab import ExtractionTab
from gui.home_tab import HomeTab
from gui.settings_tab import SettingsTab
from gui.theme_tab import ThemeTab
from gui.tools_tab import ToolsTab
from modules.app_settings import AppSettings

# Import or create fallback for load_svg_icon function
try:
    from modules.ui_functions import load_svg_icon
except ImportError:

    def load_svg_icon(name: str, size: int = 24, color_hex: str = "#ffffff") -> QIcon:  # type: ignore[misc]
        """Fallback function for missing load_svg_icon."""
        return QIcon()  # Return empty icon


# Global settings
SETTINGS = AppSettings()  # Initialize globally

# Global variable to store available QtAwesome icons
AVAILABLE_QTA_ICONS = {}


class MainWindow(QMainWindow):
    """Main window for the RetroClamp application.

    This class represents the main application window, containing the sidebar menu,
    content area, and various UI elements.
    """

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        # --- Mypy Type Hint Declarations ---
        # Note: title_bar removed - using native window controls
        self.central_widget: Optional[QWidget] = None
        self.main_layout: Optional[QHBoxLayout] = (
            None  # Simplified to horizontal layout
        )
        self.left_menu_bg: Optional[QFrame] = None  # Corresponds to Mypy's 'sidebar'
        self.left_menu_layout: Optional[QVBoxLayout] = None
        self.top_menu: Optional[QFrame] = None
        self.top_menu_layout: Optional[QVBoxLayout] = None
        self.stacked_widget: Optional[QStackedWidget] = None
        self.home_tab: Optional[HomeTab] = None
        self.compression_tab: Optional[CompressionTab] = None
        self.extraction_tab: Optional[ExtractionTab] = None
        self.batch_tab: Optional[BatchTab] = None
        self.settings_tab: Optional[SettingsTab] = None  # For the settings UI/page
        self.theme_tab: Optional[ThemeTab] = None  # For the theme UI/page
        self.tools_tab: Optional[ToolsTab] = None

        self.status_bar: Optional[QStatusBar] = None
        self.status_label: Optional[QLabel] = None
        self.status_grip: Optional[QSizeGrip] = None

        self.sidebar_toggle_btn: Optional[QPushButton] = None
        # For buttons like self.btn_home, if they are accessed outside setup_ui and cause errors:
        self.btn_home: Optional[QPushButton] = None
        self.btn_compress: Optional[QPushButton] = None
        self.btn_extract: Optional[QPushButton] = None
        self.btn_batch: Optional[QPushButton] = None
        self.btn_tools: Optional[QPushButton] = None
        self.btn_settings: Optional[QPushButton] = None
        self.btn_theme: Optional[QPushButton] = None
        self.toggle_button: Optional[QPushButton] = (
            None  # Common name for sidebar toggle
        )

        self.settings_dialog: Optional[SettingsTab] = (
            None  # If settings is a dialog opened from here
        )
        self.app_settings: AppSettings = SETTINGS  # Explicitly type and assign
        self.update_checker: Optional[Any] = None
        self.update_dialog: Optional[Any] = None  # Or QDialog if it's a simple dialog
        # --- End Mypy Type Hint Declarations ---

        # Initialize settings
        SETTINGS.set("logging", "enabled", True)
        SETTINGS.set("logging", "log_level", "DEBUG")

        # Initialize QSettings for cross-platform configuration
        self.qt_settings = QSettings("RetroClamp", "RetroClamp")

        # Initialize the DebugLogger with the loaded settings
        from core.debug_logger import get_logger

        self.logger = get_logger(SETTINGS)
        if self.logger:
            self.logger.info("main", "RetroClamp started with QDarkStyleSheet theming.")

        # Set up window properties (simplified - using native window controls)
        self.setWindowTitle("RetroClamp")
        # Use QtAwesome icon if available, otherwise fallback
        if qta:
            try:
                self.setWindowIcon(qta.icon("fa6s.compact-disc"))
            except Exception:
                self.setWindowIcon(QIcon("resources/icon.ico"))
        else:
            self.setWindowIcon(QIcon("resources/icon.ico"))
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)

        # Use native window controls (no custom frameless window)

        # Set up platform-specific integration
        self.setup_platform_integration()

        # Set up UI (simplified - no custom theme application needed)
        self.setup_ui()
        self.connect_signals()

        # Restore window state
        self.restore_window_state()

        # Note: Window will be shown by main() function

    def get_best_icon(self, icon_candidates):
        """Get the best available icon from a list of candidates."""
        for icon_name in icon_candidates:
            if icon_name in AVAILABLE_QTA_ICONS:
                print(
                    f"📋 DEBUG: Selected '{icon_name}' from candidates {icon_candidates}"
                )
                return icon_name
        # Return first candidate as fallback if none found in QtAwesome
        fallback = icon_candidates[0] if icon_candidates else "fa5s.circle"
        print(
            f"📋 DEBUG: No QtAwesome match for {icon_candidates}, using fallback '{fallback}'"
        )
        return fallback

    def initialize_qtawesome(self):
        """Initialize QtAwesome fonts and verify they're working."""
        if not qta:
            if self.logger:
                self.logger.warning("main", "QtAwesome not available")
            return

        try:
            print("🔍 DEBUG: Initializing QtAwesome fonts...")

            # Force QtAwesome to load fonts by requesting an icon
            qta.icon("fa5s.home")

            # Check if initialization worked
            if hasattr(qta, "_instance") and qta._instance():
                instance = qta._instance()
                if hasattr(instance, "charmap") and instance.charmap:
                    charmap_size = len(instance.charmap)
                    print(f"✅ DEBUG: QtAwesome initialized with {charmap_size} icons")

                    # Check available prefixes
                    prefixes = set()
                    for key in list(instance.charmap.keys())[:100]:
                        if "." in key:
                            prefix = key.split(".")[0]
                            prefixes.add(prefix)
                    print(f"✅ DEBUG: Available prefixes: {sorted(prefixes)}")

                    # Store available prefixes for later use
                    self.available_icon_prefixes = prefixes

                    if self.logger:
                        self.logger.info(
                            "main",
                            f"QtAwesome initialized with prefixes: {sorted(prefixes)}",
                        )
                else:
                    print("❌ DEBUG: QtAwesome charmap is empty")
                    self.available_icon_prefixes = set()
            else:
                print("❌ DEBUG: QtAwesome instance not created")
                self.available_icon_prefixes = set()

        except Exception as e:
            print(f"❌ DEBUG: QtAwesome initialization failed: {e}")
            self.available_icon_prefixes = set()
            if self.logger:
                self.logger.error("main", f"QtAwesome initialization failed: {e}")

    def create_toggle_icon(self, direction: str) -> QIcon:
        """Create a toggle icon (chevron) using simple drawing that matches Tabler icon colors."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QPainter, QPen, QPixmap

        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Use high contrast white for WCAG AAA compliance
        # 21:1 contrast ratio against dark backgrounds
        pen = QPen(
            QColor("#ffffff"),
            2,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)

        center_x, center_y = size // 2, size // 2

        if direction == "right":
            # Right-pointing chevron
            points = [
                QPoint(center_x - 6, center_y - 8),
                QPoint(center_x + 6, center_y),
                QPoint(center_x - 6, center_y + 8),
            ]
        else:  # left
            # Left-pointing chevron
            points = [
                QPoint(center_x + 6, center_y - 8),
                QPoint(center_x - 6, center_y),
                QPoint(center_x + 6, center_y + 8),
            ]

        # Draw the chevron lines
        painter.drawLine(points[0], points[1])
        painter.drawLine(points[1], points[2])

        painter.end()
        return QIcon(pixmap)

    def load_tabler_icon(self, icon_name: str) -> QIcon:
        """Load a Tabler SVG icon from the resources directory."""
        # Map button names to available Tabler icons
        tabler_icon_map = {
            "Home": "home.svg",
            "Compress": "file-zip.svg",
            "Extract": "file-export.svg",
            "Tools": "tool.svg",
            "Theme": "file-plus.svg",  # Use file-plus as alternative for theme
            "Settings": "disc.svg",  # Use disc as alternative for settings
            "Hide": "chevron-left",  # Use custom chevron instead of menu-2.svg
        }

        svg_filename = tabler_icon_map.get(icon_name, "home.svg")

        # Handle special case for chevron icons
        if svg_filename.startswith("chevron-"):
            direction = svg_filename.split("-")[1]  # "left" or "right"
            print(f"✅ DEBUG: Creating custom chevron icon: {direction}")
            return self.create_toggle_icon(direction)

        # Try multiple locations for the SVG file
        possible_paths = [
            f"resources/icons/tabler-icons-svg/{svg_filename}",
            f"resources/icons/tabler-icons/icons/outline/{svg_filename}",
            f"resources/icons/tabler-icons/icons/filled/{svg_filename.replace('.svg', '')}.svg",
        ]

        for svg_path in possible_paths:
            if os.path.exists(svg_path):
                print(f"✅ DEBUG: Found Tabler icon at {svg_path}")
                return QIcon(svg_path)

        # If no SVG found, create a simple fallback
        print(f"⚠️ DEBUG: No Tabler icon found for '{icon_name}', using fallback")
        return self.create_simple_fallback_icon(icon_name)

    def create_simple_fallback_icon(self, text: str) -> QIcon:
        """Create a simple fallback icon when SVG isn't found."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap

        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw simple colored square
        color = QColor("#bd93f9")
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color, 1))
        painter.drawRoundedRect(4, 4, size - 8, size - 8, 4, 4)

        # Draw letter
        painter.setPen(QPen(QColor("#f8f8f2")))
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text[0].upper())

        painter.end()
        return QIcon(pixmap)

    def create_nav_button(self, text: str, icon_name: str) -> QPushButton:
        """Create a navigation button using existing Tabler SVG icons."""
        btn = QPushButton(text)
        btn.setObjectName(f"btn_{text.lower()}")

        print(f"🔍 DEBUG: Creating button '{text}' with Tabler SVG icons")

        # Load Tabler SVG icon from resources
        icon = self.load_tabler_icon(text)
        btn.setIcon(icon)

        print(f"✅ DEBUG: Loaded icon for '{text}'")

        btn.setIconSize(QSize(36, 36))  # Larger icons for better visibility
        btn.setMinimumHeight(56)  # WCAG minimum touch target size
        btn.setFont(
            QFont("Segoe UI", 12, QFont.Weight.Medium)
        )  # Larger, accessible font
        return btn

    def setup_platform_integration(self):
        """Set up platform-specific integration features."""
        current_platform = platform.system()

        if current_platform == "Darwin":  # macOS
            self.setup_macos_integration()
        elif current_platform == "Windows":
            self.setup_windows_integration()
        elif current_platform == "Linux":
            self.setup_linux_integration()

    def setup_macos_integration(self):
        """Set up macOS-specific features."""
        # Enable native macOS global menu bar
        self.menuBar().setNativeMenuBar(True)

        # Set up macOS-style menu structure
        self.setup_macos_menus()

        if self.logger:
            self.logger.info("main", "macOS integration enabled: global menu bar")

    def setup_windows_integration(self):
        """Set up Windows-specific features."""
        # Windows keeps menu bar in window (default Qt behavior)
        self.menuBar().setNativeMenuBar(False)

        # Set up standard Windows menu structure
        self.setup_standard_menus()

        if self.logger:
            self.logger.info("main", "Windows integration enabled: in-window menu bar")

    def setup_linux_integration(self):
        """Set up Linux-specific features."""
        # Linux uses window menu bar (default Qt behavior)
        self.menuBar().setNativeMenuBar(False)

        # Set up standard menu structure
        self.setup_standard_menus()

        if self.logger:
            self.logger.info("main", "Linux integration enabled: in-window menu bar")

    def setup_macos_menus(self):
        """Set up macOS-style menu structure with proper Preferences placement."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")

        # Determine modifier key for current platform
        modifier = (
            Qt.MetaModifier if platform.system() == "Darwin" else Qt.ControlModifier
        )

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence(modifier | Qt.Key_O))
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit RetroClamp", self)
        quit_action.setShortcut(QKeySequence(modifier | Qt.Key_Q))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = self.menuBar().addMenu("&View")

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut(QKeySequence.Refresh)
        refresh_action.triggered.connect(self.refresh_current_view)
        view_menu.addAction(refresh_action)

        toggle_sidebar_action = QAction("&Toggle Sidebar", self)
        toggle_sidebar_action.setShortcut(QKeySequence(modifier | Qt.Key_B))
        toggle_sidebar_action.triggered.connect(self.toggle_menu)
        view_menu.addAction(toggle_sidebar_action)

        # Help menu
        help_menu = self.menuBar().addMenu("&Help")

        help_action = QAction("&RetroClamp Help", self)
        help_action.setShortcut(QKeySequence.HelpContents)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        about_action = QAction("&About RetroClamp", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # On macOS, Preferences will automatically move to the app menu
        # But we still add it to a menu for other platforms
        if platform.system() == "Darwin":
            # Add preferences to the application menu (handled automatically by Qt)
            prefs_action = QAction("Preferences...", self)
            prefs_action.setMenuRole(QAction.PreferencesRole)
            prefs_action.setShortcut(QKeySequence(Qt.MetaModifier | Qt.Key_Comma))
            prefs_action.triggered.connect(lambda: self.change_page(self.settings_page))
            # Add to any menu - Qt will move it to the app menu automatically
            file_menu.addAction(prefs_action)

    def setup_standard_menus(self):
        """Set up standard menu structure for Windows/Linux."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")

        # Determine modifier key for current platform
        modifier = (
            Qt.MetaModifier if platform.system() == "Darwin" else Qt.ControlModifier
        )

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence(modifier | Qt.Key_O))
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # Preferences in File menu for Windows/Linux
        prefs_action = QAction("&Preferences...", self)
        prefs_action.setShortcut(QKeySequence(modifier | Qt.Key_Comma))
        prefs_action.triggered.connect(lambda: self.change_page(self.settings_page))
        file_menu.addAction(prefs_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence(modifier | Qt.Key_Q))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = self.menuBar().addMenu("&View")

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut(QKeySequence.Refresh)
        refresh_action.triggered.connect(self.refresh_current_view)
        view_menu.addAction(refresh_action)

        toggle_sidebar_action = QAction("&Toggle Sidebar", self)
        toggle_sidebar_action.setShortcut(QKeySequence(modifier | Qt.Key_B))
        toggle_sidebar_action.triggered.connect(self.toggle_menu)
        view_menu.addAction(toggle_sidebar_action)

        # Help menu
        help_menu = self.menuBar().addMenu("&Help")

        help_action = QAction("&RetroClamp Help", self)
        help_action.setShortcut(QKeySequence.HelpContents)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        about_action = QAction("&About RetroClamp", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_ui(self):
        """Set up the user interface."""
        # Create central widget for the main window
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout (simplified - no custom title bar needed)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

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

        # Top menu buttons - use best available icons
        self.btn_home = self.create_nav_button(
            "Home", self.get_best_icon(["fa5s.home", "fa5s.house"])
        )
        self.top_menu_layout.addWidget(self.btn_home)

        self.btn_compress = self.create_nav_button(
            "Compress",
            self.get_best_icon(
                ["fa5s.file-archive", "fa5s.compress", "fa5s.folder-open"]
            ),
        )
        self.top_menu_layout.addWidget(self.btn_compress)

        self.btn_extract = self.create_nav_button(
            "Extract",
            self.get_best_icon(["fa5s.file-export", "fa5s.download", "fa5s.upload"]),
        )
        self.top_menu_layout.addWidget(self.btn_extract)

        self.btn_tools = self.create_nav_button(
            "Tools", self.get_best_icon(["fa5s.wrench", "fa5s.tools", "fa5s.cog"])
        )
        self.top_menu_layout.addWidget(self.btn_tools)

        self.btn_theme = self.create_nav_button(
            "Theme",
            self.get_best_icon(["fa5s.palette", "fa5s.paint-brush", "fa5s.brush"]),
        )
        self.top_menu_layout.addWidget(self.btn_theme)

        # Menu spacer (this handles the vertical expansion/contraction between sections)
        self.menu_spacer = QSpacerItem(
            20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
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

        # Bottom menu buttons with best available icons
        self.btn_settings = self.create_nav_button(
            "Settings", self.get_best_icon(["fa5s.cog", "fa5s.gear", "fa5s.wrench"])
        )
        self.bottom_menu_layout.addWidget(self.btn_settings)

        # Toggle button with best available icon
        self.toggle_button = self.create_nav_button(
            "Hide", self.get_best_icon(["fa5s.chevron-left", "fa5s.arrow-left"])
        )
        self.toggle_button.setObjectName("toggleButton")
        # Ensure toggle button has consistent styling
        self.toggle_button.setMaximumHeight(45)
        self.toggle_button.setMinimumHeight(45)

        # Store nav buttons with their labels and track which have icons vs Unicode fallbacks
        self.nav_buttons = [
            (
                self.btn_home,
                "Home",
                self.btn_home.text(),
                not self.btn_home.icon().isNull(),
            ),
            (
                self.btn_compress,
                "Compress",
                self.btn_compress.text(),
                not self.btn_compress.icon().isNull(),
            ),
            (
                self.btn_extract,
                "Extract",
                self.btn_extract.text(),
                not self.btn_extract.icon().isNull(),
            ),
            (
                self.btn_tools,
                "Tools",
                self.btn_tools.text(),
                not self.btn_tools.icon().isNull(),
            ),
            (
                self.btn_theme,
                "Theme",
                self.btn_theme.text(),
                not self.btn_theme.icon().isNull(),
            ),
            (
                self.btn_settings,
                "Settings",
                self.btn_settings.text(),
                not self.btn_settings.icon().isNull(),
            ),
            (
                self.toggle_button,
                "Hide",
                self.toggle_button.text(),
                not self.toggle_button.icon().isNull(),
            ),
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

        # Remove per-tab stylesheet - using unified global stylesheet instead

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

        # Note: Custom resize handle removed - using native window controls

        # Add widgets to main layout (simplified)
        self.main_layout.addWidget(self.left_menu_bg)
        self.main_layout.addWidget(self.content_area)

        # Set initial page
        self.pages.setCurrentWidget(self.home_page)

        # Set up additional keyboard shortcuts for navigation
        self.setup_keyboard_shortcuts()

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
        """Change the current page (simplified - no custom theming needed)."""
        # Set current page
        self.pages.setCurrentWidget(page)

        # Simple button state management (QDarkStyleSheet handles styling)
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

        # Reset all buttons (let QDarkStyleSheet handle styling)
        for button in buttons:
            button.setProperty("selected", False)
            button.style().unpolish(button)
            button.style().polish(button)

        # Select the current button
        if selected_button:
            selected_button.setProperty("selected", True)
            selected_button.style().unpolish(selected_button)
            selected_button.style().polish(selected_button)

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
            for btn, label, original_text, has_icon in self.nav_buttons:
                if has_icon:
                    # For buttons with real icons, remove text completely
                    btn.setText("")
                else:
                    # For buttons with Unicode fallbacks, keep only the emoji
                    # Extract emoji from text like "🏠 Home" -> "🏠"
                    if " " in original_text:
                        emoji = original_text.split(" ")[0]
                        btn.setText(emoji)
                    else:
                        # Fallback if no space found
                        btn.setText(original_text[0] if original_text else "●")

                # Set consistent styling for collapsed mode
                if btn == self.toggle_button:
                    # Special handling for toggle button to prevent oversizing
                    btn.setIconSize(QSize(24, 24))
                    btn.setStyleSheet(
                        "text-align: center; font-size: 16px; max-height: 45px;"
                    )
                else:
                    btn.setIconSize(QSize(32, 32))  # Standard collapsed icon size
                    btn.setStyleSheet(
                        "text-align: center; font-size: 18px;"
                    )  # Center align icons
                btn.setToolTip(label)  # Show label as tooltip when collapsed
            # Change toggle button to "expand" icon
            expand_icon = self.create_toggle_icon("right")
            self.toggle_button.setIcon(expand_icon)
            self.toggle_button.setToolTip("Expand Menu")
            print("✅ DEBUG: Set toggle button to expand (right chevron)")
        else:
            # When expanding, restore original text and standard icon size
            for btn, label, original_text, has_icon in self.nav_buttons:
                if has_icon:
                    # For buttons with real icons, restore clean text
                    btn.setText(label)
                else:
                    # For buttons with Unicode fallbacks, restore original text with emoji
                    btn.setText(original_text)
                btn.setIconSize(QSize(32, 32))  # Standard icon size
                btn.setStyleSheet(
                    "padding-left: 16px; text-align: left; font-size: 11px;"
                )  # Left align text
                btn.setToolTip("")  # Clear tooltip when expanded
            # Change toggle button to "collapse" icon
            collapse_icon = self.create_toggle_icon("left")
            self.toggle_button.setIcon(collapse_icon)
            self.toggle_button.setToolTip("Hide Menu")
            print("✅ DEBUG: Set toggle button to collapse (left chevron)")

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

    def setup_keyboard_shortcuts(self):
        """Set up platform-appropriate keyboard shortcuts."""
        # Determine modifier key for current platform
        modifier = (
            Qt.MetaModifier if platform.system() == "Darwin" else Qt.ControlModifier
        )

        # Navigation shortcuts
        QShortcut(
            QKeySequence(modifier | Qt.Key_1),
            self,
            lambda: self.change_page(self.home_page),
        )
        QShortcut(
            QKeySequence(modifier | Qt.Key_2),
            self,
            lambda: self.change_page(self.compression_page),
        )
        QShortcut(
            QKeySequence(modifier | Qt.Key_3),
            self,
            lambda: self.change_page(self.extraction_page),
        )
        QShortcut(
            QKeySequence(modifier | Qt.Key_4),
            self,
            lambda: self.change_page(self.tools_page),
        )
        QShortcut(
            QKeySequence(modifier | Qt.Key_5),
            self,
            lambda: self.change_page(self.theme_page),
        )

        # Function key shortcuts
        QShortcut(QKeySequence(Qt.Key_F1), self, self.show_help)
        QShortcut(QKeySequence(Qt.Key_F5), self, self.refresh_current_view)

        if self.logger:
            platform_name = "Cmd" if platform.system() == "Darwin" else "Ctrl"
            self.logger.info(
                "main", f"Keyboard shortcuts configured for {platform_name} key"
            )

    def open_file_dialog(self):
        """Open a native file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "All Files (*);;CHD Files (*.chd);;ISO Files (*.iso);;BIN Files (*.bin)",
        )

        if file_path:
            # Switch to compression page and set the file
            self.change_page(self.compression_page)
            # TODO: Set the file in the compression tab
            if self.logger:
                self.logger.info("main", f"File selected via menu: {file_path}")

    def refresh_current_view(self):
        """Refresh the current view/page."""
        current_widget = self.pages.currentWidget()

        # Call refresh method if available on current page
        if hasattr(current_widget, "refresh"):
            current_widget.refresh()
        elif hasattr(current_widget, "reload"):
            current_widget.reload()

        if self.logger:
            self.logger.info(
                "main", f"Refreshed current view: {current_widget.__class__.__name__}"
            )

    def show_help(self):
        """Show help dialog or documentation."""
        QMessageBox.information(
            self,
            "RetroClamp Help",
            "RetroClamp is a modern GUI for CHDMAN operations.\n\n"
            "Navigation:\n"
            "• Use the sidebar to switch between different tools\n"
            "• Ctrl+1-5 (Cmd+1-5 on macOS) for quick navigation\n"
            "• F1 for help, F5 to refresh\n\n"
            "For detailed documentation, visit:\n"
            "https://github.com/Soundchazer2k/Retroclamp",
        )

    def show_about(self):
        """Show about dialog."""
        version = SETTINGS.get("general", "version", "1.2.0-dev")
        QMessageBox.about(
            self,
            "About RetroClamp",
            f"<h3>RetroClamp {version}</h3>"
            "<p>A modern, cross-platform GUI for CHDMAN operations.</p>"
            "<p>Built with PySide6 and QDarkStyleSheet.</p>"
            "<p>© 2024 RetroClamp Project</p>",
        )

    def restore_window_state(self):
        """Restore window size, position, and state from settings."""
        try:
            # Restore geometry (size and position)
            geometry = self.qt_settings.value("window_geometry")
            if geometry:
                self.restoreGeometry(geometry)

            # Restore window state (maximized, etc.)
            window_state = self.qt_settings.value("window_state")
            if window_state:
                self.restoreState(window_state)

            if self.logger:
                self.logger.info("main", "Window state restored from settings")

        except Exception as e:
            if self.logger:
                self.logger.warning("main", f"Could not restore window state: {e}")

    def save_window_state(self):
        """Save window size, position, and state to settings."""
        try:
            # Save geometry (size and position)
            self.qt_settings.setValue("window_geometry", self.saveGeometry())

            # Save window state (maximized, etc.)
            self.qt_settings.setValue("window_state", self.saveState())

            if self.logger:
                self.logger.info("main", "Window state saved to settings")

        except Exception as e:
            if self.logger:
                self.logger.warning("main", f"Could not save window state: {e}")

    # Note: toggle_maximize method removed - using native window controls

    def closeEvent(self, event: QCloseEvent) -> None:
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
            # Handle compression tab (inside QTabWidget)
            if hasattr(self, "single_file_tab") and hasattr(
                self.single_file_tab, "chd_manager"
            ):
                if self.single_file_tab.chd_manager:
                    self.logger.info(
                        "main", "Terminating CHDMAN processes from single_file_tab."
                    )
                    self.single_file_tab.chd_manager.terminate_all_processes()

            if hasattr(self, "batch_tab") and hasattr(self.batch_tab, "chd_manager"):
                if self.batch_tab.chd_manager:  # type: ignore[union-attr]
                    self.logger.info(
                        "main", "Terminating CHDMAN processes from batch_tab."
                    )
                    self.batch_tab.chd_manager.terminate_all_processes()  # type: ignore[union-attr]

            if hasattr(self, "extraction_page") and hasattr(
                self.extraction_page, "chd_manager"
            ):
                if self.extraction_page.chd_manager:
                    self.logger.info(
                        "main", "Terminating CHDMAN processes from extraction_page."
                    )
                    self.extraction_page.chd_manager.terminate_all_processes()
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
        if hasattr(self, "batch_tab") and hasattr(
            self.batch_tab, "cleanup_temp_directories"
        ):
            try:
                self.logger.info("main", "Cleaning up batch_tab temporary directories.")
                self.batch_tab.cleanup_temp_directories()  # type: ignore[union-attr]
            except Exception as e:
                self.logger.error("main", f"Error during batch_tab cleanup: {str(e)}")

        # Save window state before closing
        self.save_window_state()

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
    # Ensure stdout/stderr can handle emoji and Unicode on Windows cp1252 consoles
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    app = QApplication(sys.argv)
    app.setApplicationName("RetroClamp")
    app.setApplicationVersion(
        SETTINGS.get("general", "version", "1.2.0-dev")
    )  # Use version from settings
    app.setOrganizationName("RetroClamp")
    app.setOrganizationDomain("retroclamp.org")

    # Force QtAwesome to initialize immediately after QApplication creation
    if qta:
        print("[DEBUG] Force-initializing QtAwesome fonts...")
        try:
            # Force QtAwesome instance creation and font loading
            qta._instance()
            # Test with a simple icon to ensure fonts are loaded
            qta.icon("fa5s.home")
            print("[DEBUG] QtAwesome force-initialized")

            # Check if fonts actually loaded
            if hasattr(qta, "_instance") and qta._instance():
                instance = qta._instance()
                if hasattr(instance, "charmap") and instance.charmap:
                    charmap_size = len(instance.charmap)
                    print(f"✅ DEBUG: QtAwesome loaded {charmap_size} icons")

                    # Check available prefixes
                    prefixes = set()
                    for key in list(instance.charmap.keys()):
                        if "." in key:
                            prefix = key.split(".")[0]
                            prefixes.add(prefix)
                    print(f"✅ DEBUG: Available prefixes: {sorted(prefixes)}")

                    # Find icons we actually need that exist
                    needed_icons = [
                        "fa5s.home",
                        "fa5s.house",
                        "fa5s.file-archive",
                        "fa5s.compress",
                        "fa5s.folder-open",
                        "fa5s.file-export",
                        "fa5s.download",
                        "fa5s.upload",
                        "fa5s.wrench",
                        "fa5s.tools",
                        "fa5s.cog",
                        "fa5s.palette",
                        "fa5s.paint-brush",
                        "fa5s.brush",
                        "fa5s.chevron-left",
                        "fa5s.chevron-right",
                        "fa5s.arrow-left",
                        "fa5s.arrow-right",
                    ]

                    print("🔍 DEBUG: Checking for icons we need:")
                    available_icons = {}
                    for icon in needed_icons:
                        exists = icon in instance.charmap
                        print(f"  {'✅' if exists else '❌'} {icon}: {exists}")
                        if exists:
                            available_icons[icon] = True

                    # Store available icons for use in create_nav_button
                    global AVAILABLE_QTA_ICONS
                    AVAILABLE_QTA_ICONS = available_icons

                else:
                    print("❌ DEBUG: QtAwesome charmap still empty after force init")
        except Exception as e:
            print(f"❌ DEBUG: QtAwesome force initialization failed: {e}")
    else:
        print("❌ DEBUG: QtAwesome not available")

    # Apply WCAG-compliant stylesheet for accessibility
    try:
        # Load WCAG-compliant stylesheet first
        with open("wcag_compliant_styles.qss", encoding="utf-8") as f:
            wcag_stylesheet = f.read()

        app.setStyleSheet(wcag_stylesheet)
        print("✅ Applied WCAG AA/AAA compliant stylesheet")

    except FileNotFoundError:
        # Fallback to unified stylesheet
        try:
            with open("unified_styles.qss", encoding="utf-8") as f:
                unified_stylesheet = f.read()

            app.setStyleSheet(unified_stylesheet)
            print("✅ Applied unified RetroClamp stylesheet (fallback)")

        except FileNotFoundError:
            # Fallback to theme manager approach
            try:
                from core.theme_manager import ThemeManager

                theme_manager = ThemeManager()

                # Load saved theme or default to dark
                saved_theme = theme_manager.load_saved_theme()
                print(f"✅ Applied '{saved_theme}' theme via ThemeManager")

            except ImportError:
                # Final fallback to QDarkStyleSheet
                if qdarkstyle:
                    try:
                        base_stylesheet = qdarkstyle.load_stylesheet_pyside6()
                        app.setStyleSheet(base_stylesheet)
                        print("✅ Applied QDarkStyleSheet fallback")
                    except Exception as e:
                        print(
                            f"Warning: Error loading QDarkStyleSheet: {e}. Using default styling."
                        )
                else:
                    print("Warning: Using default Qt styling.")

    except Exception as e:
        print(f"Warning: Error loading stylesheet: {e}. Using default styling.")

    # Create window after stylesheet is applied
    window = AppWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
