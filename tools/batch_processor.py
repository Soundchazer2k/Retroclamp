#!/usr/bin/env python
"""
Batch processor for CHD operations.

This script provides a command-line interface for batch processing
CHD operations using the core/chdman.py module.
"""

import os
import sys
import argparse
from typing import List, Optional

# Add the parent directory to the path so we can import the core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chdman import CHDManager, CHDTask, CHDTaskType


def main():
    """Main entry point for the batch processor."""
    parser = argparse.ArgumentParser(description="Batch process CHD operations")
    parser.add_argument(
        "--chdman", 
        help="Path to CHDMAN executable (default: auto-detect)", 
        default=None
    )
    parser.add_argument(
        "--operation", 
        choices=["compress", "extract-cd", "extract-dvd", "extract-hd", "info", "verify"],
        required=True,
        help="Operation to perform"
    )
    parser.add_argument(
        "--input", 
        required=True, 
        help="Input file or directory"
    )
    parser.add_argument(
        "--output", 
        help="Output file or directory (required for compression/extraction)"
    )
    parser.add_argument(
        "--compression", 
        choices=["none", "fast", "normal", "best"],
        default="normal",
        help="Compression level (default: normal)"
    )
    parser.add_argument(
        "--hunk-size", 
        type=int, 
        default=16384,
        help="Hunk size in bytes (default: 16384)"
    )
    parser.add_argument(
        "--verify", 
        action="store_true", 
        default=True,
        help="Verify after operation (default: True)"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        default=False,
        help="Force overwrite of output files (default: False)"
    )
    parser.add_argument(
        "--recursive", 
        action="store_true", 
        default=False,
        help="Process directories recursively (default: False)"
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
        "verify": CHDTaskType.VERIFY
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
                print("Error: --output is required for compression/extraction operations")
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
            force=args.force
        )
        
        manager.add_task(task)
    
    # Execute tasks
    try:
        signals_list = manager.execute_all_tasks()
        
        # Connect signals for progress reporting
        for i, signals in enumerate(signals_list):
            signals.started.connect(lambda msg, i=i: print(f"Task {i+1}/{len(signals_list)}: {msg}"))
            signals.progress.connect(lambda pct, msg, i=i: print(f"Task {i+1}/{len(signals_list)}: {pct:.1f}% - {msg}"))
            signals.finished.connect(lambda success, msg, i=i: print(f"Task {i+1}/{len(signals_list)}: {'Completed' if success else 'Failed'} - {msg}"))
            signals.error.connect(lambda msg, i=i: print(f"Task {i+1}/{len(signals_list)}: Error - {msg}"))
        
        print("All tasks completed")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1


def get_input_files(input_path: str, recursive: bool = False) -> List[str]:
    """Get a list of input files from a path.
    
    Args:
        input_path: Path to input file or directory
        recursive: Whether to search directories recursively
        
    Returns:
        List of input file paths
    """
    if os.path.isfile(input_path):
        return [input_path]
    
    input_files = []
    
    if recursive:
        for root, _, files in os.walk(input_path):
            for file in files:
                input_files.append(os.path.join(root, file))
    else:
        for item in os.listdir(input_path):
            item_path = os.path.join(input_path, item)
            if os.path.isfile(item_path):
                input_files.append(item_path)
    
    return input_files


if __name__ == "__main__":
    sys.exit(main())
