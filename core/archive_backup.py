"""Archive handling module for RetroClamp.

This module provides functionality for extracting and compressing various
archive formats (ZIP, 7z, RAR) with progress reporting and error handling.
"""

import os
import platform  # Added for 7-Zip CLI
import shutil
import subprocess  # Added for 7-Zip CLI
import tempfile
import traceback
import zipfile
from datetime import datetime
from typing import Optional

import patoolib
import py7zr
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from core.debug_logger import DebugLogger

debug_logger = DebugLogger(module_name="core.archive")

# Conditional import for py7zr
try:
    import py7zr
except ImportError:
    py7zr = None
    debug_logger.warning(
        "core.archive",
        "py7zr not found, 7z extraction will fall back to other methods.",
    )

# Improved libarchive import handling - handle both ImportError and any runtime
# errors that might occur when the native library isn't available
try:
    try:
        import libarchive.public as libarchive  # Use public for newer
        # libarchive-c versions
    except ImportError:
        libarchive = None
        debug_logger.warning(
            "core.archive",
            "libarchive-c not found, libarchive fallback for 7z extraction "
            "will be unavailable.",
        )
except (TypeError, OSError, RuntimeError) as e:
    libarchive = None
    debug_logger.warning(
        "core.archive",
        f"libarchive-c found but failed to load native library: {str(e)}"
        "\nLibarchive extraction fallback unavailable.",
    )


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
    ):
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
        debug_logger.info(
            "core.archive",
            f"ArchiveWorker.run: Entered run() for {self.input_path}",
        )
        """Execute the archive operation.

        This method is called when the worker is started by the thread pool.
        It performs the requested operation and reports progress.
        """
        try:
            debug_logger.info(
                "core.archive",
                (
                    f"[ArchiveWorker] Starting run at: {datetime.now()} | "
                    f"Operation: {self.operation} | Input: {self.input_path} | "
                    f"Output: {self.output_path} | Format: {self.archive_format} | "
                    f"Password: {'Yes' if self.password else 'No'}"
                ),
            )
        except Exception as logex:
            debug_logger.error(
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
            debug_logger.error(
                "core.archive",
                f"[ArchiveWorker] Uncaught exception at: {datetime.now()}\n{tb}",
            )
            self.signals.error.emit(
                f"Error during {self.operation} operation: {str(e)}\n{tb}"
            )

    def cancel(self):
        """Cancel the running operation."""
        self.cancelled = True
        debug_logger.info("core.archive", "Archive operation cancellation requested.")

    def _extract(self):
        """Extract an archive file, or skip if already extracted."""
        msg = f"[EXTRACT] Starting extraction: {self.input_path} -> {self.output_path}"
        debug_logger.info("core.archive", msg)

        if not os.path.exists(self.input_path):
            debug_logger.error(
                "core.archive",
                f"[ArchiveWorker] Input file not found: {self.input_path} at "
                f"{datetime.now()}",
            )
            self.signals.error.emit(f"Input file not found: {self.input_path}")
            return

        if self.cancelled:
            self.signals.error.emit("Extraction cancelled by user before start.")
            debug_logger.info("core.archive", "Extraction cancelled before start.")
            return

        # Determine output path if not specified
        if not self.output_path:
            self.output_path = os.path.splitext(self.input_path)[0]

        if os.path.exists(self.output_path):
            from core.file_scanner import (
                FileScanner,
            )  # Keep import local to avoid circular deps

            file_scanner = FileScanner()
            disk_images = file_scanner.find_disk_images(self.output_path)
            if disk_images:
                debug_logger.info(
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
                debug_logger.warning(
                    "core.archive",
                    f"[ArchiveWorker] Output folder {self.output_path} exists but "
                    f"contains no disk images. Proceeding with extraction.",
                )
                # Removed the error emission here, as overwriting/
                # re-extracting might be desired.
                # If this behavior is strictly an error,
                # it can be reinstated.

        os.makedirs(self.output_path, exist_ok=True)
        ext = os.path.splitext(self.input_path)[1].lower()
        self.signals.started.emit(f"Extracting {os.path.basename(self.input_path)}")

        extraction_succeeded = False
        try:
            debug_logger.info(
                "core.archive",
                f"[EXTRACT_DIAG] Archive extension is: '{ext}' for {self.input_path}",
            )
            if ext == ".zip":
                debug_logger.info(
                    "core.archive",
                    f"[EXTRACT_DIAG] Calling _extract_zip() for {self.input_path}",
                )
                self._extract_zip()  # This method emits its own errors or completes
                # Assume success if no exception/error signal from _extract_zip
                extraction_succeeded = True
            elif ext == ".7z":
                debug_logger.info(
                    "core.archive",
                    f"[EXTRACT_DIAG] Calling _extract_7z() for {self.input_path}",
                )
                self._extract_7z()  # This method handles its fallbacks and errors
                # Assume success if no exception/error signal from _extract_7z
                extraction_succeeded = True
            elif ext in [".rar", ".tar", ".gz", ".bz2", ".xz"]:
                debug_logger.info(
                    "core.archive",
                    f"[EXTRACT_DIAG] Calling _extract_patool() for {self.input_path}",
                )
                if self._extract_patool():  # _extract_patool returns True on success
                    extraction_succeeded = True
                else:
                    # _extract_patool returning False means it handled its error message
                    # internally or expects caller.
                    # We'll emit a generic one if it was the primary method.
                    self.signals.error.emit(
                        f"Extraction failed using patool for {self.input_path}"
                    )
                    return  # Stop further processing
            else:
                err_msg = f"Unsupported archive format: {ext} for {self.input_path}"
                debug_logger.error("core.archive", f"[EXTRACT_DIAG] {err_msg}")
                self.signals.error.emit(err_msg)
                return

            # If an error was emitted by _extract_zip or _extract_7z,
            # they would have returned or an exception occurred.
            # Check self.cancelled again in case an operation was lengthy
            # but didn't throw an exception.
            if self.cancelled:
                self.signals.error.emit("Extraction cancelled by user.")
                debug_logger.info(
                    "core.archive", "Extraction cancelled during operation."
                )
                return

            # If we reach here and extraction_succeeded is True,
            # and no error signal was emitted by sub-methods.
            if extraction_succeeded:
                self.signals.finished.emit(
                    True, "Extraction completed successfully", self.output_path
                )
            # If extraction_succeeded is False but no error signal was emitted
            # (e.g. patool failed silently to here) then an error should be emitted.
            # This path should ideally be covered by sub-methods emitting errors.

        except Exception as e:
            tb = traceback.format_exc()
            debug_logger.error(
                "core.archive",
                f"[ArchiveWorker] Extraction failed for "
                f"{self.input_path} at {datetime.now()}\n{tb}",
            )
            self.signals.error.emit(f"Extraction failed: {str(e)}\n{tb}")
            # Ensure no success signal is sent if an exception occurs here
            return

    def _extract_zip(self):
        """Extract a ZIP archive."""
        total_size = 0
        extracted_size = 0
        file_count = 0

        try:
            with zipfile.ZipFile(self.input_path, "r") as zip_ref:
                file_list = zip_ref.infolist()
                file_count = len(file_list)

                if file_count == 0:
                    self.signals.error.emit(f"ZIP archive is empty: {self.input_path}")
                    return

                self.signals.progress.emit(0, f"Found {file_count} files in archive")
                for file_info in file_list:
                    total_size += file_info.file_size

                for i, file_info in enumerate(file_list):
                    if self.cancelled:
                        debug_logger.info(
                            "core.archive", "ZIP extraction cancelled by user."
                        )
                        self.signals.error.emit(
                            "ZIP extraction cancelled."
                        )  # Emit error on cancellation
                        return

                    try:
                        pwd_bytes = (
                            self.password.encode("utf-8") if self.password else None
                        )
                        zip_ref.extract(file_info, self.output_path, pwd=pwd_bytes)
                        extracted_size += file_info.file_size
                        progress = (
                            (extracted_size / total_size) * 100 if total_size > 0 else 0
                        )
                        self.signals.progress.emit(
                            progress,
                            f"Extracting {file_info.filename} ({i + 1}/{file_count})",
                        )
                    except zipfile.BadZipFile as e:
                        error_message = str(e).lower()
                        if "compression method" in error_message:
                            debug_logger.warning(
                                "core.archive",
                                f"[EXTRACT_ZIP] ZIP file uses unsupported "
                                f"compression method. Attempting fallback with patoolib: {e}",
                            )
                            try:
                                patoolib.extract_archive(
                                    self.input_path,
                                    outdir=self.output_path,
                                    interactive=False,
                                    verbosity=-1,
                                )
                                debug_logger.info(
                                    "core.archive",
                                    "[EXTRACT_ZIP] Patoolib fallback successful.",
                                )
                            except Exception as patool_e:
                                debug_logger.error(
                                    "core.archive",
                                    f"[EXTRACT_ZIP] Patoolib fallback failed: {patool_e}",
                                )
                                raise  # Re-raise the patoolib error
                        else:
                            debug_logger.error(
                                "core.archive", f"[EXTRACT_ZIP] Bad ZIP file: {e}"
                            )
                            raise
                    except RuntimeError as e:
                        if (
                            "password required" in str(e).lower()
                            or "bad password" in str(e).lower()
                        ):
                            self.signals.error.emit(
                                f"Password required or incorrect for ZIP: "
                                f"{file_info.filename}"
                            )
                        else:
                            self.signals.error.emit(
                                f"Error extracting {file_info.filename} from ZIP: "
                                f"{str(e)}"
                            )
                        return
                    except Exception as e:
                        self.signals.error.emit(
                            f"Error extracting {file_info.filename} from ZIP: {str(e)}"
                        )
                        return
                self.signals.progress.emit(
                    100, f"Successfully extracted {file_count} ZIP files"
                )
        except zipfile.BadZipFile as e:
            self.signals.error.emit(
                f"Invalid ZIP file: {self.input_path}, Error: {str(e)}"
            )
        except Exception as e:
            self.signals.error.emit(
                f"Error during ZIP extraction for {self.input_path}: {str(e)}"
            )

    # --- Enhanced 7z Extraction ---
    def _extract_7z(self):
        """Extract a 7z archive with cross-platform fallback methods."""
        debug_logger.info(
            "core.archive",
            f"[EXTRACT_7Z] Entered _extract_7z for {self.input_path} -> "
            f"{self.output_path}",
        )

        if self.cancelled:
            self.signals.error.emit("7z extraction cancelled by user before start.")
            debug_logger.info("core.archive", "7z extraction cancelled before start.")
            return

        if self._extract_7z_py7zr():
            debug_logger.info(
                "core.archive",
                f"[EXTRACT_7Z] py7zr extraction successful for {self.input_path}.",
            )
            return

        if self.cancelled:
            self.signals.error.emit(
                "7z extraction cancelled by user after py7zr attempt."
            )
            debug_logger.info(
                "core.archive", "7z extraction cancelled after py7zr attempt."
            )
            return

        debug_logger.info(
            "core.archive", "[EXTRACT_7Z] py7zr failed, trying 7-Zip command line..."
        )
        if self._extract_7z_command_line():
            debug_logger.info(
                "core.archive",
                f"[EXTRACT_7Z] 7-Zip CLI extraction successful for {self.input_path}.",
            )
            return

        if self.cancelled:
            self.signals.error.emit(
                "7z extraction cancelled by user after CLI attempt."
            )
            debug_logger.info(
                "core.archive", "7z extraction cancelled after CLI attempt."
            )
            return

        if libarchive:  # Check if libarchive was imported successfully
            debug_logger.info(
                "core.archive",
                "[EXTRACT_7Z] 7-Zip command failed, trying libarchive...",
            )
            if self._extract_7z_libarchive():
                debug_logger.info(
                    "core.archive",
                    f"[EXTRACT_7Z] libarchive extraction successful "
                    f"for {self.input_path}.",
                )
                return
        else:
            debug_logger.info(
                "core.archive", "[EXTRACT_7Z] libarchive not available, skipping."
            )

        if self.cancelled:
            self.signals.error.emit(
                "7z extraction cancelled by user after libarchive attempt."
            )
            debug_logger.info(
                "core.archive", "7z extraction cancelled after libarchive attempt."
            )
            return

        debug_logger.info(
            "core.archive",
            "[EXTRACT_7Z] All 7z-specific methods failed, "
            "trying patoolib as a last resort...",
        )
        if self._extract_patool(is_fallback_for_7z=True):  # Pass flag if needed
            debug_logger.info(
                "core.archive",
                f"[EXTRACT_7Z] patoolib extraction (as 7z fallback) successful "
                f"for {self.input_path}.",
            )
            return

        error_msg = (
            "All 7z extraction methods (py7zr, 7-Zip CLI, libarchive, patoolib) failed."
        )
        debug_logger.error(
            "core.archive", f"[EXTRACT_7Z] {error_msg} for {self.input_path}"
        )
        self.signals.error.emit(error_msg)

    def _extract_7z_py7zr(self) -> bool:
        """Extract using py7zr library."""
        debug_logger.info(
            "core.archive",
            f"[EXTRACT_7Z_PY7ZR] Attempting py7zr extraction for {self.input_path}",
        )
        try:
            # Ensure py7zr is imported (it's a top-level import, so should be fine)
            with py7zr.SevenZipFile(
                self.input_path, mode="r", password=self.password
            ) as z:
                # Progress reporting for py7zr is tricky for extractall.
                # We can count files first.
                total_files: int = -1  # Initialize as int, -1 for unknown
                try:
                    all_files = z.getnames()  # Or z.list() for more details
                    total_files = len(all_files)
                except Exception:  # Some archives might not support getnames()
                    # before extraction easily
                    # total_files remains -1, indicating unknown
                    pass

                progress_message = (
                    f"Extracting archive with {total_files} files (py7zr)..."
                    if total_files != -1
                    else "Extracting archive (py7zr)..."
                )
                self.signals.progress.emit(0, progress_message)

                # py7zr does not have a per-file callback for extractall
                # to check self.cancelled easily.
                # The main cancellation check before this method is the primary guard.
                z.extractall(path=self.output_path)

                # If extractall succeeds, report 100%
                self.signals.progress.emit(
                    100, f"Extracted {total_files} files (py7zr)"
                )
                debug_logger.info(
                    "core.archive",
                    f"[EXTRACT_7Z_PY7ZR] py7zr extraction complete "
                    f"for {self.input_path}.",
                )
            return True
        except py7zr.PasswordRequired:
            err_msg = f"Password required for 7z archive (py7zr): {self.input_path}"
            debug_logger.error("core.archive", f"[EXTRACT_7Z_PY7ZR] {err_msg}")
            # Don't emit error here, let the orchestrator _extract_7z decide
            return False
        except Exception as e:
            err_msg = f"py7zr extraction failed for {self.input_path}: {str(e)}"
            debug_logger.error(
                "core.archive",
                f"[EXTRACT_7Z_PY7ZR] {err_msg}\n{traceback.format_exc()}",
            )
            return False

    def _extract_7z_command_line(self) -> bool:
        """Extract using 7-Zip command line tool."""
        debug_logger.info(
            "core.archive",
            f"[EXTRACT_7Z_CMD] Attempting 7-Zip CLI extraction for {self.input_path}",
        )

        if self.cancelled:
            debug_logger.info(
                "core.archive",
                "[EXTRACT_7Z_CMD] Operation cancelled before starting CLI tool.",
            )
            return False  # Indicate failure due to cancellation for the orchestrator

        system = platform.system().lower()
        cmd_exec = None
        if system == "windows":
            possible_paths = [
                "7z.exe",
                "7za.exe",
                os.path.join(
                    os.environ.get("ProgramFiles", "C:\\Program Files"),
                    "7-Zip",
                    "7z.exe",
                ),
                os.path.join(
                    os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                    "7-Zip",
                    "7z.exe",
                ),
                os.path.join(
                    os.environ.get("ProgramW6432", "C:\\Program Files"),
                    "7-Zip",
                    "7z.exe",
                ),  # For 32-bit Python on 64-bit Windows
            ]
        else:  # Linux, macOS
            possible_paths = ["7z", "7za", "p7zip"]

        for p_cmd in possible_paths:
            try:
                # Check if command exists and is executable
                test_cmd_args = [p_cmd]  # Just the command to see if it runs
                subprocess.run(
                    test_cmd_args,
                    capture_output=True,
                    timeout=3,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW
                    if system == "windows"
                    else 0,
                )
                # If it didn't throw FileNotFoundError, it's likely found.
                # A more robust check might involve parsing `7z i` output.
                # For now, if it runs without FileNotFoundError,
                # assume it's usable.
                # The `check=False` means we don't rely on return code here,
                # just existence.
                cmd_exec = p_cmd
                debug_logger.info(
                    "core.archive",
                    f"[EXTRACT_7Z_CMD] Found 7-Zip executable: {cmd_exec}",
                )
                break
            except FileNotFoundError:
                debug_logger.debug(
                    "core.archive", f"[EXTRACT_7Z_CMD] Command not found: {p_cmd}"
                )
                continue
            except subprocess.TimeoutExpired:
                debug_logger.debug(
                    "core.archive",
                    f"[EXTRACT_7Z_CMD] Timeout checking command: {p_cmd}",
                )
                continue
            except Exception as e:  # Catch other potential errors during check
                debug_logger.debug(
                    "core.archive",
                    f"[EXTRACT_7Z_CMD] Error checking command {p_cmd}: {e}",
                )
                continue

        if not cmd_exec:
            debug_logger.warning(
                "core.archive", "[EXTRACT_7Z_CMD] 7-Zip command line tool not found."
            )
            return False

        cmd = [
            cmd_exec,
            "x",
            self.input_path,
            f"-o{self.output_path}",
            "-y",
        ]  # x for extract with full paths, -y for yes to all
        if self.password:
            cmd.append(f"-p{self.password}")

        self.signals.progress.emit(10, "Starting 7-Zip CLI extraction...")
        debug_logger.info(
            "core.archive", f"[EXTRACT_7Z_CMD] Executing: {' '.join(cmd)}"
        )
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
                check=False,  # We check returncode manually
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if system == "windows" else 0
                ),
            )
            if process.returncode == 0:
                # Simple progress, as parsing CLI output for file count
                # is complex and varies.
                self.signals.progress.emit(100, "7-Zip CLI extraction completed.")
                debug_logger.info(
                    "core.archive",
                    f"[EXTRACT_7Z_CMD] 7-Zip CLI extraction successful for "
                    f"{self.input_path}. Output: {process.stdout[:500]}",
                )
                return True
            else:
                err_msg = (
                    f"7-Zip CLI failed (code {process.returncode}) "
                    f"for {self.input_path}: {process.stderr[:500]}"
                )
                debug_logger.error("core.archive", f"[EXTRACT_7Z_CMD] {err_msg}")
                return False
        except subprocess.TimeoutExpired:
            err_msg = f"7-Zip CLI extraction timed out for {self.input_path}"
            debug_logger.error("core.archive", f"[EXTRACT_7Z_CMD] {err_msg}")
            return False
        except Exception as e:
            err_msg = (
                f"Error during 7-Zip CLI extraction for {self.input_path}: {str(e)}"
            )
            debug_logger.error(
                "core.archive", f"[EXTRACT_7Z_CMD] {err_msg}\n{traceback.format_exc()}"
            )
            return False

    def _extract_7z_libarchive(self) -> bool:
        """Extract using libarchive (if available)."""
        if not libarchive:  # Check if module was imported
            return False

        debug_logger.info(
            "core.archive",
            f"[EXTRACT_7Z_LIBARCHIVE] Attempting libarchive extraction "
            f"for {self.input_path}",
        )

        if self.cancelled:
            debug_logger.info(
                "core.archive",
                "[EXTRACT_7Z_LIBARCHIVE] Operation cancelled "
                "before starting libarchive.",
            )
            return False

        # libarchive-c doesn't have a direct password option in file_reader
        # for 7z like py7zr.
        # It might handle some types of encryption if the underlying
        # libarchive build supports it.
        # We proceed without explicit password handling here for libarchive.
        self.signals.progress.emit(20, "Starting libarchive extraction...")
        extracted_files_count = 0
        try:
            # Note: libarchive.public.file_reader or libarchive.file_reader
            reader_func = getattr(
                libarchive, "file_reader", None
            )  # Accommodate different import styles
            if not reader_func:
                reader_func = getattr(libarchive.public, "file_reader", None)

            if not reader_func:
                debug_logger.error(
                    "core.archive",
                    "[EXTRACT_7Z_LIBARCHIVE] Could not find file_reader in libarchive.",
                )
                return False

            with reader_func(self.input_path) as archive:
                for i, entry in enumerate(archive):
                    if self.cancelled:
                        debug_logger.info(
                            "core.archive",
                            "[EXTRACT_7Z_LIBARCHIVE] Extraction cancelled "
                            "during processing.",
                        )
                        # Don't emit error here, let the orchestrator
                        # handle it or return False
                        return False  # Indicate failure due to cancellation

                    assert self.output_path is not None  # Ensure output_path is str
                    entry_path = os.path.join(
                        self.output_path, entry.pathname
                    )  # Use pathname

                    # Ensure parent directory exists
                    if entry.filetype.file:  # Check if it's a file
                        os.makedirs(os.path.dirname(entry_path), exist_ok=True)
                        with open(entry_path, "wb") as f_out:
                            for block in entry.get_blocks():
                                f_out.write(block)
                        extracted_files_count += 1
                        self.signals.progress.emit(
                            20 + (i * 0.7), f"Extracting (libarchive): {entry.pathname}"
                        )  # Rough progress
                    elif entry.filetype.directory:  # Check if it's a directory
                        os.makedirs(entry_path, exist_ok=True)

            self.signals.progress.emit(
                100, f"Extracted {extracted_files_count} files using libarchive."
            )
            debug_logger.info(
                "core.archive",
                f"[EXTRACT_7Z_LIBARCHIVE] libarchive extraction successful "
                f"for {self.input_path}, {extracted_files_count} files.",
            )
            return True
        except Exception as e:
            # Check for common libarchive errors, e.g., related to password
            err_str = str(e).lower()
            if "password required" in err_str or "decryption failed" in err_str:
                err_msg = (
                    f"libarchive failed for {self.input_path},"
                    f" possibly due to encryption/password:"
                    f" {str(e)}"
                )
            else:
                err_msg = (
                    f"libarchive extraction failed for {self.input_path}: {str(e)}"
                )
            debug_logger.error(
                "core.archive",
                f"[EXTRACT_7Z_LIBARCHIVE] {err_msg}\n{traceback.format_exc()}",
            )
            return False

    def _extract_patool(self, is_fallback_for_7z: bool = False) -> bool:
        """Extract an archive using patool (for RAR, TAR, etc., or as 7z fallback).
        Returns True on success, False on error.
        """
        context = " (as 7z fallback)" if is_fallback_for_7z else ""
        debug_logger.info(
            "core.archive",
            f"[EXTRACT_PATOOL] Attempting patool extraction{context} "
            f"for {self.input_path} -> {self.output_path}",
        )

        if self.cancelled:
            debug_logger.info(
                "core.archive",
                f"[EXTRACT_PATOOL] Operation cancelled before "
                f"starting patool{context}.",
            )
            return False

        self.signals.progress.emit(
            0,
            f"Starting extraction with patool{context} "
            f"for {os.path.basename(self.input_path)}...",
        )
        try:
            # patoolib doesn't take password directly in extract_archive.
            # It might prompt if interactive=True, or use environment variables
            # for some backends (e.g. UNRAR_PASSWORD).
            # For non-interactive, password-protected archives might fail
            # if backend (e.g. unrar) needs it.
            patoolib.extract_archive(
                self.input_path,
                outdir=self.output_path,
                interactive=False,
                verbosity=-1,
            )
            # Patoolib does not provide easy file count or granular progress.
            self.signals.progress.emit(
                100, f"Extraction with patool{context} completed."
            )
            debug_logger.info(
                "core.archive",
                f"[EXTRACT_PATOOL] patool extraction{context} successful "
                f"for {self.input_path}",
            )
            return True
        except Exception as e:
            err_msg = (
                f"patool extraction{context} failed for {self.input_path}: {str(e)}"
            )
            debug_logger.error(
                "core.archive", f"[EXTRACT_PATOOL] {err_msg}\n{traceback.format_exc()}"
            )
            # If this is a primary call (not a 7z fallback),
            # the main _extract will emit error.
            # If it's a fallback, _extract_7z will handle it.
            return False

    # --- Compression Methods ---
    def _compress(self):
        """Compress a file or directory."""
        if not self.output_path:
            base, _ = os.path.splitext(self.input_path)
            self.output_path = f"{base}.{self.archive_format}"
            debug_logger.info(
                "core.archive",
                f"Output path not specified, defaulting to: {self.output_path}",
            )

        if self.cancelled:
            self.signals.error.emit("Compression cancelled by user before start.")
            debug_logger.info("core.archive", "Compression cancelled before start.")
            return

        self.signals.started.emit(
            f"Compressing to {os.path.basename(self.output_path)}"
        )
        debug_logger.info(
            "core.archive",
            f"[COMPRESS] Starting compression: {self.input_path} -> "
            f"{self.output_path} (format: {self.archive_format})",
        )

        compression_succeeded = False
        try:
            if self.archive_format == "zip":
                self._compress_zip()
                compression_succeeded = True
            elif self.archive_format == "7z":
                self._compress_7z()
                compression_succeeded = True
            elif self.archive_format in [
                "rar",
                "tar",
                "gz",
                "bz2",
                "xz",
            ]:  # patool for others
                self._compress_patool()
                compression_succeeded = True
            else:
                self.signals.error.emit(
                    f"Unsupported compression format: {self.archive_format}"
                )
                return

            if self.cancelled:  # Check after potentially long operation
                self.signals.error.emit("Compression cancelled by user.")
                debug_logger.info(
                    "core.archive", "Compression cancelled during operation."
                )
                return

            if compression_succeeded:
                self.signals.finished.emit(
                    True, "Compression completed successfully", self.output_path
                )

        except Exception as e:
            tb = traceback.format_exc()
            debug_logger.error(
                "core.archive",
                f"[ArchiveWorker] Compression failed for {self.input_path} "
                f"at {datetime.now()}\n{tb}",
            )
            self.signals.error.emit(f"Compression failed: {str(e)}\n{tb}")

    def _compress_zip(self):
        """Compress to a ZIP archive."""
        # Code for _compress_zip remains largely the same
        # Ensure logging uses debug_logger
        debug_logger.info(
            "core.archive",
            f"Compressing to ZIP: {self.input_path} -> {self.output_path}",
        )
        if os.path.isdir(self.input_path):
            total_files = sum(len(files) for _, _, files in os.walk(self.input_path))
            processed_files = 0
            with zipfile.ZipFile(
                self.output_path, "w", zipfile.ZIP_DEFLATED
            ) as zip_file:
                for root, _, files in os.walk(self.input_path):
                    for file in files:
                        if self.cancelled:
                            debug_logger.info(
                                "core.archive", "ZIP compression cancelled by user."
                            )
                            raise Exception(
                                "Operation cancelled by user"
                            )  # Will be caught by _compress
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(
                            file_path, os.path.dirname(self.input_path)
                        )
                        zip_file.write(file_path, arcname)
                        processed_files += 1
                        progress = (
                            (processed_files / total_files) * 100
                            if total_files > 0
                            else 0
                        )
                        self.signals.progress.emit(
                            progress,
                            f"Compressing {file} ({processed_files}/{total_files})",
                        )
        else:  # Single file
            with zipfile.ZipFile(
                self.output_path, "w", zipfile.ZIP_DEFLATED
            ) as zip_file:
                if self.cancelled:
                    debug_logger.info(
                        "core.archive", "ZIP compression cancelled by user."
                    )
                    raise Exception("Operation cancelled by user")
                arcname = os.path.basename(self.input_path)
                zip_file.write(self.input_path, arcname)
                self.signals.progress.emit(100, f"Compressed {arcname}")
        debug_logger.info(
            "core.archive", f"ZIP compression finished for {self.output_path}"
        )

    def _compress_7z(self):
        """Compress to a 7z archive."""
        # (Code for _compress_7z remains largely the same, ensure self.cancelled checks)
        # Ensure logging uses debug_logger
        debug_logger.info(
            "core.archive",
            f"Compressing to 7Z: {self.input_path} -> {self.output_path}",
        )
        filters = None
        if self.password:
            # py7zr password encryption typically requires a filter.
            # For AES256 + header encryption (common for 7-Zip GUI)
            filters = [
                {"id": py7zr.FILTER_LZMA2, "preset": 7},
                {"id": py7zr.FILTER_AES256SHA256},
            ]  # This is an example, might need adjustment
            debug_logger.info(
                "core.archive", f"Using password for 7z compression. Filters: {filters}"
            )

        if os.path.isdir(self.input_path):
            files_to_add = []
            # No longer need to calculate base_path,
            # using input_dir_name and relative_path instead
            # Get the base directory name for proper archiving
            norm_path = os.path.normpath(self.input_path)
            input_dir_name = os.path.basename(norm_path)

            for root, _, files in os.walk(self.input_path):
                for file in files:
                    if self.cancelled:
                        debug_logger.info(
                            "core.archive", "7z compression cancelled by user."
                        )
                        raise Exception("Operation cancelled by user")
                    file_path = os.path.join(root, file)
                    # Create arcname relative to the input directory itself
                    # being the root in archive, e.g., compressing 'myfolder'
                    # should result in 'file.txt', not 'myfolder/file.txt' in archive
                    # Get path relative to input directory
                    relative_path = os.path.relpath(file_path, self.input_path)
                    arcname = (
                        os.path.join(input_dir_name, relative_path)
                        if input_dir_name
                        else relative_path
                    )
                    files_to_add.append((arcname, file_path))

            total_files = len(files_to_add)
            if total_files == 0:
                debug_logger.warning(
                    "core.archive",
                    f"No files found in directory {self.input_path} to compress to 7z.",
                )
                # Create an empty archive or error? py7zr might handle empty gracefully.

            with py7zr.SevenZipFile(
                self.output_path, mode="w", password=self.password, filters=filters
            ) as z:
                for i, (arcname, file_path) in enumerate(files_to_add):
                    if self.cancelled:
                        debug_logger.info(
                            "core.archive", "7z compression cancelled by user."
                        )
                        raise Exception("Operation cancelled by user")
                    z.write(file_path, arcname)
                    progress = ((i + 1) / total_files) * 100 if total_files > 0 else 0
                    self.signals.progress.emit(
                        progress, f"Compressing {arcname} ({i + 1}/{total_files})"
                    )
        else:  # Single file
            with py7zr.SevenZipFile(
                self.output_path, mode="w", password=self.password, filters=filters
            ) as z:
                if self.cancelled:
                    debug_logger.info(
                        "core.archive", "7z compression cancelled by user."
                    )
                    raise Exception("Operation cancelled by user")
                arcname = os.path.basename(self.input_path)
                z.write(self.input_path, arcname)
                self.signals.progress.emit(100, f"Compressed {arcname}")
        debug_logger.info(
            "core.archive", f"7Z compression finished for {self.output_path}"
        )

    def _compress_patool(self):
        """Compress using patool (for formats like RAR, TAR, etc.)."""
        debug_logger.info(
            "core.archive",
            f"Compressing with patool: {self.input_path} -> "
            f"{self.output_path} (format: {self.archive_format})",
        )
        self.signals.progress.emit(0, "Starting patool compression...")
        if self.cancelled:
            debug_logger.info("core.archive", "patool compression cancelled by user.")
            raise Exception("Operation cancelled by user")

        # patoolib.create_archive(archive, file_list, verbosity,
        # interactive, program)
        # We need to specify the program for formats like rar,
        # or let patool figure it out.
        # For specific format:
        # patoolib.create_archive(self.output_path,
        # (self.input_path,),
        # program=self.archive_format)
        # However, 'program' is more like 'rar', 'zip', not the extension.
        # patool should infer the appropriate program.
        patoolib.create_archive(
            self.output_path, (self.input_path,), interactive=False, verbosity=-1
        )

        if os.path.isdir(self.input_path):
            file_count = sum([len(files) for r, d, files in os.walk(self.input_path)])
            self.signals.progress.emit(
                100, f"Compressed {file_count} files using patool"
            )
        else:
            self.signals.progress.emit(
                100, f"Compressed {os.path.basename(self.input_path)} using patool"
            )
        debug_logger.info(
            "core.archive", f"patool compression finished for {self.output_path}"
        )


