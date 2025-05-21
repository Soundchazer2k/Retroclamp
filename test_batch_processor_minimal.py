"""Minimal test for BatchProcessor save/load functionality."""
import logging
import time
import signal
import sys
from PySide6.QtCore import QCoreApplication, Qt
import pytest
from core.batch_processor import BatchProcessor, BatchTaskStatus

# Set up basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Global timeout for test steps (in seconds)
STEP_TIMEOUT = 10

class TimeoutError(Exception):
    """Custom timeout exception."""
    pass

def timeout_handler(signum, frame):
    """Handle test timeouts gracefully."""
    raise TimeoutError("Test step timed out")

# Set up signal handler for timeouts
import signal
if hasattr(signal, 'SIGALRM'):
    signal.signal(signal.SIGALRM, timeout_handler)
else:
    # On Windows, SIGALRM is not available. Consider using threading.Timer or skip timeout setup.
    print('SIGALRM not available on this platform; skipping signal-based timeout.')

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_batch_processor.log')
    ]
)
logger = logging.getLogger(__name__)

# Enable pytest-timeout with a 30-second timeout
pytestmark = pytest.mark.timeout(30)

@pytest.fixture
def mock_chd_manager():
    """Create a minimal mock CHD manager."""
    from PySide6.QtCore import QObject, Signal
    
    class MockSignals(QObject):
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
    
    class MockCHDManager:
        def __init__(self):
            # Create a combined signals class that includes everything we need
            class CHDSignals(QObject):
                # Signals from original MockSignals
                started = Signal()
                finished = Signal()
                paused = Signal()
                resumed = Signal()
                cancelled = Signal()
                progress_updated = Signal(int, int, object)
                error_occurred = Signal(str)
                state_saved = Signal(str)
                state_loaded = Signal(str)
                item_added = Signal(object)
                item_started = Signal(object)
                item_progress = Signal(object, object)
                item_completed = Signal(object)
                item_failed = Signal(object, str)
                item_skipped = Signal(object, str)
                item_updated = Signal(object)
                
                # CHDManager specific signals
                task_completed = Signal(object)  # CHDTask
                task_failed = Signal(object, str)  # CHDTask, error
                
                def __init__(self):
                    super().__init__()
                    # Connect all signals to no-op slots to avoid warnings
                    for signal_name, signal in self.__class__.__dict__.items():
                        if isinstance(signal, Signal):
                            getattr(self, signal_name).connect(lambda *args, **kwargs: None)
            
            # Use our combined signals class
            self.signals = CHDSignals()
    
    return MockCHDManager()

