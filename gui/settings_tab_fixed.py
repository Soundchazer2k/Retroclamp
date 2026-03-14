"""Fixed Settings tab with unified layout approach.

Demonstrates proper form layout patterns and consistent styling.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QWidget,
)

from core.chdman import CHDManager
from gui.layout_utils import StandardFormLayout
from modules.app_settings import AppSettings
from modules.settings import load_chdman_path, save_chdman_path


class FixedSettingsTab(QWidget):
    """Settings tab with proper unified layout and styling."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = AppSettings()
        self.chd_manager = CHDManager()

        self.setup_ui()
        self.connect_signals()
        self.load_settings()

    def setup_ui(self):
        """Set up the user interface using unified layout patterns."""
        # Create main layout with title and description
        main_layout = StandardFormLayout.create_main_layout(
            self,
            title="Application Settings",
            description="Configure application settings to customize behavior and performance. "
            "Changes will be applied after clicking the Save button.",
        )

        # Create tabbed interface without per-tab stylesheets
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Create each tab using unified layout approach
        self.create_general_tab()
        self.create_chdman_tab()
        self.create_performance_tab()

        # Create unified button bar
        save_btn = QPushButton("Save Settings")
        reset_btn = QPushButton("Reset to Default")

        StandardFormLayout.create_button_bar([reset_btn, save_btn], main_layout)

        # Store button references
        self.save_btn = save_btn
        self.reset_btn = reset_btn

    def create_general_tab(self):
        """Create General settings tab with unified form layout."""
        tab = QWidget()
        layout = StandardFormLayout.create_main_layout(tab)

        # Application Behavior group
        app_group, app_form = StandardFormLayout.create_form_group(
            "Application Behavior", layout
        )

        self.confirm_exit_cb = QCheckBox()
        StandardFormLayout.add_form_field(
            app_form, "Confirm on exit:", self.confirm_exit_cb
        )

        self.save_window_state_cb = QCheckBox()
        StandardFormLayout.add_form_field(
            app_form, "Save window state:", self.save_window_state_cb
        )

        # Logging group
        log_group, log_form = StandardFormLayout.create_form_group("Logging", layout)

        self.enable_logging_cb = QCheckBox()
        StandardFormLayout.add_form_field(
            log_form, "Enable logging:", self.enable_logging_cb
        )

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        StandardFormLayout.add_form_field(log_form, "Log level:", self.log_level_combo)

        # Interface group
        ui_group, ui_form = StandardFormLayout.create_form_group(
            "User Interface", layout
        )

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        StandardFormLayout.add_form_field(ui_form, "Theme:", self.theme_combo)

        # Add tab
        self.tabs.addTab(tab, "General")

    def create_chdman_tab(self):
        """Create CHDMAN settings tab with unified form layout."""
        tab = QWidget()
        layout = StandardFormLayout.create_main_layout(tab)

        # CHDMAN Configuration group
        chdman_group, chdman_form = StandardFormLayout.create_form_group(
            "CHDMAN Configuration", layout
        )

        # CHDMAN path with browse button
        self.chdman_path_edit = QLineEdit()
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_chdman_path)

        # Create horizontal layout for path + browse button
        from PySide6.QtWidgets import QHBoxLayout

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.chdman_path_edit)
        path_layout.addWidget(browse_btn)
        path_layout.setSpacing(8)

        from PySide6.QtWidgets import QWidget as LayoutWidget

        path_widget = LayoutWidget()
        path_widget.setLayout(path_layout)
        StandardFormLayout.add_form_field(
            chdman_form, "CHDMAN executable:", path_widget
        )

        self.auto_detect_cb = QCheckBox()
        StandardFormLayout.add_form_field(
            chdman_form, "Auto-detect CHDMAN:", self.auto_detect_cb
        )

        # Compression Options group
        comp_group, comp_form = StandardFormLayout.create_form_group(
            "Compression Options", layout
        )

        self.default_compression_combo = QComboBox()
        self.default_compression_combo.addItems(["ZLIB", "LZMA", "FLAC", "HUNK"])
        StandardFormLayout.add_form_field(
            comp_form, "Default compression:", self.default_compression_combo
        )

        self.verify_output_cb = QCheckBox()
        StandardFormLayout.add_form_field(
            comp_form, "Verify output files:", self.verify_output_cb
        )

        # Add tab
        self.tabs.addTab(tab, "CHDMAN")

    def create_performance_tab(self):
        """Create Performance settings tab with unified form layout."""
        tab = QWidget()
        layout = StandardFormLayout.create_main_layout(tab)

        # Multithreading group
        thread_group, thread_form = StandardFormLayout.create_form_group(
            "Multithreading", layout
        )

        self.enable_multithreading_cb = QCheckBox()
        StandardFormLayout.add_form_field(
            thread_form, "Enable multithreading:", self.enable_multithreading_cb
        )

        self.max_threads_spin = QSpinBox()
        self.max_threads_spin.setRange(1, 16)
        self.max_threads_spin.setValue(4)
        StandardFormLayout.add_form_field(
            thread_form, "Maximum threads:", self.max_threads_spin
        )

        # Batch Processing group
        batch_group, batch_form = StandardFormLayout.create_form_group(
            "Batch Processing", layout
        )

        self.max_simultaneous_spin = QSpinBox()
        self.max_simultaneous_spin.setRange(1, 8)
        self.max_simultaneous_spin.setValue(2)
        StandardFormLayout.add_form_field(
            batch_form, "Maximum simultaneous tasks:", self.max_simultaneous_spin
        )

        self.auto_start_cb = QCheckBox()
        StandardFormLayout.add_form_field(
            batch_form, "Automatically start next task:", self.auto_start_cb
        )

        # Memory Usage group
        memory_group, memory_form = StandardFormLayout.create_form_group(
            "Memory Usage", layout
        )

        self.buffer_size_edit = QLineEdit()
        self.buffer_size_edit.setText("8 MB")
        StandardFormLayout.add_form_field(
            memory_form, "Buffer size:", self.buffer_size_edit
        )

        self.limit_memory_cb = QCheckBox()
        StandardFormLayout.add_form_field(
            memory_form, "Limit memory usage:", self.limit_memory_cb
        )

        self.max_memory_edit = QLineEdit()
        self.max_memory_edit.setText("1024 MB")
        StandardFormLayout.add_form_field(
            memory_form, "Maximum memory:", self.max_memory_edit
        )

        # Add tab
        self.tabs.addTab(tab, "Performance")

    def connect_signals(self):
        """Connect widget signals to slots."""
        self.save_btn.clicked.connect(self.save_settings)
        self.reset_btn.clicked.connect(self.reset_settings)

        # Auto-detect CHDMAN when checkbox changes
        self.auto_detect_cb.toggled.connect(self.on_auto_detect_toggled)

    def browse_chdman_path(self):
        """Browse for CHDMAN executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CHDMAN Executable",
            "",
            "Executable files (*.exe);;All files (*)",
        )

        if file_path:
            self.chdman_path_edit.setText(file_path)

    def on_auto_detect_toggled(self, checked):
        """Handle auto-detect checkbox toggle."""
        if checked:
            # Try to auto-detect CHDMAN
            detected_path = self.chd_manager.find_chdman_executable()
            if detected_path:
                self.chdman_path_edit.setText(detected_path)
            else:
                QMessageBox.warning(
                    self,
                    "Auto-detect Failed",
                    "Could not automatically detect CHDMAN executable. "
                    "Please browse for it manually.",
                )
                self.auto_detect_cb.setChecked(False)

    def load_settings(self):
        """Load settings from configuration."""
        # General settings
        self.confirm_exit_cb.setChecked(
            self.settings.get("general", "confirm_exit", True)
        )
        self.save_window_state_cb.setChecked(
            self.settings.get("general", "save_window_state", True)
        )

        # Logging settings
        self.enable_logging_cb.setChecked(self.settings.get("logging", "enabled", True))
        log_level = self.settings.get("logging", "log_level", "DEBUG")
        index = self.log_level_combo.findText(log_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)

        # CHDMAN settings
        chdman_path = load_chdman_path()
        if chdman_path:
            self.chdman_path_edit.setText(chdman_path)

        # Performance settings
        self.enable_multithreading_cb.setChecked(
            self.settings.get("performance", "enable_multithreading", True)
        )
        self.max_threads_spin.setValue(
            self.settings.get("performance", "max_threads", 4)
        )

    def save_settings(self):
        """Save current settings to configuration."""
        # General settings
        self.settings.set("general", "confirm_exit", self.confirm_exit_cb.isChecked())
        self.settings.set(
            "general", "save_window_state", self.save_window_state_cb.isChecked()
        )

        # Logging settings
        self.settings.set("logging", "enabled", self.enable_logging_cb.isChecked())
        self.settings.set("logging", "log_level", self.log_level_combo.currentText())

        # CHDMAN settings
        chdman_path = self.chdman_path_edit.text().strip()
        if chdman_path:
            save_chdman_path(chdman_path)

        # Performance settings
        self.settings.set(
            "performance",
            "enable_multithreading",
            self.enable_multithreading_cb.isChecked(),
        )
        self.settings.set("performance", "max_threads", self.max_threads_spin.value())

        # Save to file
        self.settings.save_settings()

        QMessageBox.information(
            self, "Settings Saved", "Settings have been saved successfully."
        )

    def reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Reset to defaults and reload
            self.settings.reset_to_defaults()
            self.load_settings()

            QMessageBox.information(
                self, "Settings Reset", "Settings have been reset to default values."
            )
