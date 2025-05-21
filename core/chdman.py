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
from typing import Dict, Optional, Any
from dataclasses import dataclass

from modules.settings import load_chdman_path
from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool, QMutex, QMutexLocker

class CHDCompressionType(Enum):
    """Available compression types for CHD files."""
    ZLIB = "zlib"
    ZLIB_HUFF = "zlib_huff"
    LZMA = "lzma"
    SDX = "sdx"
    AUTO = "auto"
    # Add more as needed

class CHDManError(Exception):
    """Base exception for CHDMAN operations."""
    pass


class CHDManExecutableNotFoundError(CHDManError):
    """Raised when the CHDMAN executable cannot be found."""
    pass


class CHDManCommandError(CHDManError):
    """Raised when a CHDMAN command fails.
    
    Attributes:
        command: The command that failed
        returncode: The return code of the command
        output: The output of the command
    """
    def __init__(self, command: str, returncode: int, output: str):
        self.command = command
        self.returncode = returncode
        self.output = output
        super().__init__(f"CHDMAN command '{command}' failed with return code {returncode}: {output}")


class CHDManInputFileError(CHDManError):
    """Raised when an input file is invalid or not found."""
    pass


class CHDManOutputFileError(CHDManError):
    """Raised when an output file cannot be created or written to."""
    pass



@dataclass
class CHDManCommand:
    """Represents a CHDMAN command with its parameters.
    
    Attributes:
        name: Command name (e.g., 'createcd', 'info')
        description: Human-readable description of the command
        requires_input: Whether the command requires an input file
        requires_output: Whether the command requires an output file
        supports_compression: Whether the command supports compression options
    """
    name: str
    description: str
    requires_input: bool
    requires_output: bool
    supports_compression: bool


class CHDManSignals(QObject):
    """Signals for CHDMan operations.
    
    Signals:
        started: Emitted when the operation starts
        progress: Emitted during operation with progress percentage and message
        finished: Emitted when the operation completes successfully
        error: Emitted when an error occurs
        progress_updated: Emitted when progress is updated (progress, message, worker_id)
        task_completed: Emitted when a task is completed (task_id, success, message)
    """
    started = Signal(str)  # Command description
    progress = Signal(float, str)  # Progress percentage, message
    finished = Signal(bool, str)  # Success status, message
    error = Signal(str)  # Error message
    progress_updated = Signal(float, str, str)  # Progress percentage, message, worker_id
    task_completed = Signal(str, bool, str)  # task_id, success, message
    error_occurred = Signal(str)  # Error message for compatibility with BatchProcessor


