from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from gui.m3u_tab import M3UTab
from tools.scummvm_generator import ScummVMGenerator

# Debug print removed - was causing early execution


class ToolsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- QTabWidget for Tool Panels ---
        # Create tab widget (styling handled by unified stylesheet)
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("toolsTabWidget")

        self.m3u_tab = M3UTab(self)
        self.scummvm_tab = ScummVMGenerator(self)
        self.tab_widget.addTab(self.m3u_tab, "M3U Playlist Tool")
        self.tab_widget.addTab(self.scummvm_tab, "SCUMMVM Generator")

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
