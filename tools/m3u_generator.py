"""M3U Generator tool for RetroClamp.

This plugin provides functionality for generating M3U playlist files
for multi-disc retro games, enabling seamless disc-swapping in emulators.
"""

from __future__ import annotations

import os
import re

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from modules.ui_functions import load_svg_icon

# Plugin metadata
PLUGIN_NAME = "M3U Generator"
PLUGIN_ICON = "📋"
PLUGIN_DESCRIPTION = "Generate M3U playlist files for multi-disc retro games"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "RetroClamp Team"

# Supported disc image extensions
DISC_EXTENSIONS = (".chd", ".iso", ".bin", ".img", ".cue")

# Regex pattern to detect disc numbering in filenames
_DISC_RE = re.compile(
    r"[\s_\-\(](disc|disk|cd|side)[\s_\-]?(\d+)",
    re.IGNORECASE,
)


def _disc_sort_key(path: str) -> tuple[str, int]:
    """Return a (base_name, disc_number) tuple for natural sort ordering.

    Disc number defaults to 0 when no numbering is found.
    """
    name = os.path.splitext(os.path.basename(path))[0]
    match = _DISC_RE.search(name)
    disc_num = int(match.group(2)) if match else 0
    # Strip the disc indicator to get a stable base for grouping
    base = _DISC_RE.sub("", name).strip()
    return (base.lower(), disc_num)


