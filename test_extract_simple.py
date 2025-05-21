import os
import zipfile
import shutil
import traceback
import time
import sys

def extract_and_scan(zip_path):
    # Create a temporary directory
    temp_dir = f"temp_extract_{int(time.time())}"
    os.makedirs(temp_dir, exist_ok=True)
    
    print(f"Extracting {zip_path} to {temp_dir}")
    
    # Extract the ZIP file
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # List all extracted files
    bin_files = []
    cue_files = []
    compatible_files = []
    
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            
            if ext == '.bin':
                bin_files.append(file_path)
                compatible_files.append(file_path)
                print(f"Found BIN file: {file}")
            elif ext == '.cue':
                cue_files.append(file_path)
                compatible_files.append(file_path)
                print(f"Found CUE file: {file}")
            elif ext in ['.iso', '.img', '.gdi', '.chd', '.cdr', '.nrg', '.mdf', '.toc']:
                compatible_files.append(file_path)
                print(f"Found compatible file: {file}")
    
    # Check for .bin files without matching .cue files
    for bin_file in bin_files:
        bin_name = os.path.splitext(os.path.basename(bin_file))[0]
        has_matching_cue = False
        
        for cue_file in cue_files:
            cue_name = os.path.splitext(os.path.basename(cue_file))[0]
            if bin_name in cue_name or cue_name in bin_name:
                has_matching_cue = True
                print(f"Found matching CUE file for {bin_name}")
                break
        
        if not has_matching_cue:
            print(f"Warning: No matching CUE file found for {bin_name}")
    
    # Summary
    print(f"\nSummary:")
    print(f"Found {len(bin_files)} BIN files")
    print(f"Found {len(cue_files)} CUE files")
    print(f"Total compatible files: {len(compatible_files)}")
    
    # Clean up
    print(f"\nCleaning up temporary directory...")
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        extract_and_scan(sys.argv[1])
    else:
        print("Please provide a ZIP file path as an argument.")
