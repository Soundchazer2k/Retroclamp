"""Enhanced test for BatchProcessor with better timeout handling."""
import pytest
import logging
import os
import sys
import time
from typing import Optional, List, Dict, Tuple, Any
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY
import json
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QMutex, QCoreApplication, QTimer, QEventLoop

# Set up logging with file handler
log_dir = Path("logs")
try:
    log_dir.mkdir(exist_ok=True, parents=True)
    log_file = log_dir / f"test_batch_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Ensure we can write to the log file
    with open(log_file, 'w') as f:
        f.write("Test log started\n")
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Log file created at: {log_file.absolute()}")
except Exception as e:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to create log file: {e}")
    logger.info("Falling back to console logging only")

# Create a formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set up file handler
file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Set up console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler],
    force=True
)

# Get logger for this module
logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info("STARTING TEST SESSION")
logger.info("=" * 80)

# Try to import the BatchProcessor and related classes
try:
    from core.batch_processor import BatchProcessor, BatchItem, BatchTaskStatus
    from core.chdman import CHDManager, CHDTask
    BATCH_PROCESSOR_AVAILABLE = True
    logger.info("BatchProcessor imported successfully")
except ImportError as e:
    BATCH_PROCESSOR_AVAILABLE = False
    logger.error(f"Failed to import BatchProcessor: {e}", exc_info=True)
    logger.warning("BatchProcessor not available. Some tests will be skipped.")

# Add the project root to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.absolute()))

class MockSignals(QObject):
    """Mock signals for testing."""
    # Batch-level signals
    started = Signal()
    finished = Signal()
    paused = Signal()
    resumed = Signal()
    cancelled = Signal()
    progress_updated = Signal(int, int, object)  # current, total, time_remaining
    error_occurred = Signal(str)
    state_saved = Signal(str)
    state_loaded = Signal(str)
    
    # Task-level signals (used by BatchProcessor)
    task_completed = Signal(object)        # task_id
    task_failed = Signal(object, str)      # task_id, error
    task_progress = Signal(object, int)    # task_id, progress
    task_started = Signal(object)          # task_id
    task_skipped = Signal(object, str)     # task_id, reason
    
    # Item-level signals
    item_added = Signal(object)            # BatchItem
    item_started = Signal(object)          # BatchItem
    item_progress = Signal(object, object) # BatchItem, time_remaining
    item_completed = Signal(object)        # BatchItem
    item_failed = Signal(object, str)      # BatchItem, error
    item_skipped = Signal(object, str)     # BatchItem, reason
    item_updated = Signal(object)          # BatchItem
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Connect all signals to no-op slots to avoid warnings
        for signal_name in dir(self):
            if signal_name.startswith('_') or signal_name in ('deleteLater', 'destroyed'):
                continue
            signal = getattr(self, signal_name)
            if hasattr(signal, 'connect'):
                signal.connect(lambda *args, **kwargs: None)

