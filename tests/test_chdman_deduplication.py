import unittest
from unittest.mock import patch

from core.chdman import CHDManager, CHDTask, CHDTaskType


class TestCHDManagerDeduplication(unittest.TestCase):
    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value="dummy_chdman")
    def test_no_duplicate_workers_for_same_task_object(self, mock_which, mock_exists):
        manager = CHDManager()
        task = CHDTask(
            task_type=CHDTaskType.COMPRESS,
            input_file="dummy_input.iso",
            output_file="dummy_output.chd",
        )
        signals1 = manager.execute_task(task)
        signals2 = manager.execute_task(task)
        self.assertIs(signals1, signals2)


if __name__ == "__main__":
    unittest.main()
