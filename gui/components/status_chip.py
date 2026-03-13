"""Status chip component for batch item state display."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QPropertyAnimation, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget


class StatusChip(QLabel):
    """A compact colored pill label representing operation state.

    States
    ------
    queued     : muted blue-grey (#6272a4)
    processing : cyan (#8be9fd) with pulsing opacity animation
    done       : green (#50fa7b)
    error      : red (#ff5555)
    """

    _COLORS: dict[str, str] = {
        "queued": "#6272a4",
        "processing": "#8be9fd",
        "done": "#50fa7b",
        "error": "#ff5555",
    }

    _LABELS: dict[str, str] = {
        "queued": "Queued",
        "processing": "Processing",
        "done": "Done",
        "error": "Error",
    }

    def __init__(
        self,
        state: str = "queued",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._state = ""
        self._animation: QPropertyAnimation | None = None
        self._opacity_effect: QGraphicsOpacityEffect | None = None

        self._setup_base_style()
        self.setState(state)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def setState(self, state: str) -> None:
        """Update the chip to reflect a new state."""
        if state not in self._COLORS:
            raise ValueError(
                f"Unknown state '{state}'. Valid: {list(self._COLORS.keys())}"
            )

        # Stop any running animation
        self._stop_animation()

        self._state = state
        color = self._COLORS[state]
        label = self._LABELS[state]

        self.setText(label)
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {color}22;
                color: {color};
                border: 1px solid {color}66;
                border-radius: 8px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 600;
            }}
            """
        )

        if state == "processing":
            self._start_pulse()

    @property
    def state(self) -> str:
        return self._state

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _setup_base_style(self) -> None:
        font = QFont()
        font.setPointSize(8)
        font.setWeight(QFont.Weight.DemiBold)
        self.setFont(font)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(20)

    def _start_pulse(self) -> None:
        """Start a pulsing opacity animation for the processing state."""
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(1.0)
        self.setGraphicsEffect(effect)
        self._opacity_effect = effect

        anim = QPropertyAnimation(effect, QByteArray(b"opacity"), self)
        anim.setDuration(800)
        anim.setStartValue(1.0)
        anim.setEndValue(0.4)
        anim.setLoopCount(-1)  # infinite
        anim.start()
        self._animation = anim

    def _stop_animation(self) -> None:
        """Stop and clean up any running animation."""
        if self._animation is not None:
            self._animation.stop()
            self._animation = None
        if self._opacity_effect is not None:
            self.setGraphicsEffect(None)  # type: ignore[arg-type]
            self._opacity_effect = None
