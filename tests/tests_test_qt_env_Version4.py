from PySide6.QtCore import QMutex, QObject

def test_qt_minimal(qtbot):
    m = QMutex()
    o = QObject()
    assert m is not None
    assert o is not None