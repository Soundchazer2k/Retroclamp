"""CHDMAN wrapper module for RetroClamp.

This module provides a Pythonic interface to the CHDMAN command-line utility,
allowing for compression, extraction, verification, and information retrieval
operations on CHD files with proper progress reporting and error handling.
"""

import os
import re
import subprocess
from datetime import datetime
import time
from enum import Enum, auto
from typing import Dict, Optional, Any, List 
from dataclasses import dataclass
import logging
import shutil 
import queue 
import threading # Ensure threading is imported for locks

from modules.settings import load_chdman_path
from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool, QMutex, QMutexLocker

class CHDCompressionType(Enum):
    """Available compression types for CHD files."""
    ZLIB = 'zlib'
    ZLIB_HUFF = 'zlib_huff'
    LZMA = 'lzma'
    SDX = 'sdx'
    AUTO = 'auto'

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
        'none', 'zlib', 'zstd', 'lzma', 'huff', 'flac', 
        'cdlz', 'cdzl', 'cdfl', 'avhu'
    ]
    COMPRESSION_CORRECTIONS = {'cdzlib': 'cdzl', 'cdflac': 'cdfl'}

    def __init__(self, 
                 executable_path: str,
                 command: str, 
                 input_file: str, 
                 output_file: Optional[str] = None,
                 compression: Optional[str] = None,
                 hunk_size: Optional[int] = None,
                 force: bool = False,
                 verbose: bool = True,
                 worker_id: Optional[str] = None,
                 **kwargs):
        super().__init__()
        self.executable_path = executable_path
        self.command = command
        self.input_file = input_file
        self.output_file = output_file
        self.compression = compression
        self.hunk_size = hunk_size
        self.force = force
        self.verbose = verbose 
        self.kwargs = kwargs
        self.worker_id = worker_id or str(id(self))
        
        self.signals = CHDManSignals()
        self.process: Optional[subprocess.Popen] = None
        self.cancelled = False
        self.logger = logging.getLogger(__name__ + '.CHDManWorker')
        
        self.logger.info(
            f'__init__ for worker {self.worker_id}: command={self.command}, '
            f'input={self.input_file}, output={self.output_file}'
        )

    @staticmethod
    def _sanitize_compression_algorithms(compression_input: Optional[str]) -> Optional[str]:
        """Validates and sanitizes compression algorithm string(s)."""
        if not compression_input:
            return None

        processed_algorithms = []
        static_logger = logging.getLogger(__name__ + '.CHDManWorker._sanitize_compression_algorithms')

        for algo_name_iter in compression_input.split(','):
            original_algo_name = algo_name_iter.strip()
            algo_name = original_algo_name.lower()

            if algo_name in CHDManWorker.COMPRESSION_CORRECTIONS:
                corrected_name = CHDManWorker.COMPRESSION_CORRECTIONS[algo_name]
                static_logger.warning(
                    f"Correcting compression algorithm '{original_algo_name}' to '{corrected_name}'."
                )
                algo_name = corrected_name
            
            if algo_name not in CHDManWorker.VALID_COMPRESSION_ALGORITHMS:
                valid_options_str = ', '.join(CHDManWorker.VALID_COMPRESSION_ALGORITHMS)
                raise ValueError(
                    f"Invalid compression algorithm: '{original_algo_name}'. "
                    f"Valid options are: {valid_options_str}"
                )
            processed_algorithms.append(algo_name)
        
        return ','.join(processed_algorithms)

    def _perform_pre_flight_checks(self) -> None:
        self.logger.debug(f'Worker {self.worker_id}: Performing pre-flight checks...')
        if shutil.which(self.executable_path) is None:
            raise CHDManExecutableNotFoundError(f"Cannot find '{self.executable_path}' in PATH.")
        if not os.path.exists(self.input_file):
            raise CHDManInputFileError(f'Input file not found: {self.input_file}')
        if self.output_file:
            if os.path.exists(self.output_file) and self.force:
                try:
                    os.remove(self.output_file)
                    self.logger.info(
                        f'Worker {self.worker_id}: Removed existing output: '
                        f'{self.output_file} (force).'
                    )
                except (OSError, PermissionError) as e:
                    self.logger.warning(f'Worker {self.worker_id}: Could not remove {self.output_file}: {e}')
            output_dir = os.path.dirname(self.output_file)
            if output_dir:
                if not os.path.exists(output_dir):
                    try: 
                        os.makedirs(output_dir, exist_ok=True)
                    except OSError as e: 
                        raise CHDManOutputFileError(f'Cannot create output dir: {output_dir}. {e}')
                if not os.access(output_dir, os.W_OK):
                    raise CHDManOutputFileError(f'No write permission for output dir: {output_dir}')
                # Use global time import
                test_file = os.path.join(output_dir, f'.test_write_{int(time.time())}')
                try:
                    with open(test_file, 'w') as f: 
                        f.write('test')
                    os.remove(test_file)
                except (OSError, PermissionError) as e:
                    raise CHDManOutputFileError(f'Cannot write to output dir: {output_dir}. {e}')
        self.logger.debug(f'Worker {self.worker_id}: Pre-flight checks passed.')

    def _build_chdman_command(self) -> List[str]:
        self.logger.debug(f'Worker {self.worker_id}: Building CHDMAN command...')
        cmd = [self.executable_path, self.command, '-i', self.input_file]
        if self.output_file: 
            cmd.extend(['-o', self.output_file])

        if self.compression:
            try:
                validated_compression_str = CHDManWorker._sanitize_compression_algorithms(self.compression)
                if validated_compression_str:
                    cmd.extend(['-c', validated_compression_str])
                    self.logger.info(
                        f'Worker {self.worker_id}: Using sanitized compression '
                        f'algorithms: {validated_compression_str}'
                    )
            except ValueError as e: 
                self.logger.error(f'Worker {self.worker_id}: Compression algorithm validation failed: {e}')
                raise CHDManError(f'Compression algorithm validation failed: {e}')


        if self.hunk_size: 
            cmd.extend(['-hs', str(self.hunk_size)])
        if self.force: 
            cmd.append('-f')
        if self.verbose and self.command in ['info', 'verify']: 
            cmd.append('-v')
        for key, value in self.kwargs.items():
            if value is not None: 
                cmd.extend([f'-{key}', str(value)])
        
        cmd_str_for_log = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd])
        self.logger.debug(f'Worker {self.worker_id}: CHDMAN command built: {cmd_str_for_log}')
        return cmd

    def _execute_and_monitor_process(self, cmd: List[str]) -> tuple[int, List[str]]:
        cmd_str_for_logging = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd])
        self.logger.debug(f'Worker {self.worker_id}: === CHDMAN DETAILED INFORMATION ===')
        self.logger.debug(f'Worker {self.worker_id}: Command: {cmd_str_for_logging}')
        self.logger.debug(f'Worker {self.worker_id}: Executable: {self.executable_path}')
        self.logger.debug(f'Worker {self.worker_id}: ==================================')
        self.logger.info(f'Worker {self.worker_id}: CHDMAN COMMAND: {cmd_str_for_logging}')
        
        all_output: List[str] = []
        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
            text=True, bufsize=1, universal_newlines=True
        )
        self.logger.info(f'Worker {self.worker_id}: CHDMAN process started with PID: {self.process.pid}')
        self.signals.progress.emit(0.0, f'Started CHDMAN process (PID: {self.process.pid})')

        stdout_queue: queue.Queue[Optional[str]] = queue.Queue()
        stderr_queue: queue.Queue[Optional[str]] = queue.Queue()
        last_progress_time = time.time()
        last_progress_value = 0.0

        def read_stream_local(stream, output_queue: queue.Queue[Optional[str]], worker_self: CHDManWorker):
            try:
                for line_bytes in iter(stream.readline, b'' if hasattr(stream, 'mode') and 'b' in stream.mode else ''):
                    if line_bytes:
                        try:
                            line_str = line_bytes.decode('utf-8', errors='replace').strip() if isinstance(line_bytes, bytes) else str(line_bytes).strip()
                            if line_str: 
                                output_queue.put(line_str)
                        except Exception as e:
                            worker_self.logger.error(f'Error processing line: {line_bytes!r} - {e}', exc_info=True)
                            try: 
                                output_queue.put(str(line_bytes)) 
                            except Exception: 
                                pass # Should not fail with str()
            except Exception as e: 
                worker_self.logger.error(f'Error reading from stream: {e}', exc_info=True)
            finally: 
                output_queue.put(None)

        stdout_thread = threading.Thread(target=read_stream_local, args=(self.process.stdout, stdout_queue, self))
        stderr_thread = threading.Thread(target=read_stream_local, args=(self.process.stderr, stderr_queue, self))
        stdout_thread.daemon = True # Corrected: daemon assignment on separate lines
        stderr_thread.daemon = True
        stdout_thread.start() 
        stderr_thread.start() # Corrected: start calls on separate lines

        stdout_done, stderr_done = False, False
        while self.process.poll() is None or not (stdout_done and stderr_done):
            if self.cancelled:
                self.logger.info(f'Worker {self.worker_id}: Cancellation for PID {self.process.pid}, terminating...')
                try:
                    self.process.terminate()
                    time.sleep(0.1) 
                    Popen_poll = self.process.poll() 
                    if Popen_poll is None: 
                        time.sleep(0.4)
                        Popen_poll = self.process.poll()
                    if Popen_poll is None: 
                        self.process.kill()
                except Exception as e: 
                    self.logger.error(f'Worker {self.worker_id}: Error terminating: {e}', exc_info=True)
                self.signals.error.emit('Operation cancelled by user')
                stdout_thread.join(timeout=1.0)
                stderr_thread.join(timeout=1.0)
                return -1, all_output 
            try:
                line = stdout_queue.get(block=True, timeout=0.05)
                if line is None: 
                    stdout_done = True
                else:
                    all_output.append(line)
                    progress = self._parse_progress(line)
                    if progress is not None:
                        last_progress_value, last_progress_time = progress, time.time()
                        self.signals.progress.emit(progress, line)
                    elif line: 
                        self.signals.progress.emit(-1.0, line)
                        if not line.startswith('Processing:'): 
                            self.logger.debug(f'Worker {self.worker_id}: STDOUT: {line}')
            except queue.Empty: 
                pass
            try:
                line = stderr_queue.get(block=True, timeout=0.05)
                if line is None: 
                    stderr_done = True
                else:
                    all_output.append(line) 
                    if 'Compressing' in line or 'complete' in line or 'ratio=' in line: 
                        self.signals.progress.emit(-1.0, line) 
                    else: 
                        self.signals.progress.emit(-1.0, f'ERROR: {line}') 
                    self.logger.debug(f'Worker {self.worker_id}: STDERR: {line}')
            except queue.Empty: 
                pass
            if time.time() - last_progress_time > 2 and not self.cancelled:
                self.signals.progress.emit(last_progress_value, 'Processing... (still working)')
                last_progress_time = time.time()
        stdout_thread.join(timeout=1.0)
        stderr_thread.join(timeout=1.0)
        try:
            while True: 
                line = stdout_queue.get_nowait()
                if line is None: 
                    break
                all_output.append(line) 
                progress = self._parse_progress(line)
                self.signals.progress.emit(progress if progress is not None else -1.0, line)
                if not line.startswith('Processing:'): 
                    self.logger.debug(f'Worker {self.worker_id}: FINAL STDOUT: {line}')
        except queue.Empty: 
            pass
        except Exception as e: 
            self.logger.error(f'Worker {self.worker_id}: Error draining stdout: {e}', exc_info=True)
        try:
            while True: 
                line = stderr_queue.get_nowait()
                if line is None: 
                    break
                all_output.append(line) 
                self.signals.progress.emit(-1.0, f'ERROR: {line}')
                self.logger.debug(f'Worker {self.worker_id}: FINAL STDERR: {line}')
        except queue.Empty: 
            pass
        except Exception as e: 
            self.logger.error(f'Worker {self.worker_id}: Error draining stderr: {e}', exc_info=True)
        return_code = self.process.wait()
        self.logger.info(f'Worker {self.worker_id}: Process PID {self.process.pid} completed with code: {return_code}')
        return return_code, all_output

    def _handle_process_completion(self, return_code: int, all_output: List[str], cmd_str: str) -> None:
        if return_code == -1 and self.cancelled: 
            self.logger.info(f'Worker {self.worker_id}: Cancelled during execution. Error signal emitted from monitor.')
            return 
        if self.cancelled:
            self.logger.info(f'Worker {self.worker_id}: Completion aborted (cancelled). Emitting error.')
            if not self.signals.error.isBlocked(): 
                self.signals.error.emit('Operation cancelled by user')
            return
        output_str = '\n'.join(filter(None,all_output)) 
        is_usage_message = 'Usage:' in output_str
        is_non_error_rc1 = return_code == 1 and is_usage_message and not any(kw in output_str.lower() for kw in ['error:', 'failed', 'cannot open'])
        if return_code == 0 or is_non_error_rc1:
            self.logger.info(f"Worker {self.worker_id}: Success for '{cmd_str}'.")
            self.signals.finished.emit(True, 'Operation completed successfully')
        else:
            error_message = f"CHDMAN command '{cmd_str}' failed (code {return_code})"
            if output_str: 
                error_message += f':\n{output_str}'
            if 'Permission denied' in output_str or 'Access is denied' in output_str.lower():
                if self.output_file:
                    error_message += (f'\n\nPermission error: Write to {os.path.dirname(self.output_file)} denied.')
            elif 'No such file or directory' in output_str or 'cannot open' in output_str.lower():
                error_message += ('\n\nInput file error: File not found or inaccessible.')
            self.logger.error(f'Worker {self.worker_id}: {error_message}')
            self.signals.error.emit(error_message) 
            raise CHDManCommandError(cmd_str, return_code, output_str)

    @Slot()
    def run(self):
        if getattr(self, '_has_run', False):
            self.logger.debug(f'Worker {self.worker_id}: Already ran. Skipping.')
            return
        self._has_run = True
        cmd_list: List[str] = [] 
        cmd_str_for_signal_and_error: str = ''
        try:
            self.logger.info(f"Worker {self.worker_id}: Starting: {self.command} on {self.input_file}")
            self._perform_pre_flight_checks()
            cmd_list = self._build_chdman_command()
            cmd_str_for_signal_and_error = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd_list])
            self.signals.started.emit(f'Running: {cmd_str_for_signal_and_error}')
            return_code, all_output = self._execute_and_monitor_process(cmd_list)
            self._handle_process_completion(return_code, all_output, cmd_str_for_signal_and_error)
        except CHDManError as e: 
            self.logger.error(f"Worker {self.worker_id}: CHDManError for '{cmd_str_for_signal_and_error}': {e}", exc_info=True) 
            if not self.signals.error.isBlocked(): 
                self.signals.error.emit(str(e))
        except Exception as e: 
            self.logger.exception(f"Worker {self.worker_id}: Unexpected error for '{cmd_str_for_signal_and_error}'") 
            if not self.signals.error.isBlocked(): 
                self.signals.error.emit(f'Unexpected error: {str(e)}')
        finally:
            self.logger.info(f"Worker {self.worker_id}: Finished: {self.command} on {self.input_file}")
            
    def cancel(self):
        self.cancelled = True
        self.logger.info(f"Worker {self.worker_id}: Marked for cancellation: {self.command} on {self.input_file}.")
    
    def _parse_progress(self, line: str) -> Optional[float]:
        if not line or not line.strip(): 
            return None
        self.logger.debug(f'Worker {self.worker_id}: Parsing progress: {line}')
        match = re.search(r'(\d+(\.\d+)?)% complete', line)
        if match: 
            return float(match.group(1))
        match = re.search(r'\((\d+)%\)', line)
        if match: 
            return float(match.group(1))
        match = re.search(r'Block (\d+)/(\d+)', line)
        if match: 
            current, total = int(match.group(1)), int(match.group(2))
            return (current/total)*100 if total > 0 else 0.0
        match = re.search(r'sector (\d+)/(\d+)', line, re.IGNORECASE)
        if match: 
            current, total = int(match.group(1)), int(match.group(2))
            return (current/total)*100 if total > 0 else 0.0
        match = re.search(r'track (\d+)/(\d+)', line, re.IGNORECASE)
        if match: 
            current, total = int(match.group(1)), int(match.group(2))
            return (current/total)*100 if total > 0 else 0.0
        if 'processing' in line.lower() or 'compressing' in line.lower(): 
            return 1.0
        if line.startswith('Input') or line.startswith('Output'): 
            return 0.0
        return None

