"""
settings.py - Persistent settings for RetroClamp (CHDMAN path, etc.)
"""

from PySide6.QtCore import QSettings


def save_chdman_path(path: str) -> None:
    """Save the CHDMAN executable path to persistent settings."""
    settings = QSettings("RetroClamp", "RetroClampApp")
    settings.setValue("chdman_path", path)


def load_chdman_path() -> str:
    """Load the CHDMAN executable path from persistent settings."""
    settings = QSettings("RetroClamp", "RetroClampApp")
    return str(settings.value("chdman_path", "", type=str))
