# Placeholder for DebugLogger tests
import os

# Adjust the path to import DebugLogger from the core directory
import sys
import time
import unittest
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from core.debug_logger import DebugLogger


# Mock AppSettings for testing purposes
class MockAppSettings:
    def __init__(self):
        self.settings = {
            "advanced/debug_logging_enabled": True,
            "advanced/max_log_file_size_mb": 1,
            "advanced/log_backup_count": 1,
        }

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


class TestDebugLogger(unittest.TestCase):
    def setUp(self):
        self.mock_app_settings = MockAppSettings()
        # Patch QStandardPaths to return a temporary test directory
        self.patcher = patch("core.debug_logger.QStandardPaths")
        self.mock_qstd_paths = self.patcher.start()
        self.mock_qstd_paths.writableLocation.return_value = os.path.join(
            BASE_DIR, "tests", "temp_log_dir"
        )
        self.test_log_dir_base = os.path.join(BASE_DIR, "tests", "temp_log_dir")
        self.test_log_dir_app = os.path.join(
            self.test_log_dir_base, "RetroClamp", "logs"
        )
        os.makedirs(self.test_log_dir_app, exist_ok=True)
        self.logger = DebugLogger(settings_accessor=lambda: self.mock_app_settings)
        self.log_file_path = self.logger.get_log_file_path()

    def tearDown(self):
        self.patcher.stop()
        if self.logger and self.logger._handler:
            self.logger._handler.close()
            self.logger.logger.removeHandler(self.logger._handler)
            self.logger._handler = None
        log_file_to_remove = os.path.join(self.test_log_dir_app, "chdman_gui_debug.log")
        if os.path.exists(log_file_to_remove):
            os.remove(log_file_to_remove)
        backup_log_file = log_file_to_remove + ".1"
        if os.path.exists(backup_log_file):
            os.remove(backup_log_file)
        try:
            os.rmdir(self.test_log_dir_app)
            os.rmdir(os.path.dirname(self.test_log_dir_app))
            os.rmdir(self.test_log_dir_base)
        except OSError:
            pass

    def test_logger_initialization_enabled(self):
        self.mock_app_settings.set_setting("advanced/debug_logging_enabled", True)
        self.logger.configure_handler()
        self.assertTrue(self.logger.is_enabled())
        self.assertIsNotNone(
            self.logger._handler, "Handler should be configured when logging is enabled"
        )
        self.assertTrue(
            os.path.exists(self.logger.get_log_file_path()),
            "Log file should be created",
        )

    def test_logger_initialization_disabled(self):
        self.mock_app_settings.set_setting("advanced/debug_logging_enabled", False)
        self.logger.configure_handler()
        self.assertFalse(self.logger.is_enabled())
        self.assertIsNone(
            self.logger._handler,
            "Handler should not be configured when logging is disabled",
        )

    def test_log_file_path_creation(self):
        expected_path_part = os.path.join(
            "tests", "temp_log_dir", "RetroClamp", "logs", "chdman_gui_debug.log"
        )
        self.assertTrue(self.log_file_path.endswith(expected_path_part))
        # Directory creation is implicitly tested by setUp and initialization tests

    def test_logging_debug_message(self):
        self.logger.debug("TEST_MODULE", "This is a debug message.")
        with open(self.log_file_path) as f:
            content = f.read()
        self.assertIn(
            "[DEBUG  ] [debug_logger   ] [TEST_MODULE] This is a debug message.",
            content,
        )

    def test_logging_info_message(self):
        self.logger.info("INFO_MOD", "This is an info message.")
        with open(self.log_file_path) as f:
            content = f.read()
        self.assertIn(
            "[INFO   ] [debug_logger   ] [INFO_MOD] This is an info message.", content
        )

    def test_logging_warning_message(self):
        self.logger.warning("WARN_MOD", "This is a warning message.")
        with open(self.log_file_path) as f:
            content = f.read()
        self.assertIn(
            "[WARNING] [debug_logger   ] [WARN_MOD] This is a warning message.", content
        )

    def test_logging_error_message(self):
        self.logger.error("ERR_MOD", "This is an error message.")
        with open(self.log_file_path) as f:
            content = f.read()
        self.assertIn(
            "[ERROR  ] [debug_logger   ] [ERR_MOD] This is an error message.", content
        )

    def test_log_rotation(self):
        # Ensure logging is enabled for this test
        self.mock_app_settings.set_setting("advanced/debug_logging_enabled", True)
        self.logger.configure_handler()

        # Set max size to something very small for testing
        self.mock_app_settings.set_setting(
            "advanced/max_log_file_size_mb", 0.001
        )  # 1KB
        self.logger.configure_handler()  # Reconfigure with new size settings

        # Log enough data to trigger rotation
        # Each log message is ~100 bytes. 1KB = 1024 bytes. Need > 10 messages.
        for i in range(20):
            self.logger.info("ROTATION_TEST", f"Logging line {i} to test rotation.")

        time.sleep(0.1)  # Add a small delay for file system operations
        # Check if backup file exists (e.g., chdman_gui_debug.log.1)
        backup_log_file = self.log_file_path + ".1"
        self.assertTrue(
            os.path.exists(backup_log_file),
            "Backup log file should exist after rotation.",
        )


if __name__ == "__main__":
    unittest.main()