class CHDManWorker(QRunnable):
    """Worker for running CHDMAN operations in a separate thread.
    
    This class handles the execution of CHDMAN commands asynchronously,
    reporting progress and results through signals.
    """
    
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
        """Initialize the CHDManWorker.
        
        Args:
            executable_path: Path to the CHDMAN executable
            command: CHDMAN command to execute (e.g., 'createcd', 'info')
            input_file: Path to the input file
            output_file: Path to the output file (if applicable)
            compression: Compression algorithm(s) to use (if applicable)
            hunk_size: Hunk size in bytes (if applicable)
            force: Whether to force overwrite of output file
            verbose: Whether to enable verbose output
            **kwargs: Additional command-specific parameters
        """
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
        self.worker_id = worker_id or str(id(self))  # Use the object ID if no worker_id provided
        
        # Initialize signals
        self.signals = CHDManSignals()
        self.process = None
        self.cancelled = False
        
        # Log the worker instantiation
        try:
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"[CHDManWorker] __init__ with executable_path: {self.executable_path}, command: {self.command}\n")
        except Exception:
            pass
        
    @Slot()
    def run(self):
        if getattr(self, "_has_run", False):
            return
        self._has_run = True
        """Execute the CHDMAN command.
        
        This method is called when the worker is started by the thread pool.
        It builds the command, executes it, and monitors the progress.
        """
        try:
            # Log before launching
            try:
                with open('error.log', 'a', encoding='utf-8') as logf:
                    logf.write(f"[CHDManWorker.run] Launching: {self.executable_path} with command: {self.command}, input: {self.input_file}, output: {self.output_file}\n")
            except Exception:
                pass
            
            # Log all key paths and command info to error.log (for debugging)
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"\n[CHDManWorker] Starting run at: {datetime.now()}\n")
                logf.write(f"  Executable: {self.executable_path}\n")
                logf.write(f"  Command: {self.command}\n")
                logf.write(f"  Input file: {self.input_file}\n")
                logf.write(f"  Output file: {self.output_file}\n")
                logf.write(f"  Compression: {self.compression}\n")
                logf.write(f"  Hunk size: {self.hunk_size}\n")
                logf.write(f"  Force: {self.force}\n")
                logf.write(f"  Worker ID: {self.worker_id}\n")
                logf.write(f"  KWArgs: {self.kwargs}\n")
            print(f"[CHDManWorker] Launching: {self.executable_path} {self.command} -i {self.input_file} -o {self.output_file}")

            # Check if executable exists using shutil.which
            import shutil
            if shutil.which(self.executable_path) is None:
                raise CHDManExecutableNotFoundError(
                    f"Cannot find '{self.executable_path}' in PATH."
                )
                
            # Check if input file exists
            if not os.path.exists(self.input_file):
                raise CHDManInputFileError(f"Input file not found: {self.input_file}")
                
            # Check if output directory exists for commands that require output
            if self.output_file:
                # Check if output file exists and try to delete it first (even with force flag)
                if os.path.exists(self.output_file):
                    try:
                        os.remove(self.output_file)
                        print(f"Removed existing output file: {self.output_file}")
                    except (OSError, PermissionError) as e:
                        print(f"Warning: Could not remove existing output file: {self.output_file}. Error: {str(e)}")
                        # We'll continue and let CHDMAN handle it with the -f flag
                
                # Ensure output directory exists
                output_dir = os.path.dirname(self.output_file)
                if output_dir:
                    if not os.path.exists(output_dir):
                        try:
                            os.makedirs(output_dir, exist_ok=True)
                        except OSError as e:
                            raise CHDManOutputFileError(f"Cannot create output directory: {output_dir}. {str(e)}")
                    
                    # Check if we have write permission to the output directory
                    if not os.access(output_dir, os.W_OK):
                        raise CHDManOutputFileError(f"No write permission for output directory: {output_dir}")
                    
                    # Try to create a test file to verify write access
                    import time as _time  # Local import to avoid conflicts
                    test_file = os.path.join(output_dir, f".test_write_{int(_time.time())}")
                    try:
                        with open(test_file, 'w') as f:
                            f.write('test')
                        os.remove(test_file)  # Clean up test file
                    except (OSError, PermissionError) as e:
                        raise CHDManOutputFileError(f"Cannot write to output directory: {output_dir}. Error: {str(e)}")
            
            # Build command
            cmd = [self.executable_path, self.command]
            
            # Add input file
            cmd.extend(["-i", self.input_file])
            
            # Add output file if specified
            if self.output_file:
                cmd.extend(["-o", self.output_file])
                
            # Add compression if specified and supported
            if self.compression:
                # Check if this is a comma-separated list of algorithms
                if ',' in self.compression:
                    original_algorithms = self.compression.split(',')
                    valid_algorithms = ["none", "zlib", "zstd", "lzma", "huff", "flac", "cdlz", "cdzl", "cdfl", "avhu"]
                    corrected_algorithms = []
                    
                    # Validate each algorithm and correct if needed
                    for algo_name in original_algorithms:
                        algo_name = algo_name.strip().lower()  # Clean up
                        if algo_name not in valid_algorithms:
                            # Provide helpful error message for common mistakes
                            if algo_name == "cdzlib":
                                print("Warning: 'cdzlib' is not a valid algorithm. Did you mean 'cdzl'? Correcting automatically.")
                                corrected_algorithms.append("cdzl")
                            elif algo_name == "cdflac":
                                print("Warning: 'cdflac' is not a valid algorithm. Did you mean 'cdfl'? Correcting automatically.")
                                corrected_algorithms.append("cdfl")
                            else:
                                raise ValueError(f"Invalid compression algorithm: {algo_name}. Valid options are: {', '.join(valid_algorithms)}")
                        else:
                            corrected_algorithms.append(algo_name)
                    
                    # CHDMAN expects multiple algorithms as a single comma-separated parameter
                    algorithms_str = ','.join(corrected_algorithms)
                    cmd.extend(["-c", algorithms_str])
                    print(f"Using multiple compression algorithms: {algorithms_str}")
                else:
                    # Single algorithm
                    valid_algorithms = ["none", "zlib", "zstd", "lzma", "huff", "flac", "cdlz", "cdzl", "cdfl", "avhu"]
                    algo_name = self.compression.strip().lower()  # Clean up
                    if algo_name not in valid_algorithms:
                        # Provide helpful error message for common mistakes
                        if algo_name == "cdzlib":
                            print("Warning: 'cdzlib' is not a valid algorithm. Did you mean 'cdzl'? Correcting automatically.")
                            algo_name = "cdzl"
                        elif algo_name == "cdflac":
                            print("Warning: 'cdflac' is not a valid algorithm. Did you mean 'cdfl'? Correcting automatically.")
                            algo_name = "cdfl"
                        else:
                            raise ValueError(f"Invalid compression algorithm: {algo_name}. Valid options are: {', '.join(valid_algorithms)}")
                    
                    cmd.extend(["-c", algo_name])
                    print(f"Using compression algorithm: {algo_name}")
                
            # Add hunk size if specified
            if self.hunk_size:
                cmd.extend(["-hs", str(self.hunk_size)])
                
            # Add force flag if specified
            if self.force:
                cmd.append("-f")
                
            # Only add verbose flag for commands that support it
            # Currently, only info and verify commands reliably support the -v flag
            if self.verbose and self.command in ["info", "verify"]:
                cmd.append("-v")
                
            # Add additional parameters
            for key, value in self.kwargs.items():
                if value is not None:
                    cmd.extend([f"-{key}", str(value)])
            
            # Format the command string with proper quoting for display
            cmd_str = " ".join([f'"{arg}"' if ' ' in arg else arg for arg in cmd])
        
            # Emit started signal with a clean, formatted command string
            self.signals.started.emit(f"Running: {cmd_str}")
            
            # Print detailed information in verbose mode
            if self.verbose:
                print("\n=== CHDMAN DETAILED INFORMATION ===")
                print(f"Command: {cmd_str}")
                print(f"Executable: {self.executable_path}")
                print(f"Operation: {self.command}")
                print(f"Input file: {self.input_file}")
                if self.output_file:
                    print(f"Output file: {self.output_file}")
                print(f"Force flag: {self.force}")
                if self.compression:
                    print(f"Compression algorithms: {self.compression}")
                if self.hunk_size:
                    print(f"Hunk size: {self.hunk_size}")
                for key, value in self.kwargs.items():
                    if value is not None:
                        print(f"Additional parameter - {key}: {value}")
                print("==================================\n")
            else:
                # Print basic command for debugging
                print(f"CHDMAN COMMAND: {cmd_str}")
                print(f"Force flag: {self.force}")
                print(f"Compression: {self.compression}")
            
            # Start process with non-blocking I/O
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Collect all output for error reporting
            all_output = []
            error_output = []
            
            # Log the process ID for debugging
            print(f"CHDMAN process started with PID: {self.process.pid}")
            self.signals.progress.emit(0, f"Started CHDMAN process (PID: {self.process.pid})")
            
            # Monitor progress with a cross-platform approach using threading
            import time
            import threading
            import queue
            
            # Create queues for stdout and stderr
            stdout_queue = queue.Queue()
            stderr_queue = queue.Queue()
            
            # Keep track of last progress update time to periodically send updates even if no new output
            last_progress_time = time.time()
            last_progress_value = 0
            
            # Function to read from a stream and put lines into a queue
            def read_stream(stream, output_queue):
                # Set stream to binary mode to avoid encoding issues
                try:
                    for line in iter(stream.readline, b'' if hasattr(stream, 'mode') and 'b' in stream.mode else ''):
                        if line:
                            # Handle both bytes and strings
                            try:
                                if isinstance(line, bytes):
                                    decoded_line = line.decode('utf-8', errors='replace').strip()
                                else:
                                    # Already a string, just strip it
                                    decoded_line = line.strip()
                                    
                                if decoded_line:  # Only queue non-empty lines
                                    output_queue.put(decoded_line)
                            except Exception as e:
                                print(f"Error processing line: {e}")
                                # Try to queue the raw line as a fallback
                                try:
                                    output_queue.put(str(line))
                                except Exception:
                                    pass
                except Exception as e:
                    print(f"Error reading from stream: {e}")
                output_queue.put(None)  # Signal end of stream
            
            # Start threads to read from stdout and stderr
            stdout_thread = threading.Thread(target=read_stream, args=(self.process.stdout, stdout_queue))
            stderr_thread = threading.Thread(target=read_stream, args=(self.process.stderr, stderr_queue))
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            # Flag to track if we've reached the end of both streams
            stdout_done = False
            stderr_done = False
            
            # Continue until process completes and all output is processed
            while self.process.poll() is None or not (stdout_done and stderr_done):
                # Check if cancelled
                if self.cancelled:
                    print(f"Cancellation detected for process {self.process.pid}, terminating...")
                    try:
                        self.process.terminate()
                        # Wait briefly to see if it terminates
                        for i in range(5):
                            if self.process.poll() is not None:
                                print("Process terminated gracefully after cancel")
                                break
                            time.sleep(0.1)
                            
                        # If still running, force kill
                        if self.process.poll() is None:
                            print("Process still running after cancel, force killing...")
                            self.process.kill()
                    except Exception as e:
                        print(f"Error terminating process during cancellation: {e}")
                        
                    self.signals.error.emit("Operation cancelled by user")
                    return
                
                # Process any available stdout data
                try:
                    # Non-blocking get with timeout
                    line = stdout_queue.get(block=True, timeout=0.1)
                    if line is None:
                        stdout_done = True
                    else:
                        all_output.append(line)
                        # Parse progress information
                        progress = self._parse_progress(line)
                        if progress is not None:
                            last_progress_value = progress
                            last_progress_time = time.time()
                            self.signals.progress.emit(progress, line)
                        elif line:  # Only emit non-empty lines
                            self.signals.progress.emit(-1, line)  # -1 indicates no progress value
                            # Print additional details in verbose mode
                            if self.verbose and not line.startswith("Processing:"):
                                print(f"CHDMAN OUTPUT: {line}")
                except queue.Empty:
                    pass  # No stdout data available
                
                # Process any available stderr data
                try:
                    # Non-blocking get with timeout
                    line = stderr_queue.get(block=False)
                    if line is None:
                        stderr_done = True
                    else:
                        all_output.append(line)
                        error_output.append(line)
                        
                        # Check if this is a real error or just progress information
                        # CHDMAN sometimes outputs progress information to stderr
                        if "Compressing" in line or "complete" in line or "ratio=" in line:
                            # This is likely progress information, not an error
                            self.signals.progress.emit(-1, line)
                        else:
                            # This is likely a real error
                            error_msg = f"ERROR: {line}"
                            self.signals.progress.emit(-1, error_msg)
                            
                        # Print additional details in verbose mode
                        if self.verbose:
                            print(f"CHDMAN STDERR: {line}")
                except queue.Empty:
                    pass  # No stderr data available
                
                # If no progress update for 2 seconds, send a heartbeat
                if time.time() - last_progress_time > 2:
                    # Only send heartbeat if not cancelled
                    if not self.cancelled:
                        self.signals.progress.emit(last_progress_value, "Processing... (still working)")
                        last_progress_time = time.time()
                    
                # Don't hog the CPU
                time.sleep(0.05)
            
            # Process any remaining output after process completion
            # Wait for the stdout and stderr threads to finish
            stdout_thread.join(timeout=1.0)
            stderr_thread.join(timeout=1.0)
            
            # Process any remaining items in the queues
            try:
                while not stdout_queue.empty():
                    line = stdout_queue.get_nowait()
                    if line is None:
                        continue
                    all_output.append(line)
                    progress = self._parse_progress(line)
                    if progress is not None:
                        self.signals.progress.emit(progress, line)
                    else:
                        self.signals.progress.emit(-1, line)
                    if self.verbose:
                        print(f"CHDMAN FINAL OUTPUT: {line}")
            except Exception as e:
                print(f"Error processing remaining stdout: {e}")
                
            try:
                while not stderr_queue.empty():
                    line = stderr_queue.get_nowait()
                    if line is None:
                        continue
                    all_output.append(line)
                    error_output.append(line)
                    self.signals.progress.emit(-1, f"ERROR: {line}")
                    if self.verbose:
                        print(f"CHDMAN FINAL ERROR: {line}")
            except Exception as e:
                print(f"Error processing remaining stderr: {e}")
            
            # Wait for process to complete
            return_code = self.process.wait()
            print(f"CHDMAN process completed with return code: {return_code}")
            
            # Check if process was cancelled
            if self.cancelled:
                print("Process was cancelled, not sending completion signal")
                return
            
            # Get error output if any
            try:
                stderr_output = self.process.stderr.read().strip() if self.process.stderr else ""
                if stderr_output:
                    all_output.append("\nError output:")
                    all_output.append(stderr_output)
            except Exception as e:
                print(f"Error reading stderr after completion: {e}")
                stderr_output = ""
            
            # For chdman, return code 1 can be normal when displaying help or with missing parameters
            # Only treat as error if it's not expected or if there's actual error output
            try:
                if return_code == 0 or (return_code == 1 and "Usage:" in "\n".join(all_output) and not stderr_output):
                    print("CHDMAN process completed successfully, emitting finished signal")
                    self.signals.finished.emit(True, "Operation completed successfully")
                    return  # Return here to avoid raising an exception
                else:
                    error_output = "\n".join(all_output)
                    error_message = f"CHDMAN command failed with return code {return_code}"
                    if error_output:
                        error_message += f":\n{error_output}"
                    
                    # Check for specific error types and provide more helpful messages
                    if "Permission denied" in error_output or "Access is denied" in error_output.lower():
                        # Add more helpful information for permission errors
                        if self.output_file:
                            output_dir = os.path.dirname(self.output_file)
                            error_message += f"\n\nPermission error: Unable to write to {output_dir}."
                            error_message += "\nPlease try:"
                            error_message += "\n1. Choose a different output directory where you have write permissions"
                            error_message += "\n2. Run the application as administrator"
                            error_message += "\n3. Check if the drive is write-protected"
                            error_message += "\n4. Ensure the output file is not currently in use by another process"
                    
                    # Check for missing input file errors
                    if "No such file or directory" in error_output or "cannot open" in error_output.lower():
                        error_message += "\n\nInput file error: The specified input file could not be opened."
                        error_message += "\nPlease check that the file exists and is accessible."
                    
                    # Raise custom exception for error handling
                    cmd_str = " ".join(cmd)
                    raise CHDManCommandError(cmd_str, return_code, error_output)
            except CHDManError as e:
                # This will be caught by the outer try/except block
                raise e
                
        except CHDManError as e:
            # Handle custom exceptions
            self.signals.error.emit(str(e))
        except FileNotFoundError as e:
            # Handle file not found errors
            self.signals.error.emit(f"File not found: {str(e)}")
        except PermissionError as e:
            # Handle permission errors
            self.signals.error.emit(f"Permission error: {str(e)}")
        except OSError as e:
            # Handle OS errors
            self.signals.error.emit(f"OS error: {str(e)}")
        except Exception as e:
            # Handle other exceptions
            self.signals.error.emit(f"Error executing CHDMAN: {str(e)}")
            
    def cancel(self):
        """Cancel the running operation."""
        self.cancelled = True
    
    def _parse_progress(self, line: str) -> Optional[float]:
        """Parse progress information from CHDMAN output.
        
        Args:
            line: Line of output from CHDMAN
            
        Returns:
            Progress percentage (0-100) or None if no progress info found
        """
        # Different CHDMAN commands have different progress formats
        # Try to match common patterns
        
        # Skip empty lines
        if not line or not line.strip():
            return None
            
        # Log the line for debugging
        print(f"CHDMAN output: {line}")
        
        # Pattern: "Compressing, 45.3% complete..." (createcd, createdvd, etc.)
        match = re.search(r'(\d+(\.\d+)?)% complete', line)
        if match:
            return float(match.group(1))
        
        # Pattern: "Compression complete ... (100%)" (end of compression)
        match = re.search(r'\((\d+)%\)', line)
        if match:
            return float(match.group(1))
        
        # Pattern: "Block 1000/2000" (extractcd, extractdvd, etc.)
        match = re.search(r'Block (\d+)/(\d+)', line)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            if total > 0:
                return (current / total) * 100
        
        # Pattern: "Compressing sector 1000/2000" (some versions of CHDMAN)
        match = re.search(r'sector (\d+)/(\d+)', line, re.IGNORECASE)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            if total > 0:
                return (current / total) * 100
                
        # Pattern: "Processing track 1/10" (some versions of CHDMAN)
        match = re.search(r'track (\d+)/(\d+)', line, re.IGNORECASE)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            if total > 0:
                return (current / total) * 100
                
        # If we detect the start of processing, return 1% to show something is happening
        if "processing" in line.lower() or "compressing" in line.lower():
            return 1.0
            
        # If we see "Input" or "Output" lines, it means we're starting, so return 0%
        if line.startswith("Input") or line.startswith("Output"):
            return 0.0
                
        return None


