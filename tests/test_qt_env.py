from PySide6.QtCore import QMutex


def test_qt_mutex():
    m = QMutex()
    assert m is not None  # nosec
