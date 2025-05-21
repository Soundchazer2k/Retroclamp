#!/usr/bin/env python
"""
Test script to verify the CHDTask class with user_data parameter.
"""

import sys
from core.chdman import CHDTask, CHDTaskType

def test_chdtask_user_data():
    """Test the CHDTask class with user_data parameter."""
    print("Testing CHDTask with user_data parameter...")
    
    # Create a CHDTask with user_data
    task = CHDTask(
        task_type=CHDTaskType.CREATE_CD,
        input_file="test_input.cue",
        output_file="test_output.chd",
        algorithms="cdlz,cdzl",
        hunk_size=2448,
        force=True,
        media_type="CD",
        user_data={"row": 1, "original_input": "test_input.cue", "custom_field": "test_value"}
    )
    
    # Verify the user_data was stored correctly
    print(f"Task type: {task.task_type}")
    print(f"Input file: {task.input_file}")
    print(f"Output file: {task.output_file}")
    print(f"Algorithms: {task.algorithms}")
    print(f"Hunk size: {task.hunk_size}")
    print(f"Force: {task.force}")
    print(f"Media type: {task.media_type}")
    print(f"User data: {task.user_data}")
    
    # Verify specific user_data fields
    assert task.user_data.get("row") == 1, "Row should be 1"
    assert task.user_data.get("original_input") == "test_input.cue", "Original input mismatch"
    assert task.user_data.get("custom_field") == "test_value", "Custom field mismatch"
    
    print("All assertions passed!")
    return True

def main():
    """Main entry point."""
    success = test_chdtask_user_data()
    print(f"Test {'passed' if success else 'failed'}!")
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
