import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from .tools_tab import ToolsTab

if __name__ == "__main__":
    print("Launching minimal ToolsTab test window...")
    app = QApplication(sys.argv)
    window = QMainWindow()
    tools_tab = ToolsTab()
    window.setCentralWidget(tools_tab)
    window.setWindowTitle("ToolsTab Test")
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
