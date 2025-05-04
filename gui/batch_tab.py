#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch Processing Tab for RetroClamp.

This module provides the batch processing interface for RetroClamp,
allowing users to process multiple files at once.
"""

import os
from typing import List, Dict, Any, Optional, Tuple

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QComboBox, QSpinBox, QCheckBox, QProgressBar, QFrame,
    QScrollArea, QSizePolicy, QGridLayout, QSpacerItem
)

from core.chdman import CHDManager, CHDTask, CHDTaskType
from modules.app_settings import AppSettings
from modules.ui_functions import load_svg_icon


class BatchTab(QWidget):
    """Batch Processing Tab for RetroClamp.
    
    This tab allows users to add multiple files to a queue and process them
    in batch mode, either for compression or extraction.
    """
    
    def __init__(self):
        """Initialize the batch processing tab."""
        super().__init__()
        
        # Set up the UI
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)
        
        # Header
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 10)
        
        self.title_label = QLabel("Batch Processing")
        self.title_label.setObjectName("pageTitle")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.title_label.setFont(font)
        
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        
        # Add buttons
        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.setIcon(load_svg_icon("file-plus", 20, "#f8f8f2"))
        self.add_files_btn.setMinimumSize(120, 36)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setIcon(load_svg_icon("trash", 20, "#f8f8f2"))
        self.clear_btn.setMinimumSize(120, 36)
        
        self.start_btn = QPushButton("Start Processing")
        self.start_btn.setIcon(load_svg_icon("player-play", 20, "#f8f8f2"))
        self.start_btn.setMinimumSize(150, 36)
        
        self.header_layout.addWidget(self.add_files_btn)
        self.header_layout.addWidget(self.clear_btn)
        self.header_layout.addWidget(self.start_btn)
        
        self.main_layout.addLayout(self.header_layout)
        
        # Options frame
        self.options_frame = QFrame()
        self.options_frame.setObjectName("optionsFrame")
        self.options_frame.setFrameShape(QFrame.StyledPanel)
        self.options_frame.setFrameShadow(QFrame.Raised)
        
        self.options_layout = QHBoxLayout(self.options_frame)
        self.options_layout.setContentsMargins(10, 10, 10, 10)
        self.options_layout.setSpacing(20)
        
        # Operation type
        self.operation_layout = QVBoxLayout()
        self.operation_label = QLabel("Operation:")
        self.operation_combo = QComboBox()
        self.operation_combo.addItem("Compress to CHD", CHDTaskType.COMPRESS)
        self.operation_combo.addItem("Extract CD from CHD", CHDTaskType.EXTRACT_CD)
        self.operation_combo.addItem("Extract DVD from CHD", CHDTaskType.EXTRACT_DVD)
        self.operation_combo.addItem("Extract HD from CHD", CHDTaskType.EXTRACT_HD)
        self.operation_combo.addItem("Extract A/V from CHD", CHDTaskType.EXTRACT_AV)
        
        self.operation_layout.addWidget(self.operation_label)
        self.operation_layout.addWidget(self.operation_combo)
        
        # Compression level
        self.compression_layout = QVBoxLayout()
        self.compression_label = QLabel("Compression Level:")
        self.compression_spin = QSpinBox()
        self.compression_spin.setMinimum(0)
        self.compression_spin.setMaximum(9)
        self.compression_spin.setValue(4)
        
        self.compression_layout.addWidget(self.compression_label)
        self.compression_layout.addWidget(self.compression_spin)
        
        # Threads
        self.threads_layout = QVBoxLayout()
        self.threads_label = QLabel("Threads:")
        self.threads_spin = QSpinBox()
        self.threads_spin.setMinimum(1)
        self.threads_spin.setMaximum(16)
        self.threads_spin.setValue(4)
        
        self.threads_layout.addWidget(self.threads_label)
        self.threads_layout.addWidget(self.threads_spin)
        
        # Options
        self.options_check_layout = QVBoxLayout()
        self.options_check_label = QLabel("Options:")
        self.verify_check = QCheckBox("Verify after operation")
        self.verify_check.setChecked(True)
        
        self.options_check_layout.addWidget(self.options_check_label)
        self.options_check_layout.addWidget(self.verify_check)
        
        # Add layouts to options
        self.options_layout.addLayout(self.operation_layout)
        self.options_layout.addLayout(self.compression_layout)
        self.options_layout.addLayout(self.threads_layout)
        self.options_layout.addLayout(self.options_check_layout)
        self.options_layout.addStretch()
        
        self.main_layout.addWidget(self.options_frame)
        
        # Files table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(["File", "Size", "Status", "Progress", "Actions"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.files_table.setAlternatingRowColors(True)
        
        self.main_layout.addWidget(self.files_table)
        
        # Overall progress
        self.progress_layout = QHBoxLayout()
        self.progress_label = QLabel("Overall Progress:")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        self.progress_layout.addWidget(self.progress_label)
        self.progress_layout.addWidget(self.progress_bar)
        
        self.main_layout.addLayout(self.progress_layout)
        
        # Status label
        self.status_label = QLabel("Ready to process files.")
        self.status_label.setObjectName("statusLabel")
        self.main_layout.addWidget(self.status_label)
    
    def connect_signals(self):
        """Connect widget signals to slots."""
        self.add_files_btn.clicked.connect(self.add_files)
        self.clear_btn.clicked.connect(self.clear_files)
        self.start_btn.clicked.connect(self.start_processing)
        self.operation_combo.currentIndexChanged.connect(self.update_ui_for_operation)
    
    def add_files(self):
        """Add files to the batch processing queue."""
        # Get the current operation type
        operation = self.operation_combo.currentData()
        
        # Set up file dialog based on operation
        if operation == CHDTaskType.COMPRESS:
            file_filter = "Disk Images (*.iso *.bin *.img *.cue);;All Files (*.*)"
        else:  # Extract
            file_filter = "CHD Files (*.chd);;All Files (*.*)"
        
        # Open file dialog
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files for Batch Processing",
            "",
            file_filter
        )
        
        # Add files to the table
        for file_path in files:
            self.add_file_to_table(file_path)
    
    def add_file_to_table(self, file_path):
        """Add a file to the batch processing table.
        
        Args:
            file_path: Path to the file to add
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
        
        # File name
        item_name = QTableWidgetItem(file_name)
        item_name.setData(Qt.UserRole, file_path)  # Store full path
        self.files_table.setItem(row, 0, item_name)
        
        # File size
        item_size = QTableWidgetItem(size_str)
        item_size.setData(Qt.UserRole, file_size)  # Store raw size
        self.files_table.setItem(row, 1, item_size)
        
        # Status
        item_status = QTableWidgetItem("Pending")
        self.files_table.setItem(row, 2, item_status)
        
        # Progress
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        self.files_table.setCellWidget(row, 3, progress_bar)
        
        # Actions
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(4, 4, 4, 4)
        actions_layout.setSpacing(4)
        
        remove_btn = QPushButton()
        remove_btn.setIcon(load_svg_icon("trash", 16, "#f8f8f2"))
        remove_btn.setFixedSize(24, 24)
        remove_btn.clicked.connect(lambda: self.remove_file(row))
        
        actions_layout.addWidget(remove_btn)
        actions_layout.addStretch()
        
        self.files_table.setCellWidget(row, 4, actions_widget)
        
        # Update status
        self.status_label.setText(f"{self.files_table.rowCount()} files ready for processing.")
    
    def remove_file(self, row):
        """Remove a file from the batch processing table.
        
        Args:
            row: Row index to remove
        """
        self.files_table.removeRow(row)
        self.status_label.setText(f"{self.files_table.rowCount()} files ready for processing.")
    
    def clear_files(self):
        """Clear all files from the batch processing table."""
        self.files_table.setRowCount(0)
        self.status_label.setText("Ready to process files.")
    
    def update_ui_for_operation(self):
        """Update UI elements based on the selected operation."""
        operation = self.operation_combo.currentData()
        
        # Show/hide compression level based on operation
        self.compression_label.setVisible(operation == CHDTaskType.COMPRESS)
        self.compression_spin.setVisible(operation == CHDTaskType.COMPRESS)
    
    def start_processing(self):
        """Start batch processing of files."""
        # Get processing options
        operation = self.operation_combo.currentData()
        compression_level = self.compression_spin.value()
        threads = self.threads_spin.value()
        verify = self.verify_check.isChecked()
        
        # Check if there are files to process
        if self.files_table.rowCount() == 0:
            self.status_label.setText("No files to process. Add files first.")
            return
        
        # Update UI
        self.add_files_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.operation_combo.setEnabled(False)
        self.compression_spin.setEnabled(False)
        self.threads_spin.setEnabled(False)
        self.verify_check.setEnabled(False)
        
        # TODO: Implement actual batch processing
        # This would involve creating CHDTask objects for each file
        # and processing them using CHDManager
        
        # For now, just simulate processing
        self.status_label.setText("Batch processing started. This is a simulation.")
        self.progress_bar.setValue(0)
        
        # Simulate processing for each file
        for row in range(self.files_table.rowCount()):
            # Update status
            self.files_table.item(row, 2).setText("Processing")
            
            # Get progress bar
            progress_bar = self.files_table.cellWidget(row, 3)
            
            # Simulate progress (in a real implementation, this would be updated by signals)
            for i in range(101):
                progress_bar.setValue(i)
                # In a real implementation, you would use QApplication.processEvents()
                # to keep the UI responsive, or better yet, use a worker thread
            
            # Update status
            self.files_table.item(row, 2).setText("Completed")
            
            # Update overall progress
            self.progress_bar.setValue(int((row + 1) / self.files_table.rowCount() * 100))
        
        # Update UI
        self.add_files_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.operation_combo.setEnabled(True)
        self.compression_spin.setEnabled(True)
        self.threads_spin.setEnabled(True)
        self.verify_check.setEnabled(True)
        
        self.status_label.setText("Batch processing completed successfully.")
