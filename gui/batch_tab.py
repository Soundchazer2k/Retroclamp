"""
Batch Processing Tab for RetroClamp.

This module provides the batch processing interface for RetroClamp,
allowing users to process multiple files at once.
"""

import logging  # Standard logging
import os
import tempfile
import time
import traceback

# Import archive handling libraries
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union  # Added Union

import py7zr
import rarfile  # type: ignore[import-untyped] # rarfile may not have type stubs
from PySide6.QtCore import (
    QByteArray,
    QSettings,  # Added QSettings
    Qt,
    QThread,
    QThreadPool,
    QTimer,
    Signal,
)
from PySide6.QtGui import (  # Added QCloseEvent
    QCloseEvent,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QGuiApplication,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.archive import ArchiveManager, ArchiveWorker
from core.chdman import (
    CHDCompressionType,
    CHDMan,
    CHDManSignals,  # Assuming this is needed by CHDMan methods
    CHDManWorker,
    CHDTaskType,
)
from core.checkpoint_manager import CheckpointManager
from core.debug_logger import (
    DebugLogger,
    get_logger,
)
from core.file_scanner import (
    FileScanner,  # Assuming this is needed by FileScanner methods
)

# Import UI components and utilities
from gui.ui_functions import get_icon
from utils import show_error, show_info, show_warning

# Constants for settings
SETTINGS_ORG = "RetroClamp"
SETTINGS_APP = "RetroClamp"
SETTINGS_BATCH = "BatchProcessing"


class BatchWorker(QThread):
    """Worker thread for batch processing tasks (using CHDMAN directly)."""

    progress = Signal(int, str)
    error = Signal(str, str)
    finished = Signal()
    file_completed = Signal(str, str)

    def __init__(
        self,
        file_path: str,
        output_dir: str,
        operation: str,
        compression: CHDCompressionType = CHDCompressionType.ZLIB,
        verify: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.file_path = file_path
        self.output_dir = output_dir
        self.operation_str = operation.lower()
        self.compression_enum = compression
        self.verify_output = verify
        self._is_running = True
        self.chdman_worker_instance: Optional[CHDManWorker] = None

    def run(self):
        try:
            with open("error.log", "a", encoding="utf-8") as logf:
                logf.write(f"\n[BatchWorker] Starting run at: {datetime.now()}\n")
                logf.write(f"  Operation: {self.operation_str}\n")
                logf.write(f"  Input file: {self.file_path}\n")
                logf.write(f"  Output dir: {self.output_dir}\n")
                logf.write(f"  Compression: {self.compression_enum.name}\n")
                logf.write(f"  Verify: {self.verify_output}\n")
            logging.info(
                f"[BatchWorker] Launching: {self.operation_str} -i '{self.file_path}' -o '{self.output_dir}'"
            )
        except Exception as logex:
            print(f"[BatchWorker] Failed to log start: {logex}")

        try:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            input_filename = Path(self.file_path).name
            base_name = Path(input_filename).stem
            output_file_path = ""

            chdman_instance = CHDMan()

            if self.operation_str == CHDTaskType.COMPRESS.name.lower():
                output_file_path = str(Path(self.output_dir) / f"{base_name}.chd")
                if Path(output_file_path).exists():
                    self.file_completed.emit(
                        self.file_path, f"Skipped (exists): {output_file_path}"
                    )
                    self.progress.emit(100, "Skipped")
                    self.finished.emit()  # Ensure finished is emitted even on skip
                    return

                # Assuming create_cd returns a tuple (signals, worker_instance)
                signals: CHDManSignals
                chd_worker: CHDManWorker
                signals, chd_worker = chdman_instance.create_cd(
                    input_file=self.file_path,
                    output_file=output_file_path,
                    compression=self.compression_enum,
                )
                self.chdman_worker_instance = chd_worker
                signals.progress_updated.connect(self._chd_progress_callback)
                signals.finished.connect(
                    lambda s, m: self._chd_finished_callback(s, m, output_file_path)
                )
                signals.error.connect(
                    lambda err_msg: self.error.emit(err_msg, self.file_path)
                )
                if self._is_running:
                    chd_worker.start()
                if self._is_running:
                    chd_worker.wait()

            elif self.operation_str.startswith(
                CHDTaskType.EXTRACT_CD.name.lower().split("_")[0]  # "extract"
            ):
                if not self.file_path.lower().endswith(".chd"):
                    raise ValueError("Input for extraction must be a .chd file.")
                output_file_path = str(
                    Path(self.output_dir) / f"{base_name}.bin"
                )  # Default, may need adjustment
                if Path(output_file_path).exists():
                    self.file_completed.emit(
                        self.file_path, f"Skipped (exists): {output_file_path}"
                    )
                    self.progress.emit(100, "Skipped")
                    self.finished.emit()
                    return

                signals: CHDManSignals
                chd_worker: CHDManWorker  # Type hint for clarity
                # This part needs to map self.operation_str to the correct CHDMan extract method
                if self.operation_str == CHDTaskType.EXTRACT_CD.name.lower():
                    signals, chd_worker = chdman_instance.extract_cd(
                        input_file=self.file_path, output_file=output_file_path
                    )
                # Add elif for EXTRACT_DVD, EXTRACT_HD, EXTRACT_RAW if BatchWorker is to handle them
                # For example:
                # elif self.operation_str == CHDTaskType.EXTRACT_HD.name.lower():
                #     signals, chd_worker = chdman_instance.extract_hd(...)
                else:  # Fallback or error for unhandled extract types by BatchWorker
                    raise ValueError(
                        f"Specific extract operation '{self.operation_str}' not implemented in BatchWorker."
                    )

                self.chdman_worker_instance = chd_worker
                signals.progress_updated.connect(self._chd_progress_callback)
                signals.finished.connect(
                    lambda s, m: self._chd_finished_callback(s, m, output_file_path)
                )
                signals.error.connect(
                    lambda err_msg: self.error.emit(err_msg, self.file_path)
                )
                if self._is_running:
                    chd_worker.start()
                if self._is_running:
                    chd_worker.wait()
            else:
                raise ValueError(
                    f"Unknown operation for BatchWorker: {self.operation_str}"
                )
            # Verification is complex and would happen after _chd_finished_callback confirms success.
            # For now, it's a placeholder.
        except Exception as e:
            tb = traceback.format_exc()
            # Log to file
            try:
                with open("error.log", "a", encoding="utf-8") as logf:
                    logf.write(
                        f"\n[BatchWorker] Exception in run: {datetime.now()}\n{tb}"
                    )
            except Exception:
                pass  # Ignore logging errors
            self.error.emit(f"{str(e)}\n{tb}", self.file_path)
            self.progress.emit(0, f"Error: {str(e)}")
            self.finished.emit()  # Ensure finished is emitted on error too

    def _chd_progress_callback(self, percent: float, status_msg: str):
        if self._is_running:
            self.progress.emit(int(percent), status_msg)

    def _chd_finished_callback(
        self, success: bool, message: str, output_path_final: str
    ):
        if (
            not self._is_running and not success
        ):  # If stopped and failed, message might be "cancelled"
            self.error.emit(
                f"CHDMAN operation stopped/cancelled: {message}", self.file_path
            )
        elif success:
            self.file_completed.emit(
                self.file_path, f"Completed: {Path(output_path_final).name}"
            )
        else:  # Failed but was not stopped externally
            self.error.emit(f"CHDMAN failed: {message}", self.file_path)
        self.finished.emit()

    def pause_processing(self):
        if self.chdman_worker_instance and hasattr(
            self.chdman_worker_instance, "pause"
        ):
            self.chdman_worker_instance.pause()
            current_progress, _ = self.chdman_worker_instance.get_progress()
            self.progress.emit(current_progress, "Paused by user")

    def resume_processing(self):
        if self.chdman_worker_instance and hasattr(
            self.chdman_worker_instance, "resume"
        ):
            self.chdman_worker_instance.resume()
            current_progress, _ = self.chdman_worker_instance.get_progress()
            self.progress.emit(current_progress, "Resumed by user")

    def stop_processing(self):
        self._is_running = False
        if self.chdman_worker_instance and hasattr(self.chdman_worker_instance, "stop"):
            self.chdman_worker_instance.stop()
        self.progress.emit(0, "Stopping...")


class BatchTab(QWidget):
    task_progress = Signal(int, str, int)
    task_error = Signal(str, int)
    task_finished = Signal(bool, str, int)

    def __init__(self, parent: Optional[QWidget] = None, app_settings: Any = None):
        super().__init__(parent)
        self.app_settings = app_settings
        # Fix for logger type
        self.logger: Union[DebugLogger, logging.Logger, None] = (
            get_logger(app_settings, module_name="BatchTab")
            if app_settings
            else logging.getLogger("BatchTab_fallback")
        )

        self.files: List[Dict[str, Any]] = []
        self.current_task_index = 0
        self.is_processing = False
        self.is_aborting = False
        self.is_paused = False
        self.processed_files = 0
        self.failed_files = 0
        self.total_files = 0
        self.temp_directories: List[str] = []
        self.batch_id: str = f"batch_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        self.checkpoint_manager = CheckpointManager()
        self.archive_manager = ArchiveManager()
        self.file_scanner = FileScanner()

        self.operation_combo: Optional[QComboBox] = None
        self.compression_combo: Optional[QComboBox] = None
        self.status_indicator: Optional[QLabel] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.file_table: Optional[QTableWidget] = None
        self.log_text: Optional[QTextEdit] = None
        self.recent_files: List[str] = []
        self.output_dir: str = str(Path.home() / "RetroClamp_Output")
        self.compression_level: str = "zlib"  # Should match CHDCompressionType names

        self.active_worker: Optional[BatchWorker] = None

        # UI components that need to be initialized in setup_ui
        self.add_files_btn: Optional[QPushButton] = None
        self.add_dir_btn: Optional[QPushButton] = None
        self.clear_btn: Optional[QPushButton] = None
        self.start_btn: Optional[QPushButton] = None
        self.pause_btn: Optional[QPushButton] = None
        self.abort_btn: Optional[QPushButton] = None
        self.resume_btn: Optional[QPushButton] = None
        self.save_checkpoint_btn: Optional[QPushButton] = None
        self.load_checkpoint_btn: Optional[QPushButton] = None
        self.checkpoint_info: Optional[QTextEdit] = None

        self.setAcceptDrops(True)
        self.setup_ui()  # Initializes UI elements including self.status_indicator
        self.load_settings()

        self.task_progress.connect(self.on_task_progress)
        self.task_error.connect(self.on_task_error)
        self.task_finished.connect(self.on_task_finished)

        QTimer.singleShot(500, self.check_for_existing_checkpoints)

    def load_settings(self):
        settings = QSettings(SETTINGS_ORG, SETTINGS_BATCH)
        geom = settings.value("geometry")
        if isinstance(geom, QByteArray):
            self.restoreGeometry(geom)
        state = settings.value("windowState")
        if isinstance(state, QByteArray):
            self.restoreState(state)
        recent = settings.value("recentFiles", [])
        if isinstance(recent, list):
            self.recent_files = [str(f) for f in recent if isinstance(f, str)]
        out_dir_val = settings.value("outputDirectory", self.output_dir)
        if isinstance(out_dir_val, str) and out_dir_val:
            self.output_dir = out_dir_val

        if self.operation_combo:
            op_name = settings.value("lastOperation", CHDTaskType.COMPRESS.name)
            if isinstance(op_name, str):
                for i in range(self.operation_combo.count()):
                    item_data = self.operation_combo.itemData(i)
                    if isinstance(item_data, CHDTaskType) and item_data.name == op_name:
                        self.operation_combo.setCurrentIndex(i)
                        break
        if self.compression_combo:
            comp_name = settings.value("lastCompression", CHDCompressionType.ZLIB.name)
            if isinstance(comp_name, str):
                for i in range(self.compression_combo.count()):
                    item_data = self.compression_combo.itemData(i)
                    if (
                        isinstance(item_data, CHDCompressionType)
                        and item_data.name == comp_name
                    ):
                        self.compression_combo.setCurrentIndex(i)
                        break

    def save_settings(self):
        settings = QSettings(SETTINGS_ORG, SETTINGS_BATCH)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        if self.recent_files:
            settings.setValue("recentFiles", self.recent_files)
        if self.output_dir:
            settings.setValue("outputDirectory", self.output_dir)
        if self.operation_combo and self.operation_combo.currentData():
            settings.setValue("lastOperation", self.operation_combo.currentData().name)
        if self.compression_combo and self.compression_combo.currentData():
            settings.setValue(
                "lastCompression", self.compression_combo.currentData().name
            )
        settings.sync()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        # ... (Operation and Compression groups setup as before) ...
        operation_group = QGroupBox("Operation")
        op_layout = QHBoxLayout()
        self.operation_combo = QComboBox()
        for task_type_enum in CHDTaskType:
            self.operation_combo.addItem(
                task_type_enum.name.replace("_", " ").title(), task_type_enum
            )
        self.operation_combo.setCurrentIndex(0)
        op_layout.addWidget(QLabel("Operation:"))
        op_layout.addWidget(self.operation_combo)
        operation_group.setLayout(op_layout)
        main_layout.addWidget(operation_group)

        compression_group = QGroupBox("Compression Settings (for Compress Operation)")
        comp_layout = QHBoxLayout()
        self.compression_combo = QComboBox()
        for comp_type_enum in CHDCompressionType:
            self.compression_combo.addItem(comp_type_enum.name, comp_type_enum)
        zlib_index = self.compression_combo.findData(CHDCompressionType.ZLIB)
        if zlib_index != -1:
            self.compression_combo.setCurrentIndex(zlib_index)
        comp_layout.addWidget(QLabel("Compression:"))
        comp_layout.addWidget(self.compression_combo)
        compression_group.setLayout(comp_layout)
        main_layout.addWidget(compression_group)

        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(
            ["File Name", "Size", "Output Directory", "Status"]
        )
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.setMinimumHeight(200)
        main_layout.addWidget(self.file_table, 1)

        drop_info_label = QLabel("Drag & Drop Files/Folders Here, or Use Buttons")
        drop_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_info_label.setObjectName(
            "dropInfoLabel"
        )  # Use object name for global CSS targeting
        main_layout.addWidget(drop_info_label)

        file_management_layout = QHBoxLayout()
        self.add_files_btn = QPushButton(
            get_icon("file-plus", color="#bbeeff"), " Add Files..."
        )
        self.add_files_btn.clicked.connect(self.add_files_dialog)
        self.add_dir_btn = QPushButton(
            get_icon("folder-plus", color="#bbeeff"), " Add Folder..."
        )
        self.add_dir_btn.clicked.connect(self.add_directory_dialog)
        self.clear_btn = QPushButton(get_icon("trash", color="#ffbbbb"), " Clear List")
        self.clear_btn.clicked.connect(self.clear_file_list)
        file_management_layout.addWidget(self.add_files_btn)
        file_management_layout.addWidget(self.add_dir_btn)
        file_management_layout.addStretch()
        file_management_layout.addWidget(self.clear_btn)
        main_layout.addLayout(file_management_layout)

        processing_group = QGroupBox("Processing Controls")
        pg_layout = QVBoxLayout()
        self.status_indicator = QLabel("Status: Idle")  # Initialized here
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pg_layout.addWidget(self.status_indicator)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")  # Fixed invalid format string
        pg_layout.addWidget(self.progress_bar)
        proc_buttons_layout = QHBoxLayout()
        self.start_btn = QPushButton(get_icon("play", color="#bbffbb"), " Start Batch")
        self.start_btn.clicked.connect(self.start_processing)
        self.pause_btn = QPushButton(get_icon("pause", color="#ffffbb"), " Pause")
        self.pause_btn.clicked.connect(self.toggle_pause_resume)
        self.abort_btn = QPushButton(get_icon("stop-circle", color="#ffbbbb"), " Abort")
        self.abort_btn.clicked.connect(self.abort_processing)
        proc_buttons_layout.addWidget(self.start_btn)
        proc_buttons_layout.addWidget(self.pause_btn)
        proc_buttons_layout.addWidget(self.abort_btn)
        pg_layout.addLayout(proc_buttons_layout)
        processing_group.setLayout(pg_layout)
        main_layout.addWidget(processing_group)

        checkpoint_group = QGroupBox("Checkpoint Management")
        cg_layout = QVBoxLayout()
        cp_buttons_layout = QHBoxLayout()
        self.resume_btn = QPushButton(
            get_icon("history", color="#bbeeff"), " Resume Last"
        )
        self.resume_btn.clicked.connect(self.resume_from_last_checkpoint)
        self.resume_btn.setVisible(False)
        self.save_checkpoint_btn = QPushButton(
            get_icon("save", color="#bbeeff"), " Save Checkpoint"
        )
        self.save_checkpoint_btn.clicked.connect(self.save_checkpoint)
        self.load_checkpoint_btn = QPushButton(
            get_icon("upload-cloud", color="#bbeeff"), " Load Checkpoint"
        )
        self.load_checkpoint_btn.clicked.connect(self.load_checkpoint_dialog)
        cp_buttons_layout.addWidget(self.resume_btn)
        cp_buttons_layout.addWidget(self.save_checkpoint_btn)
        cp_buttons_layout.addWidget(self.load_checkpoint_btn)
        cg_layout.addLayout(cp_buttons_layout)
        self.checkpoint_info = QTextEdit()
        self.checkpoint_info.setReadOnly(True)
        self.checkpoint_info.setMaximumHeight(80)
        self.checkpoint_info.setVisible(False)
        cg_layout.addWidget(self.checkpoint_info)
        checkpoint_group.setLayout(cg_layout)
        main_layout.addWidget(checkpoint_group)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(100)
        log_layout.addWidget(self.log_text, 1)
        log_buttons_layout = QHBoxLayout()
        export_log_btn = QPushButton(
            get_icon("file-export", color="#bbeeff"), " Export Log"
        )
        export_log_btn.clicked.connect(self.export_log)
        copy_log_btn = QPushButton(get_icon("copy", color="#bbeeff"), " Copy Log")
        copy_log_btn.clicked.connect(self.copy_log)
        log_buttons_layout.addStretch()
        log_buttons_layout.addWidget(export_log_btn)
        log_buttons_layout.addWidget(copy_log_btn)
        log_layout.addLayout(log_buttons_layout)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group, 1)

        self.setLayout(main_layout)
        self.update_ui_for_processing(False)

    def _set_status_indicator_text(
        self, status_key: Optional[str] = None, message: Optional[str] = None
    ):
        """Helper to set text on self.status_indicator QLabel."""
        if not self.status_indicator:
            return

        base_text = "Status: "
        styled_text = "<span style='color:#f1fa8c'>Idle</span>"  # Default

        if status_key == "processing":
            styled_text = "<span style='color:#50fa7b'>Processing</span>"
        elif status_key == "paused":
            styled_text = "<span style='color:#ffb86c'>Paused</span>"
        elif status_key == "error":
            styled_text = "<span style='color:#ff5555'>Error</span>"
        elif status_key == "completed":
            styled_text = "<span style='color:#50fa7b'>Completed</span>"
        elif status_key == "aborted":
            styled_text = "<span style='color:#ffb86c'>Aborted</span>"

        full_message = base_text + styled_text
        if message:
            full_message += f" - {message}"

        self.status_indicator.setText(full_message)

    def log_message(self, message: str, level: str = "info"):
        if self.log_text:
            icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✔️"}
            colors = {
                "info": "#729fcf",
                "warning": "#fce94f",
                "error": "#ef2929",
                "success": "#8ae234",
            }
            icon = icons.get(level, icons["info"])
            color = colors.get(level, colors["info"])
            timestamp = datetime.now().strftime("[%H:%M:%S]")
            html_message = (
                f"<span style='color:{color};'>{timestamp} {icon} {message}</span>"
            )
            self.log_text.append(html_message)
            sb = self.log_text.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

        if self.logger:
            log_method = getattr(self.logger, level, self.logger.info)
            # Ensure 'message' is passed correctly based on logger type
            if isinstance(self.logger, DebugLogger):
                log_method(None, message)  # DebugLogger: (module_name, message)
            elif isinstance(self.logger, logging.Logger):
                log_method(message)  # type: ignore[call-arg]  # stdlib Logger: (message,)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if not event.mimeData().hasUrls():
            return
        urls = event.mimeData().urls()
        if not urls:
            return
        current_output_dir = self.output_dir or str(Path.home() / "RetroClamp_Output")
        chosen_output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory for Dropped Items", current_output_dir
        )
        if not chosen_output_dir:
            self.log_message("Drop cancelled: No output directory selected.", "warning")
            return
        self.output_dir = chosen_output_dir
        for url in urls:
            path_str = url.toLocalFile()
            if Path(path_str).is_dir():
                self._process_dropped_directory(path_str, chosen_output_dir)
            elif Path(path_str).is_file():
                self._process_dropped_file(path_str, chosen_output_dir)

    def _add_file_to_queue(
        self,
        file_path: str,
        output_dir_for_file: str,
        is_archive: bool = False,
        source_archive: Optional[str] = None,
    ):
        if any(f.get("path") == file_path for f in self.files):
            self.log_message(
                f"File '{Path(file_path).name}' already in queue. Skipping.", "warning"
            )
            return
        try:
            file_size = (
                Path(file_path).stat().st_size if Path(file_path).exists() else 0
            )
        except OSError:
            file_size = 0
        status = "Pending (Archive)" if is_archive else "Pending"
        if source_archive:
            status += f" (from {Path(source_archive).name})"
        file_data = {
            "path": file_path,
            "name": Path(file_path).name,
            "size": file_size,
            "status": status,
            "output_dir": output_dir_for_file,
            "is_archive": is_archive,
            "source_archive": source_archive,
        }
        self.files.append(file_data)
        self._update_file_table()
        self.log_message(
            f"Added '{file_data['name']}' to queue.",
            "success" if not source_archive else "info",
        )

    def _process_dropped_file(self, file_path: str, output_dir_for_file: str):
        ext = Path(file_path).suffix.lower()
        is_archive = ext in [".zip", ".7z", ".rar"]
        self._add_file_to_queue(file_path, output_dir_for_file, is_archive=is_archive)

    def _process_dropped_directory(self, dir_path: str, base_output_dir: str):
        self.log_message(f"Scanning directory: '{dir_path}'...", "info")
        current_op: CHDTaskType = (
            self.operation_combo.currentData()
            if self.operation_combo
            else CHDTaskType.COMPRESS
        )
        relevant_exts: List[str] = []
        if current_op == CHDTaskType.COMPRESS:
            relevant_exts = [
                ".iso",
                ".bin",
                ".img",
                ".cue",
                ".gdi",
                ".zip",
                ".7z",
                ".rar",
            ]
        elif current_op.name.startswith("EXTRACT"):
            relevant_exts = [".chd"]
        files_found_in_dir = 0
        for root, _, filenames in os.walk(dir_path):
            for filename in filenames:
                file_path = str(Path(root) / filename)
                if Path(file_path).suffix.lower() in relevant_exts:
                    self._process_dropped_file(file_path, base_output_dir)
                    files_found_in_dir += 1
        if files_found_in_dir == 0:
            self.log_message(
                f"No relevant files ({', '.join(relevant_exts)}) found in directory '{dir_path}'.",
                "warning",
            )
        else:
            self.log_message(
                f"Found and added {files_found_in_dir} relevant files from '{dir_path}'.",
                "info",
            )

    def _update_file_table(self):
        if not self.file_table:
            return
        self.file_table.setRowCount(0)  # Clear before repopulating
        self.file_table.setRowCount(len(self.files))
        for row, data in enumerate(self.files):
            name_item = QTableWidgetItem(data.get("name", ""))
            size_item = QTableWidgetItem(self._format_file_size(data.get("size", 0)))
            output_dir_item = QTableWidgetItem(data.get("output_dir", ""))
            status_item = QTableWidgetItem(data.get("status", ""))

            self.file_table.setItem(row, 0, name_item)
            self.file_table.setItem(row, 1, size_item)
            self.file_table.setItem(row, 2, output_dir_item)
            self.file_table.setItem(row, 3, status_item)  # Set item first
            self._apply_status_coloring(
                status_item, data.get("status", "")
            )  # Then color

        self.total_files = len(self.files)

    def _apply_status_coloring(self, item: QTableWidgetItem, status_text: str):
        if "completed" in status_text.lower() or "done" in status_text.lower():
            item.setForeground(Qt.GlobalColor.darkGreen)
        elif "failed" in status_text.lower() or "error" in status_text.lower():
            item.setForeground(Qt.GlobalColor.red)
        elif "pending" in status_text.lower() or "skipped" in status_text.lower():
            item.setForeground(Qt.GlobalColor.darkYellow)
        elif "processing" in status_text.lower() or "extracting" in status_text.lower():
            item.setForeground(Qt.GlobalColor.blue)  # Or another color for active

    def _format_file_size(self, size_bytes: int) -> str:
        if size_bytes < 0:
            return "N/A"
        if size_bytes == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        i = 0
        size = float(size_bytes)
        while size >= 1024.0 and i < len(units) - 1:
            size /= 1024.0
            i += 1
        return f"{size:.1f} {units[i]}" if i > 0 else f"{int(size)} {units[i]}"

    def start_processing(self):
        if not self.files:
            show_warning("No files to process.", parent=self)
            return
        if self.is_processing:
            show_info("Processing already in progress.", parent=self)
            return
        for idx, file_data in enumerate(self.files):
            f_path = Path(file_data["path"])
            out_dir = Path(file_data["output_dir"])
            if not f_path.exists():
                show_error(f"Input file does not exist: {f_path}", parent=self)
                self.files[idx]["status"] = "Error: Input missing"
                self._update_file_table_row(idx)
                return
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
                if not os.access(out_dir, os.W_OK):
                    raise OSError("Output directory not writable.")
            except OSError as e:
                show_error(
                    f"Output directory issue for '{f_path.name}': {out_dir}\n{e}",
                    parent=self,
                )
                self.files[idx]["status"] = "Error: Output dir issue"
                self._update_file_table_row(idx)
                return
        self.is_processing = True
        self.is_aborting = False
        self.is_paused = False
        self.processed_files = 0
        self.failed_files = 0
        self.total_files = 0
        self.current_task_index = 0
        self.batch_id = f"batch_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.update_ui_for_processing(True)
        self.log_message(
            f"Starting batch (ID: {self.batch_id}) for {len(self.files)} items.", "info"
        )
        self.update_overall_progress()
        QTimer.singleShot(0, self.process_next_task)

    def process_next_task(self):
        if self.is_aborting:
            self.log_message("Processing aborted by user.", "warning")
            self._finalize_processing(aborted=True)
            return
        if self.is_paused:
            self.log_message("Processing is paused.", "info")
            self._set_status_indicator_text("paused", "Paused by user.")
            return
        if self.current_task_index >= len(self.files):
            self.log_message("All tasks completed or queue empty.", "info")
            self._finalize_processing(aborted=False)
            return

        current_file_data = self.files[self.current_task_index]
        self.log_message(
            f"Item {self.current_task_index + 1}/{len(self.files)}: '{current_file_data['name']}'",
            "info",
        )
        self._set_status_indicator_text(
            "processing",
            f"Item {self.current_task_index + 1}: {current_file_data['name']}",
        )
        if current_file_data.get("is_archive"):
            self._handle_archive_item(current_file_data, self.current_task_index)
        else:
            self._start_worker_for_file(current_file_data, self.current_task_index)

    def _start_worker_for_file(self, file_data: Dict[str, Any], row_idx: int):
        if self.active_worker and self.active_worker.isRunning():
            self.log_message("Error: An operation is already in progress.", "error")
            return
        op_type: CHDTaskType = (
            self.operation_combo.currentData()
            if self.operation_combo
            else CHDTaskType.COMPRESS
        )
        comp_type: CHDCompressionType = (
            self.compression_combo.currentData()
            if self.compression_combo
            else CHDCompressionType.ZLIB
        )
        worker_op_str = op_type.name.lower()
        self.active_worker = BatchWorker(
            file_path=file_data["path"],
            output_dir=file_data["output_dir"],
            operation=worker_op_str,
            compression=comp_type,
            verify=False,
            parent=self,
        )
        self.active_worker.setProperty("task_row_index", row_idx)  # Store row_idx
        self.active_worker.progress.connect(self._on_worker_progress)
        self.active_worker.error.connect(self._on_worker_error)
        self.active_worker.file_completed.connect(self._on_worker_file_completed)
        self.active_worker.finished.connect(self._on_worker_thread_finished)
        file_data["status"] = "Processing..."
        self._update_file_table_row(row_idx)
        self.active_worker.start()

    def _handle_archive_item(self, archive_data: Dict[str, Any], row_idx: int):
        archive_path = archive_data["path"]
        archive_name = archive_data["name"]
        output_for_contents = archive_data["output_dir"]
        self.log_message(f"Handling archive: {archive_name}", "info")
        archive_data["status"] = "Extracting archive..."
        self._update_file_table_row(row_idx)
        if not self.check_archive_compatibility(archive_path, row_idx):
            msg = f"No compatible files for current op in '{archive_name}'."
            self.log_message(msg, "warning")
            self.task_finished.emit(True, msg, row_idx)
            return  # Archive "processed" (skipped)

        temp_dir_for_archive = tempfile.mkdtemp(
            prefix=f"rc_batch_{Path(archive_name).stem}_"
        )
        self.temp_directories.append(temp_dir_for_archive)
        extraction_worker = ArchiveWorker(
            operation="extract",
            input_path=archive_path,
            output_path=temp_dir_for_archive,
        )
        # Fix: Use QObject.setProperty on QThread instance (ArchiveWorker)
        extraction_worker.setProperty("original_archive_path", archive_path)  # type: ignore[attr-defined]
        extraction_worker.setProperty("original_row_idx", row_idx)  # type: ignore[attr-defined]
        extraction_worker.setProperty("output_for_contents", output_for_contents)  # type: ignore[attr-defined]
        extraction_worker.signals.finished.connect(self._on_archive_extraction_finished)
        extraction_worker.signals.error.connect(self._on_archive_extraction_error)
        QThreadPool.globalInstance().start(extraction_worker)

    def _on_archive_extraction_finished(
        self, success: bool, message: str, temp_extract_path: Optional[str]
    ):
        sender_worker = self.sender()
        if not isinstance(sender_worker, ArchiveWorker):
            return
        original_archive_path = sender_worker.property("original_archive_path")
        row_idx = sender_worker.property("original_row_idx")
        output_for_contents = sender_worker.property("output_for_contents")
        if not success or not temp_extract_path:
            err_msg = f"Failed to extract archive '{Path(original_archive_path).name}': {message}"
            self.log_message(err_msg, "error")
            self.task_finished.emit(False, err_msg, row_idx)
            return
        self.log_message(
            f"Archive '{Path(original_archive_path).name}' extracted. Scanning...",
            "info",
        )
        current_op: CHDTaskType = (
            self.operation_combo.currentData()
            if self.operation_combo
            else CHDTaskType.COMPRESS
        )
        relevant_exts = (
            [".iso", ".bin", ".img", ".cue", ".gdi"]
            if current_op == CHDTaskType.COMPRESS
            else ([".chd"] if current_op.name.startswith("EXTRACT") else [])
        )
        newly_added_files = 0
        insert_point = row_idx + 1
        for root, _, filenames_in_temp in os.walk(temp_extract_path):
            for fname in filenames_in_temp:
                extracted_f_path = str(Path(root) / fname)
                if Path(extracted_f_path).suffix.lower() in relevant_exts:
                    self._add_file_to_queue(
                        extracted_f_path,
                        output_for_contents,
                        is_archive=False,
                        source_archive=original_archive_path,
                    )
                    if len(self.files) > insert_point:
                        self.files.insert(insert_point, self.files.pop())
                    insert_point += 1
                    newly_added_files += 1
        if newly_added_files > 0:
            self._update_file_table()
            final_msg = f"Archive '{Path(original_archive_path).name}' processed. Added {newly_added_files} items."
            self.task_finished.emit(True, final_msg, row_idx)
        else:
            final_msg = f"Archive '{Path(original_archive_path).name}' extracted, no relevant files found."
            self.log_message(final_msg, "warning")
            self.task_finished.emit(True, final_msg, row_idx)

    def _on_archive_extraction_error(self, error_msg: str):
        sender_worker = self.sender()
        if not isinstance(sender_worker, ArchiveWorker):
            return
        original_archive_path = sender_worker.property("original_archive_path")
        row_idx = sender_worker.property("original_row_idx")
        full_err_msg = (
            f"Error extracting '{Path(original_archive_path).name}': {error_msg}"
        )
        self.log_message(full_err_msg, "error")
        self.task_finished.emit(False, full_err_msg, row_idx)

    def _on_worker_progress(self, percent: int, status_msg: str):
        sender = self.sender()
        if sender:
            row_idx = sender.property("task_row_index")
            self.task_progress.emit(percent, status_msg, row_idx)

    def _on_worker_error(self, error_msg: str, file_path_from_worker: str):
        sender = self.sender()
        if sender:
            row_idx = sender.property("task_row_index")
            self.task_error.emit(error_msg, row_idx)

    def _on_worker_file_completed(self, file_path_completed: str, status_message: str):
        sender = self.sender()
        if sender:
            row_idx = sender.property("task_row_index")
            self.task_finished.emit(True, status_message, row_idx)

    def _on_worker_thread_finished(self):
        if self.active_worker:
            self.active_worker.deleteLater()
            self.active_worker = None

    def _update_file_table_row(self, row_idx: int):
        if not self.file_table or not (
            0 <= row_idx < len(self.files) and row_idx < self.file_table.rowCount()
        ):
            return
        data = self.files[row_idx]
        # Ensure items exist before setting text. _update_file_table should create them.
        item_name = self.file_table.item(row_idx, 0)
        item_size = self.file_table.item(row_idx, 1)
        item_out_dir = self.file_table.item(row_idx, 2)
        item_status = self.file_table.item(row_idx, 3)

        if item_name:
            item_name.setText(data.get("name", ""))
        if item_size:
            item_size.setText(self._format_file_size(data.get("size", 0)))
        if item_out_dir:
            item_out_dir.setText(data.get("output_dir", ""))
        if item_status:
            status_text = data.get("status", "")
            item_status.setText(status_text)
            self._apply_status_coloring(item_status, status_text)

    def on_task_progress(self, percent: int, message: str, row: int):
        if self.progress_bar and 0 <= row < len(self.files):
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(
                f"{self.files[row]['name']}: {percent}% - {message}"
            )
        if 0 <= row < len(self.files):
            self.files[row]["status"] = f"{message} ({percent}%)"
            self._update_file_table_row(row)

    def on_task_error(self, error_message: str, row: int):
        if not (0 <= row < len(self.files)):
            return
        self.failed_files += 1
        self.files[row]["status"] = f"Error: {error_message[:120]}"
        self.log_message(
            f"Error processing '{self.files[row]['name']}': {error_message}", "error"
        )
        self._update_file_table_row(row)
        self.update_overall_progress()
        self.current_task_index += 1
        QTimer.singleShot(0, self.process_next_task)

    def on_task_finished(self, success: bool, message: str, row: int):
        if not (0 <= row < len(self.files)):
            return
        if success:
            self.processed_files += 1
            self.files[row]["status"] = f"Done: {message}"
        else:
            self.failed_files += 1
            self.files[row]["status"] = f"Failed: {message}"
        self.log_message(
            f"Finished '{self.files[row]['name']}': {message} (Success: {success})",
            "success" if success else "error",
        )
        self._update_file_table_row(row)
        self.update_overall_progress()
        self.current_task_index += 1
        QTimer.singleShot(0, self.process_next_task)

    def update_overall_progress(self):
        if not self.progress_bar:
            return
        if self.total_files == 0:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("0/0 - 0%")
            return
        processed_count = self.processed_files + self.failed_files
        percent_overall = (
            int((processed_count / self.total_files) * 100)
            if self.total_files > 0
            else 0
        )
        self.progress_bar.setValue(percent_overall)
        self.progress_bar.setFormat(
            f"Overall: {processed_count}/{self.total_files} items - {percent_overall}%"
        )
        if not self.is_processing and processed_count == self.total_files:
            self.progress_bar.setFormat(
                f"Batch Complete: {processed_count}/{self.total_files} - {percent_overall}%"
            )

    def _finalize_processing(self, aborted: bool):
        self.is_processing = False
        self.is_aborting = False
        self.is_paused = False
        self.cleanup_temp_directories()
        self.update_ui_for_processing(False)
        completion_message = ""
        status_key = "completed"
        log_level = "success"
        if aborted:
            completion_message = (
                f"Aborted. {self.processed_files} done, {self.failed_files} failed."
            )
            status_key = "aborted"
            log_level = "warning"
        else:
            completion_message = f"Finished. {self.processed_files} done successfully."
            if self.failed_files > 0:
                completion_message += f" {self.failed_files} failed."
                status_key = "error"
                log_level = "warning"
        self._set_status_indicator_text(status_key, completion_message)  # Use helper
        self.log_message(completion_message, log_level)
        self._show_completion_message_dialog(
            completion_message, is_error=(self.failed_files > 0 or aborted)
        )
        self.save_checkpoint()

    def _show_completion_message_dialog(self, message: str, is_error: bool = False):
        title = "Processing Complete"
        icon = QMessageBox.Icon.Information
        if is_error:
            title = "Processing Finished with Issues"
            icon = QMessageBox.Icon.Warning
        QMessageBox(icon, title, message, QMessageBox.StandardButton.Ok, self).exec()

    def toggle_pause_resume(self):
        if not self.is_processing:
            self.log_message("No active process.", "info")
            return
        if self.is_aborting:
            self.log_message("Cannot pause/resume during abort.", "warning")
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            if self.active_worker:
                self.active_worker.pause_processing()
            if self.pause_btn:
                self.pause_btn.setText(" Resume")  # TODO: Update icon
            self._set_status_indicator_text("paused", "Paused by user.")  # Use helper
            self.log_message("Processing paused.", "info")
        else:
            if self.active_worker:
                self.active_worker.resume_processing()
            if self.pause_btn:
                self.pause_btn.setText(" Pause")  # TODO: Update icon
            self._set_status_indicator_text("processing", "Resuming...")  # Use helper
            self.log_message("Processing resumed.", "info")
            QTimer.singleShot(0, self.process_next_task)

    def abort_processing(self):
        if not self.is_processing:
            self.log_message("No active process to abort.", "info")
            return
        if self.is_aborting:
            self.log_message("Abort already initiated.", "info")
            return
        reply = QMessageBox.question(
            self,
            "Confirm Abort",
            "Abort processing? Current item will try to finish.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            return
        self.is_aborting = True
        if self.abort_btn:
            self.abort_btn.setEnabled(False)
        self.log_message("Abort requested. Current item completes.", "warning")
        self._set_status_indicator_text("aborted", "Abort requested...")  # Use helper
        if self.is_paused:
            self.is_paused = False
            if self.active_worker:
                self.active_worker.resume_processing()
            if self.pause_btn:
                self.pause_btn.setEnabled(False)
        if self.active_worker:
            self.active_worker.stop_processing()
        else:
            self._finalize_processing(aborted=True)

    def update_ui_for_processing(self, processing_active: bool):
        self.is_processing = processing_active
        if self.add_files_btn:
            self.add_files_btn.setEnabled(not processing_active)
        if self.add_dir_btn:
            self.add_dir_btn.setEnabled(not processing_active)
        if self.clear_btn:
            self.clear_btn.setEnabled(not processing_active)
        if self.operation_combo:
            self.operation_combo.setEnabled(not processing_active)
        if self.compression_combo:
            self.compression_combo.setEnabled(not processing_active)
        if self.load_checkpoint_btn:
            self.load_checkpoint_btn.setEnabled(not processing_active)
        if self.save_checkpoint_btn:
            self.save_checkpoint_btn.setEnabled(True)
        if self.start_btn:
            self.start_btn.setEnabled(not processing_active)
        if self.pause_btn:
            self.pause_btn.setEnabled(processing_active and not self.is_aborting)
        if self.abort_btn:
            self.abort_btn.setEnabled(processing_active and not self.is_aborting)
        if processing_active:
            if self.start_btn:
                self.start_btn.setText(" Processing...")
            self._set_status_indicator_text("processing")  # Use helper
        else:
            if self.start_btn:
                self.start_btn.setText(" Start Processing")
            if self.pause_btn:
                self.pause_btn.setText(" Pause")
                self.is_paused = False
            if self.abort_btn:
                self.abort_btn.setText(" Abort")
                self.is_aborting = False
            # Final status set by _finalize_processing or other actions

    def check_archive_compatibility(self, archive_path: str, row_idx: int) -> bool:
        self.log_message(f"Checking compatibility: {Path(archive_path).name}", "info")
        current_op: CHDTaskType = (
            self.operation_combo.currentData()
            if self.operation_combo
            else CHDTaskType.COMPRESS
        )
        target_exts = (
            [".iso", ".bin", ".img", ".cue", ".gdi"]
            if current_op == CHDTaskType.COMPRESS
            else ([".chd"] if current_op.name.startswith("EXTRACT") else [])
        )
        if not target_exts:
            self.log_message(
                f"No specific content check for op {current_op.name}.", "info"
            )
            return True
        try:
            if archive_path.lower().endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zf:
                    if any(
                        any(f.lower().endswith(ext) for ext in target_exts)
                        for f in zf.namelist()
                    ):
                        return True
            elif archive_path.lower().endswith(".7z"):
                with py7zr.SevenZipFile(archive_path, "r") as szf:
                    if any(
                        any(f.lower().endswith(ext) for ext in target_exts)
                        for f in szf.getnames()
                    ):
                        return True
            elif archive_path.lower().endswith(".rar"):
                with rarfile.RarFile(archive_path, "r") as rf:
                    if any(
                        any(f.lower().endswith(ext) for ext in target_exts)
                        for f in rf.namelist()
                    ):
                        return True
            self.log_message(
                f"No files matching {target_exts} in '{Path(archive_path).name}'.",
                "warning",
            )
            return False
        except Exception as e:
            show_error(
                f"Error checking archive '{Path(archive_path).name}': {e}",
                title="Archive Error",
                parent=self,
            )
            self.log_message(
                f"Error checking archive compatibility for {Path(archive_path).name}: {e}",
                "error",
            )
            if self.logger and isinstance(self.logger, DebugLogger):
                self.logger.error(None, f"Archive check error for {archive_path}: {e}")
            elif self.logger:  # Standard logger
                self.logger.error(  # type: ignore[union-attr,call-arg]
                    f"Archive check error for {archive_path}: {e}", exc_info=True
                )
            return False

    def cleanup_temp_directories(self, specific_dirs: Optional[List[str]] = None):
        dirs_to_clean = (
            specific_dirs if specific_dirs is not None else self.temp_directories
        )
        if not dirs_to_clean:
            return
        self.log_message(
            f"Cleaning {len(dirs_to_clean)} temp director{'y' if len(dirs_to_clean) == 1 else 'ies'}...",
            "info",
        )
        import shutil

        for temp_dir_path in list(dirs_to_clean):
            if not temp_dir_path or not Path(temp_dir_path).exists():
                if temp_dir_path in self.temp_directories and specific_dirs is None:
                    self.temp_directories.remove(temp_dir_path)
                continue
            try:
                shutil.rmtree(temp_dir_path, ignore_errors=True)
                self.log_message(f"Removed temp dir: {temp_dir_path}", "info")
            except Exception as e:
                self.log_message(
                    f"Failed to remove temp dir {temp_dir_path}: {e}", "error"
                )
            finally:
                if temp_dir_path in self.temp_directories and specific_dirs is None:
                    self.temp_directories.remove(temp_dir_path)
        if specific_dirs is None and not self.temp_directories:
            self.log_message("All temp dirs cleaned.", "info")
        elif specific_dirs is None and self.temp_directories:
            self.log_message(
                f"{len(self.temp_directories)} temp dirs remain.", "warning"
            )

    def save_checkpoint(self):
        if not self.files and not self.is_processing:
            show_info("No batch data to save.", parent=self)
            return False
        try:
            files_status = [
                {
                    "path": fd["path"],
                    "name": fd["name"],
                    "size": fd["size"],
                    "status": fd["status"],
                    "output_dir": fd["output_dir"],
                    "is_archive": fd.get("is_archive", False),
                    "source_archive": fd.get("source_archive"),
                }
                for fd in self.files
            ]
            op_data = (
                self.operation_combo.currentData()
                if self.operation_combo
                else CHDTaskType.COMPRESS
            )
            comp_data = (
                self.compression_combo.currentData()
                if self.compression_combo
                else CHDCompressionType.ZLIB
            )
            metadata = {
                "operation": op_data.name,
                "compression": comp_data.name,
                "processed_files": self.processed_files,
                "failed_files": self.failed_files,
                "is_processing": self.is_processing,
                "is_paused": self.is_paused,
                "current_task_index": self.current_task_index,
                "timestamp": time.time(),
                "output_dir_global": self.output_dir,
                "total_files": len(self.files),
            }
            cp_path = self.checkpoint_manager.create_checkpoint(
                batch_id=self.batch_id,
                files=files_status,
                current_index=self.current_task_index,
                metadata=metadata,
            )
            if cp_path:
                self.log_message(f"Checkpoint saved: {Path(cp_path).name}", "success")
                self.update_checkpoint_preview(cp_path)
                self.check_for_existing_checkpoints()
                return True
            else:
                self.log_message("Failed to save (no path returned).", "error")
                return False
        except Exception as e:
            show_error(
                f"Failed to save checkpoint: {e}", title="Save Error", parent=self
            )
            self.log_message(f"Error saving checkpoint: {e}", "error")
            if (
                self.logger
            ):  # Log with exc_info if standard logger, else not for DebugLogger
                if isinstance(self.logger, DebugLogger):
                    self.logger.error(f"CP Save Error: {e}")
                else:
                    self.logger.error(f"CP Save Error: {e}", exc_info=True)
            return False

    def load_checkpoint(self, checkpoint_file_path: Optional[str] = None) -> bool:
        if self.is_processing:
            show_warning("Cannot load while processing.", parent=self)
            return False
        try:
            if checkpoint_file_path is None:
                # Fix: Use get_latest_checkpoint instead of get_latest_checkpoint_info
                latest_cp_file = (
                    self.checkpoint_manager.get_latest_checkpoint()
                )  # Returns path or None
                if not latest_cp_file:
                    show_info("No recent checkpoint.", parent=self)
                    return False
                checkpoint_file_path = latest_cp_file
            if not checkpoint_file_path or not Path(checkpoint_file_path).exists():
                show_error(f"CP file not found: {checkpoint_file_path}", parent=self)
                return False
            cp_data = self.checkpoint_manager.load_checkpoint(checkpoint_file_path)
            if not cp_data:
                show_error(
                    f"Could not load data from {Path(checkpoint_file_path).name}",
                    parent=self,
                )
                return False
            self.files = cp_data.get("files", [])
            self.current_task_index = cp_data.get("current_index", 0)
            metadata = cp_data.get("metadata", {})
            self.processed_files = metadata.get("processed_files", 0)
            self.failed_files = metadata.get("failed_files", 0)
            self.total_files = metadata.get("total_files", len(self.files))
            self.is_paused = metadata.get("is_paused", False)
            self.output_dir = metadata.get("output_dir_global", self.output_dir)
            self.batch_id = cp_data.get("batch_id", self.batch_id)
            self._update_file_table()
            self.update_overall_progress()
            self.restore_ui_state_from_metadata(metadata)
            self.update_checkpoint_preview(checkpoint_file_path)
            self.log_message(
                f"CP '{Path(checkpoint_file_path).name}' loaded.", "success"
            )
            was_processing = metadata.get("is_processing", False)
            if was_processing and not self.is_paused:
                reply = QMessageBox.question(
                    self,
                    "Resume?",
                    "CP saved during active processing. Resume?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.is_processing = True
                    self.update_ui_for_processing(True)
                    QTimer.singleShot(0, self.process_next_task)
            elif self.is_paused:
                self.update_ui_for_processing(True)
                self._set_status_indicator_text("paused", "Loaded paused state.")
            else:
                self.update_ui_for_processing(False)
            return True
        except Exception as e:
            show_error(f"Failed to load CP: {e}", title="Load Error", parent=self)
            self.log_message(f"Error loading CP: {e}", "error")
            if self.logger:
                if isinstance(self.logger, DebugLogger):
                    self.logger.error(None, f"CP Load Error: {e}")
                else:
                    self.logger.error(f"CP Load Error: {e}")  # type: ignore[union-attr]
            return False

    def restore_ui_state_from_metadata(self, metadata: Dict[str, Any]):
        if self.operation_combo and "operation" in metadata:
            op_name = metadata["operation"]
            idx = self.operation_combo.findData(
                CHDTaskType[op_name] if op_name in CHDTaskType.__members__ else -1
            )
            if idx != -1:
                self.operation_combo.setCurrentIndex(idx)
        if self.compression_combo and "compression" in metadata:
            comp_name = metadata["compression"]
            idx = self.compression_combo.findData(
                CHDCompressionType[comp_name]
                if comp_name in CHDCompressionType.__members__
                else -1
            )
            if idx != -1:
                self.compression_combo.setCurrentIndex(idx)

    def check_for_existing_checkpoints(self):
        # Fix: Use get_latest_checkpoint which returns path or None
        latest_cp_path = self.checkpoint_manager.get_latest_checkpoint()
        if latest_cp_path and self.resume_btn:
            self.resume_btn.setVisible(True)
            try:
                mod_time = Path(latest_cp_path).stat().st_mtime
            except OSError:
                mod_time = 0
            if mod_time:
                self.resume_btn.setToolTip(
                    f"Resume from CP of {time.strftime('%Y-%m-%d %H:%M', time.localtime(mod_time))}"
                )
            self.update_checkpoint_preview(latest_cp_path)
            self.log_message(f"Latest CP found: {Path(latest_cp_path).name}", "info")
        elif self.resume_btn:
            self.resume_btn.setVisible(False)
            if self.checkpoint_info:
                self.checkpoint_info.setVisible(False)

    def update_checkpoint_preview(self, checkpoint_file_path: str):
        if not self.checkpoint_info:
            return
        try:
            cp_data = self.checkpoint_manager.load_checkpoint(checkpoint_file_path)
            if not cp_data:
                self.checkpoint_info.setHtml("<p><i>Could not load preview.</i></p>")
                self.checkpoint_info.setVisible(True)
                return
            metadata = cp_data.get("metadata", {})
            files_in_cp = cp_data.get("files", [])
            total = metadata.get("total_files", len(files_in_cp))
            completed = metadata.get("processed_files", 0)
            failed = metadata.get("failed_files", 0)
            current_idx = metadata.get(
                "current_task_index", cp_data.get("current_index", 0)
            )
            next_file = (
                files_in_cp[current_idx]["name"]
                if 0 <= current_idx < len(files_in_cp)
                else "N/A"
            )
            created_t = metadata.get(
                "timestamp",
                (
                    Path(checkpoint_file_path).stat().st_mtime
                    if Path(checkpoint_file_path).exists()
                    else 0
                ),
            )
            preview_html = f"""<body style='font-size:9pt;'><b>File:</b> {Path(checkpoint_file_path).name}<br>
                <b>Created:</b> {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_t))}<br>
                <b>Progress:</b> {completed} done, {failed} failed of {total}.<br>
                <b>Next ({current_idx + 1}):</b> {next_file}<br>
                <b>Op:</b> {metadata.get("operation", "N/A")}, <b>Comp:</b> {metadata.get("compression", "N/A")}</body>"""
            self.checkpoint_info.setHtml(preview_html)
            self.checkpoint_info.setVisible(True)
        except Exception as e:
            self.checkpoint_info.setHtml(f"<p><i>Error loading preview: {e}</i></p>")
            self.checkpoint_info.setVisible(True)
            self.log_message(
                f"Error updating CP preview for {checkpoint_file_path}: {e}", "error"
            )

    def resume_from_last_checkpoint(self):
        self.load_checkpoint()

    def load_checkpoint_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load CP", self.checkpoint_manager.checkpoint_dir, "CP Files (*.json)"
        )
        if file_path:
            self.load_checkpoint(file_path)

    def add_files_dialog(self):
        current_op: CHDTaskType = (
            self.operation_combo.currentData()
            if self.operation_combo
            else CHDTaskType.COMPRESS
        )
        file_filter = (
            "Disk Images & Archives (*.iso *.bin *.img *.cue *.gdi *.zip *.7z *.rar);;All (*.*)"
            if current_op == CHDTaskType.COMPRESS
            else (
                "CHD (*.chd);;All (*.*)"
                if current_op.name.startswith("EXTRACT")
                else "All (*.*)"
            )
        )
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", self.output_dir, file_filter
        )
        if files:
            chosen_out_dir = QFileDialog.getExistingDirectory(
                self, "Select Output Dir", self.output_dir
            )
            if not chosen_out_dir:
                self.log_message("File add cancelled (no output dir).", "warning")
                return
            self.output_dir = chosen_out_dir
            for f_path in files:
                self._process_dropped_file(f_path, chosen_out_dir)

    def add_directory_dialog(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", self.output_dir
        )
        if dir_path:
            chosen_out_dir = QFileDialog.getExistingDirectory(
                self, "Select Output Dir", self.output_dir
            )
            if not chosen_out_dir:
                self.log_message("Folder add cancelled (no output dir).", "warning")
                return
            self.output_dir = chosen_out_dir
            self._process_dropped_directory(dir_path, chosen_out_dir)

    def clear_file_list(self):
        if self.is_processing:
            show_warning("Cannot clear while processing.", parent=self)
            return
        if not self.files:
            show_info("List already empty.", parent=self)
            return
        reply = QMessageBox.question(
            self,
            "Confirm Clear",
            "Clear all items?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.files.clear()
            self._update_file_table()
            self.processed_files = 0
            self.failed_files = 0
            self.total_files = 0
            self.current_task_index = 0
            self.update_overall_progress()
            self._set_status_indicator_text("idle", "List cleared.")
            self.log_message("List cleared.", "info")

    def export_log(self):
        if not self.log_text or not self.log_text.toPlainText():
            show_info("Log empty.", parent=self)
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", "BatchLog.html", "HTML (*.html);;Text (*.txt)"
        )
        if save_path:
            try:
                content = (
                    self.log_text.toHtml()
                    if save_path.endswith(".html")
                    else self.log_text.toPlainText()
                )
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log_message(f"Log exported to {save_path}", "success")
            except Exception as e:
                show_error(f"Failed to export: {e}", title="Export Error", parent=self)
                self.log_message(f"Error exporting: {e}", "error")

    def copy_log(self):
        if not self.log_text or not self.log_text.toPlainText():
            show_info("Log empty.", parent=self)
            return
        cb = QGuiApplication.clipboard()
        if cb:
            cb.setText(self.log_text.toPlainText())
            self.log_message("Log copied.", "success")
        else:
            show_error("No clipboard.", parent=self)

    def closeEvent(self, event: QCloseEvent):  # Fix: QCloseEvent
        if self.is_processing:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Processing active. Exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            else:
                self.is_aborting = True
            if self.active_worker:
                self.active_worker.stop_processing()
        self.save_settings()
        if self.files:
            self.save_checkpoint()
        self.cleanup_temp_directories()
        event.accept()
