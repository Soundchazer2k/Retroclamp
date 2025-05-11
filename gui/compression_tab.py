"""Compression tab for RetroClamp.

This module provides the UI and functionality for compressing disk images
using the CHDMAN utility.
"""

import os
import shutil
import traceback
import py7zr
import patoolib
from datetime import datetime

# No QtCore imports needed
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QPlainTextEdit, QFileDialog, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)

from core.chdman import CHDManager, CHDTask, CHDTaskType
from core.archive import ArchiveManager
from core.file_scanner import FileScanner

# Compression profiles
COMPRESSION_PROFILES = {
    "CD - Default": {"algorithms": "cdlz,cdzl,cdfl", "hunk_size": 19584},  # 8 * 2448 (CD sector size)
    "CD - Fast": {"algorithms": "cdlz", "hunk_size": 19584},
    "DVD - Default": {"algorithms": "zlib,huff", "hunk_size": 2048},  # DVD sector size
    "DVD - Best": {"algorithms": "lzma", "hunk_size": 2048},
    "Hard Disk - Default": {"algorithms": "zlib,huff", "hunk_size": 4096},  # Standard block size
    "Hard Disk - Best": {"algorithms": "lzma", "hunk_size": 4096}
}


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
        self.chd_manager = CHDManager()
        self.archive_manager = ArchiveManager()
        self.file_scanner = FileScanner()
        
        # Track temporary directories for cleanup
        self.temp_directories = []
        
        # Setup UI and connect signals
        self._build_ui()
        self._connect_signals()
    
    def _build_ui(self):
        """Build the user interface."""
        layout = QVBoxLayout(self)
        
        # Input selection
        in_layout = QHBoxLayout()
        self.input_path_edit = QLineEdit()
        self.browse_input_btn = QPushButton("Browse Input")
        in_layout.addWidget(QLabel("Input File or Archive:"))
        in_layout.addWidget(self.input_path_edit)
        in_layout.addWidget(self.browse_input_btn)
        layout.addLayout(in_layout)
        
        # Output directory
        out_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.browse_output_btn = QPushButton("Browse Output Dir")
        self.use_same_dir_check = QCheckBox("Use same directory as input")
        out_layout.addWidget(QLabel("Output Directory:"))
        out_layout.addWidget(self.output_dir_edit)
        out_layout.addWidget(self.browse_output_btn)
        out_layout.addWidget(self.use_same_dir_check)
        layout.addLayout(out_layout)
        
        # Compression options
        options_layout = QHBoxLayout()
        
        # Media type
        self.media_type_combo = QComboBox()
        self.media_type_combo.addItems(["Auto Detect", "CD", "DVD", "Hard Disk"])
        options_layout.addWidget(QLabel("Media Type:"))
        options_layout.addWidget(self.media_type_combo)
        
        # Compression profile
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(COMPRESSION_PROFILES.keys())
        options_layout.addWidget(QLabel("Compression Profile:"))
        options_layout.addWidget(self.profile_combo)
        
        # Overwrite option
        self.overwrite_check = QCheckBox("Overwrite Existing Files")
        options_layout.addWidget(self.overwrite_check)
        
        layout.addLayout(options_layout)
        
        # Files table
        self.files_table = QTableWidget(0, 3)
        self.files_table.setHorizontalHeaderLabels(["File", "Status", "Progress"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.files_table)
        
        # Log output
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Compression")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cleanup_btn = QPushButton("Cleanup Temp Directories")
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.cleanup_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect widget signals to slots."""
        # UI signals
        self.browse_input_btn.clicked.connect(self.browse_input)
        self.browse_output_btn.clicked.connect(self.browse_output)
        self.use_same_dir_check.toggled.connect(self.toggle_output_dir)
        self.media_type_combo.currentIndexChanged.connect(self.update_profile_list)
        self.start_btn.clicked.connect(self.start_compression)
        self.cancel_btn.clicked.connect(self.cancel_compression)
        self.cleanup_btn.clicked.connect(self.cleanup_temp_directories)
        
        # Archive manager signals will be connected when extract() is called
        # The extract method returns an ArchiveSignals object that we can connect to
    
    def start_compression(self):
        """Start the compression process.
        
        This method handles both single files and archives, creating appropriate
        CHDTask objects and connecting signals for UI updates.
        """
        # Clear any previous tasks
        self.chd_manager.clear_tasks()
        
        # Get input path
        input_path = self.input_path_edit.text().strip()
        if not input_path:
            QMessageBox.warning(self, "Input Required", "Please select an input file.")
            return
            
        # Check if input file exists
        if not os.path.exists(input_path):
            QMessageBox.warning(self, "Input File Not Found", f"The input file does not exist: {input_path}")
            return
            
        # Get output directory
        output_dir = self.output_dir_edit.text().strip()
        if not self.check_output_directory(output_dir):
            return  # check_output_directory will show appropriate error messages
            
        # Clear the files table
        self.files_table.setRowCount(0)
        
        # Reset progress bar
        self.progress_bar.setValue(0)
        
        # Add the input file to the table
        initial_ui_row = self.add_file_to_table(input_path)
        self.update_file_status(initial_ui_row, "Pending")
        
        # Determine base media type and compression options
        base_media_type = self.detect_media_type(input_path)
        base_compression_algos = self.get_compression_options()
        
        # Set task type to COMPRESS
        task_type = CHDTaskType.COMPRESS
        
        # Default output path (for single file)
        input_basename = os.path.basename(input_path)
        input_name_no_ext, _ = os.path.splitext(input_basename)
        default_chd_output_path = os.path.join(output_dir, f"{input_name_no_ext}.chd")
        
        # Check if file is an archive
        is_archive = self.archive_manager.is_archive(input_path)
        
        if is_archive:
            self.log_message(f"Processing archive: {input_path}")
            self.update_file_status(initial_ui_row, "Extracting")
            
            # Extract the archive
            success, temp_dir, extracted_files = self.extract_archive(input_path, initial_ui_row)
            
            if not success or not extracted_files:
                self.log_message("No files to compress from archive.")
                self.update_file_status(initial_ui_row, "Error: No valid files")
                self.start_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)
                return
                
            self.log_message(f"Found {len(extracted_files)} disk images in archive")
            
            # Prune the disk images to ensure only one file per disc is processed
            pruned_files = self._prune_disk_images(extracted_files)
            self.log_message(f"Pruned to {len(pruned_files)} unique discs for processing")
            
            # Update the archive row to show it was extracted successfully
            if initial_ui_row is not None and len(pruned_files) > 0:
                self.update_file_status(initial_ui_row, "Extracted")
                self.update_file_progress(initial_ui_row, 100)
            
            # Process each pruned file (one per disc)
            for i, extracted_file_path in enumerate(pruned_files):
                extracted_file_basename = os.path.basename(extracted_file_path)
                extracted_file_name_no_ext, _ = os.path.splitext(extracted_file_basename)
                
                # Output path for this specific extracted file
                current_chd_output_path = os.path.join(output_dir, f"{extracted_file_name_no_ext}.chd")
                
                # Add a new row in the UI table for this specific file to be compressed
                task_specific_row = self.add_file_to_table(extracted_file_path)
                self.update_file_status(task_specific_row, "Pending")
                
                # Skip if output exists and overwrite is not checked
                if os.path.exists(current_chd_output_path) and not self.overwrite_check.isChecked():
                    self.log_message(f"Skipping {extracted_file_path}: Output {current_chd_output_path} exists.")
                    self.update_file_status(task_specific_row, "Skipped - File exists")
                    continue
                
                # Detect media type for this specific file
                current_media_type = self.detect_media_type(extracted_file_path)
                self.log_message(f"File {i+1}/{len(extracted_files)}: {extracted_file_path} (Media type: {current_media_type})")
                
                # Create and add task
                task = CHDTask(
                    task_type=task_type,
                    input_file=extracted_file_path,
                    output_file=current_chd_output_path,
                    algorithms=base_compression_algos,
                    hunk_size=self.get_hunk_size(current_media_type),
                    force=self.overwrite_check.isChecked(),
                    media_type=current_media_type,
                    user_data={"row": task_specific_row, "original_input": extracted_file_path}
                )
                self.chd_manager.add_task(task)
                self.log_message(f"Created CHD task with input: {extracted_file_path}, output: {current_chd_output_path}")
        else:  # Not an archive, single file
            self.log_message(f"Queueing File: {input_path} (Media: {base_media_type}) -> {default_chd_output_path}")
            
            # Skip if output exists and overwrite is not checked
            if os.path.exists(default_chd_output_path) and not self.overwrite_check.isChecked():
                self.log_message(f"Skipping {input_path}: Output {default_chd_output_path} exists.")
                self.update_file_status(initial_ui_row, "Skipped - File exists")
                self.start_btn.setEnabled(True)
                return
            
            # Create and add task
            task = CHDTask(
                task_type=task_type,
                input_file=input_path,
                output_file=default_chd_output_path,
                algorithms=base_compression_algos,
                hunk_size=self.get_hunk_size(base_media_type),
                force=self.overwrite_check.isChecked(),
                media_type=base_media_type,
                user_data={"row": initial_ui_row, "original_input": input_path}
            )
            self.chd_manager.add_task(task)
        
        # Execute tasks and connect signals
        signals_list = []
        tasks_for_signals = []
        try:
            self.log_message("Executing all tasks in queue...")
            signals_list = self.chd_manager.execute_all_tasks()
            tasks_for_signals = self.chd_manager.get_last_executed_tasks_batch()  # Get the tasks
            self.log_message(f"Task execution initiated for {len(signals_list)} tasks.")
        except Exception as e:
            self.log_message(f"ERROR executing tasks: {str(e)}")
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
            self.log_message("ERROR: Mismatch between signals and task metadata. UI updates may be incorrect.")
            # Handle this error state - perhaps re-enable UI
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            return
        
        self.log_message(f"Connecting signals for {len(signals_list)} tasks...")
        any_task_started = False
        for i, signals_obj in enumerate(signals_list):
            task_for_this_signal = tasks_for_signals[i]
            
            if not hasattr(task_for_this_signal, 'user_data') or "row" not in task_for_this_signal.user_data:
                self.log_message(f"Warning: Task for signal {i} (input: {task_for_this_signal.input_file}) missing user_data or row. Skipping signal connections for this task.")
                continue
            
            # This is the crucial part: capture the row specific to this task for the lambdas
            row_for_this_task_lambda_capture = task_for_this_signal.user_data["row"]
            original_input_for_this_task = task_for_this_signal.user_data.get("original_input", "Unknown file")
            
            self.log_message(f"  Connecting signals for task {i+1}/{len(signals_list)} (File: {os.path.basename(original_input_for_this_task)}, Row: {row_for_this_task_lambda_capture})")
            self.update_file_status(row_for_this_task_lambda_capture, "Starting")  # Update status when connecting
            
            signals_obj.started.connect(
                # Default argument 'r' captures current value of row_for_this_task_lambda_capture
                lambda msg, r=row_for_this_task_lambda_capture, f=original_input_for_this_task: 
                    self.log_message(f"Task for '{os.path.basename(f)}' (Row {r}) started. CMD: {msg}")
            )
            
            signals_obj.progress.connect(
                lambda progress_val, msg_line, r=row_for_this_task_lambda_capture, f=original_input_for_this_task:
                    self.progress_with_message(progress_val, msg_line, r, f)  # Pass file for logging
            )
            
            signals_obj.finished.connect(
                lambda success, finish_msg, r=row_for_this_task_lambda_capture, f=original_input_for_this_task:
                    self.on_task_finished(success, finish_msg, r, f)  # Pass file for logging
            )
            
            signals_obj.error.connect(
                lambda err_msg, r=row_for_this_task_lambda_capture, f=original_input_for_this_task:
                    self.on_task_error(err_msg, r, f)  # Pass file for logging
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
            if status_item and status_item.text() in ["Pending", "Starting", "Compressing"]:
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
    
    def log_message(self, message):
        """Add message to log.
        
        Args:
            message: Message to log
        """
        # Get current time
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        
        # Clean up the message to ensure it's properly formatted
        # Replace any control characters or non-printable characters
        if message:
            message = str(message)  # Ensure message is a string
            message = ''.join(c if c.isprintable() or c in '\n\r\t ' else ' ' for c in message)
        
        # Add timestamped message to log
        log_message = f"{timestamp} {message}"
        self.log_text.appendPlainText(log_message)
        
        # Ensure the latest message is visible
        self.log_text.ensureCursorVisible()
        
        # Also print to console for debugging
        print(log_message)
    
    def browse_input(self):
        """Open file dialog to select input file.
        
        If an archive is selected, it will be automatically extracted and
        the contents will be displayed in the files table for preview.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Input File", "",
            "All Files (*);;Disk Images (*.iso *.bin *.img);;Archives (*.zip *.7z *.rar)"
        )
        
        if file_path:
            self.input_path_edit.setText(file_path)
            
            # If 'use same directory' is checked, update output directory
            if self.use_same_dir_check.isChecked():
                self.output_dir_edit.setText(os.path.dirname(file_path))
            
            # Clear any previous tasks and the files table
            self.chd_manager.clear_tasks()
            self.files_table.setRowCount(0)
            
            # If it's an archive, extract it now to preview contents
            if self.archive_manager.is_archive(file_path):
                self.log_message(f"Selected file is an archive: {file_path}")
                self.log_message("Extracting archive for preview...")
                
                # Add the archive to the table
                archive_row = self.add_file_to_table(file_path)
                self.update_file_status(archive_row, "Extracting")
                
                # Extract the archive
                success, temp_dir, extracted_files = self.extract_archive(file_path, archive_row)
                
                if success and extracted_files:
                    self.log_message(f"Found {len(extracted_files)} disk images in archive")
                    self.update_file_status(archive_row, "Extracted")
                    self.update_file_progress(archive_row, 100)
                    
                    # Add each extracted file to the table for preview
                    for extracted_file in extracted_files:
                        file_row = self.add_file_to_table(extracted_file)
                        media_type = self.detect_media_type(extracted_file)
                        self.update_file_status(file_row, f"Ready ({media_type})")
                else:
                    self.log_message("No valid disk images found in archive.")
                    if archive_row is not None:
                        self.update_file_status(archive_row, "Error: No valid files")
            else:
                # Add the single file to the table
                file_row = self.add_file_to_table(file_path)
                media_type = self.detect_media_type(file_path)
                self.update_file_status(file_row, f"Ready ({media_type})")
            
            # Enable the start button
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
    
    def browse_output(self):
        """Open directory dialog to select output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", ""
        )
        
        if directory:
            self.output_dir_edit.setText(directory)
    
    def toggle_output_dir(self, checked):
        """Enable/disable output directory controls based on checkbox.
        
        Args:
            checked: Whether 'use same directory' is checked
        """
        self.output_dir_edit.setEnabled(not checked)
        self.browse_output_btn.setEnabled(not checked)
        
        if checked and self.input_path_edit.text():
            self.output_dir_edit.setText(os.path.dirname(self.input_path_edit.text()))
    
    def update_profile_list(self, index=None):
        """Update the profile list based on the selected media type.
        
        Args:
            index: Index of the selected media type (optional)
        """
        media_type = self.media_type_combo.currentText()
        if media_type == "Auto Detect":
            # Show all profiles
            self.profile_combo.clear()
            self.profile_combo.addItems(COMPRESSION_PROFILES.keys())
        else:
            # Filter profiles by media type
            self.profile_combo.clear()
            filtered_profiles = [name for name in COMPRESSION_PROFILES.keys() 
                               if name.startswith(media_type)]
            self.profile_combo.addItems(filtered_profiles)
    
    def add_file_to_table(self, file_path):
        """Add file to the files table.
        
        Args:
            file_path: Path to file
            
        Returns:
            Row index of added file
        """
        # Normalize the file path to ensure consistent display
        file_path = os.path.normpath(file_path)
        
        # Check if file is already in the table
        for row in range(self.files_table.rowCount()):
            if self.files_table.item(row, 0).text() == file_path:
                return row
        
        # Add new row
        row = self.files_table.rowCount()
        self.files_table.insertRow(row)
        
        # Add file name
        self.files_table.setItem(row, 0, QTableWidgetItem(file_path))
        
        # Add status
        self.files_table.setItem(row, 1, QTableWidgetItem("Pending"))
        
        # Add progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        self.files_table.setCellWidget(row, 2, progress_bar)
        
        return row
    
    def update_file_status(self, row, status):
        """Update file status in the table.
        
        Args:
            row: Row index
            status: New status text
        """
        if row is not None and row >= 0 and row < self.files_table.rowCount():
            self.files_table.setItem(row, 1, QTableWidgetItem(status))
    
    def update_file_progress(self, row, progress):
        """Update file progress in the table.
        
        Args:
            row: Row index
            progress: Progress value (0-100)
        """
        if row is not None and row >= 0 and row < self.files_table.rowCount():
            progress_bar = self.files_table.cellWidget(row, 2)
            if progress_bar:
                # Ensure progress is an integer before setting the value
                try:
                    progress_int = int(progress)
                    progress_bar.setValue(progress_int)
                except (ValueError, TypeError) as e:
                    self.log_message(f"Warning: Invalid progress value: {progress}, error: {str(e)}")
                    # Default to no progress update if conversion fails
    
    def extract_archive(self, archive_path, row_index):
        """Extract an archive file to a temporary directory.
        
        Args:
            archive_path: Path to the archive file
            row_index: Row index in the table
            
        Returns:
            Tuple of (success, temp_dir, disk_images)
        """
        self.log_message(f"Extracting archive: {archive_path}")
        
        # Create a temporary directory in a system-appropriate location
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix="retroclamp_")
        self.log_message(f"Created temporary directory: {temp_dir}")
        
        # Add to list for cleanup (will be removed if extraction fails)
        self.temp_directories.append(temp_dir)
        
        try:
            # Handle 7z archives with py7zr
            if archive_path.lower().endswith('.7z'):
                try:
                    with py7zr.SevenZipFile(archive_path, mode='r') as z:
                        z.extractall(path=temp_dir)
                    self.log_message(f"Successfully extracted 7z archive to {temp_dir}")
                except py7zr.exceptions.Bad7zFile as e:
                    error_msg = f"Invalid 7z file format: {e}"
                    self.log_message(f"Error: {error_msg}")
                    self.update_file_status(row_index, "Error: Invalid 7z file")
                    self._cleanup_temp_dir(temp_dir)
                    return False, None, []
                except py7zr.exceptions.PasswordRequired as e:
                    error_msg = f"Password required for 7z file: {e}"
                    self.log_message(f"Error: {error_msg}")
                    self.update_file_status(row_index, "Error: Password required")
                    self._cleanup_temp_dir(temp_dir)
                    return False, None, []
                except Exception as e:
                    error_msg = f"Failed to extract 7z archive: {str(e)}"
                    self.log_message(f"Error: {error_msg}")
                    self.update_file_status(row_index, "Error: 7z extraction failed")
                    self._cleanup_temp_dir(temp_dir)
                    return False, None, []
            # Handle other archive types with patoolib
            else:
                try:
                    patoolib.extract_archive(archive_path, outdir=temp_dir)
                    self.log_message(f"Successfully extracted archive to {temp_dir}")
                except patoolib.util.PatoolError as e:
                    error_msg = f"Archive extraction failed: {e}"
                    self.log_message(f"Error: {error_msg}")
                    self.update_file_status(row_index, "Error: Extraction failed")
                    self._cleanup_temp_dir(temp_dir)
                    return False, None, []
                except Exception as e:
                    error_msg = f"Unexpected error during extraction: {str(e)}"
                    self.log_message(f"Error: {error_msg}")
                    self.update_file_status(row_index, "Error: Extraction failed")
                    self._cleanup_temp_dir(temp_dir)
                    return False, None, []

            # Scan the extracted directory for disk images
            try:
                disk_images = self.file_scanner.find_disk_images(temp_dir)

                if disk_images:
                    self.log_message(f"Found {len(disk_images)} disk images in archive")
                    return True, temp_dir, disk_images
                else:
                    self.log_message("No disk images found in archive")
                    self.update_file_status(row_index, "Error: No disk images found")
                    self._cleanup_temp_dir(temp_dir)
                    return False, None, []
            except Exception as e:
                error_msg = f"Failed to scan extracted files: {str(e)}"
                self.log_message(f"Error: {error_msg}")
                self.update_file_status(row_index, "Error: Failed to scan files")
                self._cleanup_temp_dir(temp_dir)
                return False, None, []
        except Exception as e:
            error_msg = f"Unexpected error during archive processing: {str(e)}"
            self.log_message(f"Error: {error_msg}")
            self.update_file_status(row_index, "Error: Extraction failed")
            self._cleanup_temp_dir(temp_dir)
            return False, None, []
            
    def _cleanup_temp_dir(self, temp_dir):
        """Helper method to clean up a temporary directory.
        
        Args:
            temp_dir: Path to the temporary directory to clean up
        """
        if not temp_dir:
            return
            
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            if temp_dir in self.temp_directories:
                self.temp_directories.remove(temp_dir)
        except Exception as cleanup_error:
            self.log_message(f"Warning: Could not clean up temporary directory: {str(cleanup_error)}")
    
    def on_archive_error(self, error_message, row_index):
        """Handle archive extraction error.
        
        Args:
            error_message: Error message
            row_index: Row index in the table
        """
        self.update_file_status(row_index, "Error")
        self.log_message(f"Error extracting archive: {error_message}")
    
    def _prune_disk_images(self, disk_images):
        """Group disk images by base name and select the most appropriate file for each group.
        
        When both .cue and .bin files are present for the same disc, only the .cue file
        should be processed since it contains the metadata needed by CHDMAN.
        
        Args:
            disk_images: List of paths to disk image files
            
        Returns:
            List of pruned disk image paths (one per disc)
        """
        # Group by base name
        groups = {}
        for path in disk_images:
            base, ext = os.path.splitext(os.path.basename(path).lower())
            if base not in groups:
                groups[base] = []
            groups[base].append(path)
        
        # Select one "master" per group
        pruned = []
        for base, files in groups.items():
            # Look for a .cue file first
            cue = next((f for f in files if f.lower().endswith('.cue')), None)
            if cue:
                pruned.append(cue)
                self.log_message(f"Selected .cue file for disc '{base}': {os.path.basename(cue)}")
            else:
                # If no .cue, use the first file (typically .bin or .iso)
                pruned.append(files[0])
                self.log_message(f"No .cue file found for disc '{base}', using: {os.path.basename(files[0])}")
        
        return pruned
    
    def detect_media_type(self, file_path):
        """Detect media type for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Media type string ("CD", "DVD", or "Hard Disk")
        """
        # If user selected a specific media type, use that
        selected_type = self.media_type_combo.currentText()
        if selected_type != "Auto Detect":
            return selected_type
        
        # Otherwise, auto-detect based on file extension and size
        ext = os.path.splitext(file_path)[1].lower()
        
        # Check if it's a CD/DVD image
        if ext in ['.bin', '.cue', '.iso', '.gdi']:
            # Check file size to determine if it's CD or DVD
            try:
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if size_mb < 700:  # CD images are typically < 700MB
                    return "CD"
                else:
                    return "DVD"
            except (OSError, IOError) as e:
                # If we can't determine size, default to DVD
                self.log_message(f"Warning: Could not determine file size for {file_path}: {e}")
                return "DVD"
        
        # Default to Hard Disk for other formats
        return "Hard Disk"
    
    def get_compression_options(self):
        """Get compression options from UI.
        
        Returns:
            Compression algorithm string
        """
        profile_name = self.profile_combo.currentText()
        if profile_name in COMPRESSION_PROFILES:
            return COMPRESSION_PROFILES[profile_name]["algorithms"]
        
        # Default compression options based on media type
        media_type = self.media_type_combo.currentText()
        if media_type == "CD":
            return "cdlz,cdzl,cdfl"
        elif media_type == "DVD":
            return "zlib,huff"
        else:  # Hard Disk
            return "zlib,huff"
    
    def get_hunk_size(self, media_type):
        """Get appropriate hunk size for media type.
        
        Args:
            media_type: Media type string ('CD', 'DVD', 'Hard Disk')
            
        Returns:
            Hunk size in bytes
        """
        profile_name = self.profile_combo.currentText()
        if profile_name in COMPRESSION_PROFILES:
            return COMPRESSION_PROFILES[profile_name]["hunk_size"]
        
        # Default hunk sizes based on media type
        if media_type == "CD":
            return 19584  # 8 * 2448 (CD sector size)
        elif media_type == "DVD":
            return 2048   # DVD sector size
        else:  # Hard Disk
            return 4096   # Standard block size
    
    def check_output_directory(self, output_dir):
        """Check if the output directory exists and is writable.
        
        Args:
            output_dir: Path to the output directory
            
        Returns:
            bool: True if the directory is writable, False otherwise
        """
        if not output_dir:
            QMessageBox.warning(self, "Output Directory Required", "Please select an output directory.")
            return False
            
        # Check if the directory exists, try to create it if it doesn't
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                self.log_message(f"Created output directory: {output_dir}")
            except OSError as e:
                QMessageBox.warning(
                    self, 
                    "Output Directory Error", 
                    f"Cannot create output directory: {output_dir}\n\nError: {str(e)}\n\n"
                    f"Please select a different output directory or ensure you have the necessary permissions."
                )
                return False
                
        # Check if the directory is writable
        if not os.access(output_dir, os.W_OK):
            QMessageBox.warning(
                self, 
                "Permission Error", 
                f"Cannot write to output directory: {output_dir}\n\n"
                f"Please select a different output directory or ensure you have the necessary permissions.\n\n"
                f"Possible solutions:\n"
                f"1. Choose a different output directory\n"
                f"2. Run the application as administrator\n"
                f"3. Check if the drive is write-protected"
            )
            return False
            
        return True
    
    # Removed duplicate method: extract_archive (already defined earlier)
    # Removed duplicate method: _cleanup_temp_dir (already defined earlier)
    def on_task_progress(self, progress, row):
        """Handle CHD task progress.
        
        Args:
            progress: Progress value (0-100) or message string
            row: Row index in the table
        """
        # Check if progress is a number or a message
        if isinstance(progress, (int, float)) and progress >= 0:
            # It's a progress value
            self.update_file_progress(row, progress)
            
            # Update status if starting
            if progress > 0:
                self.update_file_status(row, "Compressing")
        elif isinstance(progress, (int, float)) and progress == -1:
            # It's a message without progress value, log it
            # The actual message is in the second parameter which we're not capturing here
            pass  # We'll handle this in the progress_with_message method
        else:
            # Log any unexpected progress values for debugging
            self.log_message(f"Debug: Received progress update: {progress}")
    
    def on_task_finished(self, success, message, row, file_path_for_log=None):
        """Handle CHD task completion.
        
        Args:
            success: Whether the task completed successfully
            message: Message from the task
            row: Row index in the table
            file_path_for_log: Original input file path for more descriptive logging
        """
        file_basename = os.path.basename(file_path_for_log) if file_path_for_log else "Unknown file"
        
        if row is not None and row >= 0 and row < self.files_table.rowCount():
            table_file_path = self.files_table.item(row, 0).text()
            if success:
                self.update_file_status(row, "Completed")
                self.update_file_progress(row, 100)
                self.log_message(f"✅ Compression completed for: {file_basename}")
            else:
                self.update_file_status(row, "Failed")
                self.log_message(f"❌ Compression failed for: {file_basename}. Reason: {message}")
        else:
            self.log_message(f"Task finished (success: {success}) for {file_basename} but couldn't determine which row. Message: {message}")
        
        # Check if all tasks are complete
        if self.chd_manager.get_active_tasks_count() == 0:
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.log_message("All compression tasks completed")
            
            # Clean up temp directories
            self.cleanup_temp_directories()
    
    def update_overall_progress(self):
        """Calculate and update the overall progress bar based on all tasks."""
        total_rows = self.files_table.rowCount()
        if total_rows == 0:
            self.progress_bar.setValue(0)
            return
            
        # Calculate the average progress across all rows
        total_progress = 0
        completed_count = 0
        
        for row in range(total_rows):
            # Get the progress cell
            progress_cell = self.files_table.cellWidget(row, 2)
            if progress_cell and isinstance(progress_cell, QProgressBar):
                progress_value = progress_cell.value()
                total_progress += progress_value
                
                # Count completed tasks (100% progress)
                if progress_value == 100:
                    completed_count += 1
        
        # Calculate average progress
        average_progress = total_progress / total_rows if total_rows > 0 else 0
        
        # Update the main progress bar
        self.progress_bar.setValue(int(average_progress))
        
        # Update the progress bar tooltip to show more details
        self.progress_bar.setToolTip(f"Overall Progress: {average_progress:.1f}% ({completed_count}/{total_rows} tasks complete)")
    
    def progress_with_message(self, progress_value, message, row, file_path_for_log=None):
        """Handle progress updates with messages from CHDManWorker.
        
        Args:
            progress_value: Progress value (0-100) or -1 for message only
            message: Message from the worker
            row: Row index in the table
            file_path_for_log: Original input file path for more descriptive logging
        """
        file_basename = os.path.basename(file_path_for_log) if file_path_for_log else "Task"

        if message and message.strip():
            # Prepend file context to the message if it's a generic chdman output line
            if progress_value == -1 and not message.startswith(f"[{file_basename}]"):  # Avoid double-prefixing
                self.log_message(f"[{file_basename} - Row {row}] {message.strip()}")
            elif progress_value != -1:  # If progress % is included, chdman usually says "Compressing X"
                self.log_message(f"{message.strip()} (for {file_basename})")
            else:
                self.log_message(message)

        # Update progress if it's a valid progress value
        if isinstance(progress_value, (int, float)) and progress_value >= 0:
            self.update_file_progress(row, progress_value)
            
            # Update status if not already in a final state
            if row < self.files_table.rowCount() and self.files_table.item(row, 1).text() not in ["Completed", "Error", "Failed", "Cancelled"]:
                self.update_file_status(row, "Compressing")
                
            # Update overall progress bar based on all tasks
            self.update_overall_progress()
        elif progress_value == -1:  # Message only
            # For message-only updates, don't change the progress bar
            pass
                
            # Update status if not already in a final state
            if row < self.files_table.rowCount():
                current_status = self.files_table.item(row, 1).text()
                if current_status not in ["Completed", "Error", "Failed", "Cancelled", "Compressing"]:
                    self.update_file_status(row, "Processing...")
    
    def on_task_error(self, error_message, row, file_path_for_log=None):
        """Handle CHD task error.
        
        Args:
            error_message: Error message
            row: Row index in the table
            file_path_for_log: Original input file path for more descriptive logging
        """
        file_basename = os.path.basename(file_path_for_log) if file_path_for_log else "Unknown file"
        
        # Log the error with file context
        self.log_message(f"❌ ERROR for {file_basename}: {error_message}")
        
        # Update the UI
        if row >= 0 and row < self.files_table.rowCount():
            self.update_file_status(row, "Error")
            table_file_path = self.files_table.item(row, 0).text()
            self.log_message(f"Compression failed for file at row {row}: {file_basename}")
        else:
            self.log_message(f"Task failed for {file_basename} (invalid row {row}): {error_message}")
        
        # Check if all tasks are complete
        if self.chd_manager.get_active_tasks_count() == 0:
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.log_message("All compression tasks completed (with errors)")
            
            # Clean up temp directories
            self.cleanup_temp_directories()
    
    # Removed duplicate method: _finish_cancellation (already defined earlier)
    # Removed duplicate method: on_task_error (already defined earlier)
    # Using the existing add_file_to_table method defined earlier
    
    def cleanup_temp_directories(self):
        """Clean up all temporary directories.
        
        This method removes all temporary directories created during archive extraction
        and clears the list of tracked directories.
        """
        if not self.temp_directories:
            self.log_message("No temporary directories to clean up")
            return
            
        self.log_message(f"Cleaning up {len(self.temp_directories)} temporary directories...")
        
        # Make a copy of the list since we'll be modifying it during iteration
        temp_dirs_to_clean = self.temp_directories.copy()
        
        for temp_dir in temp_dirs_to_clean:
            try:
                if os.path.exists(temp_dir):
                    self.log_message(f"Removing temporary directory: {temp_dir}")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    if temp_dir in self.temp_directories:
                        self.temp_directories.remove(temp_dir)
            except Exception as e:
                self.log_message(f"Error cleaning up temporary directory {temp_dir}: {str(e)}")
        
        # Check if any directories remain (should be none if all cleanups succeeded)
        if self.temp_directories:
            self.log_message(f"Warning: {len(self.temp_directories)} temporary directories could not be cleaned up")
        else:
            self.log_message("All temporary directories cleaned up successfully")
    
    def closeEvent(self, event):
        """Handle widget close event.
        
        Args:
            event: Close event
        """
        # Clean up temporary directories before closing
        self.log_message("Application closing, cleaning up resources...")
        self.cleanup_temp_directories()
        
        # Terminate any running CHDMAN processes
        self.chd_manager.terminate_all_chdman_processes()
        
        # Accept the close event
        event.accept()
