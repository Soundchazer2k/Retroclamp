def test_default_compression_profiles():
    from core.compression_profiles import get_default_profiles
    profiles = get_default_profiles()
    assert "zlib" in profiles