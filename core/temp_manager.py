import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from core.debug_logger import DebugLogger


class TempDirectoryManager:
    """Centralized management of temporary directories."""

    def __init__(self, debug_logger: Optional[DebugLogger] = None):
        self.temp_directories: List[Path] = []
        self.logger = debug_logger

    def create_temp_dir(self, prefix: str = "retroclamp_") -> Path:
        """Create a temporary directory and track it for cleanup."""
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        self.temp_directories.append(temp_dir)
        if self.logger:
            self.logger.debug("TempManager", f"Created temp directory: {temp_dir}")
        return temp_dir

    def cleanup_all(self):
        """Clean up all tracked temporary directories."""
        if self.logger:
            self.logger.info("TempManager", "Cleaning up all temporary directories...")
        for temp_dir in self.temp_directories:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    if self.logger:
                        self.logger.debug("TempManager", f"Cleaned up: {temp_dir}")
            except Exception as e:
                if self.logger:
                    self.logger.error("TempManager", f"Error cleaning {temp_dir}: {e}")
        self.temp_directories.clear()
        if self.logger:
            self.logger.info("TempManager", "All temporary directories cleaned.")
