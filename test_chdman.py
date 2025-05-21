"""Test script to verify chdman.exe functionality.

This script attempts to locate and execute chdman.exe to verify it's working correctly.
"""

import os
import subprocess
import sys
from pathlib import Path

def find_chdman():
    """Find chdman.exe in the bin directory."""
    # Get the current script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Look for bin directory
    bin_dir = os.path.join(script_dir, "bin")
    print(f"Looking for chdman in: {bin_dir}")
    
    # Check if bin directory exists
    if not os.path.exists(bin_dir):
        print(f"ERROR: bin directory not found at {bin_dir}")
        return None
    
    # Check for chdman.exe
    chdman_path = os.path.join(bin_dir, "chdman.exe")
    if os.path.exists(chdman_path):
        print(f"Found chdman.exe at: {chdman_path}")
        return chdman_path
    else:
        print(f"ERROR: chdman.exe not found at {chdman_path}")
        return None

def test_chdman_execution(chdman_path):
    """Test if chdman.exe can be executed."""
    print(f"Testing execution of {chdman_path}")
    
    try:
        # Try to run chdman.exe with --help
        result = subprocess.run([chdman_path, "--help"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            print("SUCCESS: chdman.exe executed successfully")
            print("\nOutput:")
            print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            return True
        else:
            print("ERROR: chdman.exe execution failed")
            print("\nStderr:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        return False

def check_file_permissions(chdman_path):
    """Check file permissions for chdman.exe."""
    if not os.path.exists(chdman_path):
        print(f"ERROR: File does not exist: {chdman_path}")
        return
    
    # Get file stats
    stats = os.stat(chdman_path)
    print(f"File size: {stats.st_size} bytes")
    
    # Check if file is executable (Windows doesn't have execute permission bit)
    if os.name != "nt":
        is_executable = os.access(chdman_path, os.X_OK)
        print(f"Is executable: {is_executable}")
    else:
        print("On Windows, checking if file has .exe extension")
        has_exe_ext = chdman_path.lower().endswith('.exe')
        print(f"Has .exe extension: {has_exe_ext}")

def main():
    """Main function."""
    print("=== CHDMAN Diagnostic Tool ===")
    
    # Find chdman.exe
    chdman_path = find_chdman()
    if not chdman_path:
        print("ERROR: Could not find chdman.exe")
        return
    
    # Check file permissions
    check_file_permissions(chdman_path)
    
    # Test execution
    success = test_chdman_execution(chdman_path)
    
    print("\n=== Diagnostic Summary ===")
    if success:
        print("✅ chdman.exe was found and executed successfully")
        print("If the application is still not running chdman.exe, the issue is likely in how the application is calling it")
    else:
        print("❌ chdman.exe was found but could not be executed")
        print("This indicates a problem with the executable itself or permissions")

if __name__ == "__main__":
    main()