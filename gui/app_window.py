"""AppWindow — main application shell.

Wires the SidebarWidget, QStackedWidget, and all view panels together.
The core/ and modules/ backends are left untouched; only the GUI layer
is managed here.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QSettings, QSize
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from gui.sidebar_widget import SidebarWidget
from gui.views import BatchView, CompressionView, HomeView, SettingsView, ToolsView

# ---------------------------------------------------------------------------
# Key → stack-index mapping
# Handles both "compress" (sidebar) and "compression" (HomeView cards).
# ---------------------------------------------------------------------------
_KEY_INDEX: dict[str, int] = {
    "home": 0,
    "compress": 1,
    "compression": 1,  # HomeView emits "compression"
    "batch": 2,
    "tools": 3,
    "settings": 4,
}

# Reverse map for setting the sidebar active item from an index
_INDEX_KEY: dict[int, str] = {
    0: "home",
    1: "compress",
    2: "batch",
    3: "tools",
    4: "settings",
}


class AppWindow(QMainWindow):
    """Main application window.

    Layout
    ------
    Central widget (QWidget, horizontal layout)
    ├── SidebarWidget  (fixed 220 px)
    └── QStackedWidget
        ├── 0 – HomeView
        ├── 1 – CompressionView
        ├── 2 – BatchView
        ├── 3 – ToolsView
        └── 4 – SettingsView
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._settings = QSettings("RetroClamp", "RetroClamp")
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        self._restore_state()

        # Start on the Home page
        self._navigate("home")

    # ------------------------------------------------------------------
    # Window bootstrap
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowTitle("RetroClamp")
        self.setMinimumSize(QSize(800, 600))
        self.resize(1200, 800)
        self._apply_icon()

    def _apply_icon(self) -> None:
        """Set window icon from QtAwesome or fallback resource."""
        try:
            import qtawesome as qta  # type: ignore[import]
            from PySide6.QtGui import QIcon

            icon = qta.icon("fa6s.compact-disc", color="#bd93f9")
            self.setWindowIcon(icon)
        except Exception:  # noqa: BLE001
            try:
                from PySide6.QtGui import QIcon

                icon_path = os.path.join(
                    os.path.dirname(__file__), "..", "resources", "icon.ico"
                )
                if os.path.exists(icon_path):
                    self.setWindowIcon(QIcon(icon_path))
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        container = QWidget()
        container.setObjectName("AppContainer")
        self.setCentralWidget(container)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        self._sidebar = SidebarWidget()
        layout.addWidget(self._sidebar)

        # Stacked content area
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, stretch=1)

        # Build views in index order
        self._home_view = HomeView()
        self._compression_view = CompressionView()
        self._batch_view = BatchView()
        self._tools_view = ToolsView()
        self._settings_view = SettingsView()

        self._stack.addWidget(self._home_view)  # 0
        self._stack.addWidget(self._compression_view)  # 1
        self._stack.addWidget(self._batch_view)  # 2
        self._stack.addWidget(self._tools_view)  # 3
        self._stack.addWidget(self._settings_view)  # 4

        # Populate recent files on the Home page
        self._home_view.set_recent_files(self._load_recent_files())

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._sidebar.navigation_requested.connect(self._navigate)
        self._home_view.navigate_to.connect(self._navigate)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _navigate(self, key: str) -> None:
        """Switch the stack to the view identified by *key*."""
        index = _KEY_INDEX.get(key, 0)
        self._stack.setCurrentIndex(index)
        sidebar_key = _INDEX_KEY.get(index, "home")
        self._sidebar.set_active(sidebar_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_file(self, path: str) -> None:
        """Navigate to the Compression view and pre-populate *path*."""
        self._navigate("compress")
        load = getattr(self._compression_view, "load_file", None)
        if callable(load):
            load(path)
        self._add_recent_file(path)

    # ------------------------------------------------------------------
    # Recent files helpers
    # ------------------------------------------------------------------

    def _load_recent_files(self) -> list[str]:
        raw = self._settings.value("history/recent_files", [])
        if isinstance(raw, str):
            return [raw] if raw else []
        return list(raw) if raw else []  # type: ignore[call-overload]

    def _add_recent_file(self, path: str) -> None:
        files: list[str] = self._load_recent_files()
        # Keep path at front, remove duplicate if present
        if path in files:
            files.remove(path)
        files.insert(0, path)
        files = files[:20]  # cap at 20 entries
        self._settings.setValue("history/recent_files", files)
        self._home_view.set_recent_files(files)

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _restore_state(self) -> None:
        geometry = self._settings.value("window/geometry")
        if geometry:
            try:
                self.restoreGeometry(geometry)
            except Exception:  # noqa: BLE001
                pass
        state = self._settings.value("window/state")
        if state:
            try:
                self.restoreState(state)
            except Exception:  # noqa: BLE001
                pass

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/state", self.saveState())
        super().closeEvent(event)
