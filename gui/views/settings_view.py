"""Settings view — mini two-column layout with 5 setting categories.

Layout:
    QHBoxLayout
    ├── Category list (QListWidget-style, ~180px)
    └── Content stack (QStackedWidget)

Settings auto-save on change via AppSettings.set(). A "Saved" flash
(#50fa7b, fades after 1.5s via QTimer) appears bottom-right after each change.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from modules.app_settings import AppSettings

# ---------------------------------------------------------------------------
# Dracula palette constants
# ---------------------------------------------------------------------------
_BG = "#282a36"
_SURFACE = "#313444"
_SURFACE_RAISED = "#353749"
_BORDER = "#44475a"
_MUTED = "#6272a4"
_FG = "#f8f8f2"
_PURPLE = "#bd93f9"
_CYAN = "#8be9fd"
_GREEN = "#50fa7b"
_RED = "#ff5555"

_CATEGORY_ITEMS: list[tuple[str, str]] = [
    ("general", "⚙  General"),
    ("appearance", "🎨  Appearance"),
    ("chdman", "💿  CHDMAN"),
    ("paths", "📁  Paths"),
    ("advanced", "🔧  Advanced"),
]


# ---------------------------------------------------------------------------
# Section heading helper
# ---------------------------------------------------------------------------


def _section_label(text: str, parent: QWidget | None = None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setStyleSheet(
        f"color: {_MUTED}; font-size: 11px; font-weight: 700;"
        " letter-spacing: 1px; background: transparent; border: none;"
    )
    return lbl


def _row_label(text: str, parent: QWidget | None = None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setFixedWidth(160)
    lbl.setStyleSheet(
        f"color: {_FG}; font-size: 13px; background: transparent; border: none;"
    )
    return lbl


def _hint_label(text: str, parent: QWidget | None = None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setStyleSheet(
        f"color: {_MUTED}; font-size: 11px; background: transparent; border: none;"
    )
    lbl.setWordWrap(True)
    return lbl


def _combo_style() -> str:
    return (
        f"QComboBox {{"
        f"  background: {_SURFACE_RAISED}; color: {_FG};"
        f"  border: 1px solid {_BORDER}; border-radius: 5px;"
        f"  padding: 4px 8px; font-size: 12px; min-width: 140px;"
        f"}}"
        f"QComboBox::drop-down {{ border: none; }}"
        f"QComboBox QAbstractItemView {{"
        f"  background: {_SURFACE}; color: {_FG}; border: 1px solid {_BORDER};"
        f"  selection-background-color: {_PURPLE}; selection-color: {_BG};"
        f"}}"
    )


def _line_edit_style() -> str:
    return (
        f"QLineEdit {{"
        f"  background: {_SURFACE_RAISED}; color: {_FG};"
        f"  border: 1px solid {_BORDER}; border-radius: 5px;"
        f"  padding: 4px 8px; font-size: 12px;"
        f"}}"
        f"QLineEdit:focus {{ border-color: {_PURPLE}; }}"
    )


def _spinbox_style() -> str:
    return (
        f"QSpinBox {{"
        f"  background: {_SURFACE_RAISED}; color: {_FG};"
        f"  border: 1px solid {_BORDER}; border-radius: 5px;"
        f"  padding: 4px 6px; font-size: 12px; min-width: 60px;"
        f"}}"
        f"QSpinBox::up-button, QSpinBox::down-button {{ border: none; }}"
    )


def _button_style(color: str = _PURPLE) -> str:
    return (
        f"QPushButton {{"
        f"  background: transparent; color: {color};"
        f"  border: 1px solid {color}; border-radius: 5px;"
        f"  padding: 4px 12px; font-size: 12px;"
        f"}}"
        f"QPushButton:hover {{ background: rgba(255,255,255,0.06); }}"
    )


def _checkbox_style() -> str:
    return (
        f"QCheckBox {{"
        f"  color: {_FG}; font-size: 13px; background: transparent; spacing: 8px;"
        f"}}"
        f"QCheckBox::indicator {{"
        f"  width: 14px; height: 14px;"
        f"  border: 1px solid {_BORDER}; border-radius: 3px; background: {_SURFACE_RAISED};"
        f"}}"
        f"QCheckBox::indicator:checked {{"
        f"  background: {_PURPLE}; border-color: {_PURPLE};"
        f"}}"
    )


# ---------------------------------------------------------------------------
# Panel helpers — wraps content in a scroll area with consistent padding
# ---------------------------------------------------------------------------


def _scrollable_panel(content: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet(f"background: {_BG}; border: none;")
    scroll.setWidget(content)
    return scroll


# ---------------------------------------------------------------------------
# Individual category panels
# ---------------------------------------------------------------------------


class _GeneralPanel(QWidget):
    def __init__(
        self, settings: AppSettings, saved_cb, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._saved_cb = saved_cb
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"background: {_BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # --- Startup section ---
        root.addWidget(_section_label("STARTUP"))

        reopen_row = QHBoxLayout()
        reopen_row.setSpacing(12)
        self._reopen_cb = QCheckBox("Reopen last session on startup")
        self._reopen_cb.setStyleSheet(_checkbox_style())
        reopen_row.addWidget(self._reopen_cb)
        reopen_row.addStretch()
        root.addLayout(reopen_row)

        # --- Performance section ---
        root.addWidget(_section_label("PERFORMANCE"))

        thread_row = QHBoxLayout()
        thread_row.setSpacing(12)
        thread_row.addWidget(_row_label("Worker thread count"))
        self._thread_spin = QSpinBox()
        self._thread_spin.setRange(1, 16)
        self._thread_spin.setStyleSheet(_spinbox_style())
        thread_row.addWidget(self._thread_spin)
        thread_row.addStretch()
        root.addLayout(thread_row)
        root.addWidget(
            _hint_label("Number of parallel threads used by the CHDMAN worker pool.")
        )

        # --- Language section (placeholder) ---
        root.addWidget(_section_label("LOCALE"))

        lang_row = QHBoxLayout()
        lang_row.setSpacing(12)
        lang_row.addWidget(_row_label("Language"))
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["English (en)"])
        self._lang_combo.setStyleSheet(_combo_style())
        lang_row.addWidget(self._lang_combo)
        lang_row.addStretch()
        root.addLayout(lang_row)
        root.addWidget(_hint_label("Additional locales coming in a future release."))

        root.addStretch()

        # Connect signals
        self._reopen_cb.checkStateChanged.connect(self._on_reopen_changed)
        self._thread_spin.valueChanged.connect(self._on_thread_changed)

    def _load(self) -> None:
        self._reopen_cb.blockSignals(True)
        self._thread_spin.blockSignals(True)
        self._reopen_cb.setChecked(
            bool(self._settings.get("general", "reopen_last_session", False))
        )
        self._thread_spin.setValue(
            int(self._settings.get("general", "worker_thread_count", 2))
        )
        self._reopen_cb.blockSignals(False)
        self._thread_spin.blockSignals(False)

    def _on_reopen_changed(self, state) -> None:
        self._settings.set("general", "reopen_last_session", bool(state))
        self._settings.save_settings()
        self._saved_cb()

    def _on_thread_changed(self, value: int) -> None:
        self._settings.set("general", "worker_thread_count", value)
        self._settings.save_settings()
        self._saved_cb()


class _AppearancePanel(QWidget):
    def __init__(
        self, settings: AppSettings, saved_cb, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._saved_cb = saved_cb
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"background: {_BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # --- Theme section ---
        root.addWidget(_section_label("THEME"))

        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        self._theme_btns: dict[str, QPushButton] = {}
        for key, label in [
            ("dracula", "Dark (Dracula)"),
            ("light", "Light"),
            ("high_contrast", "High Contrast"),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("themeKey", key)
            btn.clicked.connect(lambda checked, k=key: self._on_theme_selected(k))
            self._theme_btns[key] = btn
            theme_row.addWidget(btn)
        theme_row.addStretch()
        root.addLayout(theme_row)
        self._update_theme_buttons("dracula")

        # --- Accent colour ---
        root.addWidget(_section_label("ACCENT COLOUR"))

        accent_row = QHBoxLayout()
        accent_row.setSpacing(8)
        self._accent_btns: dict[str, QPushButton] = {}
        for hex_val, label in [(_PURPLE, "Purple"), (_CYAN, "Cyan"), (_GREEN, "Green")]:
            btn = QPushButton(label)
            btn.setFixedSize(90, 32)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("accentColor", hex_val)
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background: {hex_val}; color: #282a36;"
                f"  border: 2px solid transparent; border-radius: 6px;"
                f"  font-weight: 600; font-size: 12px;"
                f"}}"
                f"QPushButton:checked {{ border-color: {_FG}; }}"
                f"QPushButton:hover {{ opacity: 0.85; }}"
            )
            btn.clicked.connect(lambda checked, h=hex_val: self._on_accent_selected(h))
            self._accent_btns[hex_val] = btn
            accent_row.addWidget(btn)
        accent_row.addStretch()
        root.addLayout(accent_row)

        # --- Font size ---
        root.addWidget(_section_label("FONT SIZE"))

        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        self._font_btns: dict[str, QPushButton] = {}
        for key, label in [
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("fontKey", key)
            btn.clicked.connect(lambda checked, k=key: self._on_font_selected(k))
            self._font_btns[key] = btn
            font_row.addWidget(btn)
        font_row.addStretch()
        root.addLayout(font_row)
        self._update_font_buttons("medium")

        root.addStretch()

    def _btn_active_style(self) -> str:
        return (
            f"QPushButton {{"
            f"  background: {_PURPLE}; color: {_BG};"
            f"  border: 1px solid {_PURPLE}; border-radius: 5px;"
            f"  padding: 4px 12px; font-size: 12px; font-weight: 600;"
            f"}}"
        )

    def _btn_inactive_style(self) -> str:
        return _button_style(_MUTED)

    def _update_theme_buttons(self, active: str) -> None:
        for key, btn in self._theme_btns.items():
            btn.setChecked(key == active)
            btn.setStyleSheet(
                self._btn_active_style()
                if key == active
                else self._btn_inactive_style()
            )

    def _update_font_buttons(self, active: str) -> None:
        for key, btn in self._font_btns.items():
            btn.setChecked(key == active)
            btn.setStyleSheet(
                self._btn_active_style()
                if key == active
                else self._btn_inactive_style()
            )

    def _update_accent_buttons(self, active: str) -> None:
        for hex_val, btn in self._accent_btns.items():
            btn.setChecked(hex_val == active)

    def _load(self) -> None:
        theme = str(self._settings.get("appearance", "theme", "dracula"))
        accent = str(self._settings.get("appearance", "accent_color", _PURPLE))
        font_sz = str(self._settings.get("appearance", "font_size", "medium"))
        self._update_theme_buttons(theme)
        self._update_accent_buttons(accent)
        self._update_font_buttons(font_sz)

    def _on_theme_selected(self, key: str) -> None:
        self._settings.set("appearance", "theme", key)
        self._settings.save_settings()
        self._update_theme_buttons(key)
        self._saved_cb()

    def _on_accent_selected(self, hex_val: str) -> None:
        self._settings.set("appearance", "accent_color", hex_val)
        self._settings.save_settings()
        self._update_accent_buttons(hex_val)
        self._saved_cb()

    def _on_font_selected(self, key: str) -> None:
        self._settings.set("appearance", "font_size", key)
        self._settings.save_settings()
        self._update_font_buttons(key)
        self._saved_cb()


class _CHDMANPanel(QWidget):
    def __init__(
        self, settings: AppSettings, saved_cb, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._saved_cb = saved_cb
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"background: {_BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # --- Executable ---
        root.addWidget(_section_label("EXECUTABLE"))

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("chdman  (or full path)")
        self._path_edit.setStyleSheet(_line_edit_style())
        path_row.addWidget(self._path_edit)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedHeight(30)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet(_button_style())
        browse_btn.clicked.connect(self._browse_chdman)
        path_row.addWidget(browse_btn)

        self._verify_btn = QPushButton("Verify")
        self._verify_btn.setFixedHeight(30)
        self._verify_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._verify_btn.setStyleSheet(_button_style(_CYAN))
        self._verify_btn.clicked.connect(self._verify_chdman)
        path_row.addWidget(self._verify_btn)

        root.addLayout(path_row)
        self._verify_result_lbl = QLabel("")
        self._verify_result_lbl.setStyleSheet(
            f"color: {_MUTED}; font-size: 11px; background: transparent;"
        )
        root.addWidget(self._verify_result_lbl)
        root.addWidget(
            _hint_label('Leave as "chdman" to use the version on your PATH.')
        )

        # --- Compression ---
        root.addWidget(_section_label("COMPRESSION"))

        level_row = QHBoxLayout()
        level_row.setSpacing(12)
        level_row.addWidget(_row_label("Compression codec"))
        self._level_combo = QComboBox()
        self._level_combo.addItem("Default (CHDMAN built-in)", "")
        for codec in ["zstd", "zlib", "lzma", "flac", "none"]:
            self._level_combo.addItem(codec, codec)
        self._level_combo.setStyleSheet(_combo_style())
        level_row.addWidget(self._level_combo)
        level_row.addStretch()
        root.addLayout(level_row)
        root.addWidget(
            _hint_label(
                'Overrides CHDMAN\'s default codec. "Default" lets CHDMAN choose.'
            )
        )

        verify_row = QHBoxLayout()
        verify_row.setSpacing(12)
        self._verify_cb = QCheckBox("Verify checksum after creation")
        self._verify_cb.setStyleSheet(_checkbox_style())
        verify_row.addWidget(self._verify_cb)
        verify_row.addStretch()
        root.addLayout(verify_row)
        root.addWidget(
            _hint_label(
                "(Inert in this release — will be wired to CHDMAN --verify in a future update.)"
            )
        )

        root.addStretch()

        # Signals
        self._path_edit.editingFinished.connect(self._on_path_changed)
        self._level_combo.currentIndexChanged.connect(self._on_level_changed)
        self._verify_cb.checkStateChanged.connect(self._on_verify_changed)

    def _load(self) -> None:
        self._path_edit.blockSignals(True)
        self._level_combo.blockSignals(True)
        self._verify_cb.blockSignals(True)

        path = str(self._settings.get("paths", "chdman_path", "chdman"))
        self._path_edit.setText(path)

        codec = str(self._settings.get("chdman", "compression_level", ""))
        idx = self._level_combo.findData(codec)
        if idx >= 0:
            self._level_combo.setCurrentIndex(idx)

        verify = bool(self._settings.get("chdman", "verify_checksum", True))
        self._verify_cb.setChecked(verify)

        self._path_edit.blockSignals(False)
        self._level_combo.blockSignals(False)
        self._verify_cb.blockSignals(False)

    def _browse_chdman(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select CHDMAN executable")
        if path:
            self._path_edit.setText(path)
            self._settings.set("paths", "chdman_path", path)
            self._settings.save_settings()
            self._saved_cb()

    def _verify_chdman(self) -> None:
        import subprocess  # noqa: PLC0415

        path = self._path_edit.text().strip() or "chdman"
        try:
            result = subprocess.run(
                [path],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # CHDMAN exits 1 with usage info if called with no args — that's fine
            combined = (result.stdout + result.stderr).lower()
            if "chdman" in combined or "usage" in combined:
                self._verify_result_lbl.setText("✓ CHDMAN found")
                self._verify_result_lbl.setStyleSheet(
                    f"color: {_GREEN}; font-size: 11px; background: transparent;"
                )
            else:
                self._verify_result_lbl.setText(
                    "✗ Could not verify — unexpected output"
                )
                self._verify_result_lbl.setStyleSheet(
                    f"color: {_RED}; font-size: 11px; background: transparent;"
                )
        except FileNotFoundError:
            self._verify_result_lbl.setText("✗ CHDMAN not found at this path")
            self._verify_result_lbl.setStyleSheet(
                f"color: {_RED}; font-size: 11px; background: transparent;"
            )
        except Exception as exc:  # noqa: BLE001
            self._verify_result_lbl.setText(f"✗ Error: {exc}")
            self._verify_result_lbl.setStyleSheet(
                f"color: {_RED}; font-size: 11px; background: transparent;"
            )

    def _on_path_changed(self) -> None:
        path = self._path_edit.text().strip()
        self._settings.set("paths", "chdman_path", path or "chdman")
        self._settings.save_settings()
        self._saved_cb()

    def _on_level_changed(self, _index: int) -> None:
        codec = self._level_combo.currentData()
        self._settings.set("chdman", "compression_level", codec or "")
        self._settings.save_settings()
        self._saved_cb()

    def _on_verify_changed(self, state) -> None:
        self._settings.set("chdman", "verify_checksum", bool(state))
        self._settings.save_settings()
        self._saved_cb()


class _PathsPanel(QWidget):
    def __init__(
        self, settings: AppSettings, saved_cb, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._saved_cb = saved_cb
        self._setup_ui()
        self._load()

    def _folder_row(self, label: str) -> tuple[QLineEdit, QHBoxLayout]:
        row = QHBoxLayout()
        row.setSpacing(8)
        edit = QLineEdit()
        edit.setPlaceholderText("(not set)")
        edit.setStyleSheet(_line_edit_style())
        row.addWidget(edit)
        btn = QPushButton("Browse")
        btn.setFixedHeight(30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(_button_style())
        btn.clicked.connect(lambda: self._browse_folder(edit))
        row.addWidget(btn)
        return edit, row

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"background: {_BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        root.addWidget(_section_label("DEFAULT DIRECTORIES"))

        root.addWidget(_row_label("Default source folder"))
        self._src_edit, src_row = self._folder_row("Default source folder")
        root.addLayout(src_row)

        root.addWidget(_row_label("Default output folder"))
        self._out_edit, out_row = self._folder_row("Default output folder")
        root.addLayout(out_row)

        root.addWidget(_row_label("Temp directory"))
        self._tmp_edit, tmp_row = self._folder_row(
            "Temp directory (empty = system temp)"
        )
        root.addLayout(tmp_row)
        root.addWidget(
            _hint_label("Leave temp directory empty to use the OS temporary folder.")
        )

        root.addStretch()

        self._src_edit.editingFinished.connect(self._on_src_changed)
        self._out_edit.editingFinished.connect(self._on_out_changed)
        self._tmp_edit.editingFinished.connect(self._on_tmp_changed)

    def _load(self) -> None:
        for edit, _signal in [
            (self._src_edit, None),
            (self._out_edit, None),
            (self._tmp_edit, None),
        ]:
            edit.blockSignals(True)

        self._src_edit.setText(
            str(self._settings.get("paths", "last_input_directory", ""))
        )
        self._out_edit.setText(
            str(self._settings.get("paths", "last_output_directory", ""))
        )
        self._tmp_edit.setText(
            str(self._settings.get("compression", "temp_directory", ""))
        )

        for edit in (self._src_edit, self._out_edit, self._tmp_edit):
            edit.blockSignals(False)

    def _browse_folder(self, edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Folder", edit.text() or ""
        )
        if path:
            edit.setText(path)
            edit.editingFinished.emit()

    def _on_src_changed(self) -> None:
        self._settings.set("paths", "last_input_directory", self._src_edit.text())
        self._settings.save_settings()
        self._saved_cb()

    def _on_out_changed(self) -> None:
        self._settings.set("paths", "last_output_directory", self._out_edit.text())
        self._settings.save_settings()
        self._saved_cb()

    def _on_tmp_changed(self) -> None:
        self._settings.set("compression", "temp_directory", self._tmp_edit.text())
        self._settings.save_settings()
        self._saved_cb()


class _AdvancedPanel(QWidget):
    def __init__(
        self, settings: AppSettings, saved_cb, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._saved_cb = saved_cb
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"background: {_BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # --- Batch ---
        root.addWidget(_section_label("BATCH PROCESSING"))

        workers_row = QHBoxLayout()
        workers_row.setSpacing(12)
        workers_row.addWidget(_row_label("Max concurrent jobs"))
        self._workers_spin = QSpinBox()
        self._workers_spin.setRange(1, 16)
        self._workers_spin.setStyleSheet(_spinbox_style())
        workers_row.addWidget(self._workers_spin)
        workers_row.addStretch()
        root.addLayout(workers_row)
        root.addWidget(
            _hint_label("Number of CHD jobs processed in parallel within a batch run.")
        )

        # --- Logging ---
        root.addWidget(_section_label("LOGGING"))

        log_row = QHBoxLayout()
        log_row.setSpacing(12)
        log_row.addWidget(_row_label("Log verbosity"))
        self._log_combo = QComboBox()
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            self._log_combo.addItem(level, level)
        self._log_combo.setStyleSheet(_combo_style())
        log_row.addWidget(self._log_combo)
        log_row.addStretch()
        root.addLayout(log_row)

        # --- Archives ---
        root.addWidget(_section_label("ARCHIVE HANDLING"))

        keep_row = QHBoxLayout()
        keep_row.setSpacing(12)
        self._keep_archives_cb = QCheckBox("Keep extracted archives after compression")
        self._keep_archives_cb.setStyleSheet(_checkbox_style())
        keep_row.addWidget(self._keep_archives_cb)
        keep_row.addStretch()
        root.addLayout(keep_row)
        root.addWidget(
            _hint_label(
                "When enabled, source archive files (.zip, .7z, .rar) are not deleted "
                "after their contents are compressed to CHD."
            )
        )

        root.addStretch()

        # Signals
        self._workers_spin.valueChanged.connect(self._on_workers_changed)
        self._log_combo.currentIndexChanged.connect(self._on_log_changed)
        self._keep_archives_cb.checkStateChanged.connect(self._on_keep_changed)

    def _load(self) -> None:
        self._workers_spin.blockSignals(True)
        self._log_combo.blockSignals(True)
        self._keep_archives_cb.blockSignals(True)

        self._workers_spin.setValue(
            int(self._settings.get("batch", "max_concurrent_jobs", 1))
        )
        log_level = str(self._settings.get("logging", "log_level", "INFO"))
        idx = self._log_combo.findData(log_level)
        if idx >= 0:
            self._log_combo.setCurrentIndex(idx)

        # keep-extracted-archives: use inverse of delete_source_after_extraction
        delete_src = bool(
            self._settings.get("extraction", "delete_source_after_extraction", False)
        )
        self._keep_archives_cb.setChecked(not delete_src)

        self._workers_spin.blockSignals(False)
        self._log_combo.blockSignals(False)
        self._keep_archives_cb.blockSignals(False)

    def _on_workers_changed(self, value: int) -> None:
        self._settings.set("batch", "max_concurrent_jobs", value)
        self._settings.save_settings()
        self._saved_cb()

    def _on_log_changed(self, _index: int) -> None:
        level = self._log_combo.currentData()
        self._settings.set("logging", "log_level", level)
        self._settings.save_settings()
        self._saved_cb()

    def _on_keep_changed(self, state) -> None:
        # "keep" = NOT deleting source
        self._settings.set(
            "extraction", "delete_source_after_extraction", not bool(state)
        )
        self._settings.save_settings()
        self._saved_cb()


# ---------------------------------------------------------------------------
# Category list item
# ---------------------------------------------------------------------------


class _CategoryItem(QWidget):
    """Single row in the category list."""

    _ACTIVE_BG = "#313444"
    _HOVER_BG = "rgba(255,255,255,0.04)"
    _PURPLE = _PURPLE
    _FG = _FG
    _MUTED = _MUTED

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active = False
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._indicator = QFrame()
        self._indicator.setFixedWidth(3)
        self._indicator.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._indicator)

        self._lbl = QLabel(label)
        self._lbl.setContentsMargins(12, 0, 12, 0)
        self._lbl.setStyleSheet(
            f"color: {self._MUTED}; font-size: 13px; background: transparent; border: none;"
        )
        layout.addWidget(self._lbl)
        layout.addStretch()
        self._apply_state()

    # Emit a custom signal by overriding mousePressEvent
    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            parent = self.parent()
            if hasattr(parent, "_on_category_clicked"):
                parent._on_category_clicked(self)  # type: ignore[union-attr]

    def enterEvent(self, event) -> None:  # type: ignore[override]
        if not self._active:
            self.setStyleSheet(f"background: {self._HOVER_BG};")

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        if not self._active:
            self.setStyleSheet("background: transparent;")

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_state()

    def _apply_state(self) -> None:
        if self._active:
            self._indicator.setStyleSheet(f"background: {self._PURPLE}; border: none;")
            self.setStyleSheet(f"background: {self._ACTIVE_BG};")
            self._lbl.setStyleSheet(
                f"color: {self._FG}; font-size: 13px; font-weight: 600;"
                " background: transparent; border: none;"
            )
        else:
            self._indicator.setStyleSheet("background: transparent; border: none;")
            self.setStyleSheet("background: transparent;")
            self._lbl.setStyleSheet(
                f"color: {self._MUTED}; font-size: 13px;"
                " background: transparent; border: none;"
            )


# ---------------------------------------------------------------------------
# Category list container
# ---------------------------------------------------------------------------


class _CategoryList(QWidget):
    """Left-hand category list (~180px)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[_CategoryItem] = []
        self._on_select: Callable[[int], None] | None = None
        self.setFixedWidth(180)
        self.setStyleSheet(f"background: #21222c; border-right: 1px solid {_BORDER};")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(2)
        self._layout.addStretch()

    def add_item(self, label: str) -> _CategoryItem:
        item = _CategoryItem(label, parent=self)
        # Insert before the stretch
        self._layout.insertWidget(self._layout.count() - 1, item)
        self._items.append(item)
        return item

    def set_select_callback(self, cb: Callable[[int], None]) -> None:
        self._on_select = cb

    def _on_category_clicked(self, item: _CategoryItem) -> None:
        idx = self._items.index(item)
        self.select(idx)
        if self._on_select:
            self._on_select(idx)

    def select(self, idx: int) -> None:
        for i, item in enumerate(self._items):
            item.set_active(i == idx)


