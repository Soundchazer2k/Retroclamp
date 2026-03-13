"""Home view — landing screen with ActionCard navigation and recent files."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.components.action_card import ActionCard
from gui.components.section_label import SectionLabel

try:
    from version import __version__
except ImportError:
    __version__ = "dev"


class HomeView(QWidget):
    """Landing screen featuring a 2-column ActionCard grid.

    Signals
    -------
    navigate_to(str)
        Emitted when a card is clicked. The string payload is the
        view key: 'compression', 'batch', 'tools', 'settings'.
    """

    navigate_to = Signal(str)

    # Dracula palette
    _BG = "#282a36"
    _FG = "#f8f8f2"
    _MUTED = "#6272a4"
    _SURFACE = "#313444"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {self._BG};")
        self._recent_files: list[str] = []
        self._setup_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_recent_files(self, paths: list[str]) -> None:
        """Populate the recent files list."""
        self._recent_files = paths
        self._refresh_recent()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background-color: {self._BG};")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Header
        layout.addWidget(self._build_header())

        # Card section label
        layout.addWidget(SectionLabel("Quick Actions"))

        # Card grid
        layout.addWidget(self._build_card_grid())

        # Recent files section
        layout.addWidget(SectionLabel("Recent Files"))
        self._recent_container = self._build_recent_section()
        layout.addWidget(self._recent_container)

        layout.addStretch()

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 8)
        h.setSpacing(12)

        title = QLabel("RetroClamp")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {self._FG}; background: transparent;")
        h.addWidget(title)

        version_label = QLabel(f"v{__version__}")
        version_font = QFont()
        version_font.setPointSize(11)
        version_label.setFont(version_font)
        version_label.setStyleSheet(f"color: {self._MUTED}; background: transparent;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
        h.addWidget(version_label)

        h.addStretch()
        return w

    def _build_card_grid(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        grid = QHBoxLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)

        cards = [
            ("🗜️", "Compress", "Convert disk images to CHD format.", "compression"),
            ("📦", "Batch", "Process multiple files at once.", "batch"),
            ("🔧", "Tools", "M3U generator, BIOS validator & more.", "tools"),
            ("⚙️", "Settings", "Configure CHDMAN path and preferences.", "settings"),
        ]

        for icon, title, desc, key in cards:
            card = ActionCard(icon, title, desc)
            card.clicked.connect(lambda k=key: self.navigate_to.emit(k))
            grid.addWidget(card)

        grid.addStretch()
        return w

    def _build_recent_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {self._SURFACE}; border-radius: 8px;")
        self._recent_layout = QVBoxLayout(w)
        self._recent_layout.setContentsMargins(16, 12, 16, 12)
        self._recent_layout.setSpacing(4)
        self._refresh_recent()
        return w

    def _refresh_recent(self) -> None:
        """Rebuild the recent-files label list."""
        # Clear existing children
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._recent_files:
            placeholder = QLabel("No recent files.")
            placeholder.setStyleSheet(
                f"color: {self._MUTED}; background: transparent; border: none;"
            )
            self._recent_layout.addWidget(placeholder)
            return

        for path in self._recent_files[:10]:
            lbl = QLabel(path)
            lbl.setStyleSheet(
                f"color: {self._FG}; background: transparent; border: none;"
                "font-size: 11px;"
            )
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._recent_layout.addWidget(lbl)
