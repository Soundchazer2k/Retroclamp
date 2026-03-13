"""Section label component — uppercased, muted, small-caps style."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget


class SectionLabel(QLabel):
    """A small, uppercased section heading label using the Dracula muted color.

    Automatically uppercases provided text and applies consistent styling:
    11pt, weight 600, #6272a4, 1px letter-spacing approximated via stylesheet.
    """

    _COLOR = "#6272a4"

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text.upper(), parent)
        self._apply_style()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def setText(self, text: str) -> None:  # type: ignore[override]
        """Override to auto-uppercase text."""
        super().setText(text.upper())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_style(self) -> None:
        font = QFont()
        font.setPointSize(9)
        font.setWeight(QFont.Weight.DemiBold)
        self.setFont(font)
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {self._COLOR};
                letter-spacing: 1px;
                background: transparent;
                border: none;
            }}
            """
        )
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
