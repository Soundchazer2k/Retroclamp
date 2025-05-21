#!/usr/bin/env python3
"""
PRD Parser for RetroClamp

This script parses a PRD markdown file and generates a tasks.json file for Taskmaster.
"""

import json
from pathlib import Path
from datetime import datetime

def parse_prd(prd_path: str, output_dir: str = "tasks") -> None:
    """Parse PRD file and generate tasks.json.
    
    Args:
        prd_path: Path to the PRD markdown file
        output_dir: Directory to save tasks.json (default: 'tasks')
    """
    # Create output directory if it doesn't exist
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(exist_ok=True)
    
    # Read the PRD file
    with open(prd_path, 'r', encoding='utf-8') as f:
        pass
    
    # Parse the PRD to extract tasks
    tasks = []
    
    # Task 1: Implement JobManager
    tasks.append({
        "id": 1,
        "title": "Implement JobManager Singleton",
        "description": "Create a singleton JobManager class to handle all job processing.",
        "priority": "high",
        "status": "pending",
        "dependencies": [],
        "details": """
        - Create JobManager class with singleton pattern
        - Implement job queue management
        - Add methods for adding/removing jobs
        - Add progress tracking
        - Add error handling
        """,
        "test_strategy": "Test job queue management and progress tracking"
    })
    
    # Task 2: Implement ArchiveUtils
    tasks.append({
        "id": 2,
        "title": "Implement ArchiveUtils",
        "description": "Create utility for handling archive extraction and pruning.",
        "priority": "high",
        "status": "pending",
        "dependencies": [],
        "details": """
        - Support for common archive formats (zip, 7z, rar)
        - Extract archives to temporary directories
        - Prune unnecessary files after extraction
        - Register temp dirs with TempDirManager
        """,
        "test_strategy": "Test extraction of different archive formats"
    })
    
    # Task 3: Implement TempDirManager
    tasks.append({
        "id": 3,
        "title": "Implement TempDirManager",
        "description": "Create a manager for temporary directories.",
        "priority": "high",
        "status": "pending",
        "dependencies": [],
        "details": """
        - Track all temporary directories
        - Clean up on application shutdown
        - Handle orphaned temp dirs on startup
        - Provide methods for temp dir creation and registration
        """,
        "test_strategy": "Test temp dir creation and cleanup"
    })
    
    # Task 4: Implement CheckpointManager
    tasks.append({
        "id": 4,
        "title": "Implement CheckpointManager",
        "description": "Create a manager for saving and restoring processing state.",
        "priority": "high",
        "status": "pending",
        "dependencies": [1],  # Depends on JobManager
        "details": """
        - Save processing state to JSON
        - Restore state on application restart
        - Validate checkpoint files
        - Handle versioning of checkpoints
        """,
        "test_strategy": "Test checkpoint creation and restoration"
    })
    
    # Task 5: Update CompressionTab
    tasks.append({
        "id": 5,
        "title": "Update CompressionTab",
        "description": "Update the compression tab to use the new JobManager.",
        "priority": "medium",
        "status": "pending",
        "dependencies": [1, 2],  # Depends on JobManager and ArchiveUtils
        "details": """
        - Connect UI to JobManager
        - Update progress display
        - Handle errors appropriately
        - Update status messages
        """,
        "test_strategy": "Test compression with various file types"
    })
    
    # Task 6: Update BatchTab
    tasks.append({
        "id": 6,
        "title": "Update BatchTab",
        "description": "Update the batch tab to use the new JobManager.",
        "priority": "medium",
        "status": "pending",
        "dependencies": [1, 2, 4],  # Depends on JobManager, ArchiveUtils, and CheckpointManager
        "details": """
        - Connect UI to JobManager
        - Implement drag-and-drop support
        - Handle batch processing with pause/resume
        - Update progress display
        """,
        "test_strategy": "Test batch processing with multiple files"
    })
    
    # Task 7: Implement Unified Logging
    tasks.append({
        "id": 7,
        "title": "Implement Unified Logging",
        "description": "Create a unified logging system for all operations.",
        "priority": "medium",
        "status": "pending",
        "dependencies": [],
        "details": """
        - Log all operations to a file
        - Display logs in the UI
        - Support different log levels
        - Rotate log files
        """,
        "test_strategy": "Verify log file creation and content"
    })
    
    # Task 8: Add Error Recovery
    tasks.append({
        "id": 8,
        "title": "Add Error Recovery",
        "description": "Implement error recovery mechanisms.",
        "priority": "high",
        "status": "pending",
        "dependencies": [1, 4],  # Depends on JobManager and CheckpointManager
        "details": """
        - Handle file access errors
        - Recover from crashes
        - Allow retry/skip on failure
        - Preserve state for recovery
        """,
        "test_strategy": "Test error scenarios and recovery"
    })
    
    # Task 9: Update Documentation
    tasks.append({
        "id": 9,
        "title": "Update Documentation",
        "description": "Update documentation to reflect new architecture.",
        "priority": "low",
        "status": "pending",
        "dependencies": [1, 2, 3, 4],  # After core components are implemented
        "details": """
        - Update architecture documentation
        - Add user guide for new features
        - Document API changes
        - Update README
        """,
        "test_strategy": "Review documentation for accuracy"
    })
    
    # Task 10: Testing and Bug Fixes
    tasks.append({
        "id": 10,
        "title": "Testing and Bug Fixes",
        "description": "Thoroughly test the application and fix any issues.",
        "priority": "high",
        "status": "pending",
        "dependencies": [1, 2, 3, 4, 5, 6, 7, 8],  # After all features are implemented
        "details": """
        - Write unit tests
        - Perform integration testing
        - Fix any bugs found
        - Optimize performance
        """,
        "test_strategy": "Run test suite and verify all tests pass"
    })
    
    # Create tasks.json structure
    tasks_data = {
        "version": "1.0",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "tasks": tasks
    }
    
    # Write tasks to file
    output_file = output_dir_path / "tasks.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tasks_data, f, indent=2)
    
    print(f"Successfully generated {len(tasks)} tasks in {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        prd_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "tasks"
        parse_prd(prd_path, output_dir)
    else:
        print("Usage: python parse_prd.py <prd_file> [output_dir]")
