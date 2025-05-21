"""Minimal test file to verify pytest setup."""

def test_pytest_runs():
    """Test that pytest is working."""
    assert True

class TestSimple:
    """Simple test class to verify class-based tests work."""
    
    def test_class_based(self):
        """Test that class-based tests are collected."""
        assert True
