import os

def scan_for_bin_files(dir_path):
    return [f for f in os.listdir(dir_path) if f.endswith(".bin")]

def test_scan_for_bin_files(tmp_path):
    file = tmp_path / "game.bin"
    file.write_bytes(b"data")
    found = scan_for_bin_files(tmp_path)
    assert "game.bin" in found