class M3uGenerator(QWidget):
    """M3U Generator widget.

    This widget provides a UI for generating M3U playlist files for
    multi-disc retro games.  Users select a directory, review the
    detected disc files, then write the playlist in one click.
    """

    def __init__(self, parent=None):
        """Initialise the M3uGenerator widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._disc_files: list[str] = []
        self.setup_ui()
        self.connect_signals()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def setup_ui(self):
        """Build the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title
        title_label = QLabel("M3U Playlist Generator")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Generate M3U playlist files for multi-disc retro games. "
            "Select the folder that contains your disc image files "
            "(.chd, .iso, .bin, .img, .cue) and the playlist will list "
            "them in disc order so your emulator can handle disc changes "
            "automatically."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Source directory
        source_group = QGroupBox("Game Directory")
        source_layout = QHBoxLayout(source_group)

        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Select folder containing disc images…")
        source_layout.addWidget(self.source_edit)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        source_layout.addWidget(self.browse_btn)

        layout.addWidget(source_group)

        # Detected disc files
        files_group = QGroupBox("Detected Disc Files")
        files_layout = QVBoxLayout(files_group)

        self.files_list = QListWidget()
        self.files_list.setMinimumHeight(120)
        self.files_list.setAlternatingRowColors(True)
        files_layout.addWidget(self.files_list)

        files_btn_row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Directory")
        self.scan_btn.setIcon(load_svg_icon("refresh-cw", 16, "#f8f8f2"))
        self.scan_btn.setEnabled(False)
        files_btn_row.addWidget(self.scan_btn)
        files_btn_row.addStretch()
        files_layout.addLayout(files_btn_row)

        layout.addWidget(files_group)

        # Output configuration
        output_group = QGroupBox("Output Configuration")
        output_layout = QFormLayout(output_group)

        # Playlist filename
        self.playlist_name_edit = QLineEdit()
        self.playlist_name_edit.setPlaceholderText("e.g., Final Fantasy VII")
        output_layout.addRow("Playlist Name:", self.playlist_name_edit)

        # Output directory row
        output_path_row = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Same as game directory")
        self.output_edit.setEnabled(False)
        output_path_row.addWidget(self.output_edit)

        self.output_browse_btn = QPushButton("Browse")
        self.output_browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        self.output_browse_btn.setEnabled(False)
        output_path_row.addWidget(self.output_browse_btn)

        output_layout.addRow("Output Directory:", output_path_row)

        self.use_source_dir_check = QCheckBox("Use game directory as output location")
        self.use_source_dir_check.setChecked(True)
        output_layout.addRow("", self.use_source_dir_check)

        self.relative_paths_check = QCheckBox(
            "Use relative paths in playlist (recommended)"
        )
        self.relative_paths_check.setChecked(True)
        output_layout.addRow("", self.relative_paths_check)

        layout.addWidget(output_group)

        # Action buttons
        buttons_row = QHBoxLayout()
        buttons_row.addStretch()

        self.generate_btn = QPushButton("Generate M3U Playlist")
        self.generate_btn.setIcon(load_svg_icon("file-check", 16, "#f8f8f2"))
        self.generate_btn.setMinimumWidth(200)
        self.generate_btn.setEnabled(False)
        buttons_row.addWidget(self.generate_btn)

        layout.addLayout(buttons_row)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def connect_signals(self):
        """Connect widget signals to their slots."""
        self.browse_btn.clicked.connect(self.browse_source)
        self.scan_btn.clicked.connect(self.scan_directory)
        self.output_browse_btn.clicked.connect(self.browse_output)
        self.use_source_dir_check.toggled.connect(self.toggle_output_path)
        self.generate_btn.clicked.connect(self.generate_m3u)
        self.source_edit.textChanged.connect(self.on_source_changed)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot()
    def browse_source(self):
        """Open a directory picker for the game folder."""
        path = QFileDialog.getExistingDirectory(self, "Select Game Directory", "")
        if path:
            self.source_edit.setText(path)

    @Slot(str)
    def on_source_changed(self, text: str):
        """Enable/disable dependent controls when the source path changes."""
        has_path = bool(text.strip())
        self.scan_btn.setEnabled(has_path)
        if has_path:
            # Auto-scan whenever the path changes
            self.scan_directory()
        else:
            self._disc_files = []
            self.files_list.clear()
            self.generate_btn.setEnabled(False)

    @Slot()
    def scan_directory(self):
        """Scan the selected directory for disc image files."""
        source = self.source_edit.text().strip()
        if not source or not os.path.isdir(source):
            QMessageBox.warning(
                self, "Invalid Directory", "Please select a valid game directory."
            )
            return

        found: list[str] = []
        try:
            for entry in os.scandir(source):
                if entry.is_file():
                    _, ext = os.path.splitext(entry.name)
                    if ext.lower() in DISC_EXTENSIONS:
                        found.append(entry.path)
        except OSError as exc:
            QMessageBox.critical(
                self, "Scan Error", f"Could not read directory:\n{exc}"
            )
            return

        # Sort by disc number for natural ordering
        found.sort(key=_disc_sort_key)
        self._disc_files = found

        # Populate list widget
        self.files_list.clear()
        for path in found:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)
            self.files_list.addItem(item)

        # Auto-populate playlist name from the first file if blank
        if found and not self.playlist_name_edit.text():
            first_name = os.path.splitext(os.path.basename(found[0]))[0]
            # Strip disc numbering to get the game title
            clean = _DISC_RE.sub("", first_name).strip(" -_()")
            self.playlist_name_edit.setText(clean)

        self.generate_btn.setEnabled(bool(found))

        if not found:
            QMessageBox.information(
                self,
                "No Disc Files Found",
                "No supported disc image files (.chd, .iso, .bin, .img, .cue) "
                "were found in the selected directory.",
            )

    @Slot()
    def browse_output(self):
        """Open a directory picker for the output folder."""
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory", "")
        if path:
            self.output_edit.setText(path)
            self.use_source_dir_check.setChecked(False)

    @Slot(bool)
    def toggle_output_path(self, checked: bool):
        """Enable or disable the custom output directory controls."""
        self.output_edit.setEnabled(not checked)
        self.output_browse_btn.setEnabled(not checked)
        if checked:
            self.output_edit.clear()

    @Slot()
    def generate_m3u(self):
        """Write the M3U playlist file to disk."""
        if not self._disc_files:
            QMessageBox.warning(self, "No Files", "Please scan a directory first.")
            return

        playlist_name = self.playlist_name_edit.text().strip()
        if not playlist_name:
            QMessageBox.warning(self, "Missing Name", "Please enter a playlist name.")
            return

        # Determine output directory
        if self.use_source_dir_check.isChecked():
            output_dir = os.path.dirname(self._disc_files[0])
        else:
            output_dir = self.output_edit.text().strip()
            if not output_dir or not os.path.isdir(output_dir):
                QMessageBox.warning(
                    self,
                    "Invalid Output",
                    "Please select a valid output directory.",
                )
                return

        # Build playlist content
        use_relative = self.relative_paths_check.isChecked()
        lines: list[str] = []
        for path in self._disc_files:
            if use_relative:
                try:
                    entry = os.path.relpath(path, output_dir)
                except ValueError:
                    # relpath fails across Windows drives — fall back
                    entry = path
            else:
                entry = path
            lines.append(entry)

        content = "\n".join(lines) + "\n"

        # Sanitise the playlist filename
        safe_name = re.sub(r'[<>:"/\\|?*]', "", playlist_name)
        m3u_path = os.path.join(output_dir, f"{safe_name}.m3u")

        try:
            with open(m3u_path, "w", encoding="utf-8") as fh:
                fh.write(content)

            QMessageBox.information(
                self,
                "Success",
                f"M3U playlist created successfully:\n{m3u_path}\n\n"
                f"{len(self._disc_files)} disc(s) listed.",
            )
        except OSError as exc:
            QMessageBox.critical(
                self, "Write Error", f"Failed to write playlist file:\n{exc}"
            )


def register_panel(tools_view: QWidget) -> QWidget:
    """Register this plugin and return its panel widget.

    Args:
        tools_view: The ToolsView instance that will host this panel.

    Returns:
        A QWidget subclass representing this plugin's full UI panel.
    """
    return M3uGenerator()
