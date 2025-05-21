"""Compression tab for RetroClamp.

This module provides the UI and functionality for compressing disk images
using the CHDMAN utility.
"""

import os
import traceback
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QProgressBar,
    QTableWidget,
    QMessageBox,


    QGroupBox,
    QSizePolicy,
    QTextEdit,
    QFormLayout,

)

from PySide6.QtGui import QIcon
from core.chdman import CHDTask, CHDTaskType, CHDCompressionType
from core.archive import ArchiveManager
from core.file_scanner import FileScanner

# Persistent CHDMAN path loader


# Compression profiles
COMPRESSION_PROFILES = {
    "CD - Default": {
        "algorithms": "cdlz,cdzl,cdfl",
        "hunk_size": 19584,
        "enum": CHDCompressionType.ZLIB_HUFF,
    },
    "CD - Fast": {"algorithms": "cdlz", "hunk_size": 19584, "enum": CHDCompressionType.ZLIB},
    "DVD - Default": {"algorithms": "zlib,huff", "hunk_size": 2048, "enum": CHDCompressionType.ZLIB_HUFF},
    "DVD - Best": {"algorithms": "lzma", "hunk_size": 2048, "enum": CHDCompressionType.LZMA},
    "Hard Disk - Default": {
        "algorithms": "zlib,huff",
        "hunk_size": 4096,
        "enum": CHDCompressionType.ZLIB_HUFF,
    },
    "Hard Disk - Best": {"algorithms": "lzma", "hunk_size": 4096, "enum": CHDCompressionType.LZMA},
}

# Map profile names to CHDCompressionType
PROFILE_TO_COMPRESSION_TYPE = {k: v["enum"] for k, v in COMPRESSION_PROFILES.items()}