class CHDMan:
    """Wrapper for the CHDMAN command-line utility."""
    COMMANDS = {
        'createcd': CHDManCommand('createcd', 'Create CHD from CD image', True, True, True),
        'createdvd': CHDManCommand('createdvd', 'Create CHD from DVD image', True, True, True),
        'createhd': CHDManCommand('createhd', 'Create CHD from hard disk image', True, True, True),
        'createld': CHDManCommand('createld', 'Create CHD from laserdisc image', True, True, True),
        'extractcd': CHDManCommand('extractcd', 'Extract CD image from CHD', True, True, False),
        'extractdvd': CHDManCommand('extractdvd', 'Extract DVD image from CHD', True, True, False),
        'extracthd': CHDManCommand('extracthd', 'Extract hard disk image from CHD', True, True, False),
        'extractld': CHDManCommand('extractld', 'Extract laserdisc image from CHD', True, True, False),
        'extractraw': CHDManCommand('extractraw', 'Extract raw data from CHD', True, True, False),
        'info': CHDManCommand('info', 'Display information about a CHD', True, False, False),
        'verify': CHDManCommand('verify', 'Verify CHD integrity', True, False, False),
    }
    
    def __init__(self, executable_path: Optional[str] = None, verbose: bool = False):
        if executable_path is None or executable_path.strip() == '':
            persisted_path = load_chdman_path()
            self.executable_path = persisted_path if persisted_path else 'chdman'
        else:
            self.executable_path = executable_path
        self.verbose = verbose 
        self.thread_pool = QThreadPool()
        self.active_workers: Dict[str, CHDManWorker] = {}
        self._workers_lock = threading.Lock() 
        self.logger = logging.getLogger(__name__ + '.CHDMan')
        self.logger.info(f'Initialized with executable_path: {self.executable_path}, verbose: {self.verbose}')
    
    def _create_and_start_worker(
        self,
        command: str,
        input_file: str,
        output_file: Optional[str] = None,
        compression: Optional[str] = None,
        hunk_size: Optional[int] = None,
        force: bool = False,
        worker_id_suffix: Optional[str] = None,
        **kwargs 
    ) -> CHDManWorker:
        base_worker_id = worker_id_suffix or os.path.basename(input_file) 
        worker_id = f'{command}_{base_worker_id}'
        
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command=command,
            input_file=input_file,
            output_file=output_file,
            compression=compression,
            hunk_size=hunk_size,
            force=force,
            verbose=self.verbose, 
            worker_id=worker_id,
            **kwargs
        )
        
        with self._workers_lock:
            self.active_workers[worker.worker_id] = worker
        
        worker.signals.finished.connect(lambda success, msg, w_id=worker.worker_id: self._remove_worker_by_id(w_id))
        worker.signals.error.connect(lambda msg, w_id=worker.worker_id: self._remove_worker_by_id(w_id))
        
        self.thread_pool.start(worker)
        self.logger.info(f'Started worker {worker.worker_id} for command {command} on {input_file}')
        return worker

    def terminate_all_chdman_processes(self):
        self.logger.info('CHDMan: Terminating all processes...')
        with self._workers_lock: 
            workers_to_cancel = list(self.active_workers.values())
        
        for worker in workers_to_cancel:
            if worker: 
                worker.cancelled = True 
            self.logger.info(f'Marked worker {worker.worker_id} as cancelled.')
        
        try:
            cmd_args = ['taskkill', '/F', '/IM', 'chdman.exe'] if os.name == 'nt' else ['pkill', '-9', 'chdman']
            action = 'taskkill' if os.name == 'nt' else 'pkill'
            self.logger.info(f'Using {action} to terminate chdman processes')
            result = subprocess.run(cmd_args, capture_output=True, text=True, check=False)
            self.logger.debug(f'{action} result: {result.returncode}, STDOUT: {result.stdout}, STDERR: {result.stderr}')
        except Exception as e:
            self.logger.warning(f'Failed {action}: {e}', exc_info=True)
        
        self.cleanup() 
    
    def cleanup(self):
        self.logger.info('Cleaning up CHDMan resources...')
        with self._workers_lock: 
            workers_to_process = list(self.active_workers.values())
            self.active_workers.clear() 

        for worker in workers_to_process:
            worker.cancel() 
            if worker.process and worker.process.poll() is None:
                self.logger.info(f'Terminating PID {worker.process.pid} for worker {worker.worker_id}')
                try:
                    worker.process.terminate()
                    time.sleep(0.1)
                    Popen_poll = worker.process.poll()
                    if Popen_poll is None: 
                        time.sleep(0.4)
                        Popen_poll = worker.process.poll()
                    if Popen_poll is None: 
                        worker.process.kill()
                except Exception as e: 
                    self.logger.error(f'Error terminating for {worker.worker_id}: {e}', exc_info=True)
        
        self.logger.info('CHDMan cleanup complete.')
        
    def create_cd(self, input_file: str, output_file: str, compression: Optional[str] = None,
                  hunk_size: Optional[int] = None, force: bool = False) -> CHDManWorker:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        return self._create_and_start_worker(
            'createcd', input_file, output_file, compression, 
            hunk_size, force, os.path.basename(input_file)
        )
        
    def create_dvd(self, input_file: str, output_file: str, compression: Optional[str] = None,
                   hunk_size: Optional[int] = None, force: bool = False) -> CHDManWorker:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        self.logger.info(
            f'Creating DVD CHD: Input={input_file}, Output={output_file}, Comp={compression}, '
            f'Hunk={hunk_size}, Force={force}'
        )
        return self._create_and_start_worker(
            'createdvd', input_file, output_file, compression, 
            hunk_size, force, os.path.basename(input_file)
        )
        
    def create_hd(self, input_file: str, output_file: str, compression: Optional[str] = None,
                  hunk_size: Optional[int] = None, force: bool = False,
                  input_size: Optional[int] = None) -> CHDManWorker: 
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        return self._create_and_start_worker(
            'createhd', input_file, output_file, compression, 
            hunk_size, force, os.path.basename(input_file), inputsize=input_size
        )
        
    def extract_cd(self, input_file: str, output_file: str, force: bool = False) -> CHDManWorker:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        return self._create_and_start_worker(
            'extractcd', input_file, output_file, force=force, 
            worker_id_suffix=os.path.basename(input_file)
        )

    def extract_dvd(self, input_file: str, output_file: str, force: bool = False) -> CHDManWorker:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        return self._create_and_start_worker(
            'extractdvd', input_file, output_file, force=force, 
            worker_id_suffix=os.path.basename(input_file)
        )

    def extract_hd(self, input_file: str, output_file: str, force: bool = False) -> CHDManWorker:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        return self._create_and_start_worker(
            'extracthd', input_file, output_file, force=force, 
            worker_id_suffix=os.path.basename(input_file)
        )

    def extract_ld(self, input_file: str, output_file: str, force: bool = False) -> CHDManWorker:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        return self._create_and_start_worker(
            'extractld', input_file, output_file, force=force, 
            worker_id_suffix=os.path.basename(input_file)
        )
        
    def extract_raw(self, input_file: str, output_file: str, force: bool = False) -> CHDManWorker:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        return self._create_and_start_worker(
            'extractraw', input_file, output_file, force=force, 
            worker_id_suffix=os.path.basename(input_file)
        )

    def info(self, input_file: str) -> CHDManWorker:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        return self._create_and_start_worker(
            'info', input_file, worker_id_suffix=os.path.basename(input_file)
        )

    def verify(self, input_file: str) -> CHDManWorker:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        return self._create_and_start_worker(
            'verify', input_file, worker_id_suffix=os.path.basename(input_file)
        )

    def _remove_worker_by_id(self, worker_id: str):
        with self._workers_lock: 
            if worker_id in self.active_workers:
                del self.active_workers[worker_id]
                self.logger.info(f'Worker {worker_id} removed. Active: {len(self.active_workers)}')
            else: 
                self.logger.warning(f'Attempted to remove {worker_id}, not found.')

    def _parse_info_output(self, output: str) -> Dict[str, Any]: 
        info = {}
        for line in output.splitlines():
            line = line.strip()
            if not line: 
                continue
            parts = line.split(':', 1)
            if len(parts) == 2: 
                info[parts[0].strip()] = parts[1].strip()
        return info


