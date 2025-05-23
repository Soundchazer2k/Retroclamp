#!/usr/bin/env python3

"""
Batch Processing Tab for RetroClamp.

This module provides the batch processing interface for RetroClamp,
allowing users to process multiple files at once.
"""

import logging
import os
import tempfile
import time
import traceback

# Import archive handling libraries
import zipfile
from datetime import datetime
from typing import Any, List

import py7zr
import rarfile
from PySide6.QtCore import QMutex, Qt, QThread, QTimer, QWaitCondition, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.archive import ArchiveManager

# Import core components
from core.chdman import CHDCompressionType, CHDMan, CHDTask, CHDTaskType
from core.checkpoint_manager import CheckpointManager
from core.file_scanner import FileScanner

# Import UI components and utilities
from modules.ui_functions import load_svg_icon
from utils import show_error, show_info, show_warning

# Constants for settings
SETTINGS_ORG = "RetroClamp"
SETTINGS_APP = "RetroClamp"
SETTINGS_BATCH = "BatchProcessing"


class BatchWorker(QThread):
    """Worker thread for batch processing tasks.

    This class handles the actual file processing in a background thread,
    including compression and extraction operations using CHDMAN.
    """

    # Signals for communication with the main thread
    progress = Signal(int, str)  # progress_percent, status
    error = Signal(str, str)  # error_message, file_path
    finished = Signal()  # Emitted when processing is complete
    file_completed = Signal(str, str)  # file_path, status_message

    def __init__(
        self,
        file_path: str,
        output_dir: str,
        operation: str,
        compression: CHDCompressionType = CHDCompressionType.ZLIB,
        verify: bool = False,
        parent=None,
    ):
        """Initialize the BatchWorker.

        Args:
            file_path: Path to the file to process
            output_dir: Directory to save the output file
            operation: Operation to perform ('compress' or 'extract')
            compression: Compression algorithm to use (default: 'zlib')
            verify: Whether to verify the output file (default: False)
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.file_path = file_path
        self.output_dir = output_dir
        self.operation = operation.lower()
        self.compression = (
            compression.value
            if isinstance(compression, CHDCompressionType)
            else compression
        )
        self.verify = verify
        self._is_running = True
        self._is_paused = False
        self._pause_cond = QWaitCondition()
        self._mutex = QMutex()

    def run(self):
        """Main processing method that runs in a separate thread."""
        # Log all key paths and operation info to error.log (for debugging)
        try:
            with open("error.log", "a", encoding="utf-8") as logf:
                logf.write(f"\n[BatchWorker] Starting run at: {datetime.now()}\n")
                logf.write(f"  Operation: {self.operation}\n")
                logf.write(f"  Input file: {self.file_path}\n")
                logf.write(f"  Output dir: {self.output_dir}\n")
                logf.write(f"  Compression: {self.compression}\n")
                logf.write(f"  Verify: {self.verify}\n")
            logging.info(
                f"[BatchWorker] Launching: {self.operation} -i "
                f"{self.file_path} -o {self.output_dir}"
            )
        except Exception as logex:
            # If logging fails, just print
            print(f"[BatchWorker] Failed to log start: {logex}")
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)

            # Determine output path
            input_filename = os.path.basename(self.file_path)
            base_name = os.path.splitext(input_filename)[0]

            if self.operation == "compress":
                output_path = os.path.join(self.output_dir, f"{base_name}.chd")
                self._compress_file(self.file_path, output_path)
            elif self.operation == "extract":
                if self.file_path.lower().endswith(".chd"):
                    output_path = os.path.join(self.output_dir, f"{base_name}.bin")
                    self._extract_file(self.file_path, output_path)
                else:
                    raise ValueError("Only CHD files can be extracted")
            else:
                raise ValueError(f"Unknown operation: {self.operation}")

            # Verify the output file if requested
            if self.verify and os.path.exists(output_path):
                self.progress.emit(95, "Verifying output file...")
                # TODO: Implement verification logic
                # Simulate verification delay (non-blocking)
                # TODO: Implement actual verification logic here using
                # signals/slots or async
                pass

            self.file_completed.emit(self.file_path, "Completed successfully")
            self.progress.emit(100, f"Completed {self.operation}ion")

        except Exception as e:
            tb = traceback.format_exc()
            # Log to error.log
            with open("error.log", "a", encoding="utf-8") as logf:
                logf.write(f"\n[BatchWorker] Uncaught exception at: {datetime.now()}\n")
                logf.write(tb)
            error_msg = f"{str(e)}\n{tb}"
            self.error.emit(error_msg, self.file_path)
            self.progress.emit(0, f"Error: {error_msg}")
        finally:
            self.finished.emit()

    def _compress_file(self, input_path: str, output_path: str):
        """Compress a file to CHD format."""
        logging.info(f"BatchWorker compressing {input_path} to {output_path}")
        self.progress.emit(5, "Starting compression...")

        # Check if output file already exists
        if os.path.exists(output_path):
            raise FileExistsError(f"Output file already exists: {output_path}")

        # Create a CHDMan instance
        chdman = CHDMan()

        # Perform the compression
        # Use the correct method for compression (e.g., create_cd, create_dvd, etc.)
        chdman.create_cd(
            input_file=input_path,
            output_file=output_path,
            compression=self.compression,
        ).signals.progress_updated.connect(self._progress_callback)

    def _extract_file(self, input_path: str, output_path: str):
        """Extract a CHD file."""
        logging.info(f"BatchWorker extracting {input_path} to {output_path}")
        self.progress.emit(5, "Starting extraction...")

        # Check if output file already exists
        if os.path.exists(output_path):
            raise FileExistsError(f"Output file already exists: {output_path}")

        # Create a CHDMan instance
        chdman = CHDMan()

        # Perform the extraction
        # Use the correct method for extraction (e.g., extract_cd, extract_hd, etc.)
        chdman.extract_cd(
            input_file=input_path,
            output_file=output_path,
        ).signals.progress_updated.connect(self._progress_callback)

    def _progress_callback(self, progress: float, status: str):
        self.progress.emit(5 + int(progress * 0.9), status)

    def pause(self):
        """Pause the processing."""
        logging.info(f"BatchWorker for {self.file_path} pausing.")
        self._mutex.lock()
        self._is_paused = True
        self.progress.emit(0, "Paused")

    def resume(self):
        """Resume the processing."""
        logging.info(f"BatchWorker for {self.file_path} resuming.")
        self._is_paused = False
        self._pause_cond.wakeAll()
        self._mutex.unlock()
        self.progress.emit(0, "Resumed")

    def stop(self):
        """Stop the processing."""
        logging.info(f"BatchWorker for {self.file_path} stopping.")
        self._is_running = False
        self._is_paused = False
        self._pause_cond.wakeAll()
        self.progress.emit(0, "Stopping...")


class BatchTab(QWidget):
    """Batch processing tab for handling multiple files and archives."""

    # Signals
    task_progress = Signal(int, str, int)
    task_error = Signal(str, int)
    task_finished = Signal(bool, str, int)  # success, message, row

    def __init__(self, parent=None):
        # ...existing code...
        self.log_text = None  # Will be initialized in setup_ui

        """Initialize the BatchTab.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)

        # Initialize instance variables
        self.files = []
        self.output_dirs = {}
        self.current_task_index = 0
        self.is_processing = False
        self.is_aborting = False
        self.processed_files = 0
        self.failed_files = 0
        self.total_files = 0
        self.temp_directories = []  # Track temporary directories for cleanup

        # Initialize the CHD manager (singleton)
        from core.chdman import get_chd_manager

        self.chd_manager = get_chd_manager()

        # Initialize the checkpoint manager
        self.checkpoint_manager = CheckpointManager()

        # Initialize the archive manager
        self.archive_manager = ArchiveManager()

        # Initialize the file scanner
        self.file_scanner = FileScanner()

        # UI components that will be initialized in setup_ui
        self.operation_combo = None
        self.compression_combo = None
        self.status_label = None
        self.progress_bar = None
        self.file_table = None

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Set up the UI
        self.setup_ui()
        # Add Export/Copy Log buttons below log_text
        from PySide6.QtWidgets import QHBoxLayout, QPushButton

        log_btn_layout = QHBoxLayout()
        self.export_log_btn = QPushButton("Export Log")
        self.copy_log_btn = QPushButton("Copy Log")
        log_btn_layout.addWidget(self.export_log_btn)
        log_btn_layout.addWidget(self.copy_log_btn)
        if hasattr(self, "log_text") and self.log_text:
            self.layout().addLayout(log_btn_layout)
        else:
            # Fallback: try to add to main layout
            self.layout().addLayout(log_btn_layout)
        self.export_log_btn.clicked.connect(self.export_log)
        self.copy_log_btn.clicked.connect(self.copy_log)

        # Load settings
        self.load_settings()

        # Connect signals
        self.task_progress.connect(self.on_task_progress)
        self.task_error.connect(self.on_task_error)
        self.task_finished.connect(self.on_task_finished)

        # Check for existing checkpoints (defer to after UI is fully initialized)
        QTimer.singleShot(1000, self.check_for_existing_checkpoints)

        # Load previous state if available
        self.load_checkpoint()

    def load_settings(self):
        """Load application settings from QSettings."""
        from PySide6.QtCore import QSettings

        settings = QSettings("RetroClamp", "BatchProcessing")

        # Load window geometry
        geometry = settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

        # Load window state
        window_state = settings.value("windowState")
        if window_state is not None:
            self.restoreState(window_state)

        # Load recent files
        recent_files = settings.value("recentFiles", [])
        if recent_files:
            self.recent_files = recent_files

        # Load output directory
        self.output_dir = settings.value("outputDirectory", "")

        # Load compression settings
        self.compression_level = settings.value("compressionLevel", "normal")

        # Load UI state
        if hasattr(self, "operation_combo") and self.operation_combo:
            operation = settings.value("lastOperation", "compress")
            index = self.operation_combo.findText(operation, Qt.MatchFixedString)
            if index >= 0:
                self.operation_combo.setCurrentIndex(index)

        if hasattr(self, "compression_combo") and self.compression_combo:
            compression = settings.value("compressionType", "zlib")
            index = self.compression_combo.findText(compression, Qt.MatchFixedString)
            if index >= 0:
                self.compression_combo.setCurrentIndex(index)

    def check_for_existing_checkpoints(self):
        """Check for existing checkpoints and update UI accordingly."""
        try:
            # Get list of checkpoints
            checkpoints = self.checkpoint_manager.list_checkpoints()

            if not checkpoints:
                # No checkpoints found, nothing to do
                return

            # Sort checkpoints by modification time (newest first)
            checkpoints.sort(key=lambda x: x.get("modified", 0), reverse=True)
            latest_checkpoint = checkpoints[0]

            # Update the resume button
            if hasattr(self, "resume_btn"):
                self.resume_btn.setVisible(True)
                timestamp = time.localtime(latest_checkpoint.get("modified"))
                formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", timestamp)
                self.resume_btn.setToolTip(
                    f"Resume from checkpoint created on {formatted_time}"
                )

            # Show a status message in the UI
            if hasattr(self, "status_label"):
                self.status_label.setText(
                    "Checkpoints available - click 'Resume from Last "
                    "Checkpoint' to continue"
                )

            # Log the checkpoint info
            logging.info(
                f"Found {len(checkpoints)} checkpoint(s). Latest: "
                f"{latest_checkpoint.get('filename')}"
            )

        except Exception as e:
            logging.error(f"Error checking for checkpoints: {e}", exc_info=True)

    def save_settings(self):
        """Save application settings to QSettings."""
        from PySide6.QtCore import QSettings

        settings = QSettings("RetroClamp", "BatchProcessing")

        # Save window geometry and state
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

        # Save recent files
        if hasattr(self, "recent_files") and self.recent_files:
            settings.setValue("recentFiles", self.recent_files)

        # Save output directory
        if hasattr(self, "output_dir") and self.output_dir:
            settings.setValue("outputDirectory", self.output_dir)

        # Save compression settings
        if hasattr(self, "compression_level"):
            settings.setValue("compressionLevel", self.compression_level)

        # Save UI state
        if hasattr(self, "operation_combo") and self.operation_combo:
            settings.setValue("lastOperation", self.operation_combo.currentText())

        if hasattr(self, "compression_combo") and self.compression_combo:
            settings.setValue("compressionType", self.compression_combo.currentText())

        settings.sync()  # Ensure settings are written to disk

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event to accept file/folder drops."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        """Handle drag move event to provide visual feedback."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event to process dropped files/folders."""
        logging.info("Drop event received.")
        if not event.mimeData().hasUrls():
            logging.info("Drop event ignored: No URLs in mime data.")
            return

        # Get the list of URLs from the MIME data
        urls = event.mimeData().urls()
        if not urls:
            logging.info("Drop event ignored: No URLs found.")
            return

        # Ask for output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if not output_dir:  # User cancelled
            logging.info("Output directory selection cancelled.")
            return

        logging.info(f"Selected output directory: {output_dir}")

        # Process each dropped URL
        for url in urls:
            # Convert QUrl to local file path
            file_path = url.toLocalFile()
            if not file_path:
                logging.warning(
                    f"Could not convert URL to local file path: {url.toString()}"
                )
                continue

            logging.info(f"Processing dropped item: {file_path}")
            # Check if it's a directory
            if os.path.isdir(file_path):
                self._process_dropped_directory(file_path, output_dir)
            else:
                self._process_dropped_file(file_path, output_dir)

    def _process_dropped_file(self, file_path: str, output_dir: str):
        """Process a single dropped file."""
        logging.info(f"Processing dropped file: {file_path}")
        # Check file extension to determine how to handle it
        ext = os.path.splitext(file_path)[1].lower()

        # If it's an archive, add it to be processed
        if ext in [".zip", ".7z", ".rar"]:
            logging.info(f"Identified {file_path} as an archive.")
            self._add_archive_to_queue(file_path, output_dir)
        else:
            # For regular files, just add them to the queue
            logging.info(f"Identified {file_path} as a regular file.")
            self._add_file_to_queue(file_path, output_dir)

    def log_message(self, message, level="info"):
        # HTML color and icon per level, now with timestamp
        from datetime import datetime

        icons = {
            "info": "<span style='color:#7ec8e3;'>ℹ️</span>",
            "warning": "<span style='color:#ffa500;'>⚠️</span>",
            "error": "<span style='color:#ff4c4c;'>❌</span>",
            "success": "<span style='color:#4caf50;'>✔️</span>",
        }
        colors = {
            "info": "#c8c8c8",
            "warning": "#ffa500",
            "error": "#ff4c4c",
            "success": "#4caf50",
        }
        icon = icons.get(level, "")
        color = colors.get(level, "#c8c8c8")
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        html = f"<span style='color:{color};'>{timestamp} {icon} {message}</span>"
        if self.log_text:
            self.log_text.append(html)
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
        import logging

        if level == "error":
            logging.error(message)
        elif level == "warning":
            logging.warning(message)
        elif level == "success":
            logging.info(f"SUCCESS: {message}")
        else:
            logging.info(message)

    def export_log(self):
        """Export the log contents to a file."""
        from PySide6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Log",
            "retroclamp_batch_log.txt",
            "Text Files (*.txt);;HTML Files (*.html)",
        )
        if filename:
            content = (
                self.log_text.toHtml()
                if filename.endswith(".html")
                else self.log_text.toPlainText()
            )
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            self.log_message(f"Log exported to {filename}", level="success")

    def copy_log(self):
        """Copy the log contents to the clipboard."""
        from PySide6.QtGui import QGuiApplication

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.log_text.toPlainText())
        self.log_message("Log copied to clipboard", level="success")

    def _process_dropped_directory(self, dir_path: str, output_dir: str):
        """Process a dropped directory by scanning for supported files."""
        logging.info(f"Processing dropped directory: {dir_path}")

        # Default to COMPRESS if operation_combo is not initialized
        if not hasattr(self, "operation_combo") or not self.operation_combo:
            operation = CHDTaskType.COMPRESS
            logging.warning(
                "operation_combo not initialized, defaulting to COMPRESS operation"
            )
        else:
            operation = self.operation_combo.currentData()
            logging.info(f"Current operation: {operation}")

            # Fallback to COMPRESS if currentData returns None
            if operation is None:
                operation = CHDTaskType.COMPRESS
                logging.warning("No operation selected, defaulting to COMPRESS")

        # Define file extensions based on operation
        if operation == CHDTaskType.COMPRESS:
            image_exts = [".iso", ".bin", ".img", ".cue", ".gdi"]
            archive_exts = [".zip", ".7z", ".rar"]
            extensions = image_exts + archive_exts
        else:  # Extraction
            extensions = [".chd"]
        self.log_message(
            f"Scanning directory for supported files: {dir_path}", level="info"
        )
        self.log_message(f"Looking for extensions: {extensions}", level="info")

        # Scan the directory for matching files
        found_files = 0
        from PySide6.QtCore import QThreadPool

        from core.archive import ArchiveWorker

        thread_pool = QThreadPool.globalInstance()
        pending_extractions: List[Any] = []

        def on_extraction_finished(temp_dir, file_path):
            self.log_message(
                f"Extracted archive to temp directory: {temp_dir}", level="success"
            )

            # Use FileScanner async scan for disk images in the extracted directory
            scan_signals = self.file_scanner.find_disk_images_async(temp_dir)

            def on_scan_progress(found, scanned, current):
                self.log_message(
                    f"Scanning extracted dir: {found} images found, "
                    f"{scanned} files checked...",
                    level="info",
                )

            def on_scan_error(msg):
                self.log_message(
                    f"Disk image scan error in {temp_dir}: {msg}", level="error"
                )

            def on_scan_finished(disk_images):
                nonlocal found_files
                if disk_images:
                    for extracted_path in disk_images:
                        self.log_message(
                            "Found supported image in extracted archive: "
                            f"{extracted_path}",
                            level="success",
                        )
                        self._add_file_to_queue(extracted_path, output_dir)
                        found_files += 1
                else:
                    self.log_message(
                        f"No supported files found in extracted archive: {file_path}",
                        level="warning",
                    )
                # Remove from pending extractions and check if all done
                pending_extractions.remove(file_path)
                if not pending_extractions and found_files == 0:
                    self.log_message(
                        f"No supported files found in dropped directory: {dir_path}",
                        level="warning",
                    )
                    if hasattr(self, "update_status_indicator"):
                        self.update_status_indicator(
                            "No supported files found in the dropped folder(s)."
                        )

            scan_signals.progress.connect(on_scan_progress)
            scan_signals.error.connect(on_scan_error)
            scan_signals.finished.connect(on_scan_finished)

        found_files = 0
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                if operation == CHDTaskType.COMPRESS and ext in archive_exts:
                    self.log_message(
                        f"Found archive in directory: {file_path}", level="info"
                    )
                    # Extract archive asynchronously
                    worker = ArchiveWorker(
                        operation="extract", input_path=file_path, output_path=None
                    )

                    def make_on_finished(file_path):
                        def handle(success, msg, temp_dir):
                            if success:
                                on_extraction_finished(temp_dir, file_path)
                            else:
                                self.log_message(
                                    f"Extraction failed for {file_path}: {msg}",
                                    level="error",
                                )

                        return handle

                    worker.signals.finished.connect(make_on_finished(file_path))
                    thread_pool.start(worker)
                    pending_extractions.append(file_path)
                elif any(file.lower().endswith(ext) for ext in extensions):
                    self.log_message(
                        f"Found supported file in directory: {file_path}",
                        level="success",
                    )
                    self._add_file_to_queue(file_path, output_dir)
                    found_files += 1
        if not pending_extractions and found_files == 0:
            self.log_message(
                f"No supported files found in dropped directory: {dir_path}",
                level="warning",
            )
            if hasattr(self, "update_status_indicator"):
                self.update_status_indicator(
                    "No supported files found in the dropped folder(s)."
                )

        if found_files == 0:
            self.log_message(
                f"No supported files found in dropped directory: {dir_path}",
                level="warning",
            )
            if hasattr(self, "update_status_indicator"):
                self.update_status_indicator(
                    "No supported files found in the dropped folder(s)."
                )

    def _add_archive_to_queue(self, archive_path: str, output_dir: str):
        """Add an archive file to the processing queue."""
        logging.info(
            f"Adding archive to queue: {archive_path} with output dir {output_dir}"
        )
        # Store the output directory for this archive
        self.output_dirs[archive_path] = output_dir

        # Add to the queue
        self.files.append(archive_path)
        self._update_file_table()

        # Update status (migrated to styled log)
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.setText(
                f"Added {os.path.basename(archive_path)} to queue"
            )
        self.log_message(
            f"Added {os.path.basename(archive_path)} to queue", level="success"
        )

    def _add_file_to_queue(self, file_path: str, output_dir: str):
        """Add a regular file to the processing queue."""
        logging.info(f"Adding file to queue: {file_path} with output dir {output_dir}")
        # Skip if already in queue
        if file_path in self.files:
            logging.info(f"File already in queue, skipping: {file_path}")
            return

        # Store the output directory for this file
        self.output_dirs[file_path] = output_dir

        # Add to the queue
        self.files.append(file_path)
        self._update_file_table()

        # Update status
        self.status_label.setText(f"Added {os.path.basename(file_path)} to queue")

    def _update_file_table(self):
        if not self.file_table:
            import logging

            logging.warning("File table is not initialized. Skipping update.")
            return
        """Update the file table with the current list of files."""
        if not hasattr(self, "file_table"):
            return

        self.file_table.setRowCount(len(self.files))

        for row, file_path in enumerate(self.files):
            # File name
            name_item = QTableWidgetItem(os.path.basename(file_path))
            name_item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.file_table.setItem(row, 0, name_item)

            # File size
            try:
                size = os.path.getsize(file_path)
                size_str = self._format_file_size(size)
            except OSError:
                size_str = "N/A"

            size_item = QTableWidgetItem(size_str)
            size_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.file_table.setItem(row, 1, size_item)

            # Output directory
            output_dir = self.output_dirs.get(file_path, "")
            dir_item = QTableWidgetItem(output_dir)
            self.file_table.setItem(row, 2, dir_item)

            # Status
            status_item = QTableWidgetItem("Pending")
            self.file_table.setItem(row, 3, status_item)

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in a human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes = int(size_bytes / 1024.0)
        return f"{size_bytes:.1f} PB"

    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        # ...existing UI setup code...
        # Add a log widget for user feedback
        from PySide6.QtWidgets import QTextEdit

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "QTextEdit { "
            "background: #181a20; "
            "color: #c8c8c8; "
            "font-family: Consolas, monospace; "
            "font-size: 12px; }"
        )
        main_layout.addWidget(self.log_text)

        # Set up drop zone style
        self.setStyleSheet(
            """
            QWidget {
                background-color: #2d2d2d;
                color: #f0f0f0;
            }
            QWidget#dropZone {
                border: 2px dashed #666666;
                border-radius: 10px;
                padding: 20px;
                background-color: rgba(100, 100, 100, 0.2);
            }
            QWidget#dropZone:hover {
                border-color: #4a9cff;
                background-color: rgba(74, 156, 255, 0.1);
            }
            QLabel#dropLabel {
                font-size: 16px;
                color: #aaaaaa;
                text-align: center;
            }
        """
        )

        # Operation selection
        operation_group = QGroupBox("Operation")
        operation_layout = QHBoxLayout()

        self.operation_combo = QComboBox()
        self.operation_combo.addItem("Compress to CHD", CHDTaskType.COMPRESS)
        self.operation_combo.addItem("Extract CD from CHD", CHDTaskType.EXTRACT_CD)
        self.operation_combo.addItem("Extract DVD from CHD", CHDTaskType.EXTRACT_DVD)
        self.operation_combo.addItem(
            "Extract Hard Disk from CHD", CHDTaskType.EXTRACT_HD
        )
        self.operation_combo.addItem(
            "Extract Raw Data from CHD", CHDTaskType.EXTRACT_RAW
        )
        self.operation_combo.setCurrentIndex(0)  # Default to Compress

        operation_layout.addWidget(QLabel("Operation:"))
        operation_layout.addWidget(self.operation_combo)
        operation_layout.addStretch()
        operation_group.setLayout(operation_layout)

        # Compression settings
        compression_group = QGroupBox("Compression Settings")
        compression_layout = QHBoxLayout()

        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["zlib", "lzma", "flac", "huff", "avhu"])
        self.compression_combo.setCurrentText("zlib")  # Default compression

        compression_layout.addWidget(QLabel("Compression:"))
        compression_layout.addWidget(self.compression_combo)
        compression_layout.addStretch()
        compression_group.setLayout(compression_layout)

        # Add operation and compression groups to main layout
        main_layout.addWidget(operation_group)
        main_layout.addWidget(compression_group)

        # Create drop zone widget
        self.drop_zone = QWidget()
        self.drop_zone.setObjectName("dropZone")
        self.drop_zone.setMinimumHeight(100)

        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setContentsMargins(10, 10, 10, 10)

        drop_label = QLabel("Drag and drop files or folders here")
        drop_label.setObjectName("dropLabel")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        drop_layout.addStretch()
        drop_layout.addWidget(drop_label)
        drop_layout.addStretch()

        # Add drop zone to main layout
        main_layout.addWidget(self.drop_zone)

        # Add checkpoint controls
        checkpoint_group = QGroupBox("Batch Processing")
        checkpoint_group.setStyleSheet(
            """
            QGroupBox {
                border: 1px solid #44475a;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """
        )

        checkpoint_layout = QVBoxLayout()

        # Status indicator
        self.status_indicator = QLabel()
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_status_indicator()

        # Progress bar for current operation
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Button layout
        button_layout = QHBoxLayout()

        # Resume button (initially hidden)
        self.resume_btn = QPushButton("Resume from Last Checkpoint")
        self.resume_btn.setIcon(load_svg_icon("player-play", 16, "#f8f8f2"))
        self.resume_btn.setToolTip("Resume the last saved batch processing state")
        self.resume_btn.clicked.connect(self.resume_from_last_checkpoint)
        self.resume_btn.setVisible(False)

        # Save checkpoint button
        self.save_checkpoint_btn = QPushButton("Save Checkpoint")
        self.save_checkpoint_btn.setIcon(load_svg_icon("device-floppy", 16, "#f8f8f2"))
        self.save_checkpoint_btn.setToolTip("Save the current batch processing state")
        self.save_checkpoint_btn.clicked.connect(self.save_checkpoint)

        # Load checkpoint button
        self.load_checkpoint_btn = QPushButton("Load Checkpoint...")
        self.load_checkpoint_btn.setIcon(load_svg_icon("folder-open", 16, "#f8f8f2"))
        self.load_checkpoint_btn.setToolTip(
            "Load a previously saved batch processing state"
        )
        self.load_checkpoint_btn.clicked.connect(self.load_checkpoint_dialog)

        # Add buttons to layout
        button_layout.addWidget(self.resume_btn)
        button_layout.addWidget(self.save_checkpoint_btn)
        button_layout.addWidget(self.load_checkpoint_btn)
        button_layout.addStretch()

        # Add widgets to checkpoint layout
        checkpoint_layout.addWidget(self.status_indicator)
        checkpoint_layout.addWidget(self.progress_bar)
        checkpoint_layout.addLayout(button_layout)

        # Checkpoint info panel (initially hidden)
        self.checkpoint_info = QTextEdit()
        self.checkpoint_info.setReadOnly(True)
        self.checkpoint_info.setMaximumHeight(100)
        self.checkpoint_info.setVisible(False)
        checkpoint_layout.addWidget(self.checkpoint_info)

        checkpoint_group.setLayout(checkpoint_layout)
        main_layout.addWidget(checkpoint_group)

        # Check for existing checkpoints
        self.check_for_existing_checkpoints()

        # Header
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 10)

        # ... (rest of the UI setup remains the same)

    def closeEvent(self, event):
        """Handle window close event."""
        # Save settings before closing
        self.save_settings()

        # Save checkpoint before closing
        self.save_checkpoint()

        # Clean up temporary directories
        self.cleanup_temp_directories()

        # Accept the close event
        event.accept()

    def save_checkpoint(self):
        """
        Save the current batch processing state to a checkpoint file.
        Uses CheckpointManager to save the state.
        """
        if not self.files:
            show_info("No batch in progress to save.")
            return False

        try:
            # Prepare file status information
            files_status = []
            for i, file_path in enumerate(self.files):
                status = "pending"
                if i < self.current_task_index:
                    status = "completed"
                elif i == self.current_task_index and self.is_processing:
                    status = "in_progress"

                files_status.append(
                    {
                        "path": file_path,
                        "status": status,
                        "output_dir": self.output_dirs.get(file_path, ""),
                    }
                )

            # Prepare metadata
            metadata = {
                "operation": self.operation_combo.currentData(),
                "compression": (
                    self.compression_combo.currentData()
                    if hasattr(self, "compression_combo")
                    else None
                ),
                "processed_files": self.processed_files,
                "failed_files": self.failed_files,
                "is_processing": self.is_processing,
                "timestamp": time.time(),
            }

            # Create checkpoint
            checkpoint_path = self.checkpoint_manager.create_checkpoint(
                batch_id=self.batch_id,
                files=files_status,
                current_index=self.current_task_index,
                metadata=metadata,
            )

            # Update UI
            self.update_checkpoint_preview(checkpoint_path)
            self.check_for_existing_checkpoints()

            # Show notification
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Checkpoint Saved")
            msg.setText("Batch processing checkpoint has been saved successfully.")
            msg.setInformativeText(f"Checkpoint saved to:\n{checkpoint_path}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

            return True

        except Exception as e:
            show_error(f"Failed to save checkpoint: {str(e)}")
            return False

    def load_checkpoint(self, checkpoint_file=None):
        """Load batch processing state from a checkpoint file using CheckpointManager.

        Args:
            checkpoint_file: Path to the checkpoint file. If None, loads the
                latest checkpoint.

        Returns:
            bool: True if checkpoint was loaded successfully, False otherwise.
        """
        try:
            if checkpoint_file is None:
                # Try to find the most recent checkpoint
                checkpoints = self.checkpoint_manager.list_checkpoints()
                if not checkpoints:
                    if hasattr(self, "status_label") and self.status_label:
                        self.status_label.setText("No checkpoints available.")
                    return False
                checkpoint_file = checkpoints[-1]  # Get most recent

            # Load the checkpoint
            checkpoint_data = self.checkpoint_manager.load_checkpoint(checkpoint_file)

            if not checkpoint_data:
                show_warning("No checkpoint data found or invalid checkpoint file.")
                return False

            # Restore the file list and other state
            self.files = checkpoint_data.get("files", [])
            self.output_dirs = checkpoint_data.get("output_dirs", {})
            self.current_task_index = checkpoint_data.get("current_task_index", 0)

            # Get metadata and update counters
            metadata = checkpoint_data.get("metadata", {})
            self.processed_files = metadata.get("processed_files", 0)
            self.failed_files = metadata.get("failed_files", 0)
            self.total_files = len(self.files)

            # Update UI
            self._update_file_table()
            is_processing = metadata.get("is_processing", False)
            self.update_ui_for_processing(is_processing)

            # Restore combo box selections if they exist
            if "operation" in metadata and hasattr(self, "operation_combo"):
                # Try both findData and findText for compatibility
                index = self.operation_combo.findData(metadata["operation"])
                if index < 0:  # If not found in data, try text
                    index = self.operation_combo.findText(metadata["operation"])
                if index >= 0:
                    self.operation_combo.setCurrentIndex(index)

            if "compression" in metadata and hasattr(self, "compression_combo"):
                # Try both findData and findText for compatibility
                index = self.compression_combo.findData(metadata["compression"])
                if index < 0:  # If not found in data, try text
                    index = self.compression_combo.findText(metadata["compression"])
                if index >= 0:
                    self.compression_combo.setCurrentIndex(index)

            show_info(
                f"Checkpoint loaded successfully: {os.path.basename(checkpoint_file)}"
            )
            return True

        except Exception as e:
            show_error(f"Failed to load checkpoint: {str(e)}")
            return False

    # Removed duplicate abort_processing method
    # Keeping the more complete implementation below

    # Removed duplicate definition of check_for_existing_checkpoints
    # to resolve lint warning.

    def update_status_indicator(self, status=None):
        """Update the status indicator with the current state."""
        if status == "processing":
            self.status_indicator.setText(
                "Status: <span style='color:#50fa7b'>Processing</span>"
            )
        elif status == "paused":
            self.status_indicator.setText(
                "Status: <span style='color:#ffb86c'>Paused</span>"
            )
        elif status == "error":
            self.status_indicator.setText(
                "Status: <span style='color:#ff5555'>Error</span>"
            )
        elif status == "completed":
            self.status_indicator.setText(
                "Status: <span style='color:#50fa7b'>Completed</span>"
            )
        else:
            self.status_indicator.setText(
                "Status: <span style='color:#f1fa8c'>Idle</span>"
            )

    def update_checkpoint_preview(self, checkpoint_path):
        """Update the checkpoint info panel with details about the checkpoint.

        Args:
            checkpoint_path: Path to the checkpoint file to preview

        Returns:
            bool: True if the preview was updated successfully, False otherwise
        """
        try:
            if not hasattr(self, "checkpoint_manager") or not hasattr(
                self, "checkpoint_info"
            ):
                return False

            checkpoint = self.checkpoint_manager.load_checkpoint(checkpoint_path)
            if not checkpoint:
                self.checkpoint_info.setVisible(False)
                return False

            # Extract checkpoint information
            files = checkpoint.get("files", [])
            total_files = len(files)
            completed = sum(1 for f in files if f.get("status") == "completed")
            in_progress = sum(1 for f in files if f.get("status") == "in_progress")
            pending = total_files - completed - in_progress

            # Get current file being processed
            current_file = next(
                (f for f in files if f.get("status") == "in_progress"),
                files[0] if files else {},
            )
            current_file_name = os.path.basename(current_file.get("path", "N/A"))

            # Format the preview text
            preview = f"""
            <html>
            <body style='color:#f8f8f2;'>
                <p><b>Checkpoint:</b> {os.path.basename(checkpoint_path)}</p>
                <p><b>Created:</b> {time.ctime(os.path.getmtime(checkpoint_path))}</p>
                <p><b>Progress:</b> {completed} completed, "
                     "{in_progress} in progress, {pending} pending</p>
                <p><b>Current File:</b> {current_file_name}</p>
            </body>
            </html>"""

            self.checkpoint_info.setHtml(preview)
            self.checkpoint_info.setVisible(True)
            return True

        except Exception as e:
            print(f"Error updating checkpoint preview: {e}")
            if hasattr(self, "checkpoint_info"):
                self.checkpoint_info.setVisible(False)
            return False

    def resume_from_last_checkpoint(self):
        """Resume processing from the last saved checkpoint."""
        if not hasattr(self, "checkpoint_manager"):
            return

        latest_checkpoint = self.checkpoint_manager.get_latest_checkpoint()
        if latest_checkpoint:
            self.load_checkpoint(latest_checkpoint)

    def load_checkpoint_dialog(self):
        """Show a dialog to load a checkpoint file with preview."""
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Checkpoint")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        # File selection
        file_layout = QHBoxLayout()
        file_label = QLabel("Checkpoint File:")
        file_edit = QLineEdit()
        file_edit.setReadOnly(True)

        def browse():
            file_name, _ = QFileDialog.getOpenFileName(
                dialog,
                "Select Checkpoint File",
                self.checkpoint_manager.checkpoint_dir,
                "Checkpoint Files (*.json);;All Files (*)",
            )
            if file_name:
                file_edit.setText(file_name)
                self.update_checkpoint_preview(file_name)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(browse)

        file_layout.addWidget(file_label)
        file_layout.addWidget(file_edit, 1)
        file_layout.addWidget(browse_btn)

        # Preview area
        preview_label = QLabel("Checkpoint Preview:")
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        # Add widgets to layout
        layout.addLayout(file_layout)
        layout.addWidget(preview_label)
        layout.addWidget(preview_text, 1)
        layout.addWidget(button_box)

        # Restore metadata from the loaded checkpoint
        if hasattr(self, "checkpoint_manager") and self.checkpoint_manager:
            # Get the current checkpoint data
            current_checkpoint = self.checkpoint_manager.current_checkpoint
            if current_checkpoint and hasattr(current_checkpoint, "metadata"):
                metadata = current_checkpoint.metadata
                self.processed_files = metadata.get("processed_files", 0)
                self.failed_files = metadata.get("failed_files", 0)
                self.total_files = len(self.files)

                # Update UI
                self._update_file_table()
                is_processing = metadata.get("is_processing", False)
                self.update_ui_for_processing(is_processing)

                # Restore combo box selections if they exist
                # (Add any combo box restoration logic here if needed)

    # Removed duplicate function definitions - keeping only one version of each function

    def restore_ui_state_from_metadata(self, metadata):
        """Restore UI state from metadata.

        Args:
            metadata (dict): Dictionary containing UI state
        """
        try:
            if not metadata:
                return

            # Update UI based on metadata
            if "is_processing" in metadata:
                self.update_ui_for_processing(metadata["is_processing"])

            # Restore combo box selections if they exist
            if "operation" in metadata and hasattr(self, "operation_combo"):
                # Try both findData and findText for compatibility
                index = self.operation_combo.findData(metadata["operation"])
                if index < 0:  # If not found in data, try text
                    index = self.operation_combo.findText(metadata["operation"])
                if index >= 0:
                    self.operation_combo.setCurrentIndex(index)

                if "compression" in metadata and hasattr(self, "compression_combo"):
                    index = self.compression_combo.findData(metadata["compression"])
                    if index >= 0:
                        self.compression_combo.setCurrentIndex(index)

                show_info("Checkpoint loaded successfully.")
                return True

        except Exception as e:
            show_error(f"Failed to load checkpoint: {str(e)}")
            return False

    def update_ui_for_processing(self, is_processing):
        """Update UI elements based on processing state."""
        if not hasattr(self, "add_files_btn") or not hasattr(self, "operation_combo"):
            return

        # Update button states
        self.add_files_btn.setEnabled(not is_processing)
        if hasattr(self, "add_dir_btn"):
            self.add_dir_btn.setEnabled(not is_processing)
        if hasattr(self, "clear_btn"):
            self.clear_btn.setEnabled(not is_processing)

        self.start_btn.setEnabled(not is_processing)
        self.operation_combo.setEnabled(not is_processing)

        if hasattr(self, "compression_spin"):
            self.compression_spin.setEnabled(not is_processing)
        if hasattr(self, "verify_check"):
            self.verify_check.setEnabled(not is_processing)

        # Update button states based on processing state
        if is_processing:
            self.start_btn.setEnabled(False)
            if hasattr(self, "pause_btn"):
                self.pause_btn.setEnabled(True)
            if hasattr(self, "abort_btn"):
                self.abort_btn.setEnabled(True)
        else:
            self.start_btn.setEnabled(True)
            if hasattr(self, "pause_btn"):
                self.pause_btn.setEnabled(False)
            if hasattr(self, "abort_btn"):
                self.abort_btn.setEnabled(False)

        # Add abort button if not exists
        if not hasattr(self, "abort_btn") and hasattr(self, "button_layout"):
            self.abort_btn = QPushButton("Abort")
            self.abort_btn.setIcon(load_svg_icon("x", 16, "#f8f8f2"))
            self.abort_btn.clicked.connect(self.abort_processing)
            self.button_layout.insertWidget(4, self.abort_btn)

        # Update start button
        if not is_processing:
            self.start_btn.setText("Start Processing")
            self.start_btn.setIcon(load_svg_icon("player-play", 16, "#f8f8f2"))

            # Remove pause/resume button if exists
            if hasattr(self, "pause_btn"):
                self.pause_btn.setParent(None)
                self.pause_btn.deleteLater()
                delattr(self, "pause_btn")

                # Remove abort button if exists
                if hasattr(self, "abort_btn"):
                    self.abort_btn.setParent(None)
                    self.abort_btn.deleteLater()
                    delattr(self, "abort_btn")

            # Hide the busy indicator
            if hasattr(self, "hide_busy_indicator"):
                self.hide_busy_indicator()

            # Reset state flags
            if hasattr(self, "is_paused"):
                self.is_paused = False
            if hasattr(self, "is_aborting"):
                self.is_aborting = False

            # Update status
            if hasattr(self, "status_label"):
                if hasattr(self, "current_task_index") and hasattr(self, "tasks"):
                    if self.current_task_index < len(self.tasks):
                        status_text = (
                            f"Batch processing aborted. "
                            f"{self.current_task_index}/"
                            f"{len(self.tasks)} files processed."
                        )
                        self.status_label.setText(status_text)
                    else:
                        status_text = (
                            f"Batch processing completed. "
                            f"{self.current_task_index}/"
                            f"{len(self.tasks)} files processed."
                        )
                        self.status_label.setText(status_text)

    def pause_processing(self):
        """Pause the current processing."""
        if not self.is_processing:
            return

        if self.chd_manager.is_paused():
            # Resume processing
            self.chd_manager.resume()
            self.pause_button.setText("Pause")
            self.status_label.setText("Processing resumed")
        else:
            # Pause processing
            self.chd_manager.pause()
            self.pause_button.setText("Resume")
            self.status_label.setText("Processing paused")

    def stop_processing(self):
        """Stop the current processing."""
        if not self.is_processing:
            return

        # Set abort flag
        self.is_aborting = True

        # Stop all tasks
        self.chd_manager.stop()

        # Update UI
        self.finish_processing(aborted=True)
        self.status_label.setText("Processing stopped by user")

    def abort_processing(self):
        """Gracefully abort processing after current task completes."""
        if not hasattr(self, "is_aborting") or not hasattr(self, "abort_btn"):
            return

        if not self.is_aborting:
            self.is_aborting = True
            self.abort_btn.setEnabled(False)  # Prevent multiple clicks
            self.abort_btn.setText("Aborting...")

            # Update overlay to show aborting state
            if hasattr(self, "show_busy_indicator"):
                self.show_busy_indicator("aborting")

            # If paused, resume to allow completion of current task
            if hasattr(self, "is_paused") and self.is_paused:
                self.is_paused = False
                if hasattr(self, "pause_btn"):
                    self.pause_btn.setText("Pause")
                    self.pause_btn.setIcon(load_svg_icon("player-pause", 16, "#f8f8f2"))
                    self.pause_btn.setEnabled(False)  # Disable pause during abort

                # Process next task (which will check is_aborting)
                if hasattr(self, "process_next_task"):
                    self.process_next_task()

    def toggle_pause_resume(self):
        """Toggle between pause and resume states."""
        if not hasattr(self, "is_paused") or not hasattr(self, "pause_btn"):
            return

        self.is_paused = not self.is_paused

        if self.is_paused:
            # Update button text and icon
            self.pause_btn.setText("Resume")
            self.pause_btn.setIcon(load_svg_icon("player-play", 16, "#f8f8f2"))

            # Update status and overlay if attributes exist
            if (
                hasattr(self, "status_label")
                and hasattr(self, "current_task_index")
                and hasattr(self, "tasks")
            ):
                status_text = (
                    f"Processing paused. {self.current_task_index}/"
                    f"{len(self.tasks)} files processed."
                )
                self.status_label.setText(status_text)
            if hasattr(self, "show_busy_indicator"):
                self.show_busy_indicator("paused")
        else:
            # Update button text and icon
            self.pause_btn.setText("Pause")
            self.pause_btn.setIcon(load_svg_icon("player-pause", 16, "#f8f8f2"))

            # Update status and overlay if attributes exist
            if (
                hasattr(self, "status_label")
                and hasattr(self, "current_task_index")
                and hasattr(self, "tasks")
            ):
                status_text = (
                    f"Processing resumed. {self.current_task_index}/"
                    f"{len(self.tasks)} files processed."
                )
                self.status_label.setText(status_text)
            if hasattr(self, "hide_busy_indicator"):
                self.hide_busy_indicator()

            # Continue processing if not already processing
            if (
                not hasattr(self, "is_processing") or not self.is_processing
            ) and hasattr(self, "process_next_task"):
                self.process_next_task()

    def log(self, row, message):
        """Add a message to the status column for a specific row.

        Args:
            row: Table row index
            message: Message to add
        """
        if not hasattr(self, "files_table") or not hasattr(self, "status_label"):
            return

        # Get the status item
        status_item = self.files_table.item(row, 2)
        if status_item is None:
            return

        # Add the message to the tooltip
        current_tooltip = status_item.toolTip()
        if current_tooltip:
            new_tooltip = f"{current_tooltip}\n{message}"
        else:
            new_tooltip = message

        status_item.setToolTip(new_tooltip)

        # Update the status label with the message
        self.status_label.setText(message)

    def on_task_started(self, row: int, message: str):
        """Handle task started event.

        Args:
            row: Table row index
            message: Start message
        """
        if hasattr(self, "status_labels") and row < len(self.status_labels):
            self.status_labels[row].setText(message)

        # Reset progress bar
        if hasattr(self, "progress_bars") and row < len(self.progress_bars):
            self.progress_bars[row].setValue(0)
            # Reset to default style
            self.progress_bars[row].setStyleSheet("")

    def on_task_progress(self, progress: int, message: str, row: int):
        """Update progress for a specific task.

        Args:
            progress: Progress percentage (0-100)
            message: Progress message
            row: Table row index
        """
        # Update progress bar
        if hasattr(self, "progress_bars") and row < len(self.progress_bars):
            self.progress_bars[row].setValue(progress)

        # Update status message
        if hasattr(self, "status_labels") and row < len(self.status_labels):
            self.status_labels[row].setText(message)

        # Update overall progress
        self.update_overall_progress()

    def on_task_finished(self, success: bool, message: str, row: int):
        """Handle task completion.

        Args:
            success: Whether the task completed successfully
            message: Completion message
            row: Table row index
        """
        # Update counters
        if success:
            self.processed_files += 1
        else:
            self.failed_files += 1

        # Update status
        if hasattr(self, "status_labels") and row < len(self.status_labels):
            status = "Completed" if success else "Failed"
            self.status_labels[row].setText(f"{status}: {message}")

        # Update progress bar color based on success/failure
        if hasattr(self, "progress_bars") and row < len(self.progress_bars):
            style = ""
            if success:
                style = (
                    "QProgressBar::chunk { "
                    "background-color: #4CAF50; }"  # Green for success
                )
                self.progress_bars[row].setValue(100)  # Ensure it shows as complete
            else:
                style = (
                    "QProgressBar::chunk { "
                    "background-color: #F44336; }"  # Red for failure
                )
                self.progress_bars[row].setValue(100)  # Ensure it shows as complete
            self.progress_bars[row].setStyleSheet(style)

        # Update overall progress
        self.update_overall_progress()

        # Check if all tasks are done
        if (self.processed_files + self.failed_files) >= len(self.files):
            self.finish_processing()

    def on_task_error(self, error_message: str, row: int):
        """Handle task errors.

        Args:
            error_message: Error message
            row: Table row index
        """
        # Update status
        if hasattr(self, "status_labels") and row < len(self.status_labels):
            self.status_labels[row].setText(f"Error: {error_message}")

        # Update progress bar color to indicate error
        if hasattr(self, "progress_bars") and row < len(self.progress_bars):
            style = (
                "QProgressBar::chunk { background-color: #F44336; }"  # Red for error
            )
            self.progress_bars[row].setStyleSheet(style)
            self.progress_bars[row].setValue(100)  # Make sure it's visible

        # Update counters
        self.failed_files += 1

        # Update overall progress
        self.update_overall_progress()

        # Check if all tasks are done
        if (self.processed_files + self.failed_files) >= len(self.files):
            self.finish_processing()

    def check_archive_compatibility(self, archive_path: str, row: int) -> bool:
        """Check if an archive contains compatible files.

        Args:
            archive_path: Path to the archive file
            row: Table row index for logging

        Returns:
            bool: True if the archive contains compatible files, False otherwise
        """
        self.log(
            row, f"Checking archive compatibility: {os.path.basename(archive_path)}"
        )

        # Determine the target file extension based on operation
        operation = self.operation_combo.currentData()
        if operation == CHDTaskType.COMPRESS:
            # For compression, look for disk image files
            target_extensions = [".iso", ".bin", ".img", ".cue", ".gdi", ".chd"]
        else:
            # For extraction, look for CHD files
            target_extensions = [".chd"]

        # Check archive contents
        try:
            if archive_path.lower().endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    for file in zip_ref.namelist():
                        if any(file.lower().endswith(ext) for ext in target_extensions):
                            return True

            elif archive_path.lower().endswith(".7z"):
                with py7zr.SevenZipFile(archive_path, "r") as zip_ref:
                    for file in zip_ref.getnames():
                        if any(file.lower().endswith(ext) for ext in target_extensions):
                            return True

            elif archive_path.lower().endswith(".rar"):
                with rarfile.RarFile(archive_path, "r") as rar_ref:
                    for file in rar_ref.namelist():
                        if any(file.lower().endswith(ext) for ext in target_extensions):
                            return True

            self.log(row, "No compatible files found in archive")
            return False

        except Exception as e:
            self.log(row, f"Error checking archive: {str(e)}")
            return False

    def extract_archive(self, archive_path, row):
        """Extract an archive to a temporary directory.

        Args:
            archive_path: Path to the archive file
            row: Table row index for logging

        Returns:
            str or None: Path to the temporary directory if created, None otherwise.
        """
        logging.info(f"Attempting to extract archive: {archive_path}")
        self.log(row, f"Extracting archive: {os.path.basename(archive_path)}")

        temp_dir = None
        try:
            # Create a temporary directory
            temp_dir = tempfile.mkdtemp(prefix="retroclamp_")
            self.temp_directories.append(temp_dir)
            logging.info(f"Created temporary directory for extraction: {temp_dir}")

            # Determine the target file extension based on operation
            operation = self.operation_combo.currentData()
            if operation == CHDTaskType.COMPRESS:
                # For compression, look for disk image files
                target_extensions = [".iso", ".bin", ".img", ".cue", ".gdi"]
            else:
                # For extraction, look for CHD files
                target_extensions = [".chd"]
            logging.info(f"Looking for extensions in archive: {target_extensions}")

            # Extract the archive
            self.archive_manager.extract_archive(
                archive_path,
                temp_dir,
                progress_callback=lambda value, msg: self.on_task_progress(
                    value, msg, row
                ),
                error_callback=lambda msg: self.on_task_error(msg, row),
                finished_callback=lambda success, msg: self.on_task_finished(
                    success, msg, row
                ),
            )

            # Find files matching the target extension
            # (This logic might be better in on_task_finished)
            extracted_files = []
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    for ext in target_extensions:
                        if file.lower().endswith(ext):
                            extracted_files.append(os.path.join(root, file))

            if extracted_files:
                logging.info(
                    f"Found {len(extracted_files)} compatible files "
                    f"in archive in {os.path.basename(temp_dir)}"
                )
                self.log(
                    row, f"Found {len(extracted_files)} compatible files in archive"
                )

            # The actual extraction is asynchronous via archive_manager,
            # so we don't return here. The on_task_finished callback
            # will handle the next steps. We return the temp_dir path
            # if created successfully.
            return temp_dir

        except Exception as e:
            error_msg = (
                f"Error extracting archive {os.path.basename(archive_path)}: {e}"
            )
            logging.error(error_msg)
            self.task_error.emit(error_msg, row)
            # Clean up the temporary directory if extraction failed
            if temp_dir and os.path.exists(temp_dir):
                self.cleanup_temp_directories([temp_dir])
            return None

    def start_processing(self):
        """Start processing all files in the batch."""
        from pathlib import Path

        from PySide6.QtWidgets import QMessageBox

        if not hasattr(self, "files") or not self.files:
            show_warning("No files to process")
            return

        # --- INPUT VALIDATION ---
        for file_path in self.files:
            file_obj = Path(file_path)
            if not file_obj.exists():
                QMessageBox.warning(
                    self, "Invalid Input File", f"The file does not exist: {file_path}"
                )
                return
            if not file_obj.is_file() and not self.archive_manager.is_archive(
                file_path
            ):
                QMessageBox.warning(
                    self,
                    "Invalid Input File",
                    f"The file is not a valid file or supported archive: {file_path}",
                )
                return
            # Output directory for this file
            output_dir = self.output_dirs.get(file_path, "")
            if not output_dir:
                QMessageBox.warning(
                    self,
                    "Invalid Output Directory",
                    f"No output directory specified for file: {file_path}",
                )
                return
            output_path = Path(output_dir)
            if not output_path.exists() or not output_path.is_dir():
                QMessageBox.warning(
                    self,
                    "Invalid Output Directory",
                    f"The output directory does not exist: {output_dir}",
                )
                return
            if not os.access(str(output_path), os.W_OK):
                QMessageBox.warning(
                    self,
                    "Invalid Output Directory",
                    f"The output directory is not writable: {output_dir}",
                )
                return

        if self.is_processing:
            show_info("Processing is already in progress")
            return

        # Reset counters and state
        self.processed_files = 0
        self.failed_files = 0
        self.current_task_index = 0
        self.is_processing = True
        self.is_aborting = False

        # Clear any existing tasks
        self.chd_manager.clear_tasks()

        # Create a task for each file
        for file_path in self.files:
            output_dir = self.output_dirs.get(file_path, os.path.dirname(file_path))
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(
                output_dir,
                (
                    base_name + ".chd"
                    if self.operation_combo.currentData() == CHDTaskType.COMPRESS
                    else ".bin"
                ),
            )

            # Determine operation type
            operation = self.operation_combo.currentData()

            # Create task
            task = CHDTask(
                task_type=operation,
                input_file=file_path,
                output_file=output_path,
                compression_level=self.compression_combo.currentText(),
                force=True,
                media_type=self._get_media_type(file_path),
                user_data={"file_path": file_path, "output_dir": output_dir},
            )

            self.chd_manager.add_task(task)

        # Update UI
        self.update_ui_for_processing(True)
        self.total_files = len(self.files)

        # Execute all tasks
        signals_list = self.chd_manager.execute_all_tasks()

        # Connect signals for all tasks
        for idx, signals in enumerate(signals_list):
            signals.started.connect(lambda msg, i=idx: self.on_task_started(i, msg))
            signals.progress.connect(
                lambda val, msg, i=idx: self.on_task_progress(val, msg, i)
            )
            signals.finished.connect(
                lambda success, msg, i=idx: self.on_task_finished(success, msg, i)
            )
            signals.error.connect(lambda msg, i=idx: self.on_task_error(msg, i))

    def cleanup_temp_directories(self, temp_dirs=None):
        """Clean up temporary directories created during processing.

        Args:
            temp_dirs: List of temporary directories to clean up.
                If None, uses self.temp_directories
        """
        if temp_dirs is None:
            if not hasattr(self, "temp_directories") or not self.temp_directories:
                return
            temp_dirs = self.temp_directories[:]

        logging.info("Cleaning up temporary directories...")

        for temp_dir in temp_dirs[:]:  # Iterate over a copy of the list
            try:
                if os.path.exists(temp_dir):
                    # First, try to remove files with read-only attributes
                    for root, dirs, files in os.walk(temp_dir, topdown=False):
                        for name in files:
                            file_path = os.path.join(root, name)
                            try:
                                # Set owner-only permissions (security)
                                os.chmod(file_path, 0o600)
                                os.unlink(file_path)
                            except Exception as e:
                                logging.warning(
                                    f"Could not remove file {file_path}: {e}"
                                )

                        # Remove directories
                        for name in dirs:
                            dir_path = os.path.join(root, name)
                            try:
                                # Set owner-only permissions (security)
                                os.chmod(dir_path, 0o700)
                                os.rmdir(dir_path)
                            except Exception as e:
                                logging.warning(
                                    f"Could not remove directory {dir_path}: {e}"
                                )

                    # Finally, remove the top-level directory
                    try:
                        # Set owner-only permissions (security)
                        os.chmod(temp_dir, 0o700)
                        os.rmdir(temp_dir)
                        logging.info(
                            f"Successfully removed temporary directory: {temp_dir}"
                        )
                    except Exception as e:
                        logging.error(
                            f"Failed to remove temporary directory {temp_dir}: {e}"
                        )

                # Remove from the list whether successful or not
                if temp_dir in self.temp_directories:
                    self.temp_directories.remove(temp_dir)

            except Exception as e:
                logging.error(f"Error cleaning up temporary directory {temp_dir}: {e}")

        logging.info("Temporary directory cleanup completed")

    def _get_media_type(self, file_path: str) -> str:
        """Determine the media type based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".cue", ".iso", ".bin"]:
            return "CD"
        elif ext in [".chd"]:
            # For extraction, we need to check the CHD type
            # This is a simplified version - you might want to enhance this
            return "CD"  # Default to CD
        return "Hard Disk"  # Defaults

    def process_next_task(self):
        """Process the next task in the queue."""
        if self.current_task_index < len(self.files):
            file_path = self.files[self.current_task_index]
            file_name = os.path.basename(file_path)

            # Update status
            current = self.current_task_index + 1
            status_text = f"Processing {current} of {self.total_files}: {file_name}"
            self.status_label.setText(status_text)

            # Check if file is an archive
            if any(file_name.lower().endswith(ext) for ext in [".zip", ".7z", ".rar"]):
                # Handle archive file
                self.process_archive_file(file_path)
            else:
                # Handle regular file
                self.process_regular_file(file_path)
        else:
            # All tasks completed
            self.all_tasks_completed()

    def process_archive_file(self, file_path):
        """Process an archive file by extracting and queueing its contents."""
        row = self.current_task_index
        file_name = os.path.basename(file_path)

        # Check if archive contains compatible files
        if not self.check_archive_compatibility(file_path, row):
            self.log(row, f"Skipping archive (no compatible files): {file_name}")
            self.task_completed(
                success=False, message=f"No compatible files in {file_name}"
            )
            return

        # Extract the archive
        success, temp_dir, extracted_files = self.extract_archive(file_path, row)

        if success and extracted_files:
            # Add extracted files to the processing queue
            for extracted_file in extracted_files:
                self.files.insert(self.current_task_index + 1, extracted_file)

            # Update total files count
            self.total_files = len(self.files)

            # Process the first extracted file next
            self.current_task_index += 1
            self.process_next_task()

    def process_regular_file(self, file_path: str):
        """Process a regular file (non-archive) using CHDMAN.

        Args:
            file_path: Path to the file to process
        """
        row = self.current_task_index
        file_name = os.path.basename(file_path)

        try:
            # Get output directory for this file (or use default)
            output_dir = self.output_dirs.get(file_path, os.path.dirname(file_path))

            # Get operation type from UI
            operation = self.operation_combo.currentText().lower()

            # Get compression settings from UI
            compression = "zlib"  # Default compression
            if hasattr(self, "compression_combo"):
                compression = self.compression_combo.currentText().lower()

            # Get verify setting from UI
            verify = False
            if hasattr(self, "verify_check") and self.verify_check.isChecked():
                verify = True

            # Ensure compression is a CHDCompressionType enum member
            if isinstance(compression, str):
                try:
                    compression_to_pass = CHDCompressionType[compression.upper()]
                except KeyError as err:
                    raise ValueError(
                        f"Invalid compression type: {compression}"
                    ) from err
            elif isinstance(compression, CHDCompressionType):
                compression_to_pass = compression
            else:
                raise TypeError(f"Unexpected type for compression: {type(compression)}")

            # Create and configure worker
            self.worker = BatchWorker(
                file_path=file_path,
                output_dir=output_dir,
                operation=operation,
                compression=compression_to_pass,
                verify=verify,
                parent=self,
            )

            # Connect worker signals
            self.worker.progress.connect(
                lambda p, msg, r=row: self.on_task_progress(p, msg, r)
            )
            self.worker.error.connect(lambda msg, r=row: self.on_task_error(msg, r))
            self.worker.finished.connect(lambda: self._on_worker_finished(row))
            self.worker.file_completed.connect(
                lambda path, msg, r=row: self._on_file_completed(path, msg, r)
            )

            # Store worker reference
            if not hasattr(self, "workers"):
                self.workers = {}
            self.workers[row] = self.worker

            # Update UI
            self.log(row, f"Starting {operation} for {file_name}")
            self.task_progress.emit(0, f"Starting {operation}...", row)

            # Start processing
            self.worker.start()

        except Exception as e:
            error_msg = f"Failed to start processing: {str(e)}"
            self.task_error.emit(error_msg, row)
            self.task_progress.emit(0, error_msg, row)

    def _on_worker_finished(self, row: int):
        """Handle worker completion.

        Args:
            row: Row index in the files table
        """
        # Clean up worker reference
        if hasattr(self, "workers") and row in self.workers:
            self.workers[row].deleteLater()
            del self.workers[row]

    def _on_file_completed(self, file_path: str, message: str, row: int):
        """Handle file completion.

        Args:
            file_path: Path to the processed file
            message: Completion message
            row: Row index in the files table
        """
        self.task_finished.emit(True, message, row)
        self.task_progress.emit(100, message, row)

    def all_tasks_completed(self):
        """Called when all tasks have been processed."""
        try:
            self.is_processing = False
            self.is_aborting = False

            # Save checkpoint before cleaning up
            self.save_checkpoint()

            # Clean up any temporary directories
            self.cleanup_temp_directories()

            # Disconnect all signals from CHDManager
            try:
                signals_list = self.chd_manager.get_task_signals()
                for signals in signals_list:
                    try:
                        if signals:
                            signals.started.disconnect()
                            signals.progress.disconnect()
                            signals.finished.disconnect()
                            signals.error.disconnect()
                    except (TypeError, RuntimeError):
                        pass  # Already disconnected or never connected
            except AttributeError:
                pass  # CHDManager doesn't have get_task_signals method

            # Update UI on the main thread
            QTimer.singleShot(0, self._update_ui_after_completion)

        except Exception as e:
            logging.error(f"Error in all_tasks_completed: {e}", exc_info=True)
            self._show_completion_message(
                f"Error completing tasks: {str(e)}", is_error=True
            )

    def _update_ui_after_completion(self):
        """Update UI after all tasks have completed."""
        try:
            # Update UI
            self.update_ui_for_processing(False)

            # Show completion message
            message = (
                f"Processing complete. "
                f"{self.processed_files} files processed successfully."
            )
            if self.failed_files > 0:
                message += f" {self.failed_files} files failed."

            self.status_label.setText(message)
            self._show_completion_message(message, is_error=self.failed_files > 0)

            # Clear any selection in the table
            if hasattr(self, "files_table"):
                self.files_table.clearSelection()

            # Save final checkpoint
            self.save_checkpoint()

        except Exception as e:
            logging.error(f"Error updating UI after completion: {e}", exc_info=True)

    def _show_completion_message(self, message, is_error=False):
        """Show completion message with appropriate styling."""
        try:
            if is_error:
                QMessageBox.critical(self, "Processing Completed with Errors", message)
            else:
                QMessageBox.information(self, "Processing Complete", message)
        except Exception as e:
            logging.error(f"Error showing completion message: {e}", exc_info=True)

    def task_completed(self, success=True, message=None):
        """Handle completion of a single task.

        Args:
            success: Whether the task completed successfully
            message: Optional completion message
        """
        try:
            if success:
                self.processed_files += 1
                if message:
                    logging.info(f"Task completed: {message}")
            else:
                self.failed_files += 1
                if message:
                    logging.error(f"Task failed: {message}")

            # Update progress
            total = len(self.files) if hasattr(self, "files") else 1
            if total > 0:
                processed_count = self.processed_files + self.failed_files
                progress = int((processed_count / total) * 100)
            else:
                progress = 0

            # Update progress bar on the main thread
            if hasattr(self, "progress_bar"):
                self.progress_bar.setValue(progress)

            # Update status label
            processed = self.processed_files
            failed = self.failed_files
            status_message = (
                f"Processed: {processed} | Failed: {failed} | Total: {total}"
            )
            if hasattr(self, "status_label"):
                self.status_label.setText(status_message)

            # Save checkpoint after each task
            try:
                self.save_checkpoint()
            except Exception as e:
                logging.error(f"Error saving checkpoint: {e}", exc_info=True)

            # Process next task or finish
            if (
                not self.is_aborting
                and hasattr(self, "files")
                and (self.processed_files + self.failed_files) < len(self.files)
            ):
                QTimer.singleShot(0, self.process_next_task)
            else:
                QTimer.singleShot(0, self.all_tasks_completed)

        except Exception as e:
            logging.error(f"Error in task_completed: {e}", exc_info=True)
            # Try to continue with next task
            if (
                not self.is_aborting
                and hasattr(self, "files")
                and (self.processed_files + self.failed_files) < len(self.files)
            ):
                QTimer.singleShot(0, self.process_next_task)
            else:
                QTimer.singleShot(0, self.all_tasks_completed)

    # Removed duplicate task-related function definitions
    # Keeping only one version of each function

    def browse(self):
        """Open a file dialog to select files for processing."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("All Files (*)")

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.add_files(selected_files)

    # Signal handlers - using the first implementation of these functions
