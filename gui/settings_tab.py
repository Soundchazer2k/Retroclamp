"""Settings tab for RetroClamp.

This module provides the UI and functionality for configuring application settings.
"""

import os
import sys
from typing import Dict, Any, List, Optional

from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QMessageBox, QCheckBox,
    QGroupBox, QFormLayout, QSpinBox, QTabWidget, QScrollArea, QFrame
)

# Import local modules
from modules.app_settings import AppSettings
from modules.ui_functions import load_svg_icon
from core.chdman import CHDManager


class SettingsTab(QWidget):
    """Settings tab widget.
    
    This widget provides a UI for configuring application settings.
    """
    
    def __init__(self, parent=None):
        """Initialize the SettingsTab widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize settings
        self.settings = AppSettings()
        
        # Initialize CHD manager
        self.chd_manager = CHDManager()
        
        # Setup UI
        self.setup_ui()
        self.connect_signals()
        
        # Load settings
        self.load_settings()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Application Settings")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Configure application settings to customize behavior and performance. "
            "Changes will be applied after clicking the Save button."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Create tabs
        self.tabs = QTabWidget()
        # Add the CSS styling here
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #444;
                border-bottom: none;
                border-radius: 4px 4px 0 0;
                background: #333;
                color: #ccc;
            }
            QTabBar::tab:selected {
                background: #6272a4;           /* active tab highlight */
                color: #f8f8f2;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                top: -1px;                     /* overlap with tabs */
            }
        """)
        
        # General settings tab
        self.general_tab = QWidget()
        self.setup_general_tab()
        self.tabs.addTab(self.general_tab, "General")
        
        # CHDMAN settings tab
        self.chdman_tab = QWidget()
        self.setup_chdman_tab()
        self.tabs.addTab(self.chdman_tab, "CHDMAN")
        
        # Performance settings tab
        self.performance_tab = QWidget()
        self.setup_performance_tab()
        self.tabs.addTab(self.performance_tab, "Performance")
        
        # Add tabs to layout
        layout.addWidget(self.tabs)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.setIcon(load_svg_icon("refresh", 16, "#f8f8f2"))
        self.reset_btn.setMinimumWidth(150)
        action_layout.addWidget(self.reset_btn)
        
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setIcon(load_svg_icon("device-floppy", 16, "#f8f8f2"))
        self.save_btn.setMinimumWidth(150)
        action_layout.addWidget(self.save_btn)
        
        layout.addLayout(action_layout)
    
    def setup_general_tab(self):
        """Set up the general settings tab."""
        # Main layout
        layout = QVBoxLayout(self.general_tab)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(20)
        
        # Application behavior
        behavior_group = QGroupBox("Application Behavior")
        behavior_layout = QFormLayout(behavior_group)
        
        # Confirm exit
        self.confirm_exit_check = QCheckBox("Show confirmation dialog when exiting")
        behavior_layout.addRow("", self.confirm_exit_check)
        
        # Remember window position
        self.remember_pos_check = QCheckBox("Remember window position and size")
        behavior_layout.addRow("", self.remember_pos_check)
        
        # Auto-check for updates
        self.check_updates_check = QCheckBox("Check for updates on startup")
        behavior_layout.addRow("", self.check_updates_check)
        
        layout.addWidget(behavior_group)
        
        # File handling
        file_group = QGroupBox("File Handling")
        file_layout = QFormLayout(file_group)
        
        # Default input directory
        input_dir_layout = QHBoxLayout()
        self.input_dir_edit = QLineEdit()
        self.input_dir_edit.setPlaceholderText("Default directory for input files...")
        self.input_dir_browse_btn = QPushButton("Browse")
        self.input_dir_browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        input_dir_layout.addWidget(self.input_dir_edit)
        input_dir_layout.addWidget(self.input_dir_browse_btn)
        file_layout.addRow("Default Input Directory:", input_dir_layout)
        
        # Default output directory
        output_dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Default directory for output files...")
        self.output_dir_browse_btn = QPushButton("Browse")
        self.output_dir_browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(self.output_dir_browse_btn)
        file_layout.addRow("Default Output Directory:", output_dir_layout)
        
        # Default file filters
        self.file_filters_edit = QLineEdit()
        self.file_filters_edit.setPlaceholderText("e.g., *.iso;*.bin;*.img")
        file_layout.addRow("Default File Filters:", self.file_filters_edit)
        
        layout.addWidget(file_group)
        
        # Logging
        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout(logging_group)
        
        # Enable logging
        self.enable_logging_check = QCheckBox("Enable logging")
        logging_layout.addRow("", self.enable_logging_check)
        
        # Log level
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["Debug", "Info", "Warning", "Error", "Critical"])
        logging_layout.addRow("Log Level:", self.log_level_combo)
        
        # Log file
        log_file_layout = QHBoxLayout()
        self.log_file_edit = QLineEdit()
        self.log_file_edit.setPlaceholderText("Path to log file...")
        self.log_file_browse_btn = QPushButton("Browse")
        self.log_file_browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        log_file_layout.addWidget(self.log_file_edit)
        log_file_layout.addWidget(self.log_file_browse_btn)
        logging_layout.addRow("Log File:", log_file_layout)
        
        layout.addWidget(logging_group)
        
        # Add spacer
        layout.addStretch()
    
    def setup_chdman_tab(self):
        """Set up the CHDMAN settings tab."""
        # Main layout
        layout = QVBoxLayout(self.chdman_tab)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(20)
        
        # CHDMAN executable
        chdman_group = QGroupBox("CHDMAN Executable")
        chdman_layout = QFormLayout(chdman_group)
        
        # CHDMAN path
        chdman_path_layout = QHBoxLayout()
        self.chdman_path_edit = QLineEdit()
        self.chdman_path_edit.setPlaceholderText("Path to CHDMAN executable...")
        self.chdman_path_browse_btn = QPushButton("Browse")
        self.chdman_path_browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        chdman_path_layout.addWidget(self.chdman_path_edit)
        chdman_path_layout.addWidget(self.chdman_path_browse_btn)
        chdman_layout.addRow("CHDMAN Path:", chdman_path_layout)
        
        # Auto-detect button
        self.chdman_detect_btn = QPushButton("Auto-Detect CHDMAN")
        self.chdman_detect_btn.setIcon(load_svg_icon("search", 16, "#f8f8f2"))
        chdman_layout.addRow("", self.chdman_detect_btn)
        
        # CHDMAN version
        self.chdman_version_label = QLabel("Not detected")
        chdman_layout.addRow("CHDMAN Version:", self.chdman_version_label)
        
        layout.addWidget(chdman_group)
        
        # Default compression settings
        compression_group = QGroupBox("Default Compression Settings")
        compression_layout = QFormLayout(compression_group)
        
        # Compression level
        self.compression_level_combo = QComboBox()
        self.compression_level_combo.addItems(["None", "Fast", "Normal", "Best"])
        compression_layout.addRow("Compression Level:", self.compression_level_combo)
        
        # Hunk size
        self.hunk_size_combo = QComboBox()
        self.hunk_size_combo.addItems(["4 KB", "8 KB", "16 KB", "32 KB", "64 KB"])
        compression_layout.addRow("Hunk Size:", self.hunk_size_combo)
        
        # Verify after compression
        self.verify_check = QCheckBox("Verify after compression")
        compression_layout.addRow("", self.verify_check)
        
        # Force compression
        self.force_check = QCheckBox("Force compression even if larger")
        compression_layout.addRow("", self.force_check)
        
        layout.addWidget(compression_group)
        
        # Add spacer
        layout.addStretch()
    
    def setup_performance_tab(self):
        """Set up the performance settings tab."""
        # Main layout
        layout = QVBoxLayout(self.performance_tab)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(20)
        
        # Multithreading
        threading_group = QGroupBox("Multithreading")
        threading_layout = QFormLayout(threading_group)
        
        # Enable multithreading
        self.enable_threading_check = QCheckBox("Enable multithreading")
        threading_layout.addRow("", self.enable_threading_check)
        
        # Max threads
        self.max_threads_spin = QSpinBox()
        self.max_threads_spin.setMinimum(1)
        self.max_threads_spin.setMaximum(32)
        threading_layout.addRow("Maximum Threads:", self.max_threads_spin)
        
        layout.addWidget(threading_group)
        
        # Batch processing
        batch_group = QGroupBox("Batch Processing")
        batch_layout = QFormLayout(batch_group)
        
        # Max simultaneous tasks
        self.max_tasks_spin = QSpinBox()
        self.max_tasks_spin.setMinimum(1)
        self.max_tasks_spin.setMaximum(10)
        batch_layout.addRow("Maximum Simultaneous Tasks:", self.max_tasks_spin)
        
        # Auto-start next task
        self.auto_start_check = QCheckBox("Automatically start next task")
        batch_layout.addRow("", self.auto_start_check)
        
        layout.addWidget(batch_group)
        
        # Memory usage
        memory_group = QGroupBox("Memory Usage")
        memory_layout = QFormLayout(memory_group)
        
        # Buffer size
        self.buffer_size_spin = QSpinBox()
        self.buffer_size_spin.setMinimum(1)
        self.buffer_size_spin.setMaximum(64)
        self.buffer_size_spin.setSuffix(" MB")
        memory_layout.addRow("Buffer Size:", self.buffer_size_spin)
        
        # Limit memory usage
        self.limit_memory_check = QCheckBox("Limit memory usage")
        memory_layout.addRow("", self.limit_memory_check)
        
        # Max memory
        self.max_memory_spin = QSpinBox()
        self.max_memory_spin.setMinimum(256)
        self.max_memory_spin.setMaximum(4096)
        self.max_memory_spin.setSuffix(" MB")
        memory_layout.addRow("Maximum Memory:", self.max_memory_spin)
        
        layout.addWidget(memory_group)
        
        # Add spacer
        layout.addStretch()
    
    def connect_signals(self):
        """Connect widget signals to slots."""
        # Browse buttons
        self.input_dir_browse_btn.clicked.connect(self.browse_input_dir)
        self.output_dir_browse_btn.clicked.connect(self.browse_output_dir)
        self.log_file_browse_btn.clicked.connect(self.browse_log_file)
        self.chdman_path_browse_btn.clicked.connect(self.browse_chdman_path)
        
        # CHDMAN detect button
        self.chdman_detect_btn.clicked.connect(self.detect_chdman)
        
        # Action buttons
        self.reset_btn.clicked.connect(self.reset_settings)
        self.save_btn.clicked.connect(self.save_settings)
        
        # Enable/disable controls
        self.enable_logging_check.toggled.connect(self.toggle_logging)
        self.enable_threading_check.toggled.connect(self.toggle_threading)
        self.limit_memory_check.toggled.connect(self.toggle_memory_limit)
    
    def load_settings(self):
        """Load settings from AppSettings."""
        # General settings
        self.confirm_exit_check.setChecked(self.settings.get("general", "confirm_exit", True))
        self.remember_pos_check.setChecked(self.settings.get("general", "remember_position", True))
        self.check_updates_check.setChecked(self.settings.get("general", "check_updates", True))
        
        # File handling
        self.input_dir_edit.setText(self.settings.get("files", "default_input_dir", ""))
        self.output_dir_edit.setText(self.settings.get("files", "default_output_dir", ""))
        self.file_filters_edit.setText(self.settings.get("files", "default_filters", "*.iso;*.bin;*.img;*.cue"))
        
        # Logging
        self.enable_logging_check.setChecked(self.settings.get("logging", "enabled", True))
        self.log_level_combo.setCurrentText(self.settings.get("logging", "level", "Info"))
        self.log_file_edit.setText(self.settings.get("logging", "file", "retroclamp.log"))
        
        # CHDMAN
        self.chdman_path_edit.setText(self.settings.get("chdman", "path", ""))
        self.compression_level_combo.setCurrentText(self.settings.get("chdman", "compression_level", "Normal"))
        self.hunk_size_combo.setCurrentText(self.settings.get("chdman", "hunk_size", "16 KB"))
        self.verify_check.setChecked(self.settings.get("chdman", "verify", True))
        self.force_check.setChecked(self.settings.get("chdman", "force", False))
        
        # Performance
        self.enable_threading_check.setChecked(self.settings.get("performance", "multithreading", True))
        self.max_threads_spin.setValue(self.settings.get("performance", "max_threads", 4))
        self.max_tasks_spin.setValue(self.settings.get("performance", "max_tasks", 2))
        self.auto_start_check.setChecked(self.settings.get("performance", "auto_start", True))
        self.buffer_size_spin.setValue(self.settings.get("performance", "buffer_size", 8))
        self.limit_memory_check.setChecked(self.settings.get("performance", "limit_memory", False))
        self.max_memory_spin.setValue(self.settings.get("performance", "max_memory", 1024))
        
        # Update CHDMAN version
        self.update_chdman_version()
        
        # Update enabled/disabled states
        self.toggle_logging(self.enable_logging_check.isChecked())
        self.toggle_threading(self.enable_threading_check.isChecked())
        self.toggle_memory_limit(self.limit_memory_check.isChecked())
    
    @Slot()
    def browse_input_dir(self):
        """Browse for default input directory."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Default Input Directory",
            self.input_dir_edit.text()
        )
        
        if path:
            self.input_dir_edit.setText(path)
    
    @Slot()
    def browse_output_dir(self):
        """Browse for default output directory."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Default Output Directory",
            self.output_dir_edit.text()
        )
        
        if path:
            self.output_dir_edit.setText(path)
    
    @Slot()
    def browse_log_file(self):
        """Browse for log file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Log File",
            self.log_file_edit.text(),
            "Log Files (*.log);;All Files (*.*)"
        )
        
        if path:
            self.log_file_edit.setText(path)
    
    @Slot()
    def browse_chdman_path(self):
        """Browse for CHDMAN executable."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CHDMAN Executable",
            self.chdman_path_edit.text(),
            "Executables (*.exe);;All Files (*.*)"
        )
        
        if path:
            self.chdman_path_edit.setText(path)
            self.update_chdman_version()
    
    @Slot()
    def detect_chdman(self):
        """Auto-detect CHDMAN executable."""
        # Try to detect CHDMAN
        chdman_path = self.chd_manager.find_chdman()
        
        if chdman_path and os.path.exists(chdman_path):
            self.chdman_path_edit.setText(chdman_path)
            self.update_chdman_version()
            
            QMessageBox.information(
                self,
                "CHDMAN Detected",
                f"CHDMAN executable found at:\n{chdman_path}"
            )
        else:
            QMessageBox.warning(
                self,
                "CHDMAN Not Found",
                "Could not automatically detect CHDMAN executable. "
                "Please specify the path manually."
            )
    
    def update_chdman_version(self):
        """Update CHDMAN version label."""
        chdman_path = self.chdman_path_edit.text()
        
        if chdman_path and os.path.exists(chdman_path):
            # Get CHDMAN version
            version = self.chd_manager.get_chdman_version(chdman_path)
            
            if version:
                self.chdman_version_label.setText(version)
                return
        
        self.chdman_version_label.setText("Not detected")
    
    @Slot(bool)
    def toggle_logging(self, enabled):
        """Toggle logging controls based on checkbox state.
        
        Args:
            enabled: Whether logging is enabled
        """
        self.log_level_combo.setEnabled(enabled)
        self.log_file_edit.setEnabled(enabled)
        self.log_file_browse_btn.setEnabled(enabled)
    
    @Slot(bool)
    def toggle_threading(self, enabled):
        """Toggle threading controls based on checkbox state.
        
        Args:
            enabled: Whether multithreading is enabled
        """
        self.max_threads_spin.setEnabled(enabled)
    
    @Slot(bool)
    def toggle_memory_limit(self, enabled):
        """Toggle memory limit controls based on checkbox state.
        
        Args:
            enabled: Whether memory limit is enabled
        """
        self.max_memory_spin.setEnabled(enabled)
    
    @Slot()
    def reset_settings(self):
        """Reset settings to default."""
        # Confirm reset
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to default?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Reset settings
        self.settings.reset_settings()
        
        # Reload settings
        self.load_settings()
        
        # Show success message
        QMessageBox.information(
            self,
            "Settings Reset",
            "All settings have been reset to default."
        )
    
    @Slot()
    def save_settings(self):
        """Save settings to AppSettings."""
        # General settings
        self.settings.set("general", "confirm_exit", self.confirm_exit_check.isChecked())
        self.settings.set("general", "remember_position", self.remember_pos_check.isChecked())
        self.settings.set("general", "check_updates", self.check_updates_check.isChecked())
        
        # File handling
        self.settings.set("files", "default_input_dir", self.input_dir_edit.text())
        self.settings.set("files", "default_output_dir", self.output_dir_edit.text())
        self.settings.set("files", "default_filters", self.file_filters_edit.text())
        
        # Logging
        self.settings.set("logging", "enabled", self.enable_logging_check.isChecked())
        self.settings.set("logging", "level", self.log_level_combo.currentText())
        self.settings.set("logging", "file", self.log_file_edit.text())
        
        # CHDMAN
        self.settings.set("chdman", "path", self.chdman_path_edit.text())
        self.settings.set("chdman", "compression_level", self.compression_level_combo.currentText())
        self.settings.set("chdman", "hunk_size", self.hunk_size_combo.currentText())
        self.settings.set("chdman", "verify", self.verify_check.isChecked())
        self.settings.set("chdman", "force", self.force_check.isChecked())
        
        # Performance
        self.settings.set("performance", "multithreading", self.enable_threading_check.isChecked())
        self.settings.set("performance", "max_threads", self.max_threads_spin.value())
        self.settings.set("performance", "max_tasks", self.max_tasks_spin.value())
        self.settings.set("performance", "auto_start", self.auto_start_check.isChecked())
        self.settings.set("performance", "buffer_size", self.buffer_size_spin.value())
        self.settings.set("performance", "limit_memory", self.limit_memory_check.isChecked())
        self.settings.set("performance", "max_memory", self.max_memory_spin.value())
        
        # Save settings
        self.settings.save_settings()
        
        # Show success message
        QMessageBox.information(
            self,
            "Settings Saved",
            "Settings have been saved successfully."
        )
    
    def closeEvent(self, event):
        """Handle close events.
        
        Args:
            event: Close event
        """
        # Save settings
        self.settings.save_settings()
        
        # Call parent method
        super().closeEvent(event)
