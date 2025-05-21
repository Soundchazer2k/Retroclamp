"""Archive handling module for RetroClamp.

This module provides functionality for extracting and compressing various
archive formats (ZIP, 7z, RAR) with progress reporting and error handling.
"""

import os
import zipfile
import py7zr
import patoolib
import tempfile
import shutil
from typing import Optional
from datetime import datetime
import traceback

from PySide6.QtCore import QObject, QRunnable, Signal, Slot, QThreadPool


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
        print(f"[DEBUG] ArchiveWorker.run: Entered run() for {self.input_path}")
        """Execute the archive operation.
        
        This method is called when the worker is started by the thread pool.
        It performs the requested operation and reports progress.
        """
        # Log all key paths and operation info to error.log (for debugging)
        try:
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"\n[ArchiveWorker] Starting run at: {datetime.now()}\n")
                logf.write(f"  Operation: {self.operation}\n")
                logf.write(f"  Input path: {self.input_path}\n")
                logf.write(f"  Output path: {self.output_path}\n")
                logf.write(f"  Archive format: {self.archive_format}\n")
                logf.write(f"  Password: {'Yes' if self.password else 'No'}\n")
        except Exception as logex:
            print(f"[ArchiveWorker] Failed to log start: {logex}")
        try:
            if self.operation == "extract":
                self._extract()
            elif self.operation == "compress":
                self._compress()
            else:
                self.signals.error.emit(f"Unknown operation: {self.operation}")
        except Exception as e:
            tb = traceback.format_exc()
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"\n[ArchiveWorker] Uncaught exception at: {datetime.now()}\n")
                logf.write(tb)
            self.signals.error.emit(f"Error during {self.operation} operation: {str(e)}\n{tb}")
    
    def cancel(self):
        """Cancel the running operation."""
        self.cancelled = True
    
    def _extract(self):
        """Extract an archive file, or skip if already extracted."""
        if not os.path.exists(self.input_path):
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"[ArchiveWorker] Input file not found: {self.input_path} at {datetime.now()}\n")
            self.signals.error.emit(f"Input file not found: {self.input_path}")
            return

        # Determine output path if not specified
        if not self.output_path:
            self.output_path = os.path.splitext(self.input_path)[0]

        # If output directory exists, check for disk images
        if os.path.exists(self.output_path):
            from core.file_scanner import FileScanner
            file_scanner = FileScanner()
            disk_images = file_scanner.find_disk_images(self.output_path)
            if disk_images:
                print(f"[ArchiveWorker] Skipping extraction: files already present in {self.output_path}.")
                self.signals.progress.emit(100, "Extraction skipped: files already present.")
                print(f"[ArchiveWorker] Emitting finished signal for already extracted files.")
                self.signals.finished.emit(True, "Files already extracted.", self.output_path)
                return
            else:
                print(f"[ArchiveWorker] Extraction skipped: No disk images found in existing folder {self.output_path}.")
                with open('error.log', 'a', encoding='utf-8') as logf:
                    logf.write(f"[ArchiveWorker] Extraction skipped: No disk images found in existing folder {self.output_path} at {datetime.now()}\n")
                print(f"[ArchiveWorker] Emitting error signal for no disk images found.")
                self.signals.error.emit(f"Extraction skipped: No disk images found in existing folder {self.output_path}.")
                return

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
            tb = traceback.format_exc()
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"[ArchiveWorker] Extraction failed at {datetime.now()}\n")

                logf.write(tb)
            self.signals.error.emit(f"Extraction failed: {str(e)}\n{tb}")
    
    def _compress(self):
        """Compress a file or directory into an archive."""
        if not os.path.exists(self.input_path):
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"[ArchiveWorker] Input path not found: {self.input_path} at {datetime.now()}\n")
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
            tb = traceback.format_exc()
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"[ArchiveWorker] Compression failed at {datetime.now()}\n")
                logf.write(tb)
            self.signals.error.emit(f"Compression failed: {str(e)}\n{tb}")
    
    def _extract_zip(self):
        """Extract a ZIP archive."""
        total_size = 0
        extracted_size = 0
        file_count = 0
        
        try:
            # First pass: calculate total size and check if archive is valid
            with zipfile.ZipFile(self.input_path, 'r') as zip_ref:
                file_list = zip_ref.infolist()
                file_count = len(file_list)
                
                if file_count == 0:
                    self.signals.error.emit(f"ZIP archive is empty: {self.input_path}")
                    return
                    
                self.signals.progress.emit(0, f"Found {file_count} files in archive")
                
                for file_info in file_list:
                    total_size += file_info.file_size
                
                # Second pass: extract files with progress reporting
                for i, file_info in enumerate(file_list):
                    if self.cancelled:
                        raise Exception("Operation cancelled by user")
                    
                    # Extract file, handling password if provided
                    try:
                        if self.password:
                            # If password is provided, use it
                            zip_ref.extract(file_info, self.output_path, pwd=self.password)
                        else:
                            # Otherwise extract without password
                            zip_ref.extract(file_info, self.output_path)
                            
                        extracted_size += file_info.file_size
                        progress = (extracted_size / total_size) * 100 if total_size > 0 else 0
                        
                        self.signals.progress.emit(
                            progress,
                            f"Extracting {file_info.filename} ({i+1}/{file_count})"
                        )
                    except zipfile.BadZipFile as e:
                        self.signals.error.emit(f"Bad ZIP file: {str(e)}")
                        return
                    except RuntimeError as e:
                        # This is typically a password error
                        if "password required" in str(e).lower() or "bad password" in str(e).lower():
                            self.signals.error.emit(f"Password required or incorrect for file: {file_info.filename}")
                        else:
                            self.signals.error.emit(f"Error extracting {file_info.filename}: {str(e)}")
                        return
                    except Exception as e:
                        self.signals.error.emit(f"Error extracting {file_info.filename}: {str(e)}")
                        return
                        
                # Log successful extraction
                self.signals.progress.emit(100, f"Successfully extracted {file_count} files")
                
        except zipfile.BadZipFile as e:
            self.signals.error.emit(f"Invalid ZIP file: {str(e)}")
        except Exception as e:
            self.signals.error.emit(f"Error during ZIP extraction: {str(e)}")
    
    def _extract_7z(self):
        """Extract a 7z archive with robust error handling and progress reporting."""
        try:
            with py7zr.SevenZipFile(self.input_path, mode='r', password=self.password) as z:
                total_files = len(z.files)
                self.signals.progress.emit(0, f"Extracting archive with {total_files} files...")
                try:
                    z.extractall(path=self.output_path)
                except Exception as extract_exc:
                    self.signals.error.emit(f"Error during 7z extraction: {str(extract_exc)}")
                    return
                self.signals.progress.emit(100, f"Extracted {total_files} files")
        except Exception as e:
            self.signals.error.emit(f"Failed to open 7z archive: {str(e)}")

    
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
            
        # Treat both None and empty string as 'no output path provided'
        resolved_output_path = output_path if output_path not in (None, "") else None
        if resolved_output_path is None:
            resolved_output_path = os.path.splitext(archive_path)[0]
        print(f"[ArchiveManager.extract] Using output_path: {resolved_output_path}")
        worker = ArchiveWorker(
            operation="extract",
            input_path=archive_path,
            output_path=resolved_output_path,
            password=password
        )
        print(f"[DEBUG] ArchiveManager.extract: Worker created for {archive_path}")
        self.thread_pool.start(worker)
        print(f"[DEBUG] ArchiveManager.extract: Worker started for {archive_path}")
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
    
    def extract_sync_to_temp(self, archive_path):
        """
        Synchronously extract an archive to a temporary directory.
        Returns the path to the extracted folder, or None on failure.
        """
        if not os.path.exists(archive_path):
            return None
        ext = os.path.splitext(archive_path)[1].lower()
        temp_dir = tempfile.mkdtemp(prefix="retroclamp_extract_")
        try:
            if ext == ".zip":
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(temp_dir)
            elif ext == ".7z":
                with py7zr.SevenZipFile(archive_path, 'r') as zf:
                    zf.extractall(path=temp_dir)
            elif ext in [".rar", ".tar", ".gz", ".bz2", ".xz"]:
                import patoolib
                patoolib.extract_archive(archive_path, outdir=temp_dir)
            else:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return None
            return temp_dir
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

    @staticmethod
    def is_archive(file_path) -> bool:
        """Check if a file is a supported archive format.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file is a supported archive, False otherwise
        """
        # Safety check for None or non-string values
        if file_path is None or not isinstance(file_path, str):
            return False
            
        # Check if file exists
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return False
            
        # Get file extension and check if it's a supported archive format
        try:
            ext = os.path.splitext(file_path)[1].lower()
            return ext in [".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"]
        except Exception:
            # If any error occurs during extension checking, it's not a valid archive
            return False
