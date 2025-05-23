import zipfile


def create_test_zip_with_disk_images(tmp_path):
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("disk1.bin", b"\x00" * 1024)
        zf.writestr("disk1.cue", "Cue file")
    return zip_path


def test_extract_and_scan(tmp_path):
    zip_path = create_test_zip_with_disk_images(tmp_path)
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)
    found_bin = any(f.name.endswith(".bin") for f in extract_dir.iterdir())
    found_cue = any(f.name.endswith(".cue") for f in extract_dir.iterdir())
    assert found_bin  # nosec
    assert found_cue  # nosec
