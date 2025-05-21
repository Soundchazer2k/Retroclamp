import os
import sys
import traceback
from gui.compression_tab import CompressionTab

class MockLogger:
    def __init__(self):
        self.logs = []
    
    def log(self, message):
        print(message)
        self.logs.append(message)

class MockCompressionTab(CompressionTab):
    def __init__(self):
        # Initialize with minimal requirements
        self.logger = MockLogger()
    
    def log(self, message):
        self.logger.log(message)
    
    def format_size(self, size):
        """Format file size in human-readable format."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

def test_extract_archive():
    print("\n=== Testing archive extraction ===\n")
    
    # Create a mock compression tab
    tab = MockCompressionTab()
    
    # Test with our test ZIP file
    archive_path = os.path.join(os.getcwd(), "test_files", "test.zip")
    print(f"Testing extraction of {archive_path}")
    
    try:
        # Call the extract_archive method
        success, temp_dir, disk_images = tab.extract_archive(archive_path, 0)
        
        if success:
            print(f"\nExtraction successful!")
            print(f"Temporary directory: {temp_dir}")
            print(f"Found {len(disk_images)} disk images:")
            for image in disk_images:
                print(f"  - {image}")
            
            # Clean up
            print("\nCleaning up...")
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            print("\nExtraction failed or no compatible disk images found.")
    
    except Exception as e:
        print(f"\nError during extraction: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    test_extract_archive()
