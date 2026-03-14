"""Compression tab for RetroClamp - Refactored Version.

This module provides the UI and functionality for compressing disk images
using the CHDMAN utility.
"""

import functools  # Added for functools.partial
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, TypedDict

from PySide6.QtCore import QTimer, Signal, Slot  # Added Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,  # ADDED IMPORT
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.archive import ArchiveManager
from core.chdman import CHDTask, CHDTaskType, get_chd_manager
from core.debug_logger import DebugLogger, get_logger
from core.file_scanner import FileScanner
from core.temp_manager import TempDirectoryManager
from gui.layout_utils import StandardFormLayout

# Constants
FILE_TABLE_COLUMNS = 3
UI_UPDATE_INTERVAL_MS = 1000
DEFAULT_LOG_FILENAME = "retroclamp.log"


# Compression profiles
class ProfileSettings(TypedDict):
    algorithms: str
    hunk_size: int
    media: str


COMPRESSION_PROFILES: Dict[str, ProfileSettings] = {
    "CD - Default": {
        "algorithms": "cdlz,cdzl,cdfl",
        "hunk_size": 19584,
        "media": "CD",
    },
    "CD - Fast": {
        "algorithms": "cdlz",
        "hunk_size": 19584,
        "media": "CD",
    },
    "DVD - Default": {
        "algorithms": "zlib,huff",
        "hunk_size": 2048,
        "media": "DVD",
    },
    "DVD - Best": {
        "algorithms": "lzma",
        "hunk_size": 2048,
        "media": "DVD",
    },
    "Hard Disk - Default": {
        "algorithms": "zlib,huff",
        "hunk_size": 4096,
        "media": "Hard Disk",
    },
    "Hard Disk - Best": {
        "algorithms": "lzma",
        "hunk_size": 4096,
        "media": "Hard Disk",
    },
}