class CHDMan:
    """Wrapper for the CHDMAN command-line utility.
    
    Provides a Pythonic interface to CHDMAN operations including
    compression, extraction, verification, and information retrieval.
    """
    
    # Define available commands
    COMMANDS = {
        "createcd": CHDManCommand("createcd", "Create CHD from CD image", True, True, True),
        "createdvd": CHDManCommand("createdvd", "Create CHD from DVD image", True, True, True),
        "createhd": CHDManCommand("createhd", "Create CHD from hard disk image", True, True, True),
        "createld": CHDManCommand("createld", "Create CHD from laserdisc image", True, True, True),
        "extractcd": CHDManCommand("extractcd", "Extract CD image from CHD", True, True, False),
        "extractdvd": CHDManCommand("extractdvd", "Extract DVD image from CHD", True, True, False),
        "extracthd": CHDManCommand("extracthd", "Extract hard disk image from CHD", True, True, False),
        "extractld": CHDManCommand("extractld", "Extract laserdisc image from CHD", True, True, False),
        "extractraw": CHDManCommand("extractraw", "Extract raw data from CHD", True, True, False),
        "info": CHDManCommand("info", "Display information about a CHD", True, False, False),
        "verify": CHDManCommand("verify", "Verify CHD integrity", True, False, False),
    }
    
    # Define available compression algorithms
    COMPRESSION_ALGORITHMS = [
        "none",
        "zlib",
        "zstd",
        "lzma",
        "huff",
        "flac",
        "cdlz",
        "cdfl",
        "avhu",
    ]
    
    def __init__(self, executable_path: Optional[str] = None, verbose: bool = False):
        """Initialize the CHDMan wrapper.
        
        Args:
            executable_path: Path to the CHDMAN executable (if None, load from settings)
            verbose: Whether to enable verbose output
        """
        # Use persisted path if not explicitly provided
        if executable_path is None or executable_path.strip() == "":
            persisted_path = load_chdman_path()
            if persisted_path:
                self.executable_path = persisted_path
            else:
                self.executable_path = "chdman"  # fallback
        else:
            self.executable_path = executable_path
        self.verbose = verbose
        self.thread_pool = QThreadPool()
        self.active_workers = {}  # Track active workers by task id
        # Log the path used for CHDMAN
        try:
            with open('error.log', 'a', encoding='utf-8') as logf:
                logf.write(f"[CHDMan] Initialized with executable_path: {self.executable_path}\n")
        except Exception:
            pass
    
    def terminate_all_chdman_processes(self):
        """Find and terminate all CHDMAN processes running on the system.
        
        This is more aggressive than cleanup() as it will terminate ALL CHDMAN processes,
        not just those started by this instance of the application.
        """
        print("CHDMan: Searching for and terminating all CHDMAN processes...")
        
        # First mark all active workers as cancelled
        for worker in self.active_workers:
            if worker and hasattr(worker, 'cancelled'):
                worker.cancelled = True
                print(f"Marked worker as cancelled: {worker}")
        
        # Then try to terminate processes directly
        try:
            # First try using platform-specific commands (more reliable)
            if os.name == 'nt':  # Windows
                # Use taskkill to terminate all chdman processes
                print("Using taskkill to terminate chdman.exe processes")
                result = subprocess.run(['taskkill', '/F', '/IM', 'chdman.exe'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True,
                              check=False)
                print(f"Taskkill result: {result.returncode}")
                if result.stdout:
                    print(f"Taskkill output: {result.stdout}")
                if result.stderr:
                    print(f"Taskkill error: {result.stderr}")
            else:  # Unix-like
                # Use pkill to terminate all chdman processes
                print("Using pkill to terminate chdman processes")
                result = subprocess.run(['pkill', '-9', 'chdman'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True,
                              check=False)
                print(f"Pkill result: {result.returncode}")
                if result.stdout:
                    print(f"Pkill output: {result.stdout}")
                if result.stderr:
                    print(f"Pkill error: {result.stderr}")
            print("Terminated CHDMAN processes using system commands")
        except Exception as e:
            print(f"Warning: Failed to terminate CHDMAN processes using system commands: {e}")
            # Fall back to just cleaning up our own processes
            self.cleanup()
    
    def _validate_compression_algorithms(self, compression: str):
        """Validate compression algorithms, handling comma-separated lists.
        
        Args:
            compression: Compression algorithm(s) to validate, can be comma-separated
            
        Raises:
            ValueError: If any algorithm in the list is invalid
        """
        if not compression:
            return
            
        # Split by comma if multiple algorithms are specified
        algorithms = compression.split(',')
        
        # Validate each algorithm
        for algo in algorithms:
            algo = algo.strip().lower()
            if algo not in self.COMPRESSION_ALGORITHMS:
                # Special case handling for common typos
                if algo == 'cdzlib':
                    print("Warning: 'cdzlib' is not a valid algorithm. Did you mean 'cdzl'? Correcting automatically.")
                elif algo == 'cdflac':
                    print("Warning: 'cdflac' is not a valid algorithm. Did you mean 'cdfl'? Correcting automatically.")
                else:
                    valid_algorithms = ', '.join(self.COMPRESSION_ALGORITHMS)
                    raise ValueError(f"Invalid compression algorithm: {algo}. Valid options are: {valid_algorithms}")
    
    def cleanup(self):
        """Terminate all running CHDMAN processes.
        
        This should be called when the application is closing to ensure
        all CHDMAN processes are properly terminated.
        """
        print("Cleaning up CHDManager resources...")
        
        # Cancel all active workers
        for worker in list(self.active_workers):
            if hasattr(worker, 'cancel'):
                worker.cancel()
        
        # Then terminate all active worker processes
        terminated_count = 0
        for worker in self.active_workers:
            if worker and worker.process and worker.process.poll() is None:
                print(f"Terminating CHDMAN process: {worker.process.pid}")
                try:
                    # First try to terminate gracefully
                    worker.process.terminate()
                    
                    # Give it a moment to terminate gracefully
                    for i in range(10):  # Increased timeout for graceful termination
                        if worker.process.poll() is not None:
                            print(f"Process terminated gracefully after {i/10:.1f} seconds")
                            terminated_count += 1
                            break
                        time.sleep(0.1)
                    
                    # If still running, force kill it
                    if worker.process.poll() is None:
                        print(f"Force killing CHDMAN process: {worker.process.pid}")
                        worker.process.kill()
                        
                        # Verify the kill worked
                        for i in range(5):
                            if worker.process.poll() is not None:
                                print(f"Process killed after {i/10:.1f} seconds")
                                terminated_count += 1
                                break
                            time.sleep(0.1)
                        
                        # If still not terminated, try platform-specific kill
                        if worker.process.poll() is None:
                            print("Process still running after kill, trying platform-specific termination")
                            if os.name == 'nt':  # Windows
                                try:
                                    os.system(f"taskkill /F /PID {worker.process.pid}")
                                except Exception as e:
                                    print(f"Error with taskkill: {e}")
                            else:  # Unix-like
                                try:
                                    os.system(f"kill -9 {worker.process.pid}")
                                except Exception as e:
                                    print(f"Error with kill -9: {e}")
                except Exception as e:
                    print(f"Error terminating CHDMAN process: {e}")
        
        print(f"Successfully terminated {terminated_count} process{'es' if terminated_count != 1 else ''}")
        
        # Clear the list
        self.active_workers.clear()
        print("CHDManager cleanup complete.")
        
    def create_cd(self, 
                  input_file: str, 
                  output_file: str, 
                  compression: Optional[str] = None,
                  hunk_size: Optional[int] = None,
                  force: bool = False) -> CHDManSignals:
        """Create a CHD file from a CD image.
        
        Args:
            input_file: Path to the input .cue or .iso file
            output_file: Path for the output .chd file
            compression: Compression algorithm(s) to use
            hunk_size: Size of data hunks in bytes
            force: Whether to overwrite existing output file
            
        Returns:
            CHDManSignals object for connecting to signals
            
        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If parameters are invalid
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        # The CHDManWorker will handle parsing and validating the comma-separated 'compression' string
        # No validation here as it prevents using comma-separated algorithm lists
            
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="createcd",
            input_file=input_file,
            output_file=output_file,
            compression=compression,
            hunk_size=hunk_size,
            force=force,
            verbose=self.verbose,
            worker_id=f"createcd_{id(input_file)}"
        )
        
        # Track the worker for cleanup
        self.active_workers[worker.worker_id] = worker
        
        # Connect signals to remove worker from active_workers when done
        worker.signals.finished.connect(lambda success, msg, w=worker: self._remove_worker(w))
        worker.signals.error.connect(lambda msg, w=worker: self._remove_worker(w))
        
        self.thread_pool.start(worker)
        return worker
        
    def create_dvd(self, 
                   input_file: str, 
                   output_file: str, 
                   compression: Optional[str] = None,
                   hunk_size: Optional[int] = None,
                   force: bool = False) -> CHDManSignals:
        """Create a CHD file from a DVD image.
        
        Args:
            input_file: Path to the input .iso file
            output_file: Path for the output .chd file
            compression: Compression algorithm(s) to use
            hunk_size: Size of data hunks in bytes
            force: Whether to overwrite existing output file
            
        Returns:
            CHDManSignals object for connecting to signals
        """
        # Log the parameters for debugging
        print(f"""[CHDManager] Creating DVD CHD with:
  - Input: {input_file}
  - Output: {output_file}
  - Compression: {compression}
  - Hunk Size: {hunk_size}
  - Force: {force}""")

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        # The CHDManWorker will handle parsing and validating the comma-separated 'compression' string
        # No validation here as it prevents using comma-separated algorithm lists
            
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="createdvd",
            input_file=input_file,
            output_file=output_file,
            compression=compression,
            hunk_size=hunk_size,
            force=force,
            verbose=self.verbose,
            worker_id=f"createdvd_{id(input_file)}"
        )
        
        # Track the worker for cleanup
        self.active_workers[worker.worker_id] = worker
        
        # Connect signals to remove worker from active_workers when done
        worker.signals.finished.connect(lambda success, msg, w=worker: self._remove_worker(w))
        worker.signals.error.connect(lambda msg, w=worker: self._remove_worker(w))
        
        self.thread_pool.start(worker)
        return worker
        
    def create_hd(self, 
              input_file: str, 
              output_file: str, 
              compression: Optional[str] = None,
              hunk_size: Optional[int] = None,
              force: bool = False,
              input_size: Optional[int] = None) -> CHDManSignals:
        """Create a CHD file from a hard disk image.
        
        Args:
            input_file: Path to the input raw disk image
            output_file: Path for the output .chd file
            compression: Compression algorithm(s) to use
            hunk_size: Size of data hunks in bytes
            force: Whether to overwrite existing output file
            input_size: Size of the input file in bytes (required for some raw images)
        
        Returns:
            CHDManSignals object for connecting to signals
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        # The CHDManWorker will handle parsing and validating the comma-separated 'compression' string
        # No validation here as it prevents using comma-separated algorithm lists
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="createhd",
            input_file=input_file,
            output_file=output_file,
            compression=compression,
            hunk_size=hunk_size,
            force=force,
            inputsize=input_size,  # Pass through to worker
            verbose=self.verbose,
            worker_id=f"createhd_{id(input_file)}"
        )
        # Track the worker for cleanup
        self.active_workers[worker.worker_id] = worker
        # Connect signals to remove worker from active_workers when done
        worker.signals.finished.connect(lambda success, msg, w=worker: self._remove_worker(w))
        worker.signals.error.connect(lambda msg, w=worker: self._remove_worker(w))
        self.thread_pool.start(worker)
        return worker
        
    def extract_cd(self, 
               input_file: str, 
               output_file: str,
               force: bool = False) -> CHDManSignals:
        """Extract a CD image from a CHD file.
        
        Args:
            input_file: Path to the input .chd file
            output_file: Path for the output .cue file
            force: Whether to overwrite existing output file
        
        Returns:
            CHDManSignals object for connecting to signals
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="extractcd",
            input_file=input_file,
            output_file=output_file,
            force=force,
            worker_id=f"extractcd_{id(input_file)}"
        )
        # Track the worker for cleanup
        self.active_workers[worker.worker_id] = worker
        # Connect signals to remove worker from active_workers when done
        worker.signals.finished.connect(lambda success, msg, w=worker: self._remove_worker(w))
        worker.signals.error.connect(lambda msg, w=worker: self._remove_worker(w))
        self.thread_pool.start(worker)
        return worker
        
    def extract_raw(self,
                input_file: str,
                output_file: str,
                force: bool = False) -> CHDManSignals:
        """Extract raw disk image from a CHD file.
        
        Args:
            input_file: Path to the input .chd file
            output_file: Path for the output raw disk image
            force: Whether to overwrite existing output file
        
        Returns:
            CHDManSignals object for connecting to signals
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="extractraw",  # must match the CLI command name
            input_file=input_file,
            output_file=output_file,
            force=force,
            worker_id=f"extractraw_{id(input_file)}"
        )
        # Track the worker for cleanup
        self.active_workers[worker.worker_id] = worker
        # Connect signals to remove worker from active_workers when done
        worker.signals.finished.connect(lambda success, msg, w=worker: self._remove_worker(w))
        worker.signals.error.connect(lambda msg, w=worker: self._remove_worker(w))
        self.thread_pool.start(worker)
        return worker
        
    def _remove_worker(self, worker):
        """Remove a worker from the active_workers dictionary."""
        self.active_workers.pop(worker.worker_id, None)
        print(f"[CHDMan] Worker {worker.worker_id} removed from active workers. {len(self.active_workers)} workers remaining.")

    def _parse_info_output(self, output: str) -> Dict[str, Any]:
        """Parse the output of the 'info' command into a structured format.
        Args:
            output: Output string from CHDMAN info command
        Returns:
            Dictionary containing parsed CHD information
        """
        info = {}
        # Extract key-value pairs from the output
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            # Try to split on colon for key-value pairs
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                info[key] = value
        return info



