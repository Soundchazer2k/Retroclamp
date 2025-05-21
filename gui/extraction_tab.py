"""Extraction tab for RetroClamp.

This module provides the UI and functionality for extracting disk images
from CHD files using the CHDMAN utility.
"""

import os
import zipfile
import py7zr
import shutil
from PySide6.QtWidgets import QApplication

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QCheckBox, QGroupBox, QFormLayout,
    QProgressBar, QSplitter, QPlainTextEdit
)

# Import local modules
from core.chdman import CHDManager, CHDTask, CHDTaskType, CHDManError
from core.file_scanner import FileScanner
from core.archive import ArchiveManager
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
        self.output_format_combo.addItems(["Raw (bin)", "CD (bin/cue)", "AV (avi)", "Dump Metadata"])
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
        self.files_table.setHorizontalHeaderLabels(["File", "Size", "Status", "Progress", "Output"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
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
                self,
                "Select Input CHD File",
                "",
                "CHD Files (*.chd);;All Files (*.*)"
            )
        else:  # Directory
            path = QFileDialog.getExistingDirectory(
                self,
                "Select Input Directory",
                ""
            )
        
        if path:
            self.input_path_edit.setText(path)
            
            # Update output directory if using same directory
            if self.use_same_dir_check.isChecked():
                if os.path.isfile(path):
                    self.output_dir_edit.setText(os.path.dirname(path))
                else:
                    self.output_dir_edit.setText(path)
    
    @Slot()
    def browse_output(self):
        """Browse for output directory."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            ""
        )
        
        if path:
            self.output_dir_edit.setText(path)
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
                input_path,
                ["*.chd"],
                self.include_subdirs_check.isChecked()
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
        """Start the extraction process."""
        # Check if there are files to extract
        if self.files_table.rowCount() == 0:
            QMessageBox.warning(self, "Error", "No files to extract. Please scan for files first.")
            return
        
        # Get output directory
        if self.use_same_dir_check.isChecked():
            input_path = self.input_path_edit.text()
            if os.path.isfile(input_path):
                output_dir = os.path.dirname(input_path)
            else:
                output_dir = input_path
        else:
            output_dir = self.output_dir_edit.text()
        
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "Error", "Please select a valid output directory.")
            return
        
        # Get extraction options
        output_format = self.output_format_combo.currentIndex()
        verify = self.verify_check.isChecked()
        # Note: metadata_only is determined by the output format
        # If output_format is 3 (Dump Metadata), metadata_only is implicitly true
        overwrite = self.overwrite_check.isChecked()
        
        # Determine task type based on output format
        if output_format == 0:  # Raw (bin)
            task_type = CHDTaskType.EXTRACT_RAW
            extension = ".bin"
        elif output_format == 1:  # CD (bin/cue)
            task_type = CHDTaskType.EXTRACT_CD
            extension = ".bin"  # Will also create .cue
        elif output_format == 2:  # AV (avi)
            task_type = CHDTaskType.EXTRACT_AV
            extension = ".avi"
        else:  # Dump Metadata
            task_type = CHDTaskType.DUMP_META
            extension = ".meta"
        
        # Create tasks
        tasks = []
        for row in range(self.files_table.rowCount()):
            # Get file path
            file_item = self.files_table.item(row, 0)
            file_path = file_item.data(Qt.UserRole)
            
            # Create output path
            file_name = os.path.basename(file_path)
            base_name, _ = os.path.splitext(file_name)
            output_path = os.path.join(output_dir, f"{base_name}{extension}")
            
            # Check if output file exists
            if os.path.exists(output_path) and not overwrite:
                # Update status
                self.files_table.setItem(row, 2, QTableWidgetItem("Skipped (exists)"))
                continue
            
            # Create task
            task = CHDTask(
                task_type=task_type,
                input_file=file_path,
                output_file=output_path,
                verify=verify
            )
            
            # Add task
            tasks.append((task, row))
            
            # Update status
            self.files_table.setItem(row, 2, QTableWidgetItem("Queued"))
            
            # Update output
            self.files_table.setItem(row, 4, QTableWidgetItem(output_path))
        
        # Check if there are tasks to process
        if not tasks:
            QMessageBox.information(self, "Information", "No files to extract. All files already exist.")
            return
        
        # Log
        self.log(f"Starting extraction of {len(tasks)} files...")
        
        # Update UI
        self.scan_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # Disable input controls during extraction
        self.input_mode_combo.setEnabled(False)
        self.input_path_edit.setEnabled(False)
        self.input_browse_btn.setEnabled(False)
        self.include_subdirs_check.setEnabled(False)
        self.output_format_combo.setEnabled(False)
        self.output_dir_edit.setEnabled(False)
        self.output_browse_btn.setEnabled(False)
        self.use_same_dir_check.setEnabled(False)
        self.verify_check.setEnabled(False)
        self.metadata_only_check.setEnabled(False)
        self.overwrite_check.setEnabled(False)
        
        # Reset progress indicators
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setMaximum(len(tasks))
        self.progress_label.setText(f"Processing 0/{len(tasks)} files...")
        
        # Process tasks
        self.process_tasks(tasks)
    
    def process_tasks(self, tasks):
        """Process extraction tasks.
        
        Args:
            tasks: List of (task, row) tuples
        """
        # Clear the CHD manager's task queue
        self.chd_manager.clear_tasks()
        
        # Initialize variables for tracking progress
        self.total_tasks = len(tasks)
        self.completed_tasks = 0
        self.current_task_row = None
        self.is_cancelled = False
        
        # Update UI for processing state
        self.cancel_btn.setEnabled(True)
        
        # Log
        self.log("Extraction started.")
        
        # Process each task sequentially
        for task, row in tasks:
            # Check if cancelled
            if self.is_cancelled:
                # Mark remaining tasks as cancelled
                self.files_table.setItem(row, 2, QTableWidgetItem("Cancelled"))
                continue
                
            try:
                # Update status
                self.files_table.setItem(row, 2, QTableWidgetItem("Processing"))
                self.current_task_row = row
                
                # Get progress bar
                progress_bar = self.files_table.cellWidget(row, 3)
                
                # Check if the input file is an archive
                input_file = task.input_file
                temp_dir = None
                is_archive = self.archive_manager.is_archive(input_file)
                
                if is_archive:
                    # First, check if the archive potentially contains CHD files
                    compatible = self.check_archive_compatibility(input_file, row)
                    
                    if not compatible:
                        # Skip this task if the archive doesn't seem to contain CHD files
                        self.log(f"Skipping archive as it doesn't appear to contain CHD files: {input_file}")
                        self.files_table.setItem(row, 2, QTableWidgetItem("Skipped (incompatible)"))
                        continue
                    
                    # Extract the archive
                    success, temp_dir, chd_files = self.extract_archive(input_file, row)
                    
                    if not success or not chd_files:
                        # Skip this task if extraction failed or no CHD files found
                        continue
                    
                    # Update the task with the first CHD file found
                    task.input_file = chd_files[0]
                    
                    # Log the CHD file being processed
                    self.log(f"Processing CHD file from archive: {os.path.basename(task.input_file)}")
                    
                    # If there are multiple CHD files, log them
                    if len(chd_files) > 1:
                        self.log(f"Note: {len(chd_files) - 1} additional CHD files found in archive but not processed.")
                
                # Add task to CHD manager
                self.chd_manager.clear_tasks()  # Clear previous tasks
                self.chd_manager.add_task(task)
                
                # Execute task and get signals
                try:
                    signals = self.chd_manager.execute_task(task)
                    
                    # Connect signals
                    signals.started.connect(lambda msg, r=row: self.on_task_started(msg, r))
                    signals.progress.connect(lambda value, msg, r=row: self.on_task_progress(value, msg, r))
                    signals.finished.connect(lambda success, msg, r=row: self.on_task_finished(success, msg, r))
                    signals.error.connect(lambda msg, r=row: self.on_task_error(msg, r))
                    
                    # Wait for task to complete (this is blocking, but we're processing sequentially)
                    # In a future version, we could use QThreadPool to process tasks in parallel
                    max_wait_iterations = 1000  # Prevent infinite loop
                    wait_iterations = 0
                    
                    while (wait_iterations < max_wait_iterations and
                           not self.is_cancelled and
                           progress_bar.value() < 100 and
                           self.files_table.item(row, 2).text() != "Completed" and
                           self.files_table.item(row, 2).text() != "Failed"):
                        QApplication.processEvents()  # Allow UI updates
                        wait_iterations += 1
                    
                except CHDManError as e:
                    # Handle specific CHDManError exceptions
                    error_message = f"CHDMan error: {str(e)}"
                    self.on_task_error(error_message, row)
                except Exception as e:
                    # Handle any other exceptions from task execution
                    self.on_task_error(str(e), row)
                    
                # Clean up temporary directory if we extracted an archive
                if is_archive and temp_dir and os.path.exists(temp_dir):
                    try:
                        self.log(f"Cleaning up temporary files in {temp_dir}")
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        self.log(f"Warning: Failed to clean up temporary directory: {str(e)}")
                
            except Exception as e:
                # Handle any other exceptions
                error_message = f"Error processing task: {str(e)}"
                self.log(error_message)
                self.files_table.setItem(row, 2, QTableWidgetItem("Failed"))
                
                # Update progress bar to show failure
                progress_bar = self.files_table.cellWidget(row, 3)
                if progress_bar:
                    progress_bar.setValue(0)  # Reset progress bar on failure
            
            # Update overall progress
            self.completed_tasks += 1
            self.overall_progress_bar.setValue(self.completed_tasks)
            self.progress_label.setText(f"Processing {self.completed_tasks}/{self.total_tasks} files...")
        
        # Re-enable UI controls
        self.scan_btn.setEnabled(True)
        self.extract_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        # Re-enable input controls
        self.input_mode_combo.setEnabled(True)
        self.input_path_edit.setEnabled(True)
        self.input_browse_btn.setEnabled(True)
        self.include_subdirs_check.setEnabled(self.input_mode_combo.currentIndex() == 1)  # Only if directory mode
        self.output_format_combo.setEnabled(True)
        self.output_dir_edit.setEnabled(not self.use_same_dir_check.isChecked())
        self.output_browse_btn.setEnabled(not self.use_same_dir_check.isChecked())
        self.use_same_dir_check.setEnabled(True)
        self.verify_check.setEnabled(True)
        self.metadata_only_check.setEnabled(self.output_format_combo.currentIndex() != 3)  # Not if metadata mode
        self.overwrite_check.setEnabled(True)
        
        # Update progress label
        if self.is_cancelled:
            self.progress_label.setText(f"Cancelled after {self.completed_tasks}/{self.total_tasks} files.")
            self.log("Extraction cancelled.")
        else:
            self.progress_label.setText(f"Completed {self.completed_tasks}/{self.total_tasks} files.")
            self.log("Extraction completed.")
    
    def log(self, message):
        """Add a message to the log.
        
        Args:
            message: Message to add
        """
        self.log_text.appendPlainText(message)
    
    def on_task_started(self, message, row):
        """Handle task started signal.
        
        Args:
            message: Start message
            row: Table row index
        """
        # Update status
        self.files_table.setItem(row, 2, QTableWidgetItem("Processing"))
        
        # Log
        self.log(message)
    
    def on_task_progress(self, value, message, row):
        """Handle task progress signal.
        
        Args:
            value: Progress value (0-100)
            message: Progress message
            row: Table row index
        """
        # Update progress bar
        progress_bar = self.files_table.cellWidget(row, 3)
        if progress_bar:
            progress_bar.setValue(value)
        
        # Log if message is provided
        if message:
            self.log(message)
    
    def on_task_finished(self, success, message, row):
        """Handle task finished signal.
        
        Args:
            success: Whether the task was successful
            message: Completion message
            row: Table row index
        """
        # Update status
        if success:
            self.files_table.setItem(row, 2, QTableWidgetItem("Completed"))
            # Set progress to 100% if not already
            progress_bar = self.files_table.cellWidget(row, 3)
            if progress_bar and progress_bar.value() < 100:
                progress_bar.setValue(100)
        else:
            self.files_table.setItem(row, 2, QTableWidgetItem("Failed"))
        
        # Log
        self.log(message)
    
    def on_task_error(self, message, row):
        """Handle task error signal.
        
        Args:
            message: Error message
            row: Table row index
        """
        # Update status
        self.files_table.setItem(row, 2, QTableWidgetItem("Failed"))
        
        # Log
        error_message = f"Error: {message}"
        self.log(error_message)
    
    def extract_archive(self, archive_path, row):
        """Extract an archive file before processing with CHDMAN.
        
        Args:
            archive_path: Path to the archive file
            row: Table row index
            
        Returns:
            Tuple of (success, extracted_path, files_to_process)
        """
        # Create a temporary directory for extraction
        temp_dir = os.path.join(os.path.dirname(archive_path), f"temp_extract_{os.path.basename(archive_path)}")
        
        # Update status
        self.files_table.setItem(row, 2, QTableWidgetItem("Extracting"))
        self.log(f"Extracting archive: {archive_path}")
        
        try:
            # Extract the archive
            signals = self.archive_manager.extract(archive_path, temp_dir)
            
            # Connect signals
            signals.started.connect(lambda msg: self.log(f"[Archive] {msg}"))
            signals.progress.connect(lambda value, msg: self.on_archive_progress(value, msg, row))
            signals.error.connect(lambda msg: self.on_archive_error(msg, row))
            
            # Wait for extraction to complete
            extraction_complete = [False]  # Use a list to make it mutable in closures
            extraction_success = [False]
            extracted_path = [None]
            
            # Connect finished signal with a lambda that captures the results
            signals.finished.connect(
                lambda success, msg, path: self.on_archive_finished(success, msg, path, row, extraction_complete, extraction_success, extracted_path)
            )
            
            # Wait for extraction to complete
            while not extraction_complete[0]:
                QApplication.processEvents()
            
            if not extraction_success[0]:
                return False, None, []
            
            # Find all CHD files in the extracted directory
            chd_files = []
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Check if file is a CHD file
                    if file.lower().endswith(".chd"):
                        chd_files.append(file_path)
            
            if not chd_files:
                self.log(f"No CHD files found in archive: {archive_path}")
                return False, temp_dir, []
            
            return True, temp_dir, chd_files
            
        except Exception as e:
            self.log(f"Error extracting archive: {str(e)}")
            self.files_table.setItem(row, 2, QTableWidgetItem("Extraction Failed"))
            return False, None, []
    
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
    
    def on_archive_finished(self, success, message, path, row, completion_flag, success_flag, path_container):
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
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
            elif ext == ".7z":
                # List files in 7z archive
                with py7zr.SevenZipFile(archive_path, mode='r') as z:
                    file_list = z.getnames()
            else:
                # For other archive types, we can't easily check without extracting
                # So we'll assume it might contain compatible files
                self.log(f"Cannot check compatibility for {ext} archives without extracting. Will attempt extraction.")
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
            self.log(f"Error checking archive compatibility: {str(e)}. Will attempt extraction.")
            return True
    
    @Slot()
    def cancel_extraction(self):
        """Cancel the extraction process."""
        if self.current_task_row is not None:
            # Set cancelled flag
            self.is_cancelled = True
            
            # Try to cancel the current task
            try:
                self.chd_manager.cancel_task()
                self.log("Cancelling extraction... Please wait for current task to finish.")
                
                # Update status of current task
                self.files_table.setItem(self.current_task_row, 2, QTableWidgetItem("Cancelling"))
                
                # Disable cancel button to prevent multiple clicks
                self.cancel_btn.setEnabled(False)
            except Exception as e:
                self.log(f"Error cancelling task: {str(e)}")
                # Still set cancelled flag to prevent new tasks from starting
                self.is_cancelled = True
