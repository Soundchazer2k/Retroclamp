"""Tools module for RetroClamp.

This module provides a plugin system for loading and managing tool plugins.
Each plugin should define a register_panel function that accepts a ToolsView
and returns an Optional[QWidget] to embed, or None for a coming-soon card.
"""

import importlib
import os
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtWidgets import QWidget


class ToolPlugin:
    """Represents a tool plugin.

    Attributes:
        name: Name of the plugin
        module_name: Name of the module
        description: Description of the plugin
        version: Version of the plugin
        author: Author of the plugin
        register_func: Function to register the plugin
    """

    def __init__(
        self,
        name: str,
        module_name: str,
        description: str = "",
        version: str = "1.0.0",
        author: str = "",
        register_func: Optional[Callable[..., Optional[QWidget]]] = None,
    ):
        """Initialize the ToolPlugin.

        Args:
            name: Name of the plugin
            module_name: Name of the module
            description: Description of the plugin
            version: Version of the plugin
            author: Author of the plugin
            register_func: Function to register the plugin
        """
        self.name = name
        self.module_name = module_name
        self.description = description
        self.version = version
        self.author = author
        self.register_func = register_func

    def register(self, parent: QWidget) -> Optional[QWidget]:
        """Register the plugin with the parent widget.

        Args:
            parent: Parent widget (ToolsView) to register with

        Returns:
            QWidget to embed in the tools panel, or None for a coming-soon card
        """
        if self.register_func:
            return self.register_func(parent)
        return None


class ToolManager:
    """Manager for tool plugins.

    This class provides functionality for discovering, loading, and managing
    tool plugins.
    """

    def __init__(self, tools_dir: Optional[str] = None):
        """Initialize the ToolManager.

        Args:
            tools_dir: Directory containing tool plugins
        """
        self.tools_dir = tools_dir or os.path.dirname(__file__)
        self.plugins: Dict[str, ToolPlugin] = {}

    def register_all_plugins(self, parent: QWidget) -> Dict[str, Optional[QWidget]]:
        """Register all discovered plugins to the given parent widget.

        Each plugin's registration is wrapped in try/except to ensure
        error isolation. Any plugin that fails to register will be skipped,
        and the error will be reported without crashing the app.

        Returns:
            Mapping of module_name → QWidget (or None for coming-soon cards).
        """
        results: Dict[str, Optional[QWidget]] = {}
        for plugin in self.plugins.values():
            try:
                results[plugin.module_name] = plugin.register(parent)
            except Exception as e:
                print(f"Error registering plugin '{plugin.module_name}': {e}")
                results[plugin.module_name] = None
        return results

    def discover_plugins(self) -> List[ToolPlugin]:
        """Discover available tool plugins.

        Returns:
            List of discovered plugins
        """
        plugins = []

        # Get all Python files in the tools directory
        for filename in os.listdir(self.tools_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]  # Remove .py extension

                try:
                    # Import the module
                    module = importlib.import_module(f"tools.{module_name}")

                    # Check if it has a register_panel function
                    if hasattr(module, "register_panel") and callable(
                        module.register_panel
                    ):
                        # Get plugin metadata
                        name = getattr(module, "PLUGIN_NAME", module_name)
                        description = getattr(module, "PLUGIN_DESCRIPTION", "")
                        version = getattr(module, "PLUGIN_VERSION", "1.0.0")
                        author = getattr(module, "PLUGIN_AUTHOR", "")

                        # Check for plugin dependencies
                        dependencies = getattr(module, "PLUGIN_DEPENDENCIES", [])
                        missing = []
                        for dep in dependencies:
                            try:
                                importlib.import_module(f"tools.{dep}")
                            except Exception:
                                missing.append(dep)
                        if missing:
                            print(
                                f"Plugin '{module_name}' skipped: missing "
                                f"dependencies: "
                                f"{', '.join(missing)}"
                            )
                            continue

                        # Check for plugin config schema and validate config
                        config_schema = getattr(module, "PLUGIN_CONFIG_SCHEMA", None)
                        if config_schema:
                            # For demonstration, use an empty config
                            # (could load from file/settings)
                            config: Dict[str, Any] = {}

                            config_errors = []
                            for key, typ in config_schema.items():
                                if key not in config:
                                    config_errors.append(f"Missing config key: {key}")
                                elif not isinstance(config[key], typ):
                                    config_errors.append(
                                        f"Config key '{key}' should be {typ.__name__}, "
                                        f"got "
                                        f"{type(config[key]).__name__}"
                                    )
                            if config_errors:
                                print(
                                    f"Plugin '{module_name}' skipped: config "
                                    f"validation "
                                    f"failed: {', '.join(config_errors)}"
                                )
                                continue

                        # Version compatibility check
                        try:
                            from version import __version__ as app_version
                        except ImportError:
                            app_version = "0.0.0"

                        def parse_ver(s):
                            return tuple(int(x) for x in s.split(".") if x.isdigit())

                        min_ver = getattr(module, "PLUGIN_MIN_APP_VERSION", None)
                        max_ver = getattr(module, "PLUGIN_MAX_APP_VERSION", None)
                        app_ver_tuple = parse_ver(app_version)
                        if min_ver and app_ver_tuple < parse_ver(min_ver):
                            print(
                                f"Plugin '{module_name}' skipped: requires app version "
                                f">= {min_ver}"
                            )
                            continue
                        if max_ver and app_ver_tuple >= parse_ver(max_ver):
                            print(
                                f"Plugin '{module_name}' skipped: requires app version "
                                f"< {max_ver}"
                            )
                            continue

                        # Create plugin object
                        plugin = ToolPlugin(
                            name=name,
                            module_name=module_name,
                            description=description,
                            version=version,
                            author=author,
                            register_func=module.register_panel,
                        )

                        plugins.append(plugin)
                        self.plugins[module_name] = plugin
                except Exception as e:
                    print(f"Error loading plugin {module_name}: {str(e)}")

        return plugins

    def load_plugins(self, parent: QWidget) -> Dict[str, Optional[QWidget]]:
        """Load and register all discovered plugins.

        Args:
            parent: Parent widget (ToolsView) to register plugins with

        Returns:
            Mapping of plugin module_name → QWidget returned by register_panel
            (or None when a plugin returns None / fails to load).
        """
        # Discover plugins if not already done
        if not self.plugins:
            self.discover_plugins()

        # Register each plugin and collect widgets
        results: Dict[str, Optional[QWidget]] = {}
        for plugin_name, plugin in self.plugins.items():
            try:
                results[plugin_name] = plugin.register(parent)
            except Exception as e:
                print(f"Error registering plugin {plugin_name}: {str(e)}")
                results[plugin_name] = None

        return results

    def get_plugin(self, name: str) -> Optional[ToolPlugin]:
        """Get a plugin by name.

        Args:
            name: Name of the plugin

        Returns:
            Plugin object or None if not found
        """
        return self.plugins.get(name)

    def get_all_plugins(self) -> Dict[str, ToolPlugin]:
        """Get all discovered plugins.

        Returns:
            Dictionary of plugin name to plugin object
        """
        return self.plugins


# ---------------------------------------------------------------------------
# Module-level plugin list — imported by gui/views/tools_view.py
# Each entry must expose: register_panel(tools_view) -> Optional[QWidget]
# Optionally: PLUGIN_NAME, PLUGIN_ICON, PLUGIN_DESCRIPTION
# ---------------------------------------------------------------------------
from . import bios_validator, m3u_generator, scummvm_generator  # noqa: E402

TOOL_PLUGINS = [m3u_generator, scummvm_generator, bios_validator]
