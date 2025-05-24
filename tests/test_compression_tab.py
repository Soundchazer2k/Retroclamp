def test_default_compression_profiles():
    from core.compression_profiles import CompressionProfileManager

    manager = CompressionProfileManager()
    # Check if a profile known to use zlib (e.g., dvd_fast) exists and contains zlib
    # Or, more broadly, check if any profile contains zlib in its algorithms
    # For simplicity, let's check if we can retrieve a profile that typically uses zlib.
    dvd_fast_profile = manager.get_profile("dvd_fast")
    assert dvd_fast_profile is not None
    assert "zlib" in dvd_fast_profile.algorithms  # nosec
