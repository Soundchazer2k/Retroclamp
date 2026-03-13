"""Compression view — two-column layout with drop zone and live log stream.

Left panel (~55%): source file drop zone → file list, settings, action buttons.
Right panel (~45%): monospace log stream, status bar.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
_BG = "#282a36"
_SURFACE = "#313444"
_SURFACE_R = "#353749"
_BORDER = "#44475a"
_FG = "#f8f8f2"
_MUTED = "#6272a4"
_PURPLE = "#bd93f9"
_GREEN = "#50fa7b"
_RED = "#ff5555"
_CYAN = "#8be9fd"
_LOG_BG = "#1e1f29"

# ---------------------------------------------------------------------------
# Console profiles — algorithms + hunk sizes per media type
# ---------------------------------------------------------------------------
_CONSOLE_PROFILES: dict[str, tuple[str, int, str]] = {
    # (algorithms, hunk_size, media_label)
    "Auto-detect": ("", 0, ""),
    "PS1": ("cdlz,cdzl,cdfl", 19584, "CD"),
    "PS2": ("zlib,huff", 2048, "DVD"),
    "Dreamcast": ("cdlz,cdzl,cdfl", 19584, "CD"),
    "Saturn": ("cdlz,cdzl,cdfl", 19584, "CD"),
    "CD — Default": ("cdlz,cdzl,cdfl", 19584, "CD"),
    "CD — Fast": ("cdlz", 19584, "CD"),
    "DVD — Default": ("zlib,huff", 2048, "DVD"),
    "DVD — Best": ("lzma", 2048, "DVD"),
    "Hard Disk": ("zlib,huff", 4096, "Hard Disk"),
}


# ---------------------------------------------------------------------------
# Status chip colours
# ---------------------------------------------------------------------------
_CHIP_COLORS = {
    "Queued": _MUTED,
    "Compressing": _CYAN,
    "Extracting": _CYAN,
    "Done": _GREEN,
    "Error": _RED,
}


def _chip_style(color: str) -> str:
    return (
        f"color: {color}; background: {color}22; border: 1px solid {color}44;"
        " border-radius: 3px; padding: 1px 6px; font-size: 11px;"
    )


# ---------------------------------------------------------------------------
# Helper — styled section label
# ---------------------------------------------------------------------------
def _section_lbl(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color: {_MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        " background: transparent; border: none;"
    )
    return lbl


# ---------------------------------------------------------------------------
# Drop Zone widget
# ---------------------------------------------------------------------------
class _DropZone(QFrame):
    """Dashed-border drop target. Disappears once files are loaded."""

    files_dropped = Signal(list)  # list[str]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setStyleSheet(
            f"QFrame {{ border: 1.5px dashed {_BORDER}; border-radius: 8px;"
            f" background: {_SURFACE}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel("💿")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 32px; background: transparent; border: none;")
        layout.addWidget(icon)

        hint = QLabel("Drop disc images here  or  Browse")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(
            f"color: {_MUTED}; font-size: 13px; background: transparent; border: none;"
        )
        layout.addWidget(hint)

        browse_btn = QPushButton("Browse files")
        browse_btn.setFixedWidth(120)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_PURPLE};"
            f" border: 1px solid {_PURPLE}; border-radius: 4px; padding: 4px 12px; }}"
            f" QPushButton:hover {{ background: {_PURPLE}22; }}"
        )
        browse_btn.clicked.connect(self._browse)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _browse(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select disc images",
            "",
            "Disc images (*.cue *.bin *.iso *.img *.cdr *.gdi *.chd);;All files (*)",
        )
        if paths:
            self.files_dropped.emit(paths)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()


# ---------------------------------------------------------------------------
# File row data
# ---------------------------------------------------------------------------
_COL_NAME = 0
_COL_SIZE = 1
_COL_STATUS = 2
_COL_REMOVE = 3


class _FileTable(QTableWidget):
    """Compact file list replacing the drop zone once files are added."""

    remove_requested = Signal(int)  # row index

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, 4, parent)
        self.setHorizontalHeaderLabels(["File", "Size", "Status", ""])
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(
            _COL_NAME,
            self.horizontalHeader().ResizeMode.Stretch,
        )
        self.horizontalHeader().setSectionResizeMode(
            _COL_SIZE, self.horizontalHeader().ResizeMode.ResizeToContents
        )
        self.horizontalHeader().setSectionResizeMode(
            _COL_STATUS, self.horizontalHeader().ResizeMode.ResizeToContents
        )
        self.horizontalHeader().setSectionResizeMode(
            _COL_REMOVE, self.horizontalHeader().ResizeMode.Fixed
        )
        self.setColumnWidth(_COL_REMOVE, 28)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setStyleSheet(
            f"QTableWidget {{ background: {_SURFACE}; color: {_FG}; border: none;"
            f" alternate-background-color: {_SURFACE_R}; gridline-color: {_BORDER}; }}"
            f" QTableWidget::item {{ padding: 4px 6px; border: none; }}"
            f" QHeaderView::section {{ background: {_SURFACE_R}; color: {_MUTED};"
            f" border: none; padding: 4px 6px; font-size: 11px; font-weight: 600; }}"
            f" QScrollBar:vertical {{ background: {_BG}; width: 8px; }}"
            f" QScrollBar::handle:vertical {{ background: {_BORDER}; border-radius: 4px; }}"
        )

    def add_file(self, path: str) -> int:
        """Add a file row; return the row index."""
        row: int = int(self.rowCount())
        self.insertRow(row)
        name_item = QTableWidgetItem(Path(path).name)
        name_item.setData(Qt.ItemDataRole.UserRole, path)
        name_item.setToolTip(path)
        self.setItem(row, _COL_NAME, name_item)

        try:
            size = os.path.getsize(path)
            size_str = _fmt_size(size)
        except OSError:
            size_str = "?"
        self.setItem(row, _COL_SIZE, QTableWidgetItem(size_str))

        status_item = QTableWidgetItem("Queued")
        status_item.setForeground(
            __import__("PySide6.QtGui", fromlist=["QColor"]).QColor(_MUTED)
        )
        self.setItem(row, _COL_STATUS, status_item)

        remove_btn = QToolButton()
        remove_btn.setText("✕")
        remove_btn.setFixedSize(22, 22)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet(
            f"QToolButton {{ color: {_MUTED}; background: transparent; border: none; }}"
            f" QToolButton:hover {{ color: {_RED}; }}"
        )
        remove_btn.clicked.connect(lambda checked=False, r=row: self._on_remove(r))
        self.setCellWidget(row, _COL_REMOVE, remove_btn)

        return row

    def _on_remove(self, row: int) -> None:
        self.remove_requested.emit(row)

    def set_status(self, row: int, status: str) -> None:
        if row >= self.rowCount():
            return
        color = _CHIP_COLORS.get(status, _FG)
        item = self.item(row, _COL_STATUS)
        if item:
            item.setText(status)
            item.setForeground(
                __import__("PySide6.QtGui", fromlist=["QColor"]).QColor(color)
            )

    def file_paths(self) -> list[str]:
        paths = []
        for r in range(self.rowCount()):
            it = self.item(r, _COL_NAME)
            if it is not None:
                paths.append(str(it.data(Qt.ItemDataRole.UserRole)))
        return paths


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n //= 1024
    return f"{n:.1f} TB"


# ===========================================================================
# CompressionView
# ===========================================================================
class CompressionView(QWidget):
    """Two-column compression view per the GUI card redesign spec §3.

    Left (~55%): source file drop zone / file list + settings + action buttons.
    Right (~45%): monospace live log stream + status bar.
    """

    # Public API for HomeView navigation
    def load_file(self, path: str) -> None:
        """Pre-populate the file list with *path* (called from HomeView recent files)."""
        self._add_files([path])

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")

        self._files: list[str] = []  # ordered list of source paths
        self._running = False
        self._completed = 0
        self._errors = 0
        self._active_row_signals: dict[int, object] = {}

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header
        header = QLabel("Compress / Extract")
        header.setStyleSheet(
            f"color: {_FG}; font-size: 20px; font-weight: 700; background: transparent;"
        )
        root.addWidget(header)

        # Splitter — left 55 %, right 45 %
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {_BORDER}; }}")
        root.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([550, 450])

    # ------------------------------------------------------------------
    # Left panel
    # ------------------------------------------------------------------

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background: {_SURFACE}; border-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # --- Drop zone / file list stack ---
        layout.addWidget(_section_lbl("Source Files"))

        self._drop_zone = _DropZone()
        self._drop_zone.files_dropped.connect(self._add_files)
        layout.addWidget(self._drop_zone)

        self._file_table = _FileTable()
        self._file_table.remove_requested.connect(self._remove_file)
        self._file_table.hide()
        layout.addWidget(self._file_table)

        # Add more files button (shown when file list is visible)
        self._add_more_btn = QPushButton("＋ Add more files")
        self._add_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_more_btn.setFixedHeight(28)
        self._add_more_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUTED};"
            f" border: 1px dashed {_BORDER}; border-radius: 4px; font-size: 11px; }}"
            f" QPushButton:hover {{ color: {_FG}; border-color: {_MUTED}; }}"
        )
        self._add_more_btn.clicked.connect(self._browse_more)
        self._add_more_btn.hide()
        layout.addWidget(self._add_more_btn)

        # --- Settings section ---
        layout.addWidget(_section_lbl("Settings"))

        # Output path
        out_row = QHBoxLayout()
        out_row.setSpacing(6)
        out_lbl = QLabel("Output:")
        out_lbl.setStyleSheet(
            f"color: {_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        out_lbl.setFixedWidth(52)
        out_row.addWidget(out_lbl)

        self._out_combo = QComboBox()
        self._out_combo.addItems(["Same as source", "Custom…"])
        self._out_combo.setStyleSheet(self._combo_style())
        self._out_combo.currentIndexChanged.connect(self._on_output_mode_changed)
        out_row.addWidget(self._out_combo, 1)
        layout.addLayout(out_row)

        self._out_path_row = QHBoxLayout()
        self._out_path_row.setSpacing(6)
        self._out_path_edit = QLineEdit()
        self._out_path_edit.setPlaceholderText("Select output folder…")
        self._out_path_edit.setReadOnly(True)
        self._out_path_edit.setStyleSheet(self._line_edit_style())
        self._out_path_row.addWidget(self._out_path_edit, 1)
        browse_out_btn = QPushButton("Browse")
        browse_out_btn.setFixedWidth(68)
        browse_out_btn.setStyleSheet(self._secondary_btn_style())
        browse_out_btn.clicked.connect(self._browse_output)
        self._out_path_row.addWidget(browse_out_btn)
        out_path_widget = QWidget()
        out_path_widget.setLayout(self._out_path_row)
        out_path_widget.hide()
        self._out_path_widget = out_path_widget
        layout.addWidget(out_path_widget)

        # Console profile
        prof_row = QHBoxLayout()
        prof_row.setSpacing(6)
        prof_lbl = QLabel("Console:")
        prof_lbl.setStyleSheet(
            f"color: {_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        prof_lbl.setFixedWidth(52)
        prof_row.addWidget(prof_lbl)

        self._profile_combo = QComboBox()
        self._profile_combo.addItems(list(_CONSOLE_PROFILES.keys()))
        self._profile_combo.setStyleSheet(self._combo_style())
        prof_row.addWidget(self._profile_combo, 1)
        layout.addLayout(prof_row)

        # Advanced disclosure
        self._adv_btn = QPushButton("Advanced ▸")
        self._adv_btn.setCheckable(True)
        self._adv_btn.setFixedHeight(26)
        self._adv_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._adv_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUTED};"
            f" border: none; text-align: left; font-size: 12px; padding-left: 0; }}"
            f" QPushButton:checked {{ color: {_FG}; }}"
        )
        self._adv_btn.toggled.connect(self._toggle_advanced)
        layout.addWidget(self._adv_btn)

        self._adv_widget = QWidget()
        adv_layout = QVBoxLayout(self._adv_widget)
        adv_layout.setContentsMargins(0, 0, 0, 0)
        adv_layout.setSpacing(6)
        adv_lbl = QLabel("Extra CHDMAN flags:")
        adv_lbl.setStyleSheet(
            f"color: {_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        adv_layout.addWidget(adv_lbl)
        self._extra_flags_edit = QLineEdit()
        self._extra_flags_edit.setPlaceholderText("e.g. --unitsize 2048")
        self._extra_flags_edit.setStyleSheet(self._line_edit_style())
        adv_layout.addWidget(self._extra_flags_edit)
        self._adv_widget.hide()
        layout.addWidget(self._adv_widget)

        layout.addStretch()

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._compress_btn = QPushButton("⚡ Compress")
        self._compress_btn.setFixedHeight(40)
        self._compress_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._compress_btn.setStyleSheet(
            f"QPushButton {{ background: {_PURPLE}; color: #282a36;"
            f" border: none; border-radius: 6px; font-size: 14px; font-weight: 700; }}"
            f" QPushButton:hover {{ background: #caa0ff; }}"
            f" QPushButton:disabled {{ background: {_BORDER}; color: {_MUTED}; }}"
        )
        self._compress_btn.clicked.connect(self._start_compress)
        btn_row.addWidget(self._compress_btn, 3)

        self._extract_btn = QPushButton("↓ Extract")
        self._extract_btn.setFixedHeight(40)
        self._extract_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._extract_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_PURPLE};"
            f" border: 1.5px solid {_PURPLE}; border-radius: 6px;"
            f" font-size: 14px; font-weight: 600; }}"
            f" QPushButton:hover {{ background: {_PURPLE}22; }}"
            f" QPushButton:disabled {{ color: {_MUTED}; border-color: {_BORDER}; }}"
        )
        self._extract_btn.clicked.connect(self._start_extract)
        btn_row.addWidget(self._extract_btn, 2)

        self._cancel_btn = QPushButton("✕ Cancel")
        self._cancel_btn.setFixedHeight(40)
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_RED};"
            f" border: 1.5px solid {_RED}; border-radius: 6px;"
            f" font-size: 14px; font-weight: 600; }}"
            f" QPushButton:hover {{ background: {_RED}22; }}"
        )
        self._cancel_btn.hide()
        self._cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self._cancel_btn, 2)

        layout.addLayout(btn_row)

        return panel

    # ------------------------------------------------------------------
    # Right panel
    # ------------------------------------------------------------------

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background: {_SURFACE}; border-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        log_lbl = _section_lbl("Output Log")
        header_row.addWidget(log_lbl)
        header_row.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(22)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUTED};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" font-size: 11px; padding: 0 8px; }}"
            f" QPushButton:hover {{ color: {_FG}; }}"
        )
        clear_btn.clicked.connect(self._clear_log)
        header_row.addWidget(clear_btn)
        layout.addLayout(header_row)

        # Log stream
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        self._log.setStyleSheet(
            f"QPlainTextEdit {{ background: {_LOG_BG}; color: {_FG};"
            f" font-family: 'Consolas', 'Courier New', monospace; font-size: 12px;"
            f" border: none; border-radius: 6px; padding: 8px; }}"
            f" QScrollBar:vertical {{ background: {_BG}; width: 8px; }}"
            f" QScrollBar::handle:vertical {{ background: {_BORDER}; border-radius: 4px; }}"
        )
        layout.addWidget(self._log)

        # Status bar
        status_frame = QFrame()
        status_frame.setFixedHeight(32)
        status_frame.setStyleSheet(
            f"QFrame {{ background: {_SURFACE_R}; border-radius: 6px;"
            f" border: 1px solid {_BORDER}; }}"
        )
        status_row = QHBoxLayout(status_frame)
        status_row.setContentsMargins(10, 0, 10, 0)
        status_row.setSpacing(16)

        self._console_tag = QLabel("—")
        self._console_tag.setStyleSheet(
            f"color: {_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        status_row.addWidget(self._console_tag)
        status_row.addStretch()

        self._done_lbl = QLabel("Done: 0")
        self._done_lbl.setStyleSheet(
            f"color: {_GREEN}; font-size: 11px; background: transparent; border: none;"
        )
        status_row.addWidget(self._done_lbl)

        self._err_lbl = QLabel("Errors: 0")
        self._err_lbl.setStyleSheet(
            f"color: {_RED}; font-size: 11px; background: transparent; border: none;"
        )
        status_row.addWidget(self._err_lbl)

        layout.addWidget(status_frame)

        return panel

    # ------------------------------------------------------------------
    # Style helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _combo_style() -> str:
        return (
            f"QComboBox {{ background: {_SURFACE_R}; color: {_FG}; border: 1px solid {_BORDER};"
            f" border-radius: 4px; padding: 4px 8px; }}"
            f" QComboBox::drop-down {{ border: none; }}"
            f" QComboBox QAbstractItemView {{ background: {_SURFACE_R}; color: {_FG};"
            f" selection-background-color: {_PURPLE}44; border: 1px solid {_BORDER}; }}"
        )

    @staticmethod
    def _line_edit_style() -> str:
        return (
            f"QLineEdit {{ background: {_SURFACE_R}; color: {_FG}; border: 1px solid {_BORDER};"
            f" border-radius: 4px; padding: 4px 8px; }}"
        )

    @staticmethod
    def _secondary_btn_style() -> str:
        return (
            f"QPushButton {{ background: transparent; color: {_PURPLE};"
            f" border: 1px solid {_PURPLE}; border-radius: 4px; padding: 4px 8px; }}"
            f" QPushButton:hover {{ background: {_PURPLE}22; }}"
        )

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def _add_files(self, paths: list[str]) -> None:
        added = 0
        for p in paths:
            if p not in self._files:
                self._files.append(p)
                self._file_table.add_file(p)
                added += 1
        if added:
            self._show_file_list()

    def _show_file_list(self) -> None:
        self._drop_zone.hide()
        self._file_table.show()
        self._add_more_btn.show()

    def _show_drop_zone(self) -> None:
        self._file_table.hide()
        self._add_more_btn.hide()
        self._drop_zone.show()

    def _remove_file(self, row: int) -> None:
        if 0 <= row < len(self._files):
            self._files.pop(row)
        self._file_table.removeRow(row)
        if self._file_table.rowCount() == 0:
            self._show_drop_zone()

    def _browse_more(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add files",
            "",
            "Disc images (*.cue *.bin *.iso *.img *.cdr *.gdi *.chd);;All files (*)",
        )
        if paths:
            self._add_files(paths)

    # ------------------------------------------------------------------
    # Settings UI helpers
    # ------------------------------------------------------------------

    def _on_output_mode_changed(self, idx: int) -> None:
        self._out_path_widget.setVisible(idx == 1)

    def _browse_output(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select output folder")
        if d:
            self._out_path_edit.setText(d)

    def _toggle_advanced(self, checked: bool) -> None:
        self._adv_btn.setText("Advanced ▾" if checked else "Advanced ▸")
        self._adv_widget.setVisible(checked)

    # ------------------------------------------------------------------
    # Compression / extraction
    # ------------------------------------------------------------------

    def _resolve_output_dir(self, input_path: str) -> str | None:
        """Return the output directory, or None to signal same-as-source."""
        if self._out_combo.currentIndex() == 0:
            return None  # same as source
        custom = self._out_path_edit.text().strip()
        return custom if custom else None

    def _get_profile(self) -> tuple[str, int, str]:
        name = self._profile_combo.currentText()
        return _CONSOLE_PROFILES.get(name, ("", 0, ""))

    def _start_compress(self) -> None:
        if not self._files:
            self._log_line("⚠ No files selected.", color=_RED)
            return
        if self._running:
            return

        try:
            from core.chdman import CHDManager, CHDTask, CHDTaskType
        except Exception as exc:
            self._log_line(f"⚠ Could not load CHDManager: {exc}", color=_RED)
            return

        algorithms, hunk_size, _media = self._get_profile()
        mgr = CHDManager()
        mgr.signals.finished.connect(self._on_manager_finished)

        self._running = True
        self._completed = 0
        self._errors = 0
        self._update_status()
        self._set_running_ui(True)
        self._log_line("▶ Starting compression…")

        for i, path in enumerate(self._files):
            out_dir = self._resolve_output_dir(path)
            if out_dir is None:
                out_dir = str(Path(path).parent)
            out_file = str(Path(out_dir) / (Path(path).stem + ".chd"))

            task = CHDTask(
                task_type=CHDTaskType.COMPRESS,
                input_file=path,
                output_file=out_file,
                algorithms=algorithms or None,
                hunk_size=hunk_size or None,
            )
            mgr.add_task(task)
            self._file_table.set_status(i, "Compressing")

        workers = mgr.start_processing()
        profile_name = self._profile_combo.currentText()
        self._console_tag.setText(profile_name)

        for signals, _worker in workers:
            signals.progress_updated.connect(self._on_progress)
            signals.finished.connect(self._on_worker_finished)
            signals.error.connect(self._on_worker_error)

        self._log_line(f"  {len(self._files)} file(s) queued.")

    def _start_extract(self) -> None:
        if not self._files:
            self._log_line("⚠ No CHD files selected.", color=_RED)
            return
        if self._running:
            return

        # Only .chd files can be extracted
        chd_files = [p for p in self._files if p.lower().endswith(".chd")]
        if not chd_files:
            self._log_line("⚠ Please add .chd files to extract.", color=_RED)
            return

        try:
            from core.chdman import CHDManager, CHDTask, CHDTaskType
        except Exception as exc:
            self._log_line(f"⚠ Could not load CHDManager: {exc}", color=_RED)
            return

        mgr = CHDManager()
        mgr.signals.finished.connect(self._on_manager_finished)

        self._running = True
        self._completed = 0
        self._errors = 0
        self._update_status()
        self._set_running_ui(True)
        self._log_line("▶ Starting extraction…")

        for _i, path in enumerate(chd_files):
            out_dir = self._resolve_output_dir(path)
            if out_dir is None:
                out_dir = str(Path(path).parent)
            out_file = str(Path(out_dir) / (Path(path).stem + ".cue"))

            task = CHDTask(
                task_type=CHDTaskType.EXTRACT_CD,
                input_file=path,
                output_file=out_file,
            )
            mgr.add_task(task)
            # Mark the row for this chd
            for r in range(self._file_table.rowCount()):
                item = self._file_table.item(r, _COL_NAME)
                if item and item.data(Qt.ItemDataRole.UserRole) == path:
                    self._file_table.set_status(r, "Extracting")
                    break

        workers = mgr.start_processing()
        for signals, _worker in workers:
            signals.progress_updated.connect(self._on_progress)
            signals.finished.connect(self._on_worker_finished)
            signals.error.connect(self._on_worker_error)

        self._log_line(f"  {len(chd_files)} CHD file(s) queued for extraction.")

    def _cancel(self) -> None:
        """Cancel is handled at the CHDManager level; here we just reset UI."""
        self._log_line("✕ Operation cancelled by user.", color=_RED)
        self._running = False
        self._set_running_ui(False)
        # Reset all "Compressing"/"Extracting" rows to Queued
        for r in range(self._file_table.rowCount()):
            item = self._file_table.item(r, _COL_STATUS)
            if item and item.text() in ("Compressing", "Extracting"):
                self._file_table.set_status(r, "Queued")

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_progress(self, pct: float, msg: str, extra: str = "") -> None:
        line = f"  [{pct:5.1f}%] {msg}"
        if extra:
            line += f" — {extra}"
        self._log_line(line)

    def _on_worker_finished(self, success: bool, msg: str) -> None:
        if success:
            self._completed += 1
            color = _GREEN
            prefix = "✓"
        else:
            self._errors += 1
            color = _RED
            prefix = "✗"
        self._log_line(f"{prefix} {msg}", color=color)
        self._update_status()

        # Mark the first still-active row as Done/Error
        status_to_find = ("Compressing", "Extracting")
        new_status = "Done" if success else "Error"
        for r in range(self._file_table.rowCount()):
            item = self._file_table.item(r, _COL_STATUS)
            if item and item.text() in status_to_find:
                self._file_table.set_status(r, new_status)
                break

    def _on_worker_error(self, msg: str) -> None:
        self._errors += 1
        self._log_line(f"✗ ERROR: {msg}", color=_RED)
        self._update_status()

    def _on_manager_finished(self, success: bool, msg: str) -> None:
        self._running = False
        self._set_running_ui(False)
        self._log_line(
            f"{'✓ Finished.' if success else '✗ Finished with errors.'} {msg}",
            color=_GREEN if success else _RED,
        )

    # ------------------------------------------------------------------
    # UI state helpers
    # ------------------------------------------------------------------

    def _set_running_ui(self, running: bool) -> None:
        self._compress_btn.setVisible(not running)
        self._extract_btn.setVisible(not running)
        self._cancel_btn.setVisible(running)
        self._compress_btn.setEnabled(not running)
        self._extract_btn.setEnabled(not running)

    def _update_status(self) -> None:
        self._done_lbl.setText(f"Done: {self._completed}")
        self._err_lbl.setText(f"Errors: {self._errors}")

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _log_line(self, text: str, color: str | None = None) -> None:
        if color:
            self._log.appendHtml(f'<span style="color:{color};">{text}</span>')
        else:
            self._log.appendPlainText(text)
        # Auto-scroll
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear_log(self) -> None:
        self._log.clear()
        self._completed = 0
        self._errors = 0
        self._update_status()
        self._console_tag.setText("—")