class ArchiveManager:
    """Manager for archive operations.
    (Class remains the same as original)
    """

    def __init__(self):
        self.thread_pool = QThreadPool()

    def extract(
        self,
        archive_path: str,
        output_path: Optional[str] = None,
        password: Optional[str] = None,
    ) -> ArchiveSignals:
        if not os.path.exists(archive_path):
            # Log here as well before raising, or let caller handle logging
            debug_logger.error(
                "core.archive",
                f"[ArchiveManager.extract] Archive file not found: {archive_path}",
            )
            raise FileNotFoundError(f"Archive file not found: {archive_path}")

        resolved_output_path = (
            output_path if output_path else None
        )  # None if empty string too
        if resolved_output_path is None:  # If still None after check
            resolved_output_path = os.path.splitext(archive_path)[0]
        debug_logger.info(
            "core.archive",
            f"[ArchiveManager.extract] Archive: {archive_path}, "
            f"Output: {resolved_output_path}",
        )

        worker = ArchiveWorker(
            operation="extract",
            input_path=archive_path,
            output_path=resolved_output_path,
            password=password,
        )
        self.thread_pool.start(worker)
        debug_logger.info(
            "core.archive",
            f"[ArchiveManager.extract] Worker started for {archive_path}",
        )
        return worker.signals

    def compress(
        self,
        input_path: str,
        output_path: Optional[
            str
        ] = None,  # Output path is where the archive will be created
        archive_format: str = "zip",
        password: Optional[str] = None,
    ) -> ArchiveSignals:
        if not os.path.exists(input_path):
            debug_logger.error(
                "core.archive",
                f"[ArchiveManager.compress] Input path not found: {input_path}",
            )
            raise FileNotFoundError(f"Input path not found: {input_path}")

        supported_formats = ["zip", "7z", "rar", "tar", "gz", "bz2", "xz"]
        if archive_format not in supported_formats:
            debug_logger.error(
                "core.archive",
                f"[ArchiveManager.compress] Unsupported archive format: "
                f"{archive_format}",
            )
            raise ValueError(
                f"Unsupported archive format: {archive_format}."
                f"Supported: {supported_formats}"
            )

        # Determine default output_path if not provided
        actual_output_path = output_path
        if not actual_output_path:
            if os.path.isdir(input_path):
                actual_output_path = (
                    f"{os.path.basename(os.path.normpath(input_path))}.{archive_format}"
                )
            else:  # isfile
                base, _ = os.path.splitext(input_path)
                actual_output_path = f"{base}.{archive_format}"
            # Prepend input_path's directory if output_path became just a filename
            if not os.path.dirname(actual_output_path) and os.path.dirname(input_path):
                actual_output_path = os.path.join(
                    os.path.dirname(input_path), actual_output_path
                )
            elif not os.path.dirname(actual_output_path):  # Still no dir, use CWD
                actual_output_path = os.path.join(os.getcwd(), actual_output_path)

        debug_logger.info(
            "core.archive",
            f"[ArchiveManager.compress] Input: {input_path}, "
            f"Output: {actual_output_path}, Format: {archive_format}",
        )
        worker = ArchiveWorker(
            operation="compress",
            input_path=input_path,
            output_path=actual_output_path,
            archive_format=archive_format,
            password=password,
        )
        self.thread_pool.start(worker)
        debug_logger.info(
            "core.archive", f"[ArchiveManager.compress] Worker started for {input_path}"
        )
        return worker.signals

    def extract_sync_to_temp(self, archive_path, password=None):
        """
        Synchronously extract an archive to a temporary directory.
        Returns the path to the extracted folder, or None on failure.

        Args:
            archive_path: Path to the archive file
            password: Optional password for protected archives
        """
        if not os.path.exists(archive_path):
            debug_logger.warning(
                "core.archive",
                f"[extract_sync_to_temp] Archive not found: {archive_path}",
            )
            return None

        ext = os.path.splitext(archive_path)[1].lower()
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(prefix="retroclamp_extract_")
            debug_logger.info(
                "core.archive",
                f"[extract_sync_to_temp] Extracting {archive_path} "
                f"to temp dir {temp_dir}",
            )

            if ext == ".zip":
                debug_logger.info(
                    "core.archive",
                    f"[extract_sync_to_temp] Opening ZIP file: {archive_path}",
                )

                # Check if the file exists and is readable
                try:
                    file_size = os.path.getsize(archive_path)
                    debug_logger.info(
                        "core.archive",
                        f"[extract_sync_to_temp] ZIP file size: {file_size} bytes",
                    )

                    # Additional file checks
                    if file_size == 0:
                        debug_logger.error(
                            "core.archive",
                            f"[extract_sync_to_temp] ZIP file is empty: {archive_path}",
                        )
                        raise ValueError(f"ZIP file is empty: {archive_path}")

                    # Check if file is readable
                    with open(archive_path, "rb") as test_file:
                        header = test_file.read(4)
                        if header[:2] != b"PK":
                            debug_logger.error(
                                "core.archive",
                                f"[extract_sync_to_temp] File doesn't appear to be a "
                                f"valid ZIP (header: {header})",
                            )
                            raise ValueError(f"Invalid ZIP file header: {header}")

                except Exception as e:
                    debug_logger.error(
                        "core.archive",
                        f"[extract_sync_to_temp] Error accessing ZIP file: {e}",
                    )
                    raise

                try:
                    # Test if ZIP can be opened first
                    debug_logger.info(
                        "core.archive",
                        "[extract_sync_to_temp] Testing ZIP file integrity...",
                    )

                    with zipfile.ZipFile(archive_path, "r") as test_zip:
                        # Test the ZIP file integrity
                        bad_file = test_zip.testzip()
                        if bad_file:
                            debug_logger.error(
                                "core.archive",
                                f"[extract_sync_to_temp] ZIP file integrity check "
                                f"failed. Bad file: {bad_file}",
                            )
                            raise zipfile.BadZipFile(
                                f"ZIP integrity check failed. Bad file: {bad_file}"
                            )

                        # List file contents for debugging
                        file_list = test_zip.namelist()
                        file_count = len(file_list)
                        debug_logger.info(
                            "core.archive",
                            f"[extract_sync_to_temp] ZIP contains {file_count} files",
                        )
                        if file_count == 0:
                            debug_logger.warning(
                                "core.archive",
                                "[extract_sync_to_temp] ZIP file contains no files",
                            )
                            # Don't fail here, empty archives are valid
                        elif file_count > 0:
                            debug_logger.info(
                                "core.archive",
                                f"[extract_sync_to_temp] First few files: "
                                f"{file_list[:5]}",
                            )

                        # Check if output directory is writable
                        if not os.access(temp_dir, os.W_OK):
                            debug_logger.error(
                                "core.archive",
                                f"[extract_sync_to_temp] Output directory not "
                                f"writable: {temp_dir}",
                            )
                            raise PermissionError(
                                f"Output directory not writable: {temp_dir}"
                            )

                    # Now do the actual extraction
                    debug_logger.info(
                        "core.archive",
                        f"[extract_sync_to_temp] Starting extraction of {file_count} "
                        f"files to {temp_dir}",
                    )

                    with zipfile.ZipFile(archive_path, "r") as zf:
                        # Check if password is needed
                        try:
                            # Try to read the first file without password
                            if file_list:
                                first_file_info = zf.getinfo(file_list[0])
                                if first_file_info.flag_bits & 0x1:
                                    # Password protected
                                    debug_logger.info(
                                        "core.archive",
                                        "[extract_sync_to_temp] ZIP file appears to be "
                                        "password protected",
                                    )
                                    if not password:
                                        debug_logger.error(
                                            "core.archive",
                                            "[extract_sync_to_temp] Password required "
                                            "but not provided",
                                        )
                                        raise RuntimeError(
                                            "Password required for encrypted ZIP file"
                                        )
                        except Exception as e:
                            debug_logger.warning(
                                "core.archive",
                                f"[extract_sync_to_temp] Could not check password "
                                f"requirement: {e}",
                            )

                        # Extract with or without password
                        if password:
                            debug_logger.info(
                                "core.archive",
                                "[extract_sync_to_temp] Extracting with password",
                            )
                            pwd_bytes = password.encode("utf-8")
                            zf.extractall(temp_dir, pwd=pwd_bytes)
                        else:
                            debug_logger.info(
                                "core.archive",
                                "[extract_sync_to_temp] Extracting without password",
                            )
                            zf.extractall(temp_dir)

                    # Verify extraction
                    try:
                        extracted_items = os.listdir(temp_dir)
                        debug_logger.info(
                            "core.archive",
                            f"[extract_sync_to_temp] Extracted {len(extracted_items)} "
                            f"items",
                        )
                        if len(extracted_items) == 0:
                            debug_logger.warning(
                                "core.archive",
                                f"[extract_sync_to_temp] No items extracted to "
                                f"{temp_dir}. This might be valid for some archives.",
                            )
                        debug_logger.info(
                            "core.archive",
                            f"[extract_sync_to_temp] Extracted items: "
                            f"{extracted_items[:10]}",  # Show first 10
                        )
                    except Exception as e:
                        debug_logger.error(
                            "core.archive",
                            f"[extract_sync_to_temp] Error listing extracted files: {e}",
                        )
                        raise

                except zipfile.BadZipFile as e:
                    error_message = str(e).lower()
                    if "compression method" in error_message:
                        debug_logger.warning(
                            "core.archive",
                            f"[extract_sync_to_temp] ZIP file uses unsupported "
                            f"compression method. Attempting fallback with patoolib: {e}",
                        )
                        try:
                            debug_logger.debug(
                                "core.archive",
                                f"[extract_sync_to_temp] Calling patoolib.extract_archive for {archive_path} to {temp_dir}",
                            )
                            patoolib.extract_archive(
                                archive_path,
                                outdir=temp_dir,
                                interactive=False,
                                verbosity=-1,
                            )
                            debug_logger.info(
                                "core.archive",
                                "[extract_sync_to_temp] Patoolib fallback successful.",
                            )
                        except Exception as patool_e:
                            debug_logger.error(
                                "core.archive",
                                f"[extract_sync_to_temp] Patoolib fallback failed: {patool_e}",
                            )
                            debug_logger.debug(
                                "core.archive",
                                f"[extract_sync_to_temp] Patoolib traceback: {traceback.format_exc()}",
                            )
                            raise  # Re-raise the patoolib error
                    else:
                        debug_logger.error(
                            "core.archive", f"[extract_sync_to_temp] Bad ZIP file: {e}"
                        )
                        raise
                except RuntimeError as e:
                    # Handle password-protected files
                    error_str = str(e).lower()
                    if (
                        "password" in error_str
                        or "encrypted" in error_str
                        or "bad password" in error_str
                    ):
                        if password:
                            debug_logger.error(
                                "core.archive",
                                f"[extract_sync_to_temp] Incorrect password provided: "
                                f"{e}",
                            )
                            raise RuntimeError(
                                f"Incorrect password for ZIP file: {e}"
                            ) from e
                        else:
                            debug_logger.error(
                                "core.archive",
                                "[extract_sync_to_temp] Password required but not "
                                "provided",
                            )
                            raise RuntimeError(
                                f"Password required for ZIP file: {e}"
                            ) from e
                    else:
                        debug_logger.error(
                            "core.archive",
                            f"[extract_sync_to_temp] Runtime error during extraction: "
                            f"{str(e)[:85]}",
                        )
                        raise
                except PermissionError as e:
                    debug_logger.error(
                        "core.archive", f"[extract_sync_to_temp] Permission error: {e}"
                    )
                    raise
                except Exception as e:
                    debug_logger.error(
                        "core.archive",
                        f"[extract_sync_to_temp] Unexpected error during ZIP "
                        f"extraction: {e}",
                    )
                    raise

            elif ext == ".7z":
                # Using py7zr for sync temp extraction for simplicity,
                # could also use the new fallback logic if needed.
                debug_logger.info(
                    "core.archive",
                    f"[extract_sync_to_temp] Extracting 7z file: {archive_path}",
                )
                with py7zr.SevenZipFile(archive_path, "r", password=password) as zf:
                    zf.extractall(path=temp_dir)
            elif ext in [".rar", ".tar", ".gz", ".bz2", ".xz"]:
                debug_logger.info(
                    "core.archive",
                    f"[extract_sync_to_temp] Extracting {ext} file with patool: "
                    f"{archive_path}",
                )
                patoolib.extract_archive(
                    archive_path, outdir=temp_dir, interactive=False, verbosity=-1
                )
            else:
                debug_logger.warning(
                    "core.archive",
                    f"[extract_sync_to_temp] Unsupported archive type {ext} "
                    f"for {archive_path}",
                )
                if temp_dir:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                return None

            # Final verification that temp_dir exists and has content
            if not os.path.exists(temp_dir):
                debug_logger.error(
                    "core.archive",
                    f"[extract_sync_to_temp] Temp directory was not created: "
                    f"{temp_dir}",
                )
                return None

            try:
                final_items = os.listdir(temp_dir)
                if len(final_items) == 0:
                    debug_logger.warning(
                        "core.archive",
                        f"[extract_sync_to_temp] Temp directory is empty after "
                        f"extraction: {temp_dir}",
                    )
                    # For some use cases, empty extraction might be valid

                debug_logger.info(
                    "core.archive",
                    f"[extract_sync_to_temp] Successfully extracted archive to "
                    f"{temp_dir} with {len(final_items)} items",
                )
            except Exception as e:
                debug_logger.error(
                    "core.archive",
                    f"[extract_sync_to_temp] Error during final verification: {e}",
                )
                return None

            return temp_dir

        except Exception as e:
            debug_logger.error(
                "core.archive",
                f"[extract_sync_to_temp] Failed to extract {archive_path}: "
                f"{e}\n{traceback.format_exc()}",
            )
            if temp_dir and os.path.exists(temp_dir):  # Ensure cleanup on failure
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    debug_logger.info(
                        "core.archive",
                        f"[extract_sync_to_temp] Cleaned up temp directory after "
                        f"failure: {temp_dir}",
                    )
                except Exception as cleanup_error:
                    debug_logger.warning(
                        "core.archive",
                        f"[extract_sync_to_temp] Could not clean up temp directory "
                        f"{temp_dir}: {cleanup_error}",
                    )
            return None

    @staticmethod
    def is_archive(file_path) -> bool:
        if file_path is None or not isinstance(file_path, str):
            return False
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return False
        try:
            ext = os.path.splitext(file_path)[1].lower()
            return ext in [".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"]
        except Exception:
            return False
