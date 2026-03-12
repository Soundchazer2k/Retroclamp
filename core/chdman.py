"""CHDMAN wrapper module for RetroClamp.

This module provides a Pythonic interface to the CHDMAN command-line utility,
allowing for compression, extraction, verification, and information retrieval
operations on CHD files with proper progress reporting and error handling.
"""

import functools
import logging

from core.debug_logger import DebugLogger, get_logger

debug_logger = DebugLogger()
import os
import re
import shutil
import subprocess  # Added import

# Bandit note: All subprocess usage in this module is controlled.
# No untrusted input is used.
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path  # Added for modern path handling
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import (
    QMutex,
    QMutexLocker,
    QObject,
    QProcess,  # Ensure QProcess is listed here
    QRunnable,
    QThreadPool,
    Signal,
)

from modules.settings import load_chdman_path


class CHDCompressionType(Enum):
    """Available compression types for CHD files."""

    ZLIB = "zlib"
    ZLIB_HUFF = "zlib_huff"
    LZMA = "lzma"
    SDX = "sdx"
    AUTO = "auto"


class CHDManError(Exception):
    """Base exception for CHDMAN operations."""

    pass


class CHDManExecutableNotFoundError(CHDManError):
    """Raised when the CHDMAN executable cannot be found."""

    pass


class CHDManCommandError(CHDManError):
    """Raised when a CHDMAN command fails."""

    def __init__(self, command: str, returncode: int, output: str):
        self.command = command
        self.returncode = returncode
        self.output = output
        super().__init__(
            f"CHDMAN command '{command}' failed with return code {returncode}: {output}"
        )


class CHDManInputFileError(CHDManError):
    """Raised when an input file is invalid or not found."""

    pass


class CHDManOutputFileError(CHDManError):
    """Raised when an output file cannot be created or written to."""

    pass


@dataclass
class CHDManCommand:
    """Represents a CHDMAN command with its parameters."""

    name: str
    description: str
    requires_input: bool
    requires_output: bool
    supports_compression: bool


class CHDManSignals(QObject):
    """Signals for CHDMan operations."""

    started = Signal(str)
    progress = Signal(float, str)
    finished = Signal(bool, str)
    error = Signal(str)
    progress_updated = Signal(float, str, str)
    task_completed = Signal(str, bool, str)
    error_occurred = Signal(str)


