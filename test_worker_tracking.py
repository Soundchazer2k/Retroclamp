import os
import sys
import time
from PySide6.QtCore import QCoreApplication, QTimer
from core.chdman import CHDManager, CHDTaskType, CHDTask


def main():
    # Create a QApplication instance (required for Qt signals/slots)
    app = QCoreApplication([])
    
    # Create a CHDManager instance
    manager = CHDManager()
    print(f"Initial active tasks count: {manager.get_active_tasks_count()}")
    
    # Create a test directory if it doesn't exist
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
    os.makedirs(test_dir, exist_ok=True)
    
    # Create a test input file
    input_file = os.path.join(test_dir, "test_input.bin")
    with open(input_file, "wb") as f:
        f.write(b"\x00" * 1024 * 1024)  # 1MB file
    
    # Create a test output file path
    output_file = os.path.join(test_dir, "test_output.chd")
    
    # Create a task
    task = CHDTask(
        task_type=CHDTaskType.COMPRESS,
        input_file=input_file,
        output_file=output_file,
        compression_level="normal",
        media_type="Hard Disk"
    )
    
    # Add the task to the manager
    manager.add_task(task)
    
    # Execute the task
    print("Executing task...")
    manager.execute_all_tasks()
    
    # Check active tasks count after execution
    print(f"Active tasks count after execution: {manager.get_active_tasks_count()}")
    
    # Set up a timer to periodically check the active tasks count
    def check_tasks():
        count = manager.get_active_tasks_count()
        print(f"Current active tasks count: {count}")
        if count == 0:
            print("All tasks completed!")
            # Clean up
            if os.path.exists(output_file):
                print(f"Output file created: {output_file}")
            # Exit the application
            app.quit()
    
    # Check every 1 second
    timer = QTimer()
    timer.timeout.connect(check_tasks)
    timer.start(1000)
    
    # Run the application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
