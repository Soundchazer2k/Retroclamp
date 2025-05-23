"""Extraction tab for RetroClamp.

This module provides the UI and functionality for extracting disk images
from CHD files using the CHDMAN utility.
"""

import logging
import os
import zipfile
from pathlib import Path  # Added for modern path handling

import py7zr
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.archive import ArchiveManager

# Import local modules
from core.chdman import CHDManager
from core.file_scanner import FileScanner
from modules.ui_functions import load_svg_icon


class ExtractionTab(QWidget):
    """Extraction tab widget.

    This widget provides a UI for extracting disk images from CHD files.
    """

    def __init__(self, parent=None):
        """Initialize the ExtractionTab widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()

        # Initialize CHD manager
        self.chd_manager = CHDManager()

        # Initialize archive manager
        self.archive_manager = ArchiveManager()

        # Initialize file scanner
        self.file_scanner = FileScanner()

        # Track temporary directories for cleanup
        self.temp_directories = []

        # Track worker (if any) for signal disconnection
        self.worker = None

        # Initialize processing state variables
        self.is_cancelled = False
        self.total_tasks = 0
        self.completed_tasks = 0
        self.current_task_row = None

    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create a splitter for the main sections
        self.main_splitter = QSplitter(Qt.Vertical)

        # Top section - Input/Output selection
        self.top_section = QWidget()
        self.top_layout = QVBoxLayout(self.top_section)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(10)

        # Title
        title_label = QLabel("CHD Extraction")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        self.top_layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Extract disk images from CHD files to various formats. "
            "Choose the output format that best suits your needs."
        )
        desc_label.setWordWrap(True)
        self.top_layout.addWidget(desc_label)

        # Input section
        input_group = QGroupBox("Input")
        input_layout = QVBoxLayout(input_group)

        # Input mode selection
        input_mode_layout = QHBoxLayout()
        input_mode_label = QLabel("Input Mode:")
        self.input_mode_combo = QComboBox()
        self.input_mode_combo.addItems(["Single File", "Directory"])
        input_mode_layout.addWidget(input_mode_label)
        input_mode_layout.addWidget(self.input_mode_combo)
        input_mode_layout.addStretch()
        input_layout.addLayout(input_mode_layout)

        # Input path selection
        input_path_layout = QHBoxLayout()
        input_path_label = QLabel("Input Path:")
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Select input CHD file or directory...")
        self.input_browse_btn = QPushButton("Browse")
        self.input_browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        input_path_layout.addWidget(input_path_label)
        input_path_layout.addWidget(self.input_path_edit)
        input_path_layout.addWidget(self.input_browse_btn)
        input_layout.addLayout(input_path_layout)

        # Include subdirectories
        self.include_subdirs_check = QCheckBox("Include Subdirectories")
        self.include_subdirs_check.setChecked(True)
        input_layout.addWidget(self.include_subdirs_check)

        self.top_layout.addWidget(input_group)

        # Output section
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)

        # Output format
        output_format_layout = QHBoxLayout()
        output_format_label = QLabel("Output Format:")
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(
            ["Raw (bin)", "CD (bin/cue)", "AV (avi)", "Dump Metadata"]
        )
        output_format_layout.addWidget(output_format_label)
        output_format_layout.addWidget(self.output_format_combo)
        output_format_layout.addStretch()
        output_layout.addLayout(output_format_layout)

        # Output directory
        output_dir_layout = QHBoxLayout()
        output_dir_label = QLabel("Output Directory:")
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select output directory...")
        self.output_browse_btn = QPushButton("Browse")
        self.output_browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        output_dir_layout.addWidget(output_dir_label)
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(self.output_browse_btn)
        output_layout.addLayout(output_dir_layout)

        # Use same directory
        self.use_same_dir_check = QCheckBox("Use same directory as input")
        self.use_same_dir_check.setChecked(True)
        output_layout.addWidget(self.use_same_dir_check)

        # Overwrite existing files
        self.overwrite_check = QCheckBox("Overwrite existing files")
        self.overwrite_check.setChecked(False)
        output_layout.addWidget(self.overwrite_check)

        self.top_layout.addWidget(output_group)

        # Extraction options
        options_group = QGroupBox("Extraction Options")
        options_layout = QFormLayout(options_group)

        # Verify after extraction
        self.verify_check = QCheckBox("Verify after extraction")
        self.verify_check.setChecked(True)
        options_layout.addRow("", self.verify_check)

        # Extract metadata only
        self.metadata_only_check = QCheckBox("Extract metadata only")
        self.metadata_only_check.setChecked(False)
        options_layout.addRow("", self.metadata_only_check)

        self.top_layout.addWidget(options_group)

        # Action buttons
        action_layout = QHBoxLayout()

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setIcon(load_svg_icon("search"))
        action_layout.addWidget(self.scan_btn)

        self.extract_btn = QPushButton("Extract")
        self.extract_btn.setIcon(load_svg_icon("file-export"))
        action_layout.addWidget(self.extract_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(load_svg_icon("x"))
        self.cancel_btn.setEnabled(False)  # Disabled by default
        action_layout.addWidget(self.cancel_btn)

        self.top_layout.addLayout(action_layout)

        # Bottom section - File list and progress
        self.bottom_section = QWidget()
        self.bottom_layout = QVBoxLayout(self.bottom_section)
        self.bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_layout.setSpacing(10)

        # Files table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(
            ["File", "Size", "Status", "Progress", "Output"]
        )
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeToContents
        )
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.setSelectionMode(QTableWidget.SingleSelection)
        self.files_table.setAlternatingRowColors(True)
        self.bottom_layout.addWidget(self.files_table)

        # Overall progress
        progress_group = QGroupBox("Overall Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setRange(0, 100)
        self.overall_progress_bar.setValue(0)
        progress_layout.addWidget(self.overall_progress_bar)

        self.progress_label = QLabel("Ready")
        progress_layout.addWidget(self.progress_label)

        self.bottom_layout.addWidget(progress_group)

        # Log section
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        self.bottom_layout.addWidget(log_group)

        # Add sections to splitter
        self.main_splitter.addWidget(self.top_section)
        self.main_splitter.addWidget(self.bottom_section)
        self.main_splitter.setSizes([400, 400])

        # Add splitter to main layout
        layout.addWidget(self.main_splitter)

    def connect_signals(self):
        """Connect widget signals to slots."""
        # Input mode selection
        self.input_mode_combo.currentIndexChanged.connect(self.update_input_mode)

        # Output format selection
        self.output_format_combo.currentIndexChanged.connect(self.update_output_format)

        # Browse buttons
        self.input_browse_btn.clicked.connect(self.browse_input)
        self.output_browse_btn.clicked.connect(self.browse_output)

        # Use same directory checkbox
        self.use_same_dir_check.toggled.connect(self.toggle_output_dir)

        # Metadata only checkbox
        self.metadata_only_check.toggled.connect(self.toggle_metadata_only)

        # Action buttons
        self.scan_btn.clicked.connect(self.scan_files)
        self.extract_btn.clicked.connect(self.start_extraction)
        self.cancel_btn.clicked.connect(self.cancel_extraction)

        # Connect cleanup to close event (if using a custom closeEvent)

    @Slot(int)
    def update_input_mode(self, index):
        """Update the UI based on the selected input mode.

        Args:
            index: Selected index
        """
        # Enable/disable relevant widgets based on mode
        is_directory = index == 1  # Directory mode

        self.include_subdirs_check.setEnabled(is_directory)

    @Slot(int)
    def update_output_format(self, index):
        """Update the UI based on the selected output format.

        Args:
            index: Selected index
        """
        # Enable/disable relevant widgets based on format
        is_metadata = index == 3  # Dump Metadata

        if is_metadata:
            self.metadata_only_check.setChecked(True)
            self.metadata_only_check.setEnabled(False)
        else:
            self.metadata_only_check.setEnabled(True)

    @Slot()
    def browse_input(self):
        """Browse for input file or directory."""
        # Get current mode
        mode = self.input_mode_combo.currentIndex()

        if mode == 0:  # Single file
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Input CHD File", "", "CHD Files (*.chd);;All Files (*.*)"
            )
        else:  # Directory
            path = QFileDialog.getExistingDirectory(self, "Select Input Directory", "")

        if path:
            self.input_path_edit.setText(path)

            # Update output directory if using same directory
            if self.use_same_dir_check.isChecked():
                if os.path.isfile(path):
                    # If a file is selected, set output dir to its parent directory
                    self.output_dir_edit.setText(str(Path(path).parent))
                else:
                    # If a directory is selected, set output dir to that directory
                    self.output_dir_edit.setText(str(Path(path)))

    @Slot()
    def browse_output(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", ""
        )

        if directory:
            output_path = Path(directory)
            self.output_dir_edit.setText(str(output_path))
            self.use_same_dir_check.setChecked(False)

    @Slot(bool)
    def toggle_output_dir(self, checked):
        """Toggle output directory based on checkbox state.

        Args:
            checked: Whether the checkbox is checked
        """
        self.output_dir_edit.setEnabled(not checked)
        self.output_browse_btn.setEnabled(not checked)

        if checked:
            # Set output directory to same as input
            input_path = self.input_path_edit.text()
            if input_path:
                if os.path.isfile(input_path):
                    self.output_dir_edit.setText(os.path.dirname(input_path))
                else:
                    self.output_dir_edit.setText(input_path)

    @Slot(bool)
    def toggle_metadata_only(self, checked):
        """Toggle metadata only mode.

        Args:
            checked: Whether the checkbox is checked
        """
        if checked:
            # If metadata only, force output format to Dump Metadata
            self.output_format_combo.setCurrentIndex(3)

    @Slot()
    def scan_files(self):
        """Scan for files based on the selected input mode."""
        # Get input path
        input_path = self.input_path_edit.text()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Error", "Please select a valid input path.")
            return

        # Get current mode
        mode = self.input_mode_combo.currentIndex()

        # Clear table
        self.files_table.setRowCount(0)

        # Log
        self.log_text.clear()
        self.log(f"Scanning for CHD files in {input_path}...")

        # Scan for files
        if mode == 0:  # Single file
            self.add_file_to_table(input_path)
        else:  # Directory
            # Scan directory
            files = self.file_scanner.scan_directory(
                input_path, ["*.chd"], self.include_subdirs_check.isChecked()
            )

            # Add files to table
            for file in files:
                self.add_file_to_table(file)

        # Log
        self.log(f"Found {self.files_table.rowCount()} CHD files.")

    def add_file_to_table(self, file_path):
        """Add a file to the table.

        Args:
            file_path: Path to the file
        """
        # Get file info
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Format file size
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.2f} KB"
        elif file_size < 1024 * 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{file_size / (1024 * 1024 * 1024):.2f} GB"

        # Add row to table
        row = self.files_table.rowCount()
        self.files_table.insertRow(row)

        # Set file name
        item = QTableWidgetItem(file_name)
        item.setData(Qt.UserRole, file_path)  # Store full path
        self.files_table.setItem(row, 0, item)

        # Set file size
        self.files_table.setItem(row, 1, QTableWidgetItem(size_str))

        # Set status
        self.files_table.setItem(row, 2, QTableWidgetItem("Pending"))

        # Set progress
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        self.files_table.setCellWidget(row, 3, progress_bar)

        # Set output
        self.files_table.setItem(row, 4, QTableWidgetItem(""))

    @Slot()
    def start_extraction(self):
        """Start the extraction process with parallelization, progress,
        and cancellation."""
        if self.files_table.rowCount() == 0:
            QMessageBox.warning(
                self, "Error", "No files to extract. Please scan for files first."
            )
            return

        from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

        class ExtractSignals(QObject):
            progress = Signal(int, int)  # percent, row
            finished = Signal(bool, str, int)  # success, msg, row
            error = Signal(str, int)  # error msg, row

        class CHDExtractWorker(QRunnable):
            def __init__(self, chd_manager, chd_file, output_file, row):
                super().__init__()
                self.chd_manager = chd_manager
                self.chd_file = chd_file
                self.output_file = output_file
                self.row = row
                self.signals = ExtractSignals()
                self._is_cancelled = False

            def run(self):
                try:
                    from core.chdman import CHDTask, CHDTaskType

                    task = CHDTask(
                        task_type=CHDTaskType.EXTRACT,
                        input_file=self.chd_file,
                        output_file=self.output_file,
                        force=True,
                    )
                    self.chd_manager.tasks = [task]

                    # Connect progress signal for this task
                    def on_progress(percent, msg, _):
                        self.signals.progress.emit(int(percent), self.row)

                    self.chd_manager.signals.progress_updated.connect(on_progress)
                    # Execute extraction
                    self.chd_manager.execute_all_tasks()
                    self.chd_manager.signals.progress_updated.disconnect(on_progress)
                    self.signals.finished.emit(True, "Extracted", self.row)
                except Exception as e:
                    self.signals.error.emit(str(e), self.row)
                    self.signals.finished.emit(
                        False, f"Extraction Failed: {e}", self.row
                    )

        self.is_cancelled = False
        self.completed_tasks = 0
        self.total_tasks = self.files_table.rowCount()
        self.progress_label.setText("Starting extraction...")
        self.overall_progress_bar.setValue(0)

        files_to_extract = []
        temp_dirs = []

        # Gather files from the table
        for row in range(self.files_table.rowCount()):
            file_item = self.files_table.item(row, 0)
            file_path = file_item.data(Qt.UserRole) if file_item else None
            if not file_path or not os.path.exists(file_path):
                self.files_table.setItem(row, 2, QTableWidgetItem("File Missing"))
                continue

            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".chd":
                files_to_extract.append((file_path, row))
            elif ext in [".zip", ".7z"]:
                temp_dir = os.path.join(
                    os.path.dirname(file_path),
                    f"temp_extract_{os.path.basename(file_path)}",
                )
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir, exist_ok=True)
                self.temp_directories.append(temp_dir)
                temp_dirs.append(temp_dir)
                self.files_table.setItem(row, 2, QTableWidgetItem("Extracting Archive"))
                try:
                    extracted_files = self.archive_manager.extract_archive(
                        file_path, temp_dir
                    )
                    chd_files = [
                        f for f in extracted_files if f.lower().endswith(".chd")
                    ]
                    if not chd_files:
                        self.files_table.setItem(
                            row, 2, QTableWidgetItem("No CHD in Archive")
                        )
                        continue
                    for chd_file in chd_files:
                        files_to_extract.append((chd_file, row))
                except Exception as e:
                    self.files_table.setItem(
                        row, 2, QTableWidgetItem(f"Archive Error: {e}")
                    )
                    self.log(f"Error extracting archive {file_path}: {e}")
                    continue
            else:
                self.files_table.setItem(row, 2, QTableWidgetItem("Unsupported File"))
                continue

        if not files_to_extract:
            self.progress_label.setText("No valid files to extract.")
            return

        self._active_workers = []
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(2)
        self._finished_count = 0

        def on_worker_progress(percent, row):
            progress_bar = self.files_table.cellWidget(row, 3)
            if progress_bar:
                progress_bar.setValue(percent)

        def on_worker_finished(success, msg, row):
            self._finished_count += 1
            if success:
                self.files_table.setItem(row, 2, QTableWidgetItem("Extracted"))
            else:
                self.files_table.setItem(row, 2, QTableWidgetItem(msg))
            progress = int(100 * self._finished_count / len(files_to_extract))
            self.overall_progress_bar.setValue(progress)
            self.progress_label.setText(
                f"Extracted {self._finished_count}/{len(files_to_extract)}"
            )
            if self._finished_count == len(files_to_extract):
                self.cleanup_temp_directories(temp_dirs)
                self.progress_label.setText("Extraction complete.")
                self.log("Extraction process finished.")

        def on_worker_error(msg, row):
            self.files_table.setItem(
                row, 2, QTableWidgetItem(f"Extraction Failed: {msg}")
            )
            self.log(f"Extraction error on row {row}: {msg}")

        # Start extraction workers
        for chd_file, row in files_to_extract:
            if self.is_cancelled:
                self.files_table.setItem(row, 2, QTableWidgetItem("Cancelled"))
                continue
            output_dir = self.output_dir_edit.text()
            if self.use_same_dir_check.isChecked():
                input_path = self.input_path_edit.text()
                if os.path.isfile(input_path):
                    output_dir = os.path.dirname(input_path)
                else:
                    output_dir = input_path
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(
                output_dir, os.path.splitext(os.path.basename(chd_file))[0] + ".img"
            )
            worker = CHDExtractWorker(self.chd_manager, chd_file, output_file, row)
            worker.signals.progress.connect(on_worker_progress)
            worker.signals.finished.connect(on_worker_finished)
            worker.signals.error.connect(on_worker_error)
            self._active_workers.append(worker)
            self._thread_pool.start(worker)

    @Slot()
    def cancel_extraction(self):
        """Cancel the extraction process."""
        self.is_cancelled = True
        if hasattr(self, "chd_manager") and self.chd_manager is not None:
            try:
                self.chd_manager.terminate_all_chdman_processes()
            except Exception as e:
                logging.warning(f"Exception terminating all chdman processes: {e}")
        for worker in getattr(self, "_active_workers", []):
            if hasattr(worker, "_is_cancelled"):
                worker._is_cancelled = True
        self.progress_label.setText("Extraction cancelled.")
        for row in range(self.files_table.rowCount()):
            status_item = self.files_table.item(row, 2)
            if status_item and status_item.text() not in (
                "Extracted",
                "Extraction Failed",
            ):
                self.files_table.setItem(row, 2, QTableWidgetItem("Cancelled"))

    def cleanup_temp_directories(self, temp_dirs=None):
        """Clean up temporary directories created during processing.

        Args:
            temp_dirs: List of temporary directories to clean up. If None,
                uses self.temp_directories. This parameter allows for
                specifying a custom list of directories to clean up.
        """
        if temp_dirs is None:
            temp_dirs = self.temp_directories[:]
        for temp_dir in temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    import shutil

                    shutil.rmtree(temp_dir, ignore_errors=True)
                if temp_dir in self.temp_directories:
                    self.temp_directories.remove(temp_dir)
            except Exception as e:
                self.log(f"Error cleaning up temporary directory {temp_dir}: {e}")

    def closeEvent(self, event):
        """Ensure all resources are cleaned up on close."""
        self.cleanup_temp_directories()
        # Disconnect worker signals if any
        try:
            if hasattr(self, "worker") and self.worker is not None:
                self.worker.finished.disconnect()
                self.worker = None
        except Exception as e:
            logging.warning(
                f"Exception disconnecting worker: {e}"
            )  # Already disconnected or not set
        event.accept()

    def on_archive_progress(self, value, message, row):
        """Handle archive extraction progress.

        Args:
            value: Progress value (0-100)
            message: Progress message
            row: Table row index
        """
        # Update progress bar (scale to 0-50 to leave room for CHD extraction)
        progress_bar = self.files_table.cellWidget(row, 3)
        if progress_bar:
            progress_bar.setValue(int(value / 2))

        # Log if message is provided
        if message:
            self.log(f"[Archive] {message}")

    def on_archive_error(self, message, row):
        """Handle archive extraction error.

        Args:
            message: Error message
            row: Table row index
        """
        # Update status
        self.files_table.setItem(row, 2, QTableWidgetItem("Extraction Failed"))

        # Log
        error_message = f"Archive Error: {message}"
        self.log(error_message)

    def on_archive_finished(
        self, success, message, path, row, completion_flag, success_flag, path_container
    ):
        """Handle archive extraction completion.

        Args:
            success: Whether extraction was successful
            message: Completion message
            path: Path to extracted files
            row: Table row index
            completion_flag: List with a boolean flag to indicate completion
            success_flag: List with a boolean flag to indicate success
            path_container: List to store the extracted path
        """
        # Log
        self.log(f"[Archive] {message}")

        # Update flags
        success_flag[0] = success
        path_container[0] = path
        completion_flag[0] = True

    def check_archive_compatibility(self, archive_path, row):
        """Check if an archive potentially contains CHD files.

        Args:
            archive_path: Path to the archive file
            row: Table row index

        Returns:
            Boolean indicating if the archive might contain CHD files
        """
        self.log(f"Checking archive compatibility: {archive_path}")
        self.files_table.setItem(row, 2, QTableWidgetItem("Checking compatibility"))

        try:
            # Get the list of files in the archive without extracting
            file_list = []

            # Handle different archive types
            ext = os.path.splitext(archive_path)[1].lower()

            if ext == ".zip":
                # List files in ZIP archive
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    file_list = zip_ref.namelist()
            elif ext == ".7z":
                # List files in 7z archive
                with py7zr.SevenZipFile(archive_path, mode="r") as z:
                    file_list = z.getnames()
            else:
                # For other archive types, we can't easily check without extracting
                # So we'll assume it might contain compatible files
                self.log(
                    f"Cannot check compatibility for {ext} archives without extracting."
                )
                self.log("Will attempt extraction.")
                return True

            # Check if any files in the archive have .chd extension
            for file_path in file_list:
                if file_path.lower().endswith(".chd"):
                    self.log(f"Found CHD file in archive: {file_path}")
                    return True

            # No CHD files found
            self.log(f"No CHD files found in archive: {archive_path}")
            return False

        except Exception as e:
            # If there's an error checking the archive, we'll try extracting it anyway
            self.log(
                f"Error checking archive compatibility: {str(e)}. "
                "Will attempt extraction."
            )
            return True
