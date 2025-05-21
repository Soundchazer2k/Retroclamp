"""File scanner module for RetroClamp.

This module provides functionality for scanning directories and filtering files
based on extensions, with support for drag-and-drop operations.
"""

import os
import fnmatch
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import traceback

from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool, QMimeData


@dataclass
class ScanResult:
    """Result of a file scanning operation.
    
    Attributes:
        files: List of file paths found
        directories: List of directory paths found
        total_size: Total size of all files in bytes
        file_count: Number of files found
        dir_count: Number of directories found
    """
    files: List[str]
    directories: List[str]
    total_size: int
    file_count: int
    dir_count: int


class ScannerSignals(QObject):
    """Signals for file scanning operations.
    
    Signals:
        started: Emitted when the scan starts
        progress: Emitted during scanning with progress information
        finished: Emitted when the scan completes successfully
        error: Emitted when an error occurs
    """
    started = Signal(str)  # Scan description
    progress = Signal(int, int, str)  # Files found, dirs found, current path
    finished = Signal(ScanResult)  # Scan result
    error = Signal(str)  # Error message


class ScannerWorker(QRunnable):
    """Worker for running file scanning operations in a separate thread.
    
    This class handles directory scanning asynchronously, reporting progress
    and results through signals.
    """
    
    def __init__(self, 
                 path: str, 
                 recursive: bool = True,
                 include_extensions: Optional[List[str]] = None,
                 exclude_extensions: Optional[List[str]] = None,
                 exclude_patterns: Optional[List[str]] = None):
        """Initialize the ScannerWorker.
        
        Args:
            path: Path to scan
            recursive: Whether to scan subdirectories
            include_extensions: List of file extensions to include (e.g., ['.iso', '.bin'])
            exclude_extensions: List of file extensions to exclude
            exclude_patterns: List of glob patterns to exclude
        """
        super().__init__()
        self.path = path
        self.recursive = recursive
        self.include_extensions = [ext.lower() for ext in include_extensions] if include_extensions else None
        self.exclude_extensions = [ext.lower() for ext in exclude_extensions] if exclude_extensions else None
        self.exclude_patterns = exclude_patterns or []
        self.signals = ScannerSignals()
        self.cancelled = False
        
    @Slot()
    def run(self):
        """Execute the file scanning operation.
        
        This method is called when the worker is started by the thread pool.
        It scans the specified directory and reports results.
        """
        # Log all key paths and operation info to error.log (for debugging)
        try:
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"\n[ScannerWorker] Starting run at: {datetime.now()}\n")
                logf.write(f"  Path: {self.path}\n")
                logf.write(f"  Recursive: {self.recursive}\n")
                logf.write(f"  Include extensions: {self.include_extensions}\n")
                logf.write(f"  Exclude extensions: {self.exclude_extensions}\n")
                logf.write(f"  Exclude patterns: {self.exclude_patterns}\n")
        except Exception as logex:
            print(f"[ScannerWorker] Failed to log start: {logex}")
        
        try:
            if not os.path.exists(self.path):
                with open('error.log', 'a', encoding='utf-8') as logf:
                    logf.write(f"[ScannerWorker] Path not found: {self.path} at {datetime.now()}\n")
                self.signals.error.emit(f"Path not found: {self.path}")
                return
                
            self.signals.started.emit(f"Scanning {self.path}")
            
            files = []
            directories = []
            total_size = 0
            file_count = 0
            dir_count = 0
            
            # If the path is a file, handle it directly
            if os.path.isfile(self.path):
                if self._should_include_file(self.path):
                    files.append(self.path)
                    total_size += os.path.getsize(self.path)
                    file_count += 1
                    
                self.signals.progress.emit(file_count, dir_count, self.path)
            else:
                # Walk the directory
                for root, dirs, filenames in os.walk(self.path):
                    if self.cancelled:
                        with open('error.log', 'a', encoding='utf-8') as logf:
                            logf.write(f"[ScannerWorker] Scan cancelled by user at {datetime.now()}\n")
                        self.signals.error.emit("Scan cancelled by user")
                        return
                        
                    # Apply exclude patterns to directories
                    dirs[:] = [d for d in dirs if not self._should_exclude_dir(os.path.join(root, d))]
                    
                    # If not recursive, clear the dirs list to prevent descending
                    if not self.recursive and root != self.path:
                        dirs.clear()
                    
                    # Process directories
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        directories.append(dir_path)
                        dir_count += 1
                    
                    # Process files
                    for filename in filenames:
                        if self.cancelled:
                            with open('error.log', 'a', encoding='utf-8') as logf:
                                logf.write(f"[ScannerWorker] Scan cancelled by user at {datetime.now()}\n")
                            self.signals.error.emit("Scan cancelled by user")
                            return
                            
                        file_path = os.path.join(root, filename)
                        if self._should_include_file(file_path):
                            files.append(file_path)
                            try:
                                total_size += os.path.getsize(file_path)
                                file_count += 1
                            except (OSError, FileNotFoundError):
                                # Skip files that can't be accessed
                                pass
                    
                    self.signals.progress.emit(file_count, dir_count, root)
            
            # Emit the final result
            result = ScanResult(
                files=files,
                directories=directories,
                total_size=total_size,
                file_count=file_count,
                dir_count=dir_count
            )
            self.signals.finished.emit(result)
            
        except Exception as e:
            self.signals.error.emit(f"Error during scan: {str(e)}")
    
    def cancel(self):
        """Cancel the running scan."""
        self.cancelled = True
    
    def _should_include_file(self, file_path: str) -> bool:
        """Check if a file should be included in the scan results.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file should be included, False otherwise
        """
        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(os.path.basename(file_path), pattern):
                return False
        
        # Check file extension
        ext = os.path.splitext(file_path)[1].lower()
        
        # If include_extensions is specified, only include files with those extensions
        if self.include_extensions is not None:
            return ext in self.include_extensions
        
        # If exclude_extensions is specified, exclude files with those extensions
        if self.exclude_extensions is not None:
            return ext not in self.exclude_extensions
        
        # If neither is specified, include all files
        return True
    
    def _should_exclude_dir(self, dir_path: str) -> bool:
        """Check if a directory should be excluded from the scan.
        
        Args:
            dir_path: Path to the directory to check
            
        Returns:
            True if the directory should be excluded, False otherwise
        """
        dir_name = os.path.basename(dir_path)
        
        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(dir_name, pattern):
                return True
        
        return False


