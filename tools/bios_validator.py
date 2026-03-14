"""BIOS Validator tool stub for RetroClamp.

This plugin is a Coming Soon stub. It returns None from register_panel,
which causes ToolsView to render it as a coming-soon card.
"""

from __future__ import annotations

# Plugin metadata
PLUGIN_NAME = "BIOS Validator"
PLUGIN_ICON = "🔬"
PLUGIN_DESCRIPTION = "Validate BIOS files against known-good checksums"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "RetroClamp Team"


def register_panel(tools_view: object) -> None:
    """Return None — plugin is Coming Soon.

    ToolsView renders a dimmed, non-clickable coming-soon card when
    register_panel returns None.
    """
    return None
