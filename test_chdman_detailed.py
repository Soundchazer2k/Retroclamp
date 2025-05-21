"""Enhanced test script to diagnose chdman.exe issues in detail."""

import os
import subprocess
import sys
import platform
import ctypes
import hashlib
from pathlib import Path

def get_system_info():
    """Get detailed system information."""
    print("=== System Information ===")
    print(f"OS: {platform.system()} {platform.release()} {platform.version()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Python version: {platform.python_version()}")
    
    # Check if running as admin (Windows only)
    if platform.system() == "Windows":
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            print(f"Running as administrator: {is_admin}")
        except:
            print("Could not determine admin status")

def calculate_file_hash(file_path):
    """Calculate MD5 hash of a file."""
    try:
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            # Read in 4MB chunks
            for chunk in iter(lambda: f.read(4096 * 1024), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except Exception as e:
        return f"Error calculating hash: {str(e)}"

def check_chdman_file(chdman_path):
    """Perform detailed checks on the chdman.exe file."""
    print("\n=== CHDMAN File Analysis ===")
    
    if not os.path.exists(chdman_path):
        print(f"ERROR: File does not exist: {chdman_path}")
        return False
    
    # Get file stats
    stats = os.stat(chdman_path)
    print(f"File path: {chdman_path}")
    print(f"File size: {stats.st_size:,} bytes")
    print(f"File MD5 hash: {calculate_file_hash(chdman_path)}")
    
    # Check file signature (Windows only)
    if platform.system() == "Windows":
        try:
            # Use PowerShell to check file signature
            cmd = f'powershell -Command "Get-AuthenticodeSignature \'{chdman_path}\' | Format-List"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            print("\nFile Signature Information:")
            print(result.stdout)
        except Exception as e:
            print(f"Error checking file signature: {str(e)}")
    
    return True

def check_dependencies(chdman_path):
    """Check for missing dependencies using Dependency Walker equivalent."""
    print("\n=== Dependency Check ===")
    
    if platform.system() != "Windows":
        print("Dependency check is only available on Windows")
        return
    
    try:
        # Use PowerShell and dumpbin (if available) to check dependencies
        cmd = f'powershell -Command "if (Get-Command dumpbin -ErrorAction SilentlyContinue) {{ dumpbin /DEPENDENTS \'{chdman_path}\' }} else {{ Write-Output \'dumpbin not available. Install Visual Studio with C++ tools to use this feature.\' }}"'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if "dumpbin not available" in result.stdout:
            print(result.stdout)
        else:
            print("Required DLLs:")
            for line in result.stdout.splitlines():
                if ".dll" in line.lower():
                    print(f"  {line.strip()}")
    except Exception as e:
        print(f"Error checking dependencies: {str(e)}")

def test_chdman_with_args(chdman_path):
    """Test chdman.exe with different arguments to diagnose issues."""
    print("\n=== Testing CHDMAN with Different Arguments ===")
    
    # List of test commands to try
    test_commands = [
        {"args": ["--help"], "desc": "Help command"},
        {"args": ["--version"], "desc": "Version command"},
        {"args": ["info"], "desc": "Info command without parameters"},
    ]
    
    for test in test_commands:
        print(f"\nTesting: {test['desc']} ({' '.join(test['args'])})")
        try:
            cmd = [chdman_path] + test["args"]
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
                timeout=5  # Add timeout to prevent hanging
            )
            
            print(f"Return code: {result.returncode}")
            
            if result.stdout:
                print("Standard output:")
                print(result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
            
            if result.stderr:
                print("Standard error:")
                print(result.stderr[:200] + "..." if len(result.stderr) > 200 else result.stderr)
                
        except subprocess.TimeoutExpired:
            print("ERROR: Command timed out after 5 seconds")
        except Exception as e:
            print(f"ERROR: {str(e)}")

def test_alternative_execution(chdman_path):
    """Test alternative ways to execute the file."""
    print("\n=== Testing Alternative Execution Methods ===")
    
    if platform.system() != "Windows":
        print("Alternative execution tests are only for Windows")
        return
    
    # Test with cmd.exe explicit call
    print("\nTesting with cmd.exe:")
    try:
        cmd = f'cmd.exe /c "{chdman_path}" --help'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Return code: {result.returncode}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Exception: {str(e)}")
    
    # Test with PowerShell
    print("\nTesting with PowerShell:")
    try:
        cmd = f'powershell -Command "& \'{chdman_path}\' --help"'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Return code: {result.returncode}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Exception: {str(e)}")

def main():
    """Main function."""
    print("=== CHDMAN Enhanced Diagnostic Tool ===")
    
    # Get system information
    get_system_info()
    
    # Find chdman.exe
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bin_dir = os.path.join(script_dir, "bin")
    chdman_path = os.path.join(bin_dir, "chdman.exe")
    
    if not os.path.exists(chdman_path):
        print(f"\nERROR: chdman.exe not found at {chdman_path}")
        return
    
    # Check chdman.exe file
    if check_chdman_file(chdman_path):
        # Check dependencies
        check_dependencies(chdman_path)
        
        # Test with different arguments
        test_chdman_with_args(chdman_path)
        
        # Test alternative execution methods
        test_alternative_execution(chdman_path)
    
    print("\n=== Diagnostic Summary ===")
    print("Based on the tests, the chdman.exe file exists but cannot be executed properly.")
    print("Possible solutions:")
    print("1. Replace the chdman.exe file with a known working version")
    print("2. Check for missing dependencies and install them")
    print("3. Try running the application as administrator")
    print("4. Check Windows security settings that might be blocking execution")

if __name__ == "__main__":
    main()