class CHDTaskType(Enum):
    """Enum for CHD task types.
    
    Attributes:
        COMPRESS: Compress a disk image to CHD format
        EXTRACT_RAW: Extract raw data from CHD
        EXTRACT_CD: Extract CD image from CHD
        EXTRACT_DVD: Extract DVD image from CHD
        EXTRACT_HD: Extract hard disk image from CHD
        EXTRACT_AV: Extract audio/video from CHD
        INFO: Get information about a CHD file
        VERIFY: Verify CHD integrity
        DUMP_META: Dump metadata from CHD
    """
    COMPRESS = auto()
    EXTRACT_RAW = auto()
    EXTRACT_CD = auto()
    EXTRACT_DVD = auto()
    EXTRACT_HD = auto()
    EXTRACT_AV = auto()
    INFO = auto()
    VERIFY = auto()
    DUMP_META = auto()


class CHDTask:
    """Represents a CHD task to be executed.
    
    Attributes:
        task_type: Type of task to execute
        input_file: Path to input file
        output_file: Path to output file (if applicable)
        compression_level: Compression level (none, fast, normal, best)
        hunk_size: Hunk size in bytes
        verify: Whether to verify after operation
        force: Whether to force overwrite of output file
        media_type: Type of media ("CD", "DVD", or "Hard Disk") (optional)
        algorithms: Comma-separated list of compression algorithms (optional)
        user_data: Dictionary of user-defined data associated with the task (optional)
    """
    
    def __init__(
        self,
        task_type: CHDTaskType,
        input_file: str,
        output_file: Optional[str] = None,
        compression_level: Optional[str] = None,
        hunk_size: Optional[int] = None,
        verify: bool = False,
        force: bool = False,
        media_type: Optional[str] = None,
        algorithms: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None
    ):
        """Initialize the CHDTask.
        
        Args:
            task_type: Type of task
            input_file: Path to the input file
            output_file: Path to the output file (optional)
            compression_level: Compression level (optional)
            hunk_size: Hunk size in bytes (optional)
            verify: Whether to verify the CHD after operation
            force: Whether to force the operation
            media_type: Type of media ("CD", "DVD", or "Hard Disk") (optional)
            algorithms: Comma-separated list of compression algorithms (optional)
            user_data: Dictionary of user-defined data to associate with the task (optional)
        """
        self.task_type = task_type
        self.input_file = input_file
        self.output_file = output_file
        self.compression_level = compression_level
        self.hunk_size = hunk_size
        self.verify = verify
        self.force = force
        self.media_type = media_type
        self.algorithms = algorithms
        self.user_data = user_data or {}


