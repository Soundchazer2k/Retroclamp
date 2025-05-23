import os
import subprocess  # nosec

import pytest


def test_chdman_help_exists():
    chdman_path = os.path.join(os.path.dirname(__file__), "..", "bin", "chdman.exe")
    if not os.path.exists(chdman_path):
        pytest.skip("chdman.exe not found")
    result = subprocess.run(  # nosec
        [chdman_path, "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0  # nosec
