"""Simplified test for BatchProcessor save/load functionality."""
import os
import sys
import logging
import tempfile
import pytest
from pathlib import Path

# Set up logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"test_batch_simple_{os.getpid()}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Starting tests. Log file: {log_file.absolute()}")

try:
    from PySide6.QtCore import QCoreApplication, QTimer, QEventLoop
    logger.info("Successfully imported PySide6.QtCore")
except ImportError as e:
    logger.error(f"Failed to import PySide6: {e}")
    raise

try:
    from core.batch_processor import BatchProcessor
    from core.chdman import CHDManager
    logger.info("Successfully imported core modules")
except ImportError as e:
    logger.error(f"Failed to import core modules: {e}")
    raise

class TestBatchSimple:
    """Simplified test class for BatchProcessor save/load."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.app = QCoreApplication.instance() or QCoreApplication()
        self.chd_manager = CHDManager()
        self.processor = BatchProcessor(self.chd_manager)
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, 'test_state.json')
        yield
        # Cleanup
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        os.rmdir(self.temp_dir)
    
    def test_save_state(self):
        """Test saving processor state."""
        logger.info("Starting test_save_state")
        
        # Add a test item
        logger.info("Adding test item to processor")
        try:
            self.processor.add_item(
                input_path="test_input.bin",
                output_path="test_output.chd",
                media_type="cd",
                compression="zlib",
                hunk_size=2048
            )
            logger.info("Successfully added test item")
        except Exception as e:
            logger.error(f"Failed to add test item: {e}", exc_info=True)
            raise
        
        # Save state
        logger.info(f"Saving state to {self.state_file}")
        try:
            result = self.processor.save_state(self.state_file)
            logger.info(f"save_state returned: {result}")
            assert result, "Save state failed"
            assert os.path.exists(self.state_file), "State file was not created"
            logger.info("State file created successfully")
        except Exception as e:
            logger.error(f"Error during save_state: {e}", exc_info=True)
            raise
        
        # Verify file contents
        logger.info("Verifying file contents")
        try:
            with open(self.state_file, 'r') as f:
                data = f.read()
                logger.debug(f"File contents: {data[:500]}...")  # Log first 500 chars
                
                # Check for expected content
                checks = [
                    ('input_path', 'test_input.bin'),
                    ('output_path', 'test_output.chd'),
                    ('media_type', 'cd'),
                    ('compression', 'zlib'),
                    ('hunk_size', '2048')
                ]
                
                for key, value in checks:
                    expected = f'"{key}": "{value}"' if isinstance(value, str) else f'"{key}": {value}'
                    assert expected in data, f"Expected {expected} not found in state file"
                    logger.debug(f"Found expected content: {expected}")
                    
            logger.info("File contents verified successfully")
        except Exception as e:
            logger.error(f"Error verifying file contents: {e}", exc_info=True)
            raise

    def test_save_load_cycle(self):
        """Test saving and loading processor state."""
        # Add a test item
        self.processor.add_item(
            input_path="test_input.bin",
            output_path="test_output.chd",
            media_type="cd",
            compression="zlib",
            hunk_size=2048
        )
        
        # Save state
        save_result = self.processor.save_state(self.state_file)
        assert save_result, "Save state failed"
        
        # Create a new processor and load state
        new_processor = BatchProcessor(self.chd_manager)
        load_result = new_processor.load_state(self.state_file)
        assert load_result, "Load state failed"
        
        # Verify loaded state
        assert len(new_processor.items) == 1
        item = new_processor.items[0]
        assert item.input_path == "test_input.bin"
        assert item.output_path == "test_output.chd"
        assert item.media_type == "cd"
        assert item.compression == "zlib"
        assert item.hunk_size == 2048
