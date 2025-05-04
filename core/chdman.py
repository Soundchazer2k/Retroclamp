"""CHDMAN wrapper module for RetroClamp.

This module provides a Pythonic interface to the CHDMAN command-line utility,
allowing for compression, extraction, verification, and information retrieval
operations on CHD files with proper progress reporting and error handling.
"""

import os
import sys
import subprocess
import re
import shlex
from enum import Enum, auto
from typing import Dict, List, Optional, Union, Callable, Tuple, Any
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool


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
    """
    started = Signal(str)  # Command description
    progress = Signal(float, str)  # Progress percentage, message
    finished = Signal(bool, str)  # Success flag, output message
    error = Signal(str)  # Error message


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
        self.signals = CHDManSignals()
        self.process = None
        self.cancelled = False
        
    @Slot()
    def run(self):
        """Execute the CHDMAN command.
        
        This method is called when the worker is started by the thread pool.
        It builds the command, executes it, and monitors the progress.
        """
        try:
            # Build command
            cmd = [self.executable_path, self.command]
            
            # Add input file
            cmd.extend(["-i", self.input_file])
            
            # Add output file if specified
            if self.output_file:
                cmd.extend(["-o", self.output_file])
                
            # Add compression if specified and supported
            if self.compression:
                cmd.extend(["-c", self.compression])
                
            # Add hunk size if specified
            if self.hunk_size:
                cmd.extend(["-hs", str(self.hunk_size)])
                
            # Add force flag if specified
            if self.force:
                cmd.append("-f")
                
            # Add verbose flag if specified
            if self.verbose:
                cmd.append("-v")
                
            # Add additional parameters
            for key, value in self.kwargs.items():
                if value is not None:
                    cmd.extend([f"-{key}", str(value)])
            
            # Emit started signal
            self.signals.started.emit(f"Running {self.command} on {os.path.basename(self.input_file)}")
            
            # Start process
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor progress
            for line in iter(self.process.stdout.readline, ""):
                if self.cancelled:
                    self.process.terminate()
                    self.signals.error.emit("Operation cancelled by user")
                    return
                    
                # Parse progress information
                progress = self._parse_progress(line)
                if progress is not None:
                    self.signals.progress.emit(progress, line.strip())
                elif line.strip():  # Only emit non-empty lines
                    self.signals.progress.emit(-1, line.strip())  # -1 indicates no progress value
                
            # Wait for process to complete
            return_code = self.process.wait()
            
            if return_code == 0:
                self.signals.finished.emit(True, "Operation completed successfully")
            else:
                error_output = self.process.stderr.read()
                self.signals.error.emit(f"Process failed with code {return_code}: {error_output}")
                
        except Exception as e:
            self.signals.error.emit(f"Error executing CHDMAN command: {str(e)}")
    
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
        
        # Pattern: "Compressing, 45.3% complete..." (createcd, createdvd, etc.)
        match = re.search(r'(\d+(\.\d+)?)% complete', line)
        if match:
            return float(match.group(1))
            
        # Pattern: "Block 1000/2000" (extractcd, extractdvd, etc.)
        match = re.search(r'Block (\d+)/(\d+)', line)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            if total > 0:
                return (current / total) * 100
                
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
    
    def __init__(self, executable_path: str = "chdman"):
        """Initialize the CHDMan wrapper.
        
        Args:
            executable_path: Path to the CHDMAN executable
        """
        self.executable_path = executable_path
        self.thread_pool = QThreadPool()
        
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
            
        if compression and compression not in self.COMPRESSION_ALGORITHMS:
            raise ValueError(f"Invalid compression algorithm: {compression}")
            
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="createcd",
            input_file=input_file,
            output_file=output_file,
            compression=compression,
            hunk_size=hunk_size,
            force=force
        )
        
        self.thread_pool.start(worker)
        return worker.signals
        
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
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        if compression and compression not in self.COMPRESSION_ALGORITHMS:
            raise ValueError(f"Invalid compression algorithm: {compression}")
            
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="createdvd",
            input_file=input_file,
            output_file=output_file,
            compression=compression,
            hunk_size=hunk_size,
            force=force
        )
        
        self.thread_pool.start(worker)
        return worker.signals
        
    def create_hd(self, 
                  input_file: str, 
                  output_file: str, 
                  compression: Optional[str] = None,
                  hunk_size: Optional[int] = None,
                  force: bool = False) -> CHDManSignals:
        """Create a CHD file from a hard disk image.
        
        Args:
            input_file: Path to the input raw disk image
            output_file: Path for the output .chd file
            compression: Compression algorithm(s) to use
            hunk_size: Size of data hunks in bytes
            force: Whether to overwrite existing output file
            
        Returns:
            CHDManSignals object for connecting to signals
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        if compression and compression not in self.COMPRESSION_ALGORITHMS:
            raise ValueError(f"Invalid compression algorithm: {compression}")
            
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="createhd",
            input_file=input_file,
            output_file=output_file,
            compression=compression,
            hunk_size=hunk_size,
            force=force
        )
        
        self.thread_pool.start(worker)
        return worker.signals
        
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
            force=force
        )
        
        self.thread_pool.start(worker)
        return worker.signals
        
    def extract_dvd(self, 
                    input_file: str, 
                    output_file: str,
                    force: bool = False) -> CHDManSignals:
        """Extract a DVD image from a CHD file.
        
        Args:
            input_file: Path to the input .chd file
            output_file: Path for the output .iso file
            force: Whether to overwrite existing output file
            
        Returns:
            CHDManSignals object for connecting to signals
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="extractdvd",
            input_file=input_file,
            output_file=output_file,
            force=force
        )
        
        self.thread_pool.start(worker)
        return worker.signals
        
    def extract_hd(self, 
                   input_file: str, 
                   output_file: str,
                   force: bool = False) -> CHDManSignals:
        """Extract a hard disk image from a CHD file.
        
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
            command="extracthd",
            input_file=input_file,
            output_file=output_file,
            force=force
        )
        
        self.thread_pool.start(worker)
        return worker.signals
        
    def info(self, input_file: str) -> CHDManSignals:
        """Display information about a CHD file.
        
        Args:
            input_file: Path to the input .chd file
            
        Returns:
            CHDManSignals object for connecting to signals
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="info",
            input_file=input_file
        )
        
        self.thread_pool.start(worker)
        return worker.signals
        
    def verify(self, input_file: str) -> CHDManSignals:
        """Verify the integrity of a CHD file.
        
        Args:
            input_file: Path to the input .chd file
            
        Returns:
            CHDManSignals object for connecting to signals
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        worker = CHDManWorker(
            executable_path=self.executable_path,
            command="verify",
            input_file=input_file
        )
        
        self.thread_pool.start(worker)
        return worker.signals
        
    def parse_info_output(self, output: str) -> Dict[str, Any]:
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


