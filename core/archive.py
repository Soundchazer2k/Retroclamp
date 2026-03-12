"""Archive handling module for RetroClamp.

This module provides functionality for extracting and compressing various
archive formats (ZIP, 7z, RAR) with progress reporting and error handling.
"""

import os
import shutil
import subprocess
import tempfile
import traceback
import zipfile
from datetime import datetime
from typing import Optional

import patoolib
import py7zr
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from core.debug_logger import DebugLogger

# Conditional import for py7zr
try:
    import py7zr
except ImportError:
    py7zr = None

# Improved libarchive import handling - handle both ImportError and any runtime
# errors that might occur when the native library isn't available
try:
    try:
        import libarchive.public as libarchive  # Use public for newer
        # libarchive-c versions
    except ImportError:
        libarchive = None
except (TypeError, OSError, RuntimeError):
    libarchive = None


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

    def __init__(
        self,
        operation: str,
        input_path: str,
        output_path: Optional[str] = None,
        archive_format: Optional[str] = None,
        password: Optional[str] = None,
        debug_logger: Optional[DebugLogger] = None,  # Added debug_logger parameter
    ):
        """Initialize the ArchiveWorker.

        Args:
            operation: Operation to perform ('extract' or 'compress')
            input_path: Path to the input file or directory
            output_path: Path for the output file or directory
            archive_format: Format for compression (zip, 7z, rar)
            password: Password for encrypted archives
            debug_logger: Optional DebugLogger instance
        """
        super().__init__()
        self.operation = operation
        self.input_path = input_path
        self.output_path = output_path
        self.archive_format = archive_format
        self.password = password
        self.signals = ArchiveSignals()
        self.cancelled = False
        self.debug_logger = debug_logger  # Stored debug_logger

    @Slot()
    def run(self):
        if self.debug_logger:  # Added check
            self.debug_logger.info(  # Changed to self.debug_logger
                "core.archive",
                f"ArchiveWorker.run: Entered run() for {self.input_path}",
            )
        """Execute the archive operation.

        This method is called when the worker is started by the thread pool.
        It performs the requested operation and reports progress.
        """
        try:
            if self.debug_logger:  # Added check
                self.debug_logger.info(  # Changed to self.debug_logger
                    "core.archive",
                    (
                        f"[ArchiveWorker] Starting run at: {datetime.now()} | "
                        f"Operation: {self.operation} | Input: {self.input_path} | "
                        f"Output: {self.output_path} | Format: {self.archive_format} | "
                        f"Password: {'Yes' if self.password else 'No'}"
                    ),
                )
        except Exception as logex:
            if self.debug_logger:  # Added check
                self.debug_logger.error(  # Changed to self.debug_logger
                    "core.archive", f"[ArchiveWorker] Failed to log start: {logex}"
                )
        try:
            if self.operation == "extract":
                self._extract()
            elif self.operation == "compress":
                self._compress()
            else:
                self.signals.error.emit(f"Unknown operation: {self.operation}")
        except Exception as e:
            tb = traceback.format_exc()
            if self.debug_logger:  # Added check
                self.debug_logger.error(  # Changed to self.debug_logger
                    "core.archive",
                    f"[ArchiveWorker] Uncaught exception at: {datetime.now()}\n{tb}",
                )
            self.signals.error.emit(
                f"Error during {self.operation} operation: {str(e)}\n{tb}"
            )

    def cancel(self):
        """Cancel the running operation."""
        self.cancelled = True
        if self.debug_logger:  # Added check
            self.debug_logger.info(
                "core.archive", "Archive operation cancellation requested."
            )  # Changed to self.debug_logger

    def _extract(self):
        """Extract an archive file, or skip if already extracted."""
        msg = f"[EXTRACT] Starting extraction: {self.input_path} -> {self.output_path}"
        if self.debug_logger:  # Added check
            self.debug_logger.info("core.archive", msg)  # Changed to self.debug_logger

        if not os.path.exists(self.input_path):
            if self.debug_logger:  # Added check
                self.debug_logger.error(  # Changed to self.debug_logger
                    "core.archive",
                    f"[ArchiveWorker] Input file not found: {self.input_path} at "
                    f"{datetime.now()}",
                )
            self.signals.error.emit(f"Input file not found: {self.input_path}")
            return

        if self.cancelled:
            self.signals.error.emit("Extraction cancelled by user before start.")
            if self.debug_logger:  # Added check
                self.debug_logger.info(
                    "core.archive", "Extraction cancelled before start."
                )  # Changed to self.debug_logger
            return

        # Determine output path if not specified
        if not self.output_path:
            self.output_path = os.path.splitext(self.input_path)[0]

        if os.path.exists(self.output_path):
            from core.file_scanner import (
                FileScanner,
            )  # Keep import local to avoid circular deps

            # Note: FileScanner will need debug_logger passed in main.py
            file_scanner = FileScanner()
            disk_images = file_scanner.find_disk_images(self.output_path)
            if disk_images:
                if self.debug_logger:  # Added check
                    self.debug_logger.info(  # Changed to self.debug_logger
                        "core.archive",
                        f"[ArchiveWorker] Skipping extraction: files already present "
                        f"in {self.output_path}.",
                    )
                self.signals.progress.emit(
                    100, "Extraction skipped: files already present."
                )
                self.signals.finished.emit(
                    True,
                    "Files already extracted.",
                    self.output_path,
                )
                return
            else:
                # Changed to warning as it might not be an error condition always
                if self.debug_logger:  # Added check
                    self.debug_logger.warning(  # Changed to self.debug_logger
                        "core.archive",
                        f"Output path {self.output_path} exists but contains no "
                        "disk images. Proceeding with extraction.",
                    )
                os.makedirs(self.output_path, exist_ok=True)

        os.makedirs(self.output_path, exist_ok=True)
        ext = os.path.splitext(self.input_path)[1].lower()
        self.signals.started.emit(f"Extracting {os.path.basename(self.input_path)}")

        extraction_succeeded = False
        try:
            if self.debug_logger:
                log_message = (
                    f"[EXTRACT_DIAG] Archive extension is: '{ext}' "
                    f"for {self.input_path}"
                )
                self.debug_logger.info(
                    "core.archive",
                    log_message,
                )
            if ext == ".zip":
                if self.debug_logger:
                    log_message = (
                        f"[EXTRACT_DIAG] Calling _extract_zip() for {self.input_path}"
                    )
                    self.debug_logger.info(
                        "core.archive",
                        log_message,
                    )
                self._extract_zip()
                extraction_succeeded = True
            elif ext == ".7z":
                if self.debug_logger:
                    log_message = (
                        f"[EXTRACT_DIAG] Calling _extract_7z() for {self.input_path}"
                    )
                    self.debug_logger.info(
                        "core.archive",
                        log_message,
                    )
                self._extract_7z()
                extraction_succeeded = True
            elif ext in (".rar", ".cbr"):
                if self.debug_logger:
                    log_message = (
                        f"[EXTRACT_DIAG] Calling _extract_patool() "
                        f"for {self.input_path}"
                    )
                    self.debug_logger.info(
                        "core.archive",
                        log_message,
                    )
                if self._extract_patool():
                    extraction_succeeded = True
                else:
                    self.signals.error.emit(
                        f"Extraction failed using patool for {self.input_path}"
                    )
                    return
            else:
                err_msg = f"Unsupported archive format: {ext} for {self.input_path}"
                if self.debug_logger:
                    self.debug_logger.error("core.archive", f"[EXTRACT_DIAG] {err_msg}")
                self.signals.error.emit(err_msg)
                return

            if self.cancelled:
                self.signals.error.emit("Extraction cancelled by user.")
                if self.debug_logger:
                    self.debug_logger.info(
                        "core.archive", "Extraction cancelled during operation."
                    )
                return

            if extraction_succeeded:
                self.signals.finished.emit(
                    True, "Extraction completed successfully", self.output_path
                )

        except Exception as e:
            tb = traceback.format_exc()
            if self.debug_logger:
                self.debug_logger.error(
                    "core.archive",
                    f"[ArchiveWorker] Extraction failed for "
                    f"{self.input_path} at {datetime.now()}\n{tb}",
                )
            self.signals.error.emit(f"Extraction failed: {str(e)}\n{tb}")
            return

    def _extract_zip(self):
        """Extracts a ZIP archive, falling back to libarchive if zipfile fails."""
        if self.debug_logger:
            log_message = f"Extracting ZIP: {self.input_path}"
            self.debug_logger.info("core.archive", log_message)

        extracted_with_zipfile = False
        try:
            with zipfile.ZipFile(str(self.input_path), "r") as zip_ref:
                total_files = len(zip_ref.infolist())
                extracted_count = 0
                for i, member in enumerate(zip_ref.infolist()):
                    if self.cancelled:
                        raise Exception("Extraction cancelled by user.")

                    # Handle directories
                    if member.is_dir():
                        dir_path = os.path.join(str(self.output_path), member.filename)
                        os.makedirs(dir_path, exist_ok=True)
                        extracted_count += 1
                        progress = (extracted_count / total_files) * 100
                        self.signals.progress.emit(
                            progress, f"Creating directory {member.filename}"
                        )
                        continue

                    # Attempt to extract with password if provided
                    try:
                        zip_ref.extract(
                            member, str(self.output_path), pwd=self.password
                        )
                    except Exception as e:
                        if isinstance(e, zipfile.BadZipFile):
                            raise Exception("Bad ZIP file: archive is corrupt.") from e
                        elif isinstance(e, RuntimeError) and "Bad password" in str(e):
                            raise Exception("Incorrect password for ZIP file.") from e
                        else:
                            # Fallback for unsupported compression or other errors
                            if self.debug_logger:
                                log_message = (
                                    f"zipfile failed for {member.filename}: {str(e)}. "
                                    f"Attempting patoolib fallback for this member."
                                )
                                self.debug_logger.warning("core.archive", log_message)
                            # Attempt to extract individual member with patoolib
                            try:
                                patoolib.extract_archive(
                                    str(self.input_path),
                                    outdir=str(self.output_path),
                                    files=[str(member.filename)],
                                )
                            except Exception as patoo_e:
                                if self.debug_logger:
                                    log_message = (
                                        f"patoolib failed for {member.filename}: "
                                        f"{str(patoo_e)}. Trying libarchive."
                                    )
                                    self.debug_logger.error("core.archive", log_message)
                                if libarchive:
                                    try:
                                        with libarchive.Archive.read_disk(
                                            str(self.input_path)
                                        ) as archive:
                                            for entry in archive:
                                                if entry.pathname == member.filename:
                                                    full_output_path = os.path.join(
                                                        str(self.output_path),
                                                        entry.pathname,
                                                    )
                                                    os.makedirs(
                                                        os.path.dirname(
                                                            full_output_path
                                                        ),
                                                        exist_ok=True,
                                                    )
                                                    with open(
                                                        full_output_path, "wb"
                                                    ) as f:
                                                        for block in entry.get_blocks():
                                                            f.write(block)
                                                    break
                                    except Exception as lib_e:
                                        raise Exception(
                                            f"Failed to extract {member.filename} "
                                            f"with libarchive: {str(lib_e)}"
                                        ) from lib_e
                                else:
                                    raise Exception(
                                        f"Failed to extract {member.filename} and "
                                        "libarchive not available."
                                    ) from patoo_e

                    progress = (i + 1) / total_files * 100
                    self.signals.progress.emit(
                        progress, f"Extracting {member.filename}"
                    )
            extracted_with_zipfile = True
        except Exception as e:
            if self.debug_logger:
                log_message = (
                    f"zipfile extraction failed for {self.input_path}: {str(e)}. "
                    f"Attempting patoolib fallback for entire archive."
                )
                self.debug_logger.warning("core.archive", log_message)
            try:
                patoolib.extract_archive(
                    str(self.input_path), outdir=str(self.output_path), program="zip"
                )
                self.signals.progress.emit(100, "ZIP extraction complete via patoolib.")
                extracted_with_zipfile = True
            except Exception as patoo_e:
                if self.debug_logger:
                    log_message = (
                        f"patoolib ZIP extraction failed for {self.input_path}: "
                        f"{str(patoo_e)}. Attempting libarchive fallback."
                    )
                    self.debug_logger.warning("core.archive", log_message)
                if libarchive:
                    try:
                        with libarchive.Archive.read_disk(
                            str(self.input_path)
                        ) as archive:
                            for entry in archive:
                                if self.cancelled:
                                    raise Exception("Extraction cancelled by user.")
                                full_output_path = os.path.join(
                                    str(self.output_path), entry.pathname
                                )
                                os.makedirs(
                                    os.path.dirname(full_output_path), exist_ok=True
                                )
                                with open(full_output_path, "wb") as f:
                                    for block in entry.get_blocks():
                                        f.write(block)
                                self.signals.progress.emit(
                                    0, f"Extracting {entry.pathname} (libarchive)"
                                )
                        self.signals.progress.emit(
                            100, "ZIP extraction complete via libarchive."
                        )
                        extracted_with_zipfile = True
                    except Exception as lib_e:
                        raise Exception(
                            f"ZIP extraction failed for {self.input_path}. "
                            f"Tried zipfile, patoolib, and libarchive. "
                            f"Last error: {str(lib_e)}"
                        ) from lib_e
                else:
                    raise Exception(
                        f"ZIP extraction failed for {self.input_path}. "
                        f"Tried zipfile and patoolib. libarchive not available. "
                        f"Last error: {str(patoo_e)}"
                    ) from patoo_e
        if not extracted_with_zipfile:
            raise Exception(f"Failed to extract ZIP {self.input_path} by any method.")

    def _extract_7z(self):
        """Extracts a 7z archive using py7zr or patoolib."""
        if self.debug_logger:
            log_message = f"Extracting 7z: {self.input_path}"
            self.debug_logger.info("core.archive", log_message)
        # Try py7zr first
        try:
            self._extract_7z_py7zr()
            return
        except Exception as e:
            if self.debug_logger:
                log_message = (
                    f"py7zr extraction failed for {self.input_path}: {str(e)}. "
                    f"Attempting 7z command line fallback."
                )
                self.debug_logger.warning("core.archive", log_message)

        # Fallback to 7z command line
        try:
            self._extract_7z_command_line()
            return
        except Exception as e:
            if self.debug_logger:
                log_message = (
                    f"7z command line extraction failed for {self.input_path}: "
                    f"{str(e)}. Attempting libarchive fallback."
                )
                self.debug_logger.warning("core.archive", log_message)

        # Fallback to libarchive
        if libarchive:
            try:
                self._extract_7z_libarchive()
                return
            except Exception as e:
                if self.debug_logger:
                    log_message = (
                        f"libarchive extraction failed for {self.input_path}: "
                        f"{str(e)}. Attempting patoolib fallback."
                    )
                    self.debug_logger.warning("core.archive", log_message)
        else:
            if self.debug_logger:
                log_message = "libarchive not available, using patoolib for 7z."
                self.debug_logger.info("core.archive", log_message)

        # Final fallback to patoolib
        try:
            patoolib.extract_archive(
                str(self.input_path), outdir=str(self.output_path), program="7z"
            )
        except Exception as e:
            if self.debug_logger:
                log_message = (
                    f"All extraction methods (py7zr, cmd, libarchive, patoolib) "
                    f"failed for {self.input_path}: {str(e)}"
                )
                self.debug_logger.error("core.archive", log_message)
            raise RuntimeError(
                f"All extraction methods failed for {self.input_path}"
            ) from e

    def _extract_7z_py7zr(self):
        """Extracts a 7z archive using py7zr."""
        if self.debug_logger:
            log_message = f"Extracting 7z with py7zr: {self.input_path}"
            self.debug_logger.info("core.archive", log_message)
        with py7zr.SevenZipFile(self.input_path, mode="r") as archive:
            self.signals.progress.emit(
                50, f"Extracting {os.path.basename(self.input_path)} (7z with py7zr)"
            )
            archive.extractall(path=self.output_path)
        self.signals.progress.emit(100, "7z extraction complete via py7zr.")

    def _extract_7z_command_line(self):
        """Extracts a 7z archive using the 7z command line tool."""
        if self.debug_logger:
            log_message = f"Extracting 7z with 7z command line: {self.input_path}"
            self.debug_logger.info("core.archive", log_message)
        try:
            command = [
                "7z",
                "x",
                self.input_path,
                f"-o{self.output_path}",
                "-y",
            ]
            if self.password:
                command.append(f"-p{self.password}")

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Monitor output for progress (simple approach)
            for line in process.stdout:
                if self.cancelled:
                    process.terminate()
                    raise Exception("Extraction cancelled by user.")
                if "%" in line:
                    try:
                        progress_str = line.split("%")[0].strip().split()[-1]
                        progress = float(progress_str)
                        self.signals.progress.emit(progress, line.strip())
                    except ValueError:
                        pass  # Ignore lines that don't parse as progress

            stderr_output = process.communicate()[1]
            if process.returncode != 0:
                raise Exception(f"7z command line error: {stderr_output}") from None

            self.signals.progress.emit(100, "7z extraction complete via command line.")
        except FileNotFoundError as e:  # Catch the exception as e
            raise Exception(
                "7z command line tool not found. Please install 7-Zip."
            ) from e  # Add 'from e'
        except Exception as e:
            if self.debug_logger:
                log_message = (
                    f"7z command line extraction failed for {self.input_path}: "
                    f"{str(e)}. "
                )
                self.debug_logger.warning("core.archive", log_message)
                log_message = "Attempting libarchive fallback."
                self.debug_logger.warning("core.archive", log_message)
            raise Exception(f"7z command line extraction failed: {str(e)}") from e

    def _extract_7z_libarchive(self):
        """Extracts a 7z archive using libarchive."""
        if self.debug_logger:
            log_message = f"Extracting 7z with libarchive: {self.input_path}"
            self.debug_logger.info("core.archive", log_message)
        with libarchive.Archive.read_disk(self.input_path) as archive:
            for entry in archive:
                if self.cancelled:
                    raise Exception("Extraction cancelled by user.")
                full_output_path = os.path.join(self.output_path, entry.pathname)
                os.makedirs(os.path.dirname(full_output_path), exist_ok=True)
                with open(full_output_path, "wb") as f:
                    for block in entry.get_blocks():
                        f.write(block)
                self.signals.progress.emit(
                    0, f"Extracting {entry.pathname} (libarchive)"
                )
        self.signals.progress.emit(100, "7z extraction complete via libarchive.")

    def _extract_rar(self):
        """Extracts a RAR archive using patoolib."""
        if self.debug_logger:
            log_message = f"Extracting RAR: {self.input_path}"
            self.debug_logger.info("core.archive", log_message)
        try:
            patoolib.extract_archive(
                str(self.input_path), outdir=str(self.output_path), program="unrar"
            )
            self.signals.progress.emit(100, "RAR extraction complete via patoolib.")
        except Exception as e:
            error_msg = (
                f"patoolib RAR extraction failed for {self.input_path}: {str(e)}"
            )
            if self.debug_logger:
                self.debug_logger.error("core.archive", error_msg)
            raise RuntimeError(error_msg) from e

    def _compress(self):
        """Compresses a file or directory."""
        if self.debug_logger:
            log_message = f"Compressing: {self.input_path}"
            self.debug_logger.info("core.archive", log_message)
        try:
            patoolib.create_archive(
                self.output_path, self.input_path, program=self.archive_format
            )
            self.signals.progress.emit(100, "Compression complete.")
            self.signals.finished.emit(True, "Compression complete.", self.output_path)
        except Exception as e:
            error_msg = f"Compression failed for {self.input_path}: {str(e)}"
            if self.debug_logger:
                self.debug_logger.error("core.archive", error_msg)
            self.signals.error.emit(error_msg)

    def _get_archive_type(self, file_path: str) -> Optional[str]:
        """Determines the archive type based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".zip":
            return "zip"
        elif ext == ".7z":
            return "7z"
        elif ext == ".rar":
            return "rar"
        return None


class ArchiveManager(QObject):
    """Manages archive operations using a thread pool."""

    def __init__(self, debug_logger: Optional[DebugLogger] = None):
        """Initialize the ArchiveManager."""
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(1)
        self.current_worker: Optional[ArchiveWorker] = None
        self.signals = ArchiveSignals()
        self.debug_logger = debug_logger
        if self.debug_logger:
            log_message = "Initialized"
            self.debug_logger.info("ArchiveManager", log_message)

    def extract(
        self, input_path: str, output_path: str, password: Optional[str] = None
    ) -> ArchiveSignals:
        """Extracts an archive in a separate thread."""
        if self.debug_logger:
            log_message = f"ArchiveManager: Starting extraction for {input_path}"
            self.debug_logger.info("core.archive", log_message)
        worker = ArchiveWorker(
            "extract",
            input_path,
            output_path,
            password=password,
            debug_logger=self.debug_logger,
        )
        self.current_worker = worker
        self.thread_pool.start(worker)
        return worker.signals

    def compress(
        self,
        input_path: str,
        output_path: str,
        archive_format: str,
        password: Optional[str] = None,
    ) -> ArchiveSignals:
        """Compresses a file or directory in a separate thread."""
        if self.debug_logger:
            log_message = f"ArchiveManager: Starting compression for {input_path}"
            self.debug_logger.info("core.archive", log_message)
        worker = ArchiveWorker(
            "compress",
            input_path,
            output_path,
            archive_format=archive_format,
            password=password,
            debug_logger=self.debug_logger,
        )
        self.current_worker = worker
        self.thread_pool.start(worker)
        return worker.signals

    def cancel_current_operation(self):
        """Cancels the currently running archive operation."""
        if self.current_worker:
            self.current_worker.cancel()
            if self.debug_logger:
                log_message = "ArchiveManager: Current operation cancelled."
                self.debug_logger.info("core.archive", log_message)
        else:
            if self.debug_logger:
                log_message = "ArchiveManager: No active operation to cancel."
                self.debug_logger.info("core.archive", log_message)

    @Slot(str, str, str, str)
    def start_extraction(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Starts an archive extraction operation."""
        if self.current_worker and self.current_worker.isRunning():
            if self.debug_logger:
                log_message = (
                    "Another archive operation is already running. "
                    "Skipping new request."
                )
                self.debug_logger.info("core.archive", log_message)
            return

        self.current_worker = ArchiveWorker(
            operation="extract",
            input_path=input_path,
            output_path=output_path,
            password=password,
            debug_logger=self.debug_logger,
        )
        self.current_worker.signals.started.connect(self.on_started)
        self.current_worker.signals.progress.connect(self.on_progress)
        self.current_worker.signals.finished.connect(self.on_finished)
        self.current_worker.signals.error.connect(self.on_error)
        self.thread_pool.start(self.current_worker)
        if self.debug_logger:
            log_message = f"Extraction started for {input_path}"
            self.debug_logger.info("core.archive", log_message)

    @Slot(str, str, str, str)
    def start_compression(
        self,
        input_path: str,
        output_path: str,
        archive_format: str,
        password: Optional[str] = None,
    ):
        """Starts an archive compression operation."""
        if self.current_worker and self.current_worker.isRunning():
            if self.debug_logger:
                log_message = (
                    "Another archive operation is already running. "
                    "Skipping new request."
                )
                self.debug_logger.info("core.archive", log_message)
            return

        self.current_worker = ArchiveWorker(
            operation="compress",
            input_path=input_path,
            output_path=output_path,
            archive_format=archive_format,
            password=password,
            debug_logger=self.debug_logger,
        )
        self.current_worker.signals.started.connect(self.on_started)
        self.current_worker.signals.progress.connect(self.on_progress)
        self.current_worker.signals.finished.connect(self.on_finished)
        self.current_worker.signals.error.connect(self.on_error)
        self.thread_pool.start(self.current_worker)
        if self.debug_logger:
            log_message = f"Compression started for {input_path}"
            self.debug_logger.info("core.archive", log_message)

    @Slot()
    def on_started(self, description: str):
        """Handles the started signal from the worker."""
        if self.debug_logger:
            log_message = f"Archive operation started: {description}"
            self.debug_logger.info("core.archive", log_message)
        self.signals.started.emit(description)

    @Slot(float, str)
    def on_progress(self, percentage: float, message: str):
        """Handles the progress signal from the worker."""
        if self.debug_logger:
            log_message = f"Progress: {percentage:.2f}% - {message}"
            self.debug_logger.debug("core.archive", log_message)
        self.signals.progress.emit(percentage, message)

    @Slot(bool, str, str)
    def on_finished(self, success: bool, message: str, output_path: str):
        """Handles the finished signal from the worker."""
        if self.debug_logger:
            log_message = (
                f"Archive operation finished. Success: {success}, Message: {message}, "
                f"Output: {output_path}"
            )
            self.debug_logger.info("core.archive", log_message)
        self.signals.finished.emit(success, message, output_path)
        self.current_worker = None

    @Slot(str)
    def on_error(self, error_message: str):
        """Handles the error signal from the worker."""
        if self.debug_logger:
            log_message = f"Archive operation error: {error_message}"
            self.debug_logger.error("core.archive", log_message)
        self.signals.error.emit(error_message)
        self.current_worker = None

    @staticmethod
    def extract_sync_to_temp(
        archive_path: str, debug_logger: Optional[DebugLogger] = None
    ) -> Optional[str]:
        """Synchronously extracts an archive to a temporary directory."""
        if not os.path.exists(archive_path):
            if debug_logger:
                log_message = f"Archive not found: {archive_path}"
                debug_logger.error("core.archive", log_message)
            return None

        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(prefix="retroclamp_extract_")
            if debug_logger:
                log_message = f"Synchronously extracting {archive_path} to {temp_dir}"
                debug_logger.info("core.archive", log_message)

            archive_type = ArchiveManager._get_archive_type_static(archive_path)
            if archive_type == "zip":
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)
            elif archive_type == "7z":
                if py7zr.is_7zfile(archive_path):
                    with py7zr.SevenZipFile(archive_path, mode="r") as seven_zip_ref:
                        seven_zip_ref.extractall(path=temp_dir)
                else:
                    # Fallback for non-standard 7z, e.g. some .exe installers
                    patoolib.extract_archive(
                        archive_path, outdir=temp_dir, program="7z"
                    )
            elif archive_type == "rar":
                patoolib.extract_archive(archive_path, outdir=temp_dir, program="unrar")
            else:
                if debug_logger:
                    log_message = (
                        f"Unsupported archive type for sync extraction: {archive_path}"
                    )
                    debug_logger.warning("core.archive", log_message)
                return None

            if debug_logger:
                log_message = f"Synchronous extraction complete for {archive_path}"
                debug_logger.info("core.archive", log_message)
            return temp_dir
        except Exception as e:
            tb = traceback.format_exc()
            if debug_logger:
                log_message = (
                    f"Synchronous extraction failed for {archive_path}: {str(e)}\n{tb}"
                )
                debug_logger.error("core.archive", log_message)
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    if debug_logger:
                        log_message = (
                            f"[extract_sync_to_temp] Cleaned up temp directory "
                            f"after failure: {temp_dir}"
                        )
                        debug_logger.info("core.archive", log_message)
                except Exception as cleanup_e:
                    if debug_logger:
                        log_message = (
                            f"Error cleaning up temp directory {temp_dir}: {cleanup_e}"
                        )
                        debug_logger.error("core.archive", log_message)
            return None

    @staticmethod
    def _get_archive_type_static(file_path: str) -> Optional[str]:
        """Determines the archive type based on file extension (static version)."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".zip":
            return "zip"
        elif ext == ".7z":
            return "7z"
        elif ext == ".rar":
            return "rar"
        return None

    @staticmethod
    def is_archive(file_path) -> bool:
        """Checks if a given file path points to a recognized archive type."""
        if file_path is None or not isinstance(file_path, str):
            return False
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return False
        try:
            return ArchiveManager._get_archive_type_static(file_path) is not None
        except Exception:
            return False
