# RetroClamp Application Architecture - Enhanced

This document provides a comprehensive overview of the RetroClamp application's architecture, focusing on the sophisticated threading model, signal systems, and advanced features discovered through code analysis.

## Table of Contents

- [High-Level Overview](#high-level-overview)
- [Core Architecture Patterns](#core-architecture-patterns)
- [Threading and Concurrency Model](#threading-and-concurrency-model)
- [Signal/Slot Communication System](#signalslot-communication-system)
- [Core Components Deep Dive](#core-components-deep-dive)
- [Error Handling Strategy](#error-handling-strategy)
- [State Management and Persistence](#state-management-and-persistence)
- [Performance Optimizations](#performance-optimizations)
- [Extensibility Points](#extensibility-points)

## High-Level Overview

RetroClamp is a sophisticated desktop application built with Python and PySide6 (Qt6) that provides a comprehensive interface for CHDMAN operations. The application excels in:

- **Parallel CHD Processing**: Multiple concurrent operations with real-time progress tracking
- **Advanced Archive Handling**: Seamless integration of archive extraction with CHD operations
- **Intelligent Batch Processing**: Resume-capable batch operations with checkpoint management
- **Console-Specific Optimization**: Tailored compression profiles for different gaming systems

## Core Architecture Patterns

### 1. **Worker-Manager Pattern**
```
CHDManager → CHDManWorker (QRunnable)
ArchiveManager → ArchiveWorker (QRunnable)
BatchProcessor → BatchWorker (QRunnable)
```

### 2. **Signal-Driven Communication**
- Asynchronous operation reporting through Qt signals
- Decoupled UI updates from background processing
- Progress tracking with ETA calculations

### 3. **Singleton Pattern with Thread Safety**
```python
# CHDManager singleton with proper locking
_chd_manager_singleton = None
_singleton_lock = threading.Lock()
```

## Threading and Concurrency Model

### **Multi-Level Threading Architecture**

#### **Level 1: QThreadPool Management**
- **CHDMan**: Manages CHD operation workers
- **ArchiveManager**: Handles archive extraction/compression
- **BatchProcessor**: Coordinates batch operations
- **FileScanner**: Performs directory scanning

#### **Level 2: Process Execution**
```python
# Dual execution paths in CHDManWorker
def _execute_and_monitor_process(self, cmd: List[str]):
    # subprocess.Popen for detailed monitoring

def _execute_with_qprocess(self, cmd: List[str]):
    # QProcess for Qt-integrated execution
```

#### **Level 3: Stream Monitoring**
```python
# Real-time stdout/stderr monitoring
stdout_thread = threading.Thread(target=read_stream_local)
stderr_thread = threading.Thread(target=read_stream_local)
```

### **Concurrency Features**
- **Worker Deduplication**: Prevents duplicate operations on same files
- **Graceful Cancellation**: Proper cleanup of running processes
- **Resource Management**: Automatic worker cleanup on completion
- **Thread-Safe Progress Tracking**: Mutex-protected state updates

## Signal/Slot Communication System

### **Hierarchical Signal Architecture**

#### **CHDManSignals (Core Operations)**
```python
started = Signal(str)                    # Operation start
progress = Signal(float, str)            # Real-time progress
finished = Signal(bool, str)             # Completion status
error = Signal(str)                      # Error reporting
progress_updated = Signal(float, str, str)  # Enhanced progress
task_completed = Signal(str, bool, str)  # Task-level completion
```

#### **BatchSignals (Batch Operations)**
```python
# Batch-level coordination
started, finished, paused, resumed, cancelled = ...
progress_updated = Signal(int, int, object)  # Progress with ETA

# Item-level tracking
item_started, item_progress, item_completed = ...
item_failed, item_skipped, item_updated = ...
```

#### **ArchiveSignals (Archive Operations)**
```python
started = Signal(str)
progress = Signal(float, str)
finished = Signal(bool, str, str)        # Success, message, output_path
error = Signal(str)
```

### **Advanced Signal Features**
- **ETA Calculation**: Real-time time remaining estimates
- **Progress Aggregation**: Batch-level progress from individual items
- **Error Propagation**: Detailed error context through signal chains
- **State Change Notifications**: Automatic UI synchronization

## Core Components Deep Dive

### **1. CHDMan/CHDManWorker System**

#### **Sophisticated Process Management**
```python
# Pre-flight validation pipeline
def _perform_pre_flight_checks(self):
    # 1. Executable validation
    # 2. Input file verification
    # 3. Output directory creation
    # 4. Permission testing
    # 5. Parameter validation
```

#### **Intelligent Progress Parsing**
```python
# Multiple progress pattern recognition
def _parse_progress(self, line: str):
    # Handles: "Progress: 23%", "Block 1/100", "sector 50/1000"
    # Provides fallback parsing for various CHDMAN output formats
```

#### **Compression Algorithm Validation**
```python
VALID_COMPRESSION_ALGORITHMS = [
    "none", "zlib", "zstd", "lzma", "huff",
    "flac", "cdlz", "cdzl", "cdfl", "avhu"
]
COMPRESSION_CORRECTIONS = {"cdzlib": "cdzl", "cdflac": "cdfl"}
```

### **2. Advanced Batch Processing**

#### **Retry Logic with Exponential Backoff**
```python
def _fail_item(self, item: BatchItem, error: str):
    if item.retry_count < item.max_retries:
        retry_delay = 2**item.retry_count  # Exponential backoff
        QTimer.singleShot(retry_delay * 1000, self._process_next_item)
```

#### **Checkpoint System**
```python
@dataclass
class BatchItem:
    # Comprehensive state tracking
    status: BatchTaskStatus
    progress: float
    retry_count: int
    start_time, end_time: Optional[float]
    bytes_processed, total_bytes: int
```

#### **Thread-Safe State Management**
```python
# Recursive mutex for re-entrant operations
self.mutex = QRecursiveMutex()
# Consistent mutex usage patterns throughout
with QMutexLocker(self.mutex):
    # Critical sections properly protected
```

### **3. Console-Specific Intelligence**

#### **Smart Profile Selection**
```python
# Console detection from filename and file size
def detect_console_type(self, file_path: str) -> str:
    # Extension analysis + heuristic size checking
    # Supports: PS1, PS2, PSP, Saturn, Dreamcast, etc.
```

#### **Optimized Compression Profiles**
```python
# Console-specific hunk sizes and algorithms
"ps1": algorithms="cdlz,cdzl,cdfl", hunk_size=2352*4    # 4 CD sectors
"ps2": algorithms="lzma", hunk_size=2048               # DVD optimization
"dreamcast": hunk_size=2352*8                          # 8 CD sectors
```

### **4. Robust Archive Integration**

#### **Multi-Format Support**
- **ZIP**: Native zipfile with password support
- **7Z**: py7zr integration with progress tracking
- **RAR/TAR/etc**: patoolib fallback for exotic formats

#### **Smart Extraction Logic**
```python
def _extract(self):
    # Skip if already extracted and contains disk images
    if os.path.exists(self.output_path):
        disk_images = file_scanner.find_disk_images(self.output_path)
        if disk_images:
            # Skip extraction, use existing files
```

## Error Handling Strategy

### **Multi-Level Error Handling**

#### **1. Validation Layer**
- Pre-flight checks prevent common errors
- Input sanitization and path validation
- Resource availability verification

#### **2. Execution Layer**
- Subprocess error capture and interpretation
- Stream monitoring for runtime errors
- Graceful process termination

#### **3. Recovery Layer**
- Automatic retry with exponential backoff
- Checkpoint-based recovery
- User-friendly error messages

### **Custom Exception Hierarchy**
```python
CHDManError (Base)
├── CHDManExecutableNotFoundError
├── CHDManCommandError
├── CHDManInputFileError
└── CHDManOutputFileError
```

## State Management and Persistence

### **Checkpoint System Architecture**

#### **Atomic State Operations**
```python
def _write_state_to_file(self, file_path: str, state: Dict[str, Any]):
    # Atomic write with checksum verification
    # Temporary file + atomic rename pattern
    # Corruption detection and recovery
```

#### **Versioned State Format**
```python
checkpoint = {
    "version": self.VERSION,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "current_index": current_index,
    "metadata": {...},
    "_checksum": hashlib.sha256(state_json.encode()).hexdigest()
}
```

## Performance Optimizations

### **1. Parallel Processing**
- QThreadPool-based concurrent operations
- Configurable thread limits
- Worker deduplication prevents resource waste

### **2. Progress Optimization**
- Real-time ETA calculations
- Byte-level progress tracking
- Efficient UI update throttling

### **3. Memory Management**
- Stream-based file processing
- Automatic cleanup of temporary resources
- Path object usage for efficient file operations

### **4. Smart Caching**
- Archive extraction result caching
- File scanner result reuse
- Profile recommendation memoization

## Extensibility Points

### **1. New Archive Formats**
```python
# Add to ArchiveWorker._extract()
elif ext == ".new_format":
    self._extract_new_format()
```

### **2. Additional Console Profiles**
```python
# Extend console_profiles.py
profiles["new_console"] = {
    "optimal": ConsoleProfile(...)
}
```

### **3. Custom Compression Algorithms**
```python
# Add to CHDManWorker.VALID_COMPRESSION_ALGORITHMS
# Implement validation in _sanitize_compression_algorithms
```

### **4. Enhanced Progress Parsing**
```python
# Extend CHDManWorker._parse_progress()
# Add new pattern recognition for different tools
```

## Advanced Features

### **1. Real-Time Monitoring**
- Live process output parsing
- Dynamic ETA calculation
- Resource usage tracking

### **2. Intelligent File Handling**
- Automatic media type detection
- Console-specific optimization
- Smart output path generation

### **3. Robust Error Recovery**
- Multi-level retry mechanisms
- Graceful degradation
- User intervention points

### **4. Professional Logging**
- Comprehensive debug logging
- Error context preservation
- Performance metrics tracking

---

*This enhanced documentation reflects the sophisticated architecture discovered through detailed code analysis. The threading model, signal systems, and error handling represent production-quality software engineering practices.*