class CHDTaskType(Enum):
    COMPRESS, EXTRACT_RAW, EXTRACT_CD, EXTRACT_DVD, EXTRACT_HD, EXTRACT_AV, INFO, VERIFY, DUMP_META = [auto() for _ in range(9)]

@dataclass
class CHDTask:
    task_type: CHDTaskType
    input_file: str
    output_file: Optional[str] = None
    compression_level: Optional[str] = None
    hunk_size: Optional[int] = None
    verify: bool = False
    force: bool = False
    media_type: Optional[str] = None 
    algorithms: Optional[str] = None 
    user_data: Optional[Dict[str, Any]] = None
    def __post_init__(self):
        if self.user_data is None: 
            self.user_data = {}

class CHDManager(QObject):
    signals = CHDManSignals() 
    def __init__(self, executable_path: str = 'chdman'):
        super().__init__()
        self.executable_path = executable_path 
        self.chdman = CHDMan(executable_path) 
        self.tasks: List[CHDTask] = []
        self.active_workers: Dict[str, CHDManWorker] = {} 
        self.thread_pool = QThreadPool()
        self._task_mutex = QMutex() 
        self.logger = logging.getLogger(__name__ + '.CHDManager')

    def log(self, message: str): 
        self.logger.info(message)

    def terminate_all_chdman_processes(self):
        self.logger.info('Delegating terminate all to CHDMan instance')
        self.chdman.terminate_all_chdman_processes() 
        
        with self._task_mutex: 
            manager_workers_to_cancel = list(self.active_workers.values())
        for worker in manager_workers_to_cancel:
            worker.cancel()
        self.logger.info('CHDManager also cancelled its own managed active workers if any.')


    def add_task(self, task: CHDTask) -> None:
        with QMutexLocker(self._task_mutex): 
            self.tasks.append(task)
        self.logger.info(f'Task added: {task.input_file} -> {task.task_type.name}')

    def clear_tasks(self):
        with QMutexLocker(self._task_mutex): 
            self.tasks.clear()
        self.logger.info('All tasks cleared.')
        
    def execute_all_tasks(self) -> List[CHDManWorker]:
        workers_started: List[CHDManWorker] = []
        with QMutexLocker(self._task_mutex):
            if not self.tasks: 
                self.logger.info('No tasks to execute.')
                return []
            tasks_to_run = list(self.tasks) 
            self.tasks.clear() 

        self.logger.info(f'Executing {len(tasks_to_run)} tasks.')
        for task in tasks_to_run:
            try:
                if not task.input_file or not os.path.exists(task.input_file):
                    raise CHDManInputFileError(f'Manager check: Input file not found: {task.input_file}')
                if task.output_file:
                    output_dir = os.path.dirname(task.output_file)
                    if output_dir and not os.path.exists(output_dir):
                        try: 
                            os.makedirs(output_dir, exist_ok=True)
                        except Exception as e: 
                            raise CHDManOutputFileError(
                                f'Manager check: Cannot create output dir: {output_dir}. {e}'
                            )
                
                worker = self._delegate_task_to_chdman(task)
                if worker: 
                    workers_started.append(worker)
            except CHDManError as e:
                self.logger.error(f'Error preparing or delegating task {task.input_file}: {e}', exc_info=True)
                self.signals.error.emit(f'Error for task {task.input_file}: {e}') 
            except Exception as e:
                self.logger.error(f'Unexpected error preparing or delegating task {task.input_file}: {e}', exc_info=True)
                self.signals.error.emit(f'Unexpected error for task {task.input_file}: {e}')
        return workers_started

    def _delegate_task_to_chdman(self, task: CHDTask) -> Optional[CHDManWorker]:
        self.logger.debug(f'Delegating task to CHDMan: {task.task_type.name} - {task.input_file}')
        worker: Optional[CHDManWorker] = None
        
        if task.task_type == CHDTaskType.COMPRESS:
            command_name_map = {'CD': 'createcd', 'DVD': 'createdvd', 'HD': 'createhd'}
            command_name = command_name_map.get(task.media_type or '', '')
            if not command_name: 
                self.logger.error(f'Unsupported media: {task.media_type}')
                return None
            if not task.output_file: 
                self.logger.error(f'No output file for compress: {task.input_file}')
                return None
            
            task_kwargs = {'input_size': task.user_data.get('input_size') if task.user_data else None} if command_name == 'createhd' else {}

            worker_method = getattr(self.chdman, command_name, None)
            if worker_method:
                 worker = worker_method(
                     task.input_file, task.output_file, task.algorithms, 
                     task.hunk_size, task.force, **task_kwargs
                 )
            else: 
                self.logger.error(f"CHDMan has no method '{command_name}'")
                return None
        
        elif task.task_type == CHDTaskType.EXTRACT_CD:
            if not task.output_file: 
                self.logger.error(f'No output for extract_cd: {task.input_file}')
                return None
            worker = self.chdman.extract_cd(task.input_file, task.output_file, task.force)
        elif task.task_type == CHDTaskType.EXTRACT_DVD:
            if not task.output_file: 
                self.logger.error(f'No output for extract_dvd: {task.input_file}')
                return None
            worker = self.chdman.extract_dvd(task.input_file, task.output_file, task.force)
        elif task.task_type == CHDTaskType.EXTRACT_HD:
            if not task.output_file: 
                self.logger.error(f'No output for extract_hd: {task.input_file}')
                return None
            worker = self.chdman.extract_hd(task.input_file, task.output_file, task.force)
        elif task.task_type == CHDTaskType.EXTRACT_RAW:
            if not task.output_file: 
                self.logger.error(f'No output for extract_raw: {task.input_file}')
                return None
            worker = self.chdman.extract_raw(task.input_file, task.output_file, task.force)
        elif task.task_type == CHDTaskType.INFO:
            worker = self.chdman.info(task.input_file)
        elif task.task_type == CHDTaskType.VERIFY:
            worker = self.chdman.verify(task.input_file)
        else: 
            self.logger.error(f'Unsupported task type for delegation: {task.task_type.name}')
            return None

        if worker:
            worker.signals.finished.connect(lambda s, m, t=task, w_id=worker.worker_id: self._on_delegated_worker_finished(t, s, m, w_id))
            worker.signals.error.connect(lambda e, t=task, w_id=worker.worker_id: self._on_delegated_worker_error(t, e, w_id))
            self.logger.info(f'Delegated and started worker {worker.worker_id} via CHDMan for {task.input_file}')
        return worker

    def _on_delegated_worker_finished(self, task: CHDTask, success: bool, message: str, worker_id: str):
        self.logger.info(f'Delegated worker {worker_id} for task {task.input_file} finished. Success: {success}. Msg: {message}')
        self.signals.task_completed.emit(task.input_file, success, message)

    def _on_delegated_worker_error(self, task: CHDTask, error_message: str, worker_id: str):
        self.logger.error(f'Delegated worker {worker_id} for task {task.input_file} error: {error_message}')
        self.signals.task_completed.emit(task.input_file, False, error_message)
                    
    def find_chdman(self) -> str: 
        return self.chdman.executable_path 

    def get_chdman_version(self, executable_path: Optional[str]=None) -> Optional[str]:
        return self.chdman.get_chdman_version(executable_path or self.chdman.executable_path)

    def get_active_tasks_count(self) -> int: 
        return len(self.chdman.active_workers) 
    
    def cleanup(self):
        self.logger.info('CHDManager cleanup initiated. Delegating to CHDMan instance.')
        self.chdman.cleanup() 
        with QMutexLocker(self._task_mutex): 
            self.tasks.clear()
        self.logger.info('CHDManager cleanup finished.')

_chd_manager_singleton = None
_singleton_lock = threading.Lock() 

def get_chd_manager():
    global _chd_manager_singleton
    if _chd_manager_singleton is None: 
        with _singleton_lock:
            if _chd_manager_singleton is None: 
                chdman_path = load_chdman_path()
                if not chdman_path: 
                    chdman_path = 'chdman'
                
                if not logging.getLogger().hasHandlers():
                    logging.basicConfig(
                        level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )
                _chd_manager_singleton = CHDManager(executable_path=chdman_path)
    return _chd_manager_singleton

[end of core/chdman.py]