from PySide6.QtCore import QRunnable, QObject, Signal

class DiskImageScanSignals(QObject):
    started = Signal(str)
    progress = Signal(int, int, str)  # files_found, total_files, current_path
    finished = Signal(list)  # List of found disk image paths
    error = Signal(str)

class DiskImageScanWorker(QRunnable):
    def __init__(self, directory, extensions=None):
        super().__init__()
        self.directory = directory
        self.extensions = [ext.lower() for ext in (extensions or ['.cue', '.bin', '.iso', '.img', '.cdr', '.gdi', '.mdf', '.nrg'])]
        self.signals = DiskImageScanSignals()
        self.cancelled = False

    def run(self):
        try:
            if not os.path.exists(self.directory):
                self.signals.error.emit(f"Directory not found: {self.directory}")
                return
            self.signals.started.emit(f"Scanning {self.directory}")
            disk_images = []
            total_files = 0
            for root, _, files in os.walk(self.directory):
                total_files += len(files)
            files_scanned = 0
            for root, _, files in os.walk(self.directory):
                for file in files:
                    if self.cancelled:
                        self.signals.error.emit("Scan cancelled by user")
                        return
                    file_path = os.path.join(root, file)
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self.extensions:
                        disk_images.append(file_path)
                    files_scanned += 1
                    if files_scanned % 20 == 0 or files_scanned == total_files:
                        self.signals.progress.emit(len(disk_images), files_scanned, file_path)
            self.signals.finished.emit(disk_images)
        except Exception as e:
            tb = traceback.format_exc()
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"[DiskImageScanWorker] Error at {datetime.now()}\n")
                logf.write(tb)
            self.signals.error.emit(f"Error during disk image scan: {str(e)}\n{tb}")

    def cancel(self):
        self.cancelled = True