class CHDManager(QObject):
    """Manager for CHDMAN operations.
    
    This class provides a high-level interface for CHDMAN operations.
    """
    
    def __init__(self, executable_path: str = "chdman"):
        """Initialize the CHDManager.
        
        Args:
            executable_path: Path to CHDMAN executable
        """
        super().__init__()
        self.executable_path = executable_path
        self.chdman = CHDMan(executable_path)
        self.tasks = []
        self.current_task = None
        self.active_workers = {}  # Track active workers by task ID
        self.thread_pool = QThreadPool()
        self._last_batch_executed_tasks = []  # Track the last batch of executed tasks
        self._paused_tasks = set()  # Track paused task IDs
        self._cancelled_tasks = set()  # Track cancelled task IDs
        self._task_mutex = QMutex()  # For thread-safe task operations
        
        # Initialize signals
        self.signals = CHDManSignals()
        
    def log(self, message):
        """Log a message.
        
        This is a placeholder method that can be overridden by subclasses.
        By default, it just prints to the console.
        """
        print(message)
        
    def terminate_all_chdman_processes(self):
        """Find and terminate all CHDMAN processes running on the system.
        
        This is more aggressive than cleanup() as it will terminate ALL CHDMAN processes,
        not just those started by this instance of the application.
        """
        # Simply delegate to the CHDMan instance for process termination
        print("Delegating CHDMAN process termination to CHDMan instance")
        self.chdman.terminate_all_chdman_processes()
            
    def get_last_executed_tasks_batch(self):
        """Get the last batch of executed tasks.
        
        Returns:
            List of CHDTask objects that were last executed
        """
        return self._last_batch_executed_tasks
            
    def add_task(self, task: CHDTask) -> None:
        """Add a task to the queue.
        
        Args:
            task: Task to add
        """
        self.tasks.append(task)
    
    def clear_tasks(self):
        """Clear all tasks from the queue and reset internal state.
        
        This ensures a clean slate when processing multiple files,
        especially when handling archives with multiple disk images.
        """
        # Clear the task queue
        self.tasks.clear()
        
        # Clear the last batch of executed tasks
        self._last_batch_executed_tasks.clear()
        
        # Reset task counter (used for generating task IDs)
        self._task_counter = 0
        
    def execute_all_tasks(self):
        """Execute all tasks in the queue sequentially.
        
        Returns:
            List of CHDManSignals objects for each task
            
        Raises:
            CHDManExecutableNotFoundError: If CHDMAN executable cannot be found
            CHDManInputFileError: If an input file is invalid or not found
            CHDManOutputFileError: If an output file cannot be created or written to
            CHDManCommandError: If a CHDMAN command fails
        """
        # Clear any existing active workers before starting new tasks
        self.active_workers = {}
        print("CHDManager: execute_all_tasks called")
        if not self.tasks:
            print("CHDManager: No tasks in queue")
            self._last_batch_executed_tasks = []  # Clear the last batch if there are no tasks
            return []
        
        # Find CHDMAN executable
        try:
            chdman_path = self.find_chdman()
            print(f"Found CHDMAN at: {chdman_path}")
        except Exception as e:
            print(f"Error finding CHDMAN: {e}")
            raise
        
        # Validate tasks
        for task in self.tasks:
            if not task.input_file or not os.path.exists(task.input_file):
                raise CHDManInputFileError(f"Input file not found: {task.input_file}")
            
            if not task.output_file:
                raise CHDManOutputFileError("Output file not specified")
            
            output_dir = os.path.dirname(task.output_file)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception as e:
                    raise CHDManOutputFileError(f"Cannot create output directory: {output_dir}. Error: {e}")
        
        # Store the current batch of tasks to be executed
        self._last_batch_executed_tasks = list(self.tasks)  # Make a copy
        
        # Execute tasks
        signals_list = []
        for task in self._last_batch_executed_tasks:  # Iterate the copied list
            self.current_task = task  # Still useful for single-task context if needed
            signals = self.execute_task(task)
            signals_list.append(signals)
        
        return signals_list
    
    def _create_worker_for_task(self, task: CHDTask):
        """Create a worker for the given task.
        
        Args:
            task: The task to create a worker for
            
        Returns:
            CHDManWorker instance configured for the task
        """
        if task.task_type == CHDTaskType.COMPRESS:
            if task.media_type == "CD":
                return self.chdman.create_cd(
                    task.input_file,
                    task.output_file,
                    compression=task.algorithms,
                    hunk_size=task.hunk_size,
                    force=task.force
                )
            elif task.media_type == "DVD":
                return self.chdman.create_dvd(
                    task.input_file,
                    task.output_file,
                    compression=task.algorithms,
                    hunk_size=task.hunk_size,
                    force=task.force
                )
            else:  # HD
                return self.chdman.create_hd(
                    task.input_file,
                    task.output_file,
                    compression=task.algorithms,
                    hunk_size=task.hunk_size,
                    force=task.force
                )
        elif task.task_type == CHDTaskType.EXTRACT_CD:
            return self.chdman.extract_cd(
                task.input_file,
                task.output_file,
                force=task.force
            )
        elif task.task_type == CHDTaskType.EXTRACT_DVD:
            return self.chdman.extract_dvd(
                task.input_file,
                task.output_file,
                force=task.force
            )
        elif task.task_type == CHDTaskType.EXTRACT_HD:
            return self.chdman.extract_hd(
                task.input_file,
                task.output_file,
                force=task.force
            )
        elif task.task_type == CHDTaskType.VERIFY:
            return self.chdman.verify(task.input_file)
        else:
            raise ValueError(f"Unsupported task type: {task.task_type}")
            
    def execute_task(self, task: CHDTask) -> CHDManSignals:
        """Execute a single task.
        
        Args:
            task: Task to execute
            
        Returns:
            CHDManSignals object for connecting to signals
            
        Raises:
            CHDManExecutableNotFoundError: If CHDMAN executable cannot be found
            CHDManInputFileError: If an input file is invalid or not found
            CHDManOutputFileError: If an output file cannot be created or written to
            CHDManCommandError: If a CHDMAN command fails
        """
        with QMutexLocker(self._task_mutex):
            if task in self._cancelled_tasks:
                self._cancelled_tasks.remove(task)
                raise CHDManCommandError("Task was cancelled", 1, "Task was cancelled before execution")
            # Deduplication: prevent duplicate workers for the same task
            import logging
            logger = logging.getLogger(__name__)
            if id(task) in self.active_workers:
                logger.warning(f"Duplicate worker launch prevented for task: {getattr(task, 'input_file', None)} -> {getattr(task, 'output_file', None)}")
                return self.active_workers[id(task)].signals

        # Create and configure worker based on task type
        worker = self._create_worker_for_task(task)
        
        # Store the worker
        with QMutexLocker(self._task_mutex):
            self.active_workers[id(task)] = worker
            
        # Connect signals
        worker.signals.finished.connect(lambda success, msg: self._on_task_finished(task, success, msg))
        worker.signals.error.connect(lambda msg: self._on_task_error(task, msg))
        
        # Start the worker
        self.thread_pool.start(worker)
        
        return worker.signals

    def _on_task_finished(self, task: CHDTask, success: bool, message: str):
        """Handle task completion.
        
        Args:
            task: The completed task
            success: Whether the task completed successfully
            message: Completion message
        """
        with QMutexLocker(self._task_mutex):
            self._cleanup_task(task)
            
    def _on_task_error(self, task: CHDTask, error: str):
        """Handle task errors.
        
        Args:
            task: The failed task
            error: Error message
        """
        with QMutexLocker(self._task_mutex):
            self._cleanup_task(task)
            
    def _cleanup_task(self, task: CHDTask):
        """Clean up resources for a completed task.
        
        Args:
            task: The task to clean up
        """
        if id(task) in self.active_workers:
            del self.active_workers[id(task)]
        if task in self._paused_tasks:
            self._paused_tasks.remove(task)
        if task in self._cancelled_tasks:
            self._cancelled_tasks.remove(task)
                    
    def find_chdman(self) -> str:
        """Find CHDMAN executable in bin directory or PATH.
        
        Returns:
            Path to CHDMAN executable
            
        Raises:
            CHDManExecutableNotFoundError: If CHDMAN executable cannot be found
        """
        # First, check in the bin directory
        bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
        print(f"Looking for CHDMAN in bin directory: {bin_dir}")
        
        if os.name == "nt":
            chdman_path = os.path.join(bin_dir, "chdman.exe")
        else:
            chdman_path = os.path.join(bin_dir, "chdman")
        
        print(f"Checking for CHDMAN at: {chdman_path}")
        print(f"File exists: {os.path.exists(chdman_path)}")
        
        if os.path.exists(chdman_path):
            if os.name == "nt":
                # On Windows, we can't easily check execute permissions
                print(f"Found CHDMAN at: {chdman_path}")
                return chdman_path
            else:
                # On Unix-like systems, check execute permissions
                has_exec = os.access(chdman_path, os.X_OK)
                print(f"Has execute permission: {has_exec}")
                if has_exec:
                    return chdman_path
            
        # If not found in bin directory, check PATH
        try:
            # Try to run 'chdman' with --help to check if it's in PATH
            result = subprocess.run(["chdman", "--help"], capture_output=True, text=True, check=False)
            if result.returncode == 0 or "CHDMAN" in result.stdout:
                return "chdman"  # Return just the command name if found in PATH
        except FileNotFoundError:
            # Not in PATH, continue with search
            pass
            
        # Check common installation directories
        common_dirs = []
        if os.name == "nt":
            # Windows common directories
            program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
            common_dirs = [
                os.path.join(program_files, "MAME"),
                os.path.join(program_files_x86, "MAME"),
                "C:\\MAME"
            ]
        else:
            # Linux/macOS common directories
            common_dirs = [
                "/usr/local/bin",
                "/usr/bin",
                "/opt/mame",
                os.path.expanduser("~/mame")
            ]
            
        for directory in common_dirs:
            if os.name == "nt":
                check_path = os.path.join(directory, "chdman.exe")
            else:
                check_path = os.path.join(directory, "chdman")
                
            if os.path.exists(check_path) and os.access(check_path, os.X_OK):
                return check_path
                
        # If we get here, CHDMAN was not found
        raise CHDManExecutableNotFoundError(
            "CHDMAN executable not found. Please install CHDMAN and place it in the bin directory, "
            "or ensure it's in your system PATH."
        )
    
    def get_chdman_version(self, executable_path: str) -> Optional[str]:
        """Get the CHDMAN version.
        
        Args:
            executable_path: Path to CHDMAN executable
            
        Returns:
            CHDMAN version string or None if not found
        """
        try:
            # Run CHDMAN to get version
            result = subprocess.run(
                [executable_path, "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            
            if result.returncode == 0:
                # Parse version from output
                output = result.stdout
                match = re.search(r"CHDMAN\s+([\d.]+)", output)
                if match:
                    return match.group(1)
        except Exception:
            pass
        
        return None
        
    def get_active_tasks_count(self):
        """Get the number of active tasks.
        
        Returns:
            Number of active tasks currently being processed
        """
        # Count the active workers in the CHDMan instance
        active_count = len(self.chdman.active_workers)
        print(f"[CHDManager] Active workers count: {active_count}")
        return active_count
    
    def pause_task(self, task: CHDTask) -> bool:
        """Pause a running task.
        
        Args:
            task: The task to pause
            
        Returns:
            bool: True if the task was paused, False otherwise
        """
        with QMutexLocker(self._task_mutex):
            if id(task) not in self.active_workers:
                return False
                
            # Mark task as paused
            self._paused_tasks.add(task)
            
            # Get the worker and pause it
            worker = self.active_workers[id(task)]
            if hasattr(worker, 'pause'):
                worker.pause()
                return True
                
        return False
        
    def resume_task(self, task: CHDTask) -> bool:
        """Resume a paused task.
        
        Args:
            task: The task to resume
            
        Returns:
            bool: True if the task was resumed, False otherwise
        """
        with QMutexLocker(self._task_mutex):
            if task not in self._paused_tasks:
                return False
                
            # Remove from paused set
            self._paused_tasks.remove(task)
            
            # Get the worker and resume it
            if id(task) in self.active_workers:
                worker = self.active_workers[id(task)]
                if hasattr(worker, 'resume'):
                    worker.resume()
                    return True
                    
        return False
        
    def cancel_task(self, task: CHDTask) -> bool:
        """Cancel a running or queued task.
        
        Args:
            task: The task to cancel
            
        Returns:
            bool: True if the task was cancelled, False otherwise
        """
        with QMutexLocker(self._task_mutex):
            # Mark task as cancelled
            self._cancelled_tasks.add(task)
            
            # If task is active, terminate it
            if id(task) in self.active_workers:
                worker = self.active_workers[id(task)]
                if hasattr(worker, 'terminate'):
                    worker.terminate()
                    self._cleanup_task(task)
                    return True
                    
        return False
        
    def get_task_status(self, task: CHDTask) -> str:
        """Get the status of a task.
        
        Args:
            task: The task to check
            
        Returns:
            str: Task status ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled')
        """
        with QMutexLocker(self._task_mutex):
            if task in self._cancelled_tasks:
                return 'cancelled'
            elif task in self._paused_tasks:
                return 'paused'
            elif id(task) in self.active_workers:
                return 'running'
            elif task in self.tasks:
                return 'pending'
            else:
                return 'completed'  # Assuming if it's not in any other state and not in tasks
                
    def cleanup(self):
        """Terminate all running CHDMAN processes started by this instance.
        
        This should be called when the application is closing to ensure
        all CHDMAN processes are properly terminated.
        """
        with QMutexLocker(self._task_mutex):
            # Cancel all active tasks
            for task_id in list(self.active_workers.keys()):
                task = next((t for t in self.tasks if id(t) == task_id), None)
                if task:
                    self.cancel_task(task)
                    
            # Clear all task lists
            self.tasks.clear()
            self.active_workers.clear()
            self._paused_tasks.clear()
            self._cancelled_tasks.clear()
            
        # Clean up CHDMAN
        self.chdman.cleanup()
        
        # Clear the task queue
        self.tasks.clear()
        self.current_task = None
        self.log("CHDManager task queue cleared.")

# --- Singleton accessor for CHDManager ---
_chd_manager_singleton = None

def get_chd_manager():
    """Return the singleton CHDManager instance initialized with the correct path."""
    global _chd_manager_singleton
    if _chd_manager_singleton is None:
        chdman_path = load_chdman_path()
        if not chdman_path:
            chdman_path = "chdman"
        _chd_manager_singleton = CHDManager(executable_path=chdman_path)
    return _chd_manager_singleton
