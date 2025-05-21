"""Simplified test for BatchProcessor save/load functionality."""
import logging
import os
import sys
import traceback
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QObject, Signal
import pytest
import time
from PySide6.QtCore import QTimer, QEventLoop
from typing import Optional, Callable, Any

# Add the project root to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.absolute()))

# Import BatchProcessor after setting up the path
try:
    from core.batch_processor import BatchProcessor, BatchTaskStatus
except ImportError as e:
    print(f"Error importing BatchProcessor: {e}")
    print(f"Current sys.path: {sys.path}")
    raise

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    
    def __init__(self):
        super().__init__()
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

@pytest.fixture
def qt_app():
    """Ensure a QApplication instance exists for the test."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app

@pytest.fixture
def mock_chd_manager(qtbot):
    """Create a mock CHD manager for testing."""
    logger.info("Creating mock CHD manager")
    manager = MockCHDManager()
    # No need to add to qtbot as it's not a widget
    return manager

def test_save_state_simple(qt_app, tmp_path, mock_chd_manager):
    """Test saving state with a simple mock."""
    # Create a test state file path
    state_file = tmp_path / "test_state.json"
    
    # Create a signal to track when save is complete
    save_complete = False
    
    def on_save_complete(path):
        nonlocal save_complete
        save_complete = True
        logger.info(f"State saved to: {path}")
    
    # Connect the signal
    mock_chd_manager.signals.state_saved.connect(on_save_complete)
    
    # Save the state
    logger.info(f"Saving state to: {state_file}")
    result = mock_chd_manager.save_state(str(state_file))
    
    # Process events to ensure signal is delivered
    QCoreApplication.processEvents()
    
    # Verify the result
    assert result is True, "Save should return True on success"
    assert save_complete is True, "Save signal should be emitted"
    assert state_file.exists(), "State file should exist"
    assert state_file.stat().st_size > 0, "State file should not be empty"
    
    logger.info("Test passed successfully")

class TestBatchProcessor:
    """Test BatchProcessor save/load functionality."""

    def test_save_load(self, tmp_path, mock_chd_manager):
        # Try to import BatchProcessor with detailed error handling
        try:
            from core.batch_processor import BatchProcessor
            logger.info("Successfully imported BatchProcessor")
        except ImportError as e:
            logger.error(f"Failed to import BatchProcessor: {e}")
            logger.error(f"Python path: {sys.path}")
            logger.error(f"Current working directory: {os.getcwd()}")
            logger.error(f"Core module exists: {os.path.exists(os.path.join(os.path.dirname(__file__), 'core'))}")
            if os.path.exists(os.path.join(os.path.dirname(__file__), 'core')):
                logger.error(f"Core directory contents: {os.listdir(os.path.join(os.path.dirname(__file__), 'core'))}")
            raise

        # Create a test state file path
        state_file = tmp_path / "batch_processor_state.json"
        logger.info(f"Using temporary file: {state_file}")
        
        # Create a BatchProcessor instance with the mock CHD manager
        logger.info("Creating BatchProcessor instance")
        try:
            logger.info(f"Mock CHD manager signals: {dir(mock_chd_manager.signals)}")
            logger.info(f"Mock CHD manager type: {type(mock_chd_manager)}")
            logger.info(f"Mock CHD manager dir: {dir(mock_chd_manager)}")
            
            # Try to create BatchProcessor with detailed error handling
            try:
                processor = BatchProcessor(mock_chd_manager)
                logger.info("BatchProcessor created successfully")
            except TypeError as e:
                logger.error(f"TypeError creating BatchProcessor: {e}")
                logger.error("This might be due to incorrect arguments to BatchProcessor.__init__")
                logger.error(f"Expected signature: {BatchProcessor.__init__.__annotations__}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error creating BatchProcessor: {e}")
                logger.error(traceback.format_exc())
                raise
                
            logger.info(f"BatchProcessor signals: {dir(processor.signals) if hasattr(processor, 'signals') else 'No signals attribute'}")
            
        except Exception as e:
            logger.error(f"Failed to create BatchProcessor: {e}")
            logger.error(traceback.format_exc())
            raise
        
        # Add a test task
        test_input = str(tmp_path / "test_input.bin")
        test_output = str(tmp_path / "test_output.chd")
        
        # Create a test input file
        with open(test_input, 'wb') as f:
            f.write(b'test data')
        
        # Add the task to the processor
        logger.info("Adding test task to processor")
        try:
            # Add an item to the batch processor with all required parameters
            item = processor.add_item(
                input_path=test_input,
                output_path=test_output,
                media_type="cd",  # Required parameter
                compression="zlib",
                hunk_size=2048,
                verify=True,
                overwrite=False
            )
            logger.info(f"Added item with input: {item.input_path}, output: {item.output_path}")
            assert item is not None, "Item should be added successfully"
        except Exception as e:
            logger.error(f"Failed to add task: {e}")
            raise
        
        # Track signals using a more reliable method
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
        
        # Create signal tracker
        tracker = SignalTracker()
        
        # Connect signals with proper error handling
        try:
            processor.signals.state_saved.disconnect()
            processor.signals.state_loaded.disconnect()
        except RuntimeError:
            pass  # No connections to disconnect
            
        processor.signals.state_saved.connect(tracker.on_state_saved)
        processor.signals.state_loaded.connect(tracker.on_state_loaded)
        
        # Save the state with timeout
        logger.info(f"Saving BatchProcessor state to: {state_file}")
        try:
            # Start a timer to prevent hanging
            save_timeout = 5.0  # 5 seconds timeout for save operation
            start_time = time.time()
            
            # Save the state
            save_result = processor.save_state(str(state_file))
            logger.info(f"Save result: {save_result}")
            
            # Wait for save to complete with timeout
            while not tracker.save_complete and (time.time() - start_time) < save_timeout:
                QCoreApplication.processEvents()
                time.sleep(0.1)
            
            # Check for timeout
            if not tracker.save_complete:
                raise TimeoutError("Timed out waiting for save to complete")
                
            # Verify save result
            assert save_result is True, "Save should return True on success"
            assert tracker.save_complete is True, "Save signal should be emitted"
            assert state_file.exists(), "State file should exist"
            file_size = state_file.stat().st_size
            logger.info(f"State file size: {file_size} bytes")
            assert file_size > 0, "State file should not be empty"
            
            # Verify the saved file contains valid JSON
            try:
                import json
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    logger.debug(f"State file content: {state_data}")
            except Exception as e:
                logger.error(f"Failed to parse state file: {e}")
                raise
        except Exception as e:
            logger.error(f"Error during save: {e}")
            if state_file.exists():
                logger.error(f"State file exists: {state_file.stat().st_size} bytes")
            else:
                logger.error("State file was not created")
            raise
        
        # Reset flags
        tracker.save_complete = False
        
        # Create a new processor and load the state
        logger.info("Creating a new BatchProcessor to load the state")
        new_processor = BatchProcessor(mock_chd_manager)
        
        # Connect signals for the new processor
        # Reset tracker for load operation
        tracker.save_complete = False
        tracker.load_complete = False
        
        # Load the state with timeout
        logger.info(f"Loading BatchProcessor state from: {state_file}")
        try:
            # Start a timer to prevent hanging
            load_timeout = 5.0  # 5 seconds timeout for load operation
            start_time = time.time()
            
            # Load the state
            load_result = new_processor.load_state(str(state_file))
            logger.info(f"Load result: {load_result}")
            
            # Wait for load to complete with timeout
            while not tracker.load_complete and (time.time() - start_time) < load_timeout:
                QCoreApplication.processEvents()
                time.sleep(0.1)
            
            # Check for timeout
            if not tracker.load_complete:
                raise TimeoutError("Timed out waiting for load to complete")
                
            # Verify load result
            assert load_result is True, "Load should return True on success"
            assert tracker.load_complete is True, "Load signal should be emitted"
        except Exception as e:
            logger.error(f"Exception during load operation: {e}")
            raise

        # Verify the task was loaded
        assert len(new_processor.tasks) == 1, "Should have one task after load"
        task = list(new_processor.tasks.values())[0]
        assert task.input_path == test_input, "Task input path should match"
        assert task.output_path == test_output, "Task output path should match"
        
        logger.info("BatchProcessor save/load test passed successfully")
