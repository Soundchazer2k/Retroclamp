#!/usr/bin/env python3
"""
Test script for verifying archive extraction functionality in the CompressionTab class.
"""

import os
import sys
import tempfile
import shutil
import zipfile
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the CompressionTab class
from gui.compression_tab import CompressionTab
from PySide6.QtWidgets import QApplication


class TestLogger:
    """Simple logger for testing."""
    
    def __init__(self):
        self.logs = []
    
    def log(self, message):
        print(message)
        self.logs.append(message)


class MockCompressionTab(CompressionTab):
    """Mock CompressionTab for testing."""
    
    def __init__(self):
        # Skip the parent's __init__ to avoid UI setup
        self.logger = TestLogger()
        
        # Create a FileScanner instance for testing
        from core.file_scanner import FileScanner
        self.file_scanner = FileScanner()
    
    def log_message(self, message):
        self.logger.log(message)
    
    def format_size(self, size):
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"


def create_test_archive(test_dir, archive_name, files_to_add):
    """
    Create a zip archive containing the specified files.
    Ensures all parent directories exist before writing nested files.
    """
    import os
    import zipfile

    archive_path = os.path.join(test_dir, archive_name)
    with zipfile.ZipFile(archive_path, 'w') as zipf:
        for filename, content in files_to_add:
            temp_file = os.path.join(test_dir, filename)
            parent_dir = os.path.dirname(temp_file)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(temp_file, 'w') as f:
                f.write(content)
            zipf.write(temp_file, arcname=filename)
            os.remove(temp_file)
    return archive_path


def test_extract_archive():
    """Test the extract_archive method."""
    print("\n=== Testing extract_archive method ===")
    
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    print(f"Created test directory: {test_dir}")
    
    try:
        # Create test files
        test_files = [
            ('test.bin', 'This is a test bin file'),
            ('test.cue', 'FILE "test.bin" BINARY\nTRACK 01 MODE1/2352\nINDEX 01 00:00:00'),
            ('other.txt', 'This is a text file'),
            ('subdir/nested.iso', 'This is a nested ISO file')
        ]
        
        # Create a test archive
        archive_path = create_test_archive(test_dir, 'test_archive.zip', test_files)
        print(f"Created test archive: {archive_path}")
        
        # Create a mock CompressionTab instance
        tab = MockCompressionTab()
        
        # Test extract_archive method
        success, temp_dir, disk_images = tab.extract_archive(archive_path, -1)
        
        # Print results
        print(f"\nExtraction success: {success}")
        if success:
            print(f"Temporary directory: {temp_dir}")
            print(f"Found disk images: {disk_images}")
            
            # Verify that the expected files were extracted
            expected_files = [os.path.join(temp_dir, f[0]) for f in test_files]
            for file_path in expected_files:
                if os.path.exists(file_path):
                    print(f"Found expected file: {file_path}")
                else:
                    print(f"Missing expected file: {file_path}")
            
            # Verify that the .bin and .cue files were detected as disk images
            expected_disk_images = [
                os.path.join(temp_dir, 'test.bin'),
                os.path.join(temp_dir, 'test.cue'),
                os.path.join(temp_dir, 'subdir/nested.iso')
            ]
            for disk_image in expected_disk_images:
                if disk_image in disk_images:
                    print(f"Correctly detected disk image: {disk_image}")
                else:
                    print(f"Failed to detect disk image: {disk_image}")
        
        # Print logs
        print("\nLogs:")
        for log in tab.logger.logs:
            print(f"  {log}")
    
    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"\nCleaned up test directory: {test_dir}")


def test_scan_extracted_directory():
    """Test the scan_extracted_directory method directly."""
    print("\n=== Testing scan_extracted_directory method ===")
    
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    print(f"Created test directory: {test_dir}")
    
    try:
        # Create test files
        os.makedirs(os.path.join(test_dir, 'subdir'), exist_ok=True)
        
        test_files = [
            ('test.bin', 'This is a test bin file'),
            ('test.cue', 'FILE "test.bin" BINARY\nTRACK 01 MODE1/2352\nINDEX 01 00:00:00'),
            ('other.txt', 'This is a text file'),
            ('subdir/nested.iso', 'This is a nested ISO file'),
            ('orphan.bin', 'This is an orphaned bin file without a cue')
        ]
        
        for filename, content in test_files:
            file_path = os.path.join(test_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"Created test file: {file_path}")
        
        # Create a mock CompressionTab instance
        tab = MockCompressionTab()
        
        # Test find_disk_images method
        compatible_files = tab.file_scanner.find_disk_images(test_dir)
        
        # Print results
        print(f"\nFound compatible files: {compatible_files}")
        
        # Verify that the expected files were detected
        expected_compatible_files = [
            os.path.join(test_dir, 'test.bin'),
            os.path.join(test_dir, 'test.cue'),
            os.path.join(test_dir, 'subdir/nested.iso'),
            os.path.join(test_dir, 'orphan.bin')
        ]
        
        for file_path in expected_compatible_files:
            if file_path in compatible_files:
                print(f"Correctly detected compatible file: {file_path}")
            else:
                print(f"Failed to detect compatible file: {file_path}")
        
        # Print logs
        print("\nLogs:")
        for log in tab.logger.logs:
            print(f"  {log}")
    
    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"\nCleaned up test directory: {test_dir}")


if __name__ == "__main__":
    # Create a QApplication instance (required for PySide6)
    app = QApplication(sys.argv)
    
    # Run the tests
    test_scan_extracted_directory()
    test_extract_archive()
    
    # Exit
    sys.exit(0)