class MockCHDManager(QObject):
    """Mock CHD manager for testing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = MockSignals()
        self.is_running = False
        self.tasks = {}
        self._setup_connections()
    
    def _setup_connections(self):
        """Set up signal connections."""
        # Connect all signals to log their emissions
        for signal_name in dir(self.signals):
            if signal_name.startswith('_') or signal_name in ('deleteLater', 'destroyed'):
                continue
            signal = getattr(self.signals, signal_name)
            if hasattr(signal, 'connect'):
                signal.connect(
                    lambda *args, sig=signal_name: 
                    logger.debug(f"Signal emitted: {sig} with args: {args}")
                )
    
    def save_state(self, file_path):
        """Mock save state implementation."""
        logger.info(f"MockCHDManager.save_state called with: {file_path}")
        try:
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write test state data
            with open(file_path, 'w') as f:
                f.write("{\"test\": \"mock state data\"}")
            
            logger.info(f"State saved to {file_path}")
            self.signals.state_saved.emit(file_path)
            return True
        except Exception as e:
            error_msg = f"Error saving state: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.signals.error_occurred.emit(error_msg)
            return False
    
    def load_state(self, file_path):
        """Mock load state implementation."""
        logger.info(f"MockCHDManager.load_state called with: {file_path}")
        try:
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                logger.error(error_msg)
                self.signals.error_occurred.emit(error_msg)
                return False
                
            # Read the file to verify it's accessible
            with open(file_path, 'r') as f:
                content = f.read()
                logger.debug(f"Loaded state content: {content[:100]}...")
            
            self.signals.state_loaded.emit(file_path)
            return True
        except Exception as e:
            error_msg = f"Error loading state: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.signals.error_occurred.emit(error_msg)
            return False

class TestBatchProcessorEnhanced:
    """Enhanced test for BatchProcessor with better timeout handling."""
    
    @pytest.fixture(autouse=True)
    def setup(self, qtbot):
        """Setup test environment."""
        self.qtbot = qtbot
        self.mock_chd_manager = MockCHDManager()
        self.processor = BatchProcessor(self.mock_chd_manager)
        
        # Create a temporary directory for test files
        self.temp_dir = Path("test_temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Create a test input file
        self.test_input = self.temp_dir / "test_input.bin"
        with open(self.test_input, 'wb') as f:
            f.write(b'test data' * 1000)  # Make it a bit larger
            
        self.test_output = self.temp_dir / "test_output.chd"
        self.state_file = self.temp_dir / "batch_processor_state.json"
        
        yield
        
        # Cleanup
        if self.test_input.exists():
            self.test_input.unlink()
        if self.test_output.exists():
            self.test_output.unlink()
        if self.state_file.exists():
            self.state_file.unlink()
        if self.temp_dir.exists():
            self.temp_dir.rmdir()
    
    def wait_for_signal(self, signal, timeout=5000):
        """Wait for a signal to be emitted with a timeout."""
        # Create event loop and timer in the main thread
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        
        # Use a mutable object to store the result
        result = {'received': False, 'args': None}
        
        def on_signal(*args):
            logger.debug(f"Signal received: {signal} with args: {args}")
            result['received'] = True
            result['args'] = args if len(args) > 1 else (args[0] if args else None)
            if loop.isRunning():
                loop.quit()
        
        # Connect the signal
        signal.connect(on_signal)
        
        # Set up timeout
        def on_timeout():
            logger.warning(f"Timeout waiting for signal {signal}")
            if loop.isRunning():
                loop.quit()
        
        timer.timeout.connect(on_timeout)
        timer.start(timeout)
        
        # Process events until signal or timeout
        loop.exec_()
        
        # Clean up
        timer.stop()
        try:
            signal.disconnect(on_signal)
        except (TypeError, RuntimeError):
            pass  # Signal was never connected or already disconnected
            
        logger.debug(f"Signal wait completed. Received: {result['received']}")
        return result['received'], result['args']

    @pytest.mark.skipif(not BATCH_PROCESSOR_AVAILABLE, reason="BatchProcessor not available")
    def test_save_load_cycle(self, qtbot, tmp_path):
        """Test saving and loading batch processor state."""
        logger.info("\n" + "="*80)
        logger.info("STARTING TEST: test_save_load_cycle")
        logger.info("="*80 + "\n")
        
        # Track signals
        class SignalTracker:
            def __init__(self):
                self.save_complete = False
                self.load_complete = False
                self.save_file = None
                self.load_file = None
                self.save_errors = []
                self.load_errors = []
            
            def on_state_saved(self, file_path):
                try:
                    self.save_complete = True
                    self.save_file = file_path
                    logger.info(f"[TRACKER] State saved signal received for: {file_path}")
                except Exception as e:
                    self.save_errors.append(f"Error in on_state_saved: {e}")
                    logger.error(f"[TRACKER] Error in on_state_saved: {e}")
            
            def on_state_loaded(self, file_path):
                try:
                    self.load_complete = True
                    self.load_file = file_path
                    logger.info(f"[TRACKER] State loaded signal received for: {file_path}")
                except Exception as e:
                    self.load_errors.append(f"Error in on_state_loaded: {e}")
                    logger.error(f"[TRACKER] Error in on_state_loaded: {e}")
        
        tracker = SignalTracker()
        
        # Disconnect any existing connections to avoid duplicates
        try:
            self.processor.signals.state_saved.disconnect()
            self.processor.signals.state_loaded.disconnect()
        except (TypeError, RuntimeError):
            pass  # No connections to disconnect
            
        # Connect our signal handlers
        self.processor.signals.state_saved.connect(tracker.on_state_saved)
        
        # Add a test item to the processor
        logger.info("\n" + "-"*40)
        logger.info("Adding test item to processor")
        logger.info("-"*40)
        
        try:
            # Create test input file if it doesn't exist
            self.test_input.parent.mkdir(parents=True, exist_ok=True)
            if not self.test_input.exists():
                self.test_input.write_bytes(b"TEST" * 1024)  # 4KB test file
                
            item = self.processor.add_item(
                input_path=str(self.test_input.absolute()),
                output_path=str(self.test_output.absolute()),
                media_type="cd",
                compression="zlib",
                hunk_size=2048,
                verify=True,
                overwrite=False
            )
            logger.info(f"Added item: {item}")
            
            # Set some state to verify after reload
            item.retry_count = 2
            item.max_retries = 5
            item.status = BatchTaskStatus.PENDING
            item.progress = 25.0
            
            # Set processor state
            self.processor.current_index = 0
            self.processor.is_paused = False
            self.processor.is_running = True
            
            # Save state
            logger.info("\n" + "-"*40)
            logger.info("Saving processor state")
            logger.info("-"*40)
            
            # Reset tracker state
            tracker.save_complete = False
            tracker.save_file = None
            tracker.save_errors = []
            
            # Save state with enhanced error handling and debugging
            save_success = False
            try:
                # Log processor state
                logger.info("\n" + "*"*80)
                logger.info("DEBUG: Processor state before save:")
                logger.info(f"- Items: {len(self.processor.items) if hasattr(self.processor, 'items') else 'N/A'}")
                logger.info(f"- Current index: {getattr(self.processor, 'current_index', 'N/A')}")
                logger.info(f"- Is running: {getattr(self.processor, 'is_running', 'N/A')}")
                logger.info(f"- Is paused: {getattr(self.processor, 'is_paused', 'N/A')}")
                
                # Verify items are serializable
                if hasattr(self.processor, 'items') and self.processor.items:
                    logger.info("\nVerifying item serialization:")
                    for i, item in enumerate(self.processor.items):
                        try:
                            item_dict = item.to_dict()
                            json.dumps(item_dict)  # Test serialization
                            logger.info(f"- Item {i} serialized successfully")
                        except Exception as e:
                            logger.error(f"- Item {i} failed to serialize: {e}", exc_info=True)
                            logger.error(f"Item type: {type(item)}")
                            logger.error(f"Item dir: {dir(item)}")
                            raise
                logger.info("*"*80 + "\n")
                
                # Check mutex status before saving
                logger.info("\n" + "*"*80)
                logger.info("DEBUG: Mutex status before save:")
                try:
                    mutex_locked = self.processor.mutex.tryLock(100)  # Try to lock with short timeout
                    logger.info(f"- Mutex initially {'locked' if not mutex_locked else 'unlocked'}")
                    if mutex_locked:
                        self.processor.mutex.unlock()
                except Exception as e:
                    logger.error(f"Error checking mutex: {e}", exc_info=True)
                logger.info("*"*80 + "\n")
                
                # Call save_state with detailed error handling
                logger.info(f"Calling save_state with: {self.state_file}")
                try:
                    save_success = self.processor.save_state(str(self.state_file.absolute()))
                    logger.info(f"save_state returned: {save_success}")
                    
                    if not save_success:
                        # Additional diagnostics for failed save
                        logger.error("\n" + "!"*80)
                        logger.error("SAVE_STATE FAILED - POSSIBLE CAUSES:")
                        logger.error("1. Mutex could not be acquired (check for deadlocks)")
                        logger.error("2. File permission issues (check if directory is writable)")
                        logger.error("3. Serialization error (check logs above)")
                        logger.error("!"*80 + "\n")
                        
                        # Check if file was created despite the failure
                        if self.state_file.exists():
                            logger.warning(f"File was created but save_state returned False. Size: {self.state_file.stat().st_size} bytes")
                            try:
                                with open(self.state_file, 'r') as f:
                                    content = f.read(500)  # Read first 500 chars
                                    logger.info(f"File content (first 500 chars):\n{content}")
                            except Exception as e:
                                logger.error(f"Failed to read state file: {e}")
                except Exception as e:
                    logger.error(f"Exception in save_state: {e}", exc_info=True)
                    save_success = False
                
                # Debug: Check if signals are connected and their state
                logger.info("\n" + "*"*80)
                logger.info("DEBUG: Signal connections and state:")
                try:
                    # Check signal receivers
                    receivers = self.processor.signals.state_saved.receivers
                    logger.info(f"- state_saved receivers: {len(receivers) if receivers else 0}")
                    
                    # Check signal connection status
                    is_connected = self.processor.signals.state_saved.isSignalConnected(
                        self.processor.signals.state_saved.state_saved
                    )
                    logger.info(f"- state_saved is connected: {is_connected}")
                    
                    # Check if signal is connected to our slot
                    slot_connected = False
                    for receiver in receivers or []:
                        try:
                            if getattr(receiver, '__self__', None) == tracker:
                                slot_connected = True
                                break
                        except:
                            continue
                    logger.info(f"- Connected to our tracker: {slot_connected}")
                    
                except Exception as e:
                    logger.error(f"Error checking signal receivers: {e}", exc_info=True)
                logger.info("*"*80 + "\n")
                
                # Add a small delay to ensure any async operations complete
                import time
                time.sleep(0.5)
                QCoreApplication.processEvents()
                
                # Wait for save to complete with timeout
                logger.info("Waiting for state_saved signal...")
                signal_received = self.wait_for_signal(
                    self.processor.signals.state_saved, 
                    timeout=5000  # 5 second timeout
                )
                
                # Process any pending events
                QCoreApplication.processEvents()
                
                logger.info(f"Signal received: {signal_received}")
                logger.info(f"Save complete: {tracker.save_complete}")
                logger.info(f"Save file exists: {self.state_file.exists()}")
                
                if not signal_received or not tracker.save_complete:
                    error_msg = [
                        "Save operation failed:",
                        f"- Signal received: {signal_received}",
                        f"- Save complete: {tracker.save_complete}",
                        f"- Save file exists: {self.state_file.exists()}",
                        f"- Save errors: {tracker.save_errors or 'None'}",
                        f"- File size: {self.state_file.stat().st_size if self.state_file.exists() else 0} bytes"
                    ]
                    
                    if self.state_file.exists():
                        try:
                            with open(self.state_file, 'r') as f:
                                content = f.read(1000)  # Read first 1000 chars
                                error_msg.append(f"File content (first 1000 chars):\n{content}")
                        except Exception as e:
                            error_msg.append(f"Failed to read state file: {e}")
                    
                    logger.error("\n".join(error_msg))
                    assert False, "Save operation failed. See logs for details."
                
                # Verify save result
                assert save_success is True, "Save should return True on success"
                assert tracker.save_complete is True, "Save signal should be emitted"
                assert self.state_file.exists(), "State file should exist"
                assert self.state_file.stat().st_size > 0, "State file should not be empty"
                
                # Verify the saved file contains valid JSON
                try:
                    with open(self.state_file, 'r') as f:
                        state_data = json.load(f)
                        logger.debug(f"State file content: {json.dumps(state_data, indent=2, default=str)}")
                        
                        # Basic validation of saved state
                        assert 'items' in state_data, "State file missing 'items' key"
                        assert len(state_data['items']) > 0, "State file should contain at least one item"
                        
                except Exception as e:
                    logger.error(f"Failed to parse state file: {e}")
                    raise
                
                logger.info("Save state completed successfully")
                
            except Exception as e:
                logger.error(f"Exception during save_state: {e}", exc_info=True)
                raise
                
            # Now test loading the saved state
            logger.info("\n" + "-"*40)
            logger.info("Loading processor state")
            logger.info("-"*40)
            
            # Create a new processor for loading
            from core.batch_processor import BatchProcessor
            new_processor = BatchProcessor(self.mock_chd_manager)
            
            # Connect load signal
            new_processor.signals.state_loaded.connect(tracker.on_state_loaded)
            
            # Reset tracker state
            tracker.load_complete = False
            tracker.load_file = None
            tracker.load_errors = []
            
            # Load state with error handling
            load_success = False
            try:
                logger.info(f"Calling load_state with: {self.state_file}")
                load_success = new_processor.load_state(str(self.state_file.absolute()))
                logger.info(f"load_state returned: {load_success}")
                
                # Wait for load to complete with timeout
                logger.info("Waiting for state_loaded signal...")
                signal_received = self.wait_for_signal(
                    new_processor.signals.state_loaded, 
                    timeout=5000  # 5 second timeout
                )
                
                # Process any pending events
                QCoreApplication.processEvents()
                
                logger.info(f"Signal received: {signal_received}")
                logger.info(f"Load complete: {tracker.load_complete}")
                
                if not signal_received or not tracker.load_complete:
                    error_msg = [
                        "Load operation failed:",
                        f"- Signal received: {signal_received}",
                        f"- Load complete: {tracker.load_complete}",
                        f"- Load errors: {tracker.load_errors or 'None'}",
                        f"- Loaded items: {len(new_processor.items) if hasattr(new_processor, 'items') else 'N/A'}"
                    ]
                    logger.error("\n".join(error_msg))
                    assert False, "Load operation failed. See logs for details."
                
                # Verify load result
                assert load_success is True, "Load should return True on success"
                assert tracker.load_complete is True, "Load signal should be emitted"
                
                # Verify the task was loaded correctly
                assert hasattr(new_processor, 'items'), "Loaded processor has no items"
                assert len(new_processor.items) == 1, "Should have one item after load"
                
                loaded_item = new_processor.items[0]
                logger.info(f"Loaded item: {loaded_item}")
                
                # Verify item properties
                assert loaded_item.input_path == str(self.test_input.absolute()), "Input path mismatch"
                assert loaded_item.output_path == str(self.test_output.absolute()), "Output path mismatch"
                assert loaded_item.media_type == "cd", "Media type mismatch"
                assert loaded_item.compression == "zlib", "Compression mismatch"
                assert loaded_item.hunk_size == 2048, "Hunk size mismatch"
                assert loaded_item.retry_count == 2, "Retry count mismatch"
                assert loaded_item.max_retries == 5, "Max retries mismatch"
                assert loaded_item.status == BatchTaskStatus.PENDING, "Status mismatch"
                assert loaded_item.progress == 25.0, "Progress mismatch"
                
                # Verify processor state
                assert new_processor.current_index == 0, "Current index mismatch"
                assert new_processor.is_paused is False, "Paused state mismatch"
                assert new_processor.is_running is True, "Running state mismatch"
                
                logger.info("Load state completed successfully")
                
            except Exception as e:
                logger.error(f"Exception during load_state: {e}", exc_info=True)
                raise
                
        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            raise
        finally:
            # Clean up
            try:
                if hasattr(self, 'state_file') and self.state_file.exists():
                    self.state_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up state file: {e}")
            
            logger.info("\n" + "="*80)
            logger.info("COMPLETED test_save_load_cycle")
            logger.info("="*80)
        
        assert item is not None, "Item should be added successfully"
        logger.info(f"Added item with input: {item.input_path}, output: {item.output_path}")
        
        # Track signals
        class SignalTracker:
            def __init__(self):
                self.save_complete = False
                self.load_complete = False
                self.save_file = None
                self.load_file = None
            
            def on_state_saved(self, file_path):
                self.save_complete = True
                self.save_file = file_path
                logger.info(f"State saved signal received for: {file_path}")
            
            def on_state_loaded(self, file_path):
                self.load_complete = True
                self.load_file = file_path
                logger.info(f"State loaded signal received for: {file_path}")
        
        tracker = SignalTracker()
        
        # Connect signals with proper error handling
        try:
            self.processor.signals.state_saved.disconnect()
            self.processor.signals.state_loaded.disconnect()
        except RuntimeError:
            pass  # No connections to disconnect
            
        self.processor.signals.state_saved.connect(tracker.on_state_saved)
        
        # Test save state with timeout
        logger.info(f"Saving BatchProcessor state to: {self.state_file}")
        logger.info(f"Processor items before save: {len(self.processor.items)}")
        
        # Reset tracker
        tracker.save_complete = False
        tracker.save_file = None
        
        # Start a timer to prevent hanging
        save_timeout = 10000  # 10 seconds in milliseconds
        logger.info("Calling save_state...")
        
        # Save the state
        save_success = False
        try:
            save_success = self.processor.save_state(str(self.state_file))
            logger.info(f"save_state returned: {save_success}")
        except Exception as e:
            logger.error(f"Error in save_state: {e}")
            assert False, f"Save operation raised an exception: {e}"
        
        # Verify save result
        assert save_success is True, "Save operation should return True"
        
        # Wait for save to complete with timeout
        logger.info("Waiting for state_saved signal...")
        signal_received = self.wait_for_signal(self.processor.signals.state_saved, save_timeout)
        
        # Process any pending events
        QCoreApplication.processEvents()
        
        logger.info(f"Signal received: {signal_received}, Save complete: {tracker.save_complete}")
        
        if not signal_received or not tracker.save_complete:
            error_msg = (
                f"Save operation failed. "
                f"Signal received: {signal_received}, "
                f"Save complete: {tracker.save_complete}, "
                f"File exists: {self.state_file.exists()}"
            )
            if self.state_file.exists():
                try:
                    with open(self.state_file, 'r') as f:
                        content = f.read(500)  # Read first 500 chars
                        error_msg += f"\nFile content: {content}"
                except Exception as e:
                    error_msg += f"\nFailed to read state file: {e}"
            
            logger.error(error_msg)
            assert False, error_msg
        
        # Verify save result
        assert save_success is True, "Save should return True on success"
        assert tracker.save_complete is True, "Save signal should be emitted"
        assert self.state_file.exists(), "State file should exist"
        assert self.state_file.stat().st_size > 0, "State file should not be empty"
        
        # Verify the saved file contains valid JSON
        try:
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)
                logger.debug(f"State file content: {state_data}")
        except Exception as e:
            logger.error(f"Failed to parse state file: {e}")
            raise
        
        # Create a new processor for loading
        new_processor = BatchProcessor(self.mock_chd_manager)
        new_processor.signals.state_loaded.connect(tracker.on_state_loaded)
        
        # Test load state with timeout
        logger.info(f"Loading BatchProcessor state from: {self.state_file}")
        
        # Reset tracker
        tracker.load_complete = False
        tracker.load_file = None
        
        # Start a timer to prevent hanging
        load_timeout = 10000  # 10 seconds in milliseconds
        
        # Load the state
        load_success = new_processor.load_state(str(self.state_file))
        logger.info(f"Load result: {load_success}")
        
        # Process any pending events
        QCoreApplication.processEvents()
        
        # Wait for load to complete with timeout
        signal_received = self.wait_for_signal(new_processor.signals.state_loaded, load_timeout)
        
        # Process any pending events again
        QCoreApplication.processEvents()
        
        logger.info(f"Load signal received: {signal_received}, Load complete: {tracker.load_complete}")
        
        if not signal_received or not tracker.load_complete:
            error_msg = (
                f"Load operation failed. "
                f"Signal received: {signal_received}, "
                f"Load complete: {tracker.load_complete}, "
                f"File exists: {self.state_file.exists()}"
            )
            logger.error(error_msg)
            assert False, error_msg
        
        # Verify load result
        assert load_success is True, "Load should return True on success"
        assert tracker.load_complete is True, "Load signal should be emitted"
        
        # Verify the task was loaded
        assert len(new_processor.items) == 1, "Should have one item after load"
        loaded_item = new_processor.items[0]
        assert loaded_item.input_path == str(self.test_input), "Input path should match"
        assert loaded_item.output_path == str(self.test_output), "Output path should match"
        assert loaded_item.media_type == "cd", "Media type should match"
        assert loaded_item.compression == "zlib", "Compression should match"
        assert loaded_item.hunk_size == 2048, "Hunk size should match"
        assert loaded_item.verify is True, "Verify flag should be True"
        assert loaded_item.overwrite is False, "Overwrite flag should be False"
        
        logger.info("Test completed successfully")
