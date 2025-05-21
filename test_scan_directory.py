import os
import sys
import shutil
import zipfile
import time

# Define a simple logger
class Logger:
    def log(self, message):
        print(message)

# Define a simple format_size function
def format_size(size):
    """Format file size in human-readable format."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"

# Define the scan_extracted_directory function based on our implementation
def scan_extracted_directory(temp_dir, logger):
    """Scan extracted directory for compatible disk images.
    
    Args:
        temp_dir: Path to the temporary directory
        logger: Logger object with log method
        
    Returns:
        List of compatible disk image paths
    """
    logger.log(f"Scanning extracted files in {temp_dir} for compatible disk images...")
    
    if not os.path.exists(temp_dir) or not os.path.isdir(temp_dir):
        logger.log(f"Temporary directory does not exist or is not a directory: {temp_dir}")
        return []
    
    compatible_files = []
    found_files = []
    cue_files = []
    bin_files = []
    
    # Expanded list of compatible extensions based on CHDMAN documentation
    compatible_extensions = [".iso", ".bin", ".img", ".cue", ".gdi", ".chd", ".cdr", ".nrg", ".mdf", ".toc"]
    
    # First pass: collect all files and identify .cue and .bin files
    for root, dirs, files in os.walk(temp_dir):
        if not files:
            continue
            
        logger.log(f"Found {len(files)} files in {root}")
        
        # Check each file for compatibility
        for filename in files:
            file_path = os.path.join(root, filename)
            found_files.append(file_path)
            ext = os.path.splitext(filename)[1].lower()
            base_name = os.path.splitext(filename)[0]
            
            # Get file size to log
            try:
                file_size = os.path.getsize(file_path)
                size_str = format_size(file_size)
                logger.log(f"Found file: {filename} ({size_str})")
            except Exception as e:
                logger.log(f"Error getting file size for {filename}: {str(e)}")
                size_str = "unknown size"
            
            # Track .cue and .bin files specifically
            if ext == ".cue":
                logger.log(f"Found .cue file: {filename}")
                cue_files.append((base_name, file_path))
            elif ext == ".bin":
                logger.log(f"Found .bin file: {filename}")
                bin_files.append((base_name, file_path))
            
            # Add any compatible file to disk_images
            if ext in compatible_extensions:
                logger.log(f"Compatible disk image found: {filename} ({size_str})")
                compatible_files.append(file_path)
    
    # Second pass: check for .bin files without corresponding .cue files
    for bin_name, bin_path in bin_files:
        # Check if we have a matching .cue file
        has_matching_cue = False
        for cue_name, _ in cue_files:
            # Sometimes the .cue file might have a slightly different name than the .bin file
            # So we check if one is a substring of the other
            if bin_name in cue_name or cue_name in bin_name:
                has_matching_cue = True
                break
        
        if not has_matching_cue:
            logger.log(f"Warning: Found .bin file without matching .cue file: {bin_path}")
    
    if not compatible_files:
        logger.log("No compatible disk images found in the extracted archive.")
        if found_files:
            logger.log(f"Found {len(found_files)} files, but none with compatible extensions {compatible_extensions}")
            for file_path in found_files[:10]:  # Limit to first 10 files to avoid log spam
                filename = os.path.basename(file_path)
                ext = os.path.splitext(filename)[1].lower()
                logger.log(f"  - {filename} (extension: {ext})")
            if len(found_files) > 10:
                logger.log(f"  ... and {len(found_files) - 10} more files")
    else:
        logger.log(f"Found {len(compatible_files)} compatible disk images in the extracted archive.")
    
    return compatible_files

# Test function
def test_scan_directory():
    # Create a logger
    logger = Logger()
    
    # Extract the test ZIP file to a temporary directory
    zip_path = os.path.join(os.getcwd(), "test_files", "test.zip")
    temp_dir = os.path.join(os.getcwd(), f"temp_extract_{int(time.time())}")
    
    try:
        # Create the temporary directory
        os.makedirs(temp_dir, exist_ok=True)
        
        # Extract the ZIP file
        print(f"\n=== Extracting {zip_path} to {temp_dir} ===\n")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Scan the directory for compatible disk images
        print(f"\n=== Scanning directory for compatible disk images ===\n")
        compatible_files = scan_extracted_directory(temp_dir, logger)
        
        # Print results
        print(f"\n=== Results ===\n")
        if compatible_files:
            print(f"Found {len(compatible_files)} compatible disk images:")
            for file_path in compatible_files:
                print(f"  - {os.path.basename(file_path)}")
        else:
            print("No compatible disk images found.")
    
    finally:
        # Clean up
        print(f"\n=== Cleaning up ===\n")
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_scan_directory()
