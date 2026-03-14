"""Batch processing for RetroClamp.

This module provides functionality for processing multiple CHD operations in batch,
with support for pausing, resuming, and tracking progress of operations.
"""

import json

from core.debug_logger import DebugLogger

debug_logger = DebugLogger(module_name="core.batch_processor")
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import (
    QMutexLocker,
    QObject,
    QRecursiveMutex,
    QRunnable,
    QThreadPool,
    QTimer,
    Signal,
    Slot,
)

from .chdman import CHDManager, CHDTask, CHDTaskType


class BatchTaskStatus(Enum):
    """Status of a batch task."""

    PENDING = auto()  # Task is queued but not started
    RUNNING = auto()  # Task is currently being processed
    PAUSED = auto()  # Task is paused
    COMPLETED = auto()  # Task completed successfully
    FAILED = auto()  # Task failed with an error
    SKIPPED = auto()  # Task was skipped (e.g., file exists and overwrite=False)
    CANCELLED = auto()  # Task was cancelled by the user


@dataclass
class BatchItem:
    """Represents an item in a batch operation.

    Attributes:
        input_path: Path to the input file or directory
        output_path: Path where the output CHD will be saved
        media_type: Type of media ('cd', 'dvd', 'hd', 'ld')
        compression: Compression algorithm(s) to use
        hunk_size: Size of data hunks in bytes (optional)
        status: Current status of the batch item
        progress: Progress percentage (0-100)
        error: Error message if the task failed
        verify: Whether to verify the output after creation
        overwrite: Whether to overwrite existing output files
        metadata: Additional metadata for the task
        retry_count: Number of retry attempts made
        max_retries: Maximum number of retry attempts
        start_time: Timestamp when processing started
        end_time: Timestamp when processing completed/failed
        bytes_processed: Number of bytes processed so far
        total_bytes: Total number of bytes to process
    """

    input_path: str
    output_path: str
    media_type: str
    compression: str
    hunk_size: Optional[int] = None
    status: BatchTaskStatus = BatchTaskStatus.PENDING
    progress: float = 0.0
    error: Optional[str] = None
    verify: bool = True
    overwrite: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    bytes_processed: int = 0
    total_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert the batch item to a dictionary for serialization."""
        data = asdict(self)
        data["status"] = self.status.name
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchItem":
        """Create a BatchItem from a dictionary with proper type conversion.

        Args:
            data: Dictionary containing the batch item data

        Returns:
            BatchItem: A new BatchItem instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Make a copy to avoid modifying the input
        item_data = data.copy()

        # Convert status string to BatchTaskStatus if needed
        if "status" in item_data and isinstance(item_data["status"], str):
            try:
                item_data["status"] = BatchTaskStatus[item_data["status"]]
            except KeyError:
                debug_logger.warning(
                    "core.batch_processor",
                    f"Invalid status value: {item_data['status']}, "
                    f"defaulting to PENDING",
                )
                item_data["status"] = BatchTaskStatus.PENDING

        # Ensure required fields are present
        required_fields = ["input_path", "output_path", "media_type", "compression"]
        missing = [field for field in required_fields if field not in item_data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # Convert numeric fields to the correct type
        numeric_fields = {
            "hunk_size": int,
            "retry_count": int,
            "max_retries": int,
            "bytes_processed": int,
            "total_bytes": int,
            "progress": float,
        }

        for field_name, field_type in numeric_fields.items():
            if field_name in item_data and item_data[field_name] is not None:
                try:
                    item_data[field_name] = field_type(item_data[field_name])
                except (ValueError, TypeError):
                    debug_logger.warning(
                        "core.batch_processor",
                        f"Invalid {field_name} value: {item_data[field_name]}, "
                        f"defaulting to 0",
                    )
                    item_data[field_name] = field_type(0)

        # Handle boolean fields
        boolean_fields = ["verify", "overwrite"]
        for field_name in boolean_fields:
            if field_name in item_data and not isinstance(item_data[field_name], bool):
                item_data[field_name] = str(item_data[field_name]).lower() in (
                    "true",
                    "1",
                    "t",
                    "y",
                    "yes",
                )

        # Create the BatchItem instance with the processed data
        return cls(**item_data)


class BatchSignals(QObject):
    """Signals for batch operations.

    These signals are used to communicate between the batch processor and the UI.
    """

    # General batch lifecycle signals
    started = Signal()  # Emitted when the batch processing starts
    finished = (
        Signal()
    )  # Emitted when the entire batch processing finishes (successfully or not)
    paused = Signal()  # Emitted when batch processing is paused
    resumed = Signal()  # Emitted when batch processing is resumed
    cancelled = Signal()  # Emitted when batch processing is cancelled by the user

    # Overall progress and status signals
    progress_updated = Signal(
        int, int, object
    )  # current_item_index, total_items, current_item_progress (BatchItem or dict)
    error_occurred = Signal(str)  # Generic error message for the batch
    state_saved = Signal(str)  # file_path where state was saved
    state_loaded = Signal(str)  # file_path from where state was loaded

    # Individual item signals
    item_added = Signal(object)  # BatchItem that was added
    item_started = Signal(object)  # BatchItem that started processing
    item_progress = Signal(
        object, object
    )  # BatchItem, progress_details (e.g., percentage or specific task progress)
    item_completed = Signal(object)  # BatchItem that completed successfully
    item_failed = Signal(object, str)  # BatchItem, error_message
    item_skipped = Signal(object, str)  # BatchItem, reason_message
    item_updated = Signal(object)  # BatchItem whose status/details were updated

    # New signals to address Mypy errors
    item_processed = Signal(
        object
    )  # Emits BatchItem after it's processed (completed, failed, or skipped)
    batch_progress = Signal(
        float, int, int
    )  # Overall batch: percentage, items_done, items_total
    batch_finished = Signal(bool, str)  # Overall batch: success (bool), message (str)
    log_message = Signal(str, str)  # message (str), level (str, e.g., 'INFO', 'ERROR')
    cleared = Signal()  # Emitted when the batch queue is cleared


class BatchProcessor(QObject):
    class WorkerSignals(QObject):
        progress = Signal(float, int)  # percent, item index
        finished = Signal(bool, str, int)  # success, msg, item index
        error = Signal(str, int)  # error msg, item index

    class BatchWorker(QRunnable):
        def __init__(self, chd_manager, item, index):
            super().__init__()
            self.chd_manager = chd_manager
            self.item = item
            self.index = index
            self.signals = BatchProcessor.WorkerSignals()
            self._is_cancelled = False

        def run(self):
            try:
                from .chdman import CHDTask, CHDTaskType

                task = CHDTask(
                    task_type=(
                        CHDTaskType.COMPRESS
                        if self.item.media_type
                        else CHDTaskType.EXTRACT
                    ),
                    input_file=self.item.input_path,
                    output_file=self.item.output_path,
                    force=True,
                )
                self.chd_manager.tasks = [task]

                def on_progress(percent, msg, _):
                    self.signals.progress.emit(percent, self.index)

                self.chd_manager.signals.progress_updated.connect(on_progress)
                self.chd_manager.execute_all_tasks()
                self.chd_manager.signals.progress_updated.disconnect(on_progress)
                self.signals.finished.emit(True, "Done", self.index)
            except Exception as e:
                self.signals.error.emit(str(e), self.index)
                self.signals.finished.emit(False, f"Failed: {e}", self.index)

    """Manages batch processing of CHD operations with support for pausing, resuming,
    and tracking progress.

    This class handles the queueing, processing, and tracking of batch operations for
    compressing and extracting disk images using CHDMAN.
    """

    def __init__(self, chd_manager: CHDManager):
        """Initialize the batch processor.

        Args:
            chd_manager: Instance of CHDManager to use for CHD operations
        """
        super().__init__()
        self.chd_manager = chd_manager
        self.items: List[BatchItem] = []
        self.current_index = 0
        self.is_paused = False
        self.is_running = False
        self.signals = BatchSignals()
        self.mutex = QRecursiveMutex()  # Allows the same thread to re-acquire the lock
        debug_logger.debug(
            "core.batch_processor",
            "BatchProcessor: Using QRecursiveMutex for re-entrant locking",
        )
        self.current_task: Optional[CHDTask] = None
        self._abort_requested = False
        self._batch_start_time: Optional[float] = None
        self._total_bytes_processed: int = 0
        self._total_bytes: int = 0

        # Parallel batch processing additions
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(2)
        self._active_workers: List[Any] = []

        # Connect CHD manager signals
        self.chd_manager.signals.progress_updated.connect(self._on_chd_progress)
        self.chd_manager.signals.task_completed.connect(self._on_chd_completed)
        self.chd_manager.signals.error_occurred.connect(self._on_chd_error)

    def start(self):
        """Start processing the batch in parallel."""
        if self.is_running:
            return False
        self.is_running = True
        self._abort_requested = False
        self._batch_start_time = time.time()
        self._finished_count = 0

        class WorkerSignals(QObject):
            progress = Signal(float, int)  # percent, item index
            finished = Signal(bool, str, int)  # success, msg, item index
            error = Signal(str, int)  # error msg, item index

        class BatchWorker(QRunnable):
            def __init__(self, chd_manager, item: BatchItem, index: int):
                super().__init__()
                self.chd_manager = chd_manager
                self.item = item
                self.index = index
                self.signals = WorkerSignals()
                self._is_cancelled = False

            def run(self):
                try:
                    from .chdman import CHDTask, CHDTaskType

                    task = CHDTask(
                        task_type=(
                            CHDTaskType.COMPRESS
                            if self.item.media_type
                            else CHDTaskType.EXTRACT
                        ),
                        input_file=self.item.input_path,
                        output_file=self.item.output_path,
                        force=True,
                    )
                    self.chd_manager.tasks = [task]

                    def on_progress(percent, msg, _):
                        self.signals.progress.emit(percent, self.index)

                    self.chd_manager.signals.progress_updated.connect(on_progress)
                    self.chd_manager.execute_all_tasks()
                    self.chd_manager.signals.progress_updated.disconnect(on_progress)
                    self.signals.finished.emit(True, "Done", self.index)
                except Exception as e:
                    self.signals.error.emit(str(e), self.index)
                    self.signals.finished.emit(False, f"Failed: {e}", self.index)

        # Start workers for all pending items
        for idx, item in enumerate(self.items):
            if item.status in (
                BatchTaskStatus.COMPLETED,
                BatchTaskStatus.SKIPPED,
                BatchTaskStatus.CANCELLED,
            ):
                continue
            worker = BatchWorker(self.chd_manager, item, idx)
            worker.signals.progress.connect(self._on_worker_progress)
            worker.signals.finished.connect(self._on_worker_finished)
            worker.signals.error.connect(self._on_worker_error)
            self._active_workers.append(worker)
            self._thread_pool.start(worker)
        self.signals.started.emit()
        return True

    def _on_worker_progress(self, percent, idx):
        item = self.items[idx]
        item.progress = percent
        item.status = BatchTaskStatus.RUNNING
        self.signals.item_progress.emit(item, percent)
        self._emit_overall_progress()

    def __len__(self) -> int:
        """Return the number of items in the batch."""
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            return len(self.items)

    def add_item(
        self,
        input_path: str,
        output_path: str,
        media_type: str,
        compression: str,
        hunk_size: Optional[int] = None,
        verify: bool = True,
        overwrite: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BatchItem:
        """Add an item to the batch queue.

        Args:
            input_path: Path to the input file or directory
            output_path: Path for the output CHD file
            media_type: Type of media ('cd', 'dvd', 'hd', 'ld')
            compression: Compression algorithm(s) to use
            hunk_size: Size of data hunks in bytes (optional)
            verify: Whether to verify the output after creation
            overwrite: Whether to overwrite existing output files
            metadata: Additional metadata for the task

        Returns:
            BatchItem: The created batch item

        Raises:
            ValueError: If input or output paths are invalid
        """
        # Validate paths
        input_path = os.path.abspath(input_path)
        output_path = os.path.abspath(output_path)

        if not os.path.exists(input_path):
            raise ValueError(f"Input path does not exist: {input_path}")

        if not output_path.strip():
            raise ValueError("Output path cannot be empty")

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Failed to create output directory: {e}") from e

        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            # Check for duplicates
            for item in self.items:
                if os.path.normcase(
                    os.path.abspath(item.input_path)
                ) == os.path.normcase(os.path.abspath(input_path)):
                    raise ValueError(f"Duplicate input path: {input_path}")

            item = BatchItem(
                input_path=input_path,
                output_path=output_path,
                media_type=media_type.lower(),
                compression=compression,
                hunk_size=hunk_size,
                verify=verify,
                overwrite=overwrite,
                metadata=metadata or {},
            )
            self.items.append(item)
            self.signals.item_added.emit(item)
            return item

    def add_items(self, items: List[Dict[str, Any]]) -> List[BatchItem]:
        """Add multiple items to the batch.

        Args:
            items: List of item dictionaries with keys matching BatchItem fields

        Returns:
            List[BatchItem]: List of created batch items

        Raises:
            ValueError: If any item is invalid
        """
        added_items = []
        for item_data in items:
            try:
                item = self.add_item(**item_data)
                added_items.append(item)
            except Exception:
                debug_logger.error(
                    "core.batch_processor",
                    f"Failed to add item {item_data}",
                )
                raise ValueError("Invalid item") from None
        return added_items

    def remove_item(self, index: int) -> bool:
        """Remove an item from the batch by index.

        Args:
            index: Index of the item to remove

        Returns:
            bool: True if item was removed, False if index is invalid
        """
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if 0 <= index < len(self.items):
                del self.items[index]
                if index < self.current_index:
                    self.current_index -= 1
                return True
            return False

    def clear(self) -> None:
        """Clear all items from the batch.

        This will cancel any in-progress operations and remove all items
        from the batch queue. It also resets the progress indicators.
        """
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            self.items.clear()
            self.current_index = 0
            self._batch_start_time = None
            self.signals.cleared.emit()

    def pause(self) -> bool:
        """Pause the batch processing.

        Returns:
            bool: True if processing was paused, False if not running or already paused
        """
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if not self.is_running or self.is_paused:
                return False
            self.is_paused = True
            self.signals.paused.emit()
            # Note: CHDManager does not support pausing individual tasks.
            # The batch pause flag prevents starting new tasks; the current
            # in-flight task will complete normally.
            debug_logger.info("core.batch_processor", "Batch processing paused")
            return True

    @Slot(float, str)
    def _on_progress(self, progress: float, message: str) -> None:
        """Handle progress updates from current task."""
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if not self.is_running or self.current_index >= len(self.items):
                return
            item = self.items[self.current_index]
            item.progress = progress
            self.signals.item_progress.emit(
                self.current_index, progress, f"Processing: {message}"
            )

    @Slot(bool, str)
    def _on_finished(self, success: bool, message: str) -> None:
        """Handle task completion."""
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if not self.is_running or self.current_index >= len(self.items):
                return
            item = self.items[self.current_index]
            if success:
                item.status = BatchTaskStatus.COMPLETED
                item.progress = 100.0
                self.signals.item_completed.emit(item)
            else:
                item.status = BatchTaskStatus.FAILED
                item.error = message
                self.signals.item_failed.emit(self.current_index, message)
            # Move to next item
            self.current_index += 1
            self.current_task = None
            QTimer.singleShot(0, self._process_next_item)

    @Slot(str)
    def _on_error(self, error_message: str) -> None:
        """Handle task errors."""
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if not self.is_running or self.current_index >= len(self.items):
                return
            item = self.items[self.current_index]
            self._fail_item(item, error_message)

    def _process_next_item(self) -> None:
        """Process the next item in the batch queue with retry logic."""
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            # Initialize batch timing on first item
            if self.current_index == 0 and self._batch_start_time is None:
                self._batch_start_time = time.time()
                self._total_bytes_processed = 0
                self._total_bytes = sum(
                    item.total_bytes for item in self.items if item.total_bytes > 0
                )
            # Check if we should stop processing
            if not self.is_running or self._abort_requested or self.is_paused:
                return
            # Check if we've processed all items
            if self.current_index >= len(self.items):
                self._finish_processing()
                return
            # Get the current item
            item = self.items[self.current_index]
            # Set start time for this item
            item.start_time = time.time()
            item.end_time = None
            # Skip already completed items unless forced
            if item.status == BatchTaskStatus.COMPLETED and not item.overwrite:
                self._skip_item(item, "Already completed")
                return
            # Check if output file exists
            if os.path.exists(item.output_path):
                if not item.overwrite:
                    self._skip_item(
                        item, "Output file exists and overwrite is disabled"
                    )
                    return
                try:
                    os.remove(item.output_path)
                except OSError as e:
                    self._fail_item(item, f"Failed to remove existing output file: {e}")
                    return
            # Update item status
            item.status = BatchTaskStatus.RUNNING
            item.progress = 0
            item.error = None
            self.signals.item_started.emit(item)
            try:
                # All compression tasks use the COMPRESS task type
                # The media type is passed as a parameter to the task
                task_type = CHDTaskType.COMPRESS
                # Create the CHD task
                self.current_task = CHDTask(
                    task_type=task_type,
                    input_file=item.input_path,
                    output_file=item.output_path,
                    compression_level=item.compression,
                    hunk_size=item.hunk_size,
                    verify=item.verify,
                    force=item.overwrite,
                    user_data={"batch_index": self.current_index},
                )
                # Start the task and wire up per-task signal callbacks
                signals, _worker = self.chd_manager.initiate_task_and_get_signals(
                    self.current_task
                )
                signals.progress.connect(self._on_progress)
                signals.finished.connect(self._on_finished)
                signals.error.connect(self._on_error)
            except Exception as e:
                self._fail_item(item, f"Failed to start task: {e}")

    def _finish_processing(self) -> None:
        """Clean up after all items have been processed."""
        self.is_running = False
        self.current_task = None
        self.signals.finished.emit()
        debug_logger.info("core.batch_processor", "Batch processing completed")

    def _skip_item(self, item: BatchItem, reason: str) -> None:
        """Skip processing an item with the given reason."""
        item.status = BatchTaskStatus.SKIPPED
        item.progress = 0
        self.signals.item_skipped.emit(item, reason)
        debug_logger.info(
            "core.batch_processor", f"Skipped item {item.input_path}: {reason}"
        )

        # Move to next item
        self.current_index += 1
        QTimer.singleShot(0, self._process_next_item)

    def _fail_item(self, item: BatchItem, error: str) -> None:
        """Handle item failure with retry logic."""
        item.retry_count += 1
        item.end_time = time.time()

        if item.retry_count < item.max_retries:
            # Retry the item
            retry_delay = 2**item.retry_count  # Exponential backoff
            debug_logger.warning(
                "core.batch_processor",
                f"Retry {item.retry_count}/{item.max_retries} for {item.input_path} "
                f"after {retry_delay}s: {error}",
            )
            # Update status to indicate retry
            item.status = BatchTaskStatus.PENDING
            item.error = f"Retry {item.retry_count}/{item.max_retries}: {error}"
            # Schedule retry
            QTimer.singleShot(retry_delay * 1000, lambda: self._process_next_item())
        else:
            # Mark as failed
            item.status = BatchTaskStatus.FAILED
            item.error = error
            self.signals.item_failed.emit(self.current_index, error)
            # Move to next item
            self.current_index += 1
            QTimer.singleShot(0, self._process_next_item)
            self.signals.item_progress.emit(item, None)
            debug_logger.error(
                "core.batch_processor",
                f"Failed to process {item.input_path}: {item.error}",
            )
            # Move to next item
            self.current_index += 1
            QTimer.singleShot(0, self._process_next_item)

    @Slot(int, float, str)
    def _on_chd_progress(self, task_id: int, progress: float, message: str) -> None:
        """Handle progress updates from CHD tasks with enhanced progress tracking.

        Args:
            task_id: ID of the CHD task
            progress: Progress percentage (0-100)
            message: Status message
        """
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if not self.is_running or self.current_index >= len(self.items):
                return
            item = self.items[self.current_index]
            if item.status != BatchTaskStatus.RUNNING:
                return
            # Update item progress
            item.progress = progress
            # Update bytes processed if available in message
            if "bytes" in message.lower():
                try:
                    parts = message.split()
                    for i, part in enumerate(parts):
                        if part == "bytes":
                            # Get the new bytes processed value
                            new_bytes_processed = int(parts[i - 1].replace(",", ""))

                            # Calculate the delta from the previous value
                            delta = new_bytes_processed - item.bytes_processed

                            # Only update if we have a positive delta
                            # to avoid negative values
                            if delta > 0 and hasattr(self, "_total_bytes_processed"):
                                self._total_bytes_processed += delta

                            # Update the item's bytes_processed
                            item.bytes_processed = new_bytes_processed
                            break
                except (ValueError, IndexError) as e:
                    debug_logger.warning(
                        "core.batch_processor", f"Error parsing bytes from message: {e}"
                    )
                    pass

            # Emit progress with additional context
            time_remaining = self.get_estimated_time_remaining()
            self.signals.item_progress.emit(item, time_remaining)

            # Emit overall progress
            total_items = len(self.items)
            self.signals.progress_updated.emit(
                self.current_index + 1, total_items, time_remaining
            )

    @Slot(int, bool, str)
    def _on_chd_completed(self, task_id: int, success: bool, message: str) -> None:
        """Handle completion of a CHD task.

        Args:
            task_id: ID of the completed task
            success: Whether the task completed successfully
            message: Completion message
        """
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if not self.is_running or self.current_index >= len(self.items):
                return
            item = self.items[self.current_index]
            self.current_task = None
            if success:
                item.status = BatchTaskStatus.COMPLETED
                item.progress = 100.0
                item.end_time = time.time()

                # Only update bytes_processed if it wasn't set during progress updates
                if item.bytes_processed <= 0 and item.total_bytes > 0:
                    item.bytes_processed = item.total_bytes
                    if hasattr(self, "_total_bytes_processed"):
                        self._total_bytes_processed += item.bytes_processed

                self.signals.item_completed.emit(item)
                debug_logger.info(
                    "core.batch_processor", f"Completed processing {item.input_path}"
                )

                # Move to next item
                self.current_index += 1

                # Check if this was the last item
                if self.current_index >= len(self.items):
                    self.is_running = False
                    self.signals.finished.emit()
                    debug_logger.info(
                        "core.batch_processor", "Batch processing completed"
                    )
                else:
                    QTimer.singleShot(0, self._process_next_item)
            else:
                self._fail_item(item, f"Task failed: {message}")

    @Slot(int, str)
    def _on_chd_error(self, task_id: int, error: str) -> None:
        """Handle errors from CHD tasks.

        Args:
            task_id: ID of the task that failed
            error: Error message
        """
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if not self.is_running or self.current_index >= len(self.items):
                return
            item = self.items[self.current_index]
            self._fail_item(item, f"CHD error: {error}")

    def get_progress(self) -> float:
        """Get overall batch progress.

        Returns:
            float: Progress percentage (0-100)
        """
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if not self.items:
                return 0.0
            total = len(self.items)
            if total == 0:
                return 100.0
            # Count completed items
            completed = sum(
                1 for item in self.items if item.status == BatchTaskStatus.COMPLETED
            )
            # Add progress of current item if processing
            current_progress = 0.0
            if (
                self.is_running
                and not self.is_paused
                and 0 <= self.current_index < len(self.items)
            ):
                current_item = self.items[self.current_index]
                if current_item.status == BatchTaskStatus.RUNNING:
                    current_progress = current_item.progress / 100.0
                elif current_item.status == BatchTaskStatus.COMPLETED:
                    current_progress = 1.0

            # Calculate overall percentage
            percentage = ((completed + current_progress) / total) * 100.0
            return min(100.0, max(0.0, percentage))

    def get_current_item(self) -> Optional[BatchItem]:
        """Get the currently processing item.

        Returns:
            Optional[BatchItem]: The current batch item, or None if not processing
        """
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if 0 <= self.current_index < len(self.items):
                return self.items[self.current_index]
            return None

    def get_estimated_time_remaining(self) -> Optional[float]:
        """Get estimated time remaining for the batch operation.

        Returns:
            Optional[float]: Estimated time remaining in seconds, or None if not
            enough data
        """
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if not hasattr(self, "_batch_start_time") or not self._batch_start_time:
                return None

            elapsed = time.time() - self._batch_start_time
            if not self._total_bytes_processed or not self._total_bytes:
                return None

            progress = self._total_bytes_processed / self._total_bytes
            if progress <= 0:
                return None

            total_estimated = elapsed / progress
            return max(0, total_estimated - elapsed)

    def _prepare_state_dict(self) -> Dict[str, Any]:
        """Prepare the state dictionary for serialization.

        Returns:
            Dict containing the serialized state
        """
        return {
            "metadata": {
                "version": "1.1",  # Bump version for new format
                "timestamp": time.time(),
                "current_index": self.current_index,
                "is_paused": self.is_paused,
                "is_running": self.is_running,
                "start_time": self._batch_start_time,
                "total_bytes_processed": self._total_bytes_processed,
                "total_bytes": self._total_bytes,
                "python_version": sys.version,
                "platform": sys.platform,
            },
            "items": self._serialize_batch_items(),
        }

    def _serialize_batch_items(self) -> List[Dict[str, Any]]:
        """Serialize batch items to a list of dictionaries.

        Returns:
            List of serialized batch items
        """
        items_dict = []
        try:
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Attempting to acquire mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            with QMutexLocker(self.mutex):
                debug_logger.debug(
                    "core.batch_processor",
                    f"[BatchProcessor] Acquired mutex in "
                    f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                )
                for item in self.items:
                    try:
                        item_dict = item.to_dict()
                        item_dict["status"] = item.status.name
                        items_dict.append(item_dict)
                    except Exception as e:
                        debug_logger.exception(
                            "core.batch_processor",
                            f"Error serializing batch item: {e}",
                        )
                        continue
        except Exception:
            debug_logger.error(
                "core.batch_processor",
                "Unexpected error during batch item serialization",
            )
            raise
        return items_dict

    def _write_state_to_file(self, file_path: str, state: Dict[str, Any]) -> bool:
        """Write state to file with atomic write and checksum verification.

        Args:
            file_path: Path to save the state file
            state: State dictionary to save

        Returns:
            bool: True if write was successful, False otherwise
        """
        import hashlib
        import os

        temp_file = f"{file_path}.{os.getpid()}.tmp"

        try:
            # Create a checksum of the state
            state_json = json.dumps(state, indent=2, sort_keys=True)
            checksum = hashlib.sha256(state_json.encode("utf-8")).hexdigest()
            state["_checksum"] = checksum

            # Write to temporary file
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())

            # Verify the written file exists and has correct size
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                raise OSError("Failed to write temporary state file or file is empty")

            # Verify checksum
            with open(temp_file, encoding="utf-8") as f:
                saved_state = json.load(f)
                if saved_state.get("_checksum") != checksum:
                    raise ValueError("Checksum verification failed")

            # Atomic rename (works on POSIX and recent Windows)
            try:
                if os.path.exists(file_path):
                    os.replace(temp_file, file_path)
                else:
                    os.rename(temp_file, file_path)
            except OSError:
                # Fallback for Windows if rename fails due to file in use
                if os.name == "nt":
                    try:
                        os.remove(file_path)
                        os.rename(temp_file, file_path)
                    except Exception as fallback_error:
                        raise OSError(
                            f"Failed to replace state file: {fallback_error}"
                        ) from fallback_error
                else:
                    raise

            debug_logger.info(
                "core.batch_processor",
                f"Successfully saved state to {file_path}",
            )
            return True

        except Exception:
            debug_logger.error(
                "core.batch_processor",
                f"Failed to write state to {file_path}",
            )
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as cleanup_error:
                    debug_logger.error(
                        "core.batch_processor",
                        f"Failed to clean up temp file: {cleanup_error}",
                    )
            return False

    def _notify_state_saved(self, file_path: str) -> None:
        """Notify listeners that state was saved.

        Args:
            file_path: Path to the saved state file
        """

        from PySide6.QtCore import QCoreApplication, QTimer

        def emit_signal():
            try:
                self.signals.state_saved.emit(file_path)
            except Exception as e:
                debug_logger.error(
                    "core.batch_processor",
                    f"Error emitting state_saved signal: {e}",
                    exc_info=True,
                )

        app = QCoreApplication.instance()
        if app is None:
            debug_logger.warning(
                "core.batch_processor",
                "No QApplication instance, signal not emitted",
            )
        elif app.thread() != self.thread():
            QTimer.singleShot(0, emit_signal)
        else:
            emit_signal()

    def save_state(self, file_path: str) -> bool:
        """Save the current batch state to a file with improved error handling
        and checksum.

        This method saves the current state of the batch processor to a JSON file with
        the following features:
        - Atomic write operation using a temporary file
        - Checksum verification to detect corruption
        - Thread-safe access to shared resources
        - Detailed error logging
        - Progress tracking

        Args:
            file_path: Path where to save the state file. The directory will be
                     created if it doesn't exist.

        Returns:
            bool: True if state was saved successfully, False otherwise

        Raises:
            ValueError: If file_path is invalid
            OSError: If there's an issue with file system operations
        """
        import os

        # Validate file path
        if not file_path or not isinstance(file_path, str):
            error_msg = f"Invalid file path: {file_path}"
            debug_logger.error("core.batch_processor", error_msg)
            self.signals.error_occurred.emit(error_msg)
            return False

        # Prevent reentrancy issues
        if hasattr(self, "_saving_state") and self._saving_state:
            warning_msg = (
                "[save_state] Already saving state, ignoring concurrent request"
            )
            debug_logger.warning("core.batch_processor", warning_msg)
            self.signals.error_occurred.emit(warning_msg)
            return False

        self._saving_state: bool = True

        try:
            # Create directory if it doesn't exist
            try:
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            except OSError as e:
                error_msg = f"Failed to create directory for state file: {e}"
                debug_logger.error("core.batch_processor", error_msg)
                self.signals.error_occurred.emit(error_msg)
                return False

            # Prepare state dictionary
            try:
                state = self._prepare_state_dict()
            except Exception as e:
                error_msg = f"Failed to prepare state dictionary: {e}"
                debug_logger.error("core.batch_processor", error_msg)
                self.signals.error_occurred.emit(error_msg)
                return False

            # Write state to file
            if not self._write_state_to_file(file_path, state):
                error_msg = f"Failed to write state to {file_path}"
                debug_logger.error("core.batch_processor", error_msg)
                self.signals.error_occurred.emit(error_msg)
                return False

            # Notify listeners
            self._notify_state_saved(file_path)
            return True

        except Exception as e:
            error_msg = f"Unexpected error saving state: {e}"
            debug_logger.error("core.batch_processor", error_msg)
            self.signals.error_occurred.emit(error_msg)
            return False
        finally:
            # Clean up the saving state flag
            if hasattr(self, "_saving_state"):
                del self._saving_state

    def get_overall_progress(self) -> Tuple[int, int, float, Optional[float]]:
        """Get the overall progress of the batch.

        Returns:
            Tuple[int, int, float, Optional[float]]:
                (current_item_index, total_items, percentage_complete,
                time_remaining_seconds)
        """
        debug_logger.debug(
            "core.batch_processor",
            f"[BatchProcessor] Attempting to acquire mutex in "
            f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
        )
        with QMutexLocker(self.mutex):
            debug_logger.debug(
                "core.batch_processor",
                f"[BatchProcessor] Acquired mutex in "
                f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            )
            if not self.items:
                return 0, 0, 0.0, None
            total_items = len(self.items)
            if total_items == 0:
                return 0, 0, 0.0, None
            # Calculate overall progress
            total_progress = sum(item.progress for item in self.items)
            avg_progress = total_progress / total_items
            # Get time remaining
            time_remaining = self.get_estimated_time_remaining()
            return self.current_index, total_items, avg_progress, time_remaining