class CHDManWorker(QRunnable):
    """Worker for running CHDMAN operations in a separate thread."""

    VALID_COMPRESSION_ALGORITHMS = [
        "none",
        "zlib",
        "zstd",
        "lzma",
        "huff",
        "flac",
        "cdlz",
        "cdzl",
        "cdfl",
        "avhu",
    ]
    COMPRESSION_CORRECTIONS = {"cdzlib": "cdzl", "cdflac": "cdfl"}

    def __init__(
        self,
        executable_path: str,
        command: str,
        input_file: str,
        output_file: Optional[str] = None,
        compression: Optional[str] = None,
        hunk_size: Optional[int] = None,
        force: bool = False,
        verbose: bool = True,
        app_settings: Any = None,
        worker_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__()
        self.executable_path = executable_path
        self.command = command
        # Use Path objects for input and output files
        self.input_file = Path(input_file) if input_file is not None else None
        self.output_file = Path(output_file) if output_file is not None else None
        self.compression = compression
        self.hunk_size = hunk_size
        self.force = force
        self.verbose = verbose
        self.app_settings = app_settings
        self.kwargs = kwargs
        self.worker_id = worker_id or str(id(self))

        self.signals = CHDManSignals()
        self.process: Optional[QProcess] = None
        self.cancelled = False
        # Use DebugLogger for consistent logging
        # self.logger = logging.getLogger(__name__ + ".CHDManWorker")

        logger = (
            get_logger(self.app_settings, module_name="CHDManWorker")
            if self.app_settings
            else debug_logger
        )
        if logger:
            logger.info(
                "core.chdmanworker",
                f"__init__ for worker {self.worker_id}: command={self.command}, "
                f"input={self.input_file}, output={self.output_file}",
            )

    @staticmethod
    def _sanitize_compression_algorithms(
        compression_input: Optional[str],
    ) -> Optional[str]:
        """Validates and sanitizes compression algorithm string(s)."""
        if not compression_input:
            return None

        processed_algorithms = []
        # Use debug_logger for static method warnings

        for algo_name_iter in compression_input.split(","):
            original_algo_name = algo_name_iter.strip()
            algo_name = original_algo_name.lower()

            if algo_name in CHDManWorker.COMPRESSION_CORRECTIONS:
                corrected_name = CHDManWorker.COMPRESSION_CORRECTIONS[algo_name]
                logger = (
                    get_logger(None, module_name="CHDManWorker")
                    if None
                    else debug_logger
                )
                if logger:
                    logger.warning(
                        "core.chdmanworker",
                        f"Correcting compression algorithm '{original_algo_name}' to '",
                        f"{corrected_name}'.",
                    )
                algo_name = corrected_name

            if algo_name not in CHDManWorker.VALID_COMPRESSION_ALGORITHMS:
                valid_options_str = ", ".join(CHDManWorker.VALID_COMPRESSION_ALGORITHMS)
                raise ValueError(
                    f"Invalid compression algorithm: '{original_algo_name}'. "
                    f"Valid options are: {valid_options_str}"
                )
            processed_algorithms.append(algo_name)

        return ",".join(processed_algorithms)

    def _perform_pre_flight_checks(self) -> None:
        logger = (
            get_logger(self.app_settings, module_name="CHDManWorker")
            if self.app_settings
            else debug_logger
        )
        if logger:
            logger.debug(
                "core.chdmanworker",
                f"Worker {self.worker_id}: Performing pre-flight checks...",
            )
        # 1. CHDMAN executable
        if shutil.which(self.executable_path) is None:
            raise CHDManExecutableNotFoundError(
                f"Cannot find '{self.executable_path}' in PATH."
            )
        # 2. Input file existence and readability
        if not self.input_file or not self.input_file.exists():
            raise CHDManInputFileError(f"Input file not found: {self.input_file}")
        if not self.input_file.is_file():
            raise CHDManInputFileError(f"Input path is not a file: {self.input_file}")
        if not os.access(str(self.input_file), os.R_OK):
            raise CHDManInputFileError(f"Input file is not readable: {self.input_file}")
        # Extension validation (basic, can be extended per command)
        valid_exts = {
            ".cue",
            ".iso",
            ".bin",
            ".img",
            ".chd",
            ".gz",
            ".zip",
            ".raw",
            ".cdr",
        }
        ext = self.input_file.suffix.lower()
        if ext and ext not in valid_exts:
            if logger:
                logger.warning(
                    "core.chdmanworker",
                    f"Input file extension '{ext}' is not a common disk image type.",
                )

        # 3. Output file and directory
        if self.output_file:
            output_dir = self.output_file.parent
            if output_dir:
                if not output_dir.exists():
                    try:
                        output_dir.mkdir(parents=True, exist_ok=True)
                    except OSError as e:
                        raise CHDManOutputFileError(
                            f"Cannot create output dir: {output_dir}. {e}"
                        ) from e
                if not output_dir.is_dir():
                    raise CHDManOutputFileError(
                        f"Output directory is not a directory: {output_dir}"
                    )
                if not os.access(str(output_dir), os.W_OK):
                    raise CHDManOutputFileError(
                        f"No write permission for output dir: {output_dir}"
                    )
                # Test write
                test_file = output_dir / f".test_write_{int(time.time())}"
                try:
                    with open(test_file, "w") as f:
                        f.write("test")
                    test_file.unlink()
                except (OSError, PermissionError) as e:
                    raise CHDManOutputFileError(
                        f"Cannot write to output dir: {output_dir}. {e}"
                    ) from e
            # Output file overwrite rules
            if self.output_file.exists():
                if self.force:
                    try:
                        self.output_file.unlink()
                        if logger:
                            logger.info(
                                "core.chdmanworker",
                                f"Worker {self.worker_id}: Removed existing output: "
                                f"{self.output_file} (force).",
                            )
                    except (OSError, PermissionError) as e:
                        raise CHDManOutputFileError(
                            f"Cannot remove existing output file: {self.output_file}. "
                            f"{e}"
                        ) from e
                else:
                    raise CHDManOutputFileError(
                        f"Output file already exists: {self.output_file}. "
                        f"Use force to overwrite."
                    )

        # 4. Parameter sanity
        if self.hunk_size is not None:
            try:
                hunk = int(self.hunk_size)
                if hunk <= 0:
                    raise ValueError
            except Exception as e:
                raise CHDManError(f"Invalid hunk size: {self.hunk_size}") from e
        # Compression is validated in _sanitize_compression_algorithms
        # 5. Additional kwargs
        for key, value in self.kwargs.items():
            if isinstance(value, str) and not value.strip():
                raise CHDManError(f"Parameter '{key}' is an empty string.")
        if logger:
            logger.debug(
                "core.chdmanworker",
                f"Worker {self.worker_id}: Pre-flight checks passed.",
            )

    def _build_chdman_command(self) -> List[str]:
        logger = (
            get_logger(self.app_settings, module_name="CHDManWorker")
            if self.app_settings
            else debug_logger
        )
        if logger:
            logger.debug(
                "core.chdmanworker",
                f"Worker {self.worker_id}: Building CHDMAN command...",
            )
        cmd: List[str] = [
            self.executable_path,
            self.command,
            "-i",
            str(self.input_file),
        ]
        if self.output_file:
            cmd.extend(["-o", str(self.output_file)])

        if self.compression:
            try:
                validated_compression_str = (
                    CHDManWorker._sanitize_compression_algorithms(self.compression)
                )
                if validated_compression_str:
                    cmd.extend(["-c", validated_compression_str])
                    if logger:
                        logger.info(
                            "core.chdmanworker",
                            f"Worker {self.worker_id}: Using sanitized compression "
                            f"algorithms: {validated_compression_str}",
                        )
            except ValueError as e:
                if logger:
                    logger.error(
                        "core.chdmanworker",
                        f"Worker {self.worker_id}: Compression algorithm validation "
                        f"failed: {e}",
                    )
                raise CHDManError(
                    f"Compression algorithm validation failed: {e}"
                ) from e

        if self.hunk_size:
            cmd.extend(["-hs", str(self.hunk_size)])
        if self.force:
            cmd.append("-f")
        if self.verbose and self.command in ["info", "verify"]:
            cmd.append("-v")
        for key, value in self.kwargs.items():
            if value is not None:
                cmd.extend([f"-{key}", str(value)])

        cmd_str_for_log = " ".join(
            [str(f'"{arg}"' if " " in str(arg) else str(arg)) for arg in cmd]
        )
        print(
            f"DEBUG: CHDMAN command built: {cmd_str_for_log}"
        )  # Temporary debug print
        if logger:
            logger.debug(
                "core.chdmanworker",
                f"Worker {self.worker_id}: CHDMAN command built: {cmd_str_for_log}",
            )
        return cmd

    def _execute_with_qprocess(
        self, cmd_list: List[str], cmd_str_for_signal_and_error: str
    ):
        # Explicitly reference the imported QProcess from PySide6.QtCore
        from PySide6.QtCore import QProcess

        self.process = QProcess()
        self._all_output: List[str] = []
        self._progress_percent = 0.0
        self._progress_start_time = time.time()
        self._last_progress_percent = 0.0
        self._eta_seconds = None

        def handle_stdout():
            while self.process.canReadLine():
                line = (
                    bytes(self.process.readLine())
                    .decode("utf-8", errors="replace")
                    .strip()
                )
                self._all_output.append(line)
                if line.startswith("Progress:"):
                    import re

                    match = re.search(r"Progress:\s+(\d+)%", line)
                    if match:
                        self._progress_percent = float(match.group(1))
                        now = time.time()
                        # Estimate ETA if progress is advancing
                        if self._progress_percent > self._last_progress_percent:
                            elapsed = now - self._progress_start_time
                            if self._progress_percent > 0:
                                total_est = elapsed / (self._progress_percent / 100.0)
                                self._eta_seconds = max(0, total_est - elapsed)
                            else:
                                self._eta_seconds = None
                            self._last_progress_percent = self._progress_percent
                        eta_str = (
                            f" | ETA: {int(self._eta_seconds)}s"
                            if self._eta_seconds is not None
                            else ""
                        )
                        msg = f"{self._progress_percent:.1f}% complete{eta_str}"
                        self.signals.progress.emit(self._progress_percent, msg)

        def handle_stderr():
            while self.process.canReadLineStandardError():
                line = (
                    bytes(self.process.readLineStandardError())
                    .decode("utf-8", errors="replace")
                    .strip()
                )
                self._all_output.append(line)
                self.signals.progress.emit(-1.0, f"ERROR: {line}")
                logger = (
                    get_logger(self.app_settings, module_name="CHDManWorker")
                    if self.app_settings
                    else debug_logger
                )
                if logger:
                    logger.debug(
                        "core.chdmanworker", f"Worker {self.worker_id}: STDERR: {line}"
                    )

        def handle_finished(exit_code, exit_status):
            logger = (
                get_logger(self.app_settings, module_name="CHDManWorker")
                if self.app_settings
                else debug_logger
            )
            output_str = "\n".join(filter(None, self._all_output))

            if self.cancelled:
                if logger:
                    logger.info(
                        "core.chdmanworker",
                        f"Worker {self.worker_id}: Operation was cancelled. Emitting error.",
                    )
                if not self.signals.error.isBlocked():
                    self.signals.error.emit("Operation cancelled by user")
                return

            # Logic from _handle_process_completion
            is_usage_message = "Usage:" in output_str
            is_non_error_rc1 = (
                exit_code == 1
                and is_usage_message
                and not any(
                    kw in output_str.lower()
                    for kw in ["error:", "failed", "cannot open"]
                )
            )

            if exit_code == 0 or is_non_error_rc1:
                if logger:
                    logger.info(
                        "core.chdmanworker",
                        f"Worker {self.worker_id}: Success for "
                        f"'{cmd_str_for_signal_and_error}'.",
                    )
                self.signals.progress.emit(100.0, "Operation completed successfully")
                self.signals.finished.emit(True, "Operation completed successfully")
            else:
                error_message = (
                    f"CHDMAN command '{cmd_str_for_signal_and_error}' "
                    f"failed (code {exit_code})"
                )
                if output_str:
                    error_message += f":\n{output_str}"

                # Specific error details from _handle_process_completion
                if (
                    "Permission denied" in output_str
                    or "Access is denied" in output_str.lower()
                ):
                    if self.output_file:
                        error_message += (
                            "\n\nPermission error: Write to "
                            f"{os.path.dirname(self.output_file)} denied."
                        )
                elif (
                    "No such file or directory" in output_str
                    or "cannot open" in output_str.lower()
                ):
                    error_message += (
                        "\n\nInput file error: File not found or inaccessible."
                    )

                if logger:
                    logger.error(
                        "core.chdmanworker", f"Worker {self.worker_id}: {error_message}"
                    )
                if not self.signals.error.isBlocked():
                    self.signals.error.emit(error_message)

        # Check for None before connecting signals
        # Only connect signals if self.process is a QProcess (not Popen)
        from PySide6.QtCore import QProcess

        if self.process is not None and isinstance(self.process, QProcess):
            self.process.readyReadStandardOutput.connect(handle_stdout)
            self.process.readyReadStandardError.connect(handle_stderr)
            self.process.finished.connect(handle_finished)
            self.process.start(cmd_list[0], cmd_list[1:])
        # Note: QProcess runs asynchronously; run() will return immediately.
        # The signals will be emitted as the process runs and finishes.

    def cancel(self):
        self.cancelled = True
        logger = (
            get_logger(self.app_settings, module_name="CHDManWorker")
            if self.app_settings
            else debug_logger
        )
        if logger:
            logger.info(
                "core.chdmanworker",
                f"Worker {self.worker_id}: Marked for cancellation: "
                f"{self.command} on {self.input_file}.",
            )
        # Terminate QProcess if it's running
        if (
            self.process
            and isinstance(self.process, QProcess)
            and self.process.state() != QProcess.ProcessState.NotRunning
        ):
            if logger:
                logger.info(
                    "core.chdmanworker",
                    f"Worker {self.worker_id}: Terminating QProcess PID {self.process.processId()}",
                )
            self.process.terminate()
            # Optionally, wait for a bit and then kill if still running
            # if not self.process.waitForFinished(1000): # 1 second timeout
            #     logger.warning(
            #         "core.chdmanworker",
            #         f"Worker {self.worker_id}: QProcess did not terminate, killing."
            #     )
            #     self.process.kill()

    def _parse_progress(self, line: str) -> Optional[float]:
        if not line or not line.strip():
            return None
        logger = (
            get_logger(self.app_settings, module_name="CHDManWorker")
            if self.app_settings
            else debug_logger
        )
        if logger:
            logger.debug(
                "core.chdmanworker",
                f"Worker {self.worker_id}: Parsing progress: {line}",
            )
        match = re.search(r"(\d+(\.\d+)?)% complete", line)
        if match:
            return float(match.group(1))
        match = re.search(r"\((\d+)%\)", line)
        if match:
            return float(match.group(1))
        match = re.search(r"Block (\d+)/(\d+)", line)
        if match:
            current, total = int(match.group(1)), int(match.group(2))
            return (current / total) * 100 if total > 0 else 0.0
        match = re.search(r"sector (\d+)/(\d+)", line, re.IGNORECASE)
        if match:
            current, total = int(match.group(1)), int(match.group(2))
            return (current / total) * 100 if total > 0 else 0.0
        match = re.search(r"track (\d+)/(\d+)", line, re.IGNORECASE)
        if match:
            current, total = int(match.group(1)), int(match.group(2))
            return (current / total) * 100 if total > 0 else 0.0
        if "processing" in line.lower() or "compressing" in line.lower():
            return 1.0
        if line.startswith("Input") or line.startswith("Output"):
            return 0.0
        return None


class CHDMan(QObject):  # Ensure QObject inheritance or manage signals appropriately
    COMMANDS = {
        "createcd": CHDManCommand(
            "createcd", "Create CHD from CD image", True, True, True
        ),
        "createdvd": CHDManCommand(
            "createdvd", "Create CHD from DVD image", True, True, True
        ),
        "createhd": CHDManCommand(
            "createhd", "Create CHD from hard disk image", True, True, True
        ),
        "createld": CHDManCommand(  # Added if missing, ensure it's in COMMANDS
            "createld", "Create CHD from laserdisc image", True, True, True
        ),
        "extractcd": CHDManCommand(
            "extractcd", "Extract CD image from CHD", True, True, False
        ),
        "extractdvd": CHDManCommand(
            "extractdvd", "Extract DVD image from CHD", True, True, False
        ),
        "extracthd": CHDManCommand(
            "extracthd", "Extract hard disk image from CHD", True, True, False
        ),
        "extractld": CHDManCommand(  # Added if missing, ensure it's in COMMANDS
            "extractld", "Extract laserdisc image from CHD", True, True, False
        ),
        "extractraw": CHDManCommand(
            "extractraw", "Extract raw data from CHD", True, True, False
        ),
        "info": CHDManCommand(
            "info", "Display information about a CHD", True, False, False
        ),
        "verify": CHDManCommand("verify", "Verify CHD integrity", True, False, False),
    }

    def __init__(
        self,
        executable_path: Optional[str] = None,
        verbose: bool = False,
        app_settings: Any = None,
    ):
        super().__init__()
        self.app_settings = app_settings
        self.logger = (
            get_logger(self.app_settings, module_name="CHDMan")
            if self.app_settings
            else None
        )

        if executable_path is None or executable_path.strip() == "":
            persisted_path = load_chdman_path()
            self.executable_path = persisted_path if persisted_path else "chdman"
        else:
            self.executable_path = executable_path
        self.verbose = verbose
        self.thread_pool = QThreadPool()
        self.active_workers: Dict[str, CHDManWorker] = {}  # Should be managed by CHDMan
        self._workers_lock = threading.Lock()
        # Use DebugLogger for consistent logging
        # self.logger = logging.getLogger(__name__ + ".CHDMan")
        if self.logger:
            self.logger.info(
                "core.chdman",
                f"Initialized with executable_path: {self.executable_path}, "
                f"verbose: {self.verbose}",
            )
        else:
            debug_logger.info(
                "core.chdman",
                f"Initialized with executable_path: {self.executable_path}, "
                f"verbose: {self.verbose}",
            )

    def _create_and_start_worker(
        self,
        command: str,
        input_file: str,
        output_file: Optional[str] = None,
        compression: Optional[str] = None,
        hunk_size: Optional[int] = None,
        force: bool = False,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        # Construct a unique ID for the worker to prevent duplicates.
        # The suffix helps differentiate if the same core task is called
        # with slight variations or for specific tracking purposes.
        worker_id_parts = [command, input_file or "no_input"]
        if output_file:
            worker_id_parts.append(output_file)
        if worker_id_suffix:
            worker_id_parts.append(worker_id_suffix)

        # Use a hash of the parts for a cleaner ID, or join them carefully
        # For simplicity here, joining. Consider hashing for very long paths.
        worker_id = "-".join(worker_id_parts)

        with self._workers_lock:
            if worker_id in self.active_workers:
                debug_logger.info(
                    "core.chdmanworker",
                    f"Reusing existing worker {worker_id} for command: {command}",
                )
                return self.active_workers[worker_id].signals, self.active_workers[
                    worker_id
                ]

            worker = CHDManWorker(
                executable_path=self.executable_path,
                command=command,
                input_file=input_file,
                output_file=output_file,
                compression=compression,
                hunk_size=hunk_size,
                force=force,
                verbose=self.verbose,
                app_settings=self.app_settings,
                worker_id=worker_id,
            )

            # Connect signals using functools.partial to pass worker_id
            on_finished_partial = functools.partial(
                self._on_worker_finished, worker_id=worker_id
            )
            worker.signals.finished.connect(on_finished_partial)

            on_error_partial = functools.partial(
                self._on_worker_error, worker_id=worker_id
            )
            worker.signals.error.connect(on_error_partial)

            self.active_workers[worker_id] = worker
            self.thread_pool.start(worker)
            debug_logger.info(
                "core.chdmanworker",
                f"Started new worker {worker_id} for command: {command}",
            )
            return worker.signals, worker

    # Add new private slots for worker signals here, before other private methods
    def _on_worker_finished(self, success: bool, msg: str, worker_id: str):
        """Slot to handle worker finished signal, removing the worker."""
        # success and msg are parameters from the finished signal, can be used if needed
        debug_logger.debug(
            "core.chdmanworker",
            f"CHDMan: Worker {worker_id} finished. Success: {success}, Msg: {msg}",
        )
        self._remove_worker_by_id(worker_id)

    def _on_worker_error(self, error_msg: str, worker_id: str):
        """Slot to handle worker error signal."""
        debug_logger.error(
            "core.chdmanworker",
            f"CHDMan: Worker {worker_id} reported an error: {error_msg}",
        )
        self._handle_worker_error(worker_id, error_msg)

    def _remove_worker_by_id(self, worker_id: str):
        with self._workers_lock:  # Use the lock here
            if worker_id in self.active_workers:
                del self.active_workers[worker_id]
                debug_logger.info(
                    "core.chdmanworker", f"Removed worker {worker_id} from active list."
                )
            else:
                debug_logger.warning(
                    "core.chdmanworker",
                    f"Attempted to remove non-existent worker_id: {worker_id}",
                )

    def _handle_worker_error(self, worker_id: str, error_message: str):
        debug_logger.error("core.chdmanworker", f"Worker {worker_id}: {error_message}")
        self.signals.error.emit(error_message)

    def terminate_all_chdman_processes(self):
        with self._workers_lock:
            for worker_id, worker in list(self.active_workers.items()):  # Iterate copy
                debug_logger.info(
                    "core.chdmanworker", f"Terminating worker {worker_id}"
                )
                if worker.process and worker.process.poll() is None:
                    try:
                        worker.process.terminate()
                        worker.process.wait(timeout=5)  # Wait for graceful termination
                    except subprocess.TimeoutExpired:
                        worker.process.kill()  # Force kill if terminate fails
                    except Exception as e:
                        debug_logger.error(
                            "core.chdmanworker",
                            f"Error terminating worker {worker_id}: {e}",
                        )
                self._remove_worker_by_id(worker_id)  # Ensure worker is removed

    def cleanup(self):
        self.terminate_all_chdman_processes()
        self.thread_pool.waitForDone()

    def create_cd(
        self,
        input_file: str,
        output_file: str,
        compression: Optional[str] = None,
        hunk_size: Optional[int] = None,
        force: bool = False,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        return self._create_and_start_worker(
            "createcd",
            input_file,
            output_file,
            compression,
            hunk_size,
            force,
            worker_id_suffix=worker_id_suffix,
        )

    def create_dvd(
        self,
        input_file: str,
        output_file: str,
        compression: Optional[str] = None,
        hunk_size: Optional[int] = None,
        force: bool = False,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        return self._create_and_start_worker(
            "createdvd",
            input_file,
            output_file,
            compression,
            hunk_size,
            force,
            worker_id_suffix=worker_id_suffix,
        )

    def create_hd(
        self,
        input_file: str,
        output_file: str,
        compression: Optional[str] = None,
        hunk_size: Optional[int] = None,
        force: bool = False,
        input_size: Optional[int] = None,  # Specific to createhd
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        kwargs = {}
        if input_size is not None:
            kwargs["inputbytes"] = input_size  # CHDMAN uses --inputbytes
        return self._create_and_start_worker(
            "createhd",
            input_file,
            output_file,
            compression,
            hunk_size,
            force,
            worker_id_suffix=worker_id_suffix,
            **kwargs,
        )

    def createld(
        self,
        input_file: str,
        output_file: str,
        compression: Optional[str] = None,
        hunk_size: Optional[int] = None,
        force: bool = False,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        return self._create_and_start_worker(
            "createld",
            input_file,
            output_file,
            compression,
            hunk_size,
            force,
            worker_id_suffix=worker_id_suffix,
        )

    def extract_cd(
        self,
        input_file: str,
        output_file: str,
        force: bool = False,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        return self._create_and_start_worker(
            "extractcd",
            input_file,
            output_file,
            force=force,
            worker_id_suffix=worker_id_suffix,
        )

    def extract_dvd(
        self,
        input_file: str,
        output_file: str,
        force: bool = False,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        return self._create_and_start_worker(
            "extractdvd",
            input_file,
            output_file,
            force=force,
            worker_id_suffix=worker_id_suffix,
        )

    def extract_hd(
        self,
        input_file: str,
        output_file: str,
        force: bool = False,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        return self._create_and_start_worker(
            "extracthd",
            input_file,
            output_file,
            force=force,
            worker_id_suffix=worker_id_suffix,
        )

    def extract_ld(
        self,
        input_file: str,
        output_file: str,
        force: bool = False,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        return self._create_and_start_worker(
            "extractld",
            input_file,
            output_file,
            force=force,
            worker_id_suffix=worker_id_suffix,
        )

    def extract_raw(
        self,
        input_file: str,
        output_file: str,
        force: bool = False,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        return self._create_and_start_worker(
            "extractraw",
            input_file,
            output_file,
            force=force,
            worker_id_suffix=worker_id_suffix,
        )

    def info(
        self,
        input_file: str,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        return self._create_and_start_worker(
            "info",
            input_file,
            worker_id_suffix=worker_id_suffix,
        )

    def verify(
        self,
        input_file: str,
        worker_id_suffix: Optional[str] = None,
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        return self._create_and_start_worker(
            "verify",
            input_file,
            worker_id_suffix=worker_id_suffix,
        )

    def _parse_info_output(self, output: str) -> Dict[str, Any]:
        info = {}
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 1)
            if len(parts) == 2:
                info[parts[0].strip()] = parts[1].strip()
        return info


class CHDTaskType(Enum):
    (
        COMPRESS,
        EXTRACT_RAW,
        EXTRACT_CD,
        EXTRACT_DVD,
        EXTRACT_HD,
        EXTRACT_LD,
        EXTRACT_AV,
        INFO,
        VERIFY,
        DUMP_META,
    ) = [auto() for _ in range(10)]


@dataclass
class CHDTask:
    task_type: CHDTaskType
    input_file: str
    output_file: Optional[str] = None
    compression_level: Optional[str] = (
        None  # Should be Optional[List[str]] or str based on usage
    )
    hunk_size: Optional[int] = None
    verify: bool = False
    force: bool = False
    media_type: Optional[str] = None  # e.g., 'cdrom', 'harddisk'
    algorithms: Optional[str] = None  # For createhd, specific algorithms
    user_data: Optional[Dict[str, Any]] = None  # For arbitrary data like row index
    row: Optional[int] = None  # For tracking table row in UI

    def __post_init__(self):
        if self.user_data is None:
            self.user_data = {}
        # Field compatibility: keep algorithms and compression_level in sync
        # Allow both to be set independently if needed, but default to
        # mirroring if only one is set
        if self.algorithms and not self.compression_level:
            self.compression_level = self.algorithms
        elif self.compression_level and not self.algorithms:
            self.algorithms = self.compression_level


class CHDManager(QObject):
    signals = CHDManSignals()  # For overall batch progress, if needed

    def __init__(self, executable_path: str = "chdman"):
        super().__init__()
        self.executable_path = executable_path
        # Ensure CHDMan is instantiated with the correct executable_path from CHDManager
        self.chdman = CHDMan(executable_path=self.executable_path)
        self.tasks: List[CHDTask] = []
        self.active_workers: Dict[
            str, CHDManWorker
        ] = {}  # Should be managed by CHDMan instance
        self.thread_pool = QThreadPool()  # CHDMan has its own thread_pool
        self._task_mutex = QMutex()
        # Use DebugLogger for consistent logging
        # self.logger = logging.getLogger(__name__ + ".CHDManager")
        # Patch: Add batch tracking for integration
        self._last_executed_batch: List[CHDTask] = []

    def log(self, message: str):
        debug_logger.info("core.chdmanworker", message)

    def terminate_all_chdman_processes(self):
        # Delegate to the CHDMan instance
        self.chdman.terminate_all_chdman_processes()

    def add_task(self, task: CHDTask):
        with QMutexLocker(self._task_mutex):
            self.tasks.append(task)

    def get_last_executed_tasks_batch(self) -> List[CHDTask]:
        return self._last_executed_batch

    def clear_tasks(self):
        with QMutexLocker(self._task_mutex):
            self.tasks.clear()

    def has_pending_tasks(self) -> bool:
        """Check if there are any tasks pending in the queue."""
        with QMutexLocker(self._task_mutex):
            return bool(self.tasks)

    def start_processing(self) -> List[Tuple[CHDManSignals, CHDManWorker]]:
        with QMutexLocker(self._task_mutex):
            if not self.tasks:
                debug_logger.info("core.chdmanworker", "No tasks to process.")
                self.signals.finished.emit(
                    True, "No tasks to process."
                )  # CHDManager's own signal
                return []

            self._last_executed_batch = list(self.tasks)  # Copy tasks
            debug_logger.info(
                "core.chdmanworker", f"Starting processing of {len(self.tasks)} tasks."
            )
            workers_signals = []
            for task in self.tasks:
                signals, worker = self.initiate_task_and_get_signals(task)
                workers_signals.append((signals, worker))
            return workers_signals

    def initiate_task_and_get_signals(
        self, task: CHDTask
    ) -> Tuple[CHDManSignals, CHDManWorker]:
        """Initiates a single CHD task and returns its signals for direct monitoring."""
        worker_suffix = str(id(task))

        if task.task_type == CHDTaskType.COMPRESS:
            if not task.media_type:
                raise ValueError("media_type is required for COMPRESS tasks.")
            if task.output_file is None:
                raise ValueError(
                    f"output_file is required for COMPRESS task: {task.media_type}"
                )

            media_type_lower = task.media_type.lower()
            if media_type_lower == "cd":
                signals, worker = self.chdman.create_cd(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    compression=task.algorithms or task.compression_level,
                    hunk_size=task.hunk_size,
                    force=task.force,
                    worker_id_suffix=worker_suffix,
                )
                worker.user_data = {"row": task.row, "file_path": task.input_file}
                return signals, worker
            elif media_type_lower == "dvd":
                signals, worker = self.chdman.create_dvd(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    compression=task.algorithms or task.compression_level,
                    hunk_size=task.hunk_size,
                    force=task.force,
                    worker_id_suffix=worker_suffix,
                )
                worker.user_data = {"row": task.row, "file_path": task.input_file}
                return signals, worker
            elif media_type_lower == "hd":
                signals, worker = self.chdman.create_hd(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    compression=task.algorithms or task.compression_level,
                    hunk_size=task.hunk_size,
                    force=task.force,
                    worker_id_suffix=worker_suffix,
                )
                worker.user_data = {"row": task.row, "file_path": task.input_file}
                return signals, worker
            elif media_type_lower == "ld":
                signals, worker = self.chdman.createld(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    compression=task.algorithms or task.compression_level,
                    hunk_size=task.hunk_size,
                    force=task.force,
                    worker_id_suffix=worker_suffix,
                )
                worker.user_data = {"row": task.row, "file_path": task.input_file}
                return signals, worker
            else:
                raise ValueError(
                    f"Unsupported media_type for COMPRESS: {task.media_type}"
                )

        elif task.task_type in [
            CHDTaskType.EXTRACT_CD,
            CHDTaskType.EXTRACT_DVD,
            CHDTaskType.EXTRACT_HD,
            CHDTaskType.EXTRACT_LD,
            CHDTaskType.EXTRACT_RAW,
        ]:
            if task.output_file is None:
                raise ValueError(
                    f"output_file is required for {task.task_type.name} task"
                )

            if task.task_type == CHDTaskType.EXTRACT_CD:
                signals, worker = self.chdman.extract_cd(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    force=task.force,
                    worker_id_suffix=worker_suffix,
                )
                worker.user_data = {"row": task.row, "file_path": task.input_file}
                return signals, worker
            elif task.task_type == CHDTaskType.EXTRACT_DVD:
                signals, worker = self.chdman.extract_dvd(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    force=task.force,
                    worker_id_suffix=worker_suffix,
                )
                worker.user_data = {"row": task.row, "file_path": task.input_file}
                return signals, worker
            elif task.task_type == CHDTaskType.EXTRACT_HD:
                signals, worker = self.chdman.extract_hd(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    force=task.force,
                    worker_id_suffix=worker_suffix,
                )
                worker.user_data = {"row": task.row, "file_path": task.input_file}
                return signals, worker
            elif task.task_type == CHDTaskType.EXTRACT_LD:
                signals, worker = self.chdman.extract_ld(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    force=task.force,
                    worker_id_suffix=worker_suffix,
                )
                worker.user_data = {"row": task.row, "file_path": task.input_file}
                return signals, worker
            elif task.task_type == CHDTaskType.EXTRACT_RAW:
                signals, worker = self.chdman.extract_raw(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    force=task.force,
                    worker_id_suffix=worker_suffix,
                )
                worker.user_data = {"row": task.row, "file_path": task.input_file}
                return signals, worker
            else:
                raise AssertionError(
                    f"Unhandled task type {task.task_type.name} in extract block."
                )

        elif task.task_type == CHDTaskType.INFO:
            if not task.input_file:
                raise ValueError("input_file is required for INFO task.")
            signals, worker = self.chdman.info(
                input_file=task.input_file, worker_id_suffix=worker_suffix
            )
            worker.user_data = {"row": task.row, "file_path": task.input_file}
            return signals, worker

        elif task.task_type == CHDTaskType.VERIFY:
            if not task.input_file:
                raise ValueError("input_file is required for VERIFY task.")
            signals, worker = self.chdman.verify(
                input_file=task.input_file, worker_id_suffix=worker_suffix
            )
            worker.user_data = {"row": task.row, "file_path": task.input_file}
            return signals, worker
        else:
            raise NotImplementedError(
                f"Task type {task.task_type.name} not implemented."
            )

    def _delegate_task_to_chdman(self, task: CHDTask):
        # This method seems to be part of an older batch processing logic.
        # initiate_task_and_get_signals offers a more direct way to get signals.
        # For full batch processing via execute_all_tasks, that method would use
        # initiate_task_and_get_signals and then connect to those signals to manage
        # overall batch progress and completion.
        debug_logger.warning(
            "core.chdmanworker",
            "_delegate_task_to_chdman is likely deprecated. "
            "Use initiate_task_and_get_signals directly.",
        )
        # However, if execute_all_tasks is to be fully functional with the old
        # signal connection model, it would need refactoring. Focus on test fix.
        self.initiate_task_and_get_signals(task)

        # Example of how one might connect signals if _delegate_task_to_chdman
        # were still primary:
        # worker_id = signals.worker_id # Assuming worker_id accessible
        # signals.finished.connect(
        #    lambda s, m: self._on_delegated_worker_finished(
        #        task, s, m, worker_id
        #    )
        # )
        # signals.error.connect(
        #    lambda e_msg: self._on_delegated_worker_error(
        #        task, e_msg, worker_id
        #    )
        # )
        # signals.progress_updated.connect(
        #    lambda p, m, wid: self.signals.progress_updated.emit(
        #        p, m, f"{task.input_file} ({wid})"
        #    )
        # )
        pass  # Pass for now, direct call in execute_all_tasks for simplicity

    def _on_delegated_worker_finished(
        self, task: CHDTask, success: bool, message: str, worker_id: str
    ):
        debug_logger.info(
            "core.chdmanworker",
            f"Delegated worker {worker_id} for task {task.input_file} "
            f"finished. Success: {success}. Msg: {message}",
        )
        self.signals.task_completed.emit(task.input_file, success, message)

    def _on_delegated_worker_error(
        self, task: CHDTask, error_message: str, worker_id: str
    ):
        debug_logger.error(
            "core.chdmanworker",
            f"Delegated worker {worker_id} for task {task.input_file} "
            f"error: {error_message}",
        )
        self.signals.task_completed.emit(task.input_file, False, error_message)

    def find_chdman(self) -> str:
        return self.chdman.executable_path

    def get_chdman_version(
        self, executable_path: Optional[str] = None
    ) -> Optional[str]:
        # If CHDMan does not have get_chdman_version, return None or raise
        if hasattr(self.chdman, "get_chdman_version"):
            version = self.chdman.get_chdman_version(
                executable_path or getattr(self.chdman, "executable_path", None)
            )
            if isinstance(version, str) or version is None:
                return version
            return str(version)
        return None

    def get_active_tasks_count(self) -> int:
        return len(self.chdman.active_workers)

    def cleanup(self):
        debug_logger.info(
            "core.chdmanworker",
            "CHDManager cleanup initiated. Delegating to CHDMan instance.",
        )
        self.chdman.cleanup()
        with QMutexLocker(self._task_mutex):
            self.tasks.clear()
        debug_logger.info("core.chdmanworker", "CHDManager cleanup finished.")


_chd_manager_singleton = None
_singleton_lock = threading.Lock()


def get_chd_manager():
    global _chd_manager_singleton
    if _chd_manager_singleton is None:
        with _singleton_lock:
            if _chd_manager_singleton is None:
                chdman_path = load_chdman_path()
                if not chdman_path:
                    chdman_path = "chdman"

                if not logging.getLogger().hasHandlers():
                    logging.basicConfig(
                        level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    )
                _chd_manager_singleton = CHDManager(executable_path=chdman_path)
    return _chd_manager_singleton
