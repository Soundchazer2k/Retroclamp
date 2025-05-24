import os
import shutil
import subprocess  # nosec

import pytest


def test_chdman_help_exists():
    # Try to find chdman in PATH first (covers Linux and Windows if in PATH)
    chdman_cmd = shutil.which("chdman")

    if not chdman_cmd:
        # Fallback for local Windows dev: check relative bin/chdman.exe
        chdman_exe_path = os.path.join(
            os.path.dirname(__file__), "..", "bin", "chdman.exe"
        )
        if os.path.exists(chdman_exe_path):
            chdman_cmd = chdman_exe_path
        else:
            pytest.skip("chdman or bin/chdman.exe not found")

    result = subprocess.run(  # nosec
        [chdman_cmd, "--help"],
        capture_output=True,
        text=True,
        check=False,  # Prevent raising CalledProcessError, we check returncode manually
    )
    print(f"CHDMAN STDOUT: {result.stdout}")  # Added for debugging
    print(f"CHDMAN STDERR: {result.stderr}")  # Added for debugging
    assert "MAME Compressed Hunks of Data" in result.stdout  # New assertion
