"""Archive handling module for RetroClamp.

This module provides functionality for extracting and compressing various
archive formats (ZIP, 7z, RAR) with progress reporting and error handling.
"""

import os
import shutil
import tempfile
import zipfile
import py7zr
import patoolib
from typing import Dict, List, Optional, Union, Callable, Tuple, Any

from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool


class ArchiveSignals(QObject):
    """Signals for archive operations.
    
    Signals:
        started: Emitted when the operation starts
        progress: Emitted during operation with progress percentage and message
        finished: Emitted when the operation completes successfully
        error: Emitted when an error occurs
    """
    started = Signal(str)  # Operation description
    progress = Signal(float, str)  # Progress percentage, message
    finished = Signal(bool, str, str)  # Success flag, output message, output path
    error = Signal(str)  # Error message


class ArchiveWorker(QRunnable):
    """Worker for running archive operations in a separate thread.
    
    This class handles the extraction and compression of archives asynchronously,
    reporting progress and results through signals.
    """
    
    def __init__(self, 
                 operation: str,
                 input_path: str, 
                 output_path: Optional[str] = None,
                 archive_format: Optional[str] = None,
                 password: Optional[str] = None):
        """Initialize the ArchiveWorker.
        
        Args:
            operation: Operation to perform ('extract' or 'compress')
            input_path: Path to the input file or directory
            output_path: Path for the output file or directory
            archive_format: Format for compression (zip, 7z, rar)
            password: Password for encrypted archives
        """
        super().__init__()
        self.operation = operation
        self.input_path = input_path
        self.output_path = output_path
        self.archive_format = archive_format
        self.password = password
        self.signals = ArchiveSignals()
        self.cancelled = False
        
    @Slot()
    def run(self):
        """Execute the archive operation.
        
        This method is called when the worker is started by the thread pool.
        It performs the requested operation and reports progress.
        """
        try:
            if self.operation == "extract":
                self._extract()
            elif self.operation == "compress":
                self._compress()
            else:
                self.signals.error.emit(f"Unknown operation: {self.operation}")
        except Exception as e:
            self.signals.error.emit(f"Error during {self.operation} operation: {str(e)}")
    
    def cancel(self):
        """Cancel the running operation."""
        self.cancelled = True
    
    def _extract(self):
        """Extract an archive file."""
        if not os.path.exists(self.input_path):
            self.signals.error.emit(f"Input file not found: {self.input_path}")
            return
            
        # Determine output path if not specified
        if not self.output_path:
            self.output_path = os.path.splitext(self.input_path)[0]
            
        # Create output directory if it doesn't exist
        os.makedirs(self.output_path, exist_ok=True)
            
        # Determine archive type
        ext = os.path.splitext(self.input_path)[1].lower()
        
        self.signals.started.emit(f"Extracting {os.path.basename(self.input_path)}")
        
        try:
            if ext == ".zip":
                self._extract_zip()
            elif ext == ".7z":
                self._extract_7z()
            elif ext in [".rar", ".tar", ".gz", ".bz2", ".xz"]:
                self._extract_patool()
            else:
                self.signals.error.emit(f"Unsupported archive format: {ext}")
                return
                
            self.signals.finished.emit(True, "Extraction completed successfully", self.output_path)
        except Exception as e:
            self.signals.error.emit(f"Extraction failed: {str(e)}")
    
    def _compress(self):
        """Compress a file or directory into an archive."""
        if not os.path.exists(self.input_path):
            self.signals.error.emit(f"Input path not found: {self.input_path}")
            return
            
        # Determine output path if not specified
        if not self.output_path:
            if os.path.isdir(self.input_path):
                base_name = os.path.basename(os.path.normpath(self.input_path))
            else:
                base_name = os.path.splitext(os.path.basename(self.input_path))[0]
                
            if not self.archive_format:
                self.archive_format = "zip"  # Default format
                
            self.output_path = f"{os.path.dirname(self.input_path)}/{base_name}.{self.archive_format}"
        
        self.signals.started.emit(f"Compressing {os.path.basename(self.input_path)}")
        
        try:
            if self.archive_format == "zip":
                self._compress_zip()
            elif self.archive_format == "7z":
                self._compress_7z()
            elif self.archive_format in ["rar", "tar", "gz", "bz2", "xz"]:
                self._compress_patool()
            else:
                self.signals.error.emit(f"Unsupported archive format: {self.archive_format}")
                return
                
            self.signals.finished.emit(True, "Compression completed successfully", self.output_path)
        except Exception as e:
            self.signals.error.emit(f"Compression failed: {str(e)}")
    
    def _extract_zip(self):
        """Extract a ZIP archive."""
        total_size = 0
        extracted_size = 0
        
        # First pass: calculate total size
        with zipfile.ZipFile(self.input_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                total_size += file_info.file_size
            
            # Second pass: extract files with progress reporting
            for i, file_info in enumerate(zip_ref.infolist()):
                if self.cancelled:
                    raise Exception("Operation cancelled by user")
                    
                zip_ref.extract(file_info, self.output_path, self.password)
                extracted_size += file_info.file_size
                progress = (extracted_size / total_size) * 100 if total_size > 0 else 0
                
                self.signals.progress.emit(
                    progress,
                    f"Extracting {file_info.filename} ({i+1}/{len(zip_ref.infolist())})"
                )
    
    def _extract_7z(self):
        """Extract a 7z archive."""
        with py7zr.SevenZipFile(self.input_path, mode='r', password=self.password) as z:
            total_files = len(z.files)
            
            # Define a callback for progress reporting
            def progress_callback(extracted, total):
                if self.cancelled:
                    raise Exception("Operation cancelled by user")
                progress = (extracted / total) * 100 if total > 0 else 0
                self.signals.progress.emit(progress, f"Extracting files ({extracted}/{total})")
            
            # Extract with progress reporting
            z.extractall(path=self.output_path, progress_callback=progress_callback)
    
    def _extract_patool(self):
        """Extract an archive using patool (for formats like RAR, TAR, etc.)."""
        # patoolib doesn't provide progress reporting, so we'll emit periodic updates
        self.signals.progress.emit(0, "Starting extraction...")
        
        # Extract the archive
        patoolib.extract_archive(self.input_path, outdir=self.output_path, interactive=False)
        
        # Count extracted files for a summary
        file_count = sum([len(files) for _, _, files in os.walk(self.output_path)])
        self.signals.progress.emit(100, f"Extracted {file_count} files")
    
    def _compress_zip(self):
        """Compress to a ZIP archive."""
        if os.path.isdir(self.input_path):
            # Compress a directory
            total_files = sum([len(files) for _, _, files in os.walk(self.input_path)])
            processed_files = 0
            
            with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for root, _, files in os.walk(self.input_path):
                    for file in files:
                        if self.cancelled:
                            raise Exception("Operation cancelled by user")
                            
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(self.input_path))
                        zip_file.write(file_path, arcname)
                        
                        processed_files += 1
                        progress = (processed_files / total_files) * 100 if total_files > 0 else 0
                        self.signals.progress.emit(
                            progress,
                            f"Compressing {file} ({processed_files}/{total_files})"
                        )
        else:
            # Compress a single file
            with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                arcname = os.path.basename(self.input_path)
                zip_file.write(self.input_path, arcname)
                self.signals.progress.emit(100, f"Compressed {arcname}")
    
    def _compress_7z(self):
        """Compress to a 7z archive."""
        if os.path.isdir(self.input_path):
            # Compress a directory
            files_to_add = []
            base_path = os.path.dirname(self.input_path)
            dir_name = os.path.basename(os.path.normpath(self.input_path))
            
            for root, _, files in os.walk(self.input_path):
                for file in files:
                    if self.cancelled:
                        raise Exception("Operation cancelled by user")
                        
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, base_path)
                    files_to_add.append((arcname, file_path))
            
            total_files = len(files_to_add)
            
            with py7zr.SevenZipFile(self.output_path, mode='w') as z:
                for i, (arcname, file_path) in enumerate(files_to_add):
                    if self.cancelled:
                        raise Exception("Operation cancelled by user")
                        
                    z.write(file_path, arcname)
                    progress = ((i + 1) / total_files) * 100
                    self.signals.progress.emit(
                        progress,
                        f"Compressing {arcname} ({i+1}/{total_files})"
                    )
        else:
            # Compress a single file
            with py7zr.SevenZipFile(self.output_path, mode='w') as z:
                arcname = os.path.basename(self.input_path)
                z.write(self.input_path, arcname)
                self.signals.progress.emit(100, f"Compressed {arcname}")
    
    def _compress_patool(self):
        """Compress using patool (for formats like RAR, TAR, etc.)."""
        # patoolib doesn't provide progress reporting, so we'll emit periodic updates
        self.signals.progress.emit(0, "Starting compression...")
        
        # Compress the file or directory
        patoolib.create_archive(self.output_path, [self.input_path], interactive=False)
        
        # Final progress update
        if os.path.isdir(self.input_path):
            file_count = sum([len(files) for _, _, files in os.walk(self.input_path)])
            self.signals.progress.emit(100, f"Compressed {file_count} files")
        else:
            self.signals.progress.emit(100, f"Compressed {os.path.basename(self.input_path)}")


