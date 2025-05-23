import zipfile

import pytest


@pytest.fixture
def zip_with_files(tmp_path):
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("file1.txt", "hello")
    return zip_path


def test_zip_extraction(zip_with_files, tmp_path):
    with zipfile.ZipFile(zip_with_files, "r") as zf:
        zf.extractall(tmp_path)
    assert (tmp_path / "file1.txt").exists()  # nosec