# ---------------------------------------------------------------------------
# SettingsView
# ---------------------------------------------------------------------------


class SettingsView(QWidget):
    """Full settings view — mini two-column layout.

    Left: category list (~180px)
    Right: content panel (QStackedWidget)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = AppSettings()
        self._saved_timer: QTimer | None = None
        self._saved_lbl: QLabel | None = None
        self._saved_opacity: QGraphicsOpacityEffect | None = None
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"background: {_BG};")

        # Outer layout: header + body
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background: {_BG}; border-bottom: 1px solid {_BORDER};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)
        title_lbl = QLabel("Settings")
        title_lbl.setStyleSheet(
            f"color: {_FG}; font-size: 18px; font-weight: 700;"
            " background: transparent; border: none;"
        )
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        outer.addWidget(header)

        # Body: category list + content stack
        body = QWidget()
        body.setStyleSheet(f"background: {_BG};")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left: category list
        self._cat_list = _CategoryList(body)
        body_layout.addWidget(self._cat_list)

        # Right: content + "Saved" flash overlay
        right_container = QWidget()
        right_container.setStyleSheet(f"background: {_BG};")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._content_stack = QStackedWidget()
        self._content_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        right_layout.addWidget(self._content_stack, stretch=1)

        # "Saved" flash label (pinned bottom-right, initially hidden)
        self._saved_lbl = QLabel("✓ Saved")
        self._saved_lbl.setStyleSheet(
            f"color: {_GREEN}; font-size: 12px; font-weight: 600;"
            f" background: {_SURFACE_RAISED}; border: 1px solid {_GREEN};"
            " border-radius: 4px; padding: 4px 10px;"
        )
        self._saved_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._saved_lbl.setFixedHeight(28)
        self._saved_lbl.hide()
        right_layout.addWidget(self._saved_lbl, alignment=Qt.AlignmentFlag.AlignRight)

        body_layout.addWidget(right_container, stretch=1)
        outer.addWidget(body, stretch=1)

        # Build panels
        self._build_panels()

        # Wire category list
        self._cat_list.set_select_callback(self._on_category_selected)
        self._cat_list.select(0)
        self._content_stack.setCurrentIndex(0)

        # "Saved" flash timer
        self._saved_timer = QTimer(self)
        self._saved_timer.setSingleShot(True)
        self._saved_timer.setInterval(1500)
        self._saved_timer.timeout.connect(self._hide_saved)

    def _build_panels(self) -> None:
        """Build all category panels and register them."""
        panels = [
            ("general", "⚙  General", _GeneralPanel),
            ("appearance", "🎨  Appearance", _AppearancePanel),
            ("chdman", "💿  CHDMAN", _CHDMANPanel),
            ("paths", "📁  Paths", _PathsPanel),
            ("advanced", "🔧  Advanced", _AdvancedPanel),
        ]
        for _key, label, PanelClass in panels:
            self._cat_list.add_item(label)
            panel = PanelClass(self._settings, self._show_saved)
            scroll = _scrollable_panel(panel)
            self._content_stack.addWidget(scroll)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_category_selected(self, idx: int) -> None:
        self._content_stack.setCurrentIndex(idx)

    def _show_saved(self) -> None:
        """Flash the "Saved" indicator for 1.5 seconds."""
        if self._saved_lbl is None or self._saved_timer is None:
            return
        self._saved_lbl.show()
        self._saved_timer.start()

    def _hide_saved(self) -> None:
        if self._saved_lbl is not None:
            self._saved_lbl.hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reload(self) -> None:
        """Re-instantiate settings object and refresh (call after external changes)."""
        self._settings = AppSettings()
