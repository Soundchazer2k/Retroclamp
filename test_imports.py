import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Test imports
try:
    from core.batch_processor import BatchProcessor
    print("Successfully imported BatchProcessor")
except ImportError as e:
    print(f"Failed to import BatchProcessor: {e}")

try:
    from core.chd_manager import CHDManager
    print("Successfully imported CHDManager")
except ImportError as e:
    print(f"Failed to import CHDManager: {e}")

print("Python path:")
for path in sys.path:
    print(f"  {path}")
