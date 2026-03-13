"""Bold/Elevated card component for RetroClamp navigation cards."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ActionCard(QWidget):
    """A clickable card with emoji icon, accent bar, title, and description.

    Renders as ~180×160px with Dracula palette styling, drop shadow,
    and hover state with border lift and increased shadow blur.
    """

    clicked = Signal()

    # Dracula palette constants
    _BG = "#353749"
    _BORDER_NORMAL = "#44475a"
    _BORDER_HOVER = "#6272a4"
    _ACCENT = "#bd93f9"
    _FG = "#f8f8f2"
    _MUTED = "#6272a4"

    def __init__(
        self,
        icon: str,
        title: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon = icon
        self._title = title
        self._description = description
        self._hovered = False

        self._setup_ui()
        self._setup_shadow()
        self._apply_style(hovered=False)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(180, 160)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        # Icon label
        self._icon_label = QLabel(self._icon)
        icon_font = QFont()
        icon_font.setPointSize(22)
        self._icon_label.setFont(icon_font)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._icon_label)

        # Purple accent bar (32×3px)
        self._accent_bar = QWidget()
        self._accent_bar.setFixedSize(32, 3)
        self._accent_bar.setStyleSheet(
            f"background-color: {self._ACCENT}; border-radius: 2px;"
        )
        layout.addWidget(self._accent_bar)

        layout.addSpacing(2)

        # Title
        self._title_label = QLabel(self._title)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setWeight(QFont.Weight.DemiBold)
        self._title_label.setFont(title_font)
        self._title_label.setWordWrap(True)
        layout.addWidget(self._title_label)

        # Description
        self._desc_label = QLabel(self._description)
        desc_font = QFont()
        desc_font.setPointSize(9)
        self._desc_label.setFont(desc_font)
        self._desc_label.setWordWrap(True)
        layout.addWidget(self._desc_label)

        layout.addStretch()

    def _setup_shadow(self) -> None:
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(20)
        self._shadow.setOffset(0, 4)
        self._shadow.setColor(QColor(0, 0, 0, 128))
        self.setGraphicsEffect(self._shadow)

    def _apply_style(self, hovered: bool) -> None:
        border_color = self._BORDER_HOVER if hovered else self._BORDER_NORMAL
        self.setStyleSheet(
            f"""
            ActionCard {{
                background-color: {self._BG};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )
        self._title_label.setStyleSheet(f"color: {self._FG};")
        self._desc_label.setStyleSheet(f"color: {self._MUTED};")

        blur = 28 if hovered else 20
        self._shadow.setBlurRadius(blur)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = True
        self._apply_style(hovered=True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = False
        self._apply_style(hovered=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
