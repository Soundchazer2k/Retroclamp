from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from gui.m3u_tab import M3UTab
from tools.scummvm_generator import ScummVMGenerator

print("RUNNING tools_tab.py FROM:", __file__)


class ToolsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- QTabWidget for Tool Panels ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("toolsTabWidget")
        # Match tab styling to compression section
        # (if needed, copy stylesheet from main.py)
        self.tab_widget.setStyleSheet(
            """
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #444;
                border-bottom: none;
                border-radius: 4px 4px 0 0;
                background: #333;
                color: #ccc;
            }
            QTabBar::tab:selected {
                background: #6272a4;
                color: #f8f8f2;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                top: -1px;
            }
        """
        )

        self.m3u_tab = M3UTab(self)
        self.scummvm_tab = ScummVMGenerator(self)
        self.tab_widget.addTab(self.m3u_tab, "M3U Playlist Tool")
        self.tab_widget.addTab(self.scummvm_tab, "SCUMMVM Generator")

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
