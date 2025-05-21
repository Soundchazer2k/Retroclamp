"""Minimal test to verify Qt environment is working."""
from PySide6.QtCore import QMutex, QObject

def test_qt_minimal(qtbot):
    print("Creating QMutex")
    m = QMutex()
    print("QMutex created")
    print("Creating QObject")
    o = QObject()
    print("QObject created")
    assert True
