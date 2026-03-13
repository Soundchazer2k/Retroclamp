"""Tools view — loads plugin panels into a QStackedWidget with a back-button."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.components.action_card import ActionCard
from gui.components.section_label import SectionLabel


class ToolsView(QWidget):
    """Tools hub that shows a card grid of available tool plugins.

    Clicking a card loads that plugin's panel into a QStackedWidget and
    shows a ← Back button to return to the hub.
    """

    # Dracula palette
    _BG = "#282a36"
    _FG = "#f8f8f2"
    _MUTED = "#6272a4"
    _SURFACE = "#313444"
    _PURPLE = "#bd93f9"
    _RED = "#ff5555"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._panels: dict[str, QWidget] = {}
        self._setup_ui()
        self._load_plugins()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"background: {self._BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget(self)
        root.addWidget(self._stack)

        # -- Page 0: hub --
        self._hub_page = QWidget()
        self._hub_page.setStyleSheet(f"background: {self._BG};")
        hub_root = QVBoxLayout(self._hub_page)
        hub_root.setContentsMargins(0, 0, 0, 0)
        hub_root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background: {self._BG}; border: none;")

        content = QWidget()
        content.setStyleSheet(f"background: {self._BG};")
        self._hub_layout = QVBoxLayout(content)
        self._hub_layout.setContentsMargins(24, 24, 24, 24)
        self._hub_layout.setSpacing(20)

        # Header
        header_lbl = QLabel("Tools")
        header_lbl.setStyleSheet(
            f"color: {self._FG}; font-size: 22px; font-weight: 700;"
            " background: transparent; border: none;"
        )
        self._hub_layout.addWidget(header_lbl)

        self._hub_layout.addWidget(SectionLabel("Available Tools"))

        # Card container
        self._card_row = QHBoxLayout()
        self._card_row.setSpacing(16)
        self._card_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._hub_layout.addLayout(self._card_row)

        # Placeholder shown when no plugins loaded
        self._no_tools_lbl = QLabel("No tools available.")
        self._no_tools_lbl.setStyleSheet(
            f"color: {self._MUTED}; font-size: 13px;"
            " background: transparent; border: none;"
        )
        self._no_tools_lbl.hide()
        self._hub_layout.addWidget(self._no_tools_lbl)

        self._hub_layout.addStretch()

        scroll.setWidget(content)
        hub_root.addWidget(scroll)
        self._stack.addWidget(self._hub_page)  # index 0

        # -- Page 1: plugin panel container --
        self._panel_page = QWidget()
        self._panel_page.setStyleSheet(f"background: {self._BG};")
        panel_root = QVBoxLayout(self._panel_page)
        panel_root.setContentsMargins(0, 0, 0, 0)
        panel_root.setSpacing(0)

        # Back bar
        back_bar = QWidget()
        back_bar.setFixedHeight(44)
        back_bar.setStyleSheet(
            f"background: {self._SURFACE}; border-bottom: 1px solid #44475a;"
        )
        back_bar_layout = QHBoxLayout(back_bar)
        back_bar_layout.setContentsMargins(12, 0, 12, 0)
        back_bar_layout.setSpacing(8)

        back_btn = QPushButton("← Back to Tools")
        back_btn.setFixedHeight(28)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; color: {self._PURPLE};"
            f"  border: 1px solid {self._PURPLE}; border-radius: 4px;"
            f"  padding: 0 12px; font-size: 12px;"
            f"}}"
            f"QPushButton:hover {{ background: rgba(189,147,249,0.12); }}"
        )
        back_btn.clicked.connect(self._show_hub)
        back_bar_layout.addWidget(back_btn)

        self._panel_title_lbl = QLabel("")
        self._panel_title_lbl.setStyleSheet(
            f"color: {self._FG}; font-size: 14px; font-weight: 600;"
            " background: transparent; border: none;"
        )
        back_bar_layout.addWidget(self._panel_title_lbl)
        back_bar_layout.addStretch()

        panel_root.addWidget(back_bar)

        # Stacked area for individual plugin panels
        self._plugin_stack = QStackedWidget()
        self._plugin_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        panel_root.addWidget(self._plugin_stack)

        self._stack.addWidget(self._panel_page)  # index 1

        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Plugin loading
    # ------------------------------------------------------------------

    def _load_plugins(self) -> None:
        """Import TOOL_PLUGINS from tools package and register each panel."""
        try:
            from tools import TOOL_PLUGINS  # type: ignore[import,attr-defined]
        except Exception as exc:  # noqa: BLE001
            self._show_load_error(str(exc))
            return

        loaded = 0
        for module in TOOL_PLUGINS:
            try:
                panel = module.register_panel(self)
            except Exception as exc:  # noqa: BLE001
                # Plugin failed — add a placeholder card
                self._add_error_card(getattr(module, "__name__", str(module)), str(exc))
                continue

            name: str = getattr(
                module, "PLUGIN_NAME", getattr(module, "__name__", "Tool")
            )
            icon: str = getattr(module, "PLUGIN_ICON", "🔧")
            description: str = getattr(module, "PLUGIN_DESCRIPTION", "")

            if panel is None:
                # Plugin is Coming Soon — add a dimmed, non-clickable card
                self._add_coming_soon_card(name, icon)
                continue

            self._register_panel(name, icon, description, panel)
            loaded += 1

        if loaded == 0 and self._card_row.count() == 0:
            self._no_tools_lbl.show()

    def _register_panel(
        self,
        name: str,
        icon: str,
        description: str,
        panel: QWidget,
    ) -> None:
        """Add a card to the hub and wire it to show the panel."""
        card = ActionCard(icon, name, description, parent=self._hub_page)
        card.clicked.connect(lambda n=name, p=panel: self._open_panel(n, p))
        self._card_row.addWidget(card)
        self._panels[name] = panel
        self._plugin_stack.addWidget(panel)

    def _add_coming_soon_card(self, name: str, icon: str) -> None:
        """Add a dimmed, non-clickable coming-soon card for an unavailable plugin."""
        from PySide6.QtWidgets import QGraphicsOpacityEffect  # noqa: PLC0415

        card = ActionCard(icon, name, "Coming soon", parent=self._hub_page)
        card.setEnabled(False)
        card.setCursor(Qt.CursorShape.ForbiddenCursor)
        card.setToolTip(f"{name} — coming in a future release")
        opacity = QGraphicsOpacityEffect(card)
        opacity.setOpacity(0.5)
        card.setGraphicsEffect(opacity)
        self._card_row.addWidget(card)

    def _add_error_card(self, plugin_name: str, error: str) -> None:
        """Add a disabled error card for a plugin that failed to load."""
        card = ActionCard(
            "⚠", plugin_name, f"Load error: {error[:40]}", parent=self._hub_page
        )
        card.setEnabled(False)
        card.setToolTip(f"Plugin failed to load:\n{error}")
        self._card_row.addWidget(card)

    def _show_load_error(self, error: str) -> None:
        lbl = QLabel(f"⚠ Could not load tools package:\n{error}")
        lbl.setStyleSheet(
            f"color: {self._RED}; padding: 16px; background: transparent;"
        )
        lbl.setWordWrap(True)
        self._hub_layout.insertWidget(2, lbl)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _open_panel(self, name: str, panel: QWidget) -> None:
        self._panel_title_lbl.setText(name)
        self._plugin_stack.setCurrentWidget(panel)
        self._stack.setCurrentIndex(1)

    def _show_hub(self) -> None:
        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def panel(self, name: str) -> QWidget | None:
        """Return a registered plugin panel by name."""
        return self._panels.get(name)