class CompressionTab(QWidget):
    """Compression tab widget.

    This widget provides a UI for compressing disk images using CHDMAN.
    """

    # Custom signals for better communication
    compression_started = Signal()
    compression_finished = Signal(bool)  # success
    file_processed = Signal(str, bool, str)  # file_path, success, message

    logger: Optional[DebugLogger]

    def __init__(self, parent: Optional[QWidget] = None, app_settings: Any = None):
        """Initialize the CompressionTab widget.

        Args:
            parent: Parent widget
            app_settings: AppSettings instance for debug logging
        """
        super().__init__(parent)

        self.app_settings = app_settings
        self.logger = None
        if app_settings:
            self.logger = get_logger(app_settings, module_name="CompressionTab")
            if self.logger:
                self.logger.info(
                    "CompressionTab", "CompressionTab initializing with debug logger"
                )

        # Initialize managers
        self.chd_manager = get_chd_manager()
        if not self.chd_manager:  # Validate manager
            msg = "FATAL: CHDManager could not be initialized."
            self.log_message(msg, level="error")
            if self.logger:
                self.logger.error("CompressionTab", msg)
            # Potentially disable the tab or show a critical error
            QMessageBox.critical(
                self,
                "Initialization Error",
                "CHDManager failed to load. Compression will not work.",
            )

        self.archive_manager = ArchiveManager(debug_logger=self.logger)
        self.file_scanner = FileScanner(debug_logger=self.logger)
        self.temp_manager = TempDirectoryManager(debug_logger=self.logger)

        # Initialize state
        self.queued_files: Set[str] = set()
        self.is_processing = False

        # UI state timer for periodic updates
        self.ui_timer = QTimer(self)  # Pass parent
        self.ui_timer.timeout.connect(self._update_ui_state)
        self.ui_timer.start(UI_UPDATE_INTERVAL_MS)

        # Setup UI and connect signals
        self._build_ui()
        self._connect_signals()
        self._update_ui_state()  # Initial UI state

        self._log_initialization()

    def _log_initialization(self) -> None:
        """Log initialization details."""
        if self.logger:
            self.logger.info(
                "CompressionTab", "CompressionTab initialized with CHDMAN singleton"
            )

        # Also log to the old log file for backward compatibility
        try:
            with open(DEFAULT_LOG_FILENAME, "a", encoding="utf-8") as logf:
                logf.write(
                    f"[{datetime.now()}] [CompressionTab] Initialized with CHDMAN singleton.\n"
                )
        except Exception as e:
            if self.logger:
                self.logger.warning(
                    "CompressionTab", f"Failed to write to old log file: {e}"
                )

    def log_message(self, message: str, level: str = "info") -> None:
        """Enhanced log message method that uses both old and new logging."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_ui_message = f"[{timestamp}] [{level.upper()}] {message}"

        if self.logger:
            log_method = getattr(self.logger, level.lower(), self.logger.info)
            log_method("CompressionTab", message)  # Use the logger's module context

        # Update UI log panel (ensure it's done on the main thread if called from others)
        # For now, assuming log_message is called from main thread or Qt's signal mechanism handles it.
        if hasattr(self, "log_panel"):  # Check if UI is built
            self.log_panel.append(formatted_ui_message)
            scrollbar = self.log_panel.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())

        # Also write to fallback log file
        try:
            with open(DEFAULT_LOG_FILENAME, "a", encoding="utf-8") as logf:
                logf.write(formatted_ui_message + "\n")
        except Exception as e:
            if self.logger:
                self.logger.warning(
                    "CompressionTab", f"Failed to write to fallback log file: {e}"
                )

    def clear_log(self) -> None:
        """Clear the log output."""
        self.log_panel.clear()
        self.log_message("Log cleared", "info")

    def export_log(self) -> None:
        """Export the log contents to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"retroclamp_log_{timestamp}.txt"

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Log",
            default_name,
            "Text Files (*.txt);;HTML Files (*.html)",
        )
        if filename:
            content = (
                self.log_panel.toHtml()
                if filename.endswith(".html")
                else self.log_panel.toPlainText()
            )
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log_message(
                    f"Log exported to {filename}", level="info"
                )  # Changed from success
            except OSError as e:
                self.log_message(f"Failed to export log: {e}", level="error")

    def copy_log(self) -> None:
        """Copy the log contents to the clipboard."""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.log_panel.toPlainText())
        self.log_message(
            "Log copied to clipboard", level="info"
        )  # Changed from success

    def _validate_inputs(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Validate input and output paths.

        Returns:
            Tuple of (input_path, output_path) or (None, None) if invalid
        """
        input_text = self.input_path_edit.text().strip()
        if not input_text:
            QMessageBox.warning(
                self, "Invalid Input", "Please specify an input file or archive."
            )
            self.log_message(
                "Input validation failed: Input file not specified.", level="warning"
            )
            return None, None

        input_path = Path(input_text)
        if not input_path.exists():
            QMessageBox.warning(
                self,
                "Invalid Input",
                f"The specified input file does not exist: {input_text}",
            )
            self.log_message(
                f"Input validation failed: Input file does not exist: {input_text}",
                level="warning",
            )
            return None, None

        output_path_str: Optional[str] = None
        if self.use_same_dir_check.isChecked():
            output_path = input_path.parent
            output_path_str = str(output_path)
        else:
            output_text = self.output_dir_edit.text().strip()
            if not output_text:
                QMessageBox.warning(
                    self, "Invalid Output", "Please specify an output directory."
                )
                self.log_message(
                    "Input validation failed: Output directory not specified.",
                    level="warning",
                )
                return None, None
            output_path = Path(output_text)
            output_path_str = output_text

        if not output_path.exists():
            QMessageBox.warning(
                self,
                "Invalid Output",
                f"The specified output directory does not exist: {output_path_str}",
            )
            self.log_message(
                f"Input validation failed: Output directory does not exist: {output_path_str}",
                level="warning",
            )
            return None, None

        if not output_path.is_dir():
            QMessageBox.warning(
                self,
                "Invalid Output",
                f"The specified output path is not a directory: {output_path_str}",
            )
            self.log_message(
                f"Input validation failed: Output path is not a directory: {output_path_str}",
                level="warning",
            )
            return None, None

        try:
            test_file = output_path / f".write_test_{datetime.now().timestamp()}"
            test_file.touch()
            test_file.unlink()
        except OSError as e:
            QMessageBox.warning(
                self,
                "Invalid Output",
                f"The specified output directory is not writable: {output_path_str}. Error: {e}",
            )
            self.log_message(
                f"Input validation failed: Output directory not writable: {output_path_str}",
                level="warning",
            )
            return None, None

        return input_path, output_path

    def start_compression(self) -> None:
        """Start the compression process with comprehensive debug logging."""
        self.log_message("Start compression process requested.", "info")
        if self.logger:
            self.logger.debug("CompressionTab", "start_compression() called")

        if not self.chd_manager:
            self.log_message(
                "CHDManager not available. Cannot start compression.", "error"
            )
            if self.logger:
                self.logger.error(
                    "CompressionTab", "CHDManager is None in start_compression."
                )
            return

        input_path, output_path = self._validate_inputs()
        if not input_path or not output_path:
            self.log_message(
                "Input validation failed. Aborting compression.", "warning"
            )
            return

        if self.is_processing:
            self.log_message("Compression is already in progress.", "warning")
            if self.logger:
                self.logger.warning(
                    "CompressionTab",
                    "start_compression called while already processing.",
                )
            return

        if self.logger:
            self.logger.info(
                "CompressionTab",
                f"Input validated - input: {input_path}, output: {output_path}",
            )

        try:
            self.chd_manager.clear_tasks()
        except Exception as e:
            self.log_message(f"Error clearing CHD tasks: {e}", "error")
            if self.logger:
                self.logger.exception("CompressionTab", "Failed to clear CHD tasks")
            self._abort_processing()  # Abort if we can't clear tasks
            return

        self.queued_files.clear()
        self.files_table.setRowCount(0)

        self.is_processing = True
        self.compression_started.emit()
        self.overall_progress.setValue(0)
        self.overall_progress.setFormat("Starting...")
        self._update_ui_state()  # Reflect processing state immediately

        try:
            if self.archive_manager.is_archive(str(input_path)):
                if self.logger:
                    self.logger.info(
                        "CompressionTab", f"Processing archive: {input_path}"
                    )
                self._process_archive(input_path, output_path)
            else:
                if self.logger:
                    self.logger.info(
                        "CompressionTab", f"Processing single file: {input_path}"
                    )
                self._queue_chd_task_for_file(input_path, output_path)
                if self.chd_manager.has_pending_tasks():
                    self._execute_tasks()
                else:
                    self.log_message(
                        "No CHD tasks to process after queuing single file.", "info"
                    )
                    self._finish_processing_if_needed(
                        True
                    )  # Assume success if no tasks
        except Exception as e:
            self.log_message(f"Error starting compression: {e}", "error")
            if self.logger:
                self.logger.exception(
                    "CompressionTab", "Exception in start_compression main block"
                )
            self._abort_processing()

    def _process_archive(self, archive_path: Path, final_chd_dir: Path) -> None:
        """Extracts the archive asynchronously and queues extracted disk images for compression."""
        self.log_message(
            f"Starting archive extraction for {archive_path.name}...", level="info"
        )
        if self.logger:
            self.logger.debug(
                "CompressionTab", f"_process_archive called for {archive_path.name}"
            )

        try:
            temp_dir = self.temp_manager.create_temp_dir(prefix="retroclamp_extract_")
            self.log_message(
                f"Extracting to temporary directory: {temp_dir}", level="debug"
            )
            if self.logger:
                self.logger.debug("CompressionTab", f"Created temp dir: {temp_dir}")

            extraction_signals = self.archive_manager.extract(
                str(archive_path), str(temp_dir)
            )

            extraction_signals.progress.connect(self._on_archive_extraction_progress)
            extraction_signals.error.connect(
                functools.partial(self._on_archive_extraction_error, archive_path.name)
            )
            extraction_signals.finished.connect(
                functools.partial(
                    self._on_archive_extracted,
                    temp_dir,
                    final_chd_dir,
                    archive_path.name,
                )
            )
        except Exception as e:
            self.log_message(
                f"Failed to start archive extraction for {archive_path.name}: {e}",
                "error",
            )
            if self.logger:
                self.logger.exception(
                    "CompressionTab",
                    f"Error in _process_archive for {archive_path.name}",
                )
            self._abort_processing()

    @Slot(float, str)
    def _on_archive_extraction_progress(self, pct: float, msg: str):
        self.overall_progress.setFormat(f"Extracting: {pct:.0f}% - {msg}")
        # Scale extraction progress to 0-50% of overall progress
        self.overall_progress.setValue(int(pct / 2))

    @Slot(str, str)  # archive_name, error_message
    def _on_archive_extraction_error(self, archive_name: str, error_message: str):
        self.log_message(
            f"Archive extraction failed for {archive_name}: {error_message}", "error"
        )
        QMessageBox.critical(
            self,
            "Extraction Error",
            f"Failed to extract {archive_name}: {error_message}",
        )
        self._abort_processing()

    @Slot(
        Path, Path, str, bool, str, str
    )  # temp_dir, final_dir, name, success, msg, output_path (from archive signals)
    def _on_archive_extracted(
        self,
        temp_dir: Path,
        final_dir: Path,
        name: str,
        success: bool,
        msg: str,
        _extracted_output_path: str,
    ):
        """Callback after archive extraction is complete."""
        self.log_message(
            f"Archive extraction for {name} finished. Success: {success}, Message: {msg}",
            level="info",
        )
        if self.logger:
            self.logger.debug(
                "CompressionTab",
                f"_on_archive_extracted for {name}. Success: {success}, Extracted to: {_extracted_output_path}",
            )

        if not success:
            self.log_message(
                f"Archive extraction failed for {name}: {msg}", level="error"
            )
            # QMessageBox might have been shown by _on_archive_extraction_error if that was the path
            if "Extraction Error" not in msg:  # Avoid double pop-up
                QMessageBox.critical(
                    self,
                    "Extraction Failed",
                    f"Failed to extract {name}: {msg}",
                )
            self._abort_processing()
            return

        self.log_message(f"Scanning extracted files in {temp_dir}...", level="info")
        if self.logger:
            self.logger.debug(
                "CompressionTab", f"Scanning extracted files in {temp_dir}"
            )
        self.overall_progress.setFormat("Scanning files...")  # Update progress message

        try:
            scan_signals = self.file_scanner.find_disk_images_async(str(temp_dir))
            scan_signals.finished.connect(
                functools.partial(
                    self._on_extracted_files_scanned, final_dir, name, temp_dir
                )  # Pass temp_dir for cleanup context
            )
            scan_signals.error.connect(self._on_file_scan_error)
        except Exception as e:
            self.log_message(f"Failed to start file scanning: {e}", "error")
            if self.logger:
                self.logger.exception(
                    "CompressionTab",
                    "Error in _on_archive_extracted when starting scan",
                )
            self._abort_processing()

    @Slot(str)
    def _on_file_scan_error(self, error_message: str):
        self.log_message(f"File scanning failed: {error_message}", level="error")
        QMessageBox.critical(
            self, "File Scan Error", f"File scanning failed: {error_message}"
        )
        self._abort_processing()

    @Slot(
        Path, str, Path, list
    )  # final_dir, archive_name, extracted_temp_dir, raw_paths
    def _on_extracted_files_scanned(
        self,
        final_dir: Path,
        archive_name: str,
        extracted_temp_dir: Path,
        raw_paths: List[Path],
    ):
        """Callback after scanning extracted files."""
        self.log_message(
            f"Scan complete. Found {len(raw_paths)} potential files from {archive_name}.",
            level="info",
        )
        if self.logger:
            self.logger.debug(
                "CompressionTab",
                f"_on_extracted_files_scanned for {archive_name}. Found {len(raw_paths)} raw paths.",
            )
            self.logger.debug("CompressionTab", f"Raw paths found: {raw_paths}")

        compatible_files = []
        for p_str in raw_paths:  # raw_paths from FileScanner are strings
            p = Path(p_str)
            if self._is_compatible_disk_image(p):
                compatible_files.append(p)
            else:
                self.log_message(
                    f"Skipping incompatible or non-existent file: {p.name if p else 'Invalid Path'} (Extension: {p.suffix if p else 'N/A'})",
                    level="warning",
                )

        self.log_message(
            f"Found {len(compatible_files)} compatible disk images from {archive_name}.",
            level="info",
        )
        if self.logger:
            self.logger.debug("CompressionTab", f"Compatible files: {compatible_files}")

        if not compatible_files:
            self.log_message(
                f"No compatible disk images found in {archive_name}.", level="warning"
            )
            QMessageBox.warning(
                self,
                "No Compatible Images",
                f"No compatible disk images found in {archive_name}.",
            )
            # self.temp_manager.cleanup_directory(extracted_temp_dir) # Clean specific temp dir
            self._finish_processing_if_needed(
                True
            )  # No tasks, so effectively success for this stage
            return

        for input_path in compatible_files:
            self._queue_chd_task_for_file(input_path, final_dir)

        if self.chd_manager and self.chd_manager.has_pending_tasks():
            self.overall_progress.setFormat("Preparing compression...")
            self._execute_tasks()
        else:
            self.log_message(
                "No CHD tasks to process after queuing from archive.", "info"
            )
            # self.temp_manager.cleanup_directory(extracted_temp_dir) # Clean specific temp dir
            self._finish_processing_if_needed(
                True
            )  # Success if no tasks were ultimately queued

    def _queue_chd_task_for_file(self, input_path: Path, output_dir: Path):
        """Queue a CHD task for a single file with debug logging."""
        if self.logger:
            self.logger.debug(
                "CompressionTab",
                f"_queue_chd_task_for_file called: {input_path} -> {output_dir}",
            )

        if not self.chd_manager:
            self.log_message("CHDManager not available. Cannot queue task.", "error")
            if self.logger:
                self.logger.error(
                    "CompressionTab", "CHDManager is None in _queue_chd_task_for_file."
                )
            return

        if not self._is_compatible_disk_image(input_path):
            self.log_message(
                f"Skipping incompatible file for CHD task: {input_path.name}",
                level="warning",
            )
            return

        if not input_path.exists():
            self.log_message(
                f"Input file for CHD task does not exist: {input_path}", level="error"
            )
            if self.logger:
                self.logger.error(
                    "CompressionTab", f"File {input_path} disappeared before queuing."
                )
            return

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            row = self.add_file_to_table(
                str(input_path)
            )  # add_file_to_table now expects str
            assert row is not None
            self.update_file_status(row, "pending")
            if self.logger:
                self.logger.debug("CompressionTab", f"Added file to table at row {row}")

            output_file = output_dir / f"{input_path.stem}.chd"
            profile_name = self.compression_profile_combo.currentText()
            profile: Optional[ProfileSettings] = COMPRESSION_PROFILES.get(profile_name)

            if not profile:
                self.log_message(
                    f"Profile '{profile_name}' not found. Using default settings.",
                    "warning",
                )

            hunk_size_from_profile: Any = profile.get("hunk_size") if profile else None
            hunk_size: Optional[int] = None  # This is the variable we'll use for CHDMan

            if isinstance(hunk_size_from_profile, int):
                hunk_size = hunk_size_from_profile
            elif isinstance(hunk_size_from_profile, str):
                try:
                    hunk_size_int = int(hunk_size_from_profile)
                    hunk_size = hunk_size_int
                except ValueError:
                    self.log_message(
                        f"Warning: hunk_size '{hunk_size_from_profile}' in profile '{profile_name}' is not a valid integer. Using default.",
                        "warning",
                    )
            elif hunk_size_from_profile is not None:
                # If it's not an int or str but also not None, log a warning.
                self.log_message(
                    f"Warning: hunk_size in profile '{profile_name}' has unexpected type: {type(hunk_size_from_profile)}. Value: {hunk_size_from_profile}. Using default.",
                    "warning",
                )

            if profile:
                profile_media = profile.get(
                    "media", self.media_type_combo.currentText()
                )  # Prioritize profile's media
            else:
                profile_media = self.media_type_combo.currentText()

            if self.logger:
                algs = profile.get("algorithms") if profile else None  # type: ignore[union-attr]
                self.logger.debug(
                    "CompressionTab",
                    f"Profile: {profile_name}, algorithms: {algs}, hunk_size: {hunk_size}, media: {profile_media}",
                )

            task = CHDTask(
                task_type=CHDTaskType.COMPRESS,
                input_file=str(input_path),
                output_file=str(output_file),
                algorithms=str(profile.get("algorithms")) if profile else None,
                hunk_size=hunk_size,
                force=self.overwrite_check.isChecked(),
                media_type=str(profile_media) if profile_media is not None else None,
                user_data={
                    "file_path_str": str(input_path)
                },  # Keep original path string for logging
                row=row,  # Assign row directly to task
            )

            if self.logger:
                self.logger.info(
                    "CompressionTab",
                    f"Created CHDTask: input={task.input_file}, output={task.output_file}, row={task.row}",
                )

            self.chd_manager.add_task(task)
            self.queued_files.add(str(input_path))

            if self.logger:
                pending_count = (
                    len(self.chd_manager.tasks)
                    if hasattr(self.chd_manager, "tasks")
                    else "unknown (no tasks attr)"
                )
                self.logger.info(
                    "CompressionTab",
                    f"Task added to manager. Total pending tasks: {pending_count}",
                )

            self.log_message(f"Queued for compression: {input_path.name} (Row: {row})")

        except Exception as e:
            error_msg = f"Error queuing task for {input_path}: {e}"
            self.log_message(error_msg, level="error")
            if self.logger:
                self.logger.exception("CompressionTab", error_msg)
            if "row" in locals() and row is not None:
                self.update_file_status(row, "Queue Failed")

    def _execute_tasks(self):
        """Execute all queued CHD tasks with comprehensive debug logging."""
        if self.logger:
            self.logger.debug("CompressionTab", "_execute_tasks() called")

        if not self.chd_manager:
            self.log_message("CHDManager not available. Cannot execute tasks.", "error")
            if self.logger:
                self.logger.error(
                    "CompressionTab", "CHDManager is None in _execute_tasks."
                )
            self._finish_processing_if_needed(False)
            return

        try:
            if not self.chd_manager.has_pending_tasks():
                self.log_message("No pending CHD tasks to execute.", "info")
                if self.logger:
                    self.logger.warning(
                        "CompressionTab",
                        "No pending CHD tasks found in _execute_tasks.",
                    )
                self._finish_processing_if_needed(
                    True
                )  # No tasks, success for this stage
                return

            self.log_message(
                f"Executing {len(self.chd_manager.tasks)} CHD tasks...", "info"
            )
            self.overall_progress.setFormat("Compressing files...")
            if self.logger:
                self.logger.info(
                    "CompressionTab", "Starting CHD task processing via CHDManager."
                )

            # This returns a list of (signals, worker) tuples
            workers_with_signals = self.chd_manager.start_processing()

            if not workers_with_signals:
                self.log_message(
                    "CHDManager's start_processing did not return any workers. Check CHDManager logs.",
                    "warning",
                )
                if self.logger:
                    self.logger.warning(
                        "CompressionTab", "start_processing returned no workers."
                    )
                self._finish_processing_if_needed(
                    True
                )  # Assume success if no workers implies no work
                return

            if self.logger:
                self.logger.info(
                    "CompressionTab",
                    f"Retrieved {len(workers_with_signals)} worker(s) with signals from CHDManager.",
                )

            for i, (signals, worker) in enumerate(workers_with_signals):
                # user_data should be on the worker instance, set by CHDManager.initiate_task_and_get_signals
                user_data = getattr(worker, "user_data", {})
                task_row = user_data.get(
                    "row"
                )  # This should come from worker.user_data.row
                task_file_path_str = user_data.get("file_path", "Unknown File")

                if task_row is None:
                    self.log_message(
                        f"Worker {i} missing row info in user_data. Cannot connect signals properly.",
                        "error",
                    )
                    if self.logger:
                        self.logger.error(
                            "CompressionTab",
                            f"Worker {i} (file: {task_file_path_str}) missing 'row' in user_data: {user_data}",
                        )
                    continue  # Skip this worker if row is missing

                if self.logger:
                    self.logger.debug(
                        "CompressionTab",
                        f"Setting up signals for worker {i} (File: {task_file_path_str}, Row: {task_row})",
                    )

                if signals:
                    # Using functools.partial for safer capture of loop variables
                    signals.started.connect(
                        functools.partial(
                            self._on_worker_started, task_file_path_str, task_row
                        )
                    )
                    signals.progress.connect(
                        functools.partial(self._on_worker_progress, task_row)
                    )
                    signals.finished.connect(
                        functools.partial(
                            self._on_worker_finished, task_row, task_file_path_str
                        )
                    )
                    signals.error.connect(
                        functools.partial(
                            self._on_worker_error, task_row, task_file_path_str
                        )
                    )
                    if self.logger:
                        self.logger.info(
                            "CompressionTab",
                            f"Connected signals for worker processing {task_file_path_str} at row {task_row}",
                        )
                else:
                    self.log_message(
                        f"Worker for {task_file_path_str} (Row {task_row}) has no signals object.",
                        "warning",
                    )
                    if self.logger:
                        self.logger.warning(
                            "CompressionTab",
                            f"Worker for {task_file_path_str} (Row {task_row}) returned no signals object from CHDManager.",
                        )
                    self.update_file_status(task_row, "Signal Error")

        except Exception as e:
            self.log_message(f"Critical error during task execution: {e}", "error")
            if self.logger:
                self.logger.error(  # type: ignore[call-arg]
                    "CompressionTab",
                    f"Critical error during task execution: {e}",
                    exc_info=True,
                )
            self._abort_processing()  # Abort on critical failure
            return

    # New dedicated handlers for worker signals
    @Slot(str, int, str)  # original_file_path, row, chdman_command_str
    def _on_worker_started(
        self, original_file_path_str: str, row: int, chdman_command_str: str
    ):
        try:
            safe_file_name = Path(original_file_path_str).name
            self.log_message(
                f"CHDMAN started for: {safe_file_name} (Row: {row}). Cmd: {chdman_command_str}",
                level="debug",
            )
            if self.logger:
                self.logger.debug(
                    "CompressionTab",
                    f"Worker started for {original_file_path_str} (Row {row}). Command: {chdman_command_str}",
                )
            self.update_file_status(row, "Processing")
        except Exception as e:
            self.log_message(f"Error in _on_worker_started for row {row}: {e}", "error")
            if self.logger:
                self.logger.exception(
                    "CompressionTab", f"Exception in _on_worker_started for row {row}"
                )

    @Slot(int, float, str)  # row, progress_percent, message
    def _on_worker_progress(self, row: int, progress_percent: float, message: str):
        try:
            if 0 <= row < self.files_table.rowCount():
                self.update_file_progress(row, int(progress_percent))
                # self.update_file_status(row, message) # This can be too chatty, progress bar shows percentage
                if progress_percent > 0 and progress_percent < 100:
                    self.update_file_status(
                        row,
                        "Processing",  # Changed from dynamic f-string to fixed "Processing"
                    )
            else:
                if self.logger:
                    self.logger.warning(
                        "CompressionTab",
                        f"Invalid row {row} in _on_worker_progress. Message: {message}",
                    )
        except Exception as e:
            self.log_message(f"Error updating progress for row {row}: {e}", "error")
            if self.logger:
                self.logger.exception(
                    "CompressionTab", f"Exception in _on_worker_progress for row {row}"
                )

    @Slot(int, str, bool, str)  # row, original_file_path_str, success, message
    def _on_worker_finished(
        self, row: int, original_file_path_str: str, success: bool, message: str
    ):
        try:
            safe_file_name = Path(original_file_path_str).name
            if 0 <= row < self.files_table.rowCount():
                if success:
                    self.update_file_status(row, "Complete")
                    self.update_file_progress(row, 100)
                    self.log_message(
                        f"Successfully compressed: {safe_file_name}. {message}",
                        level="info",
                    )  # Changed from success
                    self.file_processed.emit(original_file_path_str, True, message)
                else:
                    self.update_file_status(row, "Failed")
                    self.log_message(
                        f"Failed to compress {safe_file_name}: {message}", level="error"
                    )
                    self.file_processed.emit(original_file_path_str, False, message)
            else:
                if self.logger:
                    self.logger.warning(
                        "CompressionTab",
                        f"Invalid row {row} in _on_worker_finished for {safe_file_name}",
                    )

            self._finish_processing_if_needed()
        except Exception as e:
            self.log_message(
                f"Error in _on_worker_finished for row {row}: {e}", "error"
            )
            if self.logger:
                self.logger.exception(
                    "CompressionTab",
                    f"Exception in _on_worker_finished for {original_file_path_str}, row {row}",
                )
            self._finish_processing_if_needed()  # Still try to finish

    @Slot(int, str, str)  # row, original_file_path_str, error_message
    def _on_worker_error(
        self, row: int, original_file_path_str: str, error_message: str
    ):
        try:
            safe_file_name = Path(original_file_path_str).name
            if 0 <= row < self.files_table.rowCount():
                self.update_file_status(row, "Error")
                self.log_message(
                    f"Error compressing {safe_file_name}: {error_message}",
                    level="error",
                )
                self.file_processed.emit(original_file_path_str, False, error_message)
            else:
                if self.logger:
                    self.logger.warning(
                        "CompressionTab",
                        f"Invalid row {row} in _on_worker_error for {safe_file_name}",
                    )

            self._finish_processing_if_needed()
        except Exception as e:
            self.log_message(f"Error in _on_worker_error for row {row}: {e}", "error")
            if self.logger:
                self.logger.exception(
                    "CompressionTab",
                    f"Exception in _on_worker_error for {original_file_path_str}, row {row}",
                )
            self._finish_processing_if_needed()  # Still try to finish

    def _finish_processing_if_needed(
        self, overall_success_hint: Optional[bool] = None
    ) -> None:
        """Check if all tasks are done and update UI accordingly.
        overall_success_hint can be True, False, or None (determine from tasks).
        """
        if not self.chd_manager:
            if self.is_processing:  # If we were processing but manager is gone
                self.is_processing = False
                self.overall_progress.setFormat("Error: CHDManager lost")
                self.log_message(
                    "CHDManager became unavailable during processing.", "error"
                )
                self.compression_finished.emit(False)
                self._update_ui_state()
            return

        try:
            # Check if CHDManager still has active workers or tasks it knows about
            # This relies on CHDManager correctly managing its internal state.
            # has_pending_tasks() might refer to the queue, get_active_tasks_count() for running.
            num_active_chd_tasks = (
                self.chd_manager.get_active_tasks_count()
                if hasattr(self.chd_manager, "get_active_tasks_count")
                else 0
            )

            if self.logger:
                self.logger.debug(
                    "CompressionTab",
                    f"_finish_processing_if_needed: is_processing={self.is_processing}, active_chd_tasks={num_active_chd_tasks}",
                )

            # Only proceed to finish if we were processing and no tasks are active
            if self.is_processing and num_active_chd_tasks == 0:
                self.is_processing = False  # Mark processing as done

                # Determine overall status
                all_successful = True
                has_failures = False
                if overall_success_hint is not None:
                    all_successful = overall_success_hint
                else:  # Check table statuses if no hint
                    for r in range(self.files_table.rowCount()):
                        status_item = self.files_table.item(r, 1)
                        if status_item:
                            status_text = status_item.text()
                            if status_text not in [
                                "Complete",
                                "Skipped",
                                "Cancelled by user",
                            ]:  # Consider "Cancelled" not a failure for overall state
                                all_successful = False
                            if status_text in ["Failed", "Error", "Queue Failed"]:
                                has_failures = True
                                break  # One failure is enough to mark not all successful

                if all_successful and not has_failures:
                    self.overall_progress.setFormat("All tasks complete!")
                    self.overall_progress.setValue(100)
                    self.log_message(
                        "All compression tasks finished successfully.", level="info"
                    )
                    self.compression_finished.emit(True)
                elif has_failures:
                    self.overall_progress.setFormat("Completed with errors.")
                    self.overall_progress.setValue(
                        100
                    )  # Still 100% done, but with errors
                    self.log_message(
                        "Compression tasks finished, but some errors occurred.",
                        level="warning",
                    )
                    self.compression_finished.emit(False)
                else:  # Mixed results or cancelled
                    self.overall_progress.setFormat("Processing finished.")
                    self.overall_progress.setValue(100)
                    self.log_message("Compression processing finished.", level="info")
                    self.compression_finished.emit(
                        True
                    )  # Or False depending on definition of success

                if self.logger:
                    self.logger.info(
                        "CompressionTab",
                        "All tasks seem complete. Cleaning up temporary directories.",
                    )
                try:
                    self.temp_manager.cleanup_all()
                    self.log_message("Temporary directories cleaned up.", "debug")
                except Exception as e:
                    self.log_message(
                        f"Error cleaning up temporary directories: {e}", "error"
                    )
                    if self.logger:
                        self.logger.exception(
                            "CompressionTab", "Temp directory cleanup failed."
                        )

                self._update_ui_state()  # Update UI after processing flag changes
        except Exception as e:
            self.log_message(f"Error in _finish_processing_if_needed: {e}", "error")
            if self.logger:
                self.logger.exception(
                    "CompressionTab", "Exception in _finish_processing_if_needed"
                )
            # Fallback to ensure UI is responsive
            if self.is_processing:
                self.is_processing = False
                self.compression_finished.emit(False)  # Emit failure due to error
                self._update_ui_state()

    def _update_ui_state(self) -> None:
        """Update the UI elements based on the current processing state."""
        # Determine if CHD manager might be active even if self.is_processing is false
        # This can happen if app was closed and reopened, or after an error.
        # For simplicity, we mostly rely on self.is_processing.
        # A more robust check could involve querying CHDManager directly if it has a state.
        currently_busy = self.is_processing
        if self.chd_manager and hasattr(self.chd_manager, "get_active_tasks_count"):
            if self.chd_manager.get_active_tasks_count() > 0:
                currently_busy = True  # If CHDMan has active tasks, we are busy

        self.start_compression_btn.setEnabled(not currently_busy)
        self.stop_compression_btn.setEnabled(currently_busy)
        self.browse_input_btn.setEnabled(not currently_busy)
        self.browse_output_btn.setEnabled(
            not currently_busy and not self.use_same_dir_check.isChecked()
        )
        self.input_path_edit.setEnabled(not currently_busy)
        self.output_dir_edit.setEnabled(
            not currently_busy and not self.use_same_dir_check.isChecked()
        )
        self.use_same_dir_check.setEnabled(not currently_busy)
        self.overwrite_check.setEnabled(not currently_busy)
        self.compression_profile_combo.setEnabled(not currently_busy)
        self.media_type_combo.setEnabled(
            not currently_busy
        )  # This might be redundant if profile drives media type

        if currently_busy:
            if (
                not self.overall_progress.text().startswith("Compressing")
                and not self.overall_progress.text().startswith("Extracting")
                and not self.overall_progress.text().startswith("Scanning")
            ):
                self.overall_progress.setFormat("Processing...")
        else:  # Not busy
            has_input = bool(self.input_path_edit.text().strip())
            has_output = (
                bool(self.output_dir_edit.text().strip())
                and not self.use_same_dir_check.isChecked()
            ) or (self.use_same_dir_check.isChecked() and has_input)
            self.start_compression_btn.setEnabled(has_input and has_output)

            # Reset progress bar if not already explicitly set to complete/error
            current_format = self.overall_progress.format()
            if (
                "complete" not in current_format.lower()
                and "error" not in current_format.lower()
                and "cancelled" not in current_format.lower()
            ):
                self.overall_progress.setFormat("Ready - %p%")
                if (
                    self.overall_progress.value() == 100
                ):  # If it was 100 but not "Complete"
                    self.overall_progress.setValue(0)  # Reset if ready

    def add_file_to_table(
        self, file_path_str: str
    ) -> Optional[int]:  # Ensure return type is Optional[int]
        """Adds a file to the table and returns the row index."""
        try:
            # Normalize path for display and internal tracking if needed, but use string for display
            # normalized_path_str = str(Path(file_path_str).resolve()) # Resolve can fail on non-existent paths
            display_name = Path(file_path_str).name

            # Check for duplicates based on the original file_path_str (more robust for temp files)
            # This might not be necessary if queue_files set handles uniqueness
            # For now, assume new row per call as tasks are distinct.

            row_position = self.files_table.rowCount()
            self.files_table.insertRow(row_position)

            file_name_item = QTableWidgetItem(display_name)
            file_name_item.setToolTip(file_path_str)  # Show full path on hover
            self.files_table.setItem(row_position, 0, file_name_item)

            status_item = QTableWidgetItem("Pending")
            self.files_table.setItem(row_position, 1, status_item)

            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setTextVisible(True)
            progress_bar.setFormat("%p%")
            self.files_table.setCellWidget(row_position, 2, progress_bar)

            return int(row_position)
        except Exception as e:
            self.log_message(
                f"Error adding file {file_path_str} to table: {e}", "error"
            )
            if self.logger:
                self.logger.error(
                    "CompressionTab",
                    f"Error adding file {file_path_str} to table: {e}",
                )
            return None  # Ensure None is returned on error

    def update_file_status(self, row: int, status: str):
        """Updates the status of a file in the table."""
        if not (0 <= row < self.files_table.rowCount()):
            self.log_message(
                f"Invalid row index {row} for update_file_status ('{status}'). Table rows: {self.files_table.rowCount()}",
                "warning",
            )
            if self.logger:
                self.logger.warning(
                    "CompressionTab",
                    f"Attempted to update status for invalid row: {row}",
                )
            return
        try:
            item = self.files_table.item(row, 1)
            if item:
                item.setText(status)
            else:  # Create item if it doesn't exist (should not happen with current add_file_to_table)
                self.files_table.setItem(row, 1, QTableWidgetItem(status))
        except Exception as e:
            self.log_message(
                f"Error updating status for row {row} to '{status}': {e}", "error"
            )
            if self.logger:
                self.logger.exception(
                    "CompressionTab", f"Failed to update_file_status for row {row}"
                )

    def update_file_progress(self, row: int, progress: int) -> None:  # progress is int
        """Updates the progress of a file in the table."""
        if not (0 <= row < self.files_table.rowCount()):
            self.log_message(
                f"Invalid row index {row} for update_file_progress ({progress}%). Table rows: {self.files_table.rowCount()}",
                "warning",
            )
            if self.logger:
                self.logger.warning(
                    "CompressionTab",
                    f"Attempted to update progress for invalid row: {row}",
                )
            return
        try:
            progress_bar = self.files_table.cellWidget(row, 2)
            if isinstance(progress_bar, QProgressBar):
                progress_bar.setValue(progress)
            else:
                self.log_message(
                    f"Progress bar not found or invalid type for row {row}", "warning"
                )
                if self.logger:
                    self.logger.warning(
                        "CompressionTab", f"No QProgressBar at row {row}, col 2."
                    )
        except Exception as e:
            self.log_message(
                f"Error updating progress for row {row} to {progress}%: {e}", "error"
            )
            if self.logger:
                self.logger.exception(
                    "CompressionTab", f"Failed to update_file_progress for row {row}"
                )

    def _build_ui(self) -> None:
        """Build the user interface using unified layout approach."""
        # Create main layout with standardized spacing
        layout = StandardFormLayout.create_main_layout(
            self,
            title="Disk Image Compression",
            description="Compress disk images to CHD format using CHDMAN. "
            "Supports various disk image formats and archives.",
        )

        # Build UI sections using unified approach
        layout.addWidget(self._create_input_section())
        layout.addWidget(self._create_output_section())
        layout.addWidget(self._create_options_section())
        layout.addWidget(
            self._create_file_table_section(), 1
        )  # Give table stretch factor
        layout.addWidget(self._create_log_section())
        layout.addWidget(self._create_progress_section())

        # Create unified button bar
        action_buttons = self._create_action_buttons_list()
        StandardFormLayout.create_button_bar(action_buttons, layout)

    def _create_input_section(self) -> QGroupBox:
        """Create the input section using unified layout approach."""
        input_group, input_layout = StandardFormLayout.create_form_group("Input")

        # Create input path field with browse button
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText(
            "Select a disk image file or archive (.cue, .iso, .bin, .img, .chd, .gdi, .mdf, .nrg, etc.)"
        )

        self.browse_input_btn = QPushButton("Browse...")
        self.browse_input_btn.setIcon(QIcon.fromTheme("document-open"))
        self.browse_input_btn.setToolTip("Select the file or archive to compress.")

        # Create horizontal layout for path + browse button
        input_row_layout = QHBoxLayout()
        input_row_layout.addWidget(self.input_path_edit)
        input_row_layout.addWidget(self.browse_input_btn)
        input_row_layout.setSpacing(8)

        # Create container widget for the layout
        input_widget = QWidget()
        input_widget.setLayout(input_row_layout)

        StandardFormLayout.add_form_field(
            input_layout, "Input File/Archive:", input_widget
        )
        return input_group

    def _create_output_section(self) -> QGroupBox:
        """Create the output section using unified layout approach."""
        output_group, output_layout = StandardFormLayout.create_form_group("Output")

        # Create output directory field with browse button
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText(
            "Select output directory (if not same as input)"
        )

        self.browse_output_btn = QPushButton("Browse...")
        self.browse_output_btn.setIcon(QIcon.fromTheme("folder-open"))
        self.browse_output_btn.setToolTip(
            "Select the directory to save compressed CHD files."
        )

        # Create horizontal layout for path + browse button
        output_row_layout = QHBoxLayout()
        output_row_layout.addWidget(self.output_dir_edit)
        output_row_layout.addWidget(self.browse_output_btn)
        output_row_layout.setSpacing(8)

        # Create container widget for the layout
        output_widget = QWidget()
        output_widget.setLayout(output_row_layout)

        StandardFormLayout.add_form_field(
            output_layout, "Output Directory:", output_widget
        )

        # Add checkboxes using unified approach
        self.use_same_dir_check = QCheckBox("Use same directory as input for output")
        self.use_same_dir_check.setChecked(True)
        StandardFormLayout.add_form_field(output_layout, "", self.use_same_dir_check)

        self.overwrite_check = QCheckBox("Overwrite existing CHD files if they exist")
        self.overwrite_check.setToolTip(
            "If checked, existing .chd files with the same name will be overwritten without prompting."
        )
        StandardFormLayout.add_form_field(output_layout, "", self.overwrite_check)

        return output_group

    def _create_options_section(self) -> QGroupBox:
        """Create the options section of the UI."""
        options_group = QGroupBox("Compression Options")
        options_layout = (
            QHBoxLayout()
        )  # Changed to QHBoxLayout for better horizontal arrangement

        media_type_label = QLabel("Media Type:")
        self.media_type_combo = QComboBox()
        # Populate from COMPRESSION_PROFILES to ensure consistency
        media_types_from_profiles = sorted(
            {
                str(p.get("media", ""))  # Ensure string conversion for sortable items
                for p in COMPRESSION_PROFILES.values()
                if p.get("media")
            }
        )
        self.media_type_combo.addItems(["Auto Detect"] + media_types_from_profiles)
        self.media_type_combo.setToolTip(
            "Select media type or auto-detect. Profile choice may override this."
        )

        profile_label = QLabel("Profile:")
        self.compression_profile_combo = QComboBox()
        self.compression_profile_combo.addItems(list(COMPRESSION_PROFILES.keys()))
        self.compression_profile_combo.setToolTip(
            "Choose a compression profile (overrides manual algorithm/hunk choices)."
        )
        # Default to "CD - Default" or first available
        default_profile = "CD - Default"
        if default_profile in COMPRESSION_PROFILES:
            self.compression_profile_combo.setCurrentText(default_profile)

        options_layout.addWidget(media_type_label)
        options_layout.addWidget(self.media_type_combo, 1)  # Give stretch
        options_layout.addSpacing(20)
        options_layout.addWidget(profile_label)
        options_layout.addWidget(self.compression_profile_combo, 2)  # Give more stretch

        options_group.setLayout(options_layout)
        return options_group

    def _create_file_table_section(self) -> QGroupBox:
        """Create the file table section of the UI."""
        table_group = QGroupBox("Files to Process")
        table_layout = QVBoxLayout()

        self.files_table = QTableWidget(0, FILE_TABLE_COLUMNS)
        self.files_table.setHorizontalHeaderLabels(["File Name", "Status", "Progress"])
        self.files_table.horizontalHeader().setStretchLastSection(
            False
        )  # Progress column not always last
        self.files_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,  # CHANGED FROM QGroupBox.Stretch
        )  # File name gets most space
        self.files_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,  # CHANGED FROM QGroupBox.ResizeToContents
        )  # Status
        self.files_table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,  # CHANGED FROM QGroupBox.Stretch
        )  # Progress bar also gets space
        self.files_table.setMinimumHeight(150)  # Ensure table is visible
        self.files_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        table_layout.addWidget(self.files_table)
        table_group.setLayout(table_layout)
        return table_group

    def _create_log_section(self) -> QGroupBox:
        """Create the log section of the UI."""
        log_group = QGroupBox("Log Output")
        log_layout = QVBoxLayout()

        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.log_panel.setMinimumHeight(100)  # Adjust as needed
        self.log_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        log_layout.addWidget(self.log_panel)

        log_buttons_layout = QHBoxLayout()
        self.export_log_btn = QPushButton("Export Log")
        self.export_log_btn.setIcon(QIcon.fromTheme("document-save"))
        self.copy_log_btn = QPushButton("Copy Log")
        self.copy_log_btn.setIcon(QIcon.fromTheme("edit-copy"))
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.setIcon(QIcon.fromTheme("edit-clear"))

        log_buttons_layout.addStretch()
        log_buttons_layout.addWidget(self.export_log_btn)
        log_buttons_layout.addWidget(self.copy_log_btn)
        log_buttons_layout.addWidget(self.clear_log_btn)
        log_layout.addLayout(log_buttons_layout)

        log_group.setLayout(log_layout)
        return log_group

    def _create_progress_section(self) -> QGroupBox:
        """Create the progress section of the UI."""
        progress_group = QGroupBox("Overall Progress")
        progress_layout = QVBoxLayout()

        self.overall_progress = QProgressBar()
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(True)
        self.overall_progress.setFormat("Ready - %p%")

        progress_layout.addWidget(self.overall_progress)
        progress_group.setLayout(progress_layout)
        return progress_group

    def _create_action_buttons(self) -> QHBoxLayout:
        """Create the action buttons section."""
        actions_layout = QHBoxLayout()

        self.start_compression_btn = QPushButton("Start Compression")
        self.start_compression_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.start_compression_btn.setDefault(True)  # Make it default for Enter key

        self.stop_compression_btn = QPushButton("Cancel Operation")
        self.stop_compression_btn.setIcon(QIcon.fromTheme("process-stop"))
        self.stop_compression_btn.setEnabled(False)  # Initially disabled

        self.cleanup_btn = QPushButton("Cleanup Temp Dirs")
        self.cleanup_btn.setIcon(QIcon.fromTheme("user-trash"))  # Example icon
        self.cleanup_btn.setToolTip(
            "Manually remove any leftover temporary directories created by RetroClamp."
        )

        actions_layout.addStretch()
        actions_layout.addWidget(self.start_compression_btn)
        actions_layout.addWidget(self.stop_compression_btn)
        actions_layout.addSpacing(20)
        actions_layout.addWidget(self.cleanup_btn)
        actions_layout.addStretch()

        return actions_layout

    def _create_action_buttons_list(self) -> List[QPushButton]:
        """Create action buttons as a list for unified button bar."""
        self.start_compression_btn = QPushButton("Start Compression")
        self.start_compression_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.start_compression_btn.setDefault(True)  # Make it default for Enter key

        self.stop_compression_btn = QPushButton("Cancel Operation")
        self.stop_compression_btn.setIcon(QIcon.fromTheme("process-stop"))
        self.stop_compression_btn.setEnabled(False)  # Initially disabled

        self.cleanup_btn = QPushButton("Cleanup Temp Dirs")
        self.cleanup_btn.setIcon(QIcon.fromTheme("user-trash"))
        self.cleanup_btn.setToolTip(
            "Manually remove any leftover temporary directories created by RetroClamp."
        )

        return [self.cleanup_btn, self.stop_compression_btn, self.start_compression_btn]

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        self.browse_input_btn.clicked.connect(self.browse_input)
        self.browse_output_btn.clicked.connect(self.browse_output)
        self.use_same_dir_check.toggled.connect(self._on_same_dir_toggled)

        self.compression_profile_combo.currentTextChanged.connect(
            self._on_profile_changed
        )  # Auto-update media type
        self.media_type_combo.currentTextChanged.connect(
            self._on_media_type_manually_changed
        )

        self.input_path_edit.textChanged.connect(self._on_input_path_changed)

        self.start_compression_btn.clicked.connect(self.start_compression)
        self.stop_compression_btn.clicked.connect(self.cancel_compression)

        self.cleanup_btn.clicked.connect(self._manual_cleanup_temp)

        self.export_log_btn.clicked.connect(self.export_log)
        self.copy_log_btn.clicked.connect(self.copy_log)
        self.clear_log_btn.clicked.connect(self.clear_log)

        # Connect custom signals for external use if needed
        # self.compression_started.connect(...)
        # self.compression_finished.connect(...)
        # self.file_processed.connect(...)

    def _manual_cleanup_temp(self):
        self.log_message("Manual temporary directory cleanup requested.", "info")
        try:
            self.temp_manager.cleanup_all()
            self.log_message("Temporary directories successfully cleaned up.", "info")
            QMessageBox.information(
                self, "Cleanup", "Temporary directories cleaned up."
            )
        except Exception as e:
            self.log_message(f"Error during manual cleanup: {e}", "error")
            if self.logger:
                self.logger.exception("CompressionTab", "Manual temp cleanup failed")
            QMessageBox.warning(
                self,
                "Cleanup Failed",
                f"Could not clean up all temporary directories: {e}",
            )

    def _on_input_path_changed(self, text: str) -> None:
        """Handle input path changes."""
        self._update_ui_state()  # Enable/disable start button
        if text and Path(text).exists():
            if self.use_same_dir_check.isChecked():
                self.output_dir_edit.setText(str(Path(text).parent))

            # Auto-detect media type if "Auto Detect" is selected in media_type_combo
            if self.media_type_combo.currentText() == "Auto Detect":
                self._auto_detect_and_set_profile(text)
        else:  # If path is invalid or empty
            if self.media_type_combo.currentText() == "Auto Detect":
                # Potentially reset profile or media type if input becomes invalid
                pass

    def _on_same_dir_toggled(self, checked: bool) -> None:
        """Handle same directory checkbox toggle."""
        self.output_dir_edit.setEnabled(not checked)
        self.browse_output_btn.setEnabled(not checked)
        if checked:
            input_path_str = self.input_path_edit.text()
            if (
                input_path_str and Path(input_path_str).exists()
            ):  # Check exists before getting parent
                self.output_dir_edit.setText(str(Path(input_path_str).parent))
            else:
                self.output_dir_edit.clear()  # Clear if input is invalid
        self._update_ui_state()

    def _on_profile_changed(self, profile_name: str) -> None:
        """When compression profile changes, update the media type combo if a profile is selected."""
        if profile_name in COMPRESSION_PROFILES:
            profile_details = COMPRESSION_PROFILES[profile_name]
            profile_media: Optional[str] = profile_details.get("media")

            if profile_media:
                # Temporarily disconnect media_type_combo's signal to prevent feedback loop
                try:
                    self.media_type_combo.currentTextChanged.disconnect(
                        self._on_media_type_manually_changed
                    )
                except RuntimeError:  # Thrown if not connected
                    pass

                assert profile_media is not None, (
                    "Type checker hint: profile_media is str here"
                )
                current_media_index = self.media_type_combo.findText(profile_media)
                if current_media_index != -1:
                    self.media_type_combo.setCurrentIndex(current_media_index)
                else:  # If profile_media is not in combo, select "Auto Detect" or a fallback
                    auto_idx = self.media_type_combo.findText("Auto Detect")
                    if auto_idx != -1:
                        self.media_type_combo.setCurrentIndex(auto_idx)

                # Reconnect
                self.media_type_combo.currentTextChanged.connect(
                    self._on_media_type_manually_changed
                )
        self._update_ui_state()

    def _on_media_type_manually_changed(self, media_type: str) -> None:
        """Handle manual media type combo box changes. This might adjust available profiles."""
        # This logic is more complex: if user picks "CD", profiles list should filter.
        # For now, mainly let profile drive media type. If user changes media type,
        # it might not perfectly align with selected profile's intended media.
        # A simple approach: if media type is changed, and current profile doesn't match,
        # perhaps clear profile or select a matching one.

        # Example: if user selects "CD" and profile is "DVD - Default", warn or auto-change profile.
        # For now, we assume profile is king or user knows what they're doing.
        # The _queue_chd_task_for_file uses profile's media first.
        self.log_message(
            f"Media type manually changed to: {media_type}. Review profile selection if needed.",
            "debug",
        )
        self._update_ui_state()

    def _auto_detect_and_set_profile(self, file_path_str: str) -> None:
        """Auto-detect media type and suggest a default profile."""
        try:
            path = Path(file_path_str)
            if not path.is_file():  # Only detect for files
                return

            detected_media = "unknown"
            extension = path.suffix.lower()

            # Basic extension-based detection
            if extension in [
                ".iso",
                ".bin",
                ".cue",
                ".img",
                ".wav",
                ".flac",
            ]:  # Common CD image/track types
                size_mb = path.stat().st_size / (1024 * 1024)
                detected_media = (
                    "CD" if size_mb < 900 else "DVD"
                )  # Rough guess: CD < 900MB
            elif extension in [".chd"]:  # Already compressed, but for info
                # For CHD, need chdman info to know original type. Default to CD for now.
                detected_media = "CD"  # Placeholder
            elif extension in [
                ".vhd",
                ".vmdk",
                ".raw",
                ".hdd",
                ".hdimage",
            ]:
                detected_media = "Hard Disk"

            if detected_media != "unknown":
                self.log_message(
                    f"Auto-detected media type as: {detected_media} for {path.name}",
                    "debug",
                )
                # Find a default profile for this media type
                # Example: "CD - Default", "DVD - Default", "Hard Disk - Default"
                target_profile_name = f"{detected_media} - Default"

                # Temporarily disconnect profile's signal to prevent feedback loop
                try:
                    self.compression_profile_combo.currentTextChanged.disconnect(
                        self._on_profile_changed
                    )
                except RuntimeError:
                    pass

                if target_profile_name in COMPRESSION_PROFILES:
                    self.compression_profile_combo.setCurrentText(target_profile_name)
                    # The _on_profile_changed will then set the media_type_combo
                    self._on_profile_changed(target_profile_name)
                else:  # Fallback if specific default profile not found
                    # Find *any* profile matching the media type
                    found_matching_profile = False
                    for pname, pdetails in COMPRESSION_PROFILES.items():
                        if pdetails.get("media") == detected_media:
                            self.compression_profile_combo.setCurrentText(pname)
                            self._on_profile_changed(pname)
                            found_matching_profile = True
                            break
                    if not found_matching_profile and self.logger:
                        self.logger.warning(
                            "CompressionTab",
                            f"No default or matching profile found for auto-detected media: {detected_media}",
                        )

                # Reconnect profile signal
                self.compression_profile_combo.currentTextChanged.connect(
                    self._on_profile_changed
                )

            else:
                if self.logger:
                    self.logger.debug(
                        "CompressionTab",
                        f"Could not auto-detect media type for {path.name}",
                    )

        except Exception as e:
            self.log_message(
                f"Error during media type auto-detection for {file_path_str}: {e}",
                level="warning",
            )
            if self.logger:
                self.logger.exception("CompressionTab", "Auto-detection error")

    def browse_input(self) -> None:
        """Open file dialog to select input file or archive."""
        # More comprehensive filter list
        filters = [
            "Supported Images & Archives (*.cue *.iso *.bin *.img *.chd *.gdi *.mdf *.nrg *.zip *.7z *.rar *.gz *.tar)",
            "Disk Images (*.cue *.iso *.bin *.img *.chd *.gdi *.mdf *.nrg)",
            "Archives (*.zip *.7z *.rar *.gz *.tar)",
            "All Files (*)",
        ]
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Input File or Archive", "", ";;".join(filters)
        )
        if file_path:
            self.input_path_edit.setText(file_path)
            # Trigger auto-detection if relevant
            self._on_input_path_changed(file_path)

    def browse_output(self) -> None:
        """Open directory dialog to select output directory."""
        # Suggest starting directory based on input if possible
        start_dir = ""
        input_path_str = self.input_path_edit.text()
        if input_path_str and Path(input_path_str).exists():
            start_dir = str(Path(input_path_str).parent)
        elif self.output_dir_edit.text():  # Use current output dir if set
            start_dir = self.output_dir_edit.text()

        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", start_dir
        )
        if directory:
            self.output_dir_edit.setText(str(Path(directory)))
            self._update_ui_state()

    def cancel_compression(self) -> None:
        """Cancel the current compression operation."""
        self.log_message(
            "User requested cancellation of compression operations...", level="warning"
        )
        if self.logger:
            self.logger.info("CompressionTab", "cancel_compression() called by user.")

        if not self.is_processing:
            self.log_message("No active compression to cancel.", "info")
            return

        # Terminate CHDMAN processes
        if self.chd_manager:
            try:
                self.chd_manager.terminate_all_chdman_processes()
                self.log_message("CHDMAN processes instructed to terminate.", "info")
            except Exception as e:
                self.log_message(f"Error terminating CHDMAN processes: {e}", "error")
                if self.logger:
                    self.logger.exception("CompressionTab", "CHDMAN termination error")

        # Cancel archive extraction if in progress
        if self.archive_manager and hasattr(
            self.archive_manager, "cancel_current_operation"
        ):
            try:
                self.archive_manager.cancel_current_operation()
                self.log_message("Archive extraction instructed to cancel.", "info")
            except Exception as e:
                self.log_message(f"Error cancelling archive extraction: {e}", "error")
                if self.logger:
                    self.logger.exception("CompressionTab", "Archive cancel error")

        # Cancel file scanning if in progress
        if self.file_scanner and hasattr(
            self.file_scanner, "cancel_current_scan"
        ):  # Assuming scanner has this
            try:
                # self.file_scanner.cancel_current_scan() # Implement this in FileScanner if needed
                self.log_message(
                    "File scanning instructed to cancel (if scanner supports it).",
                    "info",
                )
            except Exception as e:
                self.log_message(f"Error cancelling file scan: {e}", "error")

        self.is_processing = False  # Set this early
        self.overall_progress.setFormat("Cancelled by user")
        self.overall_progress.setValue(
            100
        )  # Or 0, depending on preference for cancelled state

        # Update status of files in table that were being processed or queued
        for row in range(self.files_table.rowCount()):
            status_item = self.files_table.item(row, 1)
            if status_item and status_item.text().lower() in [
                "pending",
                "queued",
                "processing",
                "extracting",
                "scanning",
            ]:
                self.update_file_status(row, "Cancelled by user")

        self.compression_finished.emit(False)  # Indicate cancellation/failure
        self._update_ui_state()
        self.log_message("Compression operation cancelled.", "info")

        # Cleanup temp dirs as cancellation might leave them
        try:
            self.temp_manager.cleanup_all()
            self.log_message(
                "Temporary directories cleaned up after cancellation.", "debug"
            )
        except Exception as e:
            self.log_message(
                f"Error cleaning temp dirs post-cancellation: {e}", "warning"
            )

    def closeEvent(self, event) -> None:
        """Handle widget close event (called by main window)."""
        if self.logger:
            self.logger.info("CompressionTab", "closeEvent received.")
        try:
            if self.is_processing:
                reply = QMessageBox.question(
                    self,
                    "Confirm Exit",
                    "Compression is in progress. Are you sure you want to exit? This will cancel ongoing tasks.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.log_message(
                        "Closing while processing: attempting to cancel operations.",
                        "warning",
                    )
                    self.cancel_compression()  # Attempt graceful cancel
                else:
                    event.ignore()
                    return

            if self.ui_timer.isActive():
                self.ui_timer.stop()

            # Temp manager cleanup is typically handled by MainWindow or TempManager itself on app exit,
            # but can be called here if this tab has exclusive temp dirs.
            # self.temp_manager.cleanup_all()
            # self.log_message("CompressionTab closed, temp dirs cleaned (if any were exclusive).", "debug")

            event.accept()
        except Exception as e:
            self.log_message(
                f"Error during CompressionTab closeEvent: {e}", level="error"
            )
            if self.logger:
                self.logger.exception("CompressionTab", "Exception in closeEvent")
            event.accept()  # Accept anyway to prevent hang

    def _abort_processing(self):
        """Forcefully stops current processing, cleans up, and resets UI. Used for critical errors."""
        self.log_message(
            "Aborting all processing due to critical error.", level="error"
        )
        if self.logger:
            self.logger.error("CompressionTab", "Processing aborted.")

        # Similar to cancel_compression but more forceful if needed, and assumes error state
        if self.chd_manager:
            self.chd_manager.terminate_all_chdman_processes()
        if self.archive_manager:
            self.archive_manager.cancel_current_operation()
        # Add file_scanner cancel if available

        self.is_processing = False  # Set this early
        self.overall_progress.setFormat("Aborted due to error")
        self.overall_progress.setValue(0)  # Or 100 with error state

        for row in range(self.files_table.rowCount()):
            status_item = self.files_table.item(row, 1)
            if status_item and status_item.text().lower() not in [
                "complete",
                "failed",
                "error",
                "cancelled by user",
            ]:
                self.update_file_status(row, "Aborted")

        self.compression_finished.emit(False)  # Signal failure
        self._update_ui_state()

    def _is_compatible_disk_image(self, file_path: Path) -> bool:
        """Check if file is a compatible disk image by extension."""
        if not file_path or not isinstance(file_path, Path):
            return False
        # Ensure file exists before checking, as temp files might vanish
        if not file_path.is_file():  # Check if it's a file and exists
            if self.logger:
                self.logger.warning(
                    "CompressionTab",
                    f"_is_compatible_disk_image: path is not a file or does not exist: {file_path}",
                )
            return False

        compatible_extensions = {
            ".iso",
            ".bin",
            ".cue",
            ".img",
            ".cdr",
            ".gdi",
            ".mdf",
            ".nrg",
            ".wav",
            ".flac",
        }  # Added audio for CD-DA
        return file_path.suffix.lower() in compatible_extensions
