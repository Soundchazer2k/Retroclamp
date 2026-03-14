"""Sidebar navigation widget and Debug log dialog."""

from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Debug Dialog
# ---------------------------------------------------------------------------


class DebugDialog(QDialog):
    """Modeless dialog that tails the RetroClamp log file in real time."""

    _BG = "#282a36"
    _SURFACE = "#313444"
    _FG = "#f8f8f2"
    _MUTED = "#6272a4"
    _PURPLE = "#bd93f9"
    _RED = "#ff5555"
    _GREEN = "#50fa7b"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Debug Log")
        self.resize(720, 460)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setModal(False)
        self.setStyleSheet(f"background: {self._BG}; color: {self._FG};")

        self._log_path: str | None = self._resolve_log_path()
        self._last_size: int = 0

        self._setup_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._poll_log)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Path label
        path_text = self._log_path or "(log path unavailable)"
        path_lbl = QLabel(f"Log: {path_text}")
        path_lbl.setStyleSheet(
            f"color: {self._MUTED}; font-size: 11px; background: transparent;"
        )
        path_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(path_lbl)

        # Text area
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text.setFont(font)
        self._text.setStyleSheet(
            f"QPlainTextEdit {{"
            f"  background: {self._SURFACE}; color: {self._FG};"
            f"  border: 1px solid #44475a; border-radius: 6px;"
            f"  padding: 6px;"
            f"}}"
        )
        root.addWidget(self._text)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        clear_btn = QPushButton("Clear Log")
        clear_btn.setFixedHeight(30)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(self._btn_style(self._RED))
        clear_btn.clicked.connect(self._clear_log)

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setFixedHeight(30)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(self._btn_style(self._PURPLE))
        copy_btn.clicked.connect(self._copy_log)

        btn_row.addWidget(clear_btn)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.close)
        close_box.setStyleSheet(
            f"QPushButton {{ color: {self._FG}; background: #44475a;"
            f" border-radius: 4px; padding: 4px 12px; }}"
            f"QPushButton:hover {{ background: #6272a4; }}"
        )
        btn_row.addWidget(close_box)
        root.addLayout(btn_row)

    @staticmethod
    def _btn_style(color: str) -> str:
        return (
            f"QPushButton {{ background: transparent; color: {color};"
            f" border: 1px solid {color}; border-radius: 4px; padding: 0 12px;"
            f" font-size: 12px; }}"
            f"QPushButton:hover {{ background: rgba(255,255,255,0.06); }}"
        )

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_log_path() -> str | None:
        """Try to retrieve the log file path from DebugLogger."""
        try:
            from core.debug_logger import get_logger  # type: ignore[import]
            from modules.app_settings import AppSettings  # type: ignore[import]

            logger = get_logger(AppSettings())
            if logger is not None:
                return logger.get_log_file_path()
        except Exception:  # noqa: BLE001
            pass
        # Fallback: look for retroclamp.log next to the executable / cwd
        candidates = [
            os.path.join(os.path.expanduser("~"), "retroclamp.log"),
            os.path.join(os.getcwd(), "retroclamp.log"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def _poll_log(self) -> None:
        """Read any new bytes appended since last poll."""
        if not self._log_path or not os.path.exists(self._log_path):
            return
        try:
            size = os.path.getsize(self._log_path)
            if size == self._last_size:
                return
            if size < self._last_size:
                # File was truncated/cleared
                self._text.clear()
                self._last_size = 0

            with open(self._log_path, encoding="utf-8", errors="replace") as fh:
                fh.seek(self._last_size)
                new_content = fh.read()

            self._last_size = size
            if new_content:
                self._text.moveCursor(self._text.textCursor().MoveOperation.End)
                self._text.insertPlainText(new_content)
                self._text.moveCursor(self._text.textCursor().MoveOperation.End)
        except OSError:
            pass

    def _clear_log(self) -> None:
        """Truncate the log file on disk and clear the text area."""
        if self._log_path and os.path.exists(self._log_path):
            try:
                with open(self._log_path, "w", encoding="utf-8") as fh:
                    fh.write("")
                self._last_size = 0
                self._text.clear()
            except OSError as exc:
                self._text.appendPlainText(f"\n[Could not clear log: {exc}]")

    def _copy_log(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self._text.toPlainText())

    # ------------------------------------------------------------------
    # Show / hide
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        # Do a full read on first show
        if self._log_path and os.path.exists(self._log_path):
            try:
                with open(self._log_path, encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                self._text.setPlainText(content)
                self._last_size = len(content.encode("utf-8", errors="replace"))
                self._text.moveCursor(self._text.textCursor().MoveOperation.End)
            except OSError:
                pass
        self._timer.start()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Nav item widget
# ---------------------------------------------------------------------------


class _NavItem(QWidget):
    """Single sidebar navigation entry: icon + label."""

    clicked = Signal()

    _FG = "#f8f8f2"
    _MUTED = "#6272a4"
    _SURFACE = "#313444"
    _PURPLE = "#bd93f9"

    def __init__(
        self,
        icon: str,
        label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._active = False
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Active indicator bar (3px wide)
        self._indicator = QFrame()
        self._indicator.setFixedWidth(3)
        self._indicator.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._indicator)

        # Icon + text area
        inner = QHBoxLayout()
        inner.setContentsMargins(12, 0, 12, 0)
        inner.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(QSize(22, 22))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            "background: transparent; border: none; font-size: 16px;"
        )
        inner.addWidget(icon_lbl)

        self._text_lbl = QLabel(label)
        self._text_lbl.setStyleSheet(
            f"color: {self._MUTED}; background: transparent; border: none;"
            " font-size: 13px;"
        )
        inner.addWidget(self._text_lbl)
        inner.addStretch()

        layout.addLayout(inner)
        self._apply_state()

    # ------------------------------------------------------------------

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_state()

    def _apply_state(self) -> None:
        if self._active:
            self._indicator.setStyleSheet(f"background: {self._PURPLE}; border: none;")
            self.setStyleSheet(f"background: {self._SURFACE};")
            self._text_lbl.setStyleSheet(
                f"color: {self._FG}; background: transparent; border: none;"
                " font-size: 13px; font-weight: 600;"
            )
        else:
            self._indicator.setStyleSheet("background: transparent; border: none;")
            self.setStyleSheet("background: transparent;")
            self._text_lbl.setStyleSheet(
                f"color: {self._MUTED}; background: transparent; border: none;"
                " font-size: 13px;"
            )

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        if not self._active:
            self.setStyleSheet("background: rgba(255,255,255,0.04);")

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        if not self._active:
            self.setStyleSheet("background: transparent;")


# ---------------------------------------------------------------------------
# SidebarWidget
# ---------------------------------------------------------------------------

NAV_ITEMS: list[tuple[str, str, str]] = [
    ("home", "🏠", "Home"),
    ("compress", "💿", "Compress"),
    ("batch", "📦", "Batch"),
    ("tools", "🔧", "Tools"),
    ("settings", "⚙", "Settings"),
]


class SidebarWidget(QWidget):
    """Fixed 220 px sidebar with icon+text nav items and a footer.

    Emits ``navigation_requested(key)`` when the user clicks a nav item.
    """

    navigation_requested = Signal(str)

    _BG = "#21222c"
    _FG = "#f8f8f2"
    _MUTED = "#6272a4"
    _BORDER = "#44475a"
    _PURPLE = "#bd93f9"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: dict[str, _NavItem] = {}
        self._debug_dialog: DebugDialog | None = None
        self.setFixedWidth(220)
        self.setStyleSheet(
            f"SidebarWidget {{ background: {self._BG};"
            f" border-right: 1px solid {self._BORDER}; }}"
        )
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Brand header
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet(
            f"background: {self._BG}; border-bottom: 1px solid {self._BORDER};"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        brand_lbl = QLabel("RetroClamp")
        brand_lbl.setStyleSheet(
            f"color: {self._FG}; font-size: 16px; font-weight: 700;"
            " background: transparent; border: none;"
        )
        header_layout.addWidget(brand_lbl)
        header_layout.addStretch()
        root.addWidget(header)

        # Nav items
        nav_container = QWidget()
        nav_container.setStyleSheet(f"background: {self._BG};")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(2)

        for key, icon, label in NAV_ITEMS:
            item = _NavItem(icon, label, parent=nav_container)
            item.clicked.connect(lambda k=key: self._on_nav_clicked(k))
            self._items[key] = item
            nav_layout.addWidget(item)

        nav_layout.addStretch()
        root.addWidget(nav_container, stretch=1)

        # Footer
        footer = QWidget()
        footer.setFixedHeight(64)
        footer.setStyleSheet(
            f"background: {self._BG}; border-top: 1px solid {self._BORDER};"
        )
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 16, 8)
        footer_layout.setSpacing(4)

        debug_btn = QPushButton("🐛 Debug Log")
        debug_btn.setFixedHeight(26)
        debug_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        debug_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; color: {self._MUTED};"
            f"  border: 1px solid {self._BORDER}; border-radius: 4px;"
            f"  font-size: 11px; text-align: left; padding-left: 8px;"
            f"}}"
            f"QPushButton:hover {{ color: {self._FG}; border-color: {self._MUTED}; }}"
        )
        debug_btn.clicked.connect(self._open_debug_dialog)
        footer_layout.addWidget(debug_btn)

        try:
            from version import __version__  # type: ignore[import]

            ver_text = f"v{__version__}"
        except Exception:  # noqa: BLE001
            ver_text = ""

        ver_lbl = QLabel(ver_text)
        ver_lbl.setStyleSheet(
            f"color: {self._MUTED}; font-size: 10px; background: transparent; border: none;"
        )
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer_layout.addWidget(ver_lbl)

        root.addWidget(footer)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_nav_clicked(self, key: str) -> None:
        self.set_active(key)
        self.navigation_requested.emit(key)

    def set_active(self, key: str) -> None:
        """Highlight the nav item matching *key*."""
        for k, item in self._items.items():
            item.set_active(k == key)

    # ------------------------------------------------------------------
    # Debug dialog
    # ------------------------------------------------------------------

    def _open_debug_dialog(self) -> None:
        if self._debug_dialog is None:
            self._debug_dialog = DebugDialog(parent=None)
        self._debug_dialog.show()
        self._debug_dialog.raise_()
        self._debug_dialog.activateWindow()