# CHDTaskType and related classes are defined below


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
    """
    
    def __init__(self, 
                 task_type: CHDTaskType,
                 input_file: str,
                 output_file: Optional[str] = None,
                 compression_level: str = "normal",
                 hunk_size: int = 16384,
                 verify: bool = True,
                 force: bool = False):
        """Initialize the CHDTask.
        
        Args:
            task_type: Type of task to execute
            input_file: Path to input file
            output_file: Path to output file (if applicable)
            compression_level: Compression level (none, fast, normal, best)
            hunk_size: Hunk size in bytes
            verify: Whether to verify after operation
            force: Whether to force overwrite of output file
        """
        self.task_type = task_type
        self.input_file = input_file
        self.output_file = output_file
        self.compression_level = compression_level
        self.hunk_size = hunk_size
        self.verify = verify
        self.force = force


class CHDManager:
    """Manager for CHD operations.
    
    This class provides a high-level interface for managing CHD tasks,
    including task queuing, execution, and progress tracking.
    """
    
    def __init__(self, executable_path: str = "chdman"):
        """Initialize the CHDManager.
        
        Args:
            executable_path: Path to the CHDMAN executable
        """
        self.chdman = CHDMan(executable_path)
        self.tasks = []
        self.current_task = None
        self.thread_pool = QThreadPool()
    
    def add_task(self, task: CHDTask) -> None:
        """Add a task to the queue.
        
        Args:
            task: Task to add
        """
        self.tasks.append(task)
    
    def clear_tasks(self) -> None:
        """Clear all tasks from the queue."""
        self.tasks.clear()
    
    def execute_task(self, task: CHDTask) -> CHDManSignals:
        """Execute a single task.
        
        Args:
            task: Task to execute
            
        Returns:
            CHDManSignals object for connecting to signals
        """
        self.current_task = task
        
        # Map task type to CHDMAN command
        if task.task_type == CHDTaskType.COMPRESS:
            # Determine compression method based on file extension
            ext = os.path.splitext(task.input_file)[1].lower()
            if ext in [".iso", ".bin", ".img"]:
                # Map compression level to algorithm
                compression = None
                if task.compression_level == "none":
                    compression = "none"
                elif task.compression_level == "fast":
                    compression = "zlib"
                elif task.compression_level == "normal":
                    compression = "zlib,zstd"
                elif task.compression_level == "best":
                    compression = "zlib,lzma"
                
                return self.chdman.create_cd(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    compression=compression,
                    hunk_size=task.hunk_size,
                    force=task.force
                )
            else:
                # Default to CD for other formats
                return self.chdman.create_cd(
                    input_file=task.input_file,
                    output_file=task.output_file,
                    compression=None,
                    hunk_size=task.hunk_size,
                    force=task.force
                )
        elif task.task_type == CHDTaskType.EXTRACT_RAW:
            return self.chdman.extract_raw(
                input_file=task.input_file,
                output_file=task.output_file,
                force=task.force
            )
        elif task.task_type == CHDTaskType.EXTRACT_CD:
            return self.chdman.extract_cd(
                input_file=task.input_file,
                output_file=task.output_file,
                force=task.force
            )
        elif task.task_type == CHDTaskType.EXTRACT_DVD:
            return self.chdman.extract_dvd(
                input_file=task.input_file,
                output_file=task.output_file,
                force=task.force
            )
        elif task.task_type == CHDTaskType.EXTRACT_HD:
            return self.chdman.extract_hd(
                input_file=task.input_file,
                output_file=task.output_file,
                force=task.force
            )
        elif task.task_type == CHDTaskType.INFO:
            return self.chdman.info(task.input_file)
        elif task.task_type == CHDTaskType.VERIFY:
            return self.chdman.verify(task.input_file)
        else:
            # Unsupported task type
            signals = CHDManSignals()
            signals.error.emit(f"Unsupported task type: {task.task_type}")
            return signals
    
    def execute_all_tasks(self) -> List[CHDManSignals]:
        """Execute all tasks in the queue sequentially.
        
        Returns:
            List of CHDManSignals objects for each task
        """
        if not self.tasks:
            return []
            
        # Find CHDMAN executable if not already set
        if self.chdman.executable_path == "chdman":
            chdman_path = self.find_chdman()
            if chdman_path:
                self.chdman.executable_path = chdman_path
            else:
                raise FileNotFoundError("CHDMAN executable not found. Please install CHDMAN and try again.")
        
        # Execute tasks sequentially
        signals_list = []
        for task in self.tasks:
            self.current_task = task
            signals = self.execute_task(task)
            signals_list.append(signals)
            
        return signals_list
    
    def find_chdman(self) -> Optional[str]:
        """Find the CHDMAN executable.
        
        Returns:
            Path to CHDMAN executable or None if not found
        """
        # Check if the executable path is already set and exists
        if os.path.exists(self.chdman.executable_path) and self.chdman.executable_path != "chdman":
            return self.chdman.executable_path
        
        # Check in the bin directory relative to the application
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bin_dir = os.path.join(app_dir, "bin")
        
        # Check for chdman.exe (Windows) or chdman (Unix)
        chdman_candidates = [
            os.path.join(bin_dir, "chdman.exe"),
            os.path.join(bin_dir, "chdman")
        ]
        
        for candidate in chdman_candidates:
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return candidate
        
        # Try to find chdman in the PATH
        try:
            if sys.platform == "win32":
                result = subprocess.run(["where", "chdman"], capture_output=True, text=True, check=True)
            else:  # Unix-like systems
                result = subprocess.run(["which", "chdman"], capture_output=True, text=True, check=True)
            
            chdman_path = result.stdout.strip().split('\n')[0]
            if os.path.exists(chdman_path):
                return chdman_path
        except subprocess.CalledProcessError:
            pass
            
        return None
    
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
