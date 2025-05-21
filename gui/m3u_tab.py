from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem, QTextEdit
)
from PySide6.QtCore import Qt

class M3UTab(QWidget):
    """M3U Playlist Tool for managing multi-disc games."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Title
        title = QLabel("M3U Playlist Tool")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("Automatically detect multi-disc games and generate M3U playlists for seamless multi-disc emulation.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Game library directory picker
        dir_layout = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("Select game library folder...")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_folder)
        dir_layout.addWidget(QLabel("Game Library Folder:"))
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(self.browse_btn)
        layout.addLayout(dir_layout)

        # Table of detected multi-disc games
        self.games_table = QTableWidget()
        self.games_table.setColumnCount(4)
        self.games_table.setHorizontalHeaderLabels(["Game Name", "Discs Found", "M3U Exists", "Action"])
        layout.addWidget(self.games_table)

        # Batch action buttons
        batch_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Scan for Multi-Disc Games")
        self.create_all_btn = QPushButton("Create All M3Us")
        self.organize_btn = QPushButton("Organize All Games")
        batch_layout.addWidget(self.scan_btn)
        batch_layout.addWidget(self.create_all_btn)
        batch_layout.addWidget(self.organize_btn)
        layout.addLayout(batch_layout)

        # Status/log output
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        layout.addWidget(self.log_panel)

        self.setLayout(layout)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Game Library Folder")
        if folder:
            self.dir_edit.setText(folder)

    # Placeholder for backend logic:
    # def scan_for_multidisc_games(self): ...
    # def create_m3u_for_game(self, ...): ...
    # def organize_games(self, ...): ...
