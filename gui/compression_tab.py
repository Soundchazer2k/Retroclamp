"""Compression tab for RetroClamp.

This module provides the UI and functionality for compressing disk images
using the CHDMAN utility.
"""

import os
import tempfile
import time
import shutil
import traceback
import zipfile
import py7zr

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QFileDialog, QMessageBox, QGroupBox, QFormLayout,
    QPlainTextEdit, QApplication
)

# Import local modules
from core.chdman import CHDManager, CHDTask, CHDTaskType
from core.file_scanner import FileScanner
from core.archive import ArchiveManager
from modules.ui_functions import load_svg_icon


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
        self.setup_ui()
        self.connect_signals()
        
        # Initialize CHD manager
        self.chd_manager = CHDManager()
        
        # Initialize archive manager
        self.archive_manager = ArchiveManager()
        
        # Initialize file scanner
        self.file_scanner = FileScanner()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        title_label = QLabel("Single File Compression")
        title_label.setObjectName("pageTitle")
        font = title_label.font()
        font.setPointSize(16)
        font.setBold(True)
        title_label.setFont(font)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Info text
        info_label = QLabel("This tab is for compressing a single disk image file. For batch processing of multiple files or directories, use the Batch tab.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Input section
        input_group = QGroupBox("Input")
        input_layout = QVBoxLayout(input_group)
        
        # Input path selection
        input_path_layout = QHBoxLayout()
        input_path_label = QLabel("Input File:")
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Select input file...")
        self.input_browse_btn = QPushButton("Browse")
        self.input_browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        input_path_layout.addWidget(input_path_label)
        input_path_layout.addWidget(self.input_path_edit)
        input_path_layout.addWidget(self.input_browse_btn)
        input_layout.addLayout(input_path_layout)
        
        layout.addWidget(input_group)
        
        # Output section
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        
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
        
        layout.addWidget(output_group)
        
        # Compression options
        options_group = QGroupBox("Compression Options")
        options_layout = QFormLayout(options_group)
        
        # Media type selection
        self.media_type_layout = QHBoxLayout()
        self.media_type_label = QLabel("Media Type:")
        self.media_type_combo = QComboBox()
        self.media_type_combo.addItems(["Auto-detect", "CD", "DVD", "Hard Disk"])
        self.media_type_combo.setCurrentText("Auto-detect")
        self.media_type_combo.setToolTip("Auto-detect will determine the media type based on file size and extension")
        self.media_type_combo.currentTextChanged.connect(self.update_recommended_settings)
        self.detected_type_label = QLabel("")
        self.detected_type_label.setStyleSheet("color: #6272a4; font-style: italic;")
        self.media_type_layout.addWidget(self.media_type_label)
        self.media_type_layout.addWidget(self.media_type_combo)
        self.media_type_layout.addWidget(self.detected_type_label)
        options_layout.addRow("", self.media_type_layout)
        
        # Compression level
        self.compression_level_combo = QComboBox()
        self.compression_level_combo.addItems(["None", "Fast", "Normal", "Best"])
        self.compression_level_combo.setCurrentText("Normal")
        self.compression_level_combo.currentTextChanged.connect(self.update_recommended_settings)
        options_layout.addRow("Compression Level:", self.compression_level_combo)
        
        # Hunk size
        self.hunk_size_combo = QComboBox()
        # Include multiples of CD sector size (2448 bytes)
        self.hunk_size_combo.addItems(["2 KB", "4 KB", "9.8 KB", "19.6 KB", "32 KB", "64 KB"])
        # 9.8 KB (2448*4) is the recommended default for CD images
        self.hunk_size_combo.setCurrentText("9.8 KB")
        self.hunk_size_combo.setToolTip("Recommended: 9.8 KB for CDs (multiple of 2448 bytes), 2 KB for DVDs/PSP, 4 KB for hard disk images")
        options_layout.addRow("Hunk Size:", self.hunk_size_combo)
        
        # Verify after compression
        self.verify_check = QCheckBox("Verify after compression")
        self.verify_check.setChecked(True)
        options_layout.addRow("", self.verify_check)
        
        # Force compression
        self.force_check = QCheckBox("Force compression even if larger")
        self.force_check.setChecked(False)
        options_layout.addRow("", self.force_check)
        
        layout.addWidget(options_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.scan_btn = QPushButton("Scan for Files")
        self.scan_btn.setIcon(load_svg_icon("search", 20, "#f8f8f2"))
        self.scan_btn.setMinimumHeight(36)
        self.scan_btn.setVisible(False)  # Hide scan button in single file mode
        
        self.compress_btn = QPushButton("Compress File")
        self.compress_btn.setIcon(load_svg_icon("player-play", 20, "#f8f8f2"))
        self.compress_btn.setMinimumHeight(36)
        self.compress_btn.setMinimumWidth(150)
        action_layout.addWidget(self.compress_btn)
        
        layout.addLayout(action_layout)
        
        # File list and progress section
        file_section = QWidget()
        file_layout = QVBoxLayout(file_section)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(10)
        
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
        file_layout.addWidget(self.files_table)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Overall progress
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setMinimum(0)
        self.overall_progress_bar.setMaximum(100)
        self.overall_progress_bar.setValue(0)
        self.progress_label = QLabel("Ready")
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.overall_progress_bar)
        
        file_layout.addWidget(progress_group)
        
        # Log section
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)  # Limit to avoid memory issues
        
        log_layout.addWidget(self.log_text)
        
        file_layout.addWidget(log_group)
        
        # Add file section to main layout
        layout.addWidget(file_section)
    
    def connect_signals(self):
        """Connect widget signals to slots."""
        # Input/output buttons
        self.input_browse_btn.clicked.connect(self.browse_input)
        self.output_browse_btn.clicked.connect(self.browse_output)
        
        # Use same directory checkbox
        self.use_same_dir_check.toggled.connect(self.toggle_output_dir)
        
        # Media type and compression options
        self.input_path_edit.textChanged.connect(self.update_recommended_settings)
        
        # Action buttons
        self.compress_btn.clicked.connect(self.start_compression)
    
    def update_recommended_settings(self):
        """Update recommended settings based on the selected file and media type."""
        # Get the input file path
        file_path = self.input_path_edit.text()
        
        # Only proceed if we have a valid file
        if not file_path or not os.path.exists(file_path) or not os.path.isfile(file_path):
            self.detected_type_label.setText("")
            return
            
        # Detect media type if set to auto-detect
        if self.media_type_combo.currentText() == "Auto-detect":
            detected_type = self.detect_media_type(file_path)
            if detected_type:
                self.detected_type_label.setText(f"(Detected: {detected_type})")
                
                # Set recommended hunk size based on media type
                if detected_type == "CD":
                    # For CDs, use a multiple of 2448 (CD sector size)
                    self.hunk_size_combo.setCurrentText("9.8 KB")
                elif detected_type == "DVD":
                    # For DVDs, use 2 KB (2048 bytes)
                    self.hunk_size_combo.setCurrentText("2 KB")
                else:  # Hard Disk
                    # For hard disks, use 4 KB
                    self.hunk_size_combo.setCurrentText("4 KB")
        else:
            # User has manually selected a media type
            self.detected_type_label.setText("")
            
            # Set recommended hunk size based on selected media type
            selected_type = self.media_type_combo.currentText()
            if selected_type == "CD":
                # For CDs, use a multiple of 2448 (CD sector size)
                self.hunk_size_combo.setCurrentText("9.8 KB")
            elif selected_type == "DVD":
                # For DVDs, use 2 KB (2048 bytes)
                self.hunk_size_combo.setCurrentText("2 KB")
            elif selected_type == "Hard Disk":
                # For hard disks, use 4 KB
                self.hunk_size_combo.setCurrentText("4 KB")
    
    def check_archive_compatibility(self, archive_path, row_index):
        """Check if an archive contains compatible disk images.
        
        Args:
            archive_path: Path to the archive file
            row_index: Row index in the table (-1 if not in table yet)
            
        Returns:
            True if the archive contains compatible disk images, False otherwise
        """
        try:
            # Create a temporary directory for extraction
            temp_dir = os.path.join(tempfile.gettempdir(), f"retroclamp_{os.getpid()}_{int(time.time())}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Log
            self.log(f"Checking archive: {archive_path}")
            
            # Extract archive to temporary directory
            signals = self.archive_manager.extract(archive_path, temp_dir)
            
            # Connect signals
            signals.started.connect(lambda msg: self.log(f"Archive check started: {msg}"))
            signals.error.connect(lambda msg: self.log(f"Archive check error: {msg}"))
            
            # Wait for extraction to complete (this is just for checking, not the full extraction)
            # In a real application, this should be done asynchronously
            # For simplicity, we're using a blocking approach here
            time.sleep(1)  # Give it a moment to start
            
            # Check if the archive contains compatible disk images
            compatible_extensions = [".iso", ".bin", ".img", ".cue"]
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in compatible_extensions:
                        # Clean up temporary directory
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return True
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
            
        except Exception as e:
            self.log(f"Error checking archive compatibility: {str(e)}")
            self.log(traceback.format_exc())
            return False
    
    def extract_archive(self, archive_path, row_index):
        """Extract an archive file.
        
        Args:
            archive_path: Path to the archive file
            row_index: Row index in the table (-1 if not in table yet)
            
        Returns:
            Tuple of (success, temp_dir, disk_images)
        """
        try:
            # Create a temporary directory for extraction
            temp_dir = os.path.join(tempfile.gettempdir(), f"retroclamp_{os.getpid()}_{int(time.time())}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Log
            self.log(f"Extracting archive: {archive_path} to {temp_dir}")
            
            # Update status if row exists
            if row_index >= 0:
                self.files_table.setItem(row_index, 2, QTableWidgetItem("Extracting..."))
            
            # Extract archive to temporary directory
            signals = self.archive_manager.extract(archive_path, temp_dir)
            
            # Connect signals
            signals.started.connect(lambda msg: self.log(f"Extraction started: {msg}"))
            signals.progress.connect(lambda pct, msg: self.log(f"Extraction progress: {pct}% - {msg}"))
            signals.error.connect(lambda msg: self.log(f"Extraction error: {msg}"))
            signals.finished.connect(lambda success, msg, path: self.log(f"Extraction finished: {msg}"))
            
            # Wait for extraction to complete
            # In a real application, this should be done asynchronously
            # For simplicity, we're using a blocking approach here
            time.sleep(2)  # Give it a moment to extract
            
            # Find disk images in the extracted files
            disk_images = []
            compatible_extensions = [".iso", ".bin", ".img", ".cue"]
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    ext = os.path.splitext(file)[1].lower()
                    if ext in compatible_extensions:
                        disk_images.append(file_path)
            
            if disk_images:
                self.log(f"Found {len(disk_images)} disk images in archive")
                return True, temp_dir, disk_images
            else:
                self.log("No disk images found in archive")
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, None, []
                
        except Exception as e:
            self.log(f"Error extracting archive: {str(e)}")
            self.log(traceback.format_exc())
            return False, None, []
    
    @Slot()
    def browse_input(self):
        """Browse for input file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input File",
            "",
            "Disk Images & Archives (*.iso;*.bin;*.img;*.cue;*.zip;*.7z;*.rar);;Disk Images (*.iso;*.bin;*.img;*.cue);;Archives (*.zip;*.7z;*.rar);;All Files (*.*)",
        )
        
        if not path:
            return
            
        self.input_path_edit.setText(path)
        
        # Update output directory if using same directory
        if self.use_same_dir_check.isChecked():
            self.output_dir_edit.setText(os.path.dirname(path))
        
        # Clear the table first
        self.files_table.setRowCount(0)
        
        # If it's an archive, extract it right away
        if os.path.isfile(path) and self.archive_manager.is_archive(path):
            self.log(f"Detected archive file: {path}")
            self.log("Checking archive compatibility...")
            
            # Check if archive contains compatible files
            compatible = self.check_archive_compatibility(path, -1)  # -1 means no row in table yet
            
            if compatible:
                self.log("Extracting archive...")
                success, temp_dir, disk_images = self.extract_archive(path, -1)
                
                if success and disk_images:
                    # Add the first extracted image to the table
                    self.log(f"Using extracted image: {disk_images[0]}")
                    self.add_file_to_table(disk_images[0])
                    return
                else:
                    self.log("Failed to extract compatible disk images from archive")
            else:
                self.log("Archive does not contain compatible disk images")
        
        # If we get here, either it's not an archive or extraction failed
        # Just add the original file to the table
        if os.path.isfile(path):
            self.add_file_to_table(path)
            self.log(f"Added file to table: {path}")
    
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
        
        # Action buttons
        self.scan_btn.clicked.connect(self.scan_files)
        self.compress_btn.clicked.connect(self.start_compression)
    
    @Slot(int)
    def update_input_mode(self, index):
        """Update the UI based on the selected input mode.
            
        Args:
            index: Selected index
        """
        # Single file mode is the only mode now, so no UI updates needed
        pass
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input File",
            "",
            "Disk Images & Archives (*.iso;*.bin;*.img;*.cue;*.zip;*.7z;*.rar);;Disk Images (*.iso;*.bin;*.img;*.cue);;Archives (*.zip;*.7z;*.rar);;All Files (*.*)"
        )
        
        if path:
            self.input_path_edit.setText(path)
            
            # Update output directory if using same directory
            if self.use_same_dir_check.isChecked():
                self.output_dir_edit.setText(os.path.dirname(path))
            
            # Automatically add the file to the table
            if os.path.isfile(path):
                # Clear the table first
                self.files_table.setRowCount(0)
                # Add the file to the table
                self.add_file_to_table(path)
                self.log(f"Added file to table: {path}")
    
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
    
    @Slot()
    def scan_files(self):
        """Scan for files based on the selected input mode."""
        # This method is kept for compatibility but is simplified in single file mode
        # since files are automatically added when selected
        
        # Get output directory
        output_dir = self.output_dir_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "Error", "Please select an output directory.")
            return
            
        # Check if output directory exists
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                self.log(f"Created output directory: {output_dir}")
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Failed to create output directory: {str(e)}")
                return
                
        # Log the output directory for debugging
        self.log(f"Using output directory: {output_dir}")
        
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
        self.log(f"Scanning for files in {input_path}...")
        
        # Scan for files
        if mode == 0:  # Single file
            # Check if it's an archive
            if self.archive_manager.is_archive(input_path):
                # Extract the archive first
                self.log(f"Detected archive file: {input_path}")
                self.log("Checking archive compatibility...")
                
                # Check if archive contains compatible files
                compatible = self.check_archive_compatibility(input_path, -1)  # -1 means no row in table yet
                
                if not compatible:
                    QMessageBox.warning(self, "Incompatible Archive", "The selected archive does not appear to contain any compatible disk images.")
                    return
                
                # Extract the archive
                self.log("Extracting archive...")
                
                # Create a temporary row for extraction progress
                temp_row = self.files_table.rowCount()
                self.files_table.insertRow(temp_row)
                self.files_table.setItem(temp_row, 0, QTableWidgetItem(os.path.basename(input_path)))
                self.files_table.setItem(temp_row, 1, QTableWidgetItem("Extracting..."))
                
                # Extract the archive
                success, temp_dir, disk_images = self.extract_archive(input_path, temp_row)
                
                # Remove the temporary row
                self.files_table.removeRow(temp_row)
                
                if not success or not disk_images:
                    QMessageBox.warning(self, "Extraction Failed", "Failed to extract any compatible disk images from the archive.")
                    return
                
                # Add the extracted files to the table
                for file in disk_images:
                    self.add_file_to_table(file)
            else:
                # Regular file, add it directly
                self.add_file_to_table(input_path)
        elif mode == 1:  # Directory
            # Get filters
            filters = self.filter_edit.text().split(';')
            include_subdirs = self.include_subdirs_check.isChecked()
            
            # Scan directory
            files = self.file_scanner.scan_directory(
                input_path,
                filters,
                include_subdirs
            )
            
            # Add files to table
            for file in files:
                # Check if it's an archive
                if self.archive_manager.is_archive(file):
                    # We'll handle archives during compression
                    # Add the archive file directly for now
                    self.add_file_to_table(file)
                else:
                    # Regular file, add it directly
                    self.add_file_to_table(file)
        else:  # Archive mode (not used currently)
            QMessageBox.information(self, "Not Implemented", "Archive scanning mode is not yet implemented.")
            return
        
        # Log
        self.log(f"Found {self.files_table.rowCount()} files.")
    
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
    
    def format_size(self, size):
        """Format file size in human-readable format.
        
        Args:
            size: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
            
    def detect_media_type(self, file_path):
        """Detect the media type of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected media type ("CD", "DVD", or "Hard Disk")
        """
        if not file_path or not os.path.exists(file_path) or not os.path.isfile(file_path):
            return None
            
        # Get file extension and size
        ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)
        
        # Detect based on extension and size
        if ext == ".cue":
            return "CD"  # .cue files are typically for CDs
        elif ext == ".iso":
            # For .iso files, use size to determine if it's a DVD
            return "CD" if file_size < 734_003_200 else "DVD"  # 700MB threshold
        elif ext in [".bin", ".img"]:
            # For .bin and .img files, could be either CD or DVD
            return "CD" if file_size < 734_003_200 else "DVD"
        elif ext in [".chd"]:
            # For .chd files, use size to determine
            if file_size < 734_003_200:
                return "CD"
            elif file_size < 8_589_934_592:  # 8GB threshold for DVDs
                return "DVD"
            else:
                return "Hard Disk"
        else:
            # For other files, use size as a heuristic
            if file_size < 734_003_200:
                return "CD"
            elif file_size < 8_589_934_592:  # 8GB threshold for DVDs
                return "DVD"
            else:
                return "Hard Disk"
    
    @Slot()
    def start_compression(self):
        """Start the compression process for a single file."""
        # If no files are in the table but we have a path, add it to the table
        if self.files_table.rowCount() == 0:
            input_path = self.input_path_edit.text()
            if input_path and os.path.exists(input_path) and os.path.isfile(input_path):
                self.log(f"Adding file directly to table: {input_path}")
                self.add_file_to_table(input_path)
            else:
                QMessageBox.warning(self, "Error", "Please select a valid file for compression.")
                return
            
        # Check if there are files to compress after potential scan
        if self.files_table.rowCount() == 0:
            QMessageBox.warning(self, "Error", "No files to compress. Please select a valid file or scan for files first.")
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
        
        # Validate output directory
        if not output_dir:
            QMessageBox.warning(self, "Error", "Please select an output directory.")
            return
            
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                self.log(f"Created output directory: {output_dir}")
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Failed to create output directory: {str(e)}")
                return
        
        # Log the output directory for debugging
        self.log(f"Using output directory: {output_dir}")
        
        # Get compression options
        compression_level = self.compression_level_combo.currentText().lower()
        
        # Get media type (either selected or detected)
        media_type = self.media_type_combo.currentText()
        if media_type == "Auto-detect":
            # Detect media type based on file
            file_path = self.input_path_edit.text()
            if file_path and os.path.exists(file_path) and os.path.isfile(file_path):
                media_type = self.detect_media_type(file_path)
                self.log(f"Auto-detected media type: {media_type}")
            else:
                # Default to CD if we can't detect
                media_type = "CD"
                self.log("Could not detect media type, defaulting to CD")
        
        self.log(f"Using media type: {media_type}")
        
        # Parse hunk size - handle decimal values correctly
        hunk_size_text = self.hunk_size_combo.currentText()
        try:
            # Extract the number part (e.g., '9.8' from '9.8 KB')
            hunk_size_value = float(hunk_size_text.split()[0])
            
            # Special case for CD sector size multiples
            if hunk_size_value == 9.8:
                # This is exactly 4 * 2448 bytes (CD sector size)
                hunk_size = 4 * 2448  # 9792 bytes
            elif hunk_size_value == 19.6:
                # This is exactly 8 * 2448 bytes (CD sector size)
                hunk_size = 8 * 2448  # 19584 bytes
            else:
                # Convert KB to bytes (round to nearest integer)
                hunk_size = int(hunk_size_value * 1024)
            
            # For CDs, ensure hunk size is a multiple of 2448 (CD sector size)
            if media_type == "CD" and hunk_size % 2448 != 0:
                # Round up to the next multiple of 2448
                original_hunk_size = hunk_size
                hunk_size = ((hunk_size + 2448 - 1) // 2448) * 2448
                self.log(f"Adjusted hunk size from {original_hunk_size} to {hunk_size} bytes to be a multiple of CD sector size (2448 bytes)")
            
            self.log(f"Using hunk size: {hunk_size} bytes")
        except (ValueError, IndexError):
            # Fallback to a safe default based on media type
            if media_type == "CD":
                hunk_size = 4 * 2448  # 9792 bytes (4 * CD sector size)
            elif media_type == "DVD":
                hunk_size = 2048  # 2KB (DVD sector size)
            else:  # Hard Disk
                hunk_size = 4096  # 4KB (common block size)
                
            self.log(f"Failed to parse hunk size, using default for {media_type}: {hunk_size} bytes")
            
        verify = self.verify_check.isChecked()
        force = self.force_check.isChecked()
        overwrite = self.overwrite_check.isChecked()
        
        # Create tasks
        tasks = []
        for row in range(self.files_table.rowCount()):
            # Get file path
            file_item = self.files_table.item(row, 0)
            if file_item is None:
                self.log(f"Warning: Row {row} has no file item")
                continue  # Skip if item is None
                
            file_path = file_item.data(Qt.UserRole)
            if file_path is None or not isinstance(file_path, str) or not os.path.exists(file_path):
                self.log(f"Warning: Row {row} has invalid file path: {file_path}")
                continue  # Skip if file path is None or invalid
            
            # Add diagnostic logging
            self.log(f"Processing file: {file_path} (type: {type(file_path).__name__})")
            
            # Check if the file is an archive
            try:
                # Make sure file_path is a valid string before checking
                if file_path is not None and isinstance(file_path, str) and os.path.exists(file_path):
                    self.log(f"Checking if file is archive: {file_path}")
                    is_archive = self.archive_manager.is_archive(file_path)
                    self.log(f"Archive check result: {is_archive}")
                    if is_archive:
                        # Handle archive files by extracting them first
                        self.log(f"Processing archive file: {file_path}")
                        compatible = self.check_archive_compatibility(file_path, row)
                        
                        if compatible:
                            self.log("Archive contains compatible disk images, extracting...")
                            success, temp_dir, disk_images = self.extract_archive(file_path, row)
                            
                            if success and disk_images:
                                # Use the first disk image for compression
                                file_path = disk_images[0]
                                self.log(f"Using extracted image for compression: {file_path}")
                            else:
                                self.log("Failed to extract compatible disk images from archive")
                                self.files_table.setItem(row, 2, QTableWidgetItem("Failed (extraction)"))
                                continue
                        else:
                            self.log("Archive does not contain compatible disk images")
                            self.files_table.setItem(row, 2, QTableWidgetItem("Failed (no disk images)"))
                            continue
                else:
                    self.log(f"Warning: Skipping invalid file path: {file_path} (type: {type(file_path).__name__})")
                    continue
            except Exception as e:
                self.log(f"Error checking if file is archive: {str(e)}")
                self.log(traceback.format_exc())
                continue
            
            # Create output path
            file_name = os.path.basename(file_path)
            base_name, _ = os.path.splitext(file_name)
            output_path = os.path.join(output_dir, f"{base_name}.chd")
            
            # Check if output file exists
            if os.path.exists(output_path):
                if not overwrite:
                    # Update status
                    self.files_table.setItem(row, 2, QTableWidgetItem("Skipped (exists)"))
                    self.log(f"Skipping existing file: {output_path} (overwrite is disabled)")
                    continue
                else:
                    self.log(f"Output file exists but will be overwritten: {output_path}")
            
            # Get the media type for this specific file
            file_media_type = self.detect_media_type(file_path)
            if not file_media_type:
                file_media_type = media_type  # Use the global media type if detection fails
            self.log(f"Using media type '{file_media_type}' for file: {file_path}")
            
            # Create task
            task = CHDTask(
                task_type=CHDTaskType.COMPRESS,
                input_file=file_path,
                output_file=output_path,
                compression_level=compression_level,
                hunk_size=hunk_size,  # Already in bytes
                verify=verify,
                force=force,
                media_type=file_media_type
            )
            
            # Add task
            tasks.append((task, row))
            
            # Update status
            self.files_table.setItem(row, 2, QTableWidgetItem("Queued"))
            
            # Update output
            self.files_table.setItem(row, 4, QTableWidgetItem(output_path))
        
        # Check if there are tasks to process
        if not tasks:
            if self.overwrite_check.isChecked():
                QMessageBox.information(self, "Information", "No files to compress. Please check your input files.")
            else:
                QMessageBox.information(self, "Information", "No files to compress. All output files already exist.\n\nEnable 'Overwrite existing files' if you want to recompress them.")
            return
        
        # Log
        self.log(f"Starting compression of {len(tasks)} files...")
        
        # Update UI
        self.scan_btn.setEnabled(False)
        self.compress_btn.setEnabled(False)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setMaximum(len(tasks))
        self.progress_label.setText(f"Processing 0/{len(tasks)} files...")
        
        # Process tasks
        self.process_tasks(tasks)
    
    def process_tasks(self, tasks):
        """Process compression tasks.
        
        Args:
            tasks: List of (task, row) tuples
        """
        # Clear the CHD manager's task queue
        self.chd_manager.clear_tasks()
        
        # Initialize variables for tracking progress
        self.total_tasks = len(tasks)
        self.completed_tasks = 0
        self.current_task_row = None
        
        # Log
        self.log("Compression started.")
        
        # Process each task sequentially
        for task, row in tasks:
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
                    # First, check if the archive potentially contains compatible files
                    compatible = self.check_archive_compatibility(input_file, row)
                    
                    if not compatible:
                        # Skip this task if the archive doesn't seem to contain compatible files
                        self.log(f"Skipping archive as it doesn't appear to contain compatible disk images: {input_file}")
                        self.files_table.setItem(row, 2, QTableWidgetItem("Skipped (incompatible)"))
                        continue
                    
                    # Extract the archive
                    success, temp_dir, disk_images = self.extract_archive(input_file, row)
                    
                    if not success or not disk_images:
                        # Skip this task if extraction failed or no disk images found
                        continue
                    
                    # Update the task with the first disk image found
                    task.input_file = disk_images[0]
                    
                    # Log the disk image being processed
                    self.log(f"Processing disk image from archive: {os.path.basename(task.input_file)}")
                    
                    # If there are multiple disk images, log them
                    if len(disk_images) > 1:
                        self.log(f"Note: {len(disk_images) - 1} additional disk images found in archive but not processed.")
                
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
                    while progress_bar.value() < 100 and self.files_table.item(row, 2).text() != "Completed" and self.files_table.item(row, 2).text() != "Failed":
                        QApplication.processEvents()  # Allow UI updates
                    
                except Exception as e:
                    # Handle any exceptions from task execution
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
                self.log(f"Error processing task: {str(e)}")
                self.files_table.setItem(row, 2, QTableWidgetItem("Failed"))
            
            # Update overall progress
            self.completed_tasks += 1
            self.overall_progress_bar.setValue(self.completed_tasks)
            self.progress_label.setText(f"Processing {self.completed_tasks}/{self.total_tasks} files...")
        
        # Update UI when done
        self.scan_btn.setEnabled(True)
        self.compress_btn.setEnabled(True)
        self.progress_label.setText(f"Completed {self.completed_tasks}/{self.total_tasks} files.")
        
        # Log
        self.log("Compression completed.")
    
    def log(self, message):
        """Add a message to the log.
        
        Args:
            message: Message to add
        """
        self.log_text.appendPlainText(message)
    
    @Slot(str, int)
    def on_task_started(self, message, row):
        """Handle task started signal.
        
        Args:
            message: Start message
            row: Table row index
        """
        # Update status
        self.files_table.setItem(row, 2, QTableWidgetItem("Processing"))
        
        # Log
        self.log(f"Task started: {message}")
    
    @Slot(float, str, int)
    def on_task_progress(self, value, message, row):
        """Handle task progress signal.
        
        Args:
            value: Progress value (0-100)
            message: Progress message
            row: Table row index
        """
        # Get progress bar
        progress_bar = self.files_table.cellWidget(row, 3)
        
        # Update progress
        if value >= 0:
            progress_bar.setValue(int(value))
        
        # Log if message is not empty
        if message.strip():
            self.log(message)
    
    @Slot(bool, str, int)
    def on_task_finished(self, success, message, row):
        """Handle task finished signal.
        
        Args:
            success: Whether the task completed successfully
            message: Completion message
            row: Table row index
        """
        # Update status
        self.files_table.setItem(row, 2, QTableWidgetItem("Completed"))
        
        # Update progress to 100%
        progress_bar = self.files_table.cellWidget(row, 3)
        progress_bar.setValue(100)
        
        # Log
        self.log(f"Task completed: {message}")
    
    @Slot(str, int)
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
        
        # Show error message
        QMessageBox.critical(self, "Error", f"Failed to process file:\n{message}")

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
            
            # Find all disk image files in the extracted directory
            disk_images = []
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Check if file is a supported disk image format
                    if any(file.lower().endswith(ext) for ext in [".iso", ".bin", ".img", ".cue", ".gdi"]):
                        disk_images.append(file_path)
            
            if not disk_images:
                self.log(f"No supported disk images found in archive: {archive_path}")
                return False, temp_dir, []
            
            return True, temp_dir, disk_images
            
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
        # Update progress bar (scale to 0-50 to leave room for CHD compression)
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
        """Check if an archive potentially contains compatible disk image files.
        
        Args:
            archive_path: Path to the archive file
            row: Table row index
            
        Returns:
            Boolean indicating if the archive might contain compatible files
        """
        self.log(f"Checking archive compatibility: {archive_path}")
        self.files_table.setItem(row, 2, QTableWidgetItem("Checking compatibility"))
        
        try:
            # Supported disk image extensions
            supported_extensions = [".iso", ".bin", ".img", ".cue", ".gdi"]
            
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
            
            # Check if any files in the archive have supported extensions
            for file_path in file_list:
                if any(file_path.lower().endswith(ext) for ext in supported_extensions):
                    self.log(f"Found potentially compatible file in archive: {file_path}")
                    return True
            
            # No compatible files found
            self.log(f"No compatible disk image files found in archive: {archive_path}")
            return False
            
        except Exception as e:
            # If there's an error checking the archive, we'll try extracting it anyway
            self.log(f"Error checking archive compatibility: {str(e)}. Will attempt extraction.")
            return True