class CompressionTab(QWidget):
    """Compression tab widget.

    This widget provides a UI for compressing disk images using CHDMAN.
    """

    def __init__(self, parent=None):
        """Initialize the CompressionTab widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Initialize managers
        from core.chdman import get_chd_manager

        self.chd_manager = get_chd_manager()
        self.archive_manager = ArchiveManager()
        self.file_scanner = FileScanner()
        # Debug log for CHDMAN path used in compression tab
        try:
            with open("error.log", "a", encoding="utf-8") as logf:
                logf.write("[CompressionTab] Using CHDMAN singleton instance.\n")
        except Exception:
            pass

        # Track temporary directories for cleanup
        self.temp_directories = []
        # Track disk images for grouping/pruning logic
        self.disk_images = []

        # Setup UI and connect signals
        self._build_ui()
        self._connect_signals()
        print("[LOG] CompressionTab initialized. Signal connections will be logged.")

    def browse_output(self):
        """Open directory dialog to select output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", ""
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def toggle_output_dir(self, checked: bool):
        """Enable or disable the output directory field based on checkbox."""
        self.output_dir_edit.setEnabled(not checked)
        if checked:
            input_path = self.input_path_edit.text()
            if input_path:
                self.output_dir_edit.setText(os.path.dirname(input_path))

    def _build_ui(self):
        """Build the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(18, 18, 18, 18)

        # --- Input Section ---
        input_group = QGroupBox("Input")
        input_group.setObjectName("InputGroup")
        input_layout = QFormLayout()
        input_layout.setSpacing(10)
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setObjectName("InputPathEdit")
        self.browse_input_btn = QPushButton(QIcon("folder"), "Browse Input")
        self.browse_input_btn.setToolTip("Select the file or archive to compress.")
        row = QHBoxLayout()
        row.addWidget(self.input_path_edit, 1)
        row.addWidget(self.browse_input_btn)
        input_layout.addRow(QLabel("Input File or Archive:"), row)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # --- Output Section ---
        output_group = QGroupBox("Output")
        output_group.setObjectName("OutputGroup")
        output_layout = QFormLayout()
        output_layout.setSpacing(10)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setObjectName("OutputDirEdit")
        self.browse_output_btn = QPushButton(QIcon("folder"), "Browse Output Dir")
        self.browse_output_btn.setToolTip(
            "Select the directory to save the compressed file."
        )
        row = QHBoxLayout()
        row.addWidget(self.output_dir_edit, 1)
        row.addWidget(self.browse_output_btn)
        output_layout.addRow(QLabel("Output Directory:"), row)
        self.use_same_dir_check = QCheckBox("Use same directory as input")
        output_layout.addRow(self.use_same_dir_check)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # --- Options Section ---
        options_group = QGroupBox("Options")
        options_group.setObjectName("OptionsGroup")
        options_layout = QHBoxLayout()
        self.media_type_combo = QComboBox()
        self.media_type_combo.addItems(["Auto Detect", "CD", "DVD", "Hard Disk"])
        self.media_type_combo.setToolTip(
            "Media type will be auto-detected based on file."
        )
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(COMPRESSION_PROFILES.keys())
        self.profile_combo.setToolTip("Choose a compression profile.")
        options_layout.addWidget(QLabel("Media Type:"))
        options_layout.addWidget(self.media_type_combo)
        options_layout.addSpacing(24)
        options_layout.addWidget(QLabel("Compression Profile:"))
        options_layout.addWidget(self.profile_combo)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # --- File Table Section ---
        table_group = QGroupBox("Files to Process")
        table_group.setObjectName("TableGroup")
        table_layout = QVBoxLayout()
        self.files_table = QTableWidget(0, 3)
        self.files_table.setObjectName("FilesTable")
        self.files_table.setHorizontalHeaderLabels(["File", "Status", "Progress"])
        self.files_table.horizontalHeader().setStretchLastSection(True)
        self.files_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table_layout.addWidget(self.files_table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group, 1)

        # --- Log Section ---
        log_group = QGroupBox("Log Output")
        log_group.setObjectName("LogGroup")
        log_layout = QVBoxLayout()
        self.log_panel = QTextEdit()
        self.log_panel.setObjectName("LogPanel")
        self.log_panel.setReadOnly(True)
        self.log_panel.setMinimumHeight(120)
        log_layout.addWidget(self.log_panel)
        log_btn_row = QHBoxLayout()
        self.export_log_btn = QPushButton(QIcon("download"), "Export Log")
        self.export_log_btn.setToolTip("Export the log to a file.")
        self.copy_log_btn = QPushButton(QIcon("clipboard"), "Copy Log")
        self.copy_log_btn.setToolTip("Copy the log output to clipboard.")
        log_btn_row.addWidget(self.export_log_btn)
        log_btn_row.addWidget(self.copy_log_btn)
        log_layout.addLayout(log_btn_row)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # --- Progress Section ---
        progress_group = QGroupBox("Overall Progress")
        progress_group.setObjectName("ProgressGroup")
        progress_layout = QVBoxLayout()
        self.overall_progress = QProgressBar()
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(True)
        progress_layout.addWidget(self.overall_progress)
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # --- Action Buttons ---
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton(QIcon("play"), "Start Compression")
        self.start_btn.setToolTip("Begin compressing the selected file.")
        self.cancel_btn = QPushButton(QIcon("x"), "Cancel")
        self.cancel_btn.setToolTip("Cancel the current operation.")
        self.cleanup_btn = QPushButton(QIcon("broom"), "Cleanup Temp Directories")
        self.cleanup_btn.setToolTip("Remove temporary files and folders.")
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.cleanup_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _connect_signals(self):
        """Connect widget signals to slots."""
        # This method should connect all signals for compression tasks
        # Add logging for each connection; actual worker signal connections occur in start_compression
        print(
            "[LOG] _connect_signals called (static UI signals only; worker signals logged in start_compression)"
        )
        self.browse_input_btn.clicked.connect(self.browse_input)
        print("[LOG] Connected browse_input_btn.clicked to browse_input")
        self.browse_output_btn.clicked.connect(self.browse_output)
        print("[LOG] Connected browse_output_btn.clicked to browse_output")
        self.use_same_dir_check.toggled.connect(self.toggle_output_dir)
        print("[LOG] Connected use_same_dir_check.toggled to toggle_output_dir")
        self.media_type_combo.currentIndexChanged.connect(self.update_profile_list)
        print(
            "[LOG] Connected media_type_combo.currentIndexChanged to update_profile_list"
        )
        self.start_btn.clicked.connect(self.start_compression)
        print("[LOG] Connected start_btn.clicked to start_compression")
        self.cancel_btn.clicked.connect(self.cancel_compression)
        print("[LOG] Connected cancel_btn.clicked to cancel_compression")
        self.cleanup_btn.clicked.connect(self.cleanup_temp_directories)
        print("[LOG] Connected cleanup_btn.clicked to cleanup_temp_directories")
        self.export_log_btn.clicked.connect(self.export_log)
        print("[LOG] Connected export_log_btn.clicked to export_log")
        self.copy_log_btn.clicked.connect(self.copy_log)
        print("[LOG] Connected copy_log_btn.clicked to copy_log")

    def update_profile_list(self):
        """Update compression profiles based on selected media type."""
        media_type = self.media_type_combo.currentText()
        print("[LOG] update_profile_list called for media type: " + media_type)
        self.profile_combo.clear()
        if media_type == "CD":
            self.profile_combo.addItems(
                [
                    k
                    for k in COMPRESSION_PROFILES
                    if COMPRESSION_PROFILES[k]["media"] == "CD"
                ]
            )
        elif media_type == "DVD":
            self.profile_combo.addItems(
                [
                    k
                    for k in COMPRESSION_PROFILES
                    if COMPRESSION_PROFILES[k]["media"] == "DVD"
                ]
            )
        elif media_type == "Hard Disk":
            self.profile_combo.addItems(
                [
                    k
                    for k in COMPRESSION_PROFILES
                    if COMPRESSION_PROFILES[k]["media"] == "Hard Disk"
                ]
            )
        else:  # Auto Detect or unknown
            self.profile_combo.addItems(COMPRESSION_PROFILES.keys())
        print(
            f"[LOG] profile_combo updated: {[self.profile_combo.itemText(i) for i in range(self.profile_combo.count())]}"
        )

    def add_file_to_table(self, file_path):
        """Add file to the files table if not already present. Returns the row index."""
        # Normalize path
        file_path = os.path.normpath(file_path)
        # Check for duplicates
        for row in range(self.files_table.rowCount()):
            existing = self.files_table.item(row, 0)
            if existing and existing.text() == file_path:
                return row
        # Add new row
        row = self.files_table.rowCount()
        self.files_table.insertRow(row)
        from PySide6.QtWidgets import QTableWidgetItem, QProgressBar

        file_item = QTableWidgetItem(file_path)
        status_item = QTableWidgetItem("Pending")
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        self.files_table.setItem(row, 0, file_item)
        self.files_table.setItem(row, 1, status_item)
        self.files_table.setCellWidget(row, 2, progress_bar)
        return row

    def update_file_status(self, row, status):
        """Update file status in the table."""
        if row is not None and row >= 0 and row < self.files_table.rowCount():
            from PySide6.QtWidgets import QTableWidgetItem

            self.files_table.setItem(row, 1, QTableWidgetItem(status))

    def update_file_progress(self, row, progress):
        """Update the progress bar for a given row in the files table."""
        if row is not None and row >= 0 and row < self.files_table.rowCount():
            progress_bar = self.files_table.cellWidget(row, 2)
            if progress_bar is not None:
                progress_bar.setValue(progress)

    def log_message(self, message, level="info"):
        """Append a message to the log widget."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level.upper()}] {message}"
        self.log_panel.append(formatted)
        # Also write to error.log for persistent debugging
        try:
            with open("error.log", "a", encoding="utf-8") as logf:
                logf.write(formatted + "\n")
        except Exception:
            pass

    def export_log(self):
        """Export the log contents to a file."""
        from PySide6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Log",
            "retroclamp_log.txt",
            "Text Files (*.txt);;HTML Files (*.html)",
        )
        if filename:
            content = (
                self.log_panel.toHtml()
                if filename.endswith(".html")
                else self.log_panel.toPlainText()
            )
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            self.log_message("Log exported to " + filename, level="success")

    def copy_log(self):
        """Copy the log contents to the clipboard."""
        from PySide6.QtGui import QGuiApplication

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.log_panel.toPlainText())
        self.log_message("Log copied to clipboard", level="success")

    def start_compression(self):
        print("[MARKER] start_compression method ENTERED (unique marker)")
        self.log_message("[MARKER] start_compression method ENTERED (unique marker)")
        row_count = self.files_table.rowCount()
        print(f"[MARKER] files_table row count: {row_count}")
        self.log_message(f"[MARKER] files_table row count: {row_count}")
        if row_count == 0:
            print("[MARKER] WARNING: files_table is empty at start_compression!")
            self.log_message("[MARKER] WARNING: files_table is empty at start_compression!")
        import os
        from PySide6.QtWidgets import QMessageBox
        self._queued_files = set()
        # When connecting worker signals, log each connection
        # Example (actual code may differ):
        # worker.signals.finished.connect(lambda *args: self.on_task_finished(*args))
        # print("[LOG] Connected worker.finished to on_task_finished")
        # worker.signals.error.connect(lambda *args: self.on_task_error(*args))
        # print("[LOG] Connected worker.error to on_task_error")

        """Start the compression process.
        
        This method handles both single files and archives, creating appropriate
        CHDTask objects and connecting signals for UI updates.
        """
        # Clear any previous tasks
        self.chd_manager.clear_tasks()

        # Get input path
        input_path = self.input_path_edit.text().strip()
        if not input_path:
            self.log_message("Please select an input file.", level="warning")
            QMessageBox.warning(self, "Input Required", "Please select an input file.")
            return

        # Check if input file exists
        if not os.path.exists(input_path):
            self.log_message(
                "The input file does not exist: " + input_path, level="error"
            )
            QMessageBox.warning(
                self,
                "Input File Not Found",
                "The input file does not exist: " + input_path,
            )
            return

        # Get output directory
        output_dir = self.output_dir_edit.text().strip()
        if not self.check_output_directory(output_dir):
            return  # check_output_directory will show appropriate error messages

        # Reset progress bar
        self.overall_progress.setValue(0)

        # Determine base media type and compression options
        base_media_type = self.detect_media_type(input_path)
        base_compression_algos = self.get_compression_options()

        # Set task type to COMPRESS
        task_type = CHDTaskType.COMPRESS

        # Default output path (for single file)
        input_basename = os.path.basename(input_path)
        input_name_no_ext, _ = os.path.splitext(input_basename)
        default_chd_output_path = os.path.join(output_dir, input_name_no_ext + ".chd")

        # Check if file is an archive
        is_archive = self.archive_manager.is_archive(input_path)

        # If the files table contains extracted disk images (after archive extraction),
        # queue each of those files for compression (skip archive rows).
        files_to_queue = []
        try:
            print("[DEBUG] Starting files_table row scan...")
            self.log_message("[DEBUG] Starting files_table row scan...")
            for row in range(self.files_table.rowCount()):
                try:
                    file_item = self.files_table.item(row, 0)
                    status_item = self.files_table.item(row, 1)
                    fi_str = (
                        "None"
                        if file_item is None
                        else f"<{type(file_item).__name__} {repr(file_item)} >"
                    )
                    si_str = (
                        "None"
                        if status_item is None
                        else f"<{type(status_item).__name__} {repr(status_item)} >"
                    )
                    print(
                        f"[DEBUG] Row {row}: file_item={fi_str}, status_item={si_str}"
                    )
                    self.log_message(
                        f"[DEBUG] Row {row}: file_item={fi_str}, status_item={si_str}"
                    )

                    file_path = file_item.text() if file_item else None
                    status = status_item.text() if status_item else None
                    debug_msg = (
                        f"[DEBUG] Row {row}: file='{file_path}', status='{status}'"
                    )
                    print(debug_msg)
                    self.log_message(debug_msg)
                    if not file_item:
                        print(f"[DEBUG] Row {row}: SKIP - file_item is None")
                        self.log_message(f"[DEBUG] Row {row}: SKIP - file_item is None")
                        continue
                    ext = os.path.splitext(file_path)[1].lower()
                    # Skip archive files
                    if self.archive_manager.is_archive(file_path):
                        print(f"[DEBUG] Row {row}: SKIP - is archive file: {file_path}")
                        self.log_message(
                            f"[DEBUG] Row {row}: SKIP - is archive file: {file_path}"
                        )
                        continue
                    # Only queue files with status Pending or not yet processed
                    if status_item and status not in ("Pending", "Queued", ""):
                        print(
                            f"[DEBUG] Row {row}: SKIP - status not pending/queued: {status}"
                        )
                        self.log_message(
                            f"[DEBUG] Row {row}: SKIP - status not pending/queued: {status}"
                        )
                        continue
                    print(f"[DEBUG] Row {row}: QUEUE - file: {file_path}")
                    self.log_message(f"[DEBUG] Row {row}: QUEUE - file: {file_path}")
                    files_to_queue.append((file_path, row))
                except Exception as row_exc:
                    print(f"[DEBUG] Exception in row {row}: {row_exc}")
                    self.log_message(f"[DEBUG] Exception in row {row}: {row_exc}")
            print("[DEBUG] Completed files_table row scan.")
            self.log_message("[DEBUG] Completed files_table row scan.")
        except Exception as exc:
            print(f"[DEBUG] Exception in files_table row scan: {exc}")
            self.log_message(f"[DEBUG] Exception in files_table row scan: {exc}")

        if files_to_queue:
            for file_path, row in files_to_queue:
                if file_path in self._queued_files:
                    self.log_message(
                        f"[GUARD] Skipping duplicate file in queue: {file_path}"
                    )
                    continue
                media_type = self.detect_media_type(file_path)
                compression_algos = self.get_compression_options()
                input_basename = os.path.basename(file_path)
                input_name_no_ext, _ = os.path.splitext(input_basename)
                output_dir = self.output_dir_edit.text().strip()
                output_path = os.path.join(output_dir, input_name_no_ext + ".chd")
                # Per-file overwrite prompt logic
                overwrite_all = getattr(self, "_overwrite_all", None)
                skip_all = getattr(self, "_skip_all", None)
                if os.path.exists(output_path):
                    if overwrite_all:
                        overwrite = True
                    elif skip_all:
                        self.log_message(
                            f"Skipping {file_path}: Output {output_path} exists."
                        )
                        self.update_file_status(row, "Skipped - File exists")
                        continue
                    else:
                        from PySide6.QtWidgets import QMessageBox

                        msgbox = QMessageBox(self)
                        msgbox.setIcon(QMessageBox.Warning)
                        msgbox.setWindowTitle("File Exists")
                        msgbox.setText(
                            f"Output file already exists:\n{output_path}\nOverwrite?"
                        )
                        yes = msgbox.addButton("Yes", QMessageBox.YesRole)
                        no = msgbox.addButton("No", QMessageBox.NoRole)
                        yes_all = msgbox.addButton("Yes to All", QMessageBox.YesRole)
                        no_all = msgbox.addButton("No to All", QMessageBox.NoRole)
                        cancel = msgbox.addButton("Cancel", QMessageBox.RejectRole)
                        msgbox.setDefaultButton(no)
                        msgbox.exec()
                        clicked = msgbox.clickedButton()
                        if clicked == yes:
                            overwrite = True
                        elif clicked == no:
                            self.log_message(
                                f"Skipping {file_path}: Output {output_path} exists."
                            )
                            self.update_file_status(row, "Skipped - File exists")
                            continue
                        elif clicked == yes_all:
                            self._overwrite_all = True
                            overwrite = True
                        elif clicked == no_all:
                            self._skip_all = True
                            self.log_message(
                                f"Skipping {file_path}: Output {output_path} exists."
                            )
                            self.update_file_status(row, "Skipped - File exists")
                            continue
                        else:  # Cancel
                            self.log_message("Compression cancelled by user.")
                            return
                    force_overwrite = (
                        True
                        if overwrite_all or ("overwrite" in locals() and overwrite)
                        else False
                    )
                else:
                    force_overwrite = False
                task = CHDTask(
                    task_type=CHDTaskType.COMPRESS,
                    input_file=file_path,
                    output_file=output_path,
                    algorithms=compression_algos,
                    hunk_size=self.get_hunk_size(media_type),
                    force=force_overwrite,
                    media_type=media_type,
                    compression=self.get_compression_type(),
                    user_data={"row": row, "original_input": file_path},
                )
                self.chd_manager.add_task(task)
                self.update_file_status(row, "Queued")
                self._queued_files.add(file_path)

        else:
            # Fallback: single file mode (no extracted files in table)
            if not is_archive:
                if input_path in self._queued_files:
                    self.log_message("[GUARD] Skipping duplicate file: " + input_path)
                    return
                else:
                    self._queued_files.add(input_path)
                    initial_ui_row = self.add_file_to_table(input_path)
                    self.update_file_status(initial_ui_row, "Pending")
                ext = os.path.splitext(input_path)[1].lower()
                if ext == ".bin":
                    cue_candidate = os.path.splitext(input_path)[0] + ".cue"
                    if os.path.exists(cue_candidate):
                        self.log_message(
                            "Found .bin but .cue exists ("
                            + os.path.basename(cue_candidate)
                            + "); skipping .bin.",
                            level="warning",
                        )
                        return
                if ext == ".cue":

                    def cue_has_all_bins(cue_path):
                        try:
                            cue_dir = os.path.dirname(cue_path)
                            with open(cue_path, "r", encoding="utf-8") as cuef:
                                lines = cuef.readlines()
                            bin_files = [
                                line.split('"')[1]
                                for line in lines
                                if line.strip().upper().startswith("FILE")
                                and "BINARY" in line.upper()
                            ]
                            for bin_file in bin_files:
                                bin_path = os.path.join(cue_dir, bin_file)
                                if not os.path.exists(bin_path):
                                    return False, bin_file
                            return True, None
                        except Exception as e:
                            self.log_message(
                                "Error parsing .cue file " + cue_path + ": " + str(e)
                            )
                            return False, str(e)

                    ok, missing = cue_has_all_bins(input_path)
                    if not ok:
                        self.log_message(
                            "Warning: .cue file "
                            + os.path.basename(input_path)
                            + " is missing referenced bin: "
                            + missing,
                            level="warning",
                        )
                        return
                input_basename = os.path.basename(input_path)
                input_name_no_ext, _ = os.path.splitext(input_basename)
                output_path = os.path.join(
                    self.output_dir_edit.text().strip(), input_name_no_ext + ".chd"
                )
                if os.path.exists(output_path) and not self.overwrite_check.isChecked():
                    self.log_message(
                        "Skipping "
                        + input_path
                        + ": Output "
                        + output_path
                        + " exists."
                    )
                    self.update_file_status(initial_ui_row, "Skipped - File exists")
                    self.start_btn.setEnabled(True)
                    return
                task = CHDTask(
                    task_type=CHDTaskType.COMPRESS,
                    input_file=input_path,
                    output_file=output_path,
                    algorithms=self.get_compression_options(),
                    hunk_size=self.get_hunk_size(self.detect_media_type(input_path)),
                    force=self.overwrite_check.isChecked(),
                    media_type=self.detect_media_type(input_path),
                    compression=self.get_compression_type(),
                    user_data={"row": initial_ui_row, "original_input": input_path},
                )
                self.chd_manager.add_task(task)
                self.update_file_status(initial_ui_row, "Queued")
                self._queued_files.add(input_path)

        # Execute tasks and connect signals
        signals_list = []
        tasks_for_signals = []
        try:
            self.log_message("Executing all tasks in queue...")
            signals_list = self.chd_manager.execute_all_tasks()
            tasks_for_signals = (
                self.chd_manager.get_last_executed_tasks_batch()
            )  # Get the tasks
            self.log_message(
                "Task execution initiated for " + str(len(signals_list)) + " tasks."
            )
            # Log all files in the batch for deduplication verification
            seen_inputs = set()
            for t in tasks_for_signals:
                if t.input_file in seen_inputs:
                    self.log_message(
                        "[GUARD] Duplicate task detected for input: " + t.input_file,
                        level="error",
                    )
                else:
                    seen_inputs.add(t.input_file)
        except Exception as e:
            self.log_message("ERROR executing tasks: " + str(e))
            self.log_message(traceback.format_exc())
            # Update all relevant rows to "Error"
            for task_obj in self.chd_manager.get_last_executed_tasks_batch():
                if task_obj.user_data and "row" in task_obj.user_data:
                    self.update_file_status(task_obj.user_data["row"], "Error starting")
            # Also the initial row if it wasn't part of batch (e.g. archive extraction failed before queue)
            if not self.chd_manager.get_last_executed_tasks_batch():
                self.update_file_status(initial_ui_row, "Error")
            return  # Stop here

        if not signals_list:
            self.log_message("No tasks were processed or no signals returned.")
            # UI update to re-enable start button etc.
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            return

        if len(signals_list) != len(tasks_for_signals):
            self.log_message(
                "ERROR: Mismatch between signals and task metadata. UI updates may be incorrect."
            )
            # Handle this error state - perhaps re-enable UI
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            return

        self.log_message(
            "Connecting signals for " + str(len(signals_list)) + " tasks..."
        )
        any_task_started = False
        for i, signals_obj in enumerate(signals_list):
            task_for_this_signal = tasks_for_signals[i]

            if (
                not hasattr(task_for_this_signal, "user_data")
                or "row" not in task_for_this_signal.user_data
            ):
                self.log_message(
                    "Warning: Task for signal "
                    + str(i)
                    + " (input: "
                    + task_for_this_signal.input_file
                    + ") missing user_data or row. Skipping signal connections for this task."
                )
                continue

            # This is the crucial part: capture the row specific to this task for the lambdas
            row_for_this_task_lambda_capture = task_for_this_signal.user_data["row"]
            original_input_for_this_task = task_for_this_signal.user_data.get(
                "original_input", "Unknown file"
            )

            # Prevent duplicate signal connections for the same file/task
            if hasattr(self, "_connected_signals"):
                if (
                    original_input_for_this_task,
                    row_for_this_task_lambda_capture,
                ) in self._connected_signals:
                    self.log_message(
                        "[GUARD] Duplicate signal connection prevented for "
                        + original_input_for_this_task
                        + " (Row "
                        + str(row_for_this_task_lambda_capture)
                        + ")"
                    )
                    continue
            else:
                self._connected_signals = set()
            self._connected_signals.add(
                (original_input_for_this_task, row_for_this_task_lambda_capture)
            )

            self.log_message(
                "  Connecting signals for task "
                + str(i + 1)
                + "/"
                + str(len(signals_list))
                + " (File: "
                + os.path.basename(original_input_for_this_task)
                + ", Row: "
                + str(row_for_this_task_lambda_capture)
                + ")"
            )
            self.update_file_status(
                row_for_this_task_lambda_capture, "Starting"
            )  # Update status when connecting

            signals_obj.started.connect(
                # Default argument 'r' captures current value of row_for_this_task_lambda_capture
                lambda msg, r=row_for_this_task_lambda_capture, f=original_input_for_this_task: self.log_message(
                    "Task for '"
                    + os.path.basename(f)
                    + "' (Row "
                    + str(r)
                    + ") started. CMD: "
                    + msg
                )
            )
            print(
                "[LOG] Connected signals_obj.started to lambda for task " + str(i + 1)
            )

            signals_obj.progress.connect(
                lambda progress_val, msg_line, r=row_for_this_task_lambda_capture, f=original_input_for_this_task: self.progress_with_message(
                    progress_val, msg_line, r, f
                )  # Pass file for logging
            )
            print(
                "[LOG] Connected signals_obj.progress to progress_with_message for task "
                + str(i + 1)
            )

            signals_obj.finished.connect(
                lambda success, finish_msg, r=row_for_this_task_lambda_capture, f=original_input_for_this_task: self.on_task_finished(
                    success, finish_msg, r, f
                )  # Pass file for logging
            )
            print(
                "[LOG] Connected signals_obj.finished to on_task_finished for task "
                + str(i + 1)
            )

            signals_obj.error.connect(
                lambda err_msg, r=row_for_this_task_lambda_capture, f=original_input_for_this_task: self.on_task_error(
                    err_msg, r, f
                )  # Pass file for logging
            )
            print(
                "[LOG] Connected signals_obj.error to on_task_error for task "
                + str(i + 1)
            )
            any_task_started = True

        if any_task_started:
            self.start_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
        else:  # No tasks actually had signals connected (e.g. all skipped due to no user_data)
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)

    def cancel_compression(self):
        """Cancel all running compression tasks.

        This terminates all CHDMAN processes and updates the UI accordingly.
        """
        self.log_message("Cancelling all compression tasks...")

        # Disable cancel button to prevent multiple clicks
        self.cancel_btn.setEnabled(False)

        # Terminate all CHDMAN processes
        self.chd_manager.terminate_all_chdman_processes()

        # Update status for all pending tasks
        for row in range(self.files_table.rowCount()):
            status_item = self.files_table.item(row, 1)
            if status_item and status_item.text() in [
                "Pending",
                "Starting",
                "Compressing",
            ]:
                self.update_file_status(row, "Cancelled")

        # Give processes time to terminate before cleaning up
        self.log_message("Waiting for processes to terminate...")

        # Use QTimer to add a delay before cleanup
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1000, self._finish_cancellation)

    def _finish_cancellation(self):
        """Complete the cancellation process after a delay."""
        # Clean up temp directories
        self.log_message("Cleaning up temporary directories...")
        self.cleanup_temp_directories()

        # Update UI
        self.start_btn.setEnabled(True)
        self.log_message("Cancellation complete")

    def browse_input(self):
        """Open file dialog to select input file.

        If an archive is selected, it will be automatically extracted asynchronously
        and the contents will be displayed in the files table for preview.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input File",
            "",
            "All Files (*);;Disk Images (*.iso *.bin *.img);;Archives (*.zip *.7z *.rar)",
        )
        if not file_path:
            return
        self.input_path_edit.setText(file_path)
        if self.use_same_dir_check.isChecked():
            self.output_dir_edit.setText(os.path.dirname(file_path))
        self.chd_manager.clear_tasks()
        self.files_table.setRowCount(0)
        if self.archive_manager.is_archive(file_path):
            self.log_message(
                f"Detected archive: {file_path}. Beginning async extraction..."
            )
            self.start_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
            archive_row = self.add_file_to_table(file_path)
            self.update_file_status(archive_row, "Queued for extraction")
            self.update_file_progress(archive_row, 0)

            def on_started(desc):
                self.log_message(f"[Archive Extract] {desc}")
                self.update_file_status(archive_row, "Extracting")

            def on_progress(progress, msg):
                self.log_message(f"[Archive Extract] {msg} ({progress:.1f}%)")
                self.update_file_progress(archive_row, int(progress))

            def on_finished(success, message, output_path):
                print(
                    f"[UI] on_finished called with: success={success}, message={message}, output_path={output_path}"
                )
                try:
                    if success:
                        self.log_message(f"Extraction complete: {message}")
                        # If extraction was skipped (files already extracted), remove archive row and process disk images
                        if "Files already extracted" in message:
                            self.files_table.setRowCount(
                                0
                            )  # Clear table so only disk images are shown
                            self.output_dir_edit.setText(output_path)
                            from PySide6.QtWidgets import QMessageBox

                            QMessageBox.information(
                                self,
                                "Using Existing Folder",
                                f"The extracted folder already exists and will be used: {output_path}",
                            )
                            self.log_message(
                                f"[INFO] Using existing extracted folder: {output_path}"
                            )
                            self.start_btn.setEnabled(True)
                            disk_images = self.file_scanner.find_disk_images(
                                output_path
                            )
                            if disk_images:
                                self.files_table.setRowCount(0)
                                for img in disk_images:
                                    row = self.add_file_to_table(img)
                                    self.update_file_status(row, "Pending")
                                    # Automatically queue extracted files for compression
                                    media_type = self.detect_media_type(img)
                                    compression_algos = self.get_compression_options()
                                    input_basename = os.path.basename(img)
                                    input_name_no_ext, _ = os.path.splitext(
                                        input_basename
                                    )
                                    output_dir = self.output_dir_edit.text().strip()
                                    output_path_chd = os.path.join(
                                        output_dir, input_name_no_ext + ".chd"
                                    )
                                    task = CHDTask(
                                        task_type=CHDTaskType.COMPRESS,
                                        input_file=img,
                                        output_file=output_path_chd,
                                        algorithms=compression_algos,
                                        hunk_size=self.get_hunk_size(media_type),
                                        force=self.overwrite_check.isChecked(),
                                        media_type=media_type,
                                        compression=self.get_compression_type(),
                                        user_data={"row": row, "original_input": img},
                                    )
                                    self.chd_manager.add_task(task)
                                self.log_message(
                                    f"Added {len(disk_images)} disk images from extracted archive and queued for compression."
                                )
                                self.start_btn.setEnabled(True)
                                self.cancel_btn.setEnabled(False)
                            else:
                                self.files_table.setRowCount(0)
                                self.log_message(
                                    "No disk images found in extracted archive or output folder.",
                                    level="warning",
                                )
                                self.update_file_status(
                                    archive_row, "No disk images found"
                                )
                    else:
                        self.log_message(f"Extraction failed: {message}", level="error")
                        self.update_file_status(archive_row, "Extraction failed")
                        self.start_btn.setEnabled(False)
                except Exception as exc:
                    import traceback

                    tb = traceback.format_exc()
                    self.log_message(f"UI handler exception: {exc}", level="error")
                    self.log_message(tb, level="error")
                    self.files_table.setRowCount(0)
                    self.log_message(
                        "A fatal error occurred in extraction/compression workflow. Please check the log.",
                        level="error",
                    )
                    self.start_btn.setEnabled(False)

            def on_error(error_msg):
                print(f"[UI] on_error called with: error_msg={error_msg}")
                self.log_message(f"Extraction error: {error_msg}", level="error")
                self.update_file_status(archive_row, "Extraction error")
                self.start_btn.setEnabled(False)

            # Determine output path for extraction
            output_dir = self.output_dir_edit.text().strip()
            if not output_dir:
                output_path = None
            else:
                output_path = output_dir
            self.log_message(
                f"[DEBUG] Calling archive_manager.extract with output_path={output_path!r}"
            )
            signals = self.archive_manager.extract(file_path, output_path=output_path)
            print(
                "[DEBUG] CompressionTab.browse_input: Connecting archive extraction signals..."
            )
            signals.started.connect(on_started)
            print("[DEBUG] CompressionTab.browse_input: Connected 'started' signal.")
            signals.progress.connect(on_progress)
            print("[DEBUG] CompressionTab.browse_input: Connected 'progress' signal.")
            signals.finished.connect(on_finished)
            print("[DEBUG] CompressionTab.browse_input: Connected 'finished' signal.")
            signals.error.connect(on_error)
            print("[DEBUG] CompressionTab.browse_input: Connected 'error' signal.")

            def on_finished(success, message, output_path):
                print(
                    f"[UI] on_finished called with: success={success}, message={message}, output_path={output_path}"
                )
                try:
                    if success:
                        self.log_message(f"Extraction complete: {message}")
                        # If extraction was skipped (files already extracted), remove archive row and process disk images
                        if "Files already extracted" in message:
                            self.files_table.setRowCount(
                                0
                            )  # Clear table so only disk images are shown
                            disk_images = self.file_scanner.find_disk_images(
                                output_path
                            )
                            if disk_images:
                                self.files_table.setRowCount(0)
                                for img in disk_images:
                                    row = self.add_file_to_table(img)
                                    self.update_file_status(row, "Pending")
                                    # Automatically queue extracted files for compression
                                    media_type = self.detect_media_type(img)
                                    compression_algos = self.get_compression_options()
                                    input_basename = os.path.basename(img)
                                    input_name_no_ext, _ = os.path.splitext(
                                        input_basename
                                    )
                                    output_dir = self.output_dir_edit.text().strip()
                                    output_path_chd = os.path.join(
                                        output_dir, input_name_no_ext + ".chd"
                                    )
                                    task = CHDTask(
                                        task_type=CHDTaskType.COMPRESS,
                                        input_file=img,
                                        output_file=output_path_chd,
                                        algorithms=compression_algos,
                                        hunk_size=self.get_hunk_size(media_type),
                                        force=self.overwrite_check.isChecked(),
                                        media_type=media_type,
                                        compression=self.get_compression_type(),
                                        user_data={"row": row, "original_input": img},
                                    )
                                    self.chd_manager.add_task(task)
                                self.log_message(
                                    f"Added {len(disk_images)} disk images from extracted archive and queued for compression."
                                )
                                self.start_btn.setEnabled(True)
                                self.cancel_btn.setEnabled(False)
                            else:
                                self.files_table.setRowCount(0)
                                self.log_message(
                                    "No disk images found in extracted archive or output folder.",
                                    level="warning",
                                )
                                self.update_file_status(
                                    archive_row, "No disk images found"
                                )
                        else:
                            self.files_table.setRowCount(0)
                            disk_images = self.file_scanner.find_disk_images(
                                output_path
                            )
                            if disk_images:
                                self.files_table.setRowCount(0)
                                for img in disk_images:
                                    row = self.add_file_to_table(img)
                                    self.update_file_status(row, "Pending")
                                    # Automatically queue extracted files for compression
                                    media_type = self.detect_media_type(img)
                                    compression_algos = self.get_compression_options()
                                    input_basename = os.path.basename(img)
                                    input_name_no_ext, _ = os.path.splitext(
                                        input_basename
                                    )
                                    output_dir = self.output_dir_edit.text().strip()
                                    output_path_chd = os.path.join(
                                        output_dir, input_name_no_ext + ".chd"
                                    )
                                    task = CHDTask(
                                        task_type=CHDTaskType.COMPRESS,
                                        input_file=img,
                                        output_file=output_path_chd,
                                        algorithms=compression_algos,
                                        hunk_size=self.get_hunk_size(media_type),
                                        force=self.overwrite_check.isChecked(),
                                        media_type=media_type,
                                        compression=self.get_compression_type(),
                                        user_data={"row": row, "original_input": img},
                                    )
                                    self.chd_manager.add_task(task)
                                self.log_message(
                                    f"Added {len(disk_images)} disk images from extracted archive and queued for compression."
                                )
                                self.start_btn.setEnabled(True)
                                self.cancel_btn.setEnabled(False)
                            else:
                                self.files_table.setRowCount(0)
                                self.log_message(
                                    "No disk images found in extracted archive or output folder.",
                                    level="warning",
                                )
                                self.update_file_status(
                                    archive_row, "No disk images found"
                                )
                    else:
                        self.log_message(f"Extraction failed: {message}", level="error")
                        if "archive_row" in locals():
                            self.update_file_status(archive_row, "Extraction failed")
                        self.start_btn.setEnabled(False)
                except Exception as exc:
                    import traceback

                    tb = traceback.format_exc()
                    self.log_message(f"UI handler exception: {exc}", level="error")
                    self.log_message(tb, level="error")
                    self.files_table.setRowCount(0)
                    self.log_message(
                        "A fatal error occurred in extraction/compression workflow. Please check the log.",
                        level="error",
                    )
                    self.start_btn.setEnabled(False)

            def on_error(error_msg):
                print(f"[UI] on_error called with: error_msg={error_msg}")
                self.log_message(f"Extraction error: {error_msg}", level="error")
                self.update_file_status(archive_row, "Extraction error")
                self.start_btn.setEnabled(False)

            signals.started.connect(on_started)
            signals.progress.connect(on_progress)
            signals.finished.connect(on_finished)
            signals.error.connect(on_error)
        else:
            row = self.add_file_to_table(file_path)
            self.update_file_status(row, "Pending")
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)

            try:
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if size_mb < 700:  # CD images are typically < 700MB
                    return "CD"
                else:
                    return "DVD"
            except (OSError, IOError) as e:
                # If we can't determine size, default to DVD
                self.log_message(
                    f"Warning: Could not determine file size for {file_path}: {e}"
                )
                return "DVD"

        # Default to Hard Disk for other formats
        return "Hard Disk"

    def cleanup_temp_directories(self):
        """Clean up all temporary directories created during archive extraction.
        Removes directories from disk and clears the tracked list. Logs actions and errors.
        """
        if not self.temp_directories:
            self.log_message("No temporary directories to clean up")
            return
        self.log_message(
            "Cleaning up {} temporary directories...".format(len(self.temp_directories))
        )

    def extract_archive(self, archive_path, row_index, max_retries=2, retry_delay=2):
        """Extract an archive file to a temporary directory."""
        import tempfile
        from PySide6.QtCore import QThread

        self.log_message(f"Extracting archive: {archive_path}")
        temp_dir = None
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if temp_dir and os.path.exists(temp_dir):
                    self._cleanup_temp_dir(temp_dir)
                temp_dir = tempfile.mkdtemp(prefix="retroclamp_")
                self.log_message(
                    f"Attempt {attempt + 1}/{max_retries + 1}: Created temporary directory: {temp_dir}"
                )
                if temp_dir not in self.temp_directories:
                    self.temp_directories.append(temp_dir)
                if row_index is not None:
                    self.update_file_status(
                        row_index,
                        f"Extracting (attempt {attempt + 1}/{max_retries + 1})...",
                    )
                    self.update_file_progress(row_index, 0)
                # Handle 7z archives with py7zr
                if archive_path.lower().endswith(".7z"):
                    try:
                        import py7zr

                        with py7zr.SevenZipFile(archive_path, mode="r") as z:
                            file_list = z.getnames()
                            total_files = len(file_list)
                            self.log_message(f"Found {total_files} files in archive")
                            extracted_count = 0
                            for file in file_list:
                                z.extract(path=temp_dir, targets=[file])
                                extracted_count += 1
                                if row_index is not None and total_files > 0:
                                    progress = int(
                                        (extracted_count / total_files) * 100
                                    )
                                    self.update_file_progress(row_index, progress)
                                    self.log_message(
                                        f"Extracted {extracted_count}/{total_files} files..."
                                    )
                        self.log_message(
                            f"Successfully extracted {extracted_count} files from 7z archive"
                        )
                        break
                    except Exception as e:
                        last_error = f"Failed to extract 7z archive: {str(e)}"
                        self.log_message(f"Error (attempt {attempt + 1}): {last_error}")
                        if attempt >= max_retries:
                            self.on_archive_error(last_error, row_index)
                            self._cleanup_temp_dir(temp_dir)
                            return False, None, []
                # Handle other archive types with patoolib
                else:
                    try:
                        import patoolib

                        try:
                            file_list = patoolib.get_archive_info(
                                archive_path, verbosity=-1
                            ).get("files", [])
                            self.log_message(f"Found {len(file_list)} files in archive")
                        except Exception:
                            self.log_message(
                                "Could not get file list from archive, extracting directly..."
                            )
                        patoolib.extract_archive(archive_path, outdir=temp_dir)
                        self.log_message("Successfully extracted archive")
                        break
                    except Exception as e:
                        last_error = f"Archive extraction failed: {e}"
                        self.log_message(f"Error (attempt {attempt + 1}): {last_error}")
                        if attempt >= max_retries:
                            self.on_archive_error(last_error, row_index)
                            self._cleanup_temp_dir(temp_dir)
                            return False, None, []
                if attempt < max_retries:
                    self.log_message(f"Retrying in {retry_delay} seconds...")
                    QThread.msleep(int(retry_delay * 1000))
            except Exception as e:
                last_error = str(e)
                if attempt >= max_retries:
                    self.on_archive_error(last_error, row_index)
                    self._cleanup_temp_dir(temp_dir)
                    return False, None, []
        try:
            if row_index is not None:
                self.update_file_status(row_index, "Scanning for disk images...")
                self.update_file_progress(row_index, 0)
            disk_images = self.file_scanner.find_disk_images(temp_dir)
            valid_images = []
            cue_files = [f for f in disk_images if f.lower().endswith(".cue")]
            orphan_bins = [
                f
                for f in disk_images
                if f.lower().endswith(".bin")
                and not any(
                    os.path.splitext(f)[0] == os.path.splitext(cue)[0]
                    for cue in cue_files
                )
            ]

            def cue_has_all_bins(cue_path):
                try:
                    cue_dir = os.path.dirname(cue_path)
                    with open(cue_path, "r", encoding="utf-8") as cuef:
                        lines = cuef.readlines()
                    bin_files = [
                        line.split('"')[1]
                        for line in lines
                        if line.strip().upper().startswith("FILE")
                        and "BINARY" in line.upper()
                    ]
                    for bin_file in bin_files:
                        bin_path = os.path.join(cue_dir, bin_file)
                        if not os.path.exists(bin_path):
                            return False, bin_file
                    return True, None
                except Exception as e:
                    self.log_message(f"Error parsing .cue file {cue_path}: {e}")
                    return False, str(e)

            for cue in cue_files:
                ok, missing = cue_has_all_bins(cue)
                if ok:
                    valid_images.append(cue)
                else:
                    self.log_message(
                        f"Warning: .cue file {os.path.basename(cue)} is missing referenced bin: {missing}",
                        level="warning",
                    )
            for f in disk_images:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".iso", ".gdi", ".img", ".cdr", ".mdf", ".nrg"]:
                    valid_images.append(f)
                elif ext == ".bin" and f in orphan_bins:
                    self.log_message(
                        f"Found .bin without .cue: {os.path.basename(f)}; skipping.",
                        level="warning",
                    )
            if not valid_images:
                self.log_message(
                    "No valid disk images (with .cue and all referenced .bin, or standalone images) found in extracted archive"
                )
                if row_index is not None:
                    self.update_file_status(
                        row_index, "Error: No valid disk images found"
                    )
                self._cleanup_temp_dir(temp_dir)
                return False, None, []
            self.log_message(f"Found {len(valid_images)} valid disk images in archive")
            if row_index is not None:
                self.update_file_status(row_index, "Extraction complete")
                self.update_file_progress(row_index, 100)
            return True, temp_dir, valid_images
        except Exception as e:
            error_msg = f"Failed to scan extracted files: {str(e)}"
            self.log_message(f"Error: {error_msg}")
            if row_index is not None:
                self.update_file_status(row_index, "Error: Failed to scan files")
            self._cleanup_temp_dir(temp_dir)
            return False, None, []

    def _cleanup_temp_dir(self, temp_dir):
        """Helper method to clean up a temporary directory."""
        if not temp_dir:
            return
        import shutil

        try:
            if not os.path.basename(temp_dir).startswith("retroclamp_"):
                self.log_message(
                    f"Warning: Not cleaning up non-retroclamp directory: {temp_dir}"
                )
                return
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir, topdown=False):
                    for name in files:
                        file_path = os.path.join(root, name)
                        try:
                            os.chmod(file_path, 0o777)
                        except Exception as e:
                            self.log_message(
                                f"Warning: Could not set permissions on {file_path}: {e}"
                            )
                    for name in dirs:
                        dir_path = os.path.join(root, name)
                        try:
                            os.chmod(dir_path, 0o777)
                        except Exception as e:
                            self.log_message(
                                f"Warning: Could not set permissions on directory {dir_path}: {e}"
                            )
                shutil.rmtree(temp_dir, ignore_errors=True)
                if os.path.exists(temp_dir):
                    self.log_message(
                        f"Warning: Could not remove temporary directory: {temp_dir}"
                    )
                else:
                    self.log_message(f"Cleaned up temporary directory: {temp_dir}")
            if temp_dir in self.temp_directories:
                self.temp_directories.remove(temp_dir)
        except Exception as e:
            self.log_message(f"Error cleaning up temporary directory {temp_dir}: {e}")
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            if temp_dir in self.temp_directories:
                self.temp_directories.remove(temp_dir)
        except Exception as cleanup_error:
            self.log_message(
                f"Warning: Could not clean up temporary directory: {str(cleanup_error)}"
            )

    def on_archive_error(self, error_message, row_index):
        """Handle archive extraction error."""
        formatted_error = str(error_message)
        self.log_message(f"Error: {formatted_error}")
        if row_index is not None and 0 <= row_index < self.files_table.rowCount():
            display_error = (
                formatted_error[:100] + "..."
                if len(formatted_error) > 100
                else formatted_error
            )
            self.update_file_status(row_index, f"Error: {display_error}")
            self.update_file_progress(row_index, 0)
            self.log_message(f"Detailed error: {str(error_message)}")

    def _prune_disk_images(self, disk_images):
        """Group disk images by base name and select the most appropriate file for each group."""
        groups = {}
        for path in disk_images:
            base, ext = os.path.splitext(os.path.basename(path).lower())
            if base not in groups:
                groups[base] = []
            groups[base].append((ext, path))
        pruned = []
        for base, files in groups.items():
            cue = next((f for ext, f in files if ext == ".cue"), None)
            if cue:
                pruned.append(cue)
                self.log_message(
                    f"Selected .cue file for disc '{base}': {os.path.basename(cue)}"
                )
            else:
                pruned.append(files[0][1])
                self.log_message(
                    f"No .cue file found for disc '{base}', using: {os.path.basename(files[0][1])}"
                )
        return pruned

    def get_compression_options(self):
        """Get the selected compression algorithms string from the profile combo."""
        profile = self.profile_combo.currentText()
        return COMPRESSION_PROFILES[profile]["algorithms"]

    def get_compression_type(self):
        """Get the CHDCompressionType for the selected profile."""
        profile = self.profile_combo.currentText()
        return PROFILE_TO_COMPRESSION_TYPE.get(profile, CHDCompressionType.ZLIB)

    def get_hunk_size(self, media_type):
        """Get appropriate hunk size for media type."""
        profile_name = self.profile_combo.currentText()
        if profile_name in COMPRESSION_PROFILES:
            return COMPRESSION_PROFILES[profile_name]["hunk_size"]
        if media_type == "CD":
            return 19584
        elif media_type == "DVD":
            return 2048
        else:
            return 4096

    def check_output_directory(self, output_dir):
        """Check if the output directory exists and is writable."""
        if not output_dir:
            QMessageBox.warning(
                self, "Output Directory Required", "Please select an output directory."
            )
            return False
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                self.log_message(f"Created output directory: {output_dir}")
            except OSError as e:
                QMessageBox.warning(
                    self,
                    "Output Directory Error",
                    f"Cannot create output directory: {output_dir}\n\nError: {str(e)}\n\n"
                    f"Please select a different output directory or ensure you have the necessary permissions.",
                )
                return False
        if not os.access(output_dir, os.W_OK):
            QMessageBox.warning(
                self,
                "Permission Error",
                f"Cannot write to output directory: {output_dir}\n\n"
                f"Please select a different output directory or ensure you have the necessary permissions.\n\n"
                f"Possible solutions:\n"
                f"1. Choose a different output directory\n"
                f"2. Run the application as administrator\n"
                f"3. Check if the drive is write-protected",
            )
            return False
        return True

    def on_task_progress(self, progress, row):
        """Handle CHD task progress."""
        if isinstance(progress, (int, float)) and progress >= 0:
            self.update_file_progress(row, progress)
            if progress > 0:
                self.update_file_status(row, "Compressing")
        elif isinstance(progress, (int, float)) and progress == -1:
            pass  # Message-only progress; handled elsewhere
        else:
            self.log_message(f"Debug: Received progress update: {progress}")

    def on_task_finished(self, success, message, row, file_path_for_log=None):
        print(
            f"[LOG] Entered on_task_finished: success={success}, message={message}, row={row}, file={file_path_for_log}"
        )
        try:
            file_basename = (
                os.path.basename(file_path_for_log)
                if file_path_for_log
                else "Unknown file"
            )
            if row is not None and row >= 0 and row < self.files_table.rowCount():
                if success:
                    self.update_file_status(row, "Completed")
                    self.update_file_progress(row, 100)
                    self.log_message(f"Compression completed for: {file_basename}")
                else:
                    self.update_file_status(row, "Failed")
                    self.log_message(
                        f"Compression failed for: {file_basename}. Reason: {message}"
                    )
            else:
                self.log_message(
                    f"Task finished (success: {success}) for {file_basename} but couldn't determine which row. Message: {message}"
                )
            if self.chd_manager.get_active_tasks_count() == 0:
                self.start_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)
                self.log_message("All compression tasks completed")
                self.cleanup_temp_directories()
                if hasattr(self, "maybe_close_app"):
                    self.maybe_close_app()
        except Exception as e:
            err_msg = f"[on_task_finished] Exception: {e}"
            self.log_message(err_msg, level="error")
            import traceback

            tb = traceback.format_exc()
            self.log_message(tb, level="error")
            try:
                with open("error.log", "a", encoding="utf-8") as logf:
                    logf.write(f"[on_task_finished] Exception: {e}\n{tb}\n")
            except Exception:
                pass
        print(
            f"[LOG] Exiting on_task_finished. start_btn enabled: {self.start_btn.isEnabled()}, cancel_btn enabled: {self.cancel_btn.isEnabled()}"
        )

    def update_overall_progress(self):
        """Calculate and update the overall progress bar based on all tasks."""
        total_rows = self.files_table.rowCount()
        if total_rows == 0:
            self.overall_progress.setValue(0)
            return
        total_progress = 0
        completed_count = 0
        for row in range(total_rows):
            progress_cell = self.files_table.cellWidget(row, 2)
            if progress_cell and hasattr(progress_cell, "value"):
                progress_value = progress_cell.value()
                total_progress += progress_value
                if progress_value == 100:
                    completed_count += 1
        average_progress = total_progress / total_rows if total_rows > 0 else 0
        self.progress_bar.setValue(int(average_progress))
        self.progress_bar.setToolTip(
            f"Overall Progress: {average_progress:.1f}% ({completed_count}/{total_rows} tasks complete)"
        )

    def progress_with_message(
        self, progress_value, message, row, file_path_for_log=None
    ):
        print(
            f"[LOG] Entered progress_with_message: progress_value={progress_value}, message={message}, row={row}, file={file_path_for_log}"
        )
        try:
            file_basename = (
                os.path.basename(file_path_for_log) if file_path_for_log else "Task"
            )
            if message and message.strip():
                if progress_value == -1 and not message.startswith(
                    f"[{file_basename}]"
                ):
                    self.log_message(f"[{file_basename} - Row {row}] {message.strip()}")
                elif progress_value != -1:
                    self.log_message(f"{message.strip()} (for {file_basename})")
                else:
                    self.log_message(message)
            if isinstance(progress_value, (int, float)) and progress_value >= 0:
                self.update_file_progress(row, progress_value)
                if row < self.files_table.rowCount() and self.files_table.item(
                    row, 1
                ).text() not in ["Completed", "Error", "Failed", "Cancelled"]:
                    self.update_file_status(row, "Compressing")
                self.update_overall_progress()
            elif progress_value == -1:
                pass
                if row < self.files_table.rowCount():
                    pass
        except Exception as e:
            err_msg = f"[progress_with_message] Exception: {e}"
            self.log_message(err_msg, level="error")
            import traceback

            tb = traceback.format_exc()
            self.log_message(tb, level="error")
            try:
                with open("error.log", "a", encoding="utf-8") as logf:
                    logf.write(f"[progress_with_message] Exception: {e}\n{tb}\n")
            except Exception:
                pass
        print("[LOG] Exiting progress_with_message")

    def on_task_error(self, error_message, row, file_path_for_log=None):
        print(
            f"[LOG] Entered on_task_error: error_message={error_message}, row={row}, file={file_path_for_log}"
        )
        file_basename = (
            os.path.basename(file_path_for_log) if file_path_for_log else "Unknown file"
        )
        self.log_message(f"ERROR for {file_basename}: {error_message}")
        if row >= 0 and row < self.files_table.rowCount():
            self.update_file_status(row, "Error")
            self.log_message(
                f"Compression failed for file at row {row}: {file_basename}"
            )
        else:
            self.log_message(
                f"Task failed for {file_basename} (invalid row {row}): {error_message}"
            )
        if self.chd_manager.get_active_tasks_count() == 0:
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.log_message("All compression tasks completed (with errors)")
            print(
                f"[LOG] All tasks complete in on_task_error. start_btn enabled: {self.start_btn.isEnabled()}, cancel_btn enabled: {self.cancel_btn.isEnabled()}"
            )
            self.cleanup_temp_directories()
            if hasattr(self, "maybe_close_app"):
                self.maybe_close_app()
        temp_dirs_to_clean = self.temp_directories.copy()
        for temp_dir in temp_dirs_to_clean:
            try:
                if os.path.exists(temp_dir):
                    import shutil

                    shutil.rmtree(temp_dir, ignore_errors=True)
                    self.log_message("Removed temporary directory: " + temp_dir)
                if temp_dir in self.temp_directories:
                    self.temp_directories.remove(temp_dir)
            except Exception as e:
                self.log_message(
                    "Error cleaning up temporary directory {}: {}".format(
                        temp_dir, str(e)
                    )
                )
        if self.temp_directories:
            self.log_message(
                "Warning: {} temporary directories could not be cleaned up".format(
                    len(self.temp_directories)
                )
            )
        else:
            self.log_message("All temporary directories cleaned up successfully")

    def closeEvent(self, event):
        """Handle widget close event.
        Cleans up resources and accepts the event."""
        import traceback

        print("".join(traceback.format_stack()))
        # Clean up temporary directories before closing
        self.log_message("Application closing, cleaning up resources...")
        self.cleanup_temp_directories()
        # Terminate any running CHDMAN processes
        self.chd_manager.terminate_all_chdman_processes()
        # Accept the close event
        event.accept()
