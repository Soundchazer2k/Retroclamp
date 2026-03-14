"""
RetroClamp Plugin Template
-------------------------
Use this template as a starting point for new RetroClamp tool plugins.
Fill in the required metadata and implement the register_panel function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

# === Plugin Metadata ===
#: Name of the plugin (required for plugin discovery)
PLUGIN_NAME = "My Plugin"

#: Version of the plugin (semantic versioning recommended)
PLUGIN_VERSION = "0.1.0"

#: Short description of the plugin's purpose
PLUGIN_DESCRIPTION = "Describe what your plugin does."

#: Author of the plugin
PLUGIN_AUTHOR = "Your Name"

#: List dependencies for this plugin (by module name, optional)
PLUGIN_DEPENDENCIES: list[str] = []

#: Define expected config keys and types for validation (optional)
#: Example: {"max_workers": int, "log_level": str}
PLUGIN_CONFIG_SCHEMA: dict[str, type] = {}

#: Minimum compatible RetroClamp app version (inclusive, optional)
PLUGIN_MIN_APP_VERSION = "1.0.0"

#: Maximum compatible RetroClamp app version (exclusive, optional)
PLUGIN_MAX_APP_VERSION = "2.0.0"


def register_panel(tools_view: QWidget) -> QWidget:
    """Register this plugin and return its panel widget.

    This function is called by the plugin system to obtain your plugin's UI
    widget for embedding in the Tools view.

    Args:
        tools_view: The ToolsView instance that will host this panel.

    Returns:
        A QWidget subclass representing this plugin's full UI panel.

    Example::

        from PySide6.QtWidgets import QWidget
        from gui.my_plugin_panel import MyPluginPanel

        def register_panel(tools_view: "QWidget") -> "QWidget":
            return MyPluginPanel()
    """
    from PySide6.QtWidgets import QWidget  # noqa: PLC0415

    return QWidget()  # Replace with your actual panel widget