class ArchiveManager:
    """Manager for archive operations.
    
    This class provides a high-level interface for extracting and compressing
    archives, handling the creation and management of worker threads.
    """
    
    def __init__(self):
        """Initialize the ArchiveManager."""
        self.thread_pool = QThreadPool()
    
    def extract(self, 
                archive_path: str, 
                output_path: Optional[str] = None,
                password: Optional[str] = None) -> ArchiveSignals:
        """Extract an archive file.
        
        Args:
            archive_path: Path to the archive file
            output_path: Path for the extracted files (default: same as archive without extension)
            password: Password for encrypted archives
            
        Returns:
            ArchiveSignals object for connecting to signals
            
        Raises:
            FileNotFoundError: If archive file doesn't exist
        """
        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"Archive file not found: {archive_path}")
            
        worker = ArchiveWorker(
            operation="extract",
            input_path=archive_path,
            output_path=output_path,
            password=password
        )
        
        self.thread_pool.start(worker)
        return worker.signals
    
    def compress(self, 
                 input_path: str, 
                 output_path: Optional[str] = None,
                 archive_format: str = "zip",
                 password: Optional[str] = None) -> ArchiveSignals:
        """Compress a file or directory into an archive.
        
        Args:
            input_path: Path to the file or directory to compress
            output_path: Path for the archive file
            archive_format: Format for the archive (zip, 7z, rar, etc.)
            password: Password for encrypted archives
            
        Returns:
            ArchiveSignals object for connecting to signals
            
        Raises:
            FileNotFoundError: If input path doesn't exist
            ValueError: If archive format is not supported
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input path not found: {input_path}")
            
        if archive_format not in ["zip", "7z", "rar", "tar", "gz", "bz2", "xz"]:
            raise ValueError(f"Unsupported archive format: {archive_format}")
            
        worker = ArchiveWorker(
            operation="compress",
            input_path=input_path,
            output_path=output_path,
            archive_format=archive_format,
            password=password
        )
        
        self.thread_pool.start(worker)
        return worker.signals
    
    @staticmethod
    def is_archive(file_path: str) -> bool:
        """Check if a file is a supported archive format.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file is a supported archive, False otherwise
        """
        if not os.path.isfile(file_path):
            return False
            
        ext = os.path.splitext(file_path)[1].lower()
        return ext in [".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"]
