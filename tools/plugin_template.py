"""
RetroClamp Plugin Template
-------------------------
Use this template as a starting point for new RetroClamp tool plugins.
Fill in the required metadata and implement the register_tab function.
"""

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
from typing import Dict, List

PLUGIN_DEPENDENCIES: List[str] = []

#: Define expected config keys and types for validation (optional)
#: Example: {"max_workers": int, "log_level": str}
PLUGIN_CONFIG_SCHEMA: Dict[str, type] = {}

#: Minimum compatible RetroClamp app version (inclusive, optional)
PLUGIN_MIN_APP_VERSION = "1.0.0"

#: Maximum compatible RetroClamp app version (exclusive, optional)
PLUGIN_MAX_APP_VERSION = "2.0.0"


def register_tab(main_window):
    """
    Register the plugin's tab with the main application window.

    This function is called by the plugin system to add your plugin's UI
    as a new tab in the application's tools section. It expects the main window
    to have a `tools_tab` attribute with a `tab_widget` (QTabWidget).

    Args:
        main_window: The main application window instance.
    """
    # from gui.my_plugin_tab import MyPluginTab
    # if hasattr(main_window, "tools_tab") and \
    #     hasattr(main_window.tools_tab, "tab_widget"):
    #     tab = MyPluginTab(main_window.tools_tab)
    #     main_window.tools_tab.tab_widget.addTab(tab, "My Plugin")
    #     print(
    #         "My Plugin tab registered."
    #     )
    # else:
    #     print(
    #         "Could not register My Plugin tab: tools_tab or tab_widget not found "
    #         "on main_window."

    #     )
    pass
