"""SCUMMVM Generator tool for RetroClamp.

This plugin provides functionality for generating SCUMMVM configuration files
for compressed game files.
"""

import os
import re
from typing import Dict, Any, List, Optional

from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QCheckBox, QGroupBox, QFormLayout
)

from modules.ui_functions import load_svg_icon

# Plugin metadata
PLUGIN_NAME = "SCUMMVM Generator"
PLUGIN_DESCRIPTION = "Generate SCUMMVM configuration files for compressed game files"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "RetroClamp Team"

# SCUMMVM game engines
SCUMMVM_ENGINES = [
    "scumm", "sci", "agi", "agos", "avalanche", "bbvs", "bladerunner",
    "cge", "cge2", "cine", "composer", "cruise", "cryomni3d", "draci",
    "dragons", "drascula", "dreamweb", "glk", "gnap", "gob", "groovie",
    "hopkins", "hugo", "illusions", "kingdom", "kyra", "lab", "lure",
    "made", "mohawk", "mortevielle", "myst", "neverhood", "parallaction",
    "pegasus", "plumbers", "prince", "queen", "saga", "sci", "scumm",
    "sherlock", "sky", "sword1", "sword2", "sword25", "teenagent",
    "tetraedge", "tinsel", "titanic", "toltecs", "tony", "toon",
    "touche", "tsage", "tucker", "twine", "voyeur", "wintermute", "zvision"
]


