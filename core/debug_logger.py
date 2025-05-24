"""Debug Logging System for RetroClamp."""

import logging
import os
import platform
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..modules.app_settings import AppSettings


class DebugLogger:
    """Handles debug logging operations for the application."""

    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    DEFAULT_LOG_FILENAME = "chdman_gui_debug.log"  # Synced with PRD-001
    DEFAULT_MAX_SIZE_MB = 10  # Reverted to original default
    DEFAULT_BACKUP_COUNT = 1  # Reverted to original default

    def __init__(
        self,
        app_name: str = "RetroClamp",
        settings: Optional["AppSettings"] = None,
        max_log_file_size_mb: int = DEFAULT_MAX_SIZE_MB,
        log_backup_count: int = DEFAULT_BACKUP_COUNT,
        module_name: Optional[str] = None,
    ):
        """Initialize the logger.

        Args:
            app_name: Name of the application.
            settings: The AppSettings instance.
            max_log_file_size_mb: Maximum log file size in MB.
            log_backup_count: Number of log file backups.
            module_name: Name of the module using the logger.
        """
        self.app_name = app_name
        self.settings = settings  # To get AppSettings instance
        self.module_name = module_name
        self.logger = logging.getLogger(self.app_name)
        self.logger.setLevel(logging.DEBUG)  # Process all, handler filters
        self._handler: Optional[RotatingFileHandler] = None
        self._formatter = logging.Formatter(
            fmt=(
                "[%(asctime)s.%(msecs)03d] [%(levelname)-7s] "
                "[%(module_name_override)-15s] %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.configure_handler(max_log_file_size_mb, log_backup_count)

    def get_log_file_path(self) -> str:
        """Get the full path to the log file."""
        try:
            app_name_for_path = self.app_name.replace(" ", "_").lower()
            app_name_folder = self.app_name.replace(" ", "")

            base_data_path = None
            if platform.system() == "Windows":
                local_app_data = os.environ.get("LOCALAPPDATA")
                if local_app_data:
                    base_data_path = os.path.join(local_app_data, app_name_folder)

            if not base_data_path:
                user_home = os.path.expanduser("~")
                hidden_app_folder = f".{app_name_folder}"
                base_data_path = os.path.join(user_home, hidden_app_folder)

            log_dir = os.path.join(base_data_path, "logs")

            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            final_log_path = os.path.join(log_dir, f"{app_name_for_path}.log")
            return final_log_path
        except Exception as e:
            # Fallback to a local log file in CWD in case of any error
            # Use basic print for this critical fallback, as logger might be the issue.
            print(
                f"[DebugLogger] CRITICAL ERROR in get_log_file_path: {e}."
                f" Falling back to CWD."
            )
            local_log_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(local_log_dir, exist_ok=True)
            fallback_path = os.path.join(
                local_log_dir, f"{app_name_for_path}_fallback.log"
            )
            return fallback_path

    def is_enabled(self) -> bool:
        """Check if logging is enabled based on app settings."""
        if self.settings:
            return bool(self.settings.get("advanced", "debug_logging_enabled", False))
        return False  # Default to False if settings not accessible

    def configure_handler(
        self,
        max_log_file_size_mb: int = DEFAULT_MAX_SIZE_MB,  # Use class default
        log_backup_count: int = DEFAULT_BACKUP_COUNT,  # Use class default
    ):
        """Configures the file handler based on current settings."""
        if self.is_enabled():
            if self._handler is not None:
                self.logger.removeHandler(self._handler)
                self._handler.close()
                self._handler = None

            log_file_path = self.get_log_file_path()
            # Get settings, falling back to the passed-in defaults
            default_max_size = max_log_file_size_mb
            if self.settings:
                max_size_setting = self.settings.get(
                    "advanced", "max_log_file_size_mb", default_max_size
                )
                backup_count_setting = self.settings.get(
                    "advanced", "log_backup_count", log_backup_count
                )
            else:
                max_size_setting = default_max_size
                backup_count_setting = log_backup_count
            max_bytes = int(max_size_setting * 1024 * 1024)

            self._handler = RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=backup_count_setting,
                encoding="utf-8",
            )
            self._handler.setFormatter(self._formatter)
            self.logger.addHandler(self._handler)
        else:
            if self._handler is not None:
                self.logger.removeHandler(self._handler)
                self._handler.close()
                self._handler = None

    def _get_effective_module_name(self, module_name: Optional[str]) -> str:
        """Determines the module name to be used in the log record."""
        return module_name or self.module_name or "DefaultModule"

    def _log(
        self, level: int, module_name: Optional[str], message: str, *args, exc_info=None
    ):
        if not self.is_enabled():
            return

        if not self.logger or not self.logger.hasHandlers():
            # Attempt to get logger name robustly
            logger_name_str = "UnknownLogger"
            try:
                if hasattr(self, "logger_name") and self.logger_name:
                    logger_name_str = self.logger_name
                elif hasattr(self, "app_name") and self.app_name:
                    logger_name_str = self.app_name
            except AttributeError:
                pass  # Keep UnknownLogger

            err_msg_part1 = (
                f"[DebugLogger] CRITICAL: Logger not init for '{logger_name_str}'."
            )
            msg_details = f"{level} - {module_name} - {message}"
            err_msg_part2 = f"  Msg: {msg_details} - Args: {str(args)[:30]}..."
            print(f"{err_msg_part1}\n{err_msg_part2}")
            return

        effective_module_name = self._get_effective_module_name(module_name)
        extra_info = {"module_name_override": effective_module_name}

        self.logger.log(level, message, *args, exc_info=exc_info, extra=extra_info)

    def debug(self, module_name: Optional[str], message: str, *args):
        """Log a debug message."""
        self._log(logging.DEBUG, module_name, message, *args)

    def info(self, module_name: Optional[str], message: str, *args):
        """Log an info message."""
        self._log(logging.INFO, module_name, message, *args)

    def warning(self, module_name: Optional[str], message: str, *args):
        """Log a warning message."""
        self._log(logging.WARNING, module_name, message, *args)

    def error(self, module_name: Optional[str], message: str, *args):
        """Log an error message."""
        self._log(logging.ERROR, module_name, message, *args)

    def exception(self, module_name: Optional[str], message: str, *args):
        """Log an error message with exception information."""
        self._log(logging.ERROR, module_name, message, *args, exc_info=True)

    def log_system_info(self):
        """Logs basic system and application information."""
        if not self.is_enabled():
            return
        try:
            self.info(None, f"OS: {platform.system()} {platform.release()}")
            self.info(None, f"Python Version: {platform.python_version()}")
            self.info(None, f"App Name: {self.app_name}")
        except Exception as e:
            error_message = f"Failed to log system info: {str(e)}"
            self.error(None, error_message)

    def log_chdman_execution(
        self,
        command: str,
        working_dir: str,
        exit_code: int,
        duration: float,
        output: str,
    ):
        if not self.is_enabled():
            return
        log_message = (
            f"CHDMAN Command: {command} | WD: {working_dir} | "
            f"Exit Code: {exit_code} | Duration: {duration:.2f}s"
        )
        self.info(None, log_message)
        if exit_code != 0 and output:
            self.warning(None, f"CHDMAN Output: {output.strip()}")


# Global logger instance
_logger_instance: Optional[DebugLogger] = None


def get_logger(
    settings: "AppSettings", module_name: Optional[str] = None
) -> Optional[DebugLogger]:
    """Factory function to get the DebugLogger instance."""
    global _logger_instance
    if _logger_instance is None:
        try:
            _logger_instance = DebugLogger(settings=settings)
            # Initial log to confirm it's working and to create the log file early
            _logger_instance.info(
                "DebugLogger.get_logger", "Singleton DebugLogger initialized."
            )
        except Exception as e:
            # Fallback to console print if logger initialization fails catastrophically
            print(f"[DebugLogger] CRITICAL: Failed to initialize DebugLogger: {e}")
            # We might return None or raise. For now, allow app to try to continue
            # without file logging if this critical step fails.
            return None  # Or raise an appropriate exception

    # If a module_name is passed to get_logger, it's likely a misconfiguration
    # elsewhere, as the logger methods themselves take module_name. However,
    # we won't use it here to avoid confusion with the module_name parameter
    # of the log methods.
    return _logger_instance
