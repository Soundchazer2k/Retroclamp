"""
Plugin Test Template for RetroClamp
----------------------------------
Use this template to add tests for your tool plugins. Place this file as
test_<plugin_name>.py in the tools/ directory, or in a dedicated test folder.
"""

import importlib
import os
import sys
import unittest

PLUGIN_MODULE = "batch_processor"  # Change to your plugin's module name


class TestPlugin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure project root is in sys.path for import
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        try:
            cls.plugin = importlib.import_module(f"tools.{PLUGIN_MODULE}")
        except ModuleNotFoundError:
            # Fallback: try importing as a local module (for direct runs)
            cls.plugin = importlib.import_module(PLUGIN_MODULE)

    def test_metadata(self):
        """Test that required plugin metadata fields are present and valid."""
        self.assertTrue(hasattr(self.plugin, "PLUGIN_NAME"))
        self.assertTrue(hasattr(self.plugin, "PLUGIN_VERSION"))
        self.assertTrue(hasattr(self.plugin, "PLUGIN_DESCRIPTION"))
        self.assertTrue(hasattr(self.plugin, "PLUGIN_AUTHOR"))
        self.assertIsInstance(self.plugin.PLUGIN_NAME, str)
        self.assertIsInstance(self.plugin.PLUGIN_VERSION, str)

    def test_register_panel_callable(self):
        """Test that the register_panel function exists and is callable."""
        self.assertTrue(hasattr(self.plugin, "register_panel"))
        self.assertTrue(callable(self.plugin.register_panel))

    # Add more tests here as needed for your plugin's specific logic


if __name__ == "__main__":
    unittest.main()
