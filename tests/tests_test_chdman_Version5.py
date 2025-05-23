import os
import subprocess  # nosec

import pytest


@pytest.fixture
def chdman_path():
    path = os.path.join(os.path.dirname(__file__), "..", "bin", "chdman.exe")
    if not os.path.exists(path):
        pytest.skip("chdman.exe not found")
    return path


def test_chdman_executes(chdman_path):
    result = subprocess.run(  # nosec
        [chdman_path, "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0  # nosec
    assert "usage" in result.stdout.lower()  # nosec
