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
            media_type="cd",
        )
        returned_tuple1 = manager.initiate_task_and_get_signals(task)
        signals_obj1, worker_obj1 = returned_tuple1

        returned_tuple2 = manager.initiate_task_and_get_signals(task)
        signals_obj2, worker_obj2 = returned_tuple2

        # For debugging, confirm the IDs of the objects
        # print(f"TEST_DEBUG: signals_obj1 ID: {id(signals_obj1)}, worker_obj1 ID: {id(worker_obj1)}")
        # print(f"TEST_DEBUG: signals_obj2 ID: {id(signals_obj2)}, worker_obj2 ID: {id(worker_obj2)}")

        self.assertIs(
            worker_obj1,
            worker_obj2,
            "Worker objects should be the same instance for identical tasks.",
        )
        self.assertIs(
            signals_obj1,
            signals_obj2,
            "Signals objects should be the same instance for identical tasks.",
        )


if __name__ == "__main__":
    unittest.main()
