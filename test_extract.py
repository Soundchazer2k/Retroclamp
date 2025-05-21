import os
import zipfile
import shutil
import traceback
import time
import patoolib

def scan_extracted_directory(temp_dir, log_func=print):
    """Scan extracted directory for compatible disk images.
    
    Args:
        temp_dir: Path to the temporary directory
        log_func: Function to use for logging (default: print)
        
    Returns:
        List of compatible disk image paths
    """
    log_func(f"Scanning extracted files in {temp_dir} for compatible disk images...")
    
    if not os.path.exists(temp_dir) or not os.path.isdir(temp_dir):
        log_func(f"Temporary directory does not exist or is not a directory: {temp_dir}")
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
            
        log_func(f"Found {len(files)} files in {root}")
        
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
                log_func(f"Found file: {filename} ({size_str})")
            except Exception as e:
                log_func(f"Error getting file size for {filename}: {str(e)}")
                size_str = "unknown size"
            
            # Track .cue and .bin files specifically
            if ext == ".cue":
                log_func(f"Found .cue file: {filename}")
                cue_files.append((base_name, file_path))
            elif ext == ".bin":
                log_func(f"Found .bin file: {filename}")
                bin_files.append((base_name, file_path))
            
            # Add any compatible file to disk_images
            if ext in compatible_extensions:
                log_func(f"Compatible disk image found: {filename} ({size_str})")
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
            log_func(f"Warning: Found .bin file without matching .cue file: {bin_path}")
    
    if not compatible_files:
        log_func("No compatible disk images found in the extracted archive.")
        if found_files:
            log_func(f"Found {len(found_files)} files, but none with compatible extensions {compatible_extensions}")
            for file_path in found_files[:10]:  # Limit to first 10 files to avoid log spam
                filename = os.path.basename(file_path)
                ext = os.path.splitext(filename)[1].lower()
                log_func(f"  - {filename} (extension: {ext})")
            if len(found_files) > 10:
                log_func(f"  ... and {len(found_files) - 10} more files")
    else:
        log_func(f"Found {len(compatible_files)} compatible disk images in the extracted archive.")
    
    return compatible_files

def format_size(size):
    """Format file size in human-readable format.
    
    Args:
        size: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"

def extract_archive(archive_path, log_func=print):
    """Extract an archive file.
    
    Args:
        archive_path: Path to the archive file
        log_func: Function to use for logging (default: print)
        
    Returns:
        Tuple of (success, temp_dir, disk_images)
    """
    try:
        # Create a temporary directory for extraction in the same folder as the original file
        original_folder = os.path.dirname(archive_path)
        temp_dir_name = f"retroclamp_temp_{int(time.time())}_{os.getpid()}"
        temp_dir = os.path.join(original_folder, temp_dir_name)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Log
        log_func(f"Extracting archive: {archive_path} to {temp_dir}")
        
        # Check if it's a ZIP file for direct handling
        if archive_path.lower().endswith(".zip"):
            log_func("Detected ZIP archive, extracting directly...")
            
            try:
                # First, get the list of files in the ZIP archive
                with zipfile.ZipFile(archive_path, 'r') as zip_file:
                    file_list = zip_file.namelist()
                    file_count = len(file_list)
                    
                    if file_count == 0:
                        log_func("ZIP archive is empty")
                        return False, None, []
                        
                    log_func(f"Found {file_count} files in ZIP archive")
                
                # Use patoolib for extraction as it supports more compression methods
                log_func("Using patoolib to extract ZIP archive...")
                try:
                    patoolib.extract_archive(archive_path, outdir=temp_dir, interactive=False)
                    log_func(f"Successfully extracted archive using patoolib to {temp_dir}")
                except Exception as e:
                    log_func(f"Error using patoolib to extract: {str(e)}")
                    
                    # Fallback to zipfile if patoolib fails
                    log_func("Falling back to zipfile for extraction...")
                    with zipfile.ZipFile(archive_path, 'r') as zip_file:
                        # Extract all files
                        for i, filename in enumerate(file_list):
                            try:
                                # Extract the file
                                zip_file.extract(filename, temp_dir)
                                progress = ((i + 1) / file_count) * 100
                                log_func(f"Extracted file {i+1}/{file_count}: {filename} ({progress:.1f}%)")
                            except Exception as e:
                                log_func(f"Error extracting {filename}: {str(e)}")
                        
                    log_func(f"Finished extraction attempts to {temp_dir}")
            except zipfile.BadZipFile:
                log_func(f"Invalid ZIP file: {archive_path}")
                return False, None, []
            except Exception as e:
                log_func(f"Error extracting ZIP file: {str(e)}")
                return False, None, []
        else:
            # For other archive types, we'd use the archive manager in the real app
            # But for this test, we'll just log and return failure
            log_func(f"Using archive manager for non-ZIP archive: {archive_path}")
            log_func("Archive manager not implemented in test script")
            return False, None, []
        
        # Use the scan_extracted_directory method to find disk images
        disk_images = scan_extracted_directory(temp_dir, log_func)
        
        if disk_images:
            log_func(f"Found {len(disk_images)} disk images in archive")
            return True, temp_dir, disk_images
        else:
            # Clean up temporary directory
            log_func("No compatible disk images found. Cleaning up temporary directory...")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, None, []
            
    except Exception as e:
        log_func(f"Error extracting archive: {str(e)}")
        log_func(traceback.format_exc())
        return False, None, []

# Test function
def test_extract(archive_path):
    print(f"Testing extraction of {archive_path}")
    success, temp_dir, disk_images = extract_archive(archive_path)
    
    if success:
        print(f"Successfully extracted {len(disk_images)} disk images:")
        for image in disk_images:
            print(f"  - {image}")
        
        # Clean up
        print("Cleaning up temporary directory...")
        shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        print("Extraction failed or no compatible disk images found.")

# Main function to run the test
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_extract(sys.argv[1])
    else:
        print("Please provide the path to a ZIP archive as an argument.")
