import os
import subprocess
import pytest

@pytest.fixture
def chdman_path():
    path = os.path.join(os.path.dirname(__file__), "..", "bin", "chdman.exe")
    if not os.path.exists(path):
        pytest.skip("chdman.exe not found")
    return path

def test_chdman_executes(chdman_path):
    result = subprocess.run([chdman_path, "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()