class ScummVMGenerator(QWidget):
    """SCUMMVM Generator widget.
    
    This widget provides a UI for generating SCUMMVM configuration files.
    """
    
    def __init__(self, parent=None):
        """Initialize the ScummVMGenerator widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("SCUMMVM Configuration Generator")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Generate SCUMMVM configuration files (.scummvm) for your compressed game files. "
            "These files help SCUMMVM identify and launch your games correctly."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Game path selection
        path_group = QGroupBox("Game Path")
        path_layout = QHBoxLayout(path_group)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select game directory or CHD file...")
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        path_layout.addWidget(self.browse_btn)
        
        layout.addWidget(path_group)
        
        # Game configuration
        config_group = QGroupBox("Game Configuration")
        config_layout = QFormLayout(config_group)
        
        # Game ID
        self.game_id_edit = QLineEdit()
        self.game_id_edit.setPlaceholderText("e.g., monkey1, atlantis, etc.")
        config_layout.addRow("Game ID:", self.game_id_edit)
        
        # Game title
        self.game_title_edit = QLineEdit()
        self.game_title_edit.setPlaceholderText("e.g., The Secret of Monkey Island")
        config_layout.addRow("Game Title:", self.game_title_edit)
        
        # Game engine
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(SCUMMVM_ENGINES)
        self.engine_combo.setCurrentText("scumm")  # Default to SCUMM engine
        config_layout.addRow("Engine:", self.engine_combo)
        
        # Language
        self.language_combo = QComboBox()
        self.language_combo.addItems(["en", "de", "fr", "it", "es", "pt", "jp", "zh", "kr", "ru"])
        config_layout.addRow("Language:", self.language_combo)
        
        # Platform
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["pc", "amiga", "atari", "macintosh", "windows", "dos"])
        config_layout.addRow("Platform:", self.platform_combo)
        
        # Additional options
        self.subtitles_check = QCheckBox("Enable Subtitles")
        self.subtitles_check.setChecked(True)
        config_layout.addRow("", self.subtitles_check)
        
        layout.addWidget(config_group)
        
        # Output configuration
        output_group = QGroupBox("Output Configuration")
        output_layout = QFormLayout(output_group)
        
        # Output path
        output_path_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Same as game directory")
        output_path_layout.addWidget(self.output_path_edit)
        
        self.output_browse_btn = QPushButton("Browse")
        self.output_browse_btn.setIcon(load_svg_icon("folder", 16, "#f8f8f2"))
        output_path_layout.addWidget(self.output_browse_btn)
        
        output_layout.addRow("Output Directory:", output_path_layout)
        
        # Use game directory as output
        self.use_game_dir_check = QCheckBox("Use game directory")
        self.use_game_dir_check.setChecked(True)
        output_layout.addRow("", self.use_game_dir_check)
        
        layout.addWidget(output_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.generate_btn = QPushButton("Generate Configuration")
        self.generate_btn.setIcon(load_svg_icon("file-check", 16, "#f8f8f2"))
        self.generate_btn.setMinimumWidth(200)
        buttons_layout.addWidget(self.generate_btn)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
    
    def connect_signals(self):
        """Connect widget signals to slots."""
        self.browse_btn.clicked.connect(self.browse_game_path)
        self.output_browse_btn.clicked.connect(self.browse_output_path)
        self.use_game_dir_check.toggled.connect(self.toggle_output_path)
        self.generate_btn.clicked.connect(self.generate_config)
        self.path_edit.textChanged.connect(self.update_game_info)
    
    @Slot()
    def browse_game_path(self):
        """Browse for a game path."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Game File",
            "",
            "Game Files (*.chd *.iso *.bin);;All Files (*.*)"
        )
        
        if path:
            self.path_edit.setText(path)
    
    @Slot()
    def browse_output_path(self):
        """Browse for an output path."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            ""
        )
        
        if path:
            self.output_path_edit.setText(path)
            self.use_game_dir_check.setChecked(False)
    
    @Slot(bool)
    def toggle_output_path(self, checked):
        """Toggle output path based on checkbox state.
        
        Args:
            checked: Whether the checkbox is checked
        """
        self.output_path_edit.setEnabled(not checked)
        self.output_browse_btn.setEnabled(not checked)
        
        if checked:
            self.output_path_edit.clear()
    
    @Slot()
    def update_game_info(self):
        """Update game information based on the selected path."""
        path = self.path_edit.text()
        
        if not path:
            return
        
        # Extract game ID and title from filename
        filename = os.path.basename(path)
        name, _ = os.path.splitext(filename)
        
        # Try to guess game ID (lowercase, no spaces, special chars)
        game_id = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
        
        # Set game ID if empty
        if not self.game_id_edit.text():
            self.game_id_edit.setText(game_id)
        
        # Set game title if empty
        if not self.game_title_edit.text():
            self.game_title_edit.setText(name)
    
    @Slot()
    def generate_config(self):
        """Generate the SCUMMVM configuration file."""
        # Validate inputs
        game_path = self.path_edit.text()
        if not game_path or not os.path.exists(game_path):
            QMessageBox.warning(self, "Error", "Please select a valid game path.")
            return
        
        game_id = self.game_id_edit.text()
        if not game_id:
            QMessageBox.warning(self, "Error", "Please enter a game ID.")
            return
        
        game_title = self.game_title_edit.text()
        if not game_title:
            QMessageBox.warning(self, "Error", "Please enter a game title.")
            return
        
        # Determine output path
        if self.use_game_dir_check.isChecked():
            if os.path.isfile(game_path):
                output_dir = os.path.dirname(game_path)
            else:
                output_dir = game_path
        else:
            output_dir = self.output_path_edit.text()
            if not output_dir or not os.path.isdir(output_dir):
                QMessageBox.warning(self, "Error", "Please select a valid output directory.")
                return
        
        # Create config content
        config = f"[{game_id}]\n"
        config += f"description={game_title}\n"
        config += f"path={game_path}\n"
        config += f"engine={self.engine_combo.currentText()}\n"
        config += f"language={self.language_combo.currentText()}\n"
        config += f"platform={self.platform_combo.currentText()}\n"
        
        if self.subtitles_check.isChecked():
            config += "subtitles=true\n"
        
        # Write config file
        config_path = os.path.join(output_dir, f"{game_id}.scummvm")
        try:
            with open(config_path, 'w') as f:
                f.write(config)
            
            QMessageBox.information(
                self,
                "Success",
                f"SCUMMVM configuration file created successfully:\n{config_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create configuration file:\n{str(e)}"
            )


def register_tab(parent_widget):
    """Register the SCUMMVM Generator tab.
    
    Args:
        parent_widget: Parent widget to add the tab to
    """
    # Create the widget
    widget = ScummVMGenerator(parent_widget)
    
    # Add to parent (assuming parent is a QTabWidget)
    parent_widget.addTab(widget, load_svg_icon("device-gamepad", 16, "#f8f8f2"), "SCUMMVM Generator")
