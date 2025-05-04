"""Extraction tab for RetroClamp.

This module provides the UI and functionality for extracting disk images
from CHD files using the CHDMAN utility.
"""

import os
import sys
from typing import List, Dict, Any, Optional, Tuple

from PySide6.QtCore import Qt, Signal, Slot, QSize, QThread, QRunnable, QThreadPool
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QCheckBox, QGroupBox, QFormLayout,
    QProgressBar, QSpinBox, QDoubleSpinBox, QTabWidget, QSplitter,
    QTextEdit, QPlainTextEdit, QScrollArea, QFrame
)

# Import local modules
from core.chdman import CHDManager, CHDTask, CHDTaskType
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
        
        # Initialize file scanner
        self.file_scanner = FileScanner()
    
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
        action_layout.addStretch()
        
        self.scan_btn = QPushButton("Scan for Files")
        self.scan_btn.setIcon(load_svg_icon("search", 16, "#f8f8f2"))
        self.scan_btn.setMinimumWidth(150)
        action_layout.addWidget(self.scan_btn)
        
        self.extract_btn = QPushButton("Start Extraction")
        self.extract_btn.setIcon(load_svg_icon("file-export", 16, "#f8f8f2"))
        self.extract_btn.setMinimumWidth(150)
        action_layout.addWidget(self.extract_btn)
        
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
        metadata_only = self.metadata_only_check.isChecked()
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
        # TODO: Implement task processing with QThreadPool
        # For now, just simulate processing
        
        # Log
        self.log("Extraction started.")
        
        # Update UI when done
        self.scan_btn.setEnabled(True)
        self.extract_btn.setEnabled(True)
        self.overall_progress_bar.setValue(len(tasks))
        self.progress_label.setText(f"Completed {len(tasks)}/{len(tasks)} files.")
        
        # Log
        self.log("Extraction completed.")
    
    def log(self, message):
        """Add a message to the log.
        
        Args:
            message: Message to add
        """
        self.log_text.appendPlainText(message)
