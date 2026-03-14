#!/usr/bin/env python
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from pathlib import Path  # Added for modern path handling
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

from core.chdman import CHDManager, CHDTask, CHDTaskType

# === Plugin Metadata ===
#: Name of the plugin (required for plugin discovery)
PLUGIN_NAME = "Batch Processor"

#: Version of the plugin (semantic versioning recommended)
PLUGIN_VERSION = "1.0"

#: Short description of the plugin's purpose
PLUGIN_DESCRIPTION = "Provides batch processing capabilities for RetroClamp."

#: Author of the plugin
PLUGIN_AUTHOR = "Soundchazer2k"

#: List dependencies for this plugin (by module name, optional)
PLUGIN_DEPENDENCIES: list[str] = []

#: Define expected config keys and types for validation (optional)
#: Example: {"max_workers": int, "log_level": str}
PLUGIN_CONFIG_SCHEMA = {
    "max_workers": int,
    "log_level": str,
}

#: Minimum compatible RetroClamp app version (inclusive, optional)
PLUGIN_MIN_APP_VERSION = "1.0.0"

#: Maximum compatible RetroClamp app version (exclusive, optional)
PLUGIN_MAX_APP_VERSION = "2.0.0"

"""
Batch processor for CHD operations.

This script provides a command-line interface for batch processing
CHD operations using the core/chdman.py module.
"""

# Add the parent directory to the path so we can import the core modules


def register_panel(tools_view: QWidget) -> None:
    """Register this plugin with the Tools view.

    Batch processing is a first-class view in the sidebar and does not provide
    an additional panel in the Tools tab.

    Args:
        tools_view: The ToolsView instance (unused).

    Returns:
        None — no panel widget is contributed.
    """
    return None


def main():
    """Main entry point for the batch processor."""
    parser = argparse.ArgumentParser(description="Batch process CHD operations")
    parser.add_argument(
        "--chdman",
        help="Path to CHDMAN executable (default: auto-detect)",
        default=None,
    )
    parser.add_argument(
        "--operation",
        choices=[
            "compress",
            "extract-cd",
            "extract-dvd",
            "extract-hd",
            "info",
            "verify",
        ],
        required=True,
        help="Operation to perform",
    )
    parser.add_argument("--input", required=True, help="Input file or directory")
    parser.add_argument(
        "--output",
        help="Output file or directory (required for compression/extraction)",
    )
    parser.add_argument(
        "--compression",
        choices=["none", "fast", "normal", "best"],
        default="normal",
        help="Compression level (default: normal)",
    )
    parser.add_argument(
        "--hunk-size",
        type=int,
        default=16384,
        help="Hunk size in bytes (default: 16384)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Verify after operation (default: True)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force overwrite of output files (default: False)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=False,
        help="Process directories recursively (default: False)",
    )

    args = parser.parse_args()

    # Initialize CHDManager
    manager = CHDManager(args.chdman if args.chdman else "chdman")

    # Map operation to task type
    operation_map = {
        "compress": CHDTaskType.COMPRESS,
        "extract-cd": CHDTaskType.EXTRACT_CD,
        "extract-dvd": CHDTaskType.EXTRACT_DVD,
        "extract-hd": CHDTaskType.EXTRACT_HD,
        "info": CHDTaskType.INFO,
        "verify": CHDTaskType.VERIFY,
    }

    task_type = operation_map[args.operation]

    # Process input files
    input_files = get_input_files(args.input, args.recursive)

    if not input_files:
        print(f"No input files found in {args.input}")
        return 1

    print(f"Found {len(input_files)} input files")

    # Create tasks
    for input_file in input_files:
        output_file = None

        if task_type not in [CHDTaskType.INFO, CHDTaskType.VERIFY]:
            if not args.output:
                print(
                    "Error: --output is required for compression/extraction operations"
                )
                return 1

            # If output is a directory, create output file path
            if os.path.isdir(args.output):
                output_name = os.path.basename(input_file)
                output_name = os.path.splitext(output_name)[0]

                if task_type == CHDTaskType.COMPRESS:
                    output_file = os.path.join(args.output, f"{output_name}.chd")
                elif task_type == CHDTaskType.EXTRACT_CD:
                    output_file = os.path.join(args.output, f"{output_name}.cue")
                elif task_type == CHDTaskType.EXTRACT_DVD:
                    output_file = os.path.join(args.output, f"{output_name}.iso")
                elif task_type == CHDTaskType.EXTRACT_HD:
                    output_file = os.path.join(args.output, f"{output_name}.img")
            else:
                output_file = args.output

        task = CHDTask(
            task_type=task_type,
            input_file=input_file,
            output_file=output_file,
            compression_level=args.compression,
            hunk_size=args.hunk_size,
            verify=args.verify,
            force=args.force,
        )

        manager.add_task(task)

    # Execute tasks
    try:
        signals_list = manager.execute_all_tasks()

        # Connect signals for progress reporting
        for i, signals in enumerate(signals_list):
            signals.started.connect(
                lambda msg, i=i: print(f"Task {i + 1}/{len(signals_list)}: {msg}")
            )
            signals.progress.connect(
                lambda pct, msg, i=i: print(
                    f"Task {i + 1}/{len(signals_list)}: {pct:.1f}% - {msg}"
                )
            )
            signals.finished.connect(
                lambda success, msg, i=i: print(
                    f"Task {i + 1}/{len(signals_list)}: "
                    f"{'Completed' if success else 'Failed'} - {msg}"
                )
            )
            signals.error.connect(
                lambda msg, i=i: print(
                    f"Task {i + 1}/{len(signals_list)}: Error - {msg}"
                )
            )

        print("All tasks completed")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1


def get_input_files(input_path: str, recursive: bool = False):
    """
    Get a list of input files from a path.

    Args:
        input_path: Path to input file or directory
        recursive: Whether to search directories recursively

    Returns:
        List of input file paths
    """
    path = Path(input_path)
    if path.is_file():
        return [str(path)]
    elif path.is_dir():
        if recursive:
            return [str(f) for f in path.rglob("*.chd") if f.is_file()]
        else:
            return [str(f) for f in path.glob("*.chd") if f.is_file()]
    else:
        return []


if __name__ == "__main__":
    sys.exit(main())
