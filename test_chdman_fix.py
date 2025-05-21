"""Test script to verify the fix for chdman.exe execution."""

import os
import subprocess
import sys
from pathlib import Path

def test_chdman_with_proper_params():
    """Test chdman.exe with proper parameters."""
    print("=== Testing CHDMAN with Proper Parameters ===")
    
    # Get the path to chdman.exe
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bin_dir = os.path.join(script_dir, "bin")
    chdman_path = os.path.join(bin_dir, "chdman.exe")
    
    if not os.path.exists(chdman_path):
        print(f"ERROR: chdman.exe not found at {chdman_path}")
        return False
    
    # Create a temporary directory for testing
    temp_dir = os.path.join(script_dir, "temp_test")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create a small test file
    test_file = os.path.join(temp_dir, "test.bin")
    with open(test_file, "wb") as f:
        f.write(b"\x00" * 1024)  # 1KB file
    
    # Output file
    output_file = os.path.join(temp_dir, "test.chd")
    
    # Try to create a CHD file
    print(f"Creating CHD from {test_file} to {output_file}")
    try:
        cmd = [chdman_path, "createhd", "-i", test_file, "-o", output_file, "-f"]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"Return code: {result.returncode}")
        print(f"Output: {result.stdout}")
        
        if result.stderr:
            print(f"Error: {result.stderr}")
        
        # Check if the output file was created
        if os.path.exists(output_file):
            print(f"SUCCESS: Output file created at {output_file}")
            return True
        else:
            print(f"ERROR: Output file not created at {output_file}")
            return False
    
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        return False
    finally:
        # Clean up
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
                print(f"Cleaned up test output file: {output_file}")
            except:
                pass
        
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
                print(f"Cleaned up test input file: {test_file}")
            except:
                pass
        
        try:
            os.rmdir(temp_dir)
            print(f"Removed test directory: {temp_dir}")
        except:
            pass

def main():
    """Main function."""
    print("=== CHDMAN Fix Verification Tool ===")
    
    success = test_chdman_with_proper_params()
    
    print("\n=== Test Summary ===")
    if success:
        print("✅ The fix appears to be working! chdman.exe can now be executed properly.")
        print("The application should now be able to compress files correctly.")
    else:
        print("❌ The fix did not resolve the issue. chdman.exe still cannot be executed properly.")
        print("Additional troubleshooting may be required.")

if __name__ == "__main__":
    main()