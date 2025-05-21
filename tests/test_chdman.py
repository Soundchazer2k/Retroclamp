import os
import subprocess
import pytest

def test_chdman_help_exists():
    chdman_path = os.path.join(os.path.dirname(__file__), "..", "bin", "chdman.exe")
    if not os.path.exists(chdman_path):
        pytest.skip("chdman.exe not found")
    result = subprocess.run([chdman_path, "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert result.returncode == 0