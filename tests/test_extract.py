import zipfile
import pytest

def test_extract_bin_file(tmp_path):
    zf_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zf_path, "w") as zf:
        zf.writestr("disk1.bin", b"abc")
    with zipfile.ZipFile(zf_path, "r") as zf:
        zf.extract("disk1.bin", path=tmp_path)
    assert (tmp_path / "disk1.bin").exists()