class FileScanner:
    """Manager for file scanning operations.
    
    This class provides a high-level interface for scanning directories and
    filtering files, handling the creation and management of worker threads.
    """
    
    def __init__(self):
        """Initialize the FileScanner."""
        self.thread_pool = QThreadPool()

    def find_disk_images_async(self, directory: str, extensions=None):
        """
        Asynchronously scan a directory for disk image files.
        Args:
            directory: Directory to scan
            extensions: List of file extensions to include (default: common disk image types)
        Returns:
            DiskImageScanSignals object for connecting to started, progress, finished, and error signals.
        """
        worker = DiskImageScanWorker(directory, extensions)
        self.thread_pool.start(worker)
        return worker.signals
    
    def scan(self, 
             path: str, 
             recursive: bool = True,
             include_extensions: Optional[List[str]] = None,
             exclude_extensions: Optional[List[str]] = None,
             exclude_patterns: Optional[List[str]] = None) -> ScannerSignals:
        """Scan a directory for files.
        
        Args:
            path: Path to scan
            recursive: Whether to scan subdirectories
            include_extensions: List of file extensions to include (e.g., ['.iso', '.bin'])
            exclude_extensions: List of file extensions to exclude
            exclude_patterns: List of glob patterns to exclude
            
        Returns:
            ScannerSignals object for connecting to signals
            
        Raises:
            FileNotFoundError: If the path doesn't exist
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path not found: {path}")
            
        worker = ScannerWorker(
            path=path,
            recursive=recursive,
            include_extensions=include_extensions,
            exclude_extensions=exclude_extensions,
            exclude_patterns=exclude_patterns
        )
        
        self.thread_pool.start(worker)
        return worker.signals
    
    @staticmethod
    def parse_mime_data(mime_data: QMimeData) -> List[str]:
        """Parse drag-and-drop mime data to extract file paths.
        
        Args:
            mime_data: Mime data from a drag-and-drop event
            
        Returns:
            List of file/directory paths
        """
        paths = []
        
        # Handle URLs (most common case)
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    paths.append(url.toLocalFile())
        
        # Handle plain text (some applications provide paths as text)
        elif mime_data.hasText():
            text = mime_data.text()
            for line in text.splitlines():
                line = line.strip()
                if line and os.path.exists(line):
                    paths.append(line)
        
        return paths
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format a file size in bytes to a human-readable string.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string (e.g., '1.23 MB')
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def find_disk_images(self, directory: str) -> List[str]:
        """Find disk image files in a directory.
        
        Args:
            directory: Directory to scan for disk images
            
        Returns:
            List of paths to disk image files
        """
        disk_images = []
        disk_image_extensions = ['.cue', '.bin', '.iso', '.img', '.cdr', '.gdi', '.mdf', '.nrg']
        
        # Walk through the directory and find disk images
        for root, _, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in disk_image_extensions:
                    full_path = os.path.join(root, file)
                    disk_images.append(full_path)
        
        return disk_images
    
    @staticmethod
    def get_media_type(file_path: str) -> str:
        """Determine the media type of a file based on its extension and content.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Media type ('cd', 'dvd', 'hd', or 'unknown')
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        # Check extension first
        if ext in ['.cue', '.bin', '.iso', '.img', '.cdr']:
            # Could be CD or DVD, check file size to determine
            try:
                size = os.path.getsize(file_path)
                if size > 1024 * 1024 * 1024:  # > 1 GB
                    return 'dvd'
                else:
                    return 'cd'
            except (OSError, FileNotFoundError):
                return 'unknown'
        elif ext in ['.chd']:
            # For CHD files, we need to check the header or use chdman info
            # This is a simplified approach
            return 'chd'
        elif ext in ['.vhd', '.vmdk', '.img', '.raw']:
            return 'hd'
        else:
            return 'unknown'
