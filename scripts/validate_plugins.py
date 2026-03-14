#!/usr/bin/env python3
"""Basic plugin validation for Retroclamp"""

import logging
import sys
from pathlib import Path


def main():
    tools_dir = Path("tools")
    if not tools_dir.exists():
        print("No tools directory found")
        return

    plugins = [f for f in tools_dir.glob("*.py") if f.name != "__init__.py"]
    if not plugins:
        print("No plugins found")
        return

    issues = []
    for plugin in plugins:
        try:
            with open(plugin, encoding="utf-8") as f:
                content = f.read()

            if "PLUGIN_NAME" not in content:
                issues.append(f"{plugin.name}: Missing PLUGIN_NAME")
            if "def register_panel" not in content:
                issues.append(f"{plugin.name}: Missing register_panel function")

        except Exception as e:
            logging.warning(f"Exception in validate_plugins: {e}")
            continue

    if issues:
        print("Plugin API Issues:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print(f"[OK] All {len(plugins)} plugins validated")


if __name__ == "__main__":
    main()