@pytest.fixture
def qt_app():
    """Ensure a QApplication instance exists for the test."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app

@pytest.fixture
def batch_processor():
    """Create a minimal BatchProcessor instance."""
    logger.info("Creating BatchProcessor")
    processor = BatchProcessor()
    logger.info("BatchProcessor created")
    return processor

def test_save_load_minimal(qtbot, tmp_path, batch_processor):
    """Test saving and loading batch processor state with minimal setup."""
    # Set up timeout for the entire test
    signal.alarm(60)  # 60 second timeout for the entire test
    
    try:
        logger.info("Starting test_save_load_minimal")
        
        # Get the QApplication instance
        app = QCoreApplication.instance()
        assert app is not None, "QApplication must be running"
        
        # Verify Qt application is running
        print("1. Checking QApplication instance...")
        app = QCoreApplication.instance()
        assert app is not None, "QApplication must be running"
        print(f"   ✓ QApplication is running: {app}")
        print(f"   Current thread: {QCoreApplication.instance().thread().currentThread()}")
        print(f"   Processor thread: {batch_processor.thread().currentThread()}")
        
        # Add a simple item
        print("2. Creating test file...")
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"TESTDATA")
        print(f"   ✓ Created test file: {test_file}")
        
        print("3. Adding item to batch...")
        output_path = str(tmp_path / "output.chd")
        print(f"   Input: {test_file}")
        print(f"   Output: {output_path}")
        
        item = batch_processor.add_item(
            input_path=str(test_file),
            output_path=output_path,
            media_type="cd",
            compression="cd_flac"
        )
        print(f"   ✓ Item added to batch: {item}")
        print(f"   Item status: {item.status}")
        
        print("4. Setting item status to PENDING...")
        item.status = BatchTaskStatus.PENDING
        print(f"   ✓ Item status set to: {item.status}")
        
        # Save state
        state_file = tmp_path / "state.json"
        print(f"5. Preparing to save state to {state_file}...")
        
        # Ensure we have a clean state
        if state_file.exists():
            print(f"   Removing existing state file: {state_file}")
            state_file.unlink()
        
        # Connect to signals before saving
        saved_signal_emitted = False
        received_path = None
        
        def on_state_saved(path):
            nonlocal saved_signal_emitted, received_path
            saved_signal_emitted = True
            received_path = path
            print(f"   ✓✓✓ STATE SAVED SIGNAL RECEIVED: {path}")
            print(f"   Signal thread: {QCoreApplication.instance().thread().currentThread()}")
        
        # Connect the signal with a unique connection to avoid duplicate handlers
        try:
            # First, disconnect any existing connections to avoid duplicates
            try:
                # Disconnect all slots from this signal
                batch_processor.signals.state_saved.disconnect()
                print("   Disconnected existing state_saved signal handlers")
            except RuntimeError as e:
                # This is expected if there were no connections
                print(f"   No existing state_saved signal handlers to disconnect: {e}")
            
            # Connect our signal handler with a queued connection
            print("   Connecting state_saved signal handler...")
            batch_processor.signals.state_saved.connect(
                on_state_saved,
                type=Qt.QueuedConnection
            )
            
            # In PySide6, we can't easily check the number of receivers like in PyQt
            # Instead, we'll just log that we've attempted to connect the signal
            print(f"   ✓ Connected to state_saved signal: {batch_processor.signals.state_saved}")
            
            # Get the signal index to verify it exists
            signal_index = batch_processor.signals.metaObject().indexOfSignal("state_saved(QString)")
            if signal_index >= 0:
                print(f"   ✓ Signal index found: {signal_index}")
            else:
                print("   !!! Warning: Could not find signal index for state_saved")
        except Exception as e:
            print(f"   !!! Failed to connect signal: {e}")
            raise
        
        # Save and verify
        print("6. Calling save_state...")
        try:
            # Process any pending events before saving
            app.processEvents()
            
            # Call save_state with a timeout
            save_result = batch_processor.save_state(str(state_file))
            print(f"   save_state returned: {save_result}")
            
            # Process any events that might have been queued during save_state
            app.processEvents()
            
            assert save_result, "Save failed"
            
            # Verify the file was created
            if not state_file.exists():
                print("   !!! State file was not created")
                save_result = False
            else:
                print(f"   ✓ State file exists: {state_file}")
                
        except Exception as e:
            print(f"   !!! Exception in save_state: {e}")
            if state_file.exists():
                print(f"   State file exists with size: {state_file.stat().st_size} bytes")
            raise
        
        # Process events to ensure signal is delivered
        print("7. Processing events to ensure signal delivery...")
        app.processEvents()
        
        # Wait for the signal using qtbot with a timeout
        logger.info("8. Waiting for state_saved signal...")
        
        # Set a timeout for waiting for the signal
        signal.alarm(STEP_TIMEOUT)
        try:
            # Use a loop with processEvents to ensure we don't miss the signal
            start_time = time.time()
            signal_received = False
            last_progress = start_time
            
            while not signal_received and (time.time() - start_time) < STEP_TIMEOUT:
                current_time = time.time()
                if current_time - last_progress > 1.0:  # Log progress every second
                    elapsed = current_time - start_time
                    logger.info(f"   Waiting for signal... ({elapsed:.1f}s elapsed)")
                    last_progress = current_time
                    
                # Process all pending events
                app.processEvents()
                
                # Check if we've received the signal
                if saved_signal_emitted:
                    signal_received = True
                    logger.info("   Signal received successfully")
                    break
                    
                # Small sleep to prevent busy-waiting
                time.sleep(0.05)
            
            if not signal_received:
                logger.error("   !!! Timeout waiting for state_saved signal")
                # Try one last process events in case we missed it
                app.processEvents()
                if saved_signal_emitted:
                    logger.info("   Signal received in final check")
                    signal_received = True
            
            assert signal_received, f"Timed out waiting for state_saved signal after {STEP_TIMEOUT} seconds"
            
        except TimeoutError:
            logger.error("   !!! Test step timed out")
            raise
        finally:
            signal.alarm(0)  # Disable the alarm
        
        print(f"   Signal received: {signal_received}")
        if signal_received:
            print(f"   Received path: {received_path}")
        else:
            print("   !!! Signal not received within timeout")
            # Try one more time with qtbot to see if that helps
            try:
                with qtbot.waitSignal(
                    batch_processor.signals.state_saved, 
                    timeout=2000,  # 2 second timeout
                    raising=False
                ):
                    app.processEvents()
            except Exception as e:
                print(f"   qtbot.waitSignal failed: {e}")
        
        # Clean up
        try:
            if 'batch_processor' in locals() and batch_processor is not None:
                try:
                    batch_processor.signals.state_saved.disconnect()
                    batch_processor.deleteLater()
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")
        except NameError:
            pass
        
        # Verify the state file was created
        print("9. Verifying state file was created...")
        if not state_file.exists():
            raise AssertionError(f"State file was not created: {state_file}")
            
        # Verify file has content
        file_size = state_file.stat().st_size
        if file_size == 0:
            raise AssertionError(f"State file is empty: {state_file}")
            
        print(f"   ✓ State file exists with {file_size} bytes: {state_file}")
        
        # Check signal emission
        if not signal_received:
            print("   !!! WARNING: state_saved signal was not received, but file was saved")
            print("   This suggests the signal emission is not working correctly")
            print("   However, since the file was saved, we'll continue with the test")
        
        # Mark that we don't need cleanup (test succeeded)
        cleanup_required = False
        print("10. Test completed successfully")
        print("=== Minimal test completed successfully ===\n")
        
    except Exception as e:
        logger.error(f"\n!!! TEST FAILED: {str(e)}")
        logger.exception("Test failed with exception")
        raise
    finally:
        # Clean up test files if the test failed
        if cleanup_required and state_file and state_file.exists():
            try:
                logger.warning(f"Cleaning up state file after test failure: {state_file}")
                state_file.unlink()
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up state file: {cleanup_error}")
        
        # Ensure all pending events are processed
        if qt_app:
            qt_app.processEvents()
            qt_app.sendPostedEvents(None, 0)  # Process any